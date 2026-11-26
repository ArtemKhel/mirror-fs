# Sourced by the suite scripts from the repo root.
# serve_and_mount <work dir> <extra mount options>: serve <work dir>/export with
# mirror-fs as root and mount it at <work dir>/mnt. Both are undone on exit.
# Needs sudo. Override NFS_TESTS_PORT to change the server port, RUST_LOG for server.log.

serve_and_mount() {
    root=$1
    local port=${NFS_TESTS_PORT:-20490}

    cargo build
    mkdir -p $root/mnt
    sudo rm -rf $root/export && mkdir $root/export
    cat >$root/config.toml <<EOF
[exports]
root = "$root"
paths = ["export"]
EOF

    sudo env RUST_LOG=${RUST_LOG:-info} target/debug/mirror-fs -c $root/config.toml \
        -a 127.0.0.1:$port --no-root-squash >$root/server.log 2>&1 &
    server=$!
    trap cleanup EXIT
    for _ in $(seq 50); do
        (echo >/dev/tcp/127.0.0.1/$port) 2>/dev/null && break
        kill -0 $server 2>/dev/null || { cat $root/server.log; exit 1; }
        sleep 0.2
    done

    sudo mount -t nfs -o vers=3,proto=tcp,addr=127.0.0.1,port=$port,mountport=$port$2 \
        127.0.0.1:/export $root/mnt
}

cleanup() {
    # Detach lazily if busy: a hard mount left behind a dead server hangs whatever touches it.
    sudo umount -f $root/mnt || sudo umount -l $root/mnt || true
    sudo kill -INT $server 2>/dev/null || true
    wait $server || true
}
