"""
    BIP-375 shares on a send this device did not build: which key an input's share is
    checked against.

    The transactions here are assembled from scratch rather than recorded, because what
    is being tested is the shape of the input, not any particular coin: BIP-352 accepts
    P2PKH, P2WPKH, P2SH-P2WPKH and P2TR, and each commits to its key differently, so a
    single-shape fixture proves nothing about the other three.

    The oracle is embit's own BIP-352 sender, `derive_sp_outputs`, holding every input's
    private key - the position a device is never in, which is the whole reason the shares
    and their proofs exist.

    `tests/test_bip375_vectors.py` runs macgyver13's published vectors end to end; this
    file is the unit-level statement of the same rule.
"""
import os

import pytest
from embit import ec, script
from embit.psbt import DerivationPath
from embit.transaction import Transaction, TransactionInput, TransactionOutput

from seedsigner.helpers import musig2_psbt as mp
from seedsigner.helpers import silent_payments

pytestmark = pytest.mark.skipif(not silent_payments.is_available(),
                                reason="installed embit has no BIP-352 support")


SCAN = ec.PrivateKey(bytes(31) + b"\x33")
SPEND = ec.PrivateKey(bytes(31) + b"\x34")


def _key(i: int) -> ec.PrivateKey:
    return ec.PrivateKey(bytes(31) + bytes([i + 1]))


def _input(priv, kind: str, index: int):
    """One eligible input of the given BIP-352 shape, spending a coin that pays it."""
    from embit.silent_payments.psbt import SPInputScope

    pub = priv.get_public_key()
    redeem = None
    if kind == "p2pkh":
        spk = script.p2pkh(pub)
    elif kind == "p2wpkh":
        spk = script.p2wpkh(pub)
    elif kind == "p2sh-p2wpkh":
        redeem = script.p2wpkh(pub)
        spk = script.p2sh(redeem)
    else:
        raise ValueError(kind)

    scope = SPInputScope(vin=TransactionInput(bytes([index + 100]) * 32, 0, sequence=0xFFFFFFFD))
    if kind == "p2pkh":
        # Legacy: only the whole previous transaction proves what the coin pays.
        prev = Transaction(vin=[TransactionInput(bytes(32), 0)],
                           vout=[TransactionOutput(100000, spk)])
        scope.non_witness_utxo = prev
        scope.txid, scope.vout = prev.txid(), 0
    else:
        scope.witness_utxo = TransactionOutput(100000, spk)
    scope.redeem_script = redeem
    scope.bip32_derivations[pub] = DerivationPath(b"\x00\x00\x00\x00", [0])
    return scope


def _send(kinds):
    """(psbt, private keys) for a send of one silent payment output, shares not written."""
    from embit.silent_payments.psbt import (SilentPaymentData, SilentPaymentsPSBT,
                                            SPOutputScope)

    privs = [_key(i) for i in range(len(kinds))]
    psbt = SilentPaymentsPSBT.create_v2(tx_version=2, fallback_locktime=0)
    for i, (priv, kind) in enumerate(zip(privs, kinds)):
        psbt.add_input(_input(priv, kind, i))
    out = SPOutputScope()
    out.value = 90000 * len(kinds)
    out.sp_data = SilentPaymentData(SCAN.get_public_key(), SPEND.get_public_key())
    psbt.add_output(out)
    # BIP-375 refuses a transaction whose inputs or outputs may still change.
    psbt.tx_modifiable_flags = 0
    return psbt, privs


def _oracle(psbt, privs):
    """{output index: script} as BIP-352's sender computes it holding every key."""
    from embit.script import Script
    from embit.silent_payments.sp import derive_sp_outputs, group_sp_outputs_by_scan_key

    groups, indices = group_sp_outputs_by_scan_key(psbt.outputs)
    _, _, results = derive_sp_outputs([priv.secret for priv in privs],
                                      [inp.vin for inp in psbt.inputs], groups)
    return {idx: bytes(Script(b"\x51\x20" + outs[pos]).data)
            for scan_key, (_, outs) in results.items()
            for pos, idx in enumerate(indices[scan_key])}


def _scan_key() -> bytes:
    return SCAN.get_public_key().sec()


def _write_input_shares(psbt, privs):
    from embit.silent_payments.dleq import generate_dleq_proof
    from embit.silent_payments.sp import _tweak_mul

    scan_key = _scan_key()
    for scope, priv in zip(psbt.inputs, privs):
        scope.unknown[bytes([mp.PSBT_IN_SP_ECDH_SHARE]) + scan_key] = \
            _tweak_mul(scan_key, priv.secret)
        scope.unknown[bytes([mp.PSBT_IN_SP_DLEQ]) + scan_key] = \
            generate_dleq_proof(priv.secret, scan_key, r=os.urandom(32))


def _scripts(psbt):
    return {idx: bytes(s.data) for idx, s in mp.expected_scripts(psbt).items()}


def _reparse(psbt):
    from embit.silent_payments.psbt import SilentPaymentsPSBT
    return SilentPaymentsPSBT.parse(psbt.serialize())


# --- the key an input's share is checked against ---------------------------------------

@pytest.mark.parametrize("kind", ["p2pkh", "p2wpkh", "p2sh-p2wpkh"])
def test_every_eligible_input_shape_finds_its_own_key(kind):
    """Each shape hides the key somewhere else, and BIP-352 accepts all of them."""
    psbt, privs = _send([kind])
    _write_input_shares(psbt, privs)
    assert _scripts(_reparse(psbt)) == _oracle(psbt, privs)


def test_shapes_mixed_in_one_transaction_all_contribute():
    psbt, privs = _send(["p2pkh", "p2sh-p2wpkh", "p2wpkh"])
    _write_input_shares(psbt, privs)
    assert _scripts(_reparse(psbt)) == _oracle(psbt, privs)


def test_a_wrapped_input_takes_its_key_from_the_redeem_script():
    """P2SH-P2WPKH: the scriptPubKey hashes the redeem script, not the key."""
    psbt, privs = _send(["p2sh-p2wpkh"])
    scope = psbt.inputs[0]
    assert mp._input_pubkey(scope, 0) == privs[0].get_public_key().sec()
    # The bytes the old offset would have read are the P2SH hash, not the key's.
    assert bytes(scope.script_pubkey.data[2:22]) != \
        bytes(scope.redeem_script.data[2:22])


def test_a_redeem_script_that_does_not_hash_to_the_coin_is_refused():
    """The redeem script is the PSBT's word; only the scriptPubKey is the coin's."""
    psbt, _ = _send(["p2sh-p2wpkh"])
    psbt.inputs[0].redeem_script = script.p2wpkh(_key(9).get_public_key())
    with pytest.raises(mp.Musig2Error):
        mp._input_pubkey(psbt.inputs[0], 0)


def test_an_input_with_no_derivation_for_its_key_is_refused():
    """Nothing else in the PSBT says which key a hash-committing input spends."""
    psbt, privs = _send(["p2pkh"])
    _write_input_shares(psbt, privs)
    psbt.inputs[0].bip32_derivations.clear()
    with pytest.raises(mp.Musig2Error):
        mp.expected_scripts(psbt)


def test_a_taproot_input_still_uses_the_output_key_itself():
    """P2TR commits to the key, so there is no hash to look behind."""
    psbt, _ = _send(["p2wpkh"])
    xonly = bytes(range(32))
    psbt.inputs[0].witness_utxo = TransactionOutput(100000, script.Script(b"\x51\x20" + xonly))
    assert mp._input_pubkey(psbt.inputs[0], 0) == b"\x02" + xonly
