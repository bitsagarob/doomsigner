"""
Boot entry point.

Deliberately tiny. Everything that could fail is imported inside a `try`, so
that a broken easter egg still leaves a working signing device rather than a
brick.
"""

import logging
import os

logger = logging.getLogger(__name__)


def hand_off() -> None:
    """Hand off to SeedSigner. Does not return.

    bootgame.launch is imported here, not at module scope: a module-scope
    import would let a bug in that module stop boot.py from loading at all,
    and then nothing starts. If it can't be imported either, exec main.py
    directly -- the same handoff bootgame.launch.launch_seedsigner would have
    done.
    """
    try:
        from bootgame.launch import launch_seedsigner

        launch_seedsigner()
    except Exception:
        os.chdir("/opt/src")
        os.execv("/usr/bin/python3", ["/usr/bin/python3", "main.py"])


if __name__ == "__main__":
    try:
        from bootgame.runner import run

        run()
    except Exception:
        logger.exception("boot game failed, handing off to SeedSigner anyway")

    hand_off()
