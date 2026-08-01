"""
Turning polled button levels into discrete presses.

Pulled out of the hardware adapter so it can be tested without a Pi. This is
where the "one key per press, not per poll" rule lives, which is what stops a
leaned-on button from walking through the unlock sequence on its own.
"""

import logging
from typing import Callable, Iterator, List, Optional

from bootgame.keys import Key

logger = logging.getLogger(__name__)


class EdgeDetector:
    """Yields a key once when its channel goes down, and not again until it rises."""

    def __init__(self, channels: List[int], key_for_channel: Callable[[int], Optional[Key]]):
        self.channels = list(channels)
        self.key_for_channel = key_for_channel
        self.held = set()


    def presses(self, is_pressed: Callable[[int], bool]) -> Iterator[Key]:
        for channel in self.channels:
            if not is_pressed(channel):
                self.held.discard(channel)
                continue

            if channel in self.held:
                continue

            self.held.add(channel)
            key = self.key_for_channel(channel)
            if key is not None:
                yield key
