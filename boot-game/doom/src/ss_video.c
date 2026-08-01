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

    /* Largest integer-free scale that fits both axes, in 16.16 fixed point. */
    const int scale_x = (SS_PANEL_W << 16) / src_w;
    const int scale_y = (SS_PANEL_H << 16) / src_h;
    const int scale = scale_x < scale_y ? scale_x : scale_y;

    const int out_w = (src_w * scale) >> 16;
    const int out_h = (src_h * scale) >> 16;
    const int origin_x = (SS_PANEL_W - out_w) / 2;
    const int origin_y = (SS_PANEL_H - out_h) / 2;

    for (int y = 0; y < out_h; y++) {
        const int sy = (y << 16) / scale;
        const uint32_t *src_row = src + (size_t)sy * src_w;
        uint16_t *dst_row = dst + (size_t)(origin_y + y) * SS_PANEL_W + origin_x;

        for (int x = 0; x < out_w; x++) {
            dst_row[x] = to_565(src_row[(x << 16) / scale]);
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
