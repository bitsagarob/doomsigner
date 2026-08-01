"""
Draws the game onto a PIL canvas.

Pillow is the only dependency, so rendering can be exercised off-device. The
canvas handed in is SeedSigner's own `Renderer.canvas`, which is what the
desktop emulator swaps out, so this works unchanged in both places.
"""

import logging
from typing import Tuple

from PIL import Image, ImageDraw

from bootgame.game import Cell, SnakeGame
from bootgame.menu import Menu

logger = logging.getLogger(__name__)

Colour = Tuple[int, int, int]

BACKGROUND: Colour = (0, 0, 0)
SNAKE_HEAD: Colour = (0, 255, 0)
SNAKE_BODY: Colour = (0, 160, 0)
FOOD: Colour = (255, 159, 10)
TEXT: Colour = (255, 255, 255)

SELECTED: Colour = (255, 159, 10)

# Leaves a hairline gap between cells so the body reads as segments.
CELL_INSET = 1

# Pillow's built-in font is 6px tall, which is unreadable on a 240px screen.
# Drawing small and upscaling with nearest neighbour gives legible, chunky text
# without needing a font file on the device.
TITLE_SCALE = 2
ENTRY_SCALE = 4


def render(draw: ImageDraw.ImageDraw, game: SnakeGame, width: int, height: int) -> None:
    """Render one frame. The board is centred and square, whatever the canvas."""
    draw.rectangle((0, 0, width, height), fill=BACKGROUND)

    cell_size = min(width // game.grid_width, height // game.grid_height)
    origin_x = (width - cell_size * game.grid_width) // 2
    origin_y = (height - cell_size * game.grid_height) // 2

    if game.food is not None:
        _draw_cell(draw, game.food, cell_size, origin_x, origin_y, FOOD)

    for index, segment in enumerate(game.snake):
        _draw_cell(
            draw,
            segment,
            cell_size,
            origin_x,
            origin_y,
            SNAKE_HEAD if index == 0 else SNAKE_BODY,
        )

    if game.game_over:
        _draw_centred_text(draw, "GAME OVER", width, height)


def _draw_cell(
    draw: ImageDraw.ImageDraw,
    cell: Cell,
    cell_size: int,
    origin_x: int,
    origin_y: int,
    colour: Colour,
) -> None:
    x, y = cell
    left = origin_x + x * cell_size
    top = origin_y + y * cell_size
    draw.rectangle(
        (left, top, left + cell_size - CELL_INSET, top + cell_size - CELL_INSET),
        fill=colour,
    )


def _draw_centred_text(draw: ImageDraw.ImageDraw, text: str, width: int, height: int) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text)
    draw.text(
        ((width - (right - left)) // 2, (height - (bottom - top)) // 2),
        text,
        fill=TEXT,
    )


def render_menu(canvas: Image.Image, menu: Menu) -> None:
    """Render the game chooser. Deliberately lists no route to the wallet."""
    width, height = canvas.size
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, height), fill=BACKGROUND)

    _paste_centred(canvas, "SELECT GAME", TITLE_SCALE, SNAKE_BODY, height // 6)

    spacing = height // (len(menu.entries) + 2)
    top = height // 2 - (len(menu.entries) - 1) * spacing // 2
    for index, entry in enumerate(menu.entries):
        colour = SELECTED if index == menu.index else TEXT
        _paste_centred(canvas, entry.name, ENTRY_SCALE, colour, top + index * spacing)


def _paste_centred(
    canvas: Image.Image, text: str, scale: int, colour: Colour, centre_y: int
) -> None:
    rendered = _text_image(text, colour)
    rendered = rendered.resize(
        (rendered.width * scale, rendered.height * scale), Image.NEAREST
    )
    canvas.paste(
        rendered,
        ((canvas.width - rendered.width) // 2, centre_y - rendered.height // 2),
    )


def _text_image(text: str, colour: Colour) -> Image.Image:
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    left, top, right, bottom = measure.textbbox((0, 0), text)
    image = Image.new("RGB", (right - left, bottom - top), BACKGROUND)
    ImageDraw.Draw(image).text((-left, -top), text, fill=colour)
    return image
