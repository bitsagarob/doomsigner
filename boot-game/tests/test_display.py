import pytest
from PIL import Image

from bootgame.catalog import available_games
from bootgame.display import SELECTED, render_menu
from bootgame.keys import Key
from bootgame.menu import Menu

CANVAS = 240


@pytest.fixture
def canvas():
    return Image.new("RGB", (CANVAS, CANVAS))


@pytest.fixture
def menu():
    return Menu(available_games(exists=lambda path: True))


def test_render_menu_draws_something(canvas, menu):
    render_menu(canvas, menu)

    assert canvas.getbbox() is not None


def test_the_highlighted_entry_uses_the_selected_colour(canvas, menu):
    render_menu(canvas, menu)

    # Text is anti-aliased against the background, so the exact colour may not
    # survive. Nearest match within a small tolerance is the real assertion.
    nearest = min(
        (colour for _, colour in canvas.getcolors()),
        key=lambda colour: sum(abs(a - b) for a, b in zip(colour, SELECTED)),
    )
    assert sum(abs(a - b) for a, b in zip(nearest, SELECTED)) < 30


def test_moving_the_highlight_changes_the_frame(canvas, menu):
    render_menu(canvas, menu)
    before = canvas.tobytes()

    menu.move(Key.DOWN)
    render_menu(canvas, menu)

    assert canvas.tobytes() != before
