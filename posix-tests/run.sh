#!/usr/bin/env bash
# Serve a scratch export as root, mount it and run pjdfstest. Args go to run.py.
# Needs sudo. Override PJD_ROOT / PJD_PORT to change the work dir / server port.
set -euo pipefail
cd "$(dirname "$0")/.."

root=${PJD_ROOT:-/tmp/pjdfstest}
port=${PJD_PORT:-20490}

cargo build
mkdir -p $root/mnt
sudo rm -rf $root/export && mkdir $root/export
cat >$root/config.toml <<EOF
[exports]
root = "$root"
paths = ["export"]
EOF

sudo env RUST_LOG=info target/debug/mirror-fs -c $root/config.toml \
    -a 127.0.0.1:$port --no-root-squash >$root/server.log 2>&1 &
server=$!
cleanup() {
    sudo umount -f $root/mnt 2>/dev/null || true
    sudo kill -INT $server 2>/dev/null || true
    wait $server || true
}
trap cleanup EXIT
for _ in $(seq 50); do
    (echo >/dev/tcp/127.0.0.1/$port) 2>/dev/null && break
    kill -0 $server 2>/dev/null || { cat $root/server.log; exit 1; }
    sleep 0.2
done

sudo mount -t nfs -o vers=3,proto=tcp,addr=127.0.0.1,port=$port,mountport=$port,nolock \
    127.0.0.1:/export $root/mnt
sudo "$(command -v python3)" posix-tests/run.py --mount $root/mnt --log $root/log.txt "$@"
