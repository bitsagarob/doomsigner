#!/bin/sh
# Assemble a device-shaped tree and run the boot game under the emulator.
#
# Expects, as siblings of the seedsigner-os checkout:
#   ../seedsigner-app       upstream wallet, pinned
#   ../seedsigner-emulator  desktop emulator overlay
set -eu

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
apps=$(cd "$repo/.." && pwd)
stage="$here/.stage"

rm -rf "$stage"
mkdir -p "$stage/opt" "$stage/usr/local/bootgame"

cp -r "$apps/seedsigner-app/src" "$stage/opt/src"
# The emulator is an overlay: it replaces the display, buttons and camera.
cp -r "$apps/seedsigner-emulator/seedsigner/." "$stage/opt/src/seedsigner/"
cp -r "$here/../src/bootgame" "$stage/usr/local/bootgame/bootgame"

# The emulator lags upstream: its Renderer replacement predates the
# is_screenshot_generator property that current dev expects. Rather than fork
# the emulator, add it back here.
if ! grep -q "is_screenshot_generator" "$stage/opt/src/seedsigner/gui/renderer.py"; then
  cat >> "$stage/opt/src/seedsigner/gui/renderer.py" <<'COMPAT'


    @property
    def is_screenshot_generator(self) -> bool:
        return False
COMPAT
  echo "applied is_screenshot_generator compat patch"
fi

# The emulator sets its window icon from a worker thread, which Tk rejects
# ("not a photo image"). Cosmetic, but it kills the thread and the window never
# appears, so drop the call.
sed -i '/iconphoto/d' "$stage/opt/src/seedsigner/emulator/desktopDisplay.py"

# The controller eagerly imports the camera stack. There is no camera here and
# picamera is Pi-only, so satisfy the import with a stub.
mkdir -p "$stage/opt/src/picamera"
cat > "$stage/opt/src/picamera/__init__.py" <<'STUB'
"""Stub: the emulator has no camera, but the controller imports this eagerly."""


class PiCamera:
    pass
STUB
cat > "$stage/opt/src/picamera/array.py" <<'STUB'
"""Stub, see __init__.py."""


class PiRGBArray:
    pass
STUB

echo "staged a device-shaped tree in ${stage#"$repo"/}"
