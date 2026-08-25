#!/usr/bin/env python3
"""Resolve and render-safely normalise the OLD side of one article's redline diff.

The NEW side is never touched here or by the caller: it is the document being
published, staged verbatim from the working tree. See normalize_for_diff.py's
module docstring for why only the OLD side may be normalised for rendering.

Exit codes:
  0  wrote the old-side file
  3  the article is NEW at this adoption -- caller writes an empty old side
     DELIBERATELY (whole body marked added), which is correct here and only here
  4  the article is NOT TEXT-COMPARABLE against the baseline -- its content
     moved out of markdown into a native-Typst unit between the baseline and
     now, so a text diff would show phantom deletions for content that only
     moved. The caller must render it UNMARKED: old side == new side.
  1  the article is not in adoption-map.json -- refuse rather than render as new

Draft-to-draft redlines (no --baseline) keep the historical behaviour exactly:
same filename at the old tag, no map, no normalisation.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402
import normalize_for_diff as nz  # noqa: E402

REPO = BUILD.parent


def git_show(ref: str, path: str) -> str | None:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("basename")
    ap.add_argument("old_ver")
    ap.add_argument("out_path")
    ap.add_argument("--baseline", action="store_true",
                    help="resolve through adoption-map.json and normalise both sides")
    a = ap.parse_args()

    if not a.baseline:
        # Historical behaviour, untouched: same filename at the old tag.
        text = git_show(a.old_ver, f"source/{a.basename}")
        if text is None:
            return 3
        Path(a.out_path).write_text(text)
        return 0

    amap = adoption_map.load()

    # Checked before baseline_path_for: an article can be present in `files`
    # (so it has a baseline counterpart) and still be flagged not-comparable --
    # article-02-prefatory.md maps to article-02-districts.md, but that
    # baseline file authored the district standards as markdown that no
    # longer exists in that form. Diffing it would misreport a move as a mass
    # deletion, so this check takes priority over resolving a baseline path.
    reason = amap.not_text_comparable_reason(a.basename)
    if reason is not None:
        print(f"{a.basename}: not text-comparable against {amap.baseline_version} "
              f"({reason}) -- rendering unmarked at current state", file=sys.stderr)
        return 4

    try:
        base = amap.baseline_path_for(a.basename)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if base is None:
        print(f"{a.basename}: new at this adoption — whole body will be marked added")
        return 3

    text = git_show(a.old_ver, f"source/{base}")
    if text is None:
        print(f"{a.basename}: adoption-map.json points at {base!r}, which does not "
              f"exist at {a.old_ver}. Fix the map.", file=sys.stderr)
        return 1

    # normalize_old_side, NOT normalize: this text is what gets RENDERED (the
    # old side of redline-text.py --source), and normalize()'s rewrap rule
    # flattens indented sub-clauses into run-on prose when it reaches a
    # renderer. See normalize_for_diff.py's module docstring.
    Path(a.out_path).write_text(nz.normalize_old_side(text, amap=amap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
