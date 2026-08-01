import pytest

from bootgame.keys import Key
from bootgame.unlock import DEFAULT_SEQUENCE, UnlockSequence


def test_the_full_sequence_unlocks():
    unlock = UnlockSequence()

    results = [unlock.feed(key) for key in DEFAULT_SEQUENCE]

    assert results[:-1] == [False] * (len(DEFAULT_SEQUENCE) - 1)
    assert results[-1] is True


def test_a_partial_sequence_does_not_unlock():
    unlock = UnlockSequence()

    assert not any(unlock.feed(key) for key in DEFAULT_SEQUENCE[:-1])


def test_a_wrong_press_resets_progress():
    unlock = UnlockSequence([Key.UP, Key.DOWN, Key.KEY3])

    unlock.feed(Key.UP)
    unlock.feed(Key.KEY1)

    assert unlock.progress == 0
    assert not unlock.feed(Key.DOWN)


def test_a_wrong_press_that_matches_the_opening_starts_a_new_attempt():
    unlock = UnlockSequence([Key.UP, Key.DOWN, Key.KEY3])

    unlock.feed(Key.UP)
    unlock.feed(Key.UP)  # wrong here, but a valid opening

    assert unlock.progress == 1
    assert unlock.feed(Key.DOWN) is False
    assert unlock.feed(Key.KEY3) is True


def test_it_rearms_after_unlocking():
    unlock = UnlockSequence([Key.UP])

    assert unlock.feed(Key.UP) is True
    assert unlock.progress == 0
    assert unlock.feed(Key.UP) is True


def test_an_empty_sequence_is_rejected():
    with pytest.raises(ValueError):
        UnlockSequence([])
