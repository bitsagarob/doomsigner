/*
 * The browser target: DOOM inside the SeedSigner simulator.
 *
 * What the page is handed is what the panel is handed. This target runs the
 * same ss_video.c the device runs and emits the same big endian RGB565 bytes
 * that go over SPI, so the simulator draws the wire format rather than a
 * nicer browser rendering of the same game. Rendering DOOM's native 320x200
 * straight to a canvas would look better and would be a lie.
 *
 * The unlock is not here. On the device the three side buttons drive DOOM and
 * feed the unlock detector at the same time, which is safe because only the
 * exact sequence unlocks. In the browser the page owns the unlock, so KEY1,
 * KEY2 and KEY3 are given no game action at all: there is no path in this
 * binary from those three buttons into DOOM, which is a stronger guarantee
 * than a mapping that merely happens to be harmless today.
 */
#include <emscripten.h>
#include <stdint.h>
#include <stdio.h>

#include "doomgeneric.h"
#include "doomkeys.h"
#include "ss_video.h"

/*
 * Buttons are passed across from JS by position, not by DOOM keycode, so the
 * one place that decides what a button does stays here next to doomkeys.h.
 * The order is SeedSigner's own: the four way stick, its centre press, then
 * the three side buttons.
 */
enum {
    SS_BTN_UP, SS_BTN_DOWN, SS_BTN_LEFT, SS_BTN_RIGHT,
    SS_BTN_SELECT, SS_BTN_KEY1, SS_BTN_KEY2, SS_BTN_KEY3,
};

/*
 * Presses arrive from the browser's event loop and are drained by DG_GetKey
 * inside the tick, so they have to queue. One press can post two keys, hence
 * room for more than the eight buttons.
 */
#define KEY_QUEUE_SIZE 32

static uint16_t key_queue[KEY_QUEUE_SIZE];
static unsigned int queue_write = 0;
static unsigned int queue_read = 0;

static uint16_t panel[SS_PANEL_W * SS_PANEL_H];
static uint8_t wire[SS_PANEL_W * SS_PANEL_H * 2];

static void queue_key(int pressed, int key)
{
    key_queue[queue_write] = (uint16_t)((pressed << 8) | (key & 0xFF));
    queue_write = (queue_write + 1) % KEY_QUEUE_SIZE;
}

/*
 * Handing the frame out as a view into the heap rather than a copy: the JS
 * wrapper owns that policy, because it is the only side that knows whether its
 * caller keeps the bytes.
 */
EM_JS(void, ss_emit_frame, (const uint8_t *bytes, int length), {
    if (Module.onDoomFrame) {
        Module.onDoomFrame(HEAPU8.subarray(bytes, bytes + length));
    }
});

void DG_Init(void)
{
    /* Nothing to open: the panel, the buttons and the clock are all the page's. */
}

void DG_DrawFrame(void)
{
    ss_scale_to_565(DG_ScreenBuffer, DOOMGENERIC_RESX, DOOMGENERIC_RESY, panel);
    ss_pack_wire(panel, wire);
    ss_emit_frame(wire, (int)sizeof(wire));
}

void DG_SleepMs(uint32_t ms)
{
    /*
     * Deliberately nothing. A browser main thread cannot sleep, and spinning
     * here would freeze the tab for the whole wait. DOOM only ever sleeps to
     * wait for the next tic, and the main loop below already runs at that rate,
     * so the wait it wanted has happened by the time we are called again.
     */
    (void)ms;
}

uint32_t DG_GetTicksMs(void)
{
    return (uint32_t)emscripten_get_now();
}

int DG_GetKey(int *pressed, unsigned char *key)
{
    if (queue_read == queue_write) {
        return 0;
    }

    const uint16_t entry = key_queue[queue_read];
    queue_read = (queue_read + 1) % KEY_QUEUE_SIZE;

    *pressed = entry >> 8;
    *key = (unsigned char)(entry & 0xFF);
    return 1;
}

void DG_SetWindowTitle(const char *title)
{
    (void)title; /* There is no window; the page frames the panel itself. */
}

/*
 * Returns 1 if the button drove the game and 0 if it was left alone, which is
 * how the wrapper tells its caller that KEY1, KEY2 and KEY3 are still theirs.
 */
EMSCRIPTEN_KEEPALIVE
int ss_doom_button(int button, int pressed)
{
    switch (button) {
        case SS_BTN_UP:    queue_key(pressed, KEY_UPARROW);    return 1;
        case SS_BTN_DOWN:  queue_key(pressed, KEY_DOWNARROW);  return 1;
        case SS_BTN_LEFT:  queue_key(pressed, KEY_LEFTARROW);  return 1;
        case SS_BTN_RIGHT: queue_key(pressed, KEY_RIGHTARROW); return 1;

        case SS_BTN_SELECT:
            /*
             * Fire and use on the same press. Five buttons is one short of a
             * playable DOOM: without use the player cannot open the first door
             * on E1M1 and the game ends in the opening room. Use does nothing
             * unless you are facing a door or a switch, so spending fire's
             * button on it too costs nothing, and it keeps the three reserved
             * buttons out of it.
             */
            queue_key(pressed, KEY_FIRE);
            queue_key(pressed, KEY_USE);
            return 1;

        default:
            /* KEY1, KEY2, KEY3. They spell the unlock; DOOM never sees them. */
            return 0;
    }
}

EMSCRIPTEN_KEEPALIVE
void ss_doom_start(const char *wad_path)
{
    /*
     * doomgeneric keeps argv by reference for the rest of the run, so these
     * outlive the call. -warp starts the game in E1M1 instead of on the title
     * screen: with KEY1 to KEY3 reserved there is no menu key left, so nothing
     * the visitor can press would ever get them out of the attract loop.
     */
    static char wad[256];
    static char *argv[] = { "doom", "-iwad", wad, "-warp", "1", "1" };

    snprintf(wad, sizeof(wad), "%s", wad_path);

    doomgeneric_Create((int)(sizeof(argv) / sizeof(argv[0])), argv);

    /*
     * 35Hz, DOOM's own tic rate, driven by the browser rather than by a loop
     * that never returns. Running faster would not draw more frames: DOOM would
     * spend the difference inside TryRunTics waiting for the next tic, which
     * without a real sleep is a busy wait on the thread the page needs.
     */
    emscripten_set_main_loop(doomgeneric_Tick, 35, 0);
}

/*
 * How many key events are waiting to be handed to DOOM. Exists so a test can
 * show that KEY1, KEY2 and KEY3 put nothing into the engine's input at all,
 * rather than asking the reader to take the switch above on trust. It is the
 * one property this target cannot afford to get wrong.
 */
EMSCRIPTEN_KEEPALIVE
int ss_doom_pending(void)
{
    return (int)((queue_write - queue_read + KEY_QUEUE_SIZE) % KEY_QUEUE_SIZE);
}

EMSCRIPTEN_KEEPALIVE
void ss_doom_stop(void)
{
    /*
     * Cancelling the loop is as far as this goes. DOOM has no shutdown that
     * leaves it startable again, so the page throws the module away rather than
     * restarting it.
     */
    emscripten_cancel_main_loop();
}

int main(void)
{
    /*
     * Nothing starts here. The WAD is 28.8MB and is fetched into the virtual
     * filesystem at runtime rather than baked into the binary, so the page
     * calls ss_doom_start once it has arrived.
     */
    return 0;
}
