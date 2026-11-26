# mirror-fs

A user-space NFS server written in Rust that *mirrors* local directories to
NFS clients. Files created, modified, or removed through the server appear in
the host filesystem, and any local edits are immediately visible to clients ---
the exported tree is the real filesystem, not a copy.

## Status
Work-in-progress. Current release: **NFSv3 over TCP** with the **MOUNT**
service.

## Requirements

- Rust **1.75** or newer (edition 2021)
- A Unix-like OS (uses `libc` and Unix filesystem metadata APIs)
- Client mount support for NFSv3 (any modern kernel)

## Building

```sh
cargo build --release
```

The server binary is `target/release/mirrorfs`. The only external dependency
is `nfs-mamont`, fetched from GitHub at a pinned revision.

Run the test suite:

```sh
cargo test
```

NFS client tests run through a local NFS mount against a scratch export and
need `sudo` and `mount.nfs`. Failures listed in `nfs-tests/*-known-failures.txt`
are ignored; pass `--update` to regenerate the list, or suite paths to filter.

```sh
git submodule update --init
```

- [pjdfstest](https://github.com/pjd/pjdfstest), POSIX syscall conformance.
  Build needs `autoconf` and `automake`.

  ```sh
  nfs-tests/pjdfstest-build.sh
  nfs-tests/pjdfstest.sh [--update] [chmod rename/09.t ...]
  ```

- [cthon04](https://github.com/linux-nfs/cthon04), Connectathon NFS tests.
  Build needs `libtirpc` and `pkg-config`; the general suite needs `groff`.
  Lock tests use NLM, so `rpcbind` and `rpc.statd` must be running.

  ```sh
  nfs-tests/cthon-build.sh
  nfs-tests/cthon.sh [--update] [basic special/holey ...]
  ```

- [xfstests](https://git.kernel.org/pub/scm/fs/xfs/xfstests-dev.git), the kernel's
  file system regression suite, from nixpkgs (`xfstests-check` on PATH). Serves
  separate test and scratch exports; extra args go to `check` (default `-g quick`).

  ```sh
  nfs-tests/xfstests.sh [--update] [-g quick | generic/001 ...]
  ```

## Usage

```
mirrorfs [OPTIONS] -c <CONFIG>

Options:
  -c, --config <CONFIG>  Path to TOML configuration file [required]
  -a, --addr <ADDR>      IP address and TCP port to listen on [default: 0.0.0.0:2049]
  -h, --help             Print help
```

Example:

```sh
mirrorfs -c config.toml
```

## Configuration

The server is configured with a single TOML file:

```toml
[allocator]
buffer_size  = 1048576    # bytes per pooled RPC buffer
buffer_count = 2048       # number of buffers in the pool

vfs_pool_size = 10        # VFS task pool size (perf tunable)

[exports]
root  = "/tmp/nfs"        # base directory that gets mirrored
paths = ["fs01", "fs02"]  # relative directories under `root` to export
```

## Mounting from a client

```sh
# On the NFS server
mirrorfs -c config.toml

# On the client
mkdir -p /mnt/fs01
mount -t nfs -o tcp,vers=3 <server-address>:/fs01 /mnt/fs01
```

The server listens on TCP port 2049 by default (`-a` to change it) and handles
client connections concurrently. Only TCP is supported (no UDP).

## Roadmap

- NFSv3 (and NFSv4.* in future) on top of `nfs-mamont`

## Contributing

Contributions are welcome! Check the issues in the TODO column on our
Kanban

TODO: Add Kanban link

## License

MIT — see the [LICENSE](LICENSE) file.
