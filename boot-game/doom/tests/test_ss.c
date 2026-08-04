/*
 * Tests for the parts of the DOOM port that are ours: the scaler and the
 * unlock sequence. Neither needs a Raspberry Pi, so both are tested here.
 */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ss_unlock.h"
#include "ss_video.h"

#define KEY1 0xE1
#define KEY2 0xE2
#define KEY3 0xE3

static int checks = 0;
#define CHECK(cond) do { checks++; if (!(cond)) { \
    fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); exit(1); } } while (0)

static void test_unlock_completes(void)
{
    static const int sequence[] = { KEY1, KEY2, KEY3 };
    ss_unlock_t unlock;
    ss_unlock_init(&unlock, sequence, 3);

    CHECK(ss_unlock_feed(&unlock, KEY1) == 0);
    CHECK(ss_unlock_feed(&unlock, KEY2) == 0);
    CHECK(ss_unlock_feed(&unlock, KEY3) == 1);
}

static void test_wrong_press_resets(void)
{
    static const int sequence[] = { KEY1, KEY2, KEY3 };
    ss_unlock_t unlock;
    ss_unlock_init(&unlock, sequence, 3);

    ss_unlock_feed(&unlock, KEY1);
    ss_unlock_feed(&unlock, KEY3);
    CHECK(unlock.progress == 0);
    CHECK(ss_unlock_feed(&unlock, KEY2) == 0);
}

static void test_wrong_press_may_open_a_new_attempt(void)
{
    /* Same rule as the Python implementation. */
    static const int sequence[] = { KEY1, KEY2, KEY1 };
    ss_unlock_t unlock;
    ss_unlock_init(&unlock, sequence, 3);

    ss_unlock_feed(&unlock, KEY1);
    ss_unlock_feed(&unlock, KEY1);
    CHECK(unlock.progress == 1);
    CHECK(ss_unlock_feed(&unlock, KEY2) == 0);
    CHECK(ss_unlock_feed(&unlock, KEY1) == 1);
}

static void test_it_rearms_after_unlocking(void)
{
    static const int sequence[] = { KEY1 };
    ss_unlock_t unlock;
    ss_unlock_init(&unlock, sequence, 1);

    CHECK(ss_unlock_feed(&unlock, KEY1) == 1);
    CHECK(unlock.progress == 0);
    CHECK(ss_unlock_feed(&unlock, KEY1) == 1);
}

static void test_scale_fills_the_panel(void)
{
    static uint32_t src[320 * 200];
    static uint16_t dst[SS_PANEL_W * SS_PANEL_H];

    for (int i = 0; i < 320 * 200; i++) {
        src[i] = 0x00FFFFFF; /* solid white */
    }
    ss_scale_to_565(src, 320, 200, dst);

    /* Every pixel of the panel, not most of them. A solid source has to come out
       a solid panel: bars anywhere would mean the scale stopped short of an edge,
       which is what this used to assert and what a 4:3 panel should never do to
       artwork drawn for a 4:3 screen. Corners and edges as well as the middle,
       because an off-by-one in either axis shows up there first. */
    for (int i = 0; i < SS_PANEL_W * SS_PANEL_H; i++) {
        CHECK(dst[i] == 0xFFFF);
    }
    CHECK(dst[0] == 0xFFFF);
    CHECK(dst[SS_PANEL_W - 1] == 0xFFFF);
    CHECK(dst[(size_t)(SS_PANEL_H - 1) * SS_PANEL_W] == 0xFFFF);
    CHECK(dst[(size_t)SS_PANEL_H * SS_PANEL_W - 1] == 0xFFFF);
}

static void test_scale_converts_colour(void)
{
    static uint32_t src[4];
    static uint16_t dst[SS_PANEL_W * SS_PANEL_H];

    for (int i = 0; i < 4; i++) {
        src[i] = 0x00FF0000; /* pure red */
    }
    ss_scale_to_565(src, 2, 2, dst);

    CHECK(dst[(size_t)120 * SS_PANEL_W + 120] == 0xF800);
}

static void test_scale_survives_a_degenerate_source(void)
{
    static uint16_t dst[SS_PANEL_W * SS_PANEL_H];

    ss_scale_to_565(NULL, 0, 0, dst);
    CHECK(dst[0] == 0x0000);
}

static void test_wire_packing_is_big_endian(void)
{
    static uint16_t frame[SS_PANEL_W * SS_PANEL_H];
    static uint8_t wire[SS_PANEL_W * SS_PANEL_H * 2];

    frame[0] = 0xA279;
    ss_pack_wire(frame, wire);

    /* The ST7789 wants the high byte first, whatever the host's endianness. */
    CHECK(wire[0] == 0xA2);
    CHECK(wire[1] == 0x79);
}

int main(void)
{
    test_unlock_completes();
    test_wrong_press_resets();
    test_wrong_press_may_open_a_new_attempt();
    test_it_rearms_after_unlocking();
    test_scale_fills_the_panel();
    test_scale_converts_colour();
    test_scale_survives_a_degenerate_source();
    test_wire_packing_is_big_endian();

    printf("%d checks passed\n", checks);
    return 0;
}
