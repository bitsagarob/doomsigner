/*
 * Minimal BCM2835 GPIO via /dev/gpiomem.
 *
 * Pin numbers here are BCM, not the BOARD numbering SeedSigner's Python uses.
 * The mapping is in ss_pins.h.
 */
#ifndef SS_GPIO_H
#define SS_GPIO_H

int ss_gpio_open(void);
void ss_gpio_close(void);

void ss_gpio_output(int pin);
void ss_gpio_input_pullup(int pin);
void ss_gpio_write(int pin, int high);
int ss_gpio_read(int pin);

#endif /* SS_GPIO_H */
