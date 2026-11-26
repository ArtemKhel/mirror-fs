#!/usr/bin/env python3
"""Run cthon04 test programs one by one inside an NFS mount and compare
failures against a known list (one `suite/program` per line, `#` comments).

cthon's own runtests stops at the first failure, so the programs and their
arguments are replicated here in the same order.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CTHON = HERE / "cthon04"
TIMEOUT = 30

# (name, argv); runs in <mount>/<suite> with NFSTESTDIR pointing there.
BASIC = ["test1", "test2", "test3", "test4", "test5", "test6", "test7", "test8", "test9"]
SPECIAL = [
    ["op_unlk"], ["op_ren"], ["op_chmod"], ["dupreq", "100", "testfile"], ["excltest"],
    ["negseek", "testfile"], ["rename", "100"], ["truncate"], ["holey"],
    ["nfsidem", "50", "testdir"], ["rewind"], ["telldir"], ["freesp"],
    ["bigfile", "-s", "30", "bigfile"], ["bigfile2", "bigfile"],
]
UNITS = (
    [(f"basic/{t}", [CTHON / "basic" / t, "-f"]) for t in BASIC]
    + [(f"special/{p[0]}", [CTHON / "special" / p[0], *p[1:]]) for p in SPECIAL]
    + [(f"lock/{t}", [CTHON / "lock" / t, "."]) for t in ["tlocklfs", "tlock64"]]
    # makefile.tst depends on /usr/include headers (absent on NixOS); `make -e` lets HDRS= drop them.
    + [
        (
            "general/all",
            [
                "sh",
                "-c",
                (
                    f'make -s -C {CTHON / "general"} copy DESTDIR="$PWD" PATH="$PATH"'
                    " && { [ -e /usr/include/stdio.h ] || export HDRS=; }"
                    ' && PATH="$PATH:." sh runtests.wrk FROM_RUNTESTS'
                ),
            ],
        )
    ]
)


def run_unit(name, argv, mount, log):
    workdir = mount / name.split("/")[0]
    workdir.mkdir(exist_ok=True)
    # TMPDIR empty: the op_* tests then use the cwd. CC is used by general's compiles.
    env = dict(os.environ, NFSTESTDIR=str(workdir), TMPDIR="", CC=os.environ.get("CC", "cc"))
    try:
        proc = subprocess.run(
            argv,
            check=False,
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        out, ok = proc.stdout + proc.stderr, proc.returncode == 0
    except subprocess.TimeoutExpired:
        out, ok = "timed out\n", False
    log.write(f"### {name}\n{out}\n")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--mount", required=True, type=Path, help="directory to run tests in")
    parser.add_argument("--known", type=Path, default=HERE / "cthon-known-failures.txt")
    parser.add_argument("--log", type=Path, default=Path(os.devnull), help="full test output")
    parser.add_argument("--update", action="store_true", help="rewrite known failures")
    parser.add_argument("filters", nargs="*", help="e.g. basic, special/holey")
    args = parser.parse_args()

    units = [u for u in UNITS if not args.filters or any(u[0].startswith(f) for f in args.filters)]
    if not units:
        sys.exit("no tests matched")

    known = set()
    if args.known.exists():
        known = {l.split("#", 1)[0].strip() for l in args.known.read_text().splitlines()} - {""}

    failed = set()
    with args.log.open("w") as log:
        for name, argv in units:
            ok = run_unit(name, argv, args.mount, log)
            print(f"{name}: {'ok' if ok else 'FAILED'}", flush=True)
            if not ok:
                failed.add(name)

    ran = {name for name, _ in units}
    print(f"\n{len(units)} programs, {len(failed)} failed")
    if args.update:
        known = (known - ran) | failed
        header = "# cthon04 programs known to fail on mirror-fs.\n# Regenerate with `nfs-tests/cthon.sh --update`.\n"
        args.known.write_text(header + "".join(f"{n}\n" for n in sorted(known)))
        print(f"updated {args.known}")
        return
    if fixed := sorted(known & ran - failed):
        print(f"\nnow passing ({len(fixed)}), consider removing from {args.known.name}:")
        print("\n".join(f"  {f}" for f in fixed))
    if new := sorted(failed - known):
        print(f"\nNEW FAILURES ({len(new)}):")
        print("\n".join(f"  {n}" for n in new))
        sys.exit(1)


if __name__ == "__main__":
    main()
