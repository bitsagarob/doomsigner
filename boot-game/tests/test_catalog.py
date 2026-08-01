import pytest

from bootgame.catalog import DOOM, DOOM_BINARY, SNAKE, Game, available_games


def test_only_builtin_games_when_nothing_external_is_installed():
    assert available_games(exists=lambda path: False) == [SNAKE]


def test_an_external_game_appears_once_its_binary_is_present():
    games = available_games(exists=lambda path: path == DOOM_BINARY)

    assert [game.name for game in games] == ["SNAKE", "DOOM"]


def test_a_builtin_game_names_a_module_and_no_binary():
    assert SNAKE.module == "bootgame.games.snake"
    assert SNAKE.binary is None
    assert not SNAKE.is_external


def test_an_external_game_names_a_binary_and_no_module():
    assert DOOM.binary == DOOM_BINARY
    assert DOOM.module is None
    assert DOOM.is_external


def test_a_game_must_be_one_or_the_other():
    with pytest.raises(ValueError):
        Game("BOTH", module="x", binary="/y")

    with pytest.raises(ValueError):
        Game("NEITHER")


def test_every_registered_builtin_module_actually_imports():
    # Games are imported lazily, so a typo in the catalog would otherwise only
    # surface on the device, at the moment someone picks that game.
    import importlib

    for game in (SNAKE,):
        assert hasattr(importlib.import_module(game.module), "play")
