import pytest

from bootgame.edges import EdgeDetector
from bootgame.keys import Key

CHANNELS = [10, 20, 30]
MAPPING = {10: Key.UP, 20: Key.KEY1, 30: Key.KEY2}


@pytest.fixture
def detector():
    return EdgeDetector(CHANNELS, MAPPING.get)


def pressing(*channels):
    return lambda channel: channel in channels


def test_a_press_yields_its_key(detector):
    assert list(detector.presses(pressing(10))) == [Key.UP]


def test_nothing_pressed_yields_nothing(detector):
    assert list(detector.presses(pressing())) == []


def test_a_held_button_yields_only_once(detector):
    assert list(detector.presses(pressing(10))) == [Key.UP]
    assert list(detector.presses(pressing(10))) == []
    assert list(detector.presses(pressing(10))) == []


def test_releasing_and_pressing_again_yields_again(detector):
    list(detector.presses(pressing(10)))
    list(detector.presses(pressing()))

    assert list(detector.presses(pressing(10))) == [Key.UP]


def test_simultaneous_presses_all_yield(detector):
    assert list(detector.presses(pressing(10, 20))) == [Key.UP, Key.KEY1]


def test_holding_one_while_pressing_another(detector):
    list(detector.presses(pressing(10)))

    assert list(detector.presses(pressing(10, 30))) == [Key.KEY2]


def test_unmapped_channels_are_skipped():
    detector = EdgeDetector([99], MAPPING.get)

    assert list(detector.presses(pressing(99))) == []


def test_a_held_button_cannot_walk_the_unlock_sequence():
    # The reason edge detection exists: leaning on KEY1 must not advance past
    # the first step of the sequence.
    from bootgame.unlock import UnlockSequence

    detector = EdgeDetector(CHANNELS, MAPPING.get)
    unlock = UnlockSequence([Key.KEY1, Key.KEY1, Key.KEY1])

    unlocked = False
    for _ in range(50):
        for key in detector.presses(pressing(20)):
            unlocked = unlock.feed(key) or unlocked

    assert not unlocked
