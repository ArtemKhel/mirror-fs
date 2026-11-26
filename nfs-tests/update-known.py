#!/usr/bin/env python3
"""Apply a run's NOW PASSING / NEW FAILURES report to a known-failures file.

    nfs-tests/update-known.py nfs-tests/xfstests-known-failures.txt ci.log
    nfs-tests/xfstests.sh | tee /dev/stderr | nfs-tests/update-known.py nfs-tests/xfstests-known-failures.txt

Works for every suite: an entry is the report line up to its first `:`, e.g.
`generic/035`, `basic/test5` or `chmod/00.t 12`. Comments at the top of the file
and on entry lines are kept; entries are re-sorted.
"""

import argparse
import re
import sys
from pathlib import Path


def parse_report(lines):
    """Return (now passing, new failures) entries found in the report."""
    sections = {"NOW PASSING": set(), "NEW FAILURES": set()}
    current = None
    for line in lines:
        # Tolerate GitHub Actions' timestamp prefix when a log is copied from CI.
        line = re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ", "", line.rstrip("\n"))
        header = next((name for name in sections if line.startswith(name)), None)
        if header:
            current = sections[header]
        elif current is not None and line.startswith("  "):
            current.add(line.split(":", 1)[0].strip())
        else:
            current = None
    return sections["NOW PASSING"], sections["NEW FAILURES"]


def sort_key(entry):
    # `chmod/00.t 12` sorts by case number, not as text.
    return [(0, int(part), "") if part.isdigit() else (1, 0, part) for part in entry.split()]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("known", type=Path, help="known-failures file to edit")
    parser.add_argument("report", nargs="?", type=Path, help="run output (default: stdin)")
    args = parser.parse_args()

    lines = args.report.read_text().splitlines() if args.report else sys.stdin.readlines()
    passing, failing = parse_report(lines)
    if not passing and not failing:
        sys.exit("no NOW PASSING / NEW FAILURES entries in the report")

    header, entries = [], {}
    for line in args.known.read_text().splitlines() if args.known.exists() else []:
        entry = line.split("#", 1)[0].strip()
        if entry:
            entries[entry] = line
        elif not entries:
            header.append(line)

    removed = passing & entries.keys()
    added = failing - entries.keys()
    for entry in removed:
        del entries[entry]
    for entry in added:
        entries[entry] = entry

    args.known.write_text("\n".join(header + [entries[e] for e in sorted(entries, key=sort_key)]) + "\n")
    print(f"{args.known}: removed {len(removed)}, added {len(added)}")
    for entry in sorted(passing - removed, key=sort_key):
        print(f"  not listed, ignored: {entry}")


if __name__ == "__main__":
    main()
