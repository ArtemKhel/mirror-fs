#!/usr/bin/env python3
"""Run xfstests' check and compare failures against a known list
(one test per line, e.g. `generic/013`, `#` comments).

Arguments this script doesn't know go to check (default: -g quick).
Expects FSTYP, TEST_DEV, TEST_DIR, SCRATCH_DEV, SCRATCH_MNT in the environment.
"""

import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--check", required=True, help="xfstests-check binary")
    parser.add_argument("--workdir", required=True, type=Path, help="results go to <workdir>/results")
    parser.add_argument("--known", type=Path, default=HERE / "xfstests-known-failures.txt")
    parser.add_argument("--update", action="store_true", help="rewrite known failures")
    args, check_args = parser.parse_known_args()

    if os.geteuid() != 0:
        sys.exit("xfstests must run as root")

    # xfstests-check puts results in $PWD/results; -R xunit adds result.xml there.
    results = args.workdir / "results"
    subprocess.run(["rm", "-rf", results], check=True)
    subprocess.run([args.check, "-R", "xunit", *(check_args or ["-g", "quick"])], cwd=args.workdir)

    reports = list(results.rglob("result.xml"))
    if not reports:
        sys.exit(f"no result.xml under {results}, check didn't run any test")
    ran, failed = set(), set()
    for report in reports:
        for case in ET.parse(report).iter("testcase"):
            if case.find("skipped") is not None:  # not run: says nothing about pass/fail
                continue
            ran.add(case.get("name"))
            if case.find("failure") is not None or case.find("mount-failure") is not None:
                failed.add(case.get("name"))

    known = set()
    if args.known.exists():
        known = {l.split("#", 1)[0].strip() for l in args.known.read_text().splitlines()} - {""}

    print(f"\n{len(ran)} tests, {len(failed)} failed")
    if args.update:
        known = (known - ran) | failed
        header = "# xfstests known to fail on mirror-fs.\n# Regenerate with `nfs-tests/xfstests.sh --update [check args]`.\n"
        args.known.write_text(header + "".join(f"{n}\n" for n in sorted(known)))
        if "SUDO_UID" in os.environ:  # keep the file editable by the invoking user
            os.chown(args.known, int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"]))
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
