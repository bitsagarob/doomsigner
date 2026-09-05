// SPDX-License-Identifier: GPL-2.0
/*
 * ss_display_capture — a fake SeedSigner display connection.
 *
 * SeedSigner drives its screen itself: ST7789.py opens /dev/spidev0.0 and
 * toggles the data/command, reset and backlight lines through libgpiod. Nothing
 * in the kernel knows it is a display. So to see what the device would actually
 * put on the panel, capture the wire.
 *
 * This module presents the two halves of that connection and records both:
 *
 *   - an SPI controller, so /dev/spidev0.0 exists and the app's real driver can
 *     open it with its real settings,
 *   - a 4-line gpiochip carrying D/C, RST and BL, so the app's real gpio calls
 *     land here instead of on a Pi.
 *
 * Every SPI message is written to /dev/ss_spicap tagged with the level of the
 * D/C line at the moment it was sent, which is the one bit that decides whether
 * those bytes are an ST7789 command or pixels. A userspace decoder turns the
 * stream back into a picture.
 *
 * The app is not modified in any way: it thinks it is talking to a Waveshare
 * LCD hat.
 */

#include <linux/module.h>
#include <linux/init.h>
#include <linux/kfifo.h>
#include <linux/gpio/driver.h>
#include <linux/miscdevice.h>
#include <linux/platform_device.h>
#include <linux/poll.h>
#include <linux/slab.h>
#include <linux/spi/spi.h>
#include <linux/uaccess.h>

#define CAP_FIFO_BYTES	(8 * 1024 * 1024)
/* 32 lines so the pin numbers match a real 40-pin Pi header: the app then runs
 * with its stock io_config.json and never learns it is not on hardware. */
#define CAP_LINES	32
#define LINE_DC		25
#define LINE_RST	27
#define LINE_BL		24

/* One record per SPI message: this header, then len bytes of payload. */
struct cap_header {
	u8  dc;		/* data/command line level when the message was sent */
	u8  cs;		/* chip select */
	u16 flags;	/* bit 0: this record is a gpio event, not a transfer */
	u32 len;
} __packed;

#define CAP_FLAG_GPIO	0x0001

static struct platform_device *pdev;
static struct spi_controller *ctlr;
static struct spi_device *sdev;
static struct gpio_chip gc;

static DEFINE_KFIFO(cap_fifo, u8, CAP_FIFO_BYTES);
static DEFINE_SPINLOCK(cap_lock);
static DECLARE_WAIT_QUEUE_HEAD(cap_wait);

/* Buttons are wired to ground and read through a pull-up, so released is high.
 * Start every line high; the harness pulls one low to press it. */
static u8 line_value[CAP_LINES];
static atomic_t dropped = ATOMIC_INIT(0);

static void cap_record(u8 dc, u8 cs, u16 flags, const void *buf, u32 len)
{
	struct cap_header hdr = { .dc = dc, .cs = cs, .flags = flags, .len = len };
	unsigned long irqflags;
	unsigned int room;

	spin_lock_irqsave(&cap_lock, irqflags);
	room = kfifo_avail(&cap_fifo);
	if (room < sizeof(hdr) + len) {
		/* Never block the app: a full fifo means the reader is behind,
		 * and a silently short picture is worse than a loud counter. */
		atomic_inc(&dropped);
		spin_unlock_irqrestore(&cap_lock, irqflags);
		return;
	}
	kfifo_in(&cap_fifo, (u8 *)&hdr, sizeof(hdr));
	if (len)
		kfifo_in(&cap_fifo, (const u8 *)buf, len);
	spin_unlock_irqrestore(&cap_lock, irqflags);
	wake_up_interruptible(&cap_wait);
}

/* ---- the gpiochip half: D/C, RST, BL ---- */

static int cap_gpio_get(struct gpio_chip *chip, unsigned int offset)
{
	if (offset >= CAP_LINES)
		return -EINVAL;
	return line_value[offset];
}

static void cap_gpio_set(struct gpio_chip *chip, unsigned int offset, int value)
{
	u8 event[2];

	if (offset >= CAP_LINES)
		return;
	line_value[offset] = value ? 1 : 0;

	/* Reset and backlight changes matter to a decoder too: a reset means
	 * the panel state the app assumes has been thrown away. */
	event[0] = offset;
	event[1] = line_value[offset];
	cap_record(line_value[LINE_DC], 0, CAP_FLAG_GPIO, event, sizeof(event));
}

static int cap_gpio_direction_output(struct gpio_chip *chip, unsigned int offset,
				     int value)
{
	cap_gpio_set(chip, offset, value);
	return 0;
}

static int cap_gpio_direction_input(struct gpio_chip *chip, unsigned int offset)
{
	return 0;
}

/* periphery requests the button lines with a pull-up bias. Without a
 * set_config the kernel rejects that request and the app cannot claim its
 * buttons at all, so accept the configuration and model the pull in
 * line_value instead. */
static int cap_gpio_set_config(struct gpio_chip *chip, unsigned int offset,
			       unsigned long config)
{
	return 0;
}

/* ---- the SPI half ---- */

static int cap_transfer_one_message(struct spi_controller *c,
				    struct spi_message *m)
{
	struct spi_transfer *t;

