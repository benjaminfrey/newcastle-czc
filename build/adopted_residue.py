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


def main() -> int:
    text = sys.stdin.read()
    residue = find_residue(text)
    damage = find_damage(text)
    for r in residue:
        print(f"DRAFT CHROME SURVIVED in the adopted document: {r!r}", file=sys.stderr)
    for d in damage:
        print(f"SUBSTANTIVE TEXT DAMAGED — missing: {d!r}", file=sys.stderr)
    return 1 if (residue or damage) else 0


if __name__ == "__main__":
    raise SystemExit(main())
