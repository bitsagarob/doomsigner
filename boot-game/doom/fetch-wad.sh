#!/bin/sh
# Fetches Freedoom, which is freely redistributable, unlike the retail DOOM
# WADs. Kept out of git because it is nearly 30MB of binary.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
version=${FREEDOOM_VERSION:-0.13.0}
url="https://github.com/freedoom/freedoom/releases/download/v$version/freedoom-$version.zip"

mkdir -p "$here/wad"
if [ -f "$here/wad/freedoom1.wad" ]; then
  echo "wad already present"
  exit 0
fi

echo "fetching freedoom $version"
curl -sL -o "$here/wad/freedoom.zip" "$url"
python3 - "$here/wad" <<'PY'
import shutil, sys, zipfile
from pathlib import Path

target = Path(sys.argv[1])
with zipfile.ZipFile(target / "freedoom.zip") as archive:
    for name in archive.namelist():
        if name.lower().endswith("freedoom1.wad"):
            with archive.open(name) as src, open(target / "freedoom1.wad", "wb") as dst:
                shutil.copyfileobj(src, dst)
            print("extracted", name)
            break
    else:
        raise SystemExit("freedoom1.wad not found in archive")
PY
rm -f "$here/wad/freedoom.zip"
