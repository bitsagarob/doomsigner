################################################################################
#
# libsecp256k1
#
################################################################################

# embit's ctypes wrapper looks for a system libsecp256k1 BEFORE its own in-tree
# prebuilt artifacts, and the silent payments branch ships no prebuilts at all:
# its pyproject excludes *.so, *.dll and *.dylib outright. Without this package
# embit falls back to util/py_secp256k1.py, which is correct but far too slow to
# sign on a Pi Zero -- and it fails quietly, as a wallet that takes minutes
# rather than an error anyone would notice.
LIBSECP256K1_VERSION = 0.6.0
LIBSECP256K1_SITE = $(call github,bitcoin-core,secp256k1,v$(LIBSECP256K1_VERSION))
LIBSECP256K1_LICENSE = MIT
LIBSECP256K1_LICENSE_FILES = COPYING
LIBSECP256K1_INSTALL_STAGING = YES

# The four optional modules embit binds. Verified by listing the secp256k1_*
# symbols its ctypes wrapper resolves, not assumed:
#   schnorrsig  secp256k1_schnorrsig_sign / _verify        (taproot, BIP-340)
#   extrakeys   secp256k1_xonly_pubkey_* / _keypair_create (x-only keys)
#   ecdh        secp256k1_ecdh                             (BIP-352 tweaks)
#   recovery    secp256k1_ecdsa_sign_recoverable and friends (signed messages)
# Leaving any of them off builds a library that loads and then fails at the
# first call, which is worse than not having one.
LIBSECP256K1_CONF_OPTS = \
	-DSECP256K1_ENABLE_MODULE_SCHNORRSIG=ON \
	-DSECP256K1_ENABLE_MODULE_EXTRAKEYS=ON \
	-DSECP256K1_ENABLE_MODULE_ECDH=ON \
	-DSECP256K1_ENABLE_MODULE_RECOVERY=ON \
	-DSECP256K1_BUILD_BENCHMARK=OFF \
	-DSECP256K1_BUILD_TESTS=OFF \
	-DSECP256K1_BUILD_EXHAUSTIVE_TESTS=OFF \
	-DSECP256K1_BUILD_CTIME_TESTS=OFF \
	-DSECP256K1_BUILD_EXAMPLES=OFF

$(eval $(cmake-package))
