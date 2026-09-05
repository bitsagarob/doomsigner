#!/usr/bin/env python3
"""Boot-import test for a built SeedSigner OS image.

A build can go green while producing an image whose wallet cannot start: the app
is cloned from its own repo and the Python libraries come from Buildroot
packages, so a module the app imports at the top of a file may simply not be in
the image. Nothing in the build notices, and the only symptom is a device that
comes up to a black screen.

This test opens the finished .img, pulls the rootfs out of the kernel's embedded
initramfs, and imports every app module using *the image's own* ARM Python under
qemu-user. No Raspberry Pi and no root are needed.

    python3 tests/test_image_userland.py images/seedsigner_os.dev_.pi0.img

Requires mtools, cpio and qemu-arm-static. Skips (exit 0) if any is missing, the
same way tests/test_post_image_mtools.sh does.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import lzma
import zlib

CPIO_MAGIC = b"070701"

# Imported for their side effects on the boot path. main.py imports the
# controller, so a failure in any of these is a device that does not start.
BOOT_MODULES = ["seedsigner.controller"]


def skip(msg):
    print(f"SKIP: {msg}", file=sys.stderr)
    sys.exit(0)


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def require_tools():
    for tool in ("mcopy", "cpio", "qemu-arm-static"):
        if shutil.which(tool) is None:
            skip(f"'{tool}' not found — install mtools, cpio and qemu-user-static")


def extract_kernel(image, workdir):
    """Copy zImage out of the image's FAT32 boot partition without mounting it."""
    mtoolsrc = os.path.join(workdir, "mtoolsrc")
    with open(mtoolsrc, "w") as handle:
        handle.write(f'drive z: file="{os.path.abspath(image)}" partition=1\n')

    env = dict(os.environ, MTOOLSRC=mtoolsrc, MTOOLS_SKIP_CHECK="1")
    kernel = os.path.join(workdir, "zImage")
    result = subprocess.run(
        ["mcopy", "-o", "z:/zImage", kernel],
        env=env, capture_output=True, text=True,
    )
    if result.returncode != 0 or not os.path.exists(kernel):
        fail(f"could not read zImage from {image}: {result.stderr.strip()}")
    return kernel


LZ4_MAGICS = (b"\x04\x22\x4d\x18", b"\x02\x21\x4c\x18")  # frame, legacy


def gunzip_at(blob, offset, limit=None):
    """Decompress the gzip member starting at offset, or return None."""
    try:
        stream = zlib.decompressobj(16 + zlib.MAX_WBITS)
        return stream.decompress(blob[offset:], limit) if limit else stream.decompress(
            blob[offset:]
        )
    except zlib.error:
        return None


def unlz4_at(blob, offset):
    """Decompress an lz4 region with the lz4 CLI, or return None.

    Buildroot compresses some kernels with lz4 (BR2_LINUX_KERNEL_LZ4), and there
    is no lz4 in the Python standard library. The CLI stops at the end of the
    compressed stream and reports an error for the trailing kernel bytes, so its
    exit status is ignored and only the output is trusted.
    """
    if shutil.which("lz4") is None:
        return None
    result = subprocess.run(
        ["lz4", "-d", "-c", "--no-sparse", "-"],
        input=blob[offset:], capture_output=True,
    )
    return result.stdout or None


def find_cpio(blob):
    """Return the initramfs cpio bytes inside a kernel image, or None.

    The archive may sit at one or two levels of compression: an uncompressed
    kernel with a gzipped initramfs, or a gzip/lz4 compressed kernel that itself
    contains the gzipped initramfs.
    """
    for offset in (m.start() for m in re.finditer(re.escape(CPIO_MAGIC), blob)):
        # A bare cpio archive starts with the magic followed by 104 hex digits.
        header = blob[offset + 6:offset + 110]
        if len(header) == 104 and all(c in b"0123456789ABCDEFabcdef" for c in header):
            return blob[offset:]

    # Buildroot compresses the cpio with gzip, lz4 or xz depending on the
    # profile (BR2_TARGET_ROOTFS_CPIO_*), so try each in turn.
    for offset in (m.start() for m in re.finditer(rb"\x1f\x8b\x08", blob)):
        if (gunzip_at(blob, offset, 8) or b"").startswith(CPIO_MAGIC):
            return gunzip_at(blob, offset)

    for magic in LZ4_MAGICS:
        for offset in (m.start() for m in re.finditer(re.escape(magic), blob)):
            candidate = unlz4_at(blob, offset)
            if candidate and candidate.startswith(CPIO_MAGIC):
                return candidate

    for offset in (m.start() for m in re.finditer(rb"\xfd7zXZ\x00", blob)):
        try:
            candidate = lzma.LZMADecompressor().decompress(blob[offset:])
        except lzma.LZMAError:
            continue
        if candidate.startswith(CPIO_MAGIC):
            return candidate
    return None


