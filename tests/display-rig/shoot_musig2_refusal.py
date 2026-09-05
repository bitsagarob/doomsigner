"""Shoot the refusal when the MuSig2 arrangement is malformed.

The participant-pubkeys field (0x1a) is truncated to 65 bytes, which is the case
tests/test_flows_musig2.py::test_a_malformed_arrangement_is_refused_on_screen
covers without pixels. What matters here is whether the refusal is readable.
"""
import json, sys, threading, time, types
sys.path.insert(0, "/app/tests")
stub = types.ModuleType("pytest")
stub.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda fn: fn))
stub.mark = types.SimpleNamespace(parametrize=lambda *a, **k: (lambda fn: fn))
sys.modules.setdefault("pytest", stub)

from seedsigner.models.settings import Settings
Settings.RUNTIME_PROFILE = "rpi_40"
from seedsigner.models.settings_definition import SettingsConstants
st = Settings.get_instance()
st.set_value(SettingsConstants.SETTING__DISPLAY_CONFIGURATION,
             SettingsConstants.DISPLAY_CONFIGURATION__ST7789__240x240)
st.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)

from embit.psbt import PSBT
from seedsigner.controller import Controller
from seedsigner.gui.renderer import Renderer
from seedsigner.helpers import musig2_psbt
from seedsigner.models.seed import Seed
from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.views import psbt_views

def press(line=13, hold=0.25):
    with open("/dev/ss_spicap", "wb", buffering=0) as h:
        h.write(bytes([line, 0])); time.sleep(hold); h.write(bytes([line, 1]))

def press_after(delay=2.5, times=3):
    def run():
        time.sleep(delay)
        for _ in range(times):
            press(); time.sleep(1.5)
    threading.Thread(target=run, daemon=True).start()

data = json.load(open("/app/tests/data/musig2_psbts.json"))
Controller.configure_instance(); controller = Controller.get_instance()
Renderer.configure_instance()
seed = Seed(mnemonic=data["mnemonics"]["A"].split())
controller.storage.set_pending_seed(seed); controller.storage.finalize_pending_seed()
controller.psbt_seed = seed

psbt = PSBT.from_string(data["psbt_round_one"])
scope = psbt.inputs[0]
key = next(k for k in scope.unknown
           if k[0] == musig2_psbt.PSBT_IN_MUSIG2_PARTICIPANT_PUBKEYS)
print("0x1a field length before:", len(scope.unknown[key]), flush=True)
scope.unknown[key] = scope.unknown[key][:65]
print("0x1a field length after :", len(scope.unknown[key]), flush=True)

controller.psbt = psbt
controller.psbt_parser = PSBTParser(psbt, seed=seed,
                                    network=SettingsConstants.REGTEST)
controller.musig2_session = None
press_after()
dest = psbt_views.PSBTMusig2RoundView().run()
print("refusal led to:", dest.View_cls.__name__ if dest else None, flush=True)
print("DONE", flush=True)
