"""BIP-375 cross-validation: macgyver13's published vectors against this fork's layers.

The vectors come from https://github.com/macgyver13/bip375-test-generator (the copy
carried by bip375-examples is an older v1.1 whose ECDH shares no longer verify, so it
must not be used). The file is vendored under tests/data/ and pinned by sha256: a
silent upstream edit changes the meaning of every row below, so it has to fail loudly
rather than quietly re-baseline.

Each vector is run through three layers and each layer's result is recorded, so a
verdict says WHERE the PSBT was accepted or refused:

  L1  SilentPaymentsPSBT.from_string  parsing and field-level structure (embit)
  L2  psbt.validate_sp()              BIP-375 structural validation (embit)
  L3  musig2_psbt.check_scripts()     this fork's final check, that every silent
                                      payment output pays exactly the script the
                                      verified ECDH shares derive

L3 is skipped, and recorded as n/a, when a silent payment output carries no
PSBT_OUT_SCRIPT: several of the "valid" vectors are deliberately unfinished PSBTs
where no final script exists yet, and asserting a final check against them would be
testing the wrong thing.

Rows this fork is known to get wrong are registered in KNOWN_GAPS as strict xfails,
keyed by vector description, so fixing one flips a named row instead of moving a count.

Run with --matrix=<path> to write the full pass/fail table as markdown.
"""
import hashlib
import json
import os

import pytest

from seedsigner.helpers import silent_payments


VECTORS_FILE = os.path.join(os.path.dirname(__file__), "data", "bip375_test_vectors.json")

# macgyver13/bip375-test-generator @ c4b4bd5, bip375_test_vectors.json v1.1.1.
VECTORS_VERSION = "1.1.1"
VECTORS_SHA256 = "7cb4ff1bdba1b34bc0f6ed7ccd8d4694146766fe16290ef579333a915eb6492e"
VECTORS_COUNTS = {"valid": 19, "invalid": 22}

requires_sp = pytest.mark.skipif(
    not silent_payments.is_available(),
    reason="installed embit has no BIP-352/375 support (needs embit#145)",
)


# Vectors this fork does not handle yet. One line each, so a later fix flips a
# named row. Both gaps live in musig2_psbt.expected_scripts and its helpers.
KNOWN_GAPS = {
    "can finalize: one P2PKH input single-signer":
        "_plain_input_share looks for the pubkey hash at the P2WPKH offset, so a "
        "P2PKH input never matches its BIP32 derivation",
    "can finalize: two inputs single-signer using global ECDH share":
        "expected_scripts reads only per-input PSBT_IN_SP_ECDH_SHARE, never the "
        "global PSBT_GLOBAL_SP_ECDH_SHARE (embit exposes it as psbt.sp_ecdh_shares)",
    "can finalize: two inputs / two sp outputs with mixed global and per-input ECDH shares":
        "same global-share gap: the global half of the mix is never read",
    "can finalize: three sp outputs (different scan keys) with multiple global ECDH shares":
        "same global-share gap, here with one global share per scan key",
    "can finalize: two inputs using global ECDH share - only eligible inputs contribute shares (P2SH excluded)":
        "same global-share gap, with an ineligible P2SH input alongside",
    "in progress: large PSBT with nine mixed inputs / six outputs - some inputs signed":
        "the P2PKH input and the P2SH-wrapped input both miss the pubkey lookup, "
        "which assumes a bare P2WPKH scriptPubKey",
}


def load_vectors():
    with open(VECTORS_FILE) as f:
        return json.load(f)


# The matrix rows, filled in as the vector tests run and written out by the
# module fixture below when --matrix is given.
MATRIX = []


def _short(exc):
    text = "%s: %s" % (type(exc).__name__, exc) if str(exc) else type(exc).__name__
    return " ".join(text.split())


def run_layers(psbt_b64):
    """{L1, L2, L3} for one vector: 'pass', 'fail: ...' or 'n/a: ...' per layer."""
    from embit.silent_payments.psbt import SilentPaymentsPSBT

    from seedsigner.helpers import musig2_psbt as mp

    result = {}
    try:
        psbt = SilentPaymentsPSBT.from_string(psbt_b64)
        result["L1"] = "pass"
    except Exception as exc:
        result["L1"] = "fail: " + _short(exc)
        result["L2"] = result["L3"] = "n/a: not parsed"
        return result

    try:
        psbt.validate_sp()
        result["L2"] = "pass"
    except Exception as exc:
        result["L2"] = "fail: " + _short(exc)

    sp_outputs = [out for out in psbt.outputs if getattr(out, "sp_data", None) is not None]
    if not sp_outputs:
        result["L3"] = "n/a: no silent payment output"
    elif any(out.script_pubkey is None for out in sp_outputs):
        # Unfinished on purpose: there is no declared script to check against.
        result["L3"] = "n/a: no PSBT_OUT_SCRIPT"
    else:
        try:
            mp.check_scripts(psbt)
            result["L3"] = "pass"
        except Exception as exc:
            result["L3"] = "fail: " + _short(exc)
    return result


