# DOOM

A `doomgeneric` port targeting the SeedSigner's 240x240 panel, with the same
unlock sequence as the Python games: **KEY1, KEY2, KEY3** hands off to the
wallet.

## What is here

| File | Needs a Pi | Purpose |
| --- | --- | --- |
| `src/ss_video.c` | no | Scales DOOM's 320x200 XRGB frame to 240x240 RGB565, letterboxed |
| `src/ss_unlock.c` | no | The unlock sequence, mirroring `bootgame/unlock.py` exactly |
| `src/dg_headless.c` | no | Test target: dumps frames, scripted input, virtual clock |
| `tests/test_ss.c` | no | Tests for both shared modules |

The device target and its buildroot package are **not written yet**. See below.

## Running it here

```sh
./fetch-wad.sh
make            # builds build/doom-headless
make test       # 17 checks on the scaler and the unlock

SS_OUT_DIR=frames SS_MAX_FRAMES=700 SS_DUMP_EVERY=120 \
  ./build/doom-headless -iwad wad/freedoom1.wad
```

Frames land as PPM. This is how the port was verified without hardware: DOOM
renders, the scaler letterboxes correctly, and the scripted unlock fires.

`doomgeneric` stays at its native 320x200 and we scale ourselves, rather than
setting `DOOMGENERIC_RESX/RESY` to 240. That keeps aspect ratio under our
control and avoids relying on the engine's own scaler for a non-integer ratio.

## Still to do

The device target needs `DG_DrawFrame` to push RGB565 over SPI to the ST7789 and
`DG_GetKey` to read the GPIO buttons, plus a buildroot external package to build
it into the image. Neither can be tested anywhere but on the hardware.

## Note

Freedoom is used rather than a retail WAD because it is freely redistributable.
It is fetched rather than committed, being nearly 30MB.
