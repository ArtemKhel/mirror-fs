#!/usr/bin/env bash
# Run cthon04 against mirror-fs over NFS with NLM locking. Args go to cthon.py.
# Needs sudo (server, mount) and running rpcbind + rpc.statd for the lock tests.
# Override CTHON_ROOT to change the work dir.
set -euo pipefail
cd "$(dirname "$0")/.."
. nfs-tests/lib.sh

root=${CTHON_ROOT:-/tmp/cthon}
serve_and_mount $root ""
python3 nfs-tests/cthon.py --mount $root/mnt --log $root/log.txt "$@"
