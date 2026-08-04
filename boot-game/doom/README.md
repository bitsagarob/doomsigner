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
| `src/dg_wasm.c` | no | Browser target: hands each frame to the page, driven by the browser's own loop |
| `web/doom-run.js` | no | The wrapper the simulator's page talks to |

## Building and testing

```sh
./fetch-wad.sh
make test     # unit tests for the scaler, wire packing and the unlock
make check    # the device target compiles
make          # the headless target
make tools    # ss-convert, used by the pixel format conformance test
make wasm     # the browser target; needs emscripten on PATH
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

## Running it in a browser

`make wasm` produces `build/doom.js`, `build/doom.wasm` and `build/doom-run.js`.
Serve all three from one directory, with the WAD, and the page has one thing to
talk to:

```js
DoomRun.start({ wadUrl: "freedoom1.wad", onFrame: paint });
DoomRun.key("up", true);   // up down left right select key1 key2 key3
DoomRun.stop();
await DoomRun.ready;
```

`onFrame` is handed the same 115200 bytes the panel is: 240x240 RGB565, big
endian, letterboxed, out of the same `ss_video.c` the device runs. The 28.8MB
WAD is fetched into emscripten's virtual filesystem rather than linked in, and
`doom.js` itself is only loaded once `start()` is called, so a visitor who never
plays never downloads the game.

`node tests/run_wasm_frames.js` runs that build headless and checks what comes
out of it: that the frames are the right size, that they change, and that KEY1,
KEY2 and KEY3 put nothing at all into DOOM's input queue. It writes PPMs in the
same format `dg_headless` writes, so frames from the two targets can be compared
with `cmp`.

The browser build has one fewer button than the device. KEY1, KEY2 and KEY3
spell the unlock and the page owns that, so here they drive nothing: there is no
path in the wasm from those three into DOOM at all. That leaves the stick and
one button, so `select` sends fire *and* use, since without use the first door
on E1M1 cannot be opened, and it starts in E1M1 rather than on the title screen,
since with no menu key there would be no way out of the attract loop.

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

The browser build blocks its tab for about a second on `start()`, reading the
WAD and then running DOOM's opening melt wipe, which lives inside a loop in
`D_Display` that we do not get to return from. Frames are drawn during it but
the page cannot paint them, so it reads as a pause and then a jump.

## Note

Freedoom is used rather than a retail WAD because it is freely redistributable.
It is fetched rather than committed, being nearly 30MB, and the image boots
entirely into RAM so that size is worth watching on first boot.
