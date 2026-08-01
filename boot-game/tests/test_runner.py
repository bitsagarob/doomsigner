"""
Wiring tests for the boot loop.

These exist because the emulator harness cannot be trusted to prove any of it:
its Tk thread races under Xvfb and fails at random. The logic here is ours, so
it is tested deterministically instead.
"""

import pytest

from bootgame import runner
from bootgame.catalog import DOOM, SNAKE
from bootgame.keys import Key
from bootgame.unlock import UnlockSequence
from conftest import FakeReader, HandedOff

GAMES = [SNAKE, DOOM]


@pytest.fixture(autouse=True)
def no_sleeping(monkeypatch):
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)


@pytest.fixture(autouse=True)
def handoff_raises(monkeypatch):
    monkeypatch.setattr(runner, "launch_seedsigner", lambda: (_ for _ in ()).throw(HandedOff()))


def test_the_unlock_sequence_hands_off_from_the_menu(renderer):
    reader = FakeReader([[Key.KEY1], [Key.KEY2], [Key.KEY3]])

    with pytest.raises(HandedOff):
        runner.choose_game(renderer, reader, UnlockSequence(), GAMES)


def test_the_menu_returns_the_highlighted_entry(renderer):
    chosen = runner.choose_game(renderer, FakeReader([[Key.PRESS]]), UnlockSequence(), GAMES)

    assert chosen == SNAKE


def test_the_menu_moves_before_selecting(renderer):
    reader = FakeReader([[Key.DOWN], [Key.PRESS]])

    chosen = runner.choose_game(renderer, reader, UnlockSequence(), GAMES)

    assert chosen == DOOM


def test_the_side_buttons_never_launch_a_game_from_the_menu(renderer):
    # Regression: KEY1 used to confirm the highlighted entry, so the first press
    # of the unlock sequence launched a game and the wallet became unreachable.
    reader = FakeReader([[Key.KEY1], [Key.KEY2]])

    with pytest.raises(StopIteration):
        runner.choose_game(renderer, reader, UnlockSequence(), GAMES)


def test_an_external_game_replaces_the_process(renderer, monkeypatch):
    launched = []
    monkeypatch.setattr(runner, "launch_external", launched.append)

    runner.play_game(DOOM, renderer, FakeReader([]), UnlockSequence())

    assert launched == [DOOM]


def test_a_builtin_game_is_imported_only_when_played(renderer, monkeypatch):
    imported = []

    class FakeModule:
        @staticmethod
        def play(renderer, reader, unlock):
            imported.append("played")

    monkeypatch.setattr(runner.importlib, "import_module", lambda name: imported.append(name) or FakeModule)

    runner.play_game(SNAKE, renderer, FakeReader([]), UnlockSequence())

    assert imported == ["bootgame.games.snake", "played"]


def test_a_broken_game_does_not_take_the_others_down(renderer, monkeypatch):
    # With more than one game installed, a game that raises sends the player
    # back to the chooser rather than bricking the device.
    monkeypatch.setattr(runner, "available_games", lambda: GAMES)
    monkeypatch.setattr(runner, "play_game", _raising(RuntimeError("boom")))

    visits = []

    def fake_choose(renderer, reader, unlock, games):
        visits.append(games)
        if len(visits) > 2:
            raise HandedOff()
        return SNAKE

    monkeypatch.setattr(runner, "choose_game", fake_choose)
    monkeypatch.setattr(runner, "ButtonReader", lambda: FakeReader([]), raising=False)

    with pytest.raises(HandedOff):
        _run_with_fake_renderer(runner, renderer, monkeypatch)

    assert len(visits) == 3


def _raising(error):
    def raise_it(*args, **kwargs):
        raise error

    return raise_it


def _run_with_fake_renderer(module, renderer, monkeypatch):
    """run() imports its renderer and reader lazily, so stub both out."""
    import sys
    import types

    fake_renderer_module = types.ModuleType("seedsigner.gui.renderer")

    class Renderer:
        @staticmethod
        def configure_instance():
            pass

        @staticmethod
        def get_instance():
            return renderer

    fake_renderer_module.Renderer = Renderer

    fake_input = types.ModuleType("bootgame.input")
    fake_input.ButtonReader = lambda: FakeReader([])

    monkeypatch.setitem(sys.modules, "seedsigner", types.ModuleType("seedsigner"))
    monkeypatch.setitem(sys.modules, "seedsigner.gui", types.ModuleType("seedsigner.gui"))
    monkeypatch.setitem(sys.modules, "seedsigner.gui.renderer", fake_renderer_module)
    monkeypatch.setitem(sys.modules, "bootgame.input", fake_input)

    module.run()
