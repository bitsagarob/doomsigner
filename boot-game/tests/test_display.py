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


def test_render_menu_draws_something(canvas):
    from bootgame.catalog import available_games
    from bootgame.display import render_menu
    from bootgame.menu import Menu

    render_menu(canvas, Menu(available_games(exists=lambda path: True)))

    assert canvas.getbbox() is not None


def test_the_highlighted_entry_uses_the_selected_colour(canvas):
    from bootgame.catalog import available_games
    from bootgame.display import SELECTED, render_menu
    from bootgame.menu import Menu

    render_menu(canvas, Menu(available_games(exists=lambda path: True)))

    # Text is anti-aliased against the background, so the exact colour may not
    # survive. Nearest match within a small tolerance is the real assertion.
    nearest = min(
        (colour for _, colour in canvas.getcolors()),
        key=lambda colour: sum(abs(a - b) for a, b in zip(colour, SELECTED)),
    )
    assert sum(abs(a - b) for a, b in zip(nearest, SELECTED)) < 30


def test_moving_the_highlight_changes_the_frame(canvas):
    from bootgame.catalog import available_games
    from bootgame.display import render_menu
    from bootgame.keys import Key
    from bootgame.menu import Menu

    menu = Menu(available_games(exists=lambda path: True))
    render_menu(canvas, menu)
    before = canvas.tobytes()

    menu.move(Key.DOWN)
    render_menu(canvas, menu)

    assert canvas.tobytes() != before
