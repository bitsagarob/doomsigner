"""Does a spend cost one visit now that spare nonces ride in the psbt?

The claim is that a nonce made in advance removes MuSig2's forced wait, so a
signer visits once rather than twice. The load-bearing check is not a call
counter: signing also restocks, so the card's counters move for reasons that
have nothing to do with the claim. What proves it is that the nonce published
for this signing IS the spare that was already sitting in the psbt.
"""
import json, sys, types
sys.path.insert(0, "/app/tests")
stub = types.ModuleType("pytest")
stub.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda fn: fn))
stub.mark = types.SimpleNamespace(parametrize=lambda *a, **k: (lambda fn: fn))
stub.raises = lambda *a, **k: None
sys.modules.setdefault("pytest", stub)

from embit import bip32, bip39
from seedsigner.helpers import musig2_card as mc, musig2_psbt as mp
from test_musig2_card import (FakeCardWithSecrets, without_other_nonces,
                              role_of, core_nonce)

data = json.load(open("/app/tests/data/musig2_psbts.json"))
roots = {n: bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data["mnemonics"][n]))
         for n in "ABC"}
root = roots["B"]
card = FakeCardWithSecrets(root, {1: root})

# 1. a signing that leaves spares behind
psbt = without_other_nonces(data["psbt_round_one"])
mc.CardSession(card, sid=1).advance(psbt, root)
role = role_of(psbt, root)
spares = mc._spares(psbt, role)
print(f"after a signing, spares left behind: {len(spares)} "
      f"(SPARE_NONCES={mc.SPARE_NONCES})", flush=True)
spare_key = spares[0]
spare_value = psbt.inputs[0].unknown[spare_key]

# 2. what a coordinator holding that spare would build next
fresh = without_other_nonces(data["psbt_round_one"])
fresh.inputs[0].unknown[spare_key] = spare_value
other, nonce = core_nonce(data, role)
fresh.inputs[0].unknown[mp._key(mp.PSBT_IN_MUSIG2_PUB_NONCE, role, other)] = nonce

assert mp.partial_sig(fresh, role) is None, \
    "the input is already signed; nothing below would prove anything"
print("input carries no signature of ours: confirmed", flush=True)

progress = mc.CardSession(card, sid=1).advance(fresh, root)

published = fresh.inputs[0].unknown[
    mp._key(mp.PSBT_IN_MUSIG2_PUB_NONCE, role, role.pubkey)]
used_the_spare = published == spare_value[:66]
refilled = len(mc._spares(fresh, role))

print(f"visit 1: stage={progress.stage}", flush=True)
print(f"published nonce is the spare: {used_the_spare}", flush=True)
print(f"spares in the returned psbt: {refilled}", flush=True)
print("VERDICT:",
      "one visit, and the spare was the nonce used"
      if progress.stage == mp.SIGNED and used_the_spare
      else "NOT PROVEN", flush=True)
