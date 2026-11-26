# Sourced by the suite scripts from the repo root. Needs sudo.
# serve <work dir> <export>...: serve fresh <work dir>/<export> dirs with mirror-fs as root,
#   exported as /<export>. Sets $nfs_opts to the matching mount options.
# mount_export <export> <extra mount options>: mount /<export> at <work dir>/mnt.
# On exit, everything mounted under <work dir> is unmounted and the server stopped.
# Override NFS_TESTS_PORT to change the server port, RUST_LOG for server.log.

serve() {
    root=$1
    shift
    local port=${NFS_TESTS_PORT:-20490}
    nfs_opts=vers=3,proto=tcp,addr=127.0.0.1,port=$port,mountport=$port

    # Long runs outlive sudo's timestamp; keep it fresh so cleanup doesn't prompt.
    sudo -v
    while sleep 60; do sudo -n -v || exit; done &
    keepalive=$!
    trap cleanup EXIT

    cargo build
    local paths=()
    for export in "$@"; do
        sudo rm -rf $root/$export && mkdir -p $root/$export
        paths+=("\"$export\"")
    done
    cat >$root/config.toml <<EOF
[exports]
root = "$root"
paths = [$(IFS=,; echo "${paths[*]}")]
EOF

    sudo env RUST_LOG=${RUST_LOG:-info} target/debug/mirror-fs -c $root/config.toml \
        -a 127.0.0.1:$port --no-root-squash >$root/server.log 2>&1 &
    server=$!
    for _ in $(seq 50); do
        (echo >/dev/tcp/127.0.0.1/$port) 2>/dev/null && break
        kill -0 $server 2>/dev/null || { cat $root/server.log; exit 1; }
        sleep 0.2
    done
}

mount_export() {
    mkdir -p $root/mnt
    sudo mount -t nfs -o $nfs_opts$2 127.0.0.1:/$1 $root/mnt
}

cleanup() {
    # Detach lazily if busy: a hard mount left behind a dead server hangs whatever touches it.
    for mnt in $(findmnt -rn -o TARGET | grep "^$root/" | sort -r); do
        sudo umount -f $mnt || sudo umount -l $mnt || true
    done
    [ -n "${server-}" ] && { sudo kill -INT $server 2>/dev/null; wait $server || true; }
    kill $keepalive 2>/dev/null || true
}
