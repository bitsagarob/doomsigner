"""
Snake, as a pure state machine.

No I/O, no hardware and no wall clock live in here. Every transition is driven
by an explicit `tick()` and randomness is injected, so the whole game is
deterministic and unit testable without a Raspberry Pi.
"""

import logging
from random import Random
from typing import List, Optional, Tuple

from bootgame.keys import Key

logger = logging.getLogger(__name__)

# (x, y), origin top left
Cell = Tuple[int, int]

DIRECTIONS = {
    Key.UP: (0, -1),
    Key.DOWN: (0, 1),
    Key.LEFT: (-1, 0),
    Key.RIGHT: (1, 0),
}


class SnakeGame:
    """
    Grid-based Snake. The snake is stored head first; `food` is None only when
    the board has been completely filled, which is a win rather than an error.
    """

    def __init__(self, grid_width: int = 12, grid_height: int = 12, rng: Random = None):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.rng = rng if rng is not None else Random()
        self.reset()


    def reset(self) -> None:
        """Return to the opening position: a length 3 snake heading right."""
        middle_row = self.grid_height // 2
        self.snake: List[Cell] = [(2, middle_row), (1, middle_row), (0, middle_row)]
        self.direction: Cell = DIRECTIONS[Key.RIGHT]
        self.score = 0
        self.game_over = False
        self.food = self._place_food()


    def turn(self, key: Key) -> None:
        """
        Steer the snake. Non-directional keys are ignored, as is a reversal
        straight back onto the neck, which would otherwise be an instant loss.
        """
        new_direction = DIRECTIONS.get(key)
        if new_direction is None:
            return

        if (-new_direction[0], -new_direction[1]) == self.direction:
            return

        self.direction = new_direction


    def tick(self) -> None:
        """Advance one step. Terminal once `game_over` is set."""
        if self.game_over:
            return

        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])

        if not self._in_bounds(new_head):
            self.game_over = True
            return

        eating = new_head == self.food

        # The tail vacates its cell on this same tick, so it only blocks the
        # head when the snake is about to grow into it.
        body = self.snake if eating else self.snake[:-1]
        if new_head in body:
            self.game_over = True
            return

        self.snake.insert(0, new_head)
        if eating:
            self.score += 1
            self.food = self._place_food()
        else:
            self.snake.pop()


    def _in_bounds(self, cell: Cell) -> bool:
        x, y = cell
        return 0 <= x < self.grid_width and 0 <= y < self.grid_height


    def _place_food(self) -> Optional[Cell]:
        occupied = set(self.snake)
        free = [
            (x, y)
            for y in range(self.grid_height)
            for x in range(self.grid_width)
            if (x, y) not in occupied
        ]
        if not free:
            return None

        return self.rng.choice(free)
