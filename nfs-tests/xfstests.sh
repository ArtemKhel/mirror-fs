#!/usr/bin/env bash
# Run xfstests (nixpkgs `xfstests-check`) against mirror-fs over NFSv3. Needs sudo.
# Args go to xfstests.py; the ones it doesn't know go to check (default: -g quick).
# Override XFSTESTS_ROOT to change the work dir.
set -euo pipefail
cd "$(dirname "$0")/.."
. nfs-tests/lib.sh

command -v xfstests-check >/dev/null || { echo "xfstests-check not found (nixpkgs#xfstests)"; exit 1; }
root=${XFSTESTS_ROOT:-/tmp/xfstests}
serve $root test scratch
mkdir -p $root/test-mnt $root/scratch-mnt
# nolock: NLM is not ready yet.
sudo env FSTYP=nfs TEST_DEV=127.0.0.1:/test TEST_DIR=$root/test-mnt \
    SCRATCH_DEV=127.0.0.1:/scratch SCRATCH_MNT=$root/scratch-mnt \
    NFS_MOUNT_OPTIONS="-o $nfs_opts,nolock" \
    "$(command -v python3)" nfs-tests/xfstests.py \
    --check "$(command -v xfstests-check)" --workdir $root "$@"
