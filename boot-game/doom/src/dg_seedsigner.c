/*
 * The device target: DOOM on the SeedSigner's panel and buttons.
 *
 * KEY1, KEY2, KEY3 replaces this process with SeedSigner, exactly as the Python
 * games do. If anything here fails to start, we hand off rather than leave a
 * dead device.
 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#include "doomgeneric.h"
#include "doomkeys.h"
#include "ss_display.h"
#include "ss_input.h"
#include "ss_unlock.h"
#include "ss_video.h"

#define SEEDSIGNER_SRC "/opt/src"
#define PYTHON "/usr/bin/python3"

static const int UNLOCK_SEQUENCE[] = { SS_KEY1, SS_KEY2, SS_KEY3 };
static ss_unlock_t unlock;
static uint16_t panel[SS_PANEL_W * SS_PANEL_H];

static void launch_seedsigner(void)
{
    ss_display_close();

    if (chdir(SEEDSIGNER_SRC) != 0) {
        fprintf(stderr, "doom: cannot chdir to %s\n", SEEDSIGNER_SRC);
    }

    char *const argv[] = { (char *)PYTHON, (char *)"main.py", NULL };
    execv(PYTHON, argv);

    /* Only reached if execv failed, which would leave the user with nothing. */
    fprintf(stderr, "doom: execv failed, cannot start SeedSigner\n");
    exit(1);
}

void DG_Init(void)
{
    ss_unlock_init(&unlock, UNLOCK_SEQUENCE, 3);

    if (ss_display_init() != 0 || ss_input_init() != 0) {
        fprintf(stderr, "doom: hardware init failed, handing off\n");
        launch_seedsigner();
    }
}

void DG_DrawFrame(void)
{
    ss_scale_to_565(DG_ScreenBuffer, DOOMGENERIC_RESX, DOOMGENERIC_RESY, panel);
    ss_display_push(panel);
}

void DG_SleepMs(uint32_t ms)
{
    struct timespec ts = { ms / 1000, (ms % 1000) * 1000000L };
    nanosleep(&ts, NULL);
}

uint32_t DG_GetTicksMs(void)
{
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);

    return (uint32_t)(now.tv_sec * 1000 + now.tv_nsec / 1000000);
}

int DG_GetKey(int *pressed, unsigned char *key)
{
    int doom_key = 0;
    int is_pressed = 0;
    int side_button = 0;

    if (!ss_input_poll(&doom_key, &is_pressed, &side_button)) {
        return 0;
    }

    if (side_button && ss_unlock_feed(&unlock, side_button)) {
        launch_seedsigner();
    }

    *pressed = is_pressed;
    *key = (unsigned char)doom_key;
    return 1;
}

void DG_SetWindowTitle(const char *title)
{
    (void)title;
}

int main(int argc, char **argv)
{
    doomgeneric_Create(argc, argv);

    for (;;) {
        doomgeneric_Tick();
    }

    return 0;
}
