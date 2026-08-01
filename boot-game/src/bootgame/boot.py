"""
Boot entry point.

Deliberately tiny. Everything that could fail is imported inside the `try`, so
that a broken easter egg still leaves a working signing device rather than a
brick.
"""

import logging

from bootgame.launch import launch_seedsigner

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        from bootgame.runner import run

        run()
    except Exception:
        logger.exception("boot game failed, handing off to SeedSigner anyway")

    launch_seedsigner()
