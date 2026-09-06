"""MuSig2 paying a silent payment address, driven on the Virtual HAT.

This is the one path the rig had never touched. An ordinary MuSig2 spend has two
rounds; paying a silent payment address adds one before them, because the output
script does not exist yet. Each signer first publishes d_i*B_scan with a BIP-374
proof of it, the shares are summed to rebuild what a single holder would have
computed, and only then does the script exist to be signed over.

The rounds are driven directly rather than through the screens, because what is
being checked here is the extra round and the script it produces. The screens of
this flow are captured separately by flow_walk.py.

Nothing here asserts anything a counter could fake: the check is that the script
the shares rebuild is the same script a single holder computes with the whole
private key in hand. If the shares are wrong, that equality fails.
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

from seedsigner.helpers import musig2_psbt as mp
from seedsigner.helpers import silent_payments
from seedsigner.models.settings_definition import SettingsConstants

if not silent_payments.is_available():
    print("SKIP: the installed embit has no BIP-352 support", flush=True)
    raise SystemExit(0)

from test_musig2_sp import silent_send, role_of, single_holder_scripts

data = json.load(open("/app/tests/data/musig2_psbts.json"))
roots = {n: bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data["mnemonics"][n]))
         for n in "ABC"}
recipient = silent_payments.derive_keys(
    bip39.mnemonic_to_seed(data["mnemonics"]["C"]), SettingsConstants.REGTEST)

psbt = silent_send(data, recipient)
out = psbt.outputs[0]
print(f"output has no script yet: {out.script_pubkey is None}", flush=True)
print(f"output carries sp_data  : {getattr(out, 'sp_data', None) is not None}",
      flush=True)

# Round zero: each signer publishes its share of the ECDH secret plus a proof.
sessions = {name: mp.Session() for name in "AB"}
first = sessions["A"].advance(psbt, roots["A"])
print(f"\nA, round zero : stage={first.stage}", flush=True)
second = sessions["B"].advance(psbt, roots["B"])
print(f"B, round zero : stage={second.stage}", flush=True)

# With both shares present the script can be rebuilt. This is the assertion that
# carries the whole path: it must equal what one holder of the aggregate key
# would have computed on their own.
expected = single_holder_scripts(psbt, roots)
rebuilt = mp.expected_scripts(psbt)
matches = (set(rebuilt) == set(expected) and
           all(bytes(rebuilt[i].data) == bytes(expected[i].data) for i in rebuilt))
print(f"\nscripts rebuilt from the shares: {len(rebuilt)}", flush=True)
print(f"they equal what a single holder computes: {matches}", flush=True)

# The device does not write the script into the psbt; it only verifies one that
# is already there (check_scripts). Setting it is the coordinator's job, and no
# coordinator exists yet, so stand in for it here. This is the seam where the
# rig stops and a real coordinator would begin.
for index, script in rebuilt.items():
    psbt.outputs[index].script_pubkey = script
print("coordinator step (stood in for): scripts written into the outputs",
      flush=True)

# Then the ordinary two rounds, now that there is a script to sign over.
for name in "AB":
    progress = sessions[name].advance(psbt, roots[name])
    print(f"{name}, next round : stage={progress.stage}", flush=True)
for name in "AB":
    progress = sessions[name].advance(psbt, roots[name])
    print(f"{name}, final round: stage={progress.stage}", flush=True)

signed = psbt.outputs[0].script_pubkey is not None
sigs = [k for k in psbt.inputs[0].unknown
        if k[0] == mp.PSBT_IN_MUSIG2_PARTIAL_SIG]
print(f"\noutput now has a script: {signed}", flush=True)
print(f"partial signatures in the psbt: {len(sigs)}", flush=True)
print("VERDICT:",
      "the silent payment path completed: shares rebuilt the right script and "
      f"{len(sigs)} of 2 signers signed over it"
      if matches and signed and sigs else "NOT PROVEN", flush=True)
