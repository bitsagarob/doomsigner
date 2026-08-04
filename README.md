<h1 align="center">DoomSigner</h1>

<p align="center">
  <em>A SeedSigner that boots into DOOM.</em>
</p>

**Press KEY1, KEY2, KEY3 and it hands you the wallet.**

This is a fork of SeedSigner OS, made for fun. The device comes up running DOOM
on its 320x240 panel; the three side buttons, in order, stop the game and start
the signing application. The handoff is an `os.execv`, so the game is *replaced*
rather than backgrounded: no game code is left in memory while the wallet has
your keys.

**Play it in a browser**, no hardware and no SD card:
<https://bitsaga.be/seedsigner-simulator/>. That runs the real firmware under
WebAssembly, and the DOOM it boots is this repository's own port compiled to
wasm, drawing the same pixels the panel would be sent.

## What this is not

It is not a security product, it is not audited, and it is not a SeedSigner
release. **The wallet underneath is unmodified**: it is still cloned from
upstream at build time, and nothing here patches it. What this fork changes is
one line of `opt/rootfs-overlay/start.sh`, which launches the boot game instead
of launching the wallet directly, plus the `boot-game/` package that line runs.

That line is guarded, and deliberately:

```sh
PYTHONPATH=/usr/local/bootgame /usr/bin/python3 -m bootgame.boot ||
    /usr/bin/python3 main.py
```

If the game cannot start, the wallet starts anyway. An earlier image shipped
with the game staged nowhere and the device booted to a black screen, because
that line was the only thing launching anything. A signing device has to come up
whatever the easter egg does.

Use a real SeedSigner release for anything holding real bitcoin. Use this
because a signing device running DOOM is funny.

## Where things are

| Path | What |
| --- | --- |
| `boot-game/` | The boot game, the unlock sequence and the handoff |
| `boot-game/doom/` | The doomgeneric port for the panel, and its WebAssembly build |
| `opt/` | SeedSigner OS itself, from upstream |

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


