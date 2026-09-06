"""The real SeedKeeper applet, running in jCardSim, behind pyscard's surface.

The browser simulator answers APDUs with cards written in Python. This answers
them with the applet's own Java, running on a JavaCard runtime through
AppletPipe, so what is being tested is the code that gets flashed rather than a
description of it.

Everything above this file is unchanged from the browser simulator's package:
the same pyscard-shaped surface, so the whole of pysatochip and the whole of
SeedSigner run unmodified and unaware. That is the point of putting the seam
here rather than at the wallet's own card calls -- one seam, three backends:

    browser      pyscard surface -> cards written in Python
    this rig     pyscard surface -> the real applet in jCardSim
    a device     real pyscard    -> the card in your hand

Needs JCARDSIM_JAR and APPLET_SRC in the environment, and a JDK 8 to have
compiled AppletPipe against. Raises rather than falling back to anything
simpler: a card double that quietly stands in for the real applet is exactly
the failure this exists to remove.
"""
import atexit
import os
import subprocess

JAVACARD_ATR = [0x3B, 0xFA, 0x18, 0x00, 0x00, 0x81, 0x31, 0xFE, 0x45,
                0x4A, 0x43, 0x4F, 0x50, 0x34, 0x76, 0x32, 0x34, 0x31, 0xB7]


class NoCardException(Exception):
    pass


class CardConnectionException(Exception):
    pass


class _Applet:
    """One live applet instance in jCardSim, spoken to one APDU at a time."""

    def __init__(self):
        jar = os.environ["JCARDSIM_JAR"]
        src = os.environ["APPLET_SRC"]
        java = os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-8-openjdk-amd64")
        self.proc = subprocess.Popen(
            [f"{java}/bin/java", "-cp", f"{jar}:{src}/test/classes", "AppletPipe"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1)
        atexit.register(self.close)

    def transmit(self, apdu):
        self.proc.stdin.write(bytes(apdu).hex() + "\n")
        self.proc.stdin.flush()
        # The runtime writes its own chatter to stdout, so responses are prefixed.
        line = self.proc.stdout.readline()
        while line and not line.startswith("R:"):
            line = self.proc.stdout.readline()
        if not line:
            raise CardConnectionException("the applet stopped answering")
        answer = bytes.fromhex(line[2:].strip())
        return list(answer)

    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()


_card = None
_live = []


def current_card():
    global _card
    if _card is None:
        _card = _Applet()
    return _card


def new_card():
    """Start a fresh applet instance and make it the card in the reader.

    Two signers are two people with two cards, and a MuSig2 nonce is worthless
    if both sides mint from the same one. Each call spawns its own jCardSim
    process, so the cards share nothing.
    """
    # The previous applet is left running on purpose. A connection binds to the
    # card that was current when it was made, so closing the old one here would
    # kill the first signer's card the moment the second was provisioned.
    global _card
    _card = _Applet()
    _live.append(_card)
    return _card


def poll():
    return None


def wait_for_card(timeout):
    return current_card()


class SimulatedCardConnection:
    """pyscard's CardConnection: connect, transmit, disconnect."""

    def __init__(self, card=None):
        self.card = card if card is not None else current_card()
        self.observers = []

    def connect(self, *args, **kwargs):
        if self.card is None:
            raise NoCardException("no card in the reader")
        return self

    def disconnect(self):
        return None

    def addObserver(self, observer):
        self.observers.append(observer)

    def deleteObserver(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def getReader(self):
        return SimulatedReader.name

    def getATR(self):
        return list(JAVACARD_ATR)

    def transmit(self, apdu, protocol=None):
        answer = self.card.transmit(list(apdu))
        return answer[:-2], answer[-2], answer[-1]


class SimulatedCardService:
    """What pyscard hands to observers and returns from waitforcard()."""

    def __init__(self, card=None):
        self.card = card if card is not None else current_card()
        self.atr = list(JAVACARD_ATR)
        self.connection = None

    def createConnection(self):
        return SimulatedCardConnection(self.card)


class SimulatedReader:
    name = "jCardSim running the real SeedKeeper applet"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def createConnection(self):
        return SimulatedCardConnection()


def card_service():
    return SimulatedCardService(current_card())


# --- the monitor surface the package's CardMonitoring expects ----------------
# jCardSim's applet is always present: there is no tray to take it out of, so a
# monitor is told once that a card is there and never told otherwise.
_monitors = []


def register_monitor(monitor):
    if monitor not in _monitors:
        _monitors.append(monitor)


def unregister_monitor(monitor):
    if monitor in _monitors:
        _monitors.remove(monitor)


def announce_present(monitor=None, observer=None):
    """Tell one observer, or every registered one, that the card is present."""
    targets = [monitor] if monitor is not None else list(_monitors)
    service = card_service()
    for target in targets:
        watchers = [observer] if observer is not None else list(
            getattr(target, "observers", []))
        for watcher in watchers:
            watcher.update(target, ([service], []))
