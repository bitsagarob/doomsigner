from random import Random

import pytest

from bootgame.game import SnakeGame
from bootgame.keys import Key


@pytest.fixture
def game():
    return SnakeGame(grid_width=10, grid_height=10, rng=Random(0))


def test_opens_with_a_length_three_snake_heading_right(game):
    assert len(game.snake) == 3
    assert game.direction == (1, 0)
    assert game.score == 0
    assert not game.game_over


def test_food_never_spawns_on_the_snake():
    # Many seeds, because a single one proves nothing about the exclusion.
    for seed in range(200):
        game = SnakeGame(grid_width=6, grid_height=6, rng=Random(seed))
        assert game.food not in game.snake


def test_tick_advances_the_head_and_keeps_the_length(game):
    game.food = None
    head_x, head_y = game.snake[0]

    game.tick()

    assert game.snake[0] == (head_x + 1, head_y)
    assert len(game.snake) == 3


def test_turn_changes_direction(game):
    game.turn(Key.UP)
    assert game.direction == (0, -1)


def test_turn_ignores_a_reversal_onto_its_own_neck(game):
    game.turn(Key.LEFT)
    assert game.direction == (1, 0)


def test_turn_ignores_non_directional_keys(game):
    game.turn(Key.KEY1)
    assert game.direction == (1, 0)


def test_running_into_a_wall_ends_the_game(game):
    game.food = None
    for _ in range(game.grid_width):
        game.tick()

    assert game.game_over


def test_a_finished_game_stops_advancing(game):
    game.game_over = True
    before = list(game.snake)

    game.tick()

    assert game.snake == before


def test_eating_food_grows_the_snake_and_scores(game):
    head_x, head_y = game.snake[0]
    game.food = (head_x + 1, head_y)

    game.tick()

    assert game.score == 1
    assert len(game.snake) == 4
    assert not game.game_over


def test_the_vacating_tail_cell_is_not_a_collision():
    # Curling onto the cell the tail is leaving this same tick is legal.
    game = SnakeGame(grid_width=10, grid_height=10, rng=Random(0))
    game.food = None
    game.snake = [(2, 2), (2, 1), (1, 1), (1, 2)]
    game.direction = (0, 1)

    game.tick()

    assert not game.game_over
    assert game.snake[0] == (2, 3)


def test_biting_its_own_body_ends_the_game():
    game = SnakeGame(grid_width=10, grid_height=10, rng=Random(0))
    game.food = None
    game.snake = [(2, 2), (3, 2), (3, 3), (2, 3), (1, 3), (1, 2)]
    # (2, 3) is mid-body, not the tail, so it is still occupied after this tick.
    game.direction = (0, 1)

    game.tick()

    assert game.game_over


def test_reset_restores_the_opening_position(game):
    game.tick()
    game.score = 7
    game.game_over = True

    game.reset()

    assert len(game.snake) == 3
    assert game.score == 0
    assert not game.game_over


def test_a_full_board_leaves_no_food():
    game = SnakeGame(grid_width=2, grid_height=2, rng=Random(0))
    game.snake = [(0, 0), (1, 0), (0, 1), (1, 1)]

    assert game._place_food() is None
