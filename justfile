import? "../justfile"

[default]
run:
    cargo run --features metrics -- -c config.toml

pjdfstest-build:
    posix-tests/build.sh

# Run pjdfstest against mirror-fs over NFS (needs sudo). Args go to run.py.
pjdfstest *args:
    posix-tests/run.sh {{ args }}
