"""
Which games this device actually has.

An external game only appears if its binary is present, so a Snake-only image
shows no menu at all and behaves exactly as it did before DOOM existed. That is
the feature toggle: it follows what was built into the image, with nothing to
configure.
"""

import logging
import os
from dataclasses import dataclass
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

DOOM_BINARY = "/usr/local/games/doom"


@dataclass(frozen=True)
class Game:
    """`binary` is None for the built-in game, otherwise an executable to exec."""

    name: str
    binary: Optional[str] = None

    @property
    def is_builtin(self) -> bool:
        return self.binary is None


SNAKE = Game("SNAKE")
DOOM = Game("DOOM", binary=DOOM_BINARY)

ALL_GAMES = [SNAKE, DOOM]


def available_games(exists: Callable[[str], bool] = os.path.exists) -> List[Game]:
    """Games installed on this device. `exists` is injected so this is testable."""
    return [game for game in ALL_GAMES if game.is_builtin or exists(game.binary)]
