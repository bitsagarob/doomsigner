"""
The nets that keep a broken easter egg from becoming a black screen.

All three of these failed at once on the pi0 image built 2026-08-01: stage.sh
never ran, so `python3 -m bootgame.boot` could not resolve, and because start.sh
launched nothing else, the device booted to nothing. None of it was caught,
because nothing here tested the failure path -- only the happy one.

So these tests all ask the same question from different heights: when the game
is broken, does the wallet still start?
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT_GAME = Path(__file__).resolve().parents[1]
START_SH = BOOT_GAME.parent / "opt" / "rootfs-overlay" / "start.sh"
OVERLAY = BOOT_GAME.parent / "opt" / "rootfs-overlay" / "usr/local/bootgame/bootgame"


class Handed(Exception):
    """Stands in for os.execv, which never returns."""


@pytest.fixture
def boot_module():
    from bootgame import boot

    return boot


def test_hand_off_uses_the_launch_module_when_it_works(boot_module, monkeypatch):
    called = []
    import bootgame.launch

    monkeypatch.setattr(bootgame.launch, "launch_seedsigner",
                        lambda: called.append("launch"))
    boot_module.hand_off()
    assert called == ["launch"]


def test_hand_off_execs_seedsigner_when_the_launch_module_is_unimportable(
    boot_module, monkeypatch
):
    """The regression. boot.py used to import launch at module scope, so a
    failure there stopped boot.py loading at all and nothing started."""
    monkeypatch.setitem(sys.modules, "bootgame.launch", None)

    seen = {}
    monkeypatch.setattr(boot_module.os, "chdir", lambda path: seen.update(chdir=path))

    def fake_execv(path, args):
        seen.update(execv=(path, args))
        raise Handed()

    monkeypatch.setattr(boot_module.os, "execv", fake_execv)

    with pytest.raises(Handed):
        boot_module.hand_off()

    assert seen["chdir"] == "/opt/src"
    assert seen["execv"] == ("/usr/bin/python3", ["/usr/bin/python3", "main.py"])


def test_boot_does_not_import_launch_at_module_scope():
    """Checked against the parse tree, not the text: the import inside hand_off
    is fine and required, and only one at module scope is the bug. Worth
    asserting separately because with the import back at the top every other
    test in this file still passes -- importing boot.py is what breaks, and by
    then the test run has already imported it."""
    tree = ast.parse((BOOT_GAME / "src/bootgame/boot.py").read_text())
    module_scope = [
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    ]
    assert "bootgame.launch" not in module_scope


def test_start_sh_falls_back_to_seedsigner_if_the_game_cannot_start():
    """The outermost net, and the only one that covers the package being
    missing from the image entirely -- at which point no Python of ours runs."""
    script = START_SH.read_text()
    launch = re.search(r"^\s*PYTHONPATH=.*bootgame\.boot.*$", script,
                       re.MULTILINE | re.DOTALL)
    assert launch, "start.sh no longer launches the boot game"

    active = "\n".join(l for l in script.splitlines() if not l.strip().startswith("#"))
    assert "bootgame.boot ||" in active.replace("\n", " ").replace("  ", " ") or \
           re.search(r"bootgame\.boot\s*\|\|", active), \
           "start.sh does not fall back to SeedSigner when the boot game fails"
    assert re.search(r"\|\|\s*\n?\s*/usr/bin/python3 main\.py", active), \
           "start.sh's fallback does not run main.py"


def test_stage_sh_copies_every_module_including_the_games_subpackage(tmp_path):
    """stage.sh used to copy only src/bootgame/*.py, so the menu could list a
    game whose module never shipped."""
    subprocess.run(["sh", str(BOOT_GAME / "stage.sh")], check=True,
                   capture_output=True)

    source = BOOT_GAME / "src/bootgame"
    expected = {p.relative_to(source) for p in source.rglob("*.py")}
    staged = {p.relative_to(OVERLAY) for p in OVERLAY.rglob("*.py")}
    assert expected == staged

    assert (OVERLAY / "games/snake.py").is_file(), \
        "catalog.py imports bootgame.games.snake; it has to be in the image"
