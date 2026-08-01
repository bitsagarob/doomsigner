/*
 * Reads raw XRGB8888 pixels on stdin, writes what the panel would receive on
 * stdout. Exists so a test can compare our conversion against the bytes
 * SeedSigner's Python driver produces for the same image.
 */
#include <stdio.h>
#include <stdlib.h>

#include "ss_video.h"

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: %s <width> <height>\n", argv[0]);
        return 2;
    }

    const int width = atoi(argv[1]);
    const int height = atoi(argv[2]);
    if (width <= 0 || height <= 0) {
        return 2;
    }

    uint32_t *src = malloc((size_t)width * height * sizeof(uint32_t));
    static uint16_t panel[SS_PANEL_W * SS_PANEL_H];
    if (!src) {
        return 1;
    }

    if (fread(src, sizeof(uint32_t), (size_t)width * height, stdin) != (size_t)width * height) {
        free(src);
        return 1;
    }

    static uint8_t wire[SS_PANEL_W * SS_PANEL_H * 2];
    ss_scale_to_565(src, width, height, panel);
    ss_pack_wire(panel, wire);
    fwrite(wire, 1, sizeof(wire), stdout);

    free(src);
    return 0;
}