def extract_initramfs(kernel):
    """Find the cpio archive inside the kernel image."""
    with open(kernel, "rb") as handle:
        blob = handle.read()

    found = find_cpio(blob)
    if found:
        return found

    # The kernel itself is compressed; unpack it and look again.
    inners = [gunzip_at(blob, m.start())
              for m in re.finditer(rb"\x1f\x8b\x08", blob)]
    for magic in LZ4_MAGICS:
        inners += [unlz4_at(blob, m.start())
                   for m in re.finditer(re.escape(magic), blob)]

    for inner in inners:
        if inner:
            found = find_cpio(inner)
            if found:
                return found

    if not any(inners) and shutil.which("lz4") is None:
        skip("kernel is not gzip compressed and the 'lz4' tool is missing — "
             "install lz4 to test this image")
    fail(f"no initramfs found in {kernel}")


def unpack_rootfs(cpio_bytes, workdir):
    rootfs = os.path.join(workdir, "rootfs")
    os.mkdir(rootfs)
    # Device nodes cannot be created without root; the app does not need them.
    subprocess.run(
        ["cpio", "-idmu", "--quiet", "--no-absolute-filenames"],
        input=cpio_bytes, cwd=rootfs, capture_output=True,
    )
    if not os.path.isdir(os.path.join(rootfs, "opt", "src")):
        fail("rootfs has no /opt/src — is this a SeedSigner OS image?")
    return rootfs


def app_modules(rootfs):
    """Every seedsigner.* module the image ships, as importable dotted names."""
    src = os.path.join(rootfs, "opt", "src")
    package = os.path.join(src, "seedsigner")
    modules = []
    for dirpath, _dirnames, filenames in os.walk(package):
        for filename in sorted(filenames):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            path = os.path.join(dirpath, filename)
            dotted = os.path.relpath(path, src)[: -len(".py")].replace(os.sep, ".")
            modules.append(dotted)
    return sorted(set(modules + BOOT_MODULES))


def run_in_image(rootfs, code):
    """Run code with the image's own Python, under ARM emulation."""
    python = os.path.join(rootfs, "usr", "bin", "python3")
    if not os.path.exists(python):
        fail("image has no /usr/bin/python3")
    return subprocess.run(
        [
            "qemu-arm-static", "-L", rootfs,
            "-E", f"PYTHONHOME={rootfs}/usr",
            "-E", f"PYTHONPATH={rootfs}/opt/src",
            python, "-c", code,
        ],
        capture_output=True, text=True, timeout=900,
    )


# The boot modules are imported first because main.py does. Anything that still
# fails is retried once at the end: several view modules break an import cycle by
# importing each other at the bottom of the file, so importing one of them first
# fails where the device, which always arrives via the other, succeeds. A library
# that is genuinely missing from the image fails both passes.
IMPORT_PROBE = """
import importlib
failed = []
for name in {boot!r} + {modules!r}:
    try:
        importlib.import_module(name)
    except Exception as exc:
        failed.append((name, type(exc).__name__, str(exc)[:160]))
for name, kind, message in failed:
    try:
        importlib.import_module(name)
    except Exception as exc:
        print("BROKEN\t%s\t%s: %s" % (name, type(exc).__name__, str(exc)[:160]))
"""

# embit falls back to a pure-Python secp256k1 if the native library is missing.
# The wallet still works and takes minutes to sign on an ARM1176, so assert the
# ctypes binding is the one that loads.
NATIVE_PROBE = """
try:
    from embit.util import ctypes_secp256k1
    print("NATIVE\\tok")
except Exception as exc:
    print("NATIVE\\t%s: %s" % (type(exc).__name__, exc))
"""


def main():
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[-4].strip(), file=sys.stderr)
        sys.exit(2)

    image = sys.argv[1]
    if not os.path.exists(image):
        fail(f"no such image: {image}")
    require_tools()

    workdir = tempfile.mkdtemp(prefix="ss-image-test-")
    try:
        kernel = extract_kernel(image, workdir)
        rootfs = unpack_rootfs(extract_initramfs(kernel), workdir)
        modules = app_modules(rootfs)
        print(f"{os.path.basename(image)}: {len(modules)} modules to import")

        others = [m for m in modules if m not in BOOT_MODULES]
        result = run_in_image(
            rootfs, IMPORT_PROBE.format(boot=BOOT_MODULES, modules=others)
        )
        if result.returncode != 0:
            fail(f"could not run the image's python:\n{result.stderr.strip()}")

        broken = [line.split("\t") for line in result.stdout.splitlines()
                  if line.startswith("BROKEN")]
        native = run_in_image(rootfs, NATIVE_PROBE).stdout.strip()

        for _, name, message in broken:
            print(f"  BROKEN  {name}  {message}")
        if not native.endswith("ok"):
            print(f"  BROKEN  embit native secp256k1  {native.split(chr(9))[-1]}")

        if broken or not native.endswith("ok"):
            fail(f"{len(broken)} module(s) in the image cannot be imported — "
                 "this image boots to a black screen")

        print(f"PASS: every app module imports inside {os.path.basename(image)}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
