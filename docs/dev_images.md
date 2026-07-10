# Development images

The `-dev` images exist to make it convenient to develop SeedSigner *on the device itself*. They run the same application, from the same buildroot environment, with the same libraries as the release images with additions to aid in development conveniences. **They are not security-hardened: networking and SSH are enabled. Never use a dev image with real funds.**

## How the dev image stays close to the release image

The dev board config deliberately *references* the release files and layers a delta on top, so release changes flow into the dev image automatically:

| Piece | Release base | Dev delta |
|---|---|---|
| kernel config | `../pi02w/board/kernel.config` | `pi02w-dev/board/kernel.config.fragment` |
| busybox config | `../pi02w/board/busybox.config` | `pi02w-dev/board/busybox.config.fragment` |
| rootfs overlay | `../rootfs-overlay/` | `../rootfs-overlay-dev/` (applied second) |
| defconfig | copied from `pi02w_defconfig` | dev packages appended at the bottom |
| post-build | derived from release script | skips the image-slimming steps |

Like the release image, the dev image boots entirely from an initramfs (the root filesystem lives in RAM). Persistence is provided by a second partition (see below).

## What's added

- **Networking**: onboard wifi (Zero 2 W / Pi 3 / Pi 4), any `eth*` USB ethernet adapter, and the Pi 3/4's onboard NIC. Everything is DHCP.
- **USB relay**: `dtoverlay=dwc2` plus a built-in `g_ether` gadget. Plug the Pi's USB port into a computer and it shows up as an "RNDIS/Ethernet Gadget" at a fixed `10.55.0.1`, so `ssh root@10.55.0.1` works immediately with no host-side configuration. If you also want the Pi to reach the internet over that cable, turn on internet sharing on the host (see [seedsigner docs/usb_relay.md](https://github.com/SeedSigner/seedsigner/blob/dev/docs/usb_relay.md) for host-side setup — the SD-card-side steps there are *not* needed, the dev image is preconfigured) — the Pi detects the host's DHCP server and uses that instead of its static address. See "USB relay networking" below.
- **SSH server** (dropbear): log in as `root` with the root password below, or drop an `authorized_keys` file on the boot partition. Host keys persist on the data partition, so no fingerprint warnings after reboots.
- **HDMI console + USB keyboard/mouse**: a root shell runs on `tty1`.
- **Persistent storage**: a 256MB ext4 partition (label `seedsigner-data`) mounted at `/mnt/data`, **auto-grown to fill the rest of the microSD on first boot** (so a 32GB card gives you ~32GB of `/mnt/data`). Because the whole OS runs from RAM, you can pull the microSD while the device is running (`/mnt/data` disappears, everything else keeps working) and reinsert it later — `/mnt/data` auto-remounts, no reboot needed. Run `sync` before pulling the card if you have unsaved writes.
- **CLI tools**: `git`, `rsync`, `ssh`/`scp` (dropbear), `vi` (busybox), `nano`, `wget`, `ip`/`ifconfig`/`ping`/`nslookup`, `pip` (with setuptools). The full python stdlib (including `unittest`) is kept, and all `.py` sources stay readable on-device instead of `.pyc`-only. See "Installing Python packages" below for the pip/venv specifics.

## Building the developer SeedSigner OS Image

Set `BOARD_TYPE` to the board you're building for — one of `pi0`, `pi02w`, `pi2`, or `pi4`:

```bash
export BOARD_TYPE=pi0

SS_ARGS="--${BOARD_TYPE} --dev" docker compose up --build
```

or from a shell inside the container:

```bash
./build.sh --${BOARD_TYPE} --dev
```

The image lands in `images/seedsigner_os.<branch>.${BOARD_TYPE}-dev.img`.

## Quick start (macOS)

Once you've built the image, this takes you from a flashed card to running the test suite and your own code on the device, over a single USB cable.

### 1. Flash the image to a microSD

Write `images/seedsigner_os.<branch>.<board>-dev.img` to a microSD card with Raspberry Pi Imager ("Use custom"), balenaEtcher, or `dd`, then put the card in the SeedSigner.

### 2. Plug into the correct USB port

The Pi Zero 2 W has **two** micro-USB ports. Connect the cable from your Mac to the **data** port — the one closer to the middle of the board (labeled `USB`) — **not** the one at the outer edge (labeled `PWR`), which is power-only. The device draws power and talks to your Mac over this one cable, so it will boot as soon as it's plugged in.

### 3. Share your Mac's internet over the USB link

The image appears to macOS as a USB ethernet gadget ("RNDIS/Ethernet Gadget"). Turn on Internet Sharing so the Mac hands it an IP address (and gives it internet for `git clone`/`pip`):

