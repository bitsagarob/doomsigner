"""
Checks on the DOOM port that can be made without a Raspberry Pi.

The display driver is transcribed from SeedSigner's own ST7789.py. That is the
only reason to believe it works, so the transcription is verified here rather
than trusted, and will fail if either side drifts.
"""

import os
import re
from pathlib import Path

import pytest

BOOT_GAME = Path(__file__).resolve().parents[1]
DOOM_SRC = BOOT_GAME / "doom/src"
INIT_HEADER = DOOM_SRC / "ss_st7789_init.h"
PINS_HEADER = DOOM_SRC / "ss_pins.h"

# A SeedSigner checkout, which is not part of this repo, so these tests skip
# without one. Override the location with SEEDSIGNER_APP.
SEEDSIGNER_APP = Path(
    os.environ.get("SEEDSIGNER_APP", BOOT_GAME.parent.parent / "seedsigner-app")
)
SEEDSIGNER_DRIVER = SEEDSIGNER_APP / "src/seedsigner/hardware/displays/ST7789.py"

needs_driver = pytest.mark.skipif(
    not SEEDSIGNER_DRIVER.exists(),
    reason=f"needs a SeedSigner checkout at {SEEDSIGNER_DRIVER}",
)


def parse_python_init():
    """Pull the (command, [data]) sequence out of SeedSigner's init()."""
    source = SEEDSIGNER_DRIVER.read_text()
    body = source[source.index("def init(self):"):source.index("def reset(self):")]

    # That file has commented-out alternatives on the same line as live calls,
    # so comments have to go before matching or they are read as real writes.
    body = re.sub(r"#.*", "", body)

    sequence = []
    for call, value in re.findall(r"self\.(command|data)\(0x([0-9A-Fa-f]{2})\)", body):
        if call == "command":
            sequence.append((int(value, 16), []))
        else:
            sequence[-1][1].append(int(value, 16))

    return sequence


def parse_c_init():
    """Pull the same sequence out of our C table."""
    source = INIT_HEADER.read_text()
    body = source[source.index("SS_ST7789_INIT[]"):]

    sequence = []
    for command, length, data in re.findall(
        r"\{\s*0x([0-9A-Fa-f]{2}),\s*(\d+),\s*\{([^}]*)\}\s*\}", body
    ):
        values = [int(v, 16) for v in re.findall(r"0x([0-9A-Fa-f]{2})", data)]
        sequence.append((int(command, 16), values[: int(length)]))

    return sequence


@needs_driver
def test_the_init_sequence_matches_seedsigners_driver():
    assert parse_c_init() == parse_python_init()


@needs_driver
def test_the_control_pins_match_seedsigners_driver():
    # SeedSigner uses RPi.GPIO BOARD numbering; ours are BCM. Same pins.
    board_to_bcm = {22: 25, 13: 27, 18: 24}
    source = SEEDSIGNER_DRIVER.read_text()

    for name, attribute in (("SS_PIN_DC", "_dc"), ("SS_PIN_RST", "_rst"), ("SS_PIN_BL", "_bl")):
        found = re.search(rf"self\.{attribute}\s*=\s*(\d+)", source)
        assert found, (
            f"{attribute} is no longer a literal pin number in ST7789.py. Some forks "
            f"take pins from a configuration map instead, in which case our hardcoded "
            f"{name} needs checking against whatever that map holds for this board."
        )

        board = int(found.group(1))
        ours = int(re.search(rf"#define {name}\s+(\d+)", PINS_HEADER.read_text()).group(1))
        assert ours == board_to_bcm[board], f"{name}: BOARD {board} should be BCM {board_to_bcm[board]}"


def test_the_init_sequence_ends_by_turning_the_display_on():
    commands = [command for command, _ in parse_c_init()]

    assert commands[-1] == 0x29, "DISPON must be last"
    assert 0x11 in commands, "SLPOUT must be present or the panel stays asleep"
    assert 0x3A in commands, "COLMOD must be set or the pixel format is undefined"


def test_the_unlock_sequence_matches_the_python_one():
    from bootgame.unlock import DEFAULT_SEQUENCE

    device = (DOOM_SRC / "dg_seedsigner.c").read_text()
    names = re.search(r"UNLOCK_SEQUENCE\[\]\s*=\s*\{([^}]*)\}", device).group(1)

    # The C constants are SS_KEY1 etc; the Python enum members are KEY1 etc.
    c_names = [n.strip().removeprefix("SS_") for n in names.split(",") if n.strip()]

    assert c_names == [key.name for key in DEFAULT_SEQUENCE]
