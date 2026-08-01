#include "ss_gpio.h"

#include <fcntl.h>
#include <stdint.h>
#include <stddef.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

/* BCM2835 GPIO register offsets, in 32 bit words. */
#define GPFSEL0   0
#define GPSET0    7
#define GPCLR0   10
#define GPLEV0   13
#define GPPUD    37
#define GPPUDCLK0 38

#define GPIO_MAP_LEN 4096

static volatile uint32_t *gpio = NULL;
static int gpio_fd = -1;

static void short_delay(void)
{
    struct timespec ts = { 0, 1000000 }; /* 1ms, generous for the pull latch */
    nanosleep(&ts, NULL);
}

int ss_gpio_open(void)
{
    gpio_fd = open("/dev/gpiomem", O_RDWR | O_SYNC);
    if (gpio_fd < 0) {
        return -1;
    }

    void *mapped = mmap(NULL, GPIO_MAP_LEN, PROT_READ | PROT_WRITE, MAP_SHARED, gpio_fd, 0);
    if (mapped == MAP_FAILED) {
        close(gpio_fd);
        gpio_fd = -1;
        return -1;
    }

    gpio = (volatile uint32_t *)mapped;
    return 0;
}

void ss_gpio_close(void)
{
    if (gpio) {
        munmap((void *)gpio, GPIO_MAP_LEN);
        gpio = NULL;
    }
    if (gpio_fd >= 0) {
        close(gpio_fd);
        gpio_fd = -1;
    }
}

static void set_function(int pin, uint32_t function)
{
    const int reg = GPFSEL0 + pin / 10;
    const int shift = (pin % 10) * 3;

    gpio[reg] = (gpio[reg] & ~(0x7u << shift)) | (function << shift);
}

void ss_gpio_output(int pin)
{
    set_function(pin, 0x1);
}

void ss_gpio_input_pullup(int pin)
{
    set_function(pin, 0x0);

    /* BCM2835 pull configuration: set the mode, clock it into the pin, clear. */
    gpio[GPPUD] = 0x2; /* pull up */
    short_delay();
    gpio[GPPUDCLK0 + pin / 32] = 1u << (pin % 32);
    short_delay();
    gpio[GPPUD] = 0;
    gpio[GPPUDCLK0 + pin / 32] = 0;
}

void ss_gpio_write(int pin, int high)
{
    const int reg = (high ? GPSET0 : GPCLR0) + pin / 32;
    gpio[reg] = 1u << (pin % 32);
}

int ss_gpio_read(int pin)
{
    return (gpio[GPLEV0 + pin / 32] >> (pin % 32)) & 1u;
}
