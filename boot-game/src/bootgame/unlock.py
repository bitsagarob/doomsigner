"""
The easter egg: watches the button stream for a fixed sequence.

Kept free of any hardware import so the unlock can be tested exhaustively.
"""

import logging
from typing import List

from bootgame.keys import Key

logger = logging.getLogger(__name__)

DEFAULT_SEQUENCE = [
    Key.UP,
    Key.UP,
    Key.DOWN,
    Key.DOWN,
    Key.LEFT,
    Key.RIGHT,
    Key.KEY3,
]


class UnlockSequence:
    """Any wrong press resets progress. Completing the sequence returns True once."""

    def __init__(self, sequence: List[Key] = None):
        sequence = list(sequence) if sequence is not None else list(DEFAULT_SEQUENCE)
        if not sequence:
            raise ValueError("unlock sequence must not be empty")

        self.sequence = sequence
        self.progress = 0


    def feed(self, key: Key) -> bool:
        """Feed one keypress. True on the press that completes the sequence."""
        if key == self.sequence[self.progress]:
            self.progress += 1
            if self.progress == len(self.sequence):
                logger.info("unlock sequence completed")
                self.reset()
                return True

            return False

        # A wrong press restarts, but that press may itself be a valid opening
        # for the next attempt (matters whenever the sequence repeats a key).
        self.progress = 1 if key == self.sequence[0] else 0
        return False


    def reset(self) -> None:
        self.progress = 0
