"""
The bits of SeedSigner we depend on.

Nothing here imports SeedSigner: its hardware modules pull in RPi.GPIO at module
scope. These read the source instead, which is enough to catch the kind of drift
that would break us, and lets CI run them against upstream `dev` as an early
warning without needing a Pi.

If one of these fails, the wallet has moved and our adapters need updating. That
is the point: better a red build than a black screen on a flashed card.
"""

import os
import re
from pathlib import Path

import pytest

BOOT_GAME = Path(__file__).resolve().parents[1]
SEEDSIGNER_APP = Path(
    os.environ.get("SEEDSIGNER_APP", BOOT_GAME.parent.parent / "seedsigner-app")
)
SRC = SEEDSIGNER_APP / "src"

needs_checkout = pytest.mark.skipif(
    not SRC.exists(), reason=f"needs a SeedSigner checkout at {SEEDSIGNER_APP}"
)


@needs_checkout
def test_the_entry_point_we_exec_still_exists():
    # bootgame/launch.py runs "python3 main.py" from /opt/src.
    assert (SRC / "main.py").is_file()


@needs_checkout
def test_the_button_constants_we_map_still_exist():
    # bootgame/input.py maps these names onto our Key enum.
    source = (SRC / "seedsigner/hardware/buttons.py").read_text()
    body = source[source.index("class HardwareButtonsConstants"):]

    for name in ("KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "KEY_PRESS", "KEY1", "KEY2", "KEY3"):
        assert re.search(rf"^\s+{name}\s*=", body, re.MULTILINE), f"{name} is gone"

    assert "ALL_KEYS" in body


@needs_checkout
def test_the_button_polling_method_we_call_still_exists():
    source = (SRC / "seedsigner/hardware/buttons.py").read_text()

    assert "def check_for_low(self" in source
    assert re.search(r"def check_for_low\(self,\s*key", source), "check_for_low lost its key argument"


@needs_checkout
def test_the_renderer_surface_we_use_still_exists():
    # bootgame/runner.py and the games draw through these.
    source = (SRC / "seedsigner/gui/renderer.py").read_text()

    for attribute in ("canvas", "draw", "canvas_width", "canvas_height"):
        assert re.search(rf"^\s+{attribute}\b", source, re.MULTILINE), f"Renderer.{attribute} is gone"

    assert "def configure_instance(cls" in source
    assert "def show_image(self" in source


@needs_checkout
def test_the_240x240_panel_still_uses_the_driver_we_transcribed():
    # If the factory switches 240x240 to a different driver, the DOOM init
    # sequence we transcribed is no longer the right one.
    source = (SRC / "seedsigner/hardware/displays/display_driver.py").read_text()

    assert "from seedsigner.hardware.displays.ST7789 import ST7789" in source, (
        "the 240x240 path no longer uses ST7789.py"
    )
