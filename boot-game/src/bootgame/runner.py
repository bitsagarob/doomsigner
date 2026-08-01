"""
The boot loop: choose a game, play it, hand off on the unlock sequence.

Imported lazily by `bootgame.boot` so that an import failure anywhere in here
still results in a working signing device.
"""

import importlib
import logging
import time

from bootgame.catalog import available_games
from bootgame.display import render_menu
from bootgame.launch import launch_external, launch_seedsigner
from bootgame.menu import Menu
from bootgame.unlock import UnlockSequence

logger = logging.getLogger(__name__)

POLL_SECONDS = 0.01


def choose_game(renderer, reader, unlock: UnlockSequence, games):
    """Run the chooser until an entry is picked. May hand off and never return."""
    menu = Menu(games)
    render_menu(renderer.canvas, menu)
    renderer.show_image()

    while True:
        for key in reader.presses():
            if unlock.feed(key):
                launch_seedsigner()

            if menu.is_select(key):
                return menu.selected

            menu.move(key)
            render_menu(renderer.canvas, menu)
            renderer.show_image()

        time.sleep(POLL_SECONDS)


def play_game(game, renderer, reader, unlock: UnlockSequence) -> None:
    """
    Play one game.

    External games replace this process and never come back. Built-in ones are
    imported here and not before, so an unused game costs nothing at boot and a
    broken one cannot stop the device reaching the wallet.
    """
    if game.is_external:
        # execv does not return, but be explicit rather than relying on it.
        launch_external(game)
        return

    logger.info("loading %s from %s", game.name, game.module)
    importlib.import_module(game.module).play(renderer, reader, unlock)


def run() -> None:
    """Choose, play, hand off. Does not return under normal use."""
    from seedsigner.gui.renderer import Renderer

    from bootgame.input import ButtonReader

    Renderer.configure_instance()
    renderer = Renderer.get_instance()
    reader = ButtonReader()
    unlock = UnlockSequence()

    while True:
        games = available_games()
        # With one game there is nothing to choose, so no chooser appears and
        # the device behaves exactly as it did before a second game existed.
        game = games[0] if len(games) == 1 else choose_game(renderer, reader, unlock, games)

        try:
            play_game(game, renderer, reader, unlock)
        except Exception:
            logger.exception("%s failed", game.name)
            if len(games) == 1:
                # Nothing to fall back to, so let boot.py hand off to the wallet
                # rather than spin on a game that cannot start.
                raise

        # A game that returns simply sends the player back to the chooser.
