/*
 * The ST7789 initialisation sequence.
 *
 * Transcribed from SeedSigner's own driver, src/seedsigner/hardware/displays/
 * ST7789.py, which is what actually drives this panel today. Kept as data
 * rather than code so a test can compare it against that file and fail if
 * upstream ever changes the sequence.
 *
 * Each entry is { command, data length, data bytes... }.
 */
#ifndef SS_ST7789_INIT_H
#define SS_ST7789_INIT_H

#include <stdint.h>

typedef struct {
    uint8_t command;
    uint8_t length;
    uint8_t data[16];
} ss_st7789_cmd_t;

static const ss_st7789_cmd_t SS_ST7789_INIT[] = {
    { 0x36, 1,  { 0x70 } },                                  /* MADCTL */
    { 0x3A, 1,  { 0x05 } },                                  /* COLMOD, 16 bit */
    { 0xB2, 5,  { 0x0C, 0x0C, 0x00, 0x33, 0x33 } },          /* PORCTRL */
    { 0xB7, 1,  { 0x35 } },                                  /* GCTRL */
    { 0xBB, 1,  { 0x19 } },                                  /* VCOMS */
    { 0xC0, 1,  { 0x2C } },                                  /* LCMCTRL */
    { 0xC2, 1,  { 0x01 } },                                  /* VDVVRHEN */
    { 0xC3, 1,  { 0x12 } },                                  /* VRHS */
    { 0xC4, 1,  { 0x20 } },                                  /* VDVS */
    { 0xC6, 1,  { 0x0F } },                                  /* FRCTRL2 */
    { 0xD0, 2,  { 0xA4, 0xA1 } },                            /* PWCTRL1 */
    { 0xE0, 14, { 0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B, 0x3F,
                  0x54, 0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23 } }, /* PVGAMCTRL */
    { 0xE1, 14, { 0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C, 0x3F,
                  0x44, 0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23 } }, /* NVGAMCTRL */
    { 0x21, 0,  { 0 } },                                     /* INVON */
    { 0x11, 0,  { 0 } },                                     /* SLPOUT */
    { 0x29, 0,  { 0 } },                                     /* DISPON */
};

#define SS_ST7789_INIT_LEN (sizeof(SS_ST7789_INIT) / sizeof(SS_ST7789_INIT[0]))

#endif /* SS_ST7789_INIT_H */
