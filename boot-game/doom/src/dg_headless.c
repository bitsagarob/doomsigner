/*
 * Headless doomgeneric target, for testing the port without a Raspberry Pi.
 *
 * Runs the same scaler and the same unlock detector as the device target, but
 * writes frames to disk instead of pushing them over SPI, and takes its input
 * from a script instead of GPIO. The clock is virtual so runs are repeatable.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "doomgeneric.h"
#include "doomkeys.h"
#include "ss_unlock.h"
#include "ss_video.h"

/* Stand-ins for the three side buttons. */
#define SS_KEY1 0xE1
#define SS_KEY2 0xE2
#define SS_KEY3 0xE3

static const int unlock_sequence[] = { SS_KEY1, SS_KEY2, SS_KEY3 };
static ss_unlock_t unlock;

static uint16_t panel[SS_PANEL_W * SS_PANEL_H];
static uint32_t virtual_ms = 0;
static int frame = 0;

static int max_frames = 600;
static int dump_every = 100;
static const char *out_dir = ".";

/* Scripted input: {frame, key, pressed}. Terminated by frame < 0. */
static const int script[][3] = {
    { 120, KEY_ENTER, 1 }, { 122, KEY_ENTER, 0 },   /* skip the title */
    { 200, KEY_ENTER, 1 }, { 202, KEY_ENTER, 0 },
    { 400, SS_KEY1, 1 },   { 401, SS_KEY1, 0 },     /* then the unlock */
    { 410, SS_KEY2, 1 },   { 411, SS_KEY2, 0 },
    { 420, SS_KEY3, 1 },   { 421, SS_KEY3, 0 },
    { -1, 0, 0 },
};
static int script_index = 0;

static void write_ppm(void)
{
    char path[512];
    snprintf(path, sizeof(path), "%s/doom-%04d.ppm", out_dir, frame);

    FILE *file = fopen(path, "wb");
    if (!file) {
        return;
    }

    fprintf(file, "P6\n%d %d\n255\n", SS_PANEL_W, SS_PANEL_H);
    for (int i = 0; i < SS_PANEL_W * SS_PANEL_H; i++) {
        const uint16_t p = panel[i];
        const unsigned char rgb[3] = {
            (unsigned char)(((p >> 11) & 0x1F) << 3),
            (unsigned char)(((p >> 5) & 0x3F) << 2),
            (unsigned char)((p & 0x1F) << 3),
        };
        fwrite(rgb, 1, 3, file);
    }
    fclose(file);
    printf("wrote %s\n", path);
}

void DG_Init(void)
{
    ss_unlock_init(&unlock, unlock_sequence, 3);
}

void DG_DrawFrame(void)
{
    ss_scale_to_565(DG_ScreenBuffer, DOOMGENERIC_RESX, DOOMGENERIC_RESY, panel);

    if (frame % dump_every == 0) {
        write_ppm();
    }

    frame++;
    if (frame >= max_frames) {
        printf("reached %d frames without unlocking\n", max_frames);
        exit(0);
    }
}

void DG_SleepMs(uint32_t ms)
{
    (void)ms; /* virtual clock: never actually sleep */
}

uint32_t DG_GetTicksMs(void)
{
    virtual_ms += 28; /* about 35Hz, DOOM's native tick rate */
    return virtual_ms;
}

int DG_GetKey(int *pressed, unsigned char *key)
{
    if (script[script_index][0] < 0 || script[script_index][0] > frame) {
        return 0;
    }

    const int scripted_key = script[script_index][1];
    *pressed = script[script_index][2];
    *key = (unsigned char)scripted_key;
    script_index++;

    if (*pressed && ss_unlock_feed(&unlock, scripted_key)) {
        /* On the device this is where we exec SeedSigner. */
        printf("UNLOCKED at frame %d\n", frame);
        write_ppm();
        exit(0);
    }

    /* The side buttons are ours, not DOOM's. */
    return (scripted_key == SS_KEY1 || scripted_key == SS_KEY2 || scripted_key == SS_KEY3) ? 0 : 1;
}

void DG_SetWindowTitle(const char *title)
{
    (void)title;
}

int main(int argc, char **argv)
{
    const char *env;

    if ((env = getenv("SS_OUT_DIR"))) out_dir = env;
    if ((env = getenv("SS_MAX_FRAMES"))) max_frames = atoi(env);
    if ((env = getenv("SS_DUMP_EVERY"))) dump_every = atoi(env);

    doomgeneric_Create(argc, argv);

    for (;;) {
        doomgeneric_Tick();
    }

    return 0;
}
