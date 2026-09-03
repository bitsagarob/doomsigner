<h1 align="center">DoomSigner</h1>

<p align="center">
  <em>A proof-of-concept SeedSigner for BIP-352 silent payments. It also boots into DOOM.</em>
</p>

**This is a proof of concept, not a product.** It exists to answer one question:
can an airgapped signing device handle silent payments end to end? No released
hardware wallet can, and this is an attempt at the parts that are missing.

The DOOM easter egg came first and is still here. It is no longer the point.

**Try it in a browser**, no hardware and no SD card:
<https://bitsaga.be/seedsigner-simulator/>. That runs the real firmware under
WebAssembly, and the DOOM it boots is this repository's own port compiled to
wasm, drawing the same pixels the panel would be sent.

---

## What is new here

### BIP-352 silent payments

The signing application is built from **[our own fork](https://github.com/bitsagarob/seedsigner)**
(branch `dev`), not from upstream. It adds:

| | |
| --- | --- |
| **Show a payment address** | `Seeds > (a seed) > Silent payments > Show address`. The `sp1…` / `tsp1…` string and a QR. Derivation is BIP-352 and matches [SeedSigner#769](https://github.com/SeedSigner/seedsigner/pull/769), checked against that thread's published test vectors |
| **Connect to Sparrow** | A privacy warning, the address to check against, then the `spscan…` watch key a coordinator imports. That key detects every payment the seed will ever receive and can spend none of them, so it is deliberately never shown as text |
| **Spend a received payment** | A BIP-352 output is already a tweaked key, so signing it needs `(b_spend + tweak)` forced to even Y, not BIP-341 TapTweak. Ports the hooks from [SeedSigner#949](https://github.com/SeedSigner/seedsigner/pull/949) |
| **Send to a silent payment address** | BIP-375 PSBTv2: the device ECDH-derives the output, signs, and returns ECDH shares plus DLEQ proofs for the coordinator to finalise |
| **Sparrow 2.5+ PSBTs** | Sparrow writes the tweak as `PSBT_IN_SP_TWEAK` and the spend path in a v2-only field. Both are normalised on ingest so the stock parser sees them |

Cryptography comes from **[embit#145](https://github.com/diybitcoinhardware/embit/pull/145)**
(notTanveer), pinned by commit in `requirements.txt` rather than vendored.

**Proven on chain, not just in tests.** Signet: send
[`71fb9116…`](https://signet.bitsaga.be/api/tx-proof?txid=71fb91163c8723b9e2ffe7c53c2981258c736ae18338d69a9cd35a215ffc7fdf)
then spend
[`8569ad81…`](https://signet.bitsaga.be/api/tx-proof?txid=8569ad815dfe481f1aa2e4881febdbfed5890f566f9f63a92e9a90681899b29a).
Mainnet, a real 10,000 sats to an `sp1` address:
[`17270576…`](https://mempool.space/tx/172705760a51fa109b4aeef6f8bfbfde177a46c50d035abdd508b3d430b7c1ed),
block 965081.

### Telling the device what time it is

A silent payment output appears nowhere else on chain, so there is no address a
human can compare. Validating a **BIP-353** name is the only check that exists,
and that needs DNSSEC, which needs a clock. This device has no RTC.

ShieldSigner already solved the transport in
[3rdIteration#143](https://github.com/3rdIteration/seedsigner/pull/143): scan a
GoPro Labs precision-time QR and it sets the system clock. So
**<https://silentpayments.net/timecode>** draws one, and this image reads it with
no change at all. Scan it **off a second device**, never off the machine that
built the transaction, or one attacker supplies both the proof and the date that
makes it look valid.

On-device proof validation itself is **not implemented yet**. It is blocked on
[embit#102](https://github.com/diybitcoinhardware/embit/pull/102) (alvroble),
which needs a pure-Python DNSSEC validator; ours is offered at
[pydnssec-prover#2](https://github.com/alvroble/pydnssec-prover/pull/2), with
[review notes on #102](https://github.com/diybitcoinhardware/embit/pull/102#issuecomment-5517572376).
[SeedSigner#798](https://github.com/SeedSigner/seedsigner/pull/798) (Bicaru20) is
the view layer waiting on the same thing.

Related: the Security Considerations section BIP-353 lacked, now proposed as
[bitcoin/bips#2272](https://github.com/bitcoin/bips/pull/2272).

### DOOM, and the game chooser

The device boots into a chooser with **Snake** and **DOOM**, not straight into
DOOM. Snake runs in-process; DOOM is a native binary and replaces the process.

---

## Switching between the game and the wallet

The device and the browser simulator use **different sequences**. That is a
divergence, not a design, and it should be reconciled.

| Where | To the wallet | Back to the game |
| --- | --- | --- |
| **Real device** | Press **KEY1, KEY2, KEY3** — the three side buttons, top to bottom, in order | **Not possible. Reboot.** |
| **Browser simulator** (`?firmware=doomsigner`) | **Five taps** on the top side button (KEY1) | **Five more taps** |

On the device the sequence works in the chooser, inside Snake, and inside DOOM,
which reimplements the same three-key detector in C (`boot-game/doom/src/dg_seedsigner.c`)
because by then the Python is gone. Every path is `os.execv`/`execv`: the game is
**replaced**, not backgrounded, so no game code is in memory while the wallet holds
your keys. That is also why there is no way back without a reboot.

None of the three keys steer, so the sequence cannot be spelled by ordinary play.

---

## What this is not

It is not a security product, it is not audited, and it is not a SeedSigner
release.

**The signing application is modified.** Earlier versions of this file said it
was not, and that stopped being true when the build was pointed at our fork.
Two consequences, both deliberate:

- **This image will not reproduce an upstream SeedSigner release hash.** It is
  not meant to. `docs/building.md` still describes upstream's reproducible-build
  check, which applies to upstream images, not to this one.
- **Everything under "silent payments" above is unreviewed by anyone.** The
  upstream pull requests it builds on are all open and unmerged.

Use a real SeedSigner release for anything holding real bitcoin.

## Where things are

| Path | What |
| --- | --- |
| `boot-game/` | The chooser, the unlock sequence and the handoff |
| `boot-game/doom/` | The doomgeneric port for the panel, plus its WebAssembly and device builds |
| `opt/` | SeedSigner OS itself, from upstream |
| `opt/build.sh` | Defaults to our app fork. `--app-repo` / `--app-branch` override |
| `opt/rootfs-overlay/start.sh` | The one line that launches the chooser instead of the wallet |

The guard on that line is deliberate:

```sh
PYTHONPATH=/usr/local/bootgame /usr/bin/python3 -m bootgame.boot ||
    /usr/bin/python3 main.py
```

If the game cannot start, the wallet starts anyway. An earlier image shipped with
the game staged nowhere and booted to a black screen, because that line was the
only thing launching anything. A signing device has to come up whatever the easter
egg does.

---

Everything below this line is upstream's own README, kept as it was, and it is
still how the images are built.

---

<p align="center">
  <a href="https://seedsigner.com/">
    <img alt="Gitea" src="docs/img/logo.png" width="90"/>
  </a>
</p>
<h1 align="center">SeedSigner OS</h1>

<p align="center">
  <a href="https://opensource.org/licenses/MIT" title="License: MIT">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg">
  </a>
  <a href="" title="Twitter">
  <img src="https://img.shields.io/twitter/follow/seedsigner?style=social">
  </a>
</p>

* [Overview](#overview)
* [Building](docs/building.md)
* [Building (without Docker)](docs/without_docker.md)
* [SeedSigner OS structure](docs/structure.md)
* [Dev workflow](docs/dev_workflow.md)
* [Customizing Buildroot](docs/customize_buildroot.md)

<br/>

JUMP STRAIGHT TO: [🔥🔥🔥🛠 Quickstart: SeedSigner Reproducible Build! 🛠🔥🔥🔥](docs/building.md)

<br/>

---

# Overview

A custom linux based operating system built to manage software running on airgapped Bitcoin signing device. SeedSigner is both the project name and [application](http://github.com/SeedSigner/seedsigner/) running on airgapped hardware. This custom operating system, like all operating systems, manages the hardware resources and provides them to the application code. It's currently designed to run on common Raspberry Pi hardware with [accessories](https://github.com/SeedSigner/seedsigner/#shopping-list). The goal of SeedSigner OS is to provide an easy, fast, and secure way to build microSD card image to securely run [SeedSigner](https://seedsigner.com) code.


## ⚙️ Under the Hood

SeedSigner OS is built using [Buildroot](https://www.buildroot.org). Buildroot is a simple, efficient and easy-to-use tool to generate embedded Linux systems through cross-compilation. SeedSigner OS does not fork Buildroot, but uses Buildroot with custom configurations to build microSD card images tailor made for running SeedSigner.


## 🛂 Security

SeedSigner OS is built to reduce the attack surface area and enable additional application functionality. The OS is an order of magnitude smaller in size than Raspberry Pi OS (which is what typically is used to run software on a Pi device). Here are a list of some security and functional advantages of using SeedSigner OS.

- Boots 100% from RAM. This means, once you see the SeedSigner splash screen, you can remove the microSD card because no disk I/O is needed after boot!
- One FAT32 partition on the microSD card
- Removes these standard Raspberry Pi OS Kernel modules:
   - Networking and Bluetooth
   - SWAP
   - I2C
   - Serial
   - USB
   - Pulse-Width Modulation (PWM)
- NO HDMI support
- NO Serial connection TTL support
- NO Software supporting any wireless or networking chips
- A single read only zImage file on the boot partition containing the entire Linux kernel and filesystem


