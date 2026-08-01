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

#endif /* SS_VIDEO_H */
