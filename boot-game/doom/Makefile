# Builds the headless target, for testing the port without a Raspberry Pi.
# The device target is built by buildroot, not here.

DG ?= $(HOME)/apps/doomgeneric-src/doomgeneric
OUT ?= build

# Upstream's explicit source list, which deliberately omits the SDL sound and
# music backends. Their platform entry point is replaced by ours.
DOOM_UNITS = dummy am_map doomdef doomstat dstrings d_event d_items d_iwad \
             d_loop d_main d_mode d_net f_finale f_wipe g_game hu_lib hu_stuff \
             info i_cdmus i_endoom i_joystick i_scale i_sound i_system i_timer \
             memio m_argv m_bbox m_cheat m_config m_controls m_fixed m_menu \
             m_misc m_random p_ceilng p_doors p_enemy p_floor p_inter p_lights \
             p_map p_maputl p_mobj p_plats p_pspr p_saveg p_setup p_sight \
             p_spec p_switch p_telept p_tick p_user r_bsp r_data r_draw r_main \
             r_plane r_segs r_sky r_things sha1 sounds statdump st_lib st_stuff \
             s_sound tables v_video wi_stuff w_checksum w_file w_main w_wad \
             z_zone w_file_stdc i_input i_video doomgeneric

DOOM_SRCS := $(addprefix $(DG)/, $(addsuffix .c, $(DOOM_UNITS)))
OUR_SRCS := src/ss_video.c src/ss_unlock.c src/dg_headless.c

CFLAGS += -std=gnu99 -O2 -I$(DG) -Isrc \
          -DNORMALUNIX -DLINUX -D_DEFAULT_SOURCE \
          -DDOOMGENERIC_RESX=320 -DDOOMGENERIC_RESY=200 \
          -Wno-implicit-function-declaration
LDLIBS += -lm

$(OUT)/doom-headless: $(DOOM_SRCS) $(OUR_SRCS)
	@mkdir -p $(OUT)
	$(CC) $(CFLAGS) -o $@ $^ $(LDLIBS)

clean:
	rm -rf $(OUT)

.PHONY: clean

$(OUT)/test-ss: src/ss_video.c src/ss_unlock.c tests/test_ss.c
	@mkdir -p $(OUT)
	$(CC) -std=gnu99 -O2 -Isrc -Wall -Wextra -o $@ $^ -lm

test: $(OUT)/test-ss
	./$(OUT)/test-ss

.PHONY: test
