"""Bring a fresh jCardSim SeedKeeper up to the state the wallet expects.

A card out of the factory has no PIN and holds nothing. The nonce vault needs
one that is set up, unlocked, and carrying the master seed the signer is going
to sign with, because the card mints nonces from a key it derives itself.

Everything here goes through pysatochip's own API rather than raw APDUs. That is
deliberate: the point of putting the seam at pyscard is that pysatochip runs for
real, so provisioning should exercise it too rather than reach past it.

    from provision import connect
    connector = connect(seed_bytes)
"""
import logging

logging.getLogger("pysatochip").setLevel(logging.ERROR)

PIN = "123456"


def connect(seed_bytes, label="rig seed"):
    """A connector talking to a set-up, unlocked card holding this master seed."""
    from pysatochip.CardConnector import CardConnector
    from smartcard import simulated_card

    # A fresh applet per call: two signers are two cards that share nothing.
    simulated_card.new_card()
    connector = CardConnector(card_filter=["seedkeeper"])
    # CardConnector establishes the card in a background thread.
    import time
    for _ in range(50):
        if getattr(connector, "card_present", False) or connector.cardservice:
            break
        time.sleep(0.1)

    pin = list(PIN.encode("utf-8"))
    connector.card_setup(
        0x05, 0x01, pin, pin,          # pin tries, unblock tries, pin, unblock
        0x05, 0x01, pin, pin,
        0x0000, 0x0000,                # memsize, memsize2
        0x01, 0x01, 0x01,              # create object / key / pin ACL
    )
    connector.set_pin(0, pin)
    connector.card_verify_PIN()

    header = connector.make_header("Masterseed", "Plaintext export allowed", label)
    secret_list = [len(seed_bytes)] + list(seed_bytes)
    connector.seedkeeper_import_secret({"header": header, "secret_list": secret_list})
    return connector
