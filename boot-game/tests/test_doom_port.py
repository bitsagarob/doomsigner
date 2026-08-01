"""
Checks on the DOOM port that need no Raspberry Pi.

The panel configuration is generated from SeedSigner's own driver and pin map
rather than transcribed, so what is tested here is the generator: that it agrees
with the values we believe are correct, that two independent SeedSigner
checkouts produce the same answer, and that it refuses configurations nobody has
verified instead of guessing.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT_GAME = Path(__file__).resolve().parents[1]
DOOM = BOOT_GAME / "doom"
GENERATOR = DOOM / "tools/gen_panel_config.py"

# SeedSigner checkouts, which are not part of this repo, so these tests skip
# without one. Override with SEEDSIGNER_APP and SEEDSIGNER_FORK.
SEEDSIGNER_APP = Path(os.environ.get("SEEDSIGNER_APP", BOOT_GAME.parent.parent / "seedsigner-app"))
SEEDSIGNER_FORK = Path(os.environ.get("SEEDSIGNER_FORK", BOOT_GAME.parent.parent / "shieldsigner-app"))

def _has_io_config(checkout):
    return (checkout / "src/seedsigner/hardware/io_config.json").is_file()


# Which checkout is upstream and which is a fork varies by what this repo is
# based on, so identify them by capability rather than by name.
WITH_IO_CONFIG = next(
    (c for c in (SEEDSIGNER_APP, SEEDSIGNER_FORK) if c.exists() and _has_io_config(c)), None
)
WITHOUT_IO_CONFIG = next(
    (c for c in (SEEDSIGNER_APP, SEEDSIGNER_FORK) if c.exists() and not _has_io_config(c)), None
)

needs_app = pytest.mark.skipif(not SEEDSIGNER_APP.exists(), reason=f"needs {SEEDSIGNER_APP}")
needs_both = pytest.mark.skipif(
    not (WITH_IO_CONFIG and WITHOUT_IO_CONFIG),
    reason="needs one checkout with io_config.json and one without",
)
needs_io_config = pytest.mark.skipif(
    WITH_IO_CONFIG is None, reason="needs a checkout shipping io_config.json"
)

# Verified by hand against ST7789.py, cross-checked against the emulator's
# constants, and again against io_config.json. Three independent sources.
EXPECTED_PINS = {
    "SS_PIN_DC": 25, "SS_PIN_RST": 27, "SS_PIN_BL": 24,
    "SS_PIN_UP": 6, "SS_PIN_DOWN": 19, "SS_PIN_LEFT": 5, "SS_PIN_RIGHT": 26,
    "SS_PIN_PRESS": 13, "SS_PIN_KEY1": 21, "SS_PIN_KEY2": 20, "SS_PIN_KEY3": 16,
}


def generate(app, tmp_path, profile=None, display=None):
    out = tmp_path / "ss_panel_config.h"
    command = [sys.executable, str(GENERATOR), "--app", str(app), "--out", str(out)]
    if profile:
        command += ["--profile", profile]
    if display:
        command += ["--display", display]

    result = subprocess.run(command, capture_output=True, text=True)
    return result, (out.read_text() if out.exists() else "")


def defines(header):
    return {name: int(value) for name, value in re.findall(r"#define (SS_PIN_\w+|SS_PANEL_[WH])\s+(\d+)", header)}


@needs_app
def test_it_generates_the_pins_we_verified(tmp_path):
    result, header = generate(SEEDSIGNER_APP, tmp_path)

    assert result.returncode == 0, result.stderr
    found = defines(header)
    for name, value in EXPECTED_PINS.items():
        assert found[name] == value, f"{name} generated as {found.get(name)}, expected {value}"


@needs_app
def test_it_generates_the_right_geometry(tmp_path):
    _, header = generate(SEEDSIGNER_APP, tmp_path)
    found = defines(header)

    assert (found["SS_PANEL_W"], found["SS_PANEL_H"]) == (240, 240)


@needs_app
def test_the_init_sequence_ends_by_turning_the_display_on(tmp_path):
    _, header = generate(SEEDSIGNER_APP, tmp_path)
    commands = [int(c, 16) for c in re.findall(r"\{ 0x([0-9A-F]{2}), \d+,", header)]

    assert commands[-1] == 0x29, "DISPON must be last"
    assert 0x11 in commands, "SLPOUT must be present or the panel stays asleep"
    assert 0x3A in commands, "COLMOD must be set or the pixel format is undefined"


@needs_both
def test_both_checkouts_agree(tmp_path):
    # One parses ST7789.py literals, the other reads io_config.json. They
    # describe the same hardware, so they must produce the same header.
    _, literals = generate(WITHOUT_IO_CONFIG, tmp_path / "a")
    _, mapped = generate(WITH_IO_CONFIG, tmp_path / "b", profile="RPI_40")

    assert defines(literals) == defines(mapped)


@needs_app
def test_it_refuses_a_display_nobody_has_verified(tmp_path):
    result, _ = generate(SEEDSIGNER_APP, tmp_path, display="ili9486_480x320")

    assert result.returncode != 0
    assert "has not been verified" in result.stderr


@needs_io_config
def test_it_refuses_an_unknown_hardware_profile(tmp_path):
    result, _ = generate(WITH_IO_CONFIG, tmp_path, profile="NOT_A_BOARD")

    assert result.returncode != 0
    assert "unknown profile" in result.stderr


def test_the_unlock_sequence_matches_the_python_one():
    from bootgame.unlock import DEFAULT_SEQUENCE

    device = (DOOM / "src/dg_seedsigner.c").read_text()
    names = re.search(r"UNLOCK_SEQUENCE\[\]\s*=\s*\{([^}]*)\}", device).group(1)

    # The C constants are SS_KEY1 etc; the Python enum members are KEY1 etc.
    c_names = [n.strip().removeprefix("SS_") for n in names.split(",") if n.strip()]

    assert c_names == [key.name for key in DEFAULT_SEQUENCE]