1. System Settings → General → **Sharing** → **Internet Sharing** (click the ⓘ).
2. **Share your connection from:** Wi-Fi.
3. **To computers using:** check the RNDIS/Ethernet Gadget (the USB interface).
4. Toggle **Internet Sharing** on (the indicator turns green).

The dev image already has the USB ethernet gadget (`dtoverlay=dwc2` + `g_ether`) baked in, so — unlike the upstream [usb_relay.md](https://github.com/SeedSigner/seedsigner/blob/dev/docs/usb_relay.md) guide — you do **not** need to edit anything on the card.

### 4. Add an SSH shortcut

Add this to `~/.ssh/config` on your Mac so you can just `ssh seedsigner` — always as `root`, with the host-key fingerprint check skipped entirely and no `known_hosts` churn (handy because it's a throwaway dev box):

```
Host seedsigner seedsigner.local
    HostName seedsigner.local
    User root
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
```

- `User root` — no need to type `root@`.
- `StrictHostKeyChecking no` + `UserKnownHostsFile /dev/null` — never prompt to verify the fingerprint and never store it.
- `LogLevel ERROR` — hides the "Permanently added ..." warning that would otherwise print on every connect.

### 5. Connect

```bash
ssh root@seedsigner.local
```

Password: `seedsigner`. Give the device 15–30s after plugging in to boot and to bring `seedsigner.local` up. If the name doesn't resolve yet, wait a moment and retry, or find its address on the Mac with `arp -a | grep bridge100`.

### 6. Clone the repo, set up the venv, and run the tests

On the device:

```bash
cd /mnt/data
git clone --recursive https://github.com/SeedSigner/seedsigner.git
cd seedsigner
git submodule update --init --recursive
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r tests/requirements.txt
python3 -m pip install -r l10n/requirements-l10n.txt
python3 -m pip install -e .
python setup.py compile_catalog
pytest
seedsigner restart
```

Notes:

- `/mnt/data` is the persistent partition, so the checkout and venv survive reboots.
- On this image `python3 -m venv` defaults to `--system-site-packages`, so the heavy native dependencies (Pillow, numpy, embit, pyzbar) come from the image and pip only installs the pure-Python dev/test tools into the venv.
- `compile_catalog` builds the translation `.mo` files — skip it and the l10n tests fail.
- `seedsigner restart` relaunches the app from your `/mnt/data/seedsigner` checkout (see [Controlling the app](#controlling-the-app)).

## Using the image

### Wifi credentials

Put a `wifi.txt` on the boot partition (the FAT volume you see when you insert the SD card into your computer, also visible on-device at `/mnt/microsd`):

```
MyNetworkName
MyPassphrase
US        <- optional country code, defaults to US
```

Power cycle. If you need more control (hidden SSID, enterprise auth, multiple networks), provide a full `wpa_supplicant.conf` on the boot partition instead.

### Root password

`seedsigner`. This is set in `pi02w-dev_defconfig` (`BR2_TARGET_GENERIC_ROOT_PASSWD`) and reapplied by `post-build.sh` — see the comments there if you change it, since the release rootfs-overlay's `etc/shadow` would otherwise silently overwrite it back to a locked account.

### Finding the device / SSH

The image runs an mDNS/Zeroconf responder (`mdnsd`), so from any machine on the same link you can just use its `.local` name — no need to hunt for the IP:

```bash
ssh root@seedsigner.local
```

This works over the USB relay, wifi, and ethernet alike, and follows whatever address DHCP hands out (mdnsd re-checks every 10s). macOS and Linux (with nss-mdns/avahi) resolve `.local` out of the box; on Windows it needs Bonjour installed. If `.local` resolution isn't available, run `network-info` from the HDMI console (or check your router/DHCP leases) and `ssh root@<ip>` instead.

The advertised name is `seedsigner` (set in `/etc/default/mdnsd`). The system hostname is `seedsigner-os` — the same as the release image, which the SeedSigner app requires (it keys OS-specific behavior, such as storing settings on the microSD and detecting card insert/removal, off the hostname).

The image is **IPv4-only** — IPv6 is disabled via `ipv6.disable=1` on the kernel command line (`pi02w-dev/board/boot_cmdline.txt`). Without this the USB-relay link picks up a link-local/ULA IPv6 that `ssh root@seedsigner.local` would try first and stall on before falling back to IPv4; with IPv6 off, `seedsigner.local` resolves to the IPv4 address only and plain `ssh root@seedsigner.local` connects directly.

### USB relay networking

Plug the Pi into a computer over USB. Within a few seconds:

- If the host is **not** sharing its internet connection, the Pi assigns itself `10.55.0.1` and runs a small DHCP server (`udhcpd`, range `10.55.0.2`–`10.55.0.6`), so the host auto-configures its side of the link too. Just `ssh root@10.55.0.1`.
- If the host **is** sharing its internet connection (macOS: System Settings → General → Sharing → Internet Sharing, share to the "RNDIS/Ethernet Gadget"/USB interface), the Pi detects the host's DHCP server instead and takes a normal lease from it (typically `192.168.2.x` on macOS), giving the Pi an actual internet route for `git clone`/`pip`/etc. The lease address can change between reboots — this is exactly why `ssh root@seedsigner.local` (see above) is the easiest way in. Otherwise find the address with `network-info`, or on the host: `arp -a | grep bridge100` (macOS).

### Developing on the device

There are multiple ways to work on the SeedSigner code with a dev image, and you can mix them freely — either way the app runs from `/mnt/data/seedsigner`:

- **A — Work directly on the device.** Clone the repo onto the device over the network and edit / commit / pull right there; `git`, editors (`vi`, `nano`), and the Python toolchain are all on the image. Good when you want a self-contained setup that doesn't depend on a host.
- **B — Edit on your Mac, sync to the device.** Keep your working tree and your editor/IDE on your Mac and push changes to the device with `rsync` whenever you want to test. Good when you prefer your host tooling.

In both cases `start.sh` runs `/mnt/data/seedsigner/src/main.py` when it exists (falling back to the embedded `/opt/src`), and uses a `venv`/`.venv` in the checkout if present — so once the code is under `/mnt/data/seedsigner`, the rest (controlling the app, tests, venvs) is identical.

#### Workflow A: clone on the device

```bash
cd /mnt/data
git clone --recursive https://github.com/SeedSigner/seedsigner.git
```

Then follow the venv/test setup in the [Quick start](#6-clone-the-repo-set-up-the-venv-and-run-the-tests). Edit in place on the device and `seedsigner restart` to pick up changes.

#### Workflow B: edit on your Mac, rsync to the device

Keep editing in your local checkout (e.g. `~/Source/seedsigner`) and push it to the device's `/mnt/data/seedsigner` over SSH. A ready-made helper lives at [`docs/scripts/rsync-to-seedsigner.sh`](scripts/rsync-to-seedsigner.sh) — copy it to the **root of your local seedsigner checkout** and run it from there:

```bash
cp path/to/seedsigner-os/docs/scripts/rsync-to-seedsigner.sh ~/Source/seedsigner/
cd ~/Source/seedsigner
./rsync-to-seedsigner.sh             # sync the working tree to the device
./rsync-to-seedsigner.sh --restart   # ...and `seedsigner restart` afterward
```

It `rsync`s the checkout to `root@seedsigner.local:/mnt/data/seedsigner/` (override the target with the `SEEDSIGNER_HOST` / `SEEDSIGNER_USER` env vars), mirroring with `--delete` while excluding `.git/`, `venv/`, caches, screenshots, and the like. Its header comments walk through the one-time SSH-key setup so the sync is passwordless. First-time on the device you still need to create the venv and (for l10n tests) run `compile_catalog` — see the Quick start and [Running the tests](#running-the-tests--screenshot-generator).

#### Controlling the app

The app is managed by a pidfile-tracked service, so you don't have to hunt down and `kill` python processes. From an SSH session or the console:

```bash
seedsigner status      # running (pid N) | stopped
seedsigner stop        # stop the app (frees the display)
seedsigner start       # start it (detached; survives SSH logout)
seedsigner restart     # stop + start -- pick up code changes
```

(`seedsigner` is a thin wrapper over `/etc/init.d/S02seedsigner`, which is what starts the app at boot.) So the edit loop is just: edit your tree under `/mnt/data/seedsigner`, then `seedsigner restart`. To run the app in the foreground instead (to watch its output/tracebacks live): `seedsigner stop`, then `cd /mnt/data/seedsigner/src && python3 main.py`.

### Installing Python packages

`pip` is included, so `python3 -m pip install <package>` works once the device has internet (over wifi or the USB relay with host internet sharing). Two things to keep in mind:

- **The root filesystem runs from RAM**, so a plain `python3 -m pip install <pkg>` lands in `/usr/lib/python3*/site-packages` and is **lost on reboot**. For anything you want to keep, install onto the data partition instead — either into a venv there, or with `python3 -m pip install --target=/mnt/data/pylibs <pkg>` and add that dir to `PYTHONPATH`.
- **There is no C compiler on the device** (Buildroot cross-compiles). pip can install pure-Python packages and any prebuilt `armv7l` (`manylinux`) wheels, but a package that has to compile C from an sdist will fail.
- **Don't reinstall the app's compiled dependencies with pip.** Pillow and numpy are C-extension packages already baked into the image; `python3 -m pip install -r requirements.txt` would try to *build* them and fail on the missing compiler (e.g. Pillow's "headers or library files could not be found for zlib"). Instead, make the venv see the image's copies with `--system-site-packages` (below) — pip then reports them already satisfied and skips them. (`embit` and `pyzbar` are pure-Python and *can* be pip-installed — see the embit example below for testing a newer version — but they're baked in too, so a normal setup doesn't need to.)

Virtualenvs: on this image `python3 -m venv DIR` is customized to do the right thing by default — it **includes the system site-packages** (so the venv sees the baked-in Pillow/numpy/embit/…) and **skips the pip bootstrap** (python is built `--without-ensurepip`; the system pip is used instead). So just:

```bash
python3 -m venv /mnt/data/seedsigner/venv
. /mnt/data/seedsigner/venv/bin/activate
python3 -m pip install <package>       # installs into the active venv
```

(Upstream CPython defaults are the opposite — isolated, with a bundled pip; the defaults are flipped in `pi02w-dev/board/post-build.sh` because neither upstream default is usable here. A `venv` at `/mnt/data/seedsigner/venv` is also what `start.sh` uses to launch the app — see above.)

### Example: testing a newer version of a baked-in library (embit)

Some of the app's dependencies — `embit`, `Pillow`, `numpy`, `pyzbar` — are baked into the image as system packages under `/usr/lib/python3/site-packages/`, which you can't edit in place (the rootfs runs from RAM). To try a **newer version of a pure-Python one like `embit`** without rebuilding the image, install it into your `--system-site-packages` venv: the venv's `site-packages` comes first on `sys.path`, so the copy you install there **shadows** the baked-in one. And since `seedsigner restart` launches the app through the venv's python, it picks up the shadowed version automatically.

The device needs internet for this (USB relay with Internet Sharing on, or wifi). In your checkout's venv:

```bash
cd /mnt/data/seedsigner
source venv/bin/activate

# latest release from PyPI, installed into the venv (shadows the system embit)
python3 -m pip install --upgrade embit

# ...or a specific tagged release straight from git (any tag, branch, or commit
# after the @):
# python3 -m pip install --upgrade 'git+https://github.com/diybitcoinhardware/embit.git@v0.8.1'

# confirm the venv copy is the one that now loads, and its version (embit has no
# embit.__version__, so read the version from the installed package metadata)
python3 -c "import importlib.metadata as m, embit; print(m.version('embit'), embit.__file__)"
#   -> X.Y.Z  /mnt/data/seedsigner/venv/lib/python3.12/site-packages/embit/__init__.py

seedsigner restart      # the app now runs against the new embit
pytest                  # and/or run the suite
```

pip installs into the venv (the writable location), so you'll see a harmless `Not uninstalling embit at /usr/lib/python3/site-packages, outside environment` notice — it's leaving the baked-in copy in place and layering the new one on top. Revert to the image's version any time with:

```bash
python3 -m pip uninstall embit
```

Notes:

- If pip says `Requirement already satisfied` (PyPI's latest matches the baked-in version), force it into the venv with an explicit version or `--ignore-installed`: `python3 -m pip install 'embit==0.9.0'`.
- This shadowing trick only works for **pure-Python** packages. One with a compiled C extension (`Pillow`, `numpy`, ...) can't be pip-built on the device (no compiler), so a newer version of those has to go through a Buildroot image rebuild — bump the version + hash in `opt/external-packages/python-<pkg>/`.

### Running the tests / screenshot generator

The test tools (`pytest`, `pytest-cov`, `coverage`) are **not** in the image; install them from `tests/requirements.txt`. The suite also needs the app's runtime dependencies (PIL/Pillow, numpy, embit, pyzbar, the `seedsigner` package), which **are** in the image and reachable because `python3 -m venv` includes the system site-packages by default here (without that you'd get `ModuleNotFoundError: No module named 'PIL'` at collection time):

```bash
cd /mnt/data/seedsigner
python3 -m venv venv                # defaults to --system-site-packages here
. venv/bin/activate
python3 -m pip install -r tests/requirements.txt   # pytest 7.4.2, pytest-cov, coverage
```

Sanity-check that the image's packages are visible in the venv, then run:

```bash
python3 -c "import PIL, numpy, embit; print('PIL', PIL.__version__)"
pytest                                              # full suite from the repo root
pytest tests/screenshot_generator/generator.py --locale es   # screenshots
```

Notes:

- **Use the pinned `tests/requirements.txt`**, not a bare `pip install pytest`. A bare install pulls the newest pytest (9.x), whose collection/config behavior differs from the pinned 7.4.2 the suite targets; `tests/ requirements.txt` gets the intended version (and downgrades pytest if a newer one is already in the venv).
- `coverage` has no `armv7l` wheel, so pip builds it from source. With no compiler it falls back to coverage's pure-Python tracer automatically — `pytest --cov` still works, just measures a bit slower.

### Clock

The Pi has no RTC. The dev image sets a plausible recent date at boot (so TLS/`git clone` work) and corrects it via NTP once it has internet access.
