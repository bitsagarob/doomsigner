from bootgame.catalog import DOOM_BINARY, SNAKE, available_games


def test_only_the_builtin_game_when_nothing_else_is_installed():
    games = available_games(exists=lambda path: False)

    assert games == [SNAKE]


def test_an_external_game_appears_once_its_binary_is_present():
    games = available_games(exists=lambda path: path == DOOM_BINARY)

    assert [game.name for game in games] == ["SNAKE", "DOOM"]


def test_the_builtin_game_needs_no_binary():
    assert SNAKE.is_builtin
    assert SNAKE.binary is None


def test_an_external_game_is_not_builtin():
    doom = available_games(exists=lambda path: True)[1]

    assert not doom.is_builtin
    assert doom.binary == DOOM_BINARY
