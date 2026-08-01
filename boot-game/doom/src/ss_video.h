/*
 * Scaling DOOM's 320x200 frame onto the 240x240 panel.
 *
 * Shared by both targets so the device and the headless test see exactly the
 * same pixels.
 */
#ifndef SS_VIDEO_H
#define SS_VIDEO_H

#include <stdint.h>

#define SS_PANEL_W 240
#define SS_PANEL_H 240

/*
 * Nearest-neighbour scale from XRGB8888 to RGB565, preserving aspect ratio and
 * letterboxing into the square panel. 320x200 lands as 240x150 with black bars.
 * `dst` must hold SS_PANEL_W * SS_PANEL_H uint16_t.
 */
void ss_scale_to_565(const uint32_t *src, int src_w, int src_h, uint16_t *dst);

/*
 * Pack a frame of host-order RGB565 into the byte order the ST7789 expects,
 * which is big endian. SeedSigner's Python gets this from an explicit
 * array.byteswap() before writing to SPI; we do the same here, and keeping it
 * separate means the pixel buffer itself stays in host order for anything that
 * wants to read it. `out` must hold SS_PANEL_W * SS_PANEL_H * 2 bytes.
 */
void ss_pack_wire(const uint16_t *frame, uint8_t *out);

#endif /* SS_VIDEO_H */
