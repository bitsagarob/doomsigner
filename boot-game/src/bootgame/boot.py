"""
Boot entry point.

Deliberately tiny. Everything that could fail is imported inside a `try`, so
that a broken easter egg still leaves a working signing device rather than a
brick.

That has to include the handoff itself. This module used to import
`launch_seedsigner` at the top, which meant the one thing guaranteeing a working
device was itself able to stop the module from loading -- and a guarantee that
can be taken out by what it guards is not a guarantee. So the last resort
re-implements the exec instead of importing it, and duplicating those two
constants is the point rather than an oversight.
"""

import logging
import os

logger = logging.getLogger(__name__)

# Deliberately not imported from bootgame.launch; see the module docstring.
SEEDSIGNER_SRC = "/opt/src"
PYTHON = "/usr/bin/python3"


def hand_off() -> None:
    """Become SeedSigner. Does not return, except to raise."""
    try:
        from bootgame.launch import launch_seedsigner

        launch_seedsigner()
    except Exception:
        logger.exception("launch module unusable, exec'ing SeedSigner directly")
        os.chdir(SEEDSIGNER_SRC)
        os.execv(PYTHON, [PYTHON, "main.py"])


if __name__ == "__main__":
    try:
        from bootgame.runner import run

        run()
    except Exception:
        logger.exception("boot game failed, handing off to SeedSigner anyway")

    # If even this raises, the process exits non-zero and start.sh launches
    # SeedSigner itself. That is the outermost of the three nets.
    hand_off()
