"""Demo 1 on the real applet: the nonce vault, both rounds, then a replay."""

# Run with PYTHONPATH=<this dir>:<seedsigner-sp/src> and JCARDSIM_JAR, APPLET_SRC,
# JAVA_HOME set. See README.md.
import json, sys
from embit import bip32, bip39
from embit.psbt import PSBT
from provision import connect
from seedsigner.helpers import musig2_card as mc, musig2_psbt as mp

sys.path.insert(0, "/home/rob/apps/seedsigner-sp/tests")
from test_musig2_psbt import without_other_nonces, role_of, core_nonce

data = json.load(open('/home/rob/apps/seedsigner-sp/tests/data/musig2_psbts.json'))
root = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(data['mnemonics']['A']))
cc = connect(bip39.mnemonic_to_seed(data['mnemonics']['A']))

class Ctl: Satochip_Connector = cc
def fresh():
    s = mc.select(Ctl(), root)
    assert s is not None, "card not selected"
    return s

psbt = without_other_nonces(data["psbt_round_one"])
p1 = fresh().advance(psbt, root)
round_one = psbt.to_string()
print(f"round 1: stage={p1.stage}", flush=True)

# power off, then round two on a session that never saw round one
psbt2 = PSBT.from_string(round_one)
role = role_of(psbt2, root)
other, nonce = core_nonce(data, role)
psbt2.inputs[0].unknown[mp._key(mp.PSBT_IN_MUSIG2_PUB_NONCE, role, other)] = nonce
p2 = fresh().advance(psbt2, root)
sigs = [k for k in psbt2.inputs[0].unknown if k[0] == mp.PSBT_IN_MUSIG2_PARTIAL_SIG]
print(f"round 2: stage={p2.stage}  partial signatures={len(sigs)}", flush=True)

# a copy of the sealed nonce, replayed
replay = PSBT.from_string(round_one)
replay.inputs[0].unknown[mp._key(mp.PSBT_IN_MUSIG2_PUB_NONCE, role, other)] = nonce
try:
    fresh().advance(replay, root)
    print("replay: ACCEPTED", flush=True)
except Exception as exc:
    print(f"replay refused by the applet: {type(exc).__name__}: {str(exc)[:70]}", flush=True)
