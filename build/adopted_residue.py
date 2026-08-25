#!/usr/bin/env python3
"""Draft-chrome residue check for an adopted document.

THE GATE TARGETS CHROME PHRASES, NOT THE WORD "DRAFT". The Code's own adopted
text reads "The Planning Board, or its designnee, drafts the official map of the
Town of Newcastle." A blanket search for "draft" fails on the Town's own words,
and the natural fix under time pressure is to delete the gate -- which is worse
than never having had it.

It also asserts the substantive occurrences are STILL PRESENT: a substitution
that damaged the Code's own text would be a far worse failure than a leftover
banner.
"""
from __future__ import annotations

import os
import sys

CHROME = (
    "INTEGRATED DRAFT",
    "TOWN MEETING EDITION",
    "NOT YET ADOPTED",
    "NOT ADOPTED",
    "For review only",
    "Draft v",
)

# Substantive uses of the word that MUST survive untouched.
MUST_SURVIVE = ("drafts the official map",)


def find_residue(text: str) -> list[str]:
    upper = text.upper()
    return [c for c in CHROME if c.upper() in upper]


def find_damage(text: str) -> list[str]:
    return [s for s in MUST_SURVIVE if s.lower() not in text.lower()]


def check(text: str, filenames: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Run both gates over `text` (the rendered PDF's extracted page text)
    PLUS the basenames of `filenames`.

    The filename is checked because the page-text scan alone cannot see it: a
    filename like "Newcastle CZC (Integrated Draft v1.0).pdf" carries the
    exact chrome strings this gate exists to catch, and Task 8's review found
    exactly that defect surviving a page-text-only gate (Important 1). Damage
    (MUST_SURVIVE) is checked against `text` only -- a filename is never where
    the Code's own "drafts the official map" text would live.
    """
    names = "\n".join(os.path.basename(f) for f in (filenames or []))
    combined = text + ("\n" + names if names else "")
    return find_residue(combined), find_damage(text)


def main() -> int:
    text = sys.stdin.read()
    residue, damage = check(text, sys.argv[1:])
    for r in residue:
        print(f"DRAFT CHROME SURVIVED in the adopted document: {r!r}", file=sys.stderr)
    for d in damage:
        print(f"SUBSTANTIVE TEXT DAMAGED — missing: {d!r}", file=sys.stderr)
    return 1 if (residue or damage) else 0


if __name__ == "__main__":
    raise SystemExit(main())
