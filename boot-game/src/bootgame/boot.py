"""
Boot entry point: play the game, then hand off to SeedSigner.

The handoff is an `os.execv`, which replaces this process image outright. No
game code stays resident while the signing application is handling keys, and
the game never shares a process with anything that touches a seed.

If the game raises for any reason, SeedSigner is launched anyway. A broken
easter egg must never stand between someone and their signing device.
"""

import logging
import os
import time

logger = logging.getLogger(__name__)

SEEDSIGNER_SRC = "/opt/src"
PYTHON = "/usr/bin/python3"

# Game speed, and how often button state is sampled between frames.
TICK_SECONDS = 0.18
POLL_SECONDS = 0.01
GAME_OVER_PAUSE_SECONDS = 1.5


def launch_seedsigner() -> None:
    """Replace this process with SeedSigner. Does not return."""
    logger.info("handing off to SeedSigner")
    os.chdir(SEEDSIGNER_SRC)
    os.execv(PYTHON, [PYTHON, "main.py"])


def run() -> None:
    """Play until the unlock sequence is entered. Does not return."""
    # Imported here rather than at module scope so that an import failure is
    # caught by __main__ below and still results in a working signing device.
    from seedsigner.gui.renderer import Renderer
    from seedsigner.hardware.buttons import HardwareButtons, HardwareButtonsConstants

    from bootgame.display import render
    from bootgame.game import SnakeGame
    from bootgame.input import key_for_channel
    from bootgame.unlock import UnlockSequence

    Renderer.configure_instance()
    renderer = Renderer.get_instance()
    buttons = HardwareButtons.get_instance()

    game = SnakeGame()
    unlock = UnlockSequence()

    held = set()
    next_tick = time.monotonic()

    while True:
        # Edge detect: act on the press, not on the hold, so a leaned-on button
        # cannot walk through the unlock sequence on its own.
        for channel in HardwareButtonsConstants.ALL_KEYS:
            if not buttons.check_for_low(key=channel):
                held.discard(channel)
                continue

            if channel in held:
                continue

            held.add(channel)
            key = key_for_channel(channel)
            if key is None:
                continue

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


if __name__ == "__main__":
    try:
        run()
    except Exception:
        logger.exception("boot game failed, handing off to SeedSigner anyway")

    launch_seedsigner()
