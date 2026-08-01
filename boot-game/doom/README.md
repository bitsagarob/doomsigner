# DOOM

A `doomgeneric` port for the SeedSigner's 240x240 panel. **KEY1, KEY2, KEY3**
hands off to the wallet, exactly as the Python games do.

## Layout

| File | Needs a Pi | Purpose |
| --- | --- | --- |
| `src/ss_video.c` | no | Scales 320x200 XRGB to 240x240 RGB565, letterboxed, and packs it big endian for the wire |
| `src/ss_unlock.c` | no | The unlock sequence, mirroring `bootgame/unlock.py` |
| `src/ss_st7789_init.h` | no | The panel init sequence, as data so it can be diffed against SeedSigner's driver |
| `src/ss_pins.h` | no | Pin map, BCM numbering |
| `src/ss_gpio.c` | **yes** | BCM2835 GPIO via `/dev/gpiomem` |
| `src/ss_display.c` | **yes** | ST7789 over `/dev/spidev0.0`, or raw frames to an fd |
| `src/ss_input.c` | **yes** | Edge-detected buttons, or keys from stdin |
| `src/dg_seedsigner.c` | **yes** | Device target |
| `src/dg_headless.c` | no | Test target: dumps frames, scripted input, virtual clock |

## Building and testing

```sh
./fetch-wad.sh
make test     # unit tests for the scaler, wire packing and the unlock
make check    # the device target compiles
make          # the headless target
make tools    # ss-convert, used by the pixel format conformance test
```

The Python suite in `../tests/test_doom_port.py` carries the conformance tests:
the init sequence and control pins are diffed against SeedSigner's own
`ST7789.py`, and the C unlock sequence against `bootgame/unlock.py`. Those tests
skip without a SeedSigner checkout; point `SEEDSIGNER_APP` at one to run them.

## Running it without hardware

Both backends can be swapped at runtime, so the **device binary itself** runs on
a development machine:

```sh
SS_DISPLAY=fd SS_INPUT=stdin ./build/doom-seedsigner -iwad wad/freedoom1.wad > frames.rgb565
```

That exercises everything except the SPI and GPIO register writes. Frames come
out as raw 240x240 RGB565, 115200 bytes each. `SS_DISPLAY=fd` is also the
fallback if the panel stays black on real hardware: it isolates whether the
problem is the SPI code or something upstream of it.

## Why it is built this way

`doomgeneric` stays at its native 320x200 and we scale ourselves rather than
setting `DOOMGENERIC_RESX/RESY` to 240, which keeps the aspect ratio under our
control instead of relying on the engine's scaler for a non-integer ratio.

The display driver is transcribed from SeedSigner's `ST7789.py` because that is
what actually drives this panel today. Two things about it are easy to get
wrong and were verified rather than assumed: the init sequence (diffed against
their source by a test) and the wire byte order, which is big endian. Their
Python reaches it via `Image.convert("BGR;16")` followed by `array.byteswap()`;
`ss_pack_wire` does the same, and a test compares the two byte for byte.

Eight buttons is fewer than DOOM expects, so the three side buttons drive the
game *and* feed the unlock detector. A stray press is harmless, since only the
exact sequence unlocks.

## Not yet done

The buildroot external package that builds this into the image. And none of the
SPI or GPIO register access has run on real hardware yet.

## Note

Freedoom is used rather than a retail WAD because it is freely redistributable.
It is fetched rather than committed, being nearly 30MB, and the image boots
entirely into RAM so that size is worth watching on first boot.
