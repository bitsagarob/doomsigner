"""Both MuSig2 rounds with the secret nonce on the card, then a replay attempt.

The feature's claim is that the secret nonce survives a power-off because the
card holds it sealed, and that the card opens each seal exactly once, so a copy
of the sealed nonce is worth nothing. Neither half can be checked by a unit test
of the wallet alone: the first needs the session object to be thrown away and
rebuilt, the second needs a card that refuses.

Round two must be the SAME transaction as round one with only the other
participant's nonce added, so it starts from what round one serialised rather
than from the fixture's fully-populated psbt. Starting from the latter carries a
partial signature already, and `advance` then takes its "I have signed this"
branch and never reaches the card at all. That produced a confident and entirely
wrong replay result the first time this probe was written.

Each check refuses to report unless the path it is about actually ran.
"""
import json
import sys
import types

sys.path.insert(0, "/app/tests")

# FakeCardWithSecrets lives in the branch's own test module, which imports
# pytest. Nothing in the fake needs it, so stub the decorators rather than drag
# a test runner into the sandbox or copy the class and let it drift.
stub = types.ModuleType("pytest")
stub.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda fn: fn))
stub.mark = types.SimpleNamespace(parametrize=lambda *a, **k: (lambda fn: fn))
stub.raises = lambda *a, **k: None
sys.modules.setdefault("pytest", stub)

from embit import bip32, bip39
from embit.psbt import PSBT

from seedsigner.helpers import musig2_card as mc
from seedsigner.helpers import musig2_psbt as mp
from test_musig2_card import FakeCardWithSecrets

data = json.load(open("/app/tests/data/musig2_psbts.json"))
root = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data["mnemonics"]["A"]))
other_root = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data["mnemonics"]["B"]))
card = FakeCardWithSecrets(root, {1: other_root, 2: root})


class Controller:
    Satochip_Connector = card


calls = {"new_nonce": 0, "sign": 0}
_orig_new, _orig_sign = mc.CardSession.new_nonce, mc.CardSession.sign
mc.CardSession.new_nonce = lambda self, *a, **k: (
    calls.__setitem__("new_nonce", calls["new_nonce"] + 1)
    or _orig_new(self, *a, **k))
mc.CardSession.sign = lambda self, *a, **k: (
    calls.__setitem__("sign", calls["sign"] + 1) or _orig_sign(self, *a, **k))


def fresh_session():
    """A session that has never seen a previous round, i.e. a rebooted device."""
    session = mc.select(Controller(), root)
    if session is None:
        raise SystemExit("the card was not selected; nothing below is meaningful")
    return session


def without_other_nonces(psbt_b64):
    """Drop the captured nonce so round one waits instead of signing at once."""
    psbt = PSBT.from_string(psbt_b64)
    for scope in psbt.inputs:
        for key in [k for k in scope.unknown
                    if k[0] == mp.PSBT_IN_MUSIG2_PUB_NONCE]:
            del scope.unknown[key]
    return psbt


# --- round one -------------------------------------------------------------
psbt = without_other_nonces(data["psbt_round_one"])
first = fresh_session().advance(psbt, root)
round_one_b64 = psbt.to_string()
print(f"round 1: stage={first.stage} generated={card.generated} "
      f"sealed={len(card.sealed)} opened={len(card.spent)}", flush=True)

# --- the device is switched off here ---------------------------------------
psbt2 = PSBT.from_string(round_one_b64)
# The seal rides in a proprietary field as pubnonce + sealed, so identify it by
# that length rather than by a constant the module does not export.
sealed_survived = any(
    len(v) == mc.SIZE_PUBNONCE + mc.SIZE_SEALED
    for v in psbt2.inputs[0].unknown.values())
print(f"sealed field survived serialisation: {sealed_survived}", flush=True)

role = mp.roles(psbt2, root)[0][0]
both = PSBT.from_string(data["psbt_both_nonces"])
other = next(pk for pk in role.aggregate.participants if pk != role.pubkey)
key = mp._key(mp.PSBT_IN_MUSIG2_PUB_NONCE, role, other)
psbt2.inputs[0].unknown[key] = both.inputs[0].unknown[key]

# --- round two, on a session that never saw round one ----------------------
second = fresh_session().advance(psbt2, root)
print(f"round 2: stage={second.stage} generated={card.generated} "
      f"sealed={len(card.sealed)} opened={len(card.spent)}", flush=True)
print(f"CardSession.new_nonce calls: {calls['new_nonce']}  "
      f"sign calls: {calls['sign']}", flush=True)

# --- replay ----------------------------------------------------------------
# The threat is a COPY of the sealed nonce, so rebuild exactly the psbt round two
# was given rather than reusing the one it has since written to: the module
# clears the seal after opening it, and a psbt with no seal legitimately asks the
# card for a fresh nonce, which is safe behaviour and not the thing under test.
if calls["sign"] == 0:
    print("INCONCLUSIVE: round two never called CardSession.sign, so the card's "
          "open-once rule was not exercised. No replay result is reported.",
          flush=True)
else:
    replay = PSBT.from_string(round_one_b64)
    replay.inputs[0].unknown[key] = both.inputs[0].unknown[key]
    before_generated, before_opened = card.generated, len(card.spent)
    try:
        fresh_session().advance(replay, root)
        outcome = "no error"
    except Exception as exc:
        outcome = f"{type(exc).__name__}: {str(exc)[:90]}"
    made_fresh = card.generated > before_generated
    reopened = len(card.spent) > before_opened
    print(f"replay: {outcome}", flush=True)
    print(f"        card made a fresh nonce: {made_fresh}   "
          f"reopened the old seal: {reopened}", flush=True)
    if reopened and not made_fresh:
        print("        UNSAFE: the same seal opened twice, which is two "
              "signatures under one secret nonce", flush=True)
    elif made_fresh:
        print("        safe: the card issued a new nonce rather than "
              "reopening the seal", flush=True)
    else:
        print("        safe: the card refused", flush=True)

print(f"final: generated={card.generated} opened={len(card.spent)}", flush=True)
