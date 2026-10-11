#!/usr/bin/env python3
"""release_gate.py -- refuse an incomplete or mis-paginated staged release.

  release_gate.py PLAN.json DIR

A leaf builder's exit 0 does not prove it wrote its file; this gate checks the
staged release against its plan (Ruling 10). It refuses; it does not report.

  - every planned file exists and is non-empty;
  - every planned PDF opens, carries at least one printed page number in its
    footer, and `printed - physical` is the SAME on every numbered page
    (logical == physical, the parity invariant that an uncounted front note or
    a missing page breaks);
  - nothing is present that the plan does not name. Allowed extra: an existing
    `Summary of Changes <version>.pdf`. Hidden files (names starting with ".")
    are ignored; the driver's staging dir holds none.
  - a non-PDF file is checked only for existence and size > 0.

Exit 0: one line `release_gate: N file(s) checked`.  Exit 1: one stderr line
per problem, each prefixed `release_gate: `.
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

FOOTER_NUMBER = re.compile(
    r"Newcastle Core Zoning Code\s*\|\s*(\d+)|(\d+)\s*\|\s*Newcastle Core Zoning Code")
BAND = 40  # pt, bottom of the page


def footer_numbers(pdf):
    """[(physical page, printed number)], 1-based physical, read from the bottom band."""
    d = pymupdf.open(str(pdf))
    try:
        pairs = []
        for i, p in enumerate(d):
            band = pymupdf.Rect(0, p.rect.height - BAND, p.rect.width, p.rect.height)
            m = FOOTER_NUMBER.search(p.get_text("text", clip=band))
            if m:
                pairs.append((i + 1, int(m.group(1) or m.group(2))))
        return pairs
    finally:
        d.close()


def _planned(plan):
    names = []
    for a in plan.get("artifacts", []):
        names.extend(a.get("files", []))
    return names


def check(plan, dir):
    dir = Path(dir)
    problems = []
    planned = _planned(plan)
    allowed = set(planned) | {f"Summary of Changes {plan['version']}.pdf"}
    for name in sorted(set(planned)):
        f = dir / name
        if not f.is_file():
            problems.append(f"{name}: planned file is missing")
            continue
        if f.stat().st_size == 0:
            problems.append(f"{name}: file is empty")
            continue
        if name.lower().endswith(".pdf"):
            try:
                pairs = footer_numbers(f)
            except Exception as e:
                problems.append(f"{name}: cannot be opened as a PDF ({e})")
                continue
            if not pairs:
                problems.append(f"{name}: no printed page number found")
                continue
            offsets = {printed - phys for phys, printed in pairs}
            if len(offsets) > 1:
                phys, printed = next((p, n) for p, n in pairs
                                     if n - p != pairs[0][1] - pairs[0][0])
                problems.append(
                    f"{name}: printed page numbers do not keep a constant offset "
                    f"from physical pages (physical {pairs[0][0]} prints {pairs[0][1]}, "
                    f"physical {phys} prints {printed})")
    if dir.is_dir():
        for f in sorted(dir.iterdir()):
            if f.name.startswith(".") or f.name in allowed:
                continue
            problems.append(f"{f.name}: file is not in the release plan")
    return sorted(problems)


def main(argv):
    if len(argv) != 3:
        print("usage: release_gate.py PLAN.json DIR", file=sys.stderr)
        return 2
    plan = json.loads(Path(argv[1]).read_text())
    problems = check(plan, Path(argv[2]))
    if problems:
        for p in problems:
            print(f"release_gate: {p}", file=sys.stderr)
        return 1
    print(f"release_gate: {len(set(_planned(plan)))} file(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
