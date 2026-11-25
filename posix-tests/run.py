#!/usr/bin/env python3
"""Run pjdfstest inside an NFS mount and compare failures against a known list.

Known-failures format, one entry per line (`#` starts a comment):
    chmod/00.t 12      single test case
    chown/00.t *       whole file
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = HERE / "pjdfstest" / "tests"
TIMEOUT = 10
PLAN = re.compile(r"^1\.\.(\d+)")
RESULT = re.compile(r"^(not )?ok (\d+)(.*)")


def load_known(path):
    known = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.split("#", 1)[0].split()
            if line:
                name, case = line
                known.setdefault(name, set()).add(case)
    return known


def run_file(test, mount, log):
    """Return {case number: TAP line} of failing cases."""
    try:
        out = subprocess.run(
            ["sh", str(test)],
            check=False,
            cwd=mount,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        ).stdout
    except subprocess.TimeoutExpired as error:
        out = (error.stdout or b"").decode(errors="replace") + "\n# timed out\n"
    log.write(f"### {test.relative_to(TESTS)}\n{out}\n")

    planned, seen, failed = 0, set(), {}
    for line in out.splitlines():
        if match := PLAN.match(line):
            planned = int(match.group(1))
        elif match := RESULT.match(line):
            case = int(match.group(2))
            seen.add(case)
            directive = match.group(3).upper()
            if (
                match.group(1)
                and "# TODO" not in directive
                and "# SKIP" not in directive
            ):
                failed[case] = line
    for case in range(1, planned + 1):
        if case not in seen:
            failed[case] = f"not ok {case} - never reported (crash or timeout)"
    if not planned and not seen:
        failed[0] = "no TAP output"
    return failed


def write_known(path, known):
    lines = [
        "# pjdfstest cases known to fail on mirror-fs.",
        "# Regenerate with `posix-tests/run.sh --update` (optionally filtered, e.g. `chmod`).",
    ]
    for name in sorted(known):
        cases = known[name]
        if "*" in cases:
            lines.append(f"{name} *")
        else:
            lines += [f"{name} {c}" for c in sorted(cases, key=int)]
    path.write_text("\n".join(lines) + "\n")
    if "SUDO_UID" in os.environ:  # keep the file editable by the invoking user
        os.chown(path, int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"]))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--mount", required=True, type=Path, help="directory to run tests in"
    )
    parser.add_argument("--known", type=Path, default=HERE / "known-failures.txt")
    parser.add_argument(
        "--log", type=Path, default=Path(os.devnull), help="full TAP output"
    )
    parser.add_argument("--update", action="store_true", help="rewrite known failures")
    parser.add_argument("filters", nargs="*", help="e.g. chmod, rename/09.t")
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("pjdfstest must run as root")

    tests = sorted(
        t
        for t in TESTS.rglob("*.t")
        if not args.filters
        or any(str(t.relative_to(TESTS)).startswith(f) for f in args.filters)
    )
    if not tests:
        sys.exit("no tests matched")

    known = load_known(args.known)
    new, fixed, total_failed = [], [], 0
    with args.log.open("w") as log:
        for test in tests:
            name = str(test.relative_to(TESTS))
            failed = run_file(test, args.mount, log)
            total_failed += len(failed)
            expected = known.get(name, set())
            print(f"{name}: {len(failed)} failed", flush=True)

            if args.update:
                if failed:
                    known[name] = {str(c) for c in failed}
                else:
                    known.pop(name, None)
                continue
            if "*" in expected:
                continue
            new += [
                f"{name} {c}: {line}"
                for c, line in failed.items()
                if str(c) not in expected
            ]
            fixed += [
                f"{name} {c}" for c in sorted(expected, key=int) if int(c) not in failed
            ]

    print(f"\n{len(tests)} files, {total_failed} failed cases")
    if args.update:
        write_known(args.known, known)
        print(f"updated {args.known}")
        return
    if fixed:
        print(
            f"\nnow passing ({len(fixed)}), consider removing from {args.known.name}:"
        )
        print("\n".join(f"  {f}" for f in fixed))
    if new:
        print(f"\nNEW FAILURES ({len(new)}):")
        print("\n".join(f"  {n}" for n in new))
        sys.exit(1)


if __name__ == "__main__":
    main()
