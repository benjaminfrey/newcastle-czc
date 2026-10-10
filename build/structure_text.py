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
_FM_LABELS = (("article-name:", "Article title: "), ("article-number:", "Article number: "))


def _clean(text: str) -> str:
    text = " ".join(text.split()).strip(" \"“”")
    for token in _RESERVED:
        text = text.replace(token, token.replace("-", " "))
    return text[:100]


def heading_label(line: str) -> str:
    """A heading's text, without its #s or a trailing {#id}. The two frontmatter
    lines split_markdown counts as headings read as the Article's title and
    number, not as raw YAML."""
    stripped = line.strip()
    for key, label in _FM_LABELS:
        if stripped.startswith(key):
            return _clean(label + stripped[len(key):].strip().strip("\"'"))
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


def classify_blocks(old_blocks: list[str], new_blocks: list[str]) -> dict:
    """Which raw blocks were added, removed or changed between two versions of
    one Article -- decided ONCE here, so the disclosure page and the in-text notes
    cannot disagree.

    1. A block whose exact content exists on both sides is unchanged, wherever it
       sits: a reordered table is not a change.
    2. The remaining blocks are paired by caption, in order: a pair is CHANGED
       (same caption, different content); an unpaired old block is REMOVED; an
       unpaired new block is ADDED.
    Returns {"added": [new indices], "removed": [old indices],
             "changed": [(old index, new index)]}.
    """
    from collections import Counter, defaultdict

    common = Counter(old_blocks) & Counter(new_blocks)
    left_old, left_new = [], []
    budget = Counter(common)
    for i, b in enumerate(old_blocks):
        if budget[b]:
            budget[b] -= 1
        else:
            left_old.append(i)
    budget = Counter(common)
    for j, b in enumerate(new_blocks):
        if budget[b]:
            budget[b] -= 1
        else:
            left_new.append(j)
    by_cap_old, by_cap_new = defaultdict(list), defaultdict(list)
    for i in left_old:
        by_cap_old[block_caption(old_blocks[i])].append(i)
    for j in left_new:
        by_cap_new[block_caption(new_blocks[j])].append(j)
    out = {"added": [], "removed": [], "changed": []}
    for cap in set(by_cap_old) | set(by_cap_new):
        olds, news = by_cap_old.get(cap, []), by_cap_new.get(cap, [])
        out["changed"] += list(zip(olds, news))
        out["removed"] += olds[len(news):]
        out["added"] += news[len(olds):]
    for k in out:
        out[k].sort()
    return out