def verdict_of(layers, expected):
    """('ok'|'MISMATCH', explanation). A vector is refused if any layer refuses it."""
    refused = [name for name in ("L1", "L2", "L3") if layers[name].startswith("fail")]
    if expected == "valid":
        if refused:
            return "MISMATCH", "should be accepted, refused at %s (%s)" % (
                refused[0], layers[refused[0]])
        return "ok", "accepted"
    if not refused:
        return "MISMATCH", "should be refused, every layer accepted it"
    return "ok", "refused at " + refused[0]


def vector_cases():
    data = load_vectors()
    cases = []
    for expected in ("valid", "invalid"):
        for vector in data[expected]:
            reason = KNOWN_GAPS.get(vector["description"])
            marks = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
            cases.append(pytest.param(vector, expected, id=vector["description"], marks=marks))
    return cases


def test_vector_file_matches_pinned_upstream_release():
    """The vendored file is exactly the release every row below was judged against."""
    with open(VECTORS_FILE, "rb") as f:
        raw = f.read()
    assert hashlib.sha256(raw).hexdigest() == VECTORS_SHA256, (
        "tests/data/bip375_test_vectors.json changed; re-run the matrix and update "
        "VECTORS_SHA256, VECTORS_VERSION and KNOWN_GAPS deliberately")
    data = json.loads(raw)
    assert data["version"] == VECTORS_VERSION
    assert {key: len(data[key]) for key in VECTORS_COUNTS} == VECTORS_COUNTS


@requires_sp
@pytest.mark.parametrize("vector, expected", vector_cases())
def test_bip375_vector(vector, expected):
    layers = run_layers(vector["psbt"])
    verdict, explanation = verdict_of(layers, expected)
    MATRIX.append(dict(description=vector["description"], expected=expected,
                       known_gap=vector["description"] in KNOWN_GAPS, verdict=verdict,
                       explanation=explanation, **layers))
    assert verdict == "ok", explanation


def render_matrix(rows):
    def cell(text, width=88):
        text = text.replace("|", "/")
        return text if len(text) <= width else text[:width - 3] + "..."

    lines = ["# BIP-375 vector matrix",
             "",
             "Vectors: macgyver13/bip375-test-generator v%s (sha256 %s...)" % (
                 VECTORS_VERSION, VECTORS_SHA256[:16]),
             "L1 = SilentPaymentsPSBT.from_string, L2 = validate_sp(), "
             "L3 = musig2_psbt.check_scripts()",
             "",
             "| description | expected | L1 | L2 | L3 | verdict |",
             "| --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        if row["known_gap"]:
            verdict = "known gap"
        elif row["verdict"] != "ok":
            verdict = "MISMATCH: " + row["explanation"]
        elif row["expected"] == "invalid":
            verdict = "ok (%s)" % row["explanation"]
        else:
            verdict = "ok"
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            row["description"].replace("|", "/"), row["expected"], cell(row["L1"]),
            cell(row["L2"]), cell(row["L3"]), cell(verdict)))
    matched = [r for r in rows if r["verdict"] == "ok"]
    gaps = [r for r in rows if r["verdict"] != "ok" and r["known_gap"]]
    broken = [r for r in rows if r["verdict"] != "ok" and not r["known_gap"]]
    lines += ["",
              "%d of %d rows match the vector's expectation, %d are registered known gaps, "
              "%d are unexplained." % (len(matched), len(rows), len(gaps), len(broken))]
    if gaps:
        lines += ["", "## Known gaps"]
        for row in gaps:
            lines.append("- %s: %s" % (row["description"], KNOWN_GAPS[row["description"]]))
    return "\n".join(lines) + "\n"


@pytest.fixture(scope="module", autouse=True)
def write_matrix(request):
    yield
    path = request.config.getoption("--matrix", default=None)
    if path and MATRIX:
        with open(path, "w") as f:
            f.write(render_matrix(MATRIX))
