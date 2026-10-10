#!/usr/bin/env python3
"""Plain-words names for the parts of an Article a redline cannot mark word by
word: its headings and its raw-Typst tables and figures.

The redline's in-text notes (redline-text.py) and the disclosure page
(structural_note.py, via czc_diff.structural_changes) both name these parts, so
they share one namer and cannot disagree.

A label is an ordinary string placed in a body paragraph of the marked prose,
which is also split-article-03.py's input -- and that splitter finds its markers
by SUBSTRING. So a label never carries a split-marker token.
"""
from __future__ import annotations

import re

UNTITLED = "an untitled table or figure"
_FENCE_LINE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
_CAPTION = re.compile(r"\b((?:TABLE|FIGURE|EXHIBIT)\s+\d+(?:\.\d+)?[A-Za-z]?\b[^\n\[\]]*)")
_HEADING = re.compile(r"^\s*#{1,6}[ \t]+(.*?)\s*(?:\{[^}]*\})?\s*$")
_RESERVED = ("TYPE-PAGES", "STREET-TYPE-EXHIBITS")


def _clean(text: str) -> str:
    text = " ".join(text.split()).strip(" \"“”")
    for token in _RESERVED:
        text = text.replace(token, token.replace("-", " "))
    return text[:100]


def heading_label(line: str) -> str:
    """A heading's text, without its #s or a trailing {#id}."""
    m = _HEADING.match(line)
    return _clean(m.group(1) if m else line)


def block_caption(block: str) -> str:
    """The first TABLE / FIGURE / EXHIBIT caption in a raw block's non-comment
    lines, or UNTITLED."""
    for line in block.split("\n"):
        if _FENCE_LINE.match(line) or line.strip().startswith("//"):
            continue
        m = _CAPTION.search(line)
        if m:
            return _clean(m.group(1))
    return UNTITLED
