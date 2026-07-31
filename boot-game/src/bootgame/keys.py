"""
Symbolic button names.

The game logic is written against these rather than against
`HardwareButtonsConstants` so that it stays importable off-device: the
SeedSigner button module imports RPi.GPIO at module scope, which is not
available on a development machine. `bootgame.input` maps the real GPIO
channels onto these names.
"""

from enum import Enum


class Key(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    PRESS = "press"
    KEY1 = "key1"
    KEY2 = "key2"
    KEY3 = "key3"
