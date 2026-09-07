"""Shoot the card-offer screen in the states that change what a user does."""
import json, sys, threading, time, types
sys.path.insert(0, "/app/tests")
stub = types.ModuleType("pytest")
stub.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda fn: fn))
stub.mark = types.SimpleNamespace(parametrize=lambda *a, **k: (lambda fn: fn))
stub.raises = lambda *a, **k: None
sys.modules.setdefault("pytest", stub)

from seedsigner.models.settings import Settings
Settings.RUNTIME_PROFILE = "rpi_40"
from seedsigner.models.settings_definition import SettingsConstants
st = Settings.get_instance()
st.set_value(SettingsConstants.SETTING__DISPLAY_CONFIGURATION,
             SettingsConstants.DISPLAY_CONFIGURATION__ST7789__240x240)
st.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)

from embit import bip32, bip39
from embit.psbt import PSBT
from seedsigner.controller import Controller
from seedsigner.gui.renderer import Renderer
from seedsigner.models.seed import Seed
from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.helpers import seedkeeper_utils
from seedsigner.views import psbt_views
from test_musig2_card import FakeCardWithSecrets

BUTTONS = {"DOWN": 19, "SELECT": 13}
def press(name, hold=0.25):
    with open("/dev/ss_spicap", "wb", buffering=0) as h:
        h.write(bytes([BUTTONS[name], 0])); time.sleep(hold)
        h.write(bytes([BUTTONS[name], 1]))

def press_after(seq, delay=2.0):
    def run():
        time.sleep(delay)
        for name in seq:
            press(name); time.sleep(0.8)
    threading.Thread(target=run, daemon=True).start()

data = json.load(open("/app/tests/data/musig2_psbts.json"))
root = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data["mnemonics"]["A"]))
other = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data["mnemonics"]["B"]))

Controller.configure_instance(); controller = Controller.get_instance()
Renderer.configure_instance()
seed = Seed(mnemonic=data["mnemonics"]["A"].split())
controller.storage.set_pending_seed(seed); controller.storage.finalize_pending_seed()
controller.psbt_seed = seed
controller.psbt = PSBT.from_string(data["psbt_round_one"])
controller.psbt_parser = PSBTParser(controller.psbt, seed=seed,
                                    network=SettingsConstants.REGTEST)

_real_init = seedkeeper_utils.init_satochip


def offer(card, presses):
    controller.musig2_session = None
    seedkeeper_utils.init_satochip = lambda *a, **k: card
    press_after(presses)
    dest = psbt_views.PSBTMusig2CardOfferView().run()
    return dest.View_cls.__name__

matching = FakeCardWithSecrets(root, {1: other, 2: root})
wrong = FakeCardWithSecrets(other, {1: other})

# Wrong-card screen first, alone, so it lands in an identifiable frame.
press_after(["SELECT"])
psbt_views.PSBTMusig2WrongCardView().run()
print("0 wrong-card screen rendered alone", flush=True)

print("1+2 offer, Use Card, card holds this seed ->",
      offer(matching, ["SELECT"]), flush=True)
print("    session:", type(controller.musig2_session).__name__
      if controller.musig2_session else None, flush=True)
print("3 offer, Use Card, card holds another seed ->",
      offer(wrong, ["SELECT"]), flush=True)
press_after(["SELECT"])
psbt_views.PSBTMusig2WrongCardView().run()
print("    wrong-card screen rendered", flush=True)
print("4 offer, Keep Device On ->", offer(None, ["DOWN", "SELECT"]), flush=True)
print("    session:", type(controller.musig2_session).__name__
      if controller.musig2_session else None, flush=True)

# A card already open and holding this seed is used without asking, so no offer
# screen is drawn at all. Nothing is patched here: setting the connector is what a
# seed loaded off a SeedKeeper leaves behind, and init_satochip is left alone so a
# reader being opened would show up as an extra screen.
seedkeeper_utils.init_satochip = _real_init
controller.musig2_session = None
controller.Satochip_Connector = matching
dest = psbt_views.PSBTMusig2CardOfferView().run()
print("5 card already open, no offer ->", dest.View_cls.__name__, flush=True)
print("    session:", type(controller.musig2_session).__name__
      if controller.musig2_session else None, flush=True)
print("    nonce_on_card:",
      getattr(controller.musig2_session, "nonce_on_card", None), flush=True)

# and the round screen that follows must say where the nonce went
press_after(["SELECT"])
psbt_views.PSBTMusig2RoundView().run()
print("6 round screen, card holding the nonce", flush=True)
print("DONE", flush=True)
