"""
The game chooser, as a pure state machine.

Deliberately has no entry for SeedSigner. The unlock sequence is the only way
through to the wallet, and putting it on a menu would give the whole thing away.
"""

import logging
from typing import List

from bootgame.keys import Key

logger = logging.getLogger(__name__)

# Only the joystick click confirms. The side buttons deliberately do nothing
# here: they spell the unlock sequence, and if they also selected, entering the
# sequence from the menu would be impossible because the first press would
# already have launched a game.
SELECT_KEYS = (Key.PRESS,)


class Menu:
    """Vertical list with wrap-around."""

    def __init__(self, entries: List):
        if not entries:
            raise ValueError("menu needs at least one entry")

        self.entries = list(entries)
        self.index = 0


    def move(self, key: Key) -> None:
        """Up and down move the highlight. Everything else is ignored."""
        if key == Key.UP:
            self.index = (self.index - 1) % len(self.entries)
        elif key == Key.DOWN:
            self.index = (self.index + 1) % len(self.entries)


    def is_select(self, key: Key) -> bool:
        """
        True if this key confirms the highlighted entry.

        Only the joystick click. See SELECT_KEYS for why the side buttons are
        excluded.
        """
        return key in SELECT_KEYS


    @property
    def selected(self):
        return self.entries[self.index]
