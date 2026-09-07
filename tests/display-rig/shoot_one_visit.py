"""The happy path: a spend that finishes in a single visit, and what it shows.

MuSig2 has two rounds and always will, one to exchange nonces and one to produce
partial signatures. That is not the same as two visits to the device. When the
coordinator brings back a nonce this card published on an earlier spend, every
public nonce is already in the transaction, so both rounds happen back to back
without stopping and the signer visits once.

That case is worth capturing rather than only asserting, because it is the one a
user is meant to enjoy and the one whose screen was wrong: it used to end on
"Step 2 of 2", naming a step nobody performed.

Nothing here is a shortcut. The first signing really runs, only so the card
leaves its spare nonces behind in a transaction, which is how they reach a
coordinator at all. The second uses the same card object, because a nonce sealed
by one card cannot be opened by another and a fresh fake would prove nothing.
"""
import json
import sys
import threading
import time
import types

sys.path.insert(0, "/app/tests")
stub = types.ModuleType("pytest")
stub.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda fn: fn))
stub.mark = types.SimpleNamespace(parametrize=lambda *a, **k: (lambda fn: fn))
stub.raises = lambda *a, **k: None
sys.modules.setdefault("pytest", stub)

from seedsigner.models.settings import Settings
Settings.RUNTIME_PROFILE = "rpi_40"
from seedsigner.models.settings_definition import SettingsConstants
settings = Settings.get_instance()
settings.set_value(SettingsConstants.SETTING__DISPLAY_CONFIGURATION,
                   SettingsConstants.DISPLAY_CONFIGURATION__ST7789__240x240)
settings.set_value(SettingsConstants.SETTING__NETWORK, SettingsConstants.REGTEST)

from embit import bip32, bip39
from seedsigner.controller import Controller
from seedsigner.gui.renderer import Renderer
from seedsigner.models.psbt_parser import PSBTParser
from seedsigner.models.seed import Seed
from seedsigner.helpers import musig2_card as mc, musig2_psbt as mp
from seedsigner.views import psbt_views
from test_musig2_card import (FakeCardWithSecrets, without_other_nonces, role_of,
                              core_nonce)

SELECT = 13


done = threading.Event()


def keep_pressing(delay=1.5, every=2.0):
    """Tap SELECT until the screen has been answered.

    A single timed press is a race: app start-up is slower on some runs than
    others, and a press that lands before the screen is waiting is simply lost,
    after which the probe hangs until the harness kills it. That happened, and a
    probe that hangs is worse than one that fails, because a hung capture keeps
    growing.
    """
    def run():
        time.sleep(delay)
        while not done.is_set():
            with open("/dev/ss_spicap", "wb", buffering=0) as handle:
                handle.write(bytes([SELECT, 0]))
                time.sleep(0.25)
                handle.write(bytes([SELECT, 1]))
            time.sleep(every)
    threading.Thread(target=run, daemon=True).start()


data = json.load(open("/app/tests/data/musig2_psbts.json"))
root = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data["mnemonics"]["B"]))
card = FakeCardWithSecrets(root, {1: root})

# One signing, run only to leave this card's spare nonces in a transaction.
first = without_other_nonces(data["psbt_round_one"])
mc.CardSession(card, sid=1).advance(first, root)
role = role_of(first, root)
pooled_key = mc._pooled(first, role)[0]
pooled_value = first.inputs[0].unknown[pooled_key]
print(f"spare nonces left behind: {len(mc._pooled(first, role))}", flush=True)

# What a coordinator holding one of those spares builds next.
fresh = without_other_nonces(data["psbt_round_one"])
fresh.inputs[0].unknown[pooled_key] = pooled_value
other, nonce = core_nonce(data, role)
fresh.inputs[0].unknown[mp._key(mp.PSBT_IN_MUSIG2_PUB_NONCE, role, other)] = nonce
assert mp.partial_sig(fresh, role) is None, "already signed; this would prove nothing"

Controller.configure_instance()
controller = Controller.get_instance()
Renderer.configure_instance()
seed = Seed(mnemonic=data["mnemonics"]["B"].split())
controller.psbt_seed = seed
controller.psbt = fresh
controller.psbt_parser = PSBTParser(fresh, seed=seed,
                                    network=SettingsConstants.REGTEST)
controller.musig2_session = mc.CardSession(card, sid=1)

# What the screen was told to show, not only that it drew something. A step count
# here would mean the count is of rounds again.
seen = {}
view = psbt_views.PSBTMusig2RoundView()
original = view.run_screen


def spy(screen_cls, **kwargs):
    seen.update(kwargs)
    return original(screen_cls, **kwargs)


view.run_screen = spy
keep_pressing()
view.run()
done.set()

signed = mp.partial_sig(fresh, role) is not None
headline = seen.get("status_headline", "")
used_pooled = fresh.inputs[0].unknown.get(
    mp._key(mp.PSBT_IN_MUSIG2_PUB_NONCE, role, role.pubkey)) == pooled_value[:66]

print(f"signed in this one visit: {signed}", flush=True)
print(f"the nonce used was the pooled one: {used_pooled}", flush=True)
print(f"headline: {headline!r}", flush=True)
print(f"text: {seen.get('text', '')!r}", flush=True)
print("VERDICT:",
      "one visit, signed, and the screen counts no steps"
      if signed and used_pooled and "step" not in headline.lower()
      else "NOT PROVEN", flush=True)
