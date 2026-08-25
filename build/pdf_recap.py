#!/usr/bin/env python3
"""Page and blank-page counts for one or more PDFs (ADOPTION-SPEC.md §6.5:
"page counts and blank counts recorded for each artifact").

A page counts as blank only if it has NEITHER extractable text NOR any
embedded image -- matching exactly how this build's own pad pages are made
(build-full-czc.sh / build-standalone.sh: `fitz.new_page()`, nothing drawn).
Text-only emptiness would misclassify a map or plate page (vector art, no
running head) as blank; this narrower test does not.

Usage: pdf_recap.py "<label>=<path>" [...]
Prints one line per PDF: "<label>: N pages, B blank".
"""
from __future__ import annotations

import sys

import fitz  # PyMuPDF -- already a build dependency (build-full-czc.sh uses it)


def counts(path: str) -> tuple[int, int]:
    doc = fitz.open(path)
    blanks = 0
    for page in doc:
        if not page.get_text().strip() and not page.get_images(full=True):
            blanks += 1
    n = len(doc)
    doc.close()
    return n, blanks


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: pdf_recap.py \"<label>=<path>\" [...]", file=sys.stderr)
        return 1
    for arg in sys.argv[1:]:
        label, _, path = arg.partition("=")
        n, blanks = counts(path)
        print(f"  {label:35s} {n:4d} pages, {blanks} blank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
