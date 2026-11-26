#!/usr/bin/env bash
# Build xfstests inside the submodule. Dependencies: see the "Ubuntu or Debian"
# section of nfs-tests/xfstests/README (CI installs them in .github/workflows/nfs-tests.yml).
set -euo pipefail
cd "$(dirname "$0")/xfstests"
make -j"$(nproc)"
