"""Shared doubles for the loop tests."""

import pytest
from PIL import Image, ImageDraw


class HandedOff(Exception):
    """Stands in for os.execv, which never returns."""


class FakeRenderer:
    def __init__(self, size=240):
        self.canvas = Image.new("RGB", (size, size))
        self.draw = ImageDraw.Draw(self.canvas)
        self.canvas_width = size
        self.canvas_height = size
        self.shown = 0

    def show_image(self):
        self.shown += 1


class FakeReader:
    """Yields each scripted batch of presses once, then raises to end the loop."""

    def __init__(self, script):
        self.script = list(script)

    def presses(self):
        if not self.script:
            raise StopIteration()
        return iter(self.script.pop(0))


@pytest.fixture
def renderer():
    return FakeRenderer()
