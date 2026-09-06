"""Demo 2 on the real applet: a silent payment send, MuSig2, a card per signer."""

# Run with PYTHONPATH=<this dir>:<seedsigner-sp/src> and JCARDSIM_JAR, APPLET_SRC,
# JAVA_HOME set. See README.md.
import json, sys
from embit import bip32, bip39
from provision import connect
from seedsigner.helpers import musig2_card as mc, musig2_psbt as mp
from seedsigner.helpers import silent_payments
from seedsigner.models.settings_definition import SettingsConstants

sys.path.insert(0, "/home/rob/apps/seedsigner-sp/tests")
from test_musig2_sp import silent_send, role_of, single_holder_scripts

data = json.load(open('/home/rob/apps/seedsigner-sp/tests/data/musig2_psbts.json'))
roots = {n: bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data['mnemonics'][n]))
         for n in "ABC"}
recipient = silent_payments.derive_keys(
    bip39.mnemonic_to_seed(data['mnemonics']['C']), SettingsConstants.REGTEST)

# One real applet per signer.
connectors = {n: connect(bip39.mnemonic_to_seed(data['mnemonics'][n]), f"seed {n}")
              for n in "AB"}
print("two applets provisioned, one per signer", flush=True)

def session(name):
    class Ctl: Satochip_Connector = connectors[name]
    s = mc.select(Ctl(), roots[name])
    assert s is not None, f"card for {name} not selected"
    return s

psbt = silent_send(data, recipient)
print(f"output has no script yet: {psbt.outputs[0].script_pubkey is None}", flush=True)

for name in "AB":
    print(f"{name}, shares round: stage={session(name).advance(psbt, roots[name]).stage}",
          flush=True)

expected = single_holder_scripts(psbt, roots)
rebuilt = mp.expected_scripts(psbt)
ok = (set(rebuilt) == set(expected) and
      all(bytes(rebuilt[i].data) == bytes(expected[i].data) for i in rebuilt))
print(f"shares rebuild the single-holder script: {ok}", flush=True)
for index, script in rebuilt.items():
    psbt.outputs[index].script_pubkey = script

for label in ("nonce", "sign"):
    for name in "AB":
        print(f"{name}, {label} round: stage={session(name).advance(psbt, roots[name]).stage}",
              flush=True)

sigs = [k for k in psbt.inputs[0].unknown if k[0] == mp.PSBT_IN_MUSIG2_PARTIAL_SIG]
print(f"partial signatures: {len(sigs)}", flush=True)
print("VERDICT:", "silent payment signed, both nonces from real applets"
      if ok and len(sigs) == 2 else "NOT PROVEN", flush=True)