	list_for_each_entry(t, &m->transfers, transfer_list) {
		if (t->tx_buf)
			cap_record(line_value[LINE_DC], m->spi->chip_select[0],
				   0, t->tx_buf, t->len);
		/* The panel never answers, and neither does this. Reads come
		 * back as zeroes, exactly as an ST7789 with MISO unwired. */
		if (t->rx_buf)
			memset((void *)t->rx_buf, 0, t->len);
		m->actual_length += t->len;
	}
	m->status = 0;
	spi_finalize_current_message(c);
	return 0;
}

/* ---- the char device userspace reads ---- */

static ssize_t cap_read(struct file *file, char __user *buf, size_t count,
			loff_t *ppos)
{
	unsigned int copied = 0;
	int ret;

	if (kfifo_is_empty(&cap_fifo)) {
		if (file->f_flags & O_NONBLOCK)
			return -EAGAIN;
		ret = wait_event_interruptible(cap_wait, !kfifo_is_empty(&cap_fifo));
		if (ret)
			return ret;
	}
	ret = kfifo_to_user(&cap_fifo, buf, count, &copied);
	return ret ? ret : copied;
}

/* Press a button: write two bytes, the line number and its new level. This is
 * the harness's only input channel, so a test never touches the app. */
static ssize_t cap_write(struct file *file, const char __user *buf, size_t count,
			 loff_t *ppos)
{
	u8 pair[2];

	if (count < sizeof(pair))
		return -EINVAL;
	if (copy_from_user(pair, buf, sizeof(pair)))
		return -EFAULT;
	if (pair[0] >= CAP_LINES)
		return -EINVAL;
	line_value[pair[0]] = pair[1] ? 1 : 0;
	return sizeof(pair);
}

static __poll_t cap_poll(struct file *file, poll_table *wait)
{
	poll_wait(file, &cap_wait, wait);
	return kfifo_is_empty(&cap_fifo) ? 0 : (EPOLLIN | EPOLLRDNORM);
}

static const struct file_operations cap_fops = {
	.owner   = THIS_MODULE,
	.read    = cap_read,
	.write   = cap_write,
	.poll    = cap_poll,
};

static struct miscdevice cap_misc = {
	.minor = MISC_DYNAMIC_MINOR,
	.name  = "ss_spicap",
	.fops  = &cap_fops,
	.mode  = 0666,
};

static int __init ss_capture_init(void)
{
	struct spi_board_info bi = {
		.modalias     = "dh2228fv",	/* spidev binds to this */
		.max_speed_hz = 40000000,	/* what ST7789.py asks for */
		.bus_num      = 0,
		.chip_select  = 0,
		.mode         = SPI_MODE_0,
	};
	int ret;

	pdev = platform_device_register_simple("ss-display-capture", -1, NULL, 0);
	if (IS_ERR(pdev))
		return PTR_ERR(pdev);

	gc.label             = "ss-display";
	gc.parent            = &pdev->dev;
	gc.owner             = THIS_MODULE;
	gc.base              = -1;
	gc.ngpio             = CAP_LINES;
	gc.can_sleep         = false;
	gc.get               = cap_gpio_get;
	gc.set               = cap_gpio_set;
	gc.direction_output  = cap_gpio_direction_output;
	gc.direction_input   = cap_gpio_direction_input;
	gc.set_config        = cap_gpio_set_config;

	/* released == high, matching the hat's pull-ups */
	memset(line_value, 1, sizeof(line_value));

	ret = gpiochip_add_data(&gc, NULL);
	if (ret)
		goto err_pdev;

	ret = misc_register(&cap_misc);
	if (ret)
		goto err_gpio;

	ctlr = spi_alloc_host(&pdev->dev, 0);
	if (!ctlr) {
		ret = -ENOMEM;
		goto err_misc;
	}
	ctlr->bus_num              = 0;
	ctlr->num_chipselect       = 1;
	ctlr->mode_bits            = SPI_CPOL | SPI_CPHA;
	ctlr->bits_per_word_mask   = SPI_BPW_MASK(8);
	ctlr->transfer_one_message = cap_transfer_one_message;

	ret = spi_register_controller(ctlr);
	if (ret) {
		spi_controller_put(ctlr);
		goto err_misc;
	}

	sdev = spi_new_device(ctlr, &bi);
	if (!sdev) {
		ret = -ENODEV;
		goto err_spi;
	}

	pr_info("ss_display_capture: spi %s, gpiochip base %d, /dev/ss_spicap ready\n",
		dev_name(&sdev->dev), gc.base);
	return 0;

err_spi:
	spi_unregister_controller(ctlr);
err_misc:
	misc_deregister(&cap_misc);
err_gpio:
	gpiochip_remove(&gc);
err_pdev:
	platform_device_unregister(pdev);
	return ret;
}

static void __exit ss_capture_exit(void)
{
	int lost = atomic_read(&dropped);

	if (sdev)
		spi_unregister_device(sdev);
	spi_unregister_controller(ctlr);
	misc_deregister(&cap_misc);
	gpiochip_remove(&gc);
	platform_device_unregister(pdev);
	pr_info("ss_display_capture: unloaded, %d record(s) dropped\n", lost);
}

module_init(ss_capture_init);
module_exit(ss_capture_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Capture SeedSigner's SPI display traffic and D/C line");
