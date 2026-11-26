import? "../justfile"

[default]
run:
    cargo run --features metrics -- -c config.toml

pjdfstest-build:
    nfs-tests/pjdfstest-build.sh

# Run pjdfstest against mirror-fs over NFS (needs sudo). Args go to pjdfstest.py.
pjdfstest *args:
    nfs-tests/pjdfstest.sh {{ args }}

cthon-build:
    nfs-tests/cthon-build.sh

# Run cthon04 against mirror-fs over NFS (needs sudo). Args go to cthon.py.
cthon *args:
    nfs-tests/cthon.sh {{ args }}

# Run xfstests against mirror-fs over NFS (needs sudo). Args go to xfstests.py / check.
xfstests *args:
    nfs-tests/xfstests.sh {{ args }}
