"""
Wiring tests for the boot loop.

These exist because the emulator harness cannot be trusted to prove the handoff:
its Tk thread races under Xvfb and fails at random. The logic below is ours, so
it gets tested deterministically here instead.
"""

import pytest
from PIL import Image, ImageDraw

from bootgame import runner
from bootgame.catalog import DOOM, SNAKE
from bootgame.keys import Key
from bootgame.unlock import UnlockSequence


class HandedOff(Exception):
    """Stands in for os.execv, which never returns."""


class FakeRenderer:
    def __init__(self, size=240):
        self.canvas = Image.new("RGB", (size, size))
        self.draw = ImageDraw.Draw(self.canvas)
        self.canvas_width = size
        self.canvas_height = size
        self.shown = 0

    def show_image(self):
        self.shown += 1


class FakeReader:
    """Yields each scripted batch of presses once, then nothing."""

    def __init__(self, script):
        self.script = list(script)

    def presses(self):
        return iter(self.script.pop(0)) if self.script else iter(())


@pytest.fixture
def renderer():
    return FakeRenderer()


@pytest.fixture(autouse=True)
def no_sleeping(monkeypatch):
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)


@pytest.fixture(autouse=True)
def handoff_raises(monkeypatch):
    def fake_launch():
        raise HandedOff()

    monkeypatch.setattr(runner, "launch_seedsigner", fake_launch)


def test_the_unlock_sequence_hands_off_from_the_game(renderer):
    reader = FakeReader([[Key.KEY1], [Key.KEY2], [Key.KEY3]])

    with pytest.raises(HandedOff):
        runner.play_snake(renderer, reader, UnlockSequence())


def test_ordinary_play_does_not_hand_off(renderer):
    reader = FakeReader([[Key.UP], [Key.LEFT], [Key.KEY1], [Key.DOWN]])

    # No handoff, so the loop runs on; stop it once the script is exhausted.
    with pytest.raises(StopIteration):
        _run_until_script_exhausted(runner.play_snake, renderer, reader)


def test_the_unlock_sequence_hands_off_from_the_menu(renderer):
    reader = FakeReader([[Key.KEY1], [Key.KEY2], [Key.KEY3]])

    with pytest.raises(HandedOff):
        runner.choose_game(renderer, reader, UnlockSequence(), [SNAKE, DOOM])


def test_the_menu_returns_the_highlighted_entry(renderer):
    reader = FakeReader([[Key.PRESS]])

    chosen = runner.choose_game(renderer, reader, UnlockSequence(), [SNAKE, DOOM])

    assert chosen == SNAKE


def test_the_menu_moves_before_selecting(renderer):
    reader = FakeReader([[Key.DOWN], [Key.PRESS]])

    chosen = runner.choose_game(renderer, reader, UnlockSequence(), [SNAKE, DOOM])

    assert chosen == DOOM


def test_the_side_buttons_never_launch_a_game_from_the_menu(renderer):
    # Regression: KEY1 used to confirm the highlighted entry, so the first press
    # of the unlock sequence launched a game and the wallet became unreachable.
    reader = FakeReader([[Key.KEY1], [Key.KEY2]])

    with pytest.raises(StopIteration):
        _choose_until_script_exhausted(renderer, reader, [SNAKE, DOOM])


def _choose_until_script_exhausted(renderer, reader, games):
    original = reader.presses

    def presses():
        if not reader.script:
            raise StopIteration()
        return original()

    reader.presses = presses
    runner.choose_game(renderer, reader, UnlockSequence(), games)


def _run_until_script_exhausted(loop, renderer, reader):
    original = reader.presses

    def presses():
        if not reader.script:
            raise StopIteration()
        return original()

    reader.presses = presses
    loop(renderer, reader, UnlockSequence())


def test_the_game_renders_each_tick(renderer):
    reader = FakeReader([])
    monkey = runner.time

    ticks = {"count": 0}
    real_monotonic = monkey.monotonic

    def counting_monotonic():
        ticks["count"] += 1
        if ticks["count"] > 6:
            raise HandedOff()
        return real_monotonic()

    monkey.monotonic = counting_monotonic
    try:
        with pytest.raises(HandedOff):
            runner.play_snake(renderer, reader, UnlockSequence())
    finally:
        monkey.monotonic = real_monotonic

    assert renderer.shown > 0
