import pytest

from bootgame.keys import Key
from bootgame.menu import Menu

ENTRIES = ["SNAKE", "DOOM", "PONG"]


@pytest.fixture
def menu():
    return Menu(ENTRIES)


def test_it_opens_on_the_first_entry(menu):
    assert menu.selected == "SNAKE"


def test_down_moves_to_the_next_entry(menu):
    menu.move(Key.DOWN)
    assert menu.selected == "DOOM"


def test_down_wraps_around_the_end(menu):
    for _ in range(len(ENTRIES)):
        menu.move(Key.DOWN)

    assert menu.selected == "SNAKE"


def test_up_wraps_around_the_start(menu):
    menu.move(Key.UP)
    assert menu.selected == "PONG"


def test_sideways_and_action_keys_do_not_move_the_highlight(menu):
    for key in (Key.LEFT, Key.RIGHT, Key.KEY1, Key.PRESS):
        menu.move(key)

    assert menu.selected == "SNAKE"


def test_the_joystick_click_selects(menu):
    assert menu.is_select(Key.PRESS)


def test_the_side_buttons_do_not_select(menu):
    # They spell the unlock sequence. If they also selected, the first press
    # would launch a game and the easter egg would be unreachable from here.
    for key in (Key.KEY1, Key.KEY2, Key.KEY3):
        assert not menu.is_select(key)


def test_the_direction_keys_do_not_select(menu):
    for key in (Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT):
        assert not menu.is_select(key)


def test_an_empty_menu_is_rejected():
    with pytest.raises(ValueError):
        Menu([])


def test_the_menu_offers_no_route_to_the_wallet():
    # The unlock sequence is the only way through. A menu entry would give the
    # whole thing away, so guard against one ever being added.
    menu = Menu(ENTRIES)
    assert not any("SEED" in entry.upper() for entry in menu.entries)
