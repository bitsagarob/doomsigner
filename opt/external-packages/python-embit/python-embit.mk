################################################################################
#
# python-embit
#
################################################################################

# notTanveer's BIP-352 silent payments branch (embit#145), pinned to a commit
# rather than a branch name so an upstream force-push cannot change what we
# build. This must stay in step with the pin in the app's requirements.txt:
# that file governs a desktop checkout, this one governs the device image, and
# build.sh deletes requirements.txt from the rootfs. When the two disagreed the
# image shipped 0.8.0 and the wallet had no silent payments at all.
#
# Go back to a plain PyPI release the day silent payments land in embit proper.
PYTHON_EMBIT_VERSION = 533cd850f5f4d4f52c21dc1abae18133d98e394e
PYTHON_EMBIT_SITE = $(call github,notTanveer,embit,$(PYTHON_EMBIT_VERSION))
PYTHON_EMBIT_LICENSE = MIT
PYTHON_EMBIT_SETUP_TYPE = setuptools

# 0.8.0 shipped prebuilt libsecp256k1 binaries inside the Python package and two
# patches here narrowed them to the target's architecture. That is over: embit
# now excludes *.so, *.dll and *.dylib from its package outright, so there is
# nothing left to narrow and the patches have been deleted rather than fixed.
#
# Instead the C library is a real target package, which is what Buildroot is
# for. embit's ctypes wrapper queries the system loader for libsecp256k1 before
# it looks for in-tree artifacts, so it finds this one. Without the dependency
# embit silently uses util/py_secp256k1.py, a pure-Python fallback that is far
# too slow to sign on a Pi Zero and produces no error to notice.
PYTHON_EMBIT_DEPENDENCIES = libsecp256k1

# embit pins its own build tooling to exact versions:
#
#   requires = ["setuptools==80.9.0", "wheel==0.47.0"]
#
# Buildroot builds host-python packages against the setuptools and wheel it
# already has, so those pins fail the build outright with "Missing dependencies"
# rather than fetching anything. 0.8.0 asked for `setuptools>=42.0, wheel` and
# built fine, which is why this only appeared on the branch.
#
# Relax the two constraints and nothing else. This changes how embit is BUILT,
# never what it contains: no source file is touched, and the resulting package
# is byte-identical to one built with the pinned tools unless setuptools itself
# changes its output.
define PYTHON_EMBIT_RELAX_BUILD_REQUIRES
	$(SED) 's|"setuptools==[0-9.]*"|"setuptools"|; s|"wheel==[0-9.]*"|"wheel"|' 		$(@D)/pyproject.toml
	grep -q '"setuptools"' $(@D)/pyproject.toml
endef
PYTHON_EMBIT_POST_EXTRACT_HOOKS += PYTHON_EMBIT_RELAX_BUILD_REQUIRES

$(eval $(python-package))
