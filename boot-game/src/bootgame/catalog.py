"""
Which games this device has.

A built-in game names the module that implements it; that module is imported
only when the game is chosen. An external game names a binary and only appears
when it is actually installed, so a Snake-only image shows no chooser at all.

Adding a game is one entry here plus one module under `games/`. Nothing else in
the package needs to know it exists.
"""

import logging
import os
from dataclasses import dataclass
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

DOOM_BINARY = "/usr/local/games/doom"


@dataclass(frozen=True)
class Game:
    """Exactly one of `module` or `binary` is set."""

    name: str
    module: Optional[str] = None
    binary: Optional[str] = None

    def __post_init__(self):
        if bool(self.module) == bool(self.binary):
            raise ValueError(f"{self.name}: set exactly one of module or binary")


    @property
    def is_external(self) -> bool:
        return self.binary is not None


SNAKE = Game("SNAKE", module="bootgame.games.snake")
DOOM = Game("DOOM", binary=DOOM_BINARY)

ALL_GAMES = [SNAKE, DOOM]


def available_games(exists: Callable[[str], bool] = os.path.exists) -> List[Game]:
    """Games installed here. `exists` is injected so this is testable."""
    return [
        game for game in ALL_GAMES if not game.is_external or exists(game.binary)
    ]
