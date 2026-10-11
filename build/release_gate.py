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
  - the offset must be EVEN: an odd one puts every recto on a verso.
  - planned names must be bare filenames (no "/", "\\", ".", ".."), not symlinks,
    and resolve to a direct child of DIR; a name listed twice is a plan defect.
  - a malformed plan is a problem, never a traceback.
  - the gate does not check page chrome (running head, tab): a page whose
    footer vanished is skipped; build/tests/test_unit_chrome.py owns chrome.
  - the footer/offset rules apply only to Code PDFs, decided by the artifact's
    `kind` (never the file name): integrated, integrated-redline, standalone,
    standalone-redline. A PDF of any other known kind (use-table-changes, a
    memo with no "| N" footer) must only open, have a page and extractable
    text on its first page. An unknown kind gets the strict Code rules.
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
MEMO_KINDS = {"use-table-changes"}
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
    """(names, problems) from a plan; never raises on a malformed one."""
    if not isinstance(plan, dict):
        return [], ["plan is not a JSON object"]
    problems, names = [], []
    if not isinstance(plan.get("version"), str) or not plan["version"]:
        problems.append("plan has no version")
    arts = plan.get("artifacts")
    if not isinstance(arts, list):
        problems.append("plan has no artifacts list")
        arts = []
    for i, a in enumerate(arts):
        files = a.get("files") if isinstance(a, dict) else None
        if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
            problems.append(f"plan artifact {i} has no files list")
            continue
        kind = a.get("kind")
        if not isinstance(kind, str) or not kind:
            problems.append(f"plan artifact {i} has no kind string")
            continue
        names.extend((f, kind) for f in files)
    return names, problems


def _name_problem(dir, name):
    if (not name or "/" in name or "\\" in name or name in (".", "..")
            or "\0" in name):
        return f"{name}: planned name is not a bare filename"
    f = dir / name
    if f.is_symlink():
        return f"{name}: planned file is a symlink"
    if f.resolve().parent != dir.resolve():
        return f"{name}: planned file is not directly inside the release directory"
    return None


def check(plan, dir):
    dir = Path(dir)
    planned, problems = _planned(plan)
    version = plan.get("version") if isinstance(plan, dict) else None
    allowed = {n for n, _ in planned}
    if isinstance(version, str) and version:
        allowed.add(f"Summary of Changes {version}.pdf")
    seen = set()
    for name, kind in planned:
        if name in seen:
            problems.append(f"{name}: planned twice in the plan")
            continue
        seen.add(name)
        bad = _name_problem(dir, name)
        if bad:
            problems.append(bad)
            continue
        f = dir / name
        if not f.is_file():
            problems.append(f"{name}: planned file is missing")
            continue
        if f.stat().st_size == 0:
            problems.append(f"{name}: file is empty")
            continue
        if name.lower().endswith(".pdf"):
            if kind in MEMO_KINDS:
                try:
                    d = pymupdf.open(str(f))
                    try:
                        text = d[0].get_text("text").strip() if len(d) else None
                    finally:
                        d.close()
                except Exception as e:
                    problems.append(f"{name}: cannot be opened as a PDF ({e})")
                    continue
                if text is None:
                    problems.append(f"{name}: PDF has no pages")
                elif not text:
                    problems.append(f"{name}: first page has no extractable text")
                continue
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
            else:
                off = offsets.pop()
                if off % 2:
                    problems.append(
                        f"{name}: printed - physical offset is {off}, which is odd; "
                        f"rectos would fall on versos")
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
    try:
        plan = json.loads(Path(argv[1]).read_text())
    except (OSError, ValueError) as e:
        print(f"release_gate: plan cannot be read ({e})", file=sys.stderr)
        return 1
    problems = check(plan, Path(argv[2]))
    if problems:
        for p in problems:
            print(f"release_gate: {p}", file=sys.stderr)
        return 1
    print(f"release_gate: {len({n for n, _ in _planned(plan)[0]})} file(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
