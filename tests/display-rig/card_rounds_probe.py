"""INCOMPLETE. Round one is proven; round two does not reach the card.

Round one works: the card is selected, makes one nonce, and seals it, all
verified through the app's own view on the rig. Round two, as written here,
signs through the base class instead -- CardSession.sign is called zero times --
so this probe proves nothing about the card's open-once rule, and the replay
attempt it reports is meaningless. The psbt surgery below is the suspect: the
seal is bound to the sighash, and the reconstructed psbt is probably not the
transaction the seal was made for.

Do not read a security conclusion out of this file until CardSession.sign shows
a non-zero call count.

Both MuSig2 rounds with the nonce on the card, then a replay attempt.

The feature's claim is that the secret nonce survives a power-off because the
card holds it, and that the card opens it exactly once so a copied sealed nonce
is worth nothing. Round two therefore uses a FRESH session, the way a rebooted
device would, and the replay uses a fresh one again.
"""
import json, sys, types
sys.path.insert(0, "/app/tests")
stub = types.ModuleType("pytest")
stub.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda fn: fn))
stub.mark = types.SimpleNamespace(parametrize=lambda *a, **k: (lambda fn: fn))
stub.raises = lambda *a, **k: None
sys.modules.setdefault("pytest", stub)

from embit import bip32, bip39
from embit.psbt import PSBT
from seedsigner.helpers import musig2_card as mc, musig2_psbt as mp
from test_musig2_card import FakeCardWithSecrets

data = json.load(open("/app/tests/data/musig2_psbts.json"))
root = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data["mnemonics"]["A"]))
other = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data["mnemonics"]["B"]))
card = FakeCardWithSecrets(root, {1: other, 2: root})

class Ctl:
    Satochip_Connector = card

calls = {"new_nonce": 0, "sign": 0}
_orig_new = mc.CardSession.new_nonce
_orig_sign = mc.CardSession.sign
def _new(self, *a, **k):
    calls["new_nonce"] += 1
    return _orig_new(self, *a, **k)
def _sign(self, *a, **k):
    calls["sign"] += 1
    return _orig_sign(self, *a, **k)
mc.CardSession.new_nonce = _new
mc.CardSession.sign = _sign


def fresh_session():
    s = mc.select(Ctl(), root)
    assert s is not None, "card not selected"
    return s

# Round one: no signature yet, a sealed nonce goes into the psbt.
psbt = PSBT.from_string(data["psbt_round_one"])
p1 = fresh_session().advance(psbt, root)
print(f"round 1: stage={p1.stage} generated={card.generated} "
      f"sealed={len(card.sealed)} opened={len(card.spent)}", flush=True)

# Round two, on a session that never saw round one: the device was switched off.
both = PSBT.from_string(data["psbt_both_nonces"])
for scope, source in zip(both.inputs, psbt.inputs):
    for key, value in source.unknown.items():
        scope.unknown.setdefault(key, value)
p2 = fresh_session().advance(both, root)
print(f"round 2: stage={p2.stage} generated={card.generated} "
      f"sealed={len(card.sealed)} opened={len(card.spent)}", flush=True)

sigs = [k for k in both.inputs[0].unknown if k[0] == mp.PSBT_IN_MUSIG2_PARTIAL_SIG]
print(f"partial signatures in the psbt: {len(sigs)}", flush=True)

# Replay: the same sealed nonce, a third fresh session. The card must refuse.
replay = PSBT.from_string(data["psbt_both_nonces"])
for scope, source in zip(replay.inputs, psbt.inputs):
    for key, value in source.unknown.items():
        scope.unknown.setdefault(key, value)
try:
    fresh_session().advance(replay, root)
    print("REPLAY WAS ACCEPTED", flush=True)
except Exception as exc:
    print(f"replay refused: {type(exc).__name__}: {str(exc)[:90]}", flush=True)
print(f"final: generated={card.generated} opened={len(card.spent)}", flush=True)
print("CardSession.new_nonce calls:", calls["new_nonce"], flush=True)
print("CardSession.sign calls:", calls["sign"], flush=True)
