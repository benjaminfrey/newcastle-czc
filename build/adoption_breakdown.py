#!/usr/bin/env python3
"""Prints the substantive-change breakdown for a Town Meeting packet, and its
TOTAL. Split out of build-adoption.sh's inline heredoc so it is directly
testable (subprocess against a real or synthetic adoption-map.json), rather
than only reachable through the shell wrapper.

This is the instrument the packet's headline number is read from, so
two failure modes are NOT allowed to pass silently:

  * a mapped baseline file that does not exist at the baseline tag -- would
    otherwise report the article as 100% newly-added text.
  * a mapped current file that does not exist in the working tree -- would
    otherwise vanish from both the listing and the TOTAL with no trace.

build/redline_resolve.py already refuses both cases with a "fix the map"
message when it resolves the OLD side for rendering (ADOPTION-SPEC.md §6.4:
"an unmatched file is an error, never a silent ... rendering"). This module
uses the same framing for the same reason: a silently wrong total here is
worse than a crash, because someone reads that number and concludes the
packet has been reviewed.

An article flagged not_text_comparable (its content moved OUT of markdown
into a native-Typst unit since the baseline -- Article 2's district
standards) is reported but EXCLUDED from the total, exactly as
redline_resolve.py renders it unmarked rather than diffing it: a text diff
would report a move as a mass deletion.

Exit codes:
  0  breakdown printed
  1  a mapped file could not be resolved on one side (a bad adoption-map.json
     entry, or an incomplete --src-dir / SRC_DIR source tree)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD))
REPO = BUILD.parent

import adoption_map  # noqa: E402
import normalize_for_diff as nz  # noqa: E402

# Test seam, a sibling of adoption_map.ENV_OVERRIDE and the same SRC_DIR that
# build-full-czc.sh and build-redline-full.sh honour: where the CURRENT side of
# the comparison is read from. Read at call time, never at import, so a test's
# monkeypatch.setenv takes effect. Unset -> the live source/ tree, which is what
# build-adoption.sh's precondition run must keep reading.
SRC_ENV = "SRC_DIR"
DEFAULT_SRC = REPO / "source"


def resolve_src_dir(src_dir: str | Path | None = None) -> Path:
    """--src-dir beats SRC_DIR beats the repository's source/."""
    return Path(src_dir or os.environ.get(SRC_ENV) or DEFAULT_SRC)


def run(map_path: str | None = None, src_dir: str | Path | None = None) -> int:
    m = adoption_map.load(map_path)
    src = resolve_src_dir(src_dir)
    src_label = "source" if src == DEFAULT_SRC else str(src)
    total = 0
    excluded: list[str] = []

    for cur, base in sorted(m.files.items()):
        if base is None:
            print(f"  {cur:40s}   NEW at this adoption")
            continue

        reason = m.not_text_comparable_reason(cur)
        if reason is not None:
            excluded.append(cur)
            print(f"  {cur:40s}   NOT TEXT-COMPARABLE (rendered unmarked, "
                  f"excluded from TOTAL): {reason}")
            continue

        old = subprocess.run(
            ["git", "-C", str(REPO), "show", f"{m.baseline_version}:source/{base}"],
            capture_output=True, text=True)
        if old.returncode != 0:
            print(f"{cur}: adoption-map.json points at {base!r}, which does not "
                  f"exist at {m.baseline_version}. Fix the map.", file=sys.stderr)
            return 1

        cur_path = src / cur
        if not cur_path.exists():
            if src == DEFAULT_SRC:
                print(f"{cur}: adoption-map.json maps this file, but {src_label}/{cur} "
                      f"does not exist in the working tree. Fix the map.", file=sys.stderr)
            else:
                # Not a map problem: the map is the freeze-gating file, and it
                # must never be the instruction for a bad or incomplete path.
                print(f"{cur}: the source tree {src} is incomplete -- {cur} "
                      f"(mapped by adoption-map.json) does not exist there. Check "
                      f"the --src-dir flag or the {SRC_ENV} environment variable; "
                      f"the map is not at fault.", file=sys.stderr)
            return 1

        # nz.changed_line_count, NOT a local difflib call: this number is read
        # as "what the packet marks", so it is computed by the same code path
        # the packet renders through (normalize_old_side on the old side, the
        # new side verbatim). This module used to re-implement the comparison
        # with normalize() -- which rewraps -- and could have drifted from the
        # rendered redline without anything noticing.
        c = nz.changed_line_count(old.stdout, cur_path.read_text(), amap=m)
        total += c
        print(f"  {cur:40s} {c:5d} lines")

    note = ""
    if excluded:
        note = f"  (excludes {len(excluded)} not-text-comparable article(s): {', '.join(excluded)})"
    print(f"  {'TOTAL':40s} {total:5d} substantive changed lines{note}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=None,
                    help="override adoption-map.json path (testing only)")
    ap.add_argument("--src-dir", default=None,
                    help="source tree to compare against the baseline "
                         f"(default: the repository's source/). The {SRC_ENV} env "
                         "var is honoured too, matching build-full-czc.sh's seam; "
                         "the flag wins if both are given.")
    a = ap.parse_args()
    return run(a.map, a.src_dir)


if __name__ == "__main__":
    raise SystemExit(main())
