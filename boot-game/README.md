# boot-game

The device boots into Snake. Press **KEY1, KEY2, KEY3** and it hands off to
SeedSigner.

## How it hooks in

`opt/rootfs-overlay/start.sh` is the last link in the boot chain. Upstream it
runs the wallet directly; here it runs this package instead, which runs the
wallet when the unlock sequence is entered:

```sh
PYTHONPATH=/usr/local/bootgame /usr/bin/python3 -m bootgame.boot &
```

That is the entire change to SeedSigner OS: one line. The wallet application
itself is untouched and is still cloned from upstream at build time.

The handoff is an `os.execv`, so this process is *replaced* by SeedSigner rather
than backgrounded. No game code remains in memory while the signing application
is handling keys. If the game raises for any reason, SeedSigner is launched
anyway: a broken easter egg must never stand between someone and their device.

## Layout

| Module | Needs a Pi | Purpose |
| --- | --- | --- |
| `keys.py` | no | Symbolic button names |
| `game.py` | no | Snake as a pure state machine |
| `unlock.py` | no | The unlock sequence detector |
| `display.py` | no (Pillow only) | Draws a frame onto a PIL canvas |
| `input.py` | **yes** | Maps GPIO channels onto `Key` |
| `boot.py` | **yes** | Game loop and the handoff |

SeedSigner's button module imports `RPi.GPIO` at module scope, so anything
importing it cannot even load on a development machine. Keeping the game logic
free of that import is what makes it testable off-device, and it means only two
modules need real hardware or the emulator.

## Tests

Upstream configures no formatter or linter, so none is applied here. Its
coverage config omits the hardware modules, and the same split is used here:
the pure modules are tested, the two hardware-bound ones are not.

```sh
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/w -w /w \
  -e PYTHONPATH=/w/src -e HOME=/tmp python:3.12-slim \
  sh -c "pip install -q pytest pillow && python -m pytest -q"
```

## Browser harness

`web/` runs the real modules under Pyodide, so the game can be played and the
unlock exercised without a Pi. Pyodide ships Pillow, so `display.py` renders in
the browser too and the output is pixel-identical to the device.

```sh
python3 -m http.server 8899 --directory boot-game
# then open http://127.0.0.1:8899/web/
```

Arrow keys steer, KEY1/KEY2/KEY3 (or `1`, `2`, `3`) unlock.

`web/session.py` is the harness equivalent of `boot.py`, because `boot.py` and
`input.py` import RPi.GPIO and SeedSigner and cannot load under Pyodide. So the
harness covers the game, the unlock and the rendering, but *not* the button
polling loop or the `execv` handoff. Those are only exercised on real hardware.

## Building an image

`stage.sh` copies the runtime modules into the rootfs overlay. Tests and
packaging stay here and never ship to the device.

```sh
./boot-game/stage.sh
export BOARD_TYPE=pi0
SS_ARGS="--$BOARD_TYPE --app-commit-id=1fb2956322ea978428a6a96b955baa93e965c877" \
  docker compose up --force-recreate --build
```

Pinning the app commit keeps the emulator and the image on the same SeedSigner
build, so the game cannot work in one and break in the other.

## Note

An image built from this branch will not match the published SeedSigner
reproducible build hashes. It is a toy. Do not put a real seed on it.
