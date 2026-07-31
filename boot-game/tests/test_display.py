from random import Random

import pytest
from PIL import Image, ImageDraw

from bootgame.display import BACKGROUND, FOOD, SNAKE_HEAD, render
from bootgame.game import SnakeGame

CANVAS = 240


@pytest.fixture
def canvas():
    return Image.new("RGB", (CANVAS, CANVAS))


def test_render_fills_the_whole_canvas(canvas):
    game = SnakeGame(rng=Random(0))

    render(ImageDraw.Draw(canvas), game, CANVAS, CANVAS)

    assert canvas.getbbox() is not None


def test_the_head_is_drawn_in_the_head_colour(canvas):
    game = SnakeGame(grid_width=12, grid_height=12, rng=Random(0))
    game.food = None
    cell_size = CANVAS // 12

    render(ImageDraw.Draw(canvas), game, CANVAS, CANVAS)

    head_x, head_y = game.snake[0]
    pixel = canvas.getpixel(
        (head_x * cell_size + cell_size // 2, head_y * cell_size + cell_size // 2)
    )
    assert pixel == SNAKE_HEAD


def test_food_is_drawn_in_the_food_colour(canvas):
    game = SnakeGame(grid_width=12, grid_height=12, rng=Random(0))
    cell_size = CANVAS // 12

    render(ImageDraw.Draw(canvas), game, CANVAS, CANVAS)

    food_x, food_y = game.food
    pixel = canvas.getpixel(
        (food_x * cell_size + cell_size // 2, food_y * cell_size + cell_size // 2)
    )
    assert pixel == FOOD


def test_an_empty_board_is_all_background(canvas):
    game = SnakeGame(grid_width=12, grid_height=12, rng=Random(0))
    game.snake = []
    game.food = None

    render(ImageDraw.Draw(canvas), game, CANVAS, CANVAS)

    assert canvas.getcolors() == [(CANVAS * CANVAS, BACKGROUND)]


def test_it_renders_on_a_non_square_canvas():
    game = SnakeGame(rng=Random(0))
    image = Image.new("RGB", (320, 240))

    render(ImageDraw.Draw(image), game, 320, 240)

    assert image.getbbox() is not None
