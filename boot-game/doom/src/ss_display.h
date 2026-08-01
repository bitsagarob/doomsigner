/*
 * Pushing frames to the panel.
 *
 * Two backends, chosen at runtime with SS_DISPLAY:
 *   spi  the real ST7789 over /dev/spidev0.0 (default)
 *   fd   raw RGB565 to a file descriptor, for bisecting a black screen and for
 *        driving the panel from Python instead
 */
#ifndef SS_DISPLAY_H
#define SS_DISPLAY_H

#include <stdint.h>

int ss_display_init(void);
void ss_display_push(const uint16_t *frame);
void ss_display_close(void);

#endif /* SS_DISPLAY_H */
