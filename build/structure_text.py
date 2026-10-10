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
        if cap == UNTITLED:      # no caption to pair on: never pair two untitled blocks
            out["removed"] += olds
            out["added"] += news
            continue
        out["changed"] += list(zip(olds, news))
        out["removed"] += olds[len(news):]
        out["added"] += news[len(olds):]
    for k in out:
        out[k].sort()
    return out


_H2 = re.compile(r"^\s*##[ \t]")
_HN = re.compile(r"^\s*#{3,6}[ \t]")
_LEADING_NUMBER = re.compile(r"^\d+[A-Za-z]?\.\s*")


def heading_keys(lines: list[str]) -> list[str]:
    """A key per heading line, for ALIGNING two versions of an Article. A section
    heading ("## 3. TITLE") keys as its full stripped text. A deeper heading keys
    as "{its section's title without the number} / {its own text}", so two
    sections that reuse sub-heading names ("a. DEFINITION") do not collide, and a
    renumbered section keeps its sub-headings' keys. Frontmatter lines and
    headings above the first section key as themselves."""
    keys, parent = [], None
    for line in lines:
        if _H2.match(line):
            parent = _LEADING_NUMBER.sub("", heading_label(line))
            keys.append(line.strip())
        elif _HN.match(line) and parent is not None:
            keys.append(f"{parent} / {heading_label(line)}")
        else:
            keys.append(line.strip())
    return keys


def classify_headings(old: list[str], new: list[str]) -> dict:
    """Which heading LINES were added, removed or changed between two versions
    of one Article -- decided once, for the page and the in-text notes alike.
    Aligned on heading_keys (section-qualified). Equal runs are unchanged. Inside every other run, old and new headings are
    paired greedily in order (an identical line first) when their labels are similar enough to be the
    same heading retitled (difflib ratio >= 0.5) -> CHANGED; the rest are
    REMOVED / ADDED.
    Returns {"added": [new idx], "removed": [old idx], "changed": [(old idx, new idx)]}."""
    import difflib
    out = {"added": [], "removed": [], "changed": []}
    sm = difflib.SequenceMatcher(None, heading_keys(old), heading_keys(new), autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        js = list(range(j1, j2))
        paired = set()
        for i in range(i1, i2):
            # A line identical on both sides is unchanged even when its key moved
            # (the sub-headings of a retitled section); else pair a retitle by similarity.
            same = next((j for j in js if old[i].strip() == new[j].strip()), None)
            match = same if same is not None else next((j for j in js if difflib.SequenceMatcher(
                None, heading_label(old[i]), heading_label(new[j])).ratio() >= 0.5), None)
            if match is None:
                out["removed"].append(i)
            else:
                if same is None:
                    out["changed"].append((i, match))
                paired.add(match)
                js = [j for j in js if j > match]       # keep pairs in order
        out["added"] += [j for j in range(j1, j2) if j not in paired]
    for k in out:
        out[k].sort()
    return out
