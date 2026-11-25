#!/usr/bin/env bash
# Build the pjdfstest binary inside the submodule.
set -euo pipefail
cd "$(dirname "$0")/pjdfstest"
autoreconf -ifs
./configure
make pjdfstest
