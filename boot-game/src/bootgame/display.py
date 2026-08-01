"""
Shared drawing helpers and the game chooser.

Anything specific to a single game lives in that game's own module. What is here
is only what more than one of them needs.
"""

import logging
from typing import Tuple

from PIL import Image, ImageDraw

from bootgame.menu import Menu

logger = logging.getLogger(__name__)

Colour = Tuple[int, int, int]

BACKGROUND: Colour = (0, 0, 0)
TEXT: Colour = (255, 255, 255)
SELECTED: Colour = (255, 159, 10)
DIM: Colour = (0, 160, 0)

# Pillow's built-in font is 6px tall, which is unreadable on a 240px screen.
# Drawing small and upscaling with nearest neighbour gives legible, chunky text
# without needing a font file on the device.
TITLE_SCALE = 2
ENTRY_SCALE = 4


def render_menu(canvas: Image.Image, menu: Menu) -> None:
    """Render the game chooser. Deliberately lists no route to the wallet."""
    width, height = canvas.size
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, height), fill=BACKGROUND)

    paste_centred(canvas, "SELECT GAME", TITLE_SCALE, DIM, height // 6)

    spacing = height // (len(menu.entries) + 2)
    top = height // 2 - (len(menu.entries) - 1) * spacing // 2
    for index, entry in enumerate(menu.entries):
        colour = SELECTED if index == menu.index else TEXT
        paste_centred(canvas, entry.name, ENTRY_SCALE, colour, top + index * spacing)


def centred_text(draw: ImageDraw.ImageDraw, text: str, width: int, height: int) -> None:
    """Small unscaled text in the middle of the canvas."""
    left, top, right, bottom = draw.textbbox((0, 0), text)
    draw.text(
        ((width - (right - left)) // 2, (height - (bottom - top)) // 2),
        text,
        fill=TEXT,
    )


def paste_centred(canvas: Image.Image, text: str, scale: int, colour: Colour, centre_y: int) -> None:
    """Chunky upscaled text, horizontally centred, at the given vertical centre."""
    rendered = text_image(text, colour)
    rendered = rendered.resize(
        (rendered.width * scale, rendered.height * scale), Image.NEAREST
    )
    canvas.paste(
        rendered,
        ((canvas.width - rendered.width) // 2, centre_y - rendered.height // 2),
    )


def text_image(text: str, colour: Colour) -> Image.Image:
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    left, top, right, bottom = measure.textbbox((0, 0), text)
    image = Image.new("RGB", (right - left, bottom - top), BACKGROUND)
    ImageDraw.Draw(image).text((-left, -top), text, fill=colour)
    return image
