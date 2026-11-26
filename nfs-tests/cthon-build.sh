#!/usr/bin/env bash
# Build the cthon04 test programs inside the submodule. Needs libtirpc and pkg-config.
set -euo pipefail
cd "$(dirname "$0")/cthon04"
./tests.init.sh
# Only the dirs we run: tools/ fails to link against modern libtirpc.
# PATH on the command line overrides the /bin:/usr/bin one from tests.init.
for dir in basic special lock general; do
    make -C $dir PATH="$PATH"
done
