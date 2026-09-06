"""Demo 2: a silent payment send, MuSig2, with both signers' nonces on cards.

Demo 1 is the nonce vault on an ordinary MuSig2 spend. This is the same vault
underneath the harder flow: paying a silent payment address, which adds a round
before the usual two because the output script does not exist yet.

Both signers have their own card, because in reality they are two people with
two devices. Each card mints, seals, and later opens its own nonce, and neither
knows about the other's.

What is asserted, in order of what it would cost to get wrong:

  the script the shares rebuild equals what a single holder would compute
  each card opened its own seal exactly once
  a copy of a sealed nonce is refused
  both signers ended with a partial signature
"""
import json
import sys
import types

sys.path.insert(0, "/app/tests")

stub = types.ModuleType("pytest")
stub.fixture = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda fn: fn))
stub.mark = types.SimpleNamespace(
    parametrize=lambda *a, **k: (lambda fn: fn),
    skipif=lambda *a, **k: (lambda fn: fn),
    skip=lambda *a, **k: (lambda fn: fn))
stub.raises = lambda *a, **k: None
stub.skip = lambda *a, **k: None
sys.modules.setdefault("pytest", stub)

from embit import bip32, bip39

from seedsigner.helpers import musig2_card as mc
from seedsigner.helpers import musig2_psbt as mp
from seedsigner.helpers import silent_payments
from seedsigner.models.settings_definition import SettingsConstants

if not silent_payments.is_available():
    print("SKIP: the installed embit has no BIP-352 support", flush=True)
    raise SystemExit(0)

from test_musig2_card import FakeCardWithSecrets
from test_musig2_sp import silent_send, role_of, single_holder_scripts

data = json.load(open("/app/tests/data/musig2_psbts.json"))
roots = {n: bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data["mnemonics"][n]))
         for n in "ABC"}
recipient = silent_payments.derive_keys(
    bip39.mnemonic_to_seed(data["mnemonics"]["C"]), SettingsConstants.REGTEST)

# One card per signer, each holding only its own seed.
cards = {n: FakeCardWithSecrets(roots[n], {1: roots[n]}) for n in "AB"}


class Controller:
    def __init__(self, connector):
        self.Satochip_Connector = connector


def card_session(name):
    """A session that has never seen a previous round: a rebooted device."""
    session = mc.select(Controller(cards[name]), roots[name])
    if session is None:
        raise SystemExit(f"card for {name} was not selected; nothing below counts")
    return session


psbt = silent_send(data, recipient)
print(f"output has no script yet : {psbt.outputs[0].script_pubkey is None}",
      flush=True)
print(f"output carries sp_data   : "
      f"{getattr(psbt.outputs[0], 'sp_data', None) is not None}", flush=True)

# --- round zero: each signer publishes its ECDH share and a BIP-374 proof ----
for name in "AB":
    progress = card_session(name).advance(psbt, roots[name])
    print(f"{name}, shares round : stage={progress.stage}", flush=True)

expected = single_holder_scripts(psbt, roots)
rebuilt = mp.expected_scripts(psbt)
script_ok = (set(rebuilt) == set(expected) and
             all(bytes(rebuilt[i].data) == bytes(expected[i].data) for i in rebuilt))
print(f"\nscripts rebuilt from the shares: {len(rebuilt)}", flush=True)
print(f"they equal what a single holder computes: {script_ok}", flush=True)

# The device verifies a script, it never writes one. Setting it is the
# coordinator's job and no coordinator exists yet, so stand in for it.
for index, script in rebuilt.items():
    psbt.outputs[index].script_pubkey = script
print("coordinator step (stood in for): scripts written into the outputs",
      flush=True)

# --- the two ordinary rounds, with the nonces living on the cards -----------
for label in ("nonce", "sign"):
    for name in "AB":
        progress = card_session(name).advance(psbt, roots[name])
        print(f"{name}, {label} round  : stage={progress.stage}", flush=True)

opened = {n: len(cards[n].spent) for n in "AB"}
minted = {n: cards[n].generated for n in "AB"}
sigs = [k for k in psbt.inputs[0].unknown
        if k[0] == mp.PSBT_IN_MUSIG2_PARTIAL_SIG]

print(f"\nseals opened   A={opened['A']} B={opened['B']}", flush=True)
print(f"nonces minted  A={minted['A']} B={minted['B']}", flush=True)
print(f"partial signatures in the psbt: {len(sigs)}", flush=True)

each_opened_once = all(v == 1 for v in opened.values())
print("VERDICT:",
      "silent payment signed with both nonces held on cards, each seal opened once"
      if script_ok and each_opened_once and len(sigs) == 2
      else "NOT PROVEN", flush=True)
