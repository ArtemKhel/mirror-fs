#!/usr/bin/env bash
# Run xfstests against mirror-fs over NFSv3. Needs sudo.
# Args go to xfstests.py; the ones it doesn't know go to check (default: -g quick).
# XFSTESTS_DIR: built xfstests tree (default: the submodule, see xfstests-build.sh).
# Override XFSTESTS_ROOT to change the work dir.
set -euo pipefail
cd "$(dirname "$0")/.."
. nfs-tests/lib.sh

src=${XFSTESTS_DIR:-nfs-tests/xfstests}
[ -x $src/check ] && [ -x $src/ltp/fsstress ] ||
    { echo "no built xfstests in $src: run nfs-tests/xfstests-build.sh or set XFSTESTS_DIR"; exit 1; }
root=${XFSTESTS_ROOT:-/tmp/xfstests}
serve $root test scratch
mkdir -p $root/test-mnt $root/scratch-mnt

# Run from a writable copy: tests with fs-specific outputs (e.g. generic/035) symlink
# their .out file inside tests/, and the source tree may be read-only.
sudo rm -rf $root/xfstests
cp -r $src $root/xfstests
chmod -R u+w $root/xfstests

# PATH: the tools check needs may live outside sudo's secure_path. nolock: NLM is not ready.
sudo env PATH="$PATH" FSTYP=nfs TEST_DEV=127.0.0.1:/test TEST_DIR=$root/test-mnt \
    SCRATCH_DEV=127.0.0.1:/scratch SCRATCH_MNT=$root/scratch-mnt \
    NFS_MOUNT_OPTIONS="-o $nfs_opts,nolock" \
    python3 nfs-tests/xfstests.py --xfstests $root/xfstests --results $root/results "$@"
