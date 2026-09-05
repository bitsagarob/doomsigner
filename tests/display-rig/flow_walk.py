"""Walk a signing flow on the Virtual HAT and capture every screen.

Runs inside the UML sandbox. The app is unmodified: it renders through its own
ST7789 driver onto a real /dev/spidev0.0, and the presses arrive on a real
/dev/gpiochip0. This drives navigation by following the app's own Destination
chain, so the screens and their order are the device's, not a script's idea of
them.

    python3 appsrc_flow.py musig2      one 2-of-3 MuSig2 round, from the fixture
    python3 appsrc_flow.py multisig    the same psbt reviewed without MuSig2
"""
import json
import os
import sys
import threading
import time

from seedsigner.models.settings import Settings
Settings.RUNTIME_PROFILE = "rpi_40"

from seedsigner.models.settings_definition import SettingsConstants
settings = Settings.get_instance()
settings.set_value(SettingsConstants.SETTING__DISPLAY_CONFIGURATION,
                   SettingsConstants.DISPLAY_CONFIGURATION__ST7789__240x240)
settings.set_value(SettingsConstants.SETTING__NETWORK,
                   SettingsConstants.REGTEST)

from seedsigner.controller import Controller
from seedsigner.gui.renderer import Renderer
from seedsigner.models.seed import Seed
from seedsigner.views.view import Destination

BUTTONS = {"UP": 6, "DOWN": 19, "LEFT": 5, "RIGHT": 26, "SELECT": 13,
           "KEY1": 21, "KEY2": 20, "KEY3": 16}


def press(name, hold=0.25):
    """Press a button the way a finger does: pull the line low, then let go."""
    line = BUTTONS[name]
    with open("/dev/ss_spicap", "wb", buffering=0) as handle:
        handle.write(bytes([line, 0]))
        time.sleep(hold)
        handle.write(bytes([line, 1]))


def keep_pressing(stop, button="SELECT", every=2.0):
    """Every screen in a review flow advances on SELECT, so tap it until done."""
    while not stop.is_set():
        time.sleep(every)
        if stop.is_set():
            break
        press(button)


def load_fixture():
    path = "/app/tests/data/musig2_psbts.json"
    with open(path) as handle:
        return json.load(handle)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "musig2"
    data = load_fixture()

    Controller.configure_instance()
    controller = Controller.get_instance()
    Renderer.configure_instance()

    from embit.psbt import PSBT
    from seedsigner.models.psbt_parser import PSBTParser

    seed = Seed(mnemonic=data["mnemonics"]["A"].split())
    controller.storage.set_pending_seed(seed)
    controller.storage.finalize_pending_seed()
    controller.psbt_seed = seed

    psbt = PSBT.from_string(data["psbt_round_one"])
    controller.psbt = psbt
    controller.psbt_parser = PSBTParser(
        psbt, seed=seed, network=SettingsConstants.REGTEST)
    print(f"psbt loaded: {len(psbt.inputs)} in, {len(psbt.outputs)} out", flush=True)

    from seedsigner.views import psbt_views
    start = Destination(psbt_views.PSBTOverviewView)

    stop = threading.Event()
    threading.Thread(target=keep_pressing, args=(stop,), daemon=True).start()

    seen = []
    destination = start
    for step in range(12):
        name = destination.View_cls.__name__
        seen.append(name)
        print(f"step {step + 1}: {name}", flush=True)
        try:
            destination = destination.run()
        except Exception as exc:
            print(f"  stopped at {name}: {type(exc).__name__}: {str(exc)[:120]}",
                  flush=True)
            break
        if destination is None:
            break
        time.sleep(0.4)

    stop.set()
    time.sleep(0.5)
    print("FLOW:", " -> ".join(seen), flush=True)


if __name__ == "__main__":
    main()
