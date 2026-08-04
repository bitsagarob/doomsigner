#include "ss_video.h"

#include <string.h>

static uint16_t to_565(uint32_t xrgb)
{
    const uint8_t r = (xrgb >> 16) & 0xFF;
    const uint8_t g = (xrgb >> 8) & 0xFF;
    const uint8_t b = xrgb & 0xFF;

    return (uint16_t)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
}

void ss_scale_to_565(const uint32_t *src, int src_w, int src_h, uint16_t *dst)
{
    memset(dst, 0, SS_PANEL_W * SS_PANEL_H * sizeof(uint16_t));

    if (src_w <= 0 || src_h <= 0) {
        return;
    }

    /* Each axis scaled to the panel independently, in 16.16 fixed point.
     *
     * Not a uniform scale with bars around it, which is what this did first and
     * what looks like the safe choice. DOOM's 320x200 was never meant to be
     * shown with square pixels: it was drawn for a 4:3 screen, so every pixel
     * was displayed a fifth taller than it was wide. Fitting 320x200 into a
     * 320x240 panel one pixel to one pixel keeps the original's proportions
     * wrong and spends forty rows of a small screen on black to do it.
     *
     * Filling both axes on a 4:3 panel therefore is not a stretch, it is the
     * undoing of one, and the result is the shape the artwork was drawn at. On a
     * square 240x240 panel the same rule fills the screen as well, at the cost
     * of a picture narrower than intended; the alternative there was bars over
     * a third of the panel, which is the worse of the two on a screen this
     * small. */
    const int scale_x = (SS_PANEL_W << 16) / src_w;
    const int scale_y = (SS_PANEL_H << 16) / src_h;

    for (int y = 0; y < SS_PANEL_H; y++) {
        const int sy = (y << 16) / scale_y;
        const uint32_t *src_row = src + (size_t)(sy < src_h ? sy : src_h - 1) * src_w;
        uint16_t *dst_row = dst + (size_t)y * SS_PANEL_W;

        for (int x = 0; x < SS_PANEL_W; x++) {
            const int sx = (x << 16) / scale_x;
            dst_row[x] = to_565(src_row[sx < src_w ? sx : src_w - 1]);
        }
    }
}

void ss_pack_wire(const uint16_t *frame, uint8_t *out)
{
    for (int i = 0; i < SS_PANEL_W * SS_PANEL_H; i++) {
        out[i * 2] = (uint8_t)(frame[i] >> 8);
        out[i * 2 + 1] = (uint8_t)(frame[i] & 0xFF);
    }
}
