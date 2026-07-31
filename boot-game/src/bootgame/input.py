"""
Maps SeedSigner's GPIO channel numbers onto `Key`.

This is the only module in the package that imports SeedSigner, and so the only
one that needs a Raspberry Pi or the emulator in order to import at all.
"""

import logging
from typing import Dict, Optional

from seedsigner.hardware.buttons import HardwareButtonsConstants

from bootgame.keys import Key

logger = logging.getLogger(__name__)

CHANNEL_TO_KEY: Dict[int, Key] = {
    HardwareButtonsConstants.KEY_UP: Key.UP,
    HardwareButtonsConstants.KEY_DOWN: Key.DOWN,
    HardwareButtonsConstants.KEY_LEFT: Key.LEFT,
    HardwareButtonsConstants.KEY_RIGHT: Key.RIGHT,
    HardwareButtonsConstants.KEY_PRESS: Key.PRESS,
    HardwareButtonsConstants.KEY1: Key.KEY1,
    HardwareButtonsConstants.KEY2: Key.KEY2,
    HardwareButtonsConstants.KEY3: Key.KEY3,
}


def key_for_channel(channel: int) -> Optional[Key]:
    return CHANNEL_TO_KEY.get(channel)
