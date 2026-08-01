"""
The boot loop: choose a game, play it, hand off on the unlock sequence.

Imported lazily by `bootgame.boot` so that an import failure anywhere in here
still results in a working signing device.
"""

import logging
import time

from bootgame.catalog import available_games
from bootgame.display import render, render_menu
from bootgame.game import SnakeGame
from bootgame.launch import launch_external, launch_seedsigner
from bootgame.menu import Menu
from bootgame.unlock import UnlockSequence

logger = logging.getLogger(__name__)

# Game speed, and how often button state is sampled between frames.
TICK_SECONDS = 0.18
POLL_SECONDS = 0.01
GAME_OVER_PAUSE_SECONDS = 1.5


def choose_game(renderer, reader, unlock: UnlockSequence, games):
    """Run the chooser until an entry is picked. May hand off and never return."""
    menu = Menu(games)
    render_menu(renderer.canvas, menu)
    renderer.show_image()

    while True:
        for key in reader.presses():
            # Unlock is fed first so a completed sequence always wins, even
            # though KEY1 is also a select key.
            if unlock.feed(key):
                launch_seedsigner()

            if menu.is_select(key):
                return menu.selected

            menu.move(key)
            render_menu(renderer.canvas, menu)
            renderer.show_image()

        time.sleep(POLL_SECONDS)


def play_snake(renderer, reader, unlock: UnlockSequence) -> None:
    """Play until the unlock sequence is entered. Does not return."""
    game = SnakeGame()
    next_tick = time.monotonic()

    while True:
        for key in reader.presses():
            if unlock.feed(key):
                launch_seedsigner()

            game.turn(key)

        now = time.monotonic()
        if now >= next_tick:
            game.tick()
            render(renderer.draw, game, renderer.canvas_width, renderer.canvas_height)
            renderer.show_image()

            if game.game_over:
                time.sleep(GAME_OVER_PAUSE_SECONDS)
                game.reset()

            next_tick = time.monotonic() + TICK_SECONDS

        time.sleep(POLL_SECONDS)


def run() -> None:
    """Choose, play, hand off. Does not return."""
    from seedsigner.gui.renderer import Renderer

    from bootgame.input import ButtonReader

    Renderer.configure_instance()
    renderer = Renderer.get_instance()
    reader = ButtonReader()
    unlock = UnlockSequence()

    games = available_games()
    # With one game installed there is nothing to choose, so no menu appears and
    # the device behaves exactly as it did before a second game existed.
    if len(games) == 1:
        game = games[0]
    else:
        game = choose_game(renderer, reader, unlock, games)

    if not game.is_builtin:
        launch_external(game)

    play_snake(renderer, reader, unlock)
