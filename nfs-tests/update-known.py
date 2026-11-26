#!/usr/bin/env python3
"""Apply a run's NOW PASSING / NEW FAILURES report to a known-failures file.

    nfs-tests/update-known.py ci.log
    nfs-tests/xfstests.sh | tee /dev/stderr | nfs-tests/update-known.py

The file comes from the report headers ("remove from <file>" / "add to <file>",
looked up in nfs-tests/); -k overrides it or covers logs without the name.

Works for every suite: an entry is the report line up to its first `:`, e.g.
`generic/035`, `basic/test5` or `chmod/00.t 12`. Comments at the top of the file
and on entry lines are kept; entries are re-sorted.
"""

import argparse
import re
import sys
from pathlib import Path

HEADER = re.compile(r"(NOW PASSING|NEW FAILURES)")
KNOWN_FILE = re.compile(r"(?:remove from|add to) (\S+?):?$")
# `generic/035`, `basic/test5`, `chmod/00.t 12`, optionally followed by `: <TAP line>`.
ENTRY = re.compile(r"^\s*(\S+/\S+(?: \d+| \*)?)\s*(?::|$)")


def normalize(text):
    # Copies from a browser may carry non-breaking spaces or tabs; str.split() handles both.
    return " ".join(text.split())


def parse_report(lines):
    """Return (now passing, new failures, known file named in the report or None).

    Headers may carry a prefix (e.g. CI timestamps); a section ends at the first
    line that isn't an entry.
    """
    sections = {"NOW PASSING": set(), "NEW FAILURES": set()}
    current, known = None, None
    for line in lines:
        # Drop GitHub Actions' timestamp prefix, then normalize whitespace.
        line = normalize(re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z", "", line))
        if header := HEADER.search(line):
            current = sections[header.group(1)]
            if named := KNOWN_FILE.search(line):
                known = named.group(1)
        elif current is not None and (entry := ENTRY.match(line)):
            current.add(entry.group(1))
        else:
            current = None
    return sections["NOW PASSING"], sections["NEW FAILURES"], known


def sort_key(entry):
    # `chmod/00.t 12` sorts by case number, not as text.
    return [(0, int(part), "") if part.isdigit() else (1, 0, part) for part in entry.split()]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-k", "--known", type=Path, help="known-failures file (default: from the report)")
    parser.add_argument("report", nargs="?", type=Path, help="run output (default: stdin)")
    args = parser.parse_args()

    lines = args.report.read_text().splitlines() if args.report else sys.stdin.readlines()
    passing, failing, named = parse_report(lines)
    if not passing and not failing:
        sys.exit("no NOW PASSING / NEW FAILURES entries in the report")

    known = args.known or (named and Path(named))
    if not known:
        sys.exit("the report doesn't name the known-failures file, pass -k")
    # A bare name (as the report prints it) is looked up next to this script.
    if not known.exists() and (Path(__file__).resolve().parent / known.name).exists():
        known = Path(__file__).resolve().parent / known.name
    if not known.exists():
        sys.exit(f"{known} not found")

    header, entries = [], {}
    for line in known.read_text().splitlines():
        entry = normalize(line.split("#", 1)[0])
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

    known.write_text("\n".join(header + [entries[e] for e in sorted(entries, key=sort_key)]) + "\n")
    print(f"{known}: removed {len(removed)}, added {len(added)}")
    for entry in sorted(passing - removed, key=sort_key):
        print(f"  not listed, ignored: {entry}")


if __name__ == "__main__":
    main()
