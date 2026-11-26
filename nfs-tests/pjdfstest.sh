#!/usr/bin/env bash
# Run pjdfstest against mirror-fs over NFS. Args go to pjdfstest.py. Needs sudo.
# Override PJD_ROOT to change the work dir.
set -euo pipefail
cd "$(dirname "$0")/.."
. nfs-tests/lib.sh

root=${PJD_ROOT:-/tmp/pjdfstest}
serve_and_mount $root ,nolock
sudo "$(command -v python3)" nfs-tests/pjdfstest.py --mount $root/mnt --log $root/log.txt "$@"
