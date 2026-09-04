################################################################################
#
# python-pydnssec-prover
#
################################################################################

# Offline RFC 9102 DNSSEC validation, used by the app to check a BIP-353 payment
# name against the DNS root trust anchor rather than taking the coordinator's
# word for it.
#
# Pinned to a commit rather than a branch or a release, for the same reason
# python-embit is: an upstream force-push must not be able to change what we
# build, and there is no release to pin to. Upstream is alvroble/pydnssec-prover,
# a work in progress; this is our fork, on a branch that adds an optional
# libcrypto backend for ECDSA. Without it the pure-Python path runs, correctly
# but roughly 8x slower over a whole chain, which on an ARM1176 is the difference
# between a pause and a device that looks hung.
#
# THIS MUST STAY IN STEP WITH THE PIN IN THE APP'S requirements.txt. That file
# governs a desktop checkout, this one governs the device image, and build.sh
# deletes requirements.txt from the rootfs, so a disagreement between the two
# does not show up until the hardware behaves differently from the simulator.
PYTHON_PYDNSSEC_PROVER_VERSION = df72b67f5585c4cfae779ca833db3c5c9304f625
PYTHON_PYDNSSEC_PROVER_SITE = $(call github,bitsagarob,pydnssec-prover,$(PYTHON_PYDNSSEC_PROVER_VERSION))
PYTHON_PYDNSSEC_PROVER_LICENSE = MIT
PYTHON_PYDNSSEC_PROVER_LICENSE_FILES = LICENSE

# pep517, not setuptools: the project is pyproject-only and ships no setup.py,
# so the setuptools setup type has nothing to run. Verified by building the
# wheel with the same `python -m build -n -w` that Buildroot uses; it produces a
# pure-Python wheel carrying the 12 source modules and none of the test corpus.
PYTHON_PYDNSSEC_PROVER_SETUP_TYPE = pep517

# The ECDSA backend reaches libcrypto through ctypes at runtime and degrades to
# pure Python when it is absent, so this is not a hard build dependency. It is
# declared anyway because every profile that enables this package also enables
# BR2_PACKAGE_PYTHON3_SSL, and an image that quietly shipped without libcrypto
# would simply be slow with nothing on screen to say why.
PYTHON_PYDNSSEC_PROVER_DEPENDENCIES = openssl

$(eval $(python-package))
