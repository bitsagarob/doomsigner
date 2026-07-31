"""
Browser-side driver for the test harness.

This is the harness equivalent of `bootgame.boot`: same game, same unlock, same
renderer, but driven by browser events instead of GPIO polling. It exists
because `boot.py` and `input.py` import RPi.GPIO and SeedSigner, neither of
which can load under Pyodide.

Everything it drives is the real shipped code. Only the event loop differs.
"""

from PIL import Image, ImageDraw

from bootgame.display import render
from bootgame.game import SnakeGame
from bootgame.keys import Key
from bootgame.unlock import UnlockSequence


class WebSession:
    """One playable session, rendering to an in-memory canvas."""

    def __init__(self, width: int = 240, height: int = 240):
        self.width = width
        self.height = height
        self.canvas = Image.new("RGB", (width, height))
        self.draw = ImageDraw.Draw(self.canvas)
        self.game = SnakeGame()
        self.unlock = UnlockSequence()
        self.unlocked = False


    def press(self, name: str) -> bool:
        """Feed a keypress by `Key` member name. True once the unlock completes."""
        key = Key[name]
        if self.unlock.feed(key):
            self.unlocked = True

        self.game.turn(key)
        return self.unlocked


    def tick(self) -> bytes:
        """Advance one step and return the frame as raw RGB bytes."""
        self.game.tick()
        return self.frame()


    def frame(self) -> bytes:
        render(self.draw, self.game, self.width, self.height)
        return self.canvas.tobytes()


    def reset(self) -> None:
        self.game.reset()


    @property
    def game_over(self) -> bool:
        return self.game.game_over


    @property
    def score(self) -> int:
        return self.game.score
