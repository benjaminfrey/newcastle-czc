#!/usr/bin/env python3
"""Extract the ADOPTED Newcastle Core Zoning Code (docs/Newcastle Core Zoning
Code.pdf, READ-ONLY) into rulesets/adopted/articles.json — a node tree in the
same shape a future DRAFT parser (over source/article-0N-*.md) would produce,
so engine/ and llm/ can eventually consume either ruleset through one schema.

Implements the W2 "extract the adopted Code" task. Not yet named in
CONTRACT.md; §4's schemas cover districts.json/use-matrix.json only. This
module documents its own schema below and is written to slot into that
section later without reshaping the tree.

REUSED IDIOM (do not reinvent): extract/verso.py and extract/recto.py are the
proven PyMuPDF positional-extraction technique for THIS EXACT PDF — span
dicts keyed by (x, y, size, font, color), heading detection by bold+color+
size, list nesting by marker-x clustering. build/toc_entries.py demonstrates
the same signals at document scale (opener/section font-color/size bands).
This module reuses all three ideas but adapts them to the *body* Articles
(1, 3-8), which verso.py/recto.py never touch — those two only ever see the
Article-2 district *spread* pages, which this module explicitly SKIPS.

------------------------------------------------------------------------------
LAYOUT GRAMMAR (measured on this exact PDF, see docstring bottom for probe
transcript references):

  Every content page (after the 3-page front matter) carries, per the house
  style CONTRACT.md §8.2 already names (article_blue #367AAC, body_dark
  #231F20, subsection_gray #7C766F):

    - A rotated white "ARTICLE N" tab, Bold, 14pt, color 0xFFFFFF, on EVERY
      page of that Article (not just the first) — text matches exactly
      r"^ARTICLE\\s+(\\d+)$". This is the most reliable per-page article-number
      signal: it changes on the page where the layout hands off to the next
      Article, at physical (0-indexed) pages 3, 9, 37, 45, 57, 67, 79, 99.
    - A 33pt "ARTICLE N" (Book) + 33pt NAME (Bold), both color 0x367AAC, at
      x=45, on the Article's FIRST content page only — this is the article
      OPENER, giving the Article's display name verbatim from the PDF
      (mirrors build/toc_entries.py's OPENER_SZ, just larger here: 33pt not
      30-35, so OPENER_SZ is widened slightly to catch it).
    - A running head (Bold 11pt, color 0x7C766F, y<40) repeating the Article
      name on every page — same visual style as a subsection heading but
      excluded by the y<40 chrome band, never fed to the parser.
    - A footer (Bold 10pt, mixed colors, y>740) with the printed page number
      and "Newcastle Core Zoning Code" / the amendment date — also excluded.
    - TWO reading columns per page, left and right, at x offsets that MIRROR
      between facing pages (binding gutter) — so column split is computed
      per page from the actual span x-clustering (as recto.py does), never
      hard-coded to a fixed pixel.
    - "N. TITLE" SECTION headings: Bold, size 13-15pt, color 0x367AAC
      (ARTICLE_BLUE) — "## <int>. SECTION TITLE" in draft-grammar terms.
    - "a. TITLE" SUBSECTION headings: Bold, size 10-12pt, color 0x7C766F
      (SUBSECTION_GRAY) — "### <letter>. SUBSECTION TITLE" in draft grammar.
      In Article 8 (Definitions) this same style renders a bare "Term:" with
      NO letter marker — handled as a `definition` leaf, not a subsection.
    - Body text: Light, size 8-9pt, color 0x231F20 (BODY_DARK). An ordered
      list item is a marker SPAN ("1.\\t", "a.\\t", "iii.\\t" — the tab is a
      literal character in the span, matching verso.py's MARKER convention)
      followed by its text on the same line; nesting level is NOT read off
      the marker glyph (letters and lowercase roman numerals collide, e.g.
      "i." could be either) but off the marker's X position via a small
      per-list indent STACK (see `_level_of`), so it self-calibrates to
      whichever column/page the list is currently flowing through.

  Reading order is document order: for each page (front matter and district-
  spread pages excluded, see SKIP_PAGES), left column top-to-bottom, then
  right column top-to-bottom, then the next page. Concatenated across pages
  this reproduces the linear flow the drafters intended — confirmed by a
  numbered item's list continuing seamlessly from the bottom of one page's
  column into the top of the next page's column (Art. 1 §1 item 6->7 spans
  physical pages 3->4 exactly this way).

DISTRICT SPREAD PAGES ARE SKIPPED FOR TEXT (per the W2 task brief): physical
0-indexed pages 11-36 (13 district verso/recto pairs — the same VERSO_IDX
extract/gen_districts.py already uses, recto = verso+1). Article 2's PROSE
sections (DISTRICTS, LOTS, SETBACKS, SPECIAL MAP REQUIREMENTS, CIVIC
DISTRICT) live on physical pages 9-10, *before* the first spread, and ARE
extracted normally.

------------------------------------------------------------------------------
NODE SCHEMA ("newcastle.articles/1.0.0") — the "SAME node schema the draft
parser produces" once one exists (none exists yet in this repo; this module
is establishing it, deliberately shaped so a source/article-0N-*.md parser
could target the identical tree):

    {
      "id": "art7.12.f.1.c",          # dotted path; also stable citation key
      "kind": "article"|"section"|"subsection"|"item"|"para"|"definition",
      "article": 7,                   # article number IN THIS SCHEME
      "number": "12"|"f"|"1"|"c"|None,# this node's own marker (verbatim)
      "heading": "SUBDIVISION"|None,  # article/section/subsection/definition
                                       # title; None for item/para
      "text": "..."|None,             # item/para/definition body text;
                                       # None for article/section/subsection
      "children": [ ... ],            # nested nodes, document order
      "source_ref": {"pdf_page": 86, "bbox": [x0,y0,x1,y1]}
    }

`source_ref.pdf_page` is the 1-indexed PHYSICAL page in
docs/Newcastle Core Zoning Code.pdf (i.e. `doc.load_page(pdf_page - 1)` in
PyMuPDF) — NOT the printed footer page number, which is offset by the 3-page
front matter. `bbox` is the [x0,y0,x1,y1] of the node's own heading/opening
span (merged across a wrapped multi-line heading); item/para/definition nodes
that continue onto later pages/columns also carry `source_ref.more_pages`,
the full ordered list of physical pages their text touches.

Runtime (app/) NEVER imports this module or re-parses the PDF; it only reads
the committed rulesets/adopted/articles.json this module writes, exactly like
every other ruleset_build/*.py module (CONTRACT.md §4 preamble).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent

PDF_PATH = REPO_ROOT / "docs" / "Newcastle Core Zoning Code.pdf"
OUT_PATH = APP_ROOT / "rulesets" / "adopted" / "articles.json"

SCHEMA = "newcastle.articles/1.0.0"
RULESET_KEY = "adopted"

# --- measured style constants (see module docstring) ------------------------
ARTICLE_BLUE = 0x367AAC
SUBSECTION_GRAY = 0x7C766F
BODY_DARK = 0x231F20
WHITE = 0xFFFFFF

# PyMuPDF version drift, not document drift: verified by direct measurement
# that THIS environment's pymupdf (1.28.2) decodes every "article blue" span
# in the PDF (opener/section/tab roles alike, hundreds of spans, same
# document, same sha256 as when ARTICLE_BLUE was first measured) as
# 0x3E7AAC -- exactly +8 in the red channel from ARTICLE_BLUE, green/blue
# channels identical -- while SUBSECTION_GRAY/BODY_DARK/WHITE all still
# decode exactly as originally measured. A single anti-aliasing/gamma
# rounding difference across a pymupdf version bump is a rendering-quantizer
# artifact, not a legal or structural ambiguity, so a small per-channel
# tolerance on the ARTICLE_BLUE role (well clear of SUBSECTION_GRAY, the
# nearest other role color -- min channel distance 62) is the right fix,
# not re-measuring the constant (which would just re-break under whichever
# pymupdf version decodes it the original way).
_COLOR_TOL = 12


def _color_close(a: int, b: int, tol: int = _COLOR_TOL) -> bool:
    ar, ag, ab = (a >> 16) & 0xFF, (a >> 8) & 0xFF, a & 0xFF
    br, bg, bb = (b >> 16) & 0xFF, (b >> 8) & 0xFF, b & 0xFF
    return abs(ar - br) <= tol and abs(ag - bg) <= tol and abs(ab - bb) <= tol

SECTION_SZ = (12.5, 15.5)      # "N. TITLE" — widened slightly (Art 6 measured 13.8)
SUBSECTION_SZ = (9.5, 12.5)    # "a. TITLE" / "Term:"
BODY_SZ = (7.8, 9.3)
OPENER_SZ = (30.0, 35.0)       # 33pt article-opener title (measured exactly 33.0)
TAB_SZ = (13.0, 15.0)          # rotated "ARTICLE N" tab
# A table's own column-header / row-label cells (e.g. TABLE 7.1's "NOTICE" /
# "PUBLIC HEARING" headers, TABLE 3.1's "D1".."SD-CIVIC" row labels) render
# Bold + SUBSECTION_GRAY -- same weight/color as an "a. SUBSECTION" heading --
# but measured narrower, at exactly 9.0pt, than SUBSECTION_SZ's 9.5pt floor
# (probed directly on pages 44, 50, 58, 82). Before FINDING 4's fix this
# fell through EVERY category (too small for _is_subsection, wrong
# font/color for _is_body) and was silently dropped rather than captured or
# leaked; see _is_table_label / the table-capture logic in build_tree.
TABLE_LABEL_SZ = (7.5, 9.4)

TOP_CHROME_Y = 40.0     # running head lives above this
BOTTOM_CHROME_Y = 738.0 # footer lives below this

ARTICLE_TAB_RE = re.compile(r"^ARTICLE\s+(\d+)$", re.IGNORECASE)
# whole-LINE marker regex: "<marker>.  <rest of line>" — matches numeric
# ("1", "12") or lowercase-letter-run markers ("a", "iii"; roman numerals are
# just letter runs here, never interpreted numerically — see _level_of).
LINE_MARKER_RE = re.compile(r"^\s*(\d+|[a-z]+)\.\s*(.*)$", re.DOTALL)
# a genuine BODY-list marker occupies its OWN entire span AND is literally
# tab-terminated ("1.\t", "a.\t" — verified byte-for-byte: every real marker
# span in this PDF contains a "\t" right after the dot; the tab is what
# produces the hanging indent). Applied to the FIRST SPAN of a body line,
# never to the line's joined text, and the "\t" is REQUIRED, not just
# permitted by \s* — a stray in-sentence number that starts a wrapped line
# (verified case: "...meet Title 23, Section\n704." wraps to a lone span
# "704." with NO tab) must not be mistaken for a marker.
MARKER_SPAN_RE = re.compile(r"^(\d+|[a-z]+)\.\t")
# a "Term:" definition heading (Article 8): ends in a colon, no letter marker.
DEFINITION_RE = re.compile(r"^(.*\S)\s*:\s*$")

# A table caption ("TABLE 7.1  NOTICES & PUBLIC HEARINGS", "TABLE 4.1
# ALLOWABLE ADDITION LOCATION BY DISTRICT") renders at the SAME font
# size/weight/color as a subsection heading (11pt Bold #7C766F, verified by
# probing the actual PDF: page 82's "TABLE 7.1  NOTICES & PUBLIC HEARINGS"
# and page 48's "TABLE 4.1    ALLOWABLE ADDITION"/"LOCATION BY DISTRICT" both
# carry that exact style) but is NOT a lettered subsection marker, so it
# used to fall through LINE_MARKER_RE unmatched and be silently dropped —
# never mis-attributed, per this module's "never guess" rule, but also never
# captured, which meant a real "Table N.M" that appears verbatim in the
# adopted Code had no node at all for a citation to resolve against. Matched
# explicitly, by heading text, so it becomes its own "table" kind node
# (verified against the Code's real Table numbering: 3.1, 4.1-4.7, 5.1-5.21,
# 7.1, etc., all rendered this same way).
TABLE_CAPTION_RE = re.compile(r"^TABLE\s+(\d{1,2}\.\d{1,2})\s*[:.]?\s*(.*)$", re.IGNORECASE)

# 13 district verso pages (0-indexed) — verso.py/recto.py/gen_districts.py's
# VERSO_IDX; recto = verso+1. These 26 physical pages are the district
# spreads and are skipped for Article-2 BODY TEXT per the W2 brief (the
# district data itself lives in source/article-02-data.json /
# rulesets/adopted/use-matrix.json, not here).
_DISTRICT_VERSO_IDX = [11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35]
SKIP_PAGES = frozenset(p for v in _DISTRICT_VERSO_IDX for p in (v, v + 1))


class ExtractionError(RuntimeError):
    """A structural assumption about the PDF's layout did not hold. Fails
    loudly rather than emitting a silently-wrong tree (CONTRACT.md §1 S7's
    spirit, applied to extraction instead of legal-value normalization)."""


# =============================================================================
# Pass 0 — span collection
# =============================================================================

def _spans(page) -> list[dict]:
    out = []
    for blk in page.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                if sp["text"].strip() == "":
                    continue
                out.append(dict(
                    x=round(sp["bbox"][0], 1), y=round(sp["bbox"][1], 1),
                    x1=round(sp["bbox"][2], 1), y1=round(sp["bbox"][3], 1),
                    sz=round(sp["size"], 1), font=sp["font"], col=sp["color"],
                    t=sp["text"],
                ))
    return out


def _is(sp, sz_range, color, bold=None):
    if not (sz_range[0] <= sp["sz"] <= sz_range[1]):
        return False
    if not _color_close(sp["col"], color):
        return False
    if bold is True and "Bold" not in sp["font"]:
        return False
    if bold is False and "Light" not in sp["font"]:
        return False
    return True


def _is_tab(sp):
    return _is(sp, TAB_SZ, WHITE, bold=True) and ARTICLE_TAB_RE.match(sp["t"].strip())


def _is_section(sp):
    return _is(sp, SECTION_SZ, ARTICLE_BLUE, bold=True)


def _is_subsection(sp):
    return _is(sp, SUBSECTION_SZ, SUBSECTION_GRAY, bold=True)


# Body text is overwhelmingly BODY_DARK (0x231F20), but ~585 spans across 49
# pages render in pure black (0x000000) instead — a PDF-authoring artifact
# (verified: same Light font, same 8.5pt size, same list-item role; only the
# color channel differs, e.g. the Article 8 "Agricultural Buildings"/
# "Agricultural Use" definitions). Both are accepted as body text so those
# spans are not silently dropped.
_BODY_COLORS = frozenset({BODY_DARK, 0x000000})


def _is_body(sp):
    return (BODY_SZ[0] <= sp["sz"] <= BODY_SZ[1] and sp["col"] in _BODY_COLORS
            and "Light" in sp["font"])


def _is_table_label(sp):
    return _is(sp, TABLE_LABEL_SZ, SUBSECTION_GRAY, bold=True)


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


# =============================================================================
# Pass 1 — per-page article-number map + article openers
# =============================================================================

def _page_article_map(doc) -> dict[int, int]:
    """physical 0-indexed page -> article number, via the rotated tab that
    appears on EVERY page of its Article (not just the opener)."""
    out = {}
    for pno in range(doc.page_count):
        for sp in _spans(doc[pno]):
            if _is_tab(sp):
                out[pno] = int(ARTICLE_TAB_RE.match(sp["t"].strip()).group(1))
                break
    return out


def _article_openers(doc, page_article: dict[int, int]) -> dict[int, tuple[str, dict]]:
    """article number -> (display name, bbox of the opener heading), read off
    the 33pt opener on that Article's first physical page."""
    starts: dict[int, int] = {}
    for pno, art in page_article.items():
        if art not in starts or pno < starts[art]:
            starts[art] = pno
    out = {}
    for art, pno in starts.items():
        pieces = []
        for sp in _spans(doc[pno]):
            if _is(sp, OPENER_SZ, ARTICLE_BLUE):
                pieces.append(sp)
        pieces.sort(key=lambda s: s["y"])
        # first piece is "ARTICLE N" (Book weight), the rest is the name
        # (Bold weight), possibly wrapped across >1 line.
        name_pieces = [p for p in pieces if "Bold" in p["font"]]
        name = _clean(" ".join(p["t"] for p in name_pieces))
        if not name:
            raise ExtractionError(f"no 33pt opener name found on page {pno} for Article {art}")
        bbox = [min(p["x"] for p in pieces), min(p["y"] for p in pieces),
                max(p["x1"] for p in pieces), max(p["y1"] for p in pieces)]
        out[art] = (name, {"pdf_page": pno + 1, "bbox": bbox})
    return out


# =============================================================================
# Pass 2 — per-page column split + line grouping
# =============================================================================

def _body_spans(page) -> list[dict]:
    """Spans inside the content band, chrome (tab/running-head/footer/opener)
    excluded. Chrome is excluded by Y-band + exact style match, never by
    guessing — anything left over is real body content."""
    out = []
    for sp in _spans(page):
        if not (TOP_CHROME_Y < sp["y"] < BOTTOM_CHROME_Y):
            continue
        if _is_tab(sp):
            continue
        if _is(sp, OPENER_SZ, ARTICLE_BLUE):
            continue
        out.append(sp)
    return out


def _column_split(spans: list[dict]) -> float:
    """Largest-gap column split, mirroring extract/recto.py's col_split
    logic — margins mirror between facing pages, so this is computed fresh
    per page rather than hard-coded."""
    xs = sorted(set(round(s["x"]) for s in spans))
    if len(xs) < 2:
        return 290.0
    gaps = [(xs[i + 1] - xs[i], (xs[i + 1] + xs[i]) / 2) for i in range(len(xs) - 1)]
    gap, mid = max(gaps)
    if gap < 60:
        # no real 2-column gap on this page (rare: a graphic/table-only
        # page) — fall back to a single column so nothing is dropped.
        return 1e9
    return mid


def _lines(spans: list[dict]) -> list[list[dict]]:
    """Group spans sharing a Y (rounded) into a reading line, spans in
    x-order. Two spans on one baseline share the exact bbox y in this PDF
    (verified: marker + title spans both report the same y0)."""
    buckets: dict[float, list[dict]] = {}
    for s in spans:
        buckets.setdefault(s["y"], []).append(s)
    lines = []
    for y in sorted(buckets):
        lines.append(sorted(buckets[y], key=lambda s: s["x"]))
    return lines


def _page_reading_lines(page, pno: int) -> list[tuple[int, list[dict]]]:
    """(physical_page, line) tuples in document reading order for one page:
    left column top-to-bottom, then right column top-to-bottom."""
    body = _body_spans(page)
    if not body:
        return []
    split = _column_split(body)
    left = [s for s in body if s["x"] < split]
    right = [s for s in body if s["x"] >= split]
    out = []
    for col in (left, right):
        for line in _lines(col):
            out.append((pno + 1, line))  # 1-indexed physical page
    return out


# =============================================================================
# Pass 3 — the tree builder (single linear scan over reading-ordered lines)
# =============================================================================

def _line_text(line: list[dict]) -> str:
    return _clean("".join(s["t"] for s in line))


def _line_bbox(line: list[dict]) -> list[float]:
    return [min(s["x"] for s in line), min(s["y"] for s in line),
            max(s["x1"] for s in line), max(s["y1"] for s in line)]


_ROMAN_SEQ = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
              "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx"]


def _next_alpha(marker: str) -> str:
    """'a'->'b', ..., 'z'->'aa' (bijective base-26, Excel-column style)."""
    idx = 0
    for ch in marker:
        idx = idx * 26 + (ord(ch) - ord("a") + 1)
    idx += 1
    out = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        out = chr(ord("a") + rem) + out
    return out


def _next_roman(marker: str) -> str | None:
    try:
        i = _ROMAN_SEQ.index(marker)
    except ValueError:
        return None
    return _ROMAN_SEQ[i + 1] if i + 1 < len(_ROMAN_SEQ) else None


class _Levels:
    """Nesting-depth tracker for ONE open list run (reset at every new
    subsection/definition, and on every fresh digit marker).

    NOT x-position based, on purpose: markers repeat across the 2-column,
    mirrored-margin layout at DIFFERENT absolute x per column (verified: the
    Art. 7 §12.f "d." standard resumes in the next column at x=375, not the
    x=114 its sibling "c." used one column earlier) — so an indentation
    stack keyed on x misattributes a column-crossing list every time. Depth
    is instead read off the marker's own SEQUENCE, exactly as a human reader
    would: level 0 is always digits ("1.", "2.", ...) restarting a fresh
    item, resetting everything below it; deeper levels are always letters
    ("a.", "b.", ...) or lowercase roman numerals ("i.", "ii.", ...), which
    are text-ambiguous with each other ("i." is both a letter and a roman
    numeral) but are disambiguated by which open level's "next expected
    marker" they continue — checked deepest-first — or, failing that,
    whether they are the conventional START of a fresh nested sequence
    ("a." opens a new letter level, "i." opens a new roman level) directly
    under whichever level is currently deepest.
    """

    def __init__(self):
        self.stack: list[dict] = []   # [{"kind": "digit"|"alpha"|"roman", "marker": str, "node": dict}]

    def reset(self):
        self.stack = []

    def level_for(self, marker: str, page: int) -> int:
        marker = marker.lower()
        if marker.isdigit():
            self.stack = [{"kind": "digit", "marker": marker, "node": None}]
            return 0
        # 1) continues the deepest-first matching open level's sequence?
        for depth in range(len(self.stack) - 1, -1, -1):
            entry = self.stack[depth]
            if entry["kind"] in ("digit", "seed"):
                continue
            nxt = _next_alpha(entry["marker"]) if entry["kind"] == "alpha" else _next_roman(entry["marker"])
            if nxt == marker:
                entry["marker"] = marker
                del self.stack[depth + 1:]
                return depth
        # 2) opens a fresh nested sequence under the current deepest level?
        if marker == "a":
            self.stack.append({"kind": "alpha", "marker": "a", "node": None})
            return len(self.stack) - 1
        if marker == "i":
            self.stack.append({"kind": "roman", "marker": "i", "node": None})
            return len(self.stack) - 1
        # 3) DEFECT 1/2 hardening: a marker that neither continues any open
        # level's sequence NOR opens a fresh one is exactly a gap/truncation
        # symptom (or the "i" roman-vs-alpha collision if it's ever reached
        # this branch) — this used to be silently absorbed as "a sibling of
        # whatever is currently deepest" (a guess, not a determination) and
        # is now a hard failure with the page, matching CONTRACT.md S7's
        # "no silent guessing" posture and the "RAISE, never warn" brief.
        raise ExtractionError(
            f"pdf_page {page}: list marker {marker!r} does not continue any open "
            f"sequence (open levels: {[(e['kind'], e['marker']) for e in self.stack]}) "
            f"and is not a fresh 'a'/'i' opener — refusing to guess a level for it"
        )

    def set_node(self, level: int, node: dict):
        self.stack[level]["node"] = node

    def parent_children(self, level: int, subsection_children: list) -> list:
        return subsection_children if level == 0 else self.stack[level - 1]["node"]["children"]

    def deepest(self):
        return self.stack[-1]["node"] if self.stack else None


def _new_node(kind, article, number, heading, text, page, bbox) -> dict:
    return {
        "kind": kind, "article": article, "number": number, "heading": heading,
        "text": text, "children": [],
        "source_ref": {"pdf_page": page, "bbox": bbox},
        "_id": None,  # filled in by _assign_ids after the tree is complete
    }


# =============================================================================
# Pass 3.5 — table-capture finalization (FINDING 4 fix).
#
# THE DEFECT: a "TABLE N.M ..." caption already got its own `kind: "table"`
# node (see TABLE_CAPTION_RE above), but nothing ever captured the table's
# OWN subsequent content onto that node. Every line belonging to the table --
# column headers, row labels, cell values, the dot-glyph legend -- fell
# through to whichever ordinary body-text handling was active, which meant
# it kept appending onto `levels.deepest()`: the last ITEM node that was open
# immediately before the caption. That is the same defect class as the
# truncated-list bug fixed twice before (DEFECT 1/2 above): a structural
# element silently losing its content into a neighbour. Verified against
# EVERY table in rulesets/adopted/articles.json before this fix (all 7):
# every one of them had corrupted the item immediately preceding it with the
# table's own row/legend text concatenated on with no delimiter (e.g. Table
# 7.1 turned art7.6.e.2's real text, "Time limit extentions shall be
# recorded in writing.", into "...writing. and in a Small Project plan Large
# Project Plan ... Required May be required").
#
# THE FIX: `build_tree` now tracks an explicit `table_capture` state (see the
# TABLE_CAPTION_RE branch and the new `_is_table_label`-gated branch, both
# below) that intercepts every line belonging to the currently-open table --
# instead of leaking into the neighbour item, it lands on the table's own
# buffer and is finalized here, once, when the table closes (next section /
# subsection / table caption / end of document).
#
# THE GRID: only ONE of the 7 tables ("NOTICES & PUBLIC HEARINGS", i.e.
# Table 7.1 -- the one clocks.json's `applies_to` values must be checked
# against) is actually gridded into real `columns`/`rows`/`notes`, matching
# the draft parser's markdown-table schema exactly (verified byte-for-byte
# against rulesets/draft-v0.22/articles.json's "TABLE 8.1 NOTICES & PUBLIC
# HEARINGS", the same table under the draft's Article renumbering). Its
# "Required"/"May be required" cells are not text at all -- they are vector-
# drawn circle glyphs (a filled dot vs. a filled-then-half-outlined dot),
# never available as PDF text spans -- so `_grid_notices_hearings_table`
# reads them straight from `page.get_drawings()`, classified by the drawn
# path's own item count (a full circle traces exactly 4 Bezier arcs with no
# closing line; a half-filled circle adds a straight line back to center,
# always pushing the item count above 4 -- measured directly against every
# cell on PDF page 82 and cross-checked against the draft table's already-
# correct ●/◐ values: 100% agreement, 14/14 dot cells).
#
# The other 6 tables (Article 3-5 dimensional/site-standard tables, wholly
# unrelated to the deadline engine) each use a VISUALLY DIFFERENT grammar
# for their own rows (some row labels are Bold+gray district codes, some are
# ordinary Light body text; some rows pack 2-4 columns' worth of values onto
# one line with no space between adjacent cells in the raw PDF spans). Blind-
# gridding all 6 without individually verifying each one's own layout would
# risk silently MISATTRIBUTING a cell -- exactly what CONTRACT.md §1 S7 ("no
# silent guessing") forbids. So for those 6, this module stops the leak (the
# actual Finding 4 defect) and preserves 100% of the table's own content --
# nothing is dropped, nothing corrupts a neighbour -- as a verbatim,
# reading-order `raw_text` transcript on the table node itself, explicitly
# flagged `extraction: "caption_and_raw_text_only"` so no downstream reader
# ever mistakes the absence of `columns`/`rows` for "this table has no
# content" or silently trusts a row/column split that was never verified.
# Logged to DECISIONS-NEEDED.md (see build_document's caller / the W-task
# report) rather than resolved by guessing.
# =============================================================================

NOTICES_HEARINGS_HEADING = "NOTICES & PUBLIC HEARINGS"

# The row order Table 7.1 prints in, transcribed directly off PDF page 82
# and verified identical (same 9 labels, same order) to the already-correct
# markdown table rulesets/draft-v0.22/articles.json carries for the same
# table under its own Article numbering ("TABLE 8.1"). Asserted, not
# assumed: `_grid_notices_hearings_table` raises if a future re-extraction
# ever produces a different set, rather than silently gridding a table that
# has actually changed shape.
EXPECTED_NOTICE_HEARING_ROWS: tuple[str, ...] = (
    "Small Project plan", "Large Project Plan", "Subdivision Plan",
    "Master Plan", "Plan Revision", "Special Permit", "Variance",
    "Land Conveyance", "Zoning Amendment",
)


def _dot_glyph_kind(drawing: dict) -> str:
    """'●' (Required, a full filled circle -- exactly 4 Bezier-arc path
    items and no straight-line item) or '◐' (May be required -- a half-
    filled circle, which PyMuPDF represents as the same 4 arcs PLUS a 2nd,
    partial arc-and-line pair closing back to center, always > 4 items).
    Measured directly against all 14 dot cells on PDF page 82 (7 rows x 2
    columns; the other 2 of the table's 9 rows print no dot at all) and
    cross-checked 14/14 against the draft parser's already-correct ●/◐
    transcription of the identical table -- see the Pass 3.5 docstring."""
    items = drawing.get("items") or []
    if len(items) == 4 and not any(it[0] == "l" for it in items):
        return "●"
    return "◐"


def _grid_notices_hearings_table(doc, node: dict, lines: list[tuple]) -> None:
    """Populates node['columns']/['rows']/['notes'] for the ONE table this
    module fully grids. `lines` is `table_capture["lines"]`: a list of
    (page1, role, text, raw_first_span_text, x, y) tuples in document
    reading order, `role` "label" (a table column-header cell, captured via
    `_is_table_label`) or "value" (an ordinary body-style row/legend line).
    Never called for any other table (see NOTICES_HEARINGS_HEADING gate in
    `_finalize_table_capture`)."""
    row_entries: list[tuple[str, float, float]] = []  # (text, x, y)
    notes: list[str] = []
    for page1, role, text, raw0, x, y in lines:
        if role != "value":
            continue
        # Legend lines ("Required" / "May be required") carry LITERAL
        # leading whitespace in their own PDF span text -- measured: row
        # labels ("Small Project plan", ...) carry none, the two legend
        # lines are indented 5 literal space characters in the source
        # (`'     Required'`), unlike every other indentation in this PDF,
        # which is conveyed purely by X position, never by literal spaces.
        if raw0.startswith("  "):
            notes.append(text)
        else:
            row_entries.append((text, x, y))

    got_rows = tuple(t for t, _, _ in row_entries)
    if got_rows != EXPECTED_NOTICE_HEARING_ROWS:
        raise ExtractionError(
            f"Table {node['number']} {node['heading']!r}: row labels changed shape -- "
            f"expected {EXPECTED_NOTICE_HEARING_ROWS}, got {got_rows}. Refusing to grid "
            f"a table whose row structure no longer matches what was verified against "
            f"the draft parser's identical table; re-verify before regridding."
        )
    if len(notes) != 2:
        raise ExtractionError(
            f"Table {node['number']} {node['heading']!r}: expected exactly 2 legend "
            f"lines (Required / May be required), captured {len(notes)}: {notes!r}"
        )

    pdf_page = node["source_ref"]["pdf_page"]
    page = doc[pdf_page - 1]
    row_label_x = row_entries[0][1]
    y_lo = min(y for _, _, y in row_entries) - 5.0
    y_hi = max(y for _, _, y in row_entries) + 15.0
    # Only fills clearly to the right of the row-label column and within the
    # table's own row band -- excludes any unrelated vector graphics
    # elsewhere on the page (none observed on page 82, but never assumed).
    fills = [
        d for d in page.get_drawings()
        if d["type"] == "f" and d["rect"].x0 > row_label_x + 30 and y_lo <= d["rect"].y0 <= y_hi
    ]

    xs = sorted({round((d["rect"].x0 + d["rect"].x1) / 2) for d in fills})
    if len(xs) < 2:
        raise ExtractionError(
            f"Table {node['number']} {node['heading']!r}: expected dot fills in 2 "
            f"columns (Notice / Public Hearing), found only {len(xs)} distinct x "
            f"position(s) among {len(fills)} fill(s)"
        )
    gaps = [(xs[i + 1] - xs[i], (xs[i + 1] + xs[i]) / 2) for i in range(len(xs) - 1)]
    _, col_split_x = max(gaps)

    grid = [["", ""] for _ in row_entries]
    unmatched = 0
    for d in fills:
        fy = d["rect"].y0
        idx = min(range(len(row_entries)), key=lambda i: abs(row_entries[i][2] - fy))
        if abs(row_entries[idx][2] - fy) > 10.0:
            unmatched += 1
            continue
        col = 0 if (d["rect"].x0 + d["rect"].x1) / 2 < col_split_x else 1
        grid[idx][col] = _dot_glyph_kind(d)
    if unmatched:
        raise ExtractionError(
            f"Table {node['number']} {node['heading']!r}: {unmatched} dot fill(s) "
            f"could not be matched to any row within tolerance -- refusing to guess"
        )

    node["columns"] = ["", "Notice", "Public Hearing"]
    node["rows"] = [[text, *cells] for (text, _, _), cells in zip(row_entries, grid)]
    node["notes"] = ["● = Required; ◐ = May be required"]


def _grid_or_flatten_table(doc, table_capture: dict) -> None:
    node = table_capture["node"]
    lines = table_capture["lines"]
    node["caption"] = _clean(f"TABLE {node['number']}  {node['heading']}") if node.get("number") else node["heading"]
    if (node.get("heading") or "").strip().upper() == NOTICES_HEARINGS_HEADING:
        _grid_notices_hearings_table(doc, node, lines)
    else:
        node["columns"] = []
        node["rows"] = []
        node["notes"] = []
        node["raw_text"] = _clean(" ".join(t for _, _, t, _, _, _ in lines)) or None
        node["extraction"] = "caption_and_raw_text_only"
    node["text"] = node["caption"]


def build_tree(pdf_path: Path = PDF_PATH) -> tuple[list[dict], dict]:
    """Returns (article_nodes, stats). stats carries everything --verify
    reports: per-article section counts, attributed/unattributed pages,
    coverage %."""
    import fitz  # local import: keeps `python -m ruleset_build.extract_adopted --help` fast

    if not pdf_path.exists():
        raise ExtractionError(f"adopted PDF not found: {pdf_path}")
    doc = fitz.open(str(pdf_path))
    try:
        page_article = _page_article_map(doc)
        openers = _article_openers(doc, page_article)

        content_pages = sorted(page_article)  # excludes the front-matter pages
        front_matter_pages = [p for p in range(doc.page_count) if p not in page_article]
        skip_pages = sorted(p for p in content_pages if p in SKIP_PAGES)
        scan_pages = [p for p in content_pages if p not in SKIP_PAGES]

        articles: dict[int, dict] = {}
        article_order: list[int] = []
        attributed_pages: set[int] = set()   # 1-indexed physical pages
        page_had_body: set[int] = set()      # pages with body content at all
        section_counts: dict[int, int] = {}

        current_article_num = None
        current_article = None
        current_section = None
        current_subsection = None
        levels = _Levels()
        # buffers for merging a heading that wraps across >1 line
        open_heading = None   # dict: {"node":..., "kind": "section"/"subsection"}
        # FINDING 4 fix: buffers a table's own content while its caption is
        # the most recently opened structural element, so that content lands
        # on the table node instead of leaking into whatever item/para was
        # open before the caption (see the Pass 3.5 docstring above).
        # {"node": <table node>, "lines": [(page1, role, text, raw0, x, y), ...]}
        table_capture = None

        def close_open_heading():
            nonlocal open_heading
            if open_heading is not None:
                node = open_heading["node"]
                node["heading"] = _clean(node["heading"])
                open_heading = None

        def finalize_table_capture():
            nonlocal table_capture
            if table_capture is not None:
                _grid_or_flatten_table(doc, table_capture)
                table_capture = None

        def mark_attributed(page1):
            attributed_pages.add(page1)

        for pno in scan_pages:
            page = doc[pno]
            reading_lines = _page_reading_lines(page, pno)
            if reading_lines:
                page_had_body.add(pno + 1)

            for page1, line in reading_lines:
                # --- article boundary -------------------------------------
                art = page_article[pno]
                if art != current_article_num:
                    close_open_heading()
                    finalize_table_capture()
                    if art not in articles:
                        name, ref = openers.get(art, (f"ARTICLE {art}", {
                            "pdf_page": page1, "bbox": _line_bbox(line)}))
                        node = _new_node("article", art, None, name, None,
                                          ref["pdf_page"], ref["bbox"])
                        articles[art] = node
                        article_order.append(art)
                        section_counts[art] = 0
                    current_article_num = art
                    current_article = articles[art]
                    current_section = None
                    current_subsection = None
                    levels.reset()

                first = line[0]
                text = _line_text(line)
                bbox = _line_bbox(line)

                # --- SECTION heading ---------------------------------------
                if _is_section(first):
                    m = LINE_MARKER_RE.match(text)
                    if m:
                        close_open_heading()
                        finalize_table_capture()
                        number, rest = m.group(1), m.group(2)
                        node = _new_node("section", art, number, rest, None, page1, bbox)
                        current_article["children"].append(node)
                        current_section = node
                        current_subsection = None
                        section_counts[art] += 1
                        levels.reset()
                        open_heading = {"node": node, "kind": "section"}
                        mark_attributed(page1)
                        continue
                    elif open_heading and open_heading["kind"] == "section":
                        open_heading["node"]["heading"] += " " + text
                        open_heading["node"]["source_ref"]["bbox"][2] = max(
                            open_heading["node"]["source_ref"]["bbox"][2], bbox[2])
                        open_heading["node"]["source_ref"]["bbox"][3] = max(
                            open_heading["node"]["source_ref"]["bbox"][3], bbox[3])
                        mark_attributed(page1)
                        continue
                    # a size/color match with no marker and no open section
                    # heading to continue: fall through to "unattributed"
                    # rather than guess.

                # --- SUBSECTION heading, or Article-8 "Term:" definition ---
                elif _is_subsection(first):
                    tm = TABLE_CAPTION_RE.match(text)
                    if tm:
                        # A table caption is an aside attached to whatever
                        # subsection/section is currently open -- it does
                        # NOT start a new subsection, so current_section /
                        # current_subsection are deliberately left untouched
                        # (unlike the subsection branch below); only
                        # open_heading tracks it, so a wrapped 2nd caption
                        # line ("LOCATION BY DISTRICT" following "TABLE 4.1
                        # ALLOWABLE ADDITION" one line later in the same
                        # reading-order column) still merges correctly.
                        close_open_heading()
                        finalize_table_capture()
                        num, rest = tm.group(1), tm.group(2)
                        parent = (current_subsection if current_subsection is not None
                                  else current_section if current_section is not None
                                  else current_article)
                        node = _new_node("table", art, num, rest, None, page1, bbox)
                        parent["children"].append(node)
                        open_heading = {"node": node, "kind": "table"}
                        table_capture = {"node": node, "lines": []}
                        mark_attributed(page1)
                        continue
                    m = LINE_MARKER_RE.match(text)
                    if m and re.fullmatch(r"[a-z]+", m.group(1)):
                        close_open_heading()
                        finalize_table_capture()
                        letter, rest = m.group(1), m.group(2)
                        parent = current_section if current_section is not None else current_article
                        node = _new_node("subsection", art, letter, rest, None, page1, bbox)
                        parent["children"].append(node)
                        current_subsection = node
                        levels.reset()
                        open_heading = {"node": node, "kind": "subsection"}
                        mark_attributed(page1)
                        continue
                    dm = DEFINITION_RE.match(text)
                    if dm and current_section is None:
                        # Article 8 flat "Term:" — attach directly to the
                        # article (Definitions has no numbered sections).
                        close_open_heading()
                        finalize_table_capture()
                        node = _new_node("definition", art, None, dm.group(1), "", page1, bbox)
                        current_article["children"].append(node)
                        current_subsection = node
                        levels.reset()
                        levels.stack = [{"kind": "seed", "marker": "", "node": node}]  # continuation text appends here
                        mark_attributed(page1)
                        continue
                    if open_heading and open_heading["kind"] in ("subsection", "table"):
                        open_heading["node"]["heading"] += " " + text
                        mark_attributed(page1)
                        continue
                    # otherwise: unstyled continuation of a definition term
                    # wrapping to a 2nd line (rare) — treat as body text.
                    if current_subsection is not None and current_subsection["kind"] == "definition":
                        current_subsection["heading"] = _clean(current_subsection["heading"] + " " + text)
                        mark_attributed(page1)
                        continue

                # --- a currently-open TABLE's own header/row-label cell -----
                # (FINDING 4 fix) Bold + SUBSECTION_GRAY, but narrower than an
                # ordinary subsection heading (TABLE_LABEL_SZ, not
                # SUBSECTION_SZ) -- see _is_table_label / the Pass 3.5
                # docstring. Only ever matched while a table is open; once
                # this table closes, a line at this exact style with no open
                # table falls through unattributed, same as before this fix
                # (never observed outside a table's own header row).
                elif table_capture is not None and _is_table_label(first):
                    close_open_heading()
                    table_capture["lines"].append((page1, "label", text, first["t"], bbox[0], bbox[1]))
                    mark_attributed(page1)
                    continue

                # --- BODY: list items / plain paragraphs --------------------
                elif _is_body(first):
                    close_open_heading()
                    if table_capture is not None and not MARKER_SPAN_RE.match(first["t"]):
                        # THE FIX (Finding 4): this line used to fall straight
                        # through to whichever item was open before the
                        # table's caption (`levels.deepest()` below), silently
                        # corrupting that unrelated neighbour with the
                        # table's own row/legend text. Captured onto the
                        # table instead.
                        #
                        # The MARKER_SPAN_RE exclusion above matters: a table
                        # is not always immediately followed by a new section/
                        # subsection heading -- e.g. Table 3.1 SCREENING
                        # FORMULA sits between the surrounding subsection's
                        # own item 6 and item 7 ("7.\t As an example...",
                        # resuming the SAME digit-marker list), with no
                        # heading in between. None of this module's 7 tables'
                        # own row/legend content ever starts with a tab-
                        # terminated marker span (row labels are plain text;
                        # Table 7.1's dot columns are drawings, not spans;
                        # verified against every captured table below), so a
                        # marker-span line arriving while a table is open is
                        # unambiguously the narrative list resuming, not
                        # another table row -- close the table right here and
                        # let it fall through to the normal item path.
                        table_capture["lines"].append((page1, "value", text, first["t"], bbox[0], bbox[1]))
                        mark_attributed(page1)
                        continue
                    if table_capture is not None:
                        finalize_table_capture()
                    container = current_subsection if current_subsection is not None else current_section
                    if container is None:
                        # body text with no open subsection/section (should
                        # not happen given the grammar) — do not guess a home
                        # for it; leave the page unattributed for --verify.
                        continue
                    mm = MARKER_SPAN_RE.match(first["t"])
                    if mm and len(line) >= 1:
                        marker = mm.group(1)
                        rest = _clean("".join(s["t"] for s in line[1:]))
                        level = levels.level_for(marker, page1)
                        parent_children = levels.parent_children(level, container["children"])
                        node = _new_node("item", art, marker, None, rest, page1, bbox)
                        parent_children.append(node)
                        levels.set_node(level, node)
                        mark_attributed(page1)
                        continue
                    # continuation line: append to the deepest open item, or
                    # start a fallback "para" child if this subsection has no
                    # numbered list at all (e.g. a use's bare DEFINITION).
                    target = levels.deepest()
                    if target is None:
                        target = _new_node("para", art, None, None, "", page1, bbox)
                        container["children"].append(target)
                        levels.stack = [{"kind": "seed", "marker": "", "node": target}]
                    target["text"] = _clean((target["text"] or "") + " " + text)
                    more = target["source_ref"].setdefault("more_pages", [target["source_ref"]["pdf_page"]])
                    if more[-1] != page1:
                        more.append(page1)
                    mark_attributed(page1)
                    continue
                # anything else (stray glyphs, table graphics that don't
                # match body/section/subsection style) is intentionally
                # dropped, never guessed into a node — see module docstring.
            close_open_heading()

        # end-of-document safety net: finalize a table that was still open
        # when the scan ended (none of the 7 known tables need this -- each
        # is followed by a real heading on the same page -- but a table
        # capture must never be left un-finalized, silently reverting to
        # the pre-fix "zero children, no text" shape).
        finalize_table_capture()

        # clean any dangling per-item text (strip leading/trailing space)
        def _finalize(node):
            if node.get("text") is not None:
                node["text"] = node["text"].strip()
            if node.get("heading") is not None:
                node["heading"] = _clean(node["heading"])
            for c in node["children"]:
                _finalize(c)
        article_nodes = [articles[a] for a in article_order]
        for a in article_nodes:
            _finalize(a)
        _assign_ids(article_nodes)

        list_report: list[dict] = []
        for a in article_nodes:
            _verify_ordered_lists(a, list_report)

        considered = set(scan_pages_1indexed(scan_pages))
        unattributed = sorted(p for p in (considered & page_had_body) - attributed_pages)
        coverage = (len(attributed_pages) / len(considered) * 100.0) if considered else 0.0

        stats = {
            "articles_found": [{"article": a, "heading": articles[a]["heading"],
                                 "sections": section_counts[a]} for a in article_order],
            "front_matter_pages": [p + 1 for p in front_matter_pages],
            "skipped_district_pages": [p + 1 for p in skip_pages],
            "considered_pages": len(considered),
            "attributed_pages": len(attributed_pages),
            "unattributed_pages": unattributed,
            "coverage_pct": round(coverage, 2),
            "ordered_lists_verified": len(list_report),
            "ordered_lists_report": list_report,
        }
        return article_nodes, stats
    finally:
        doc.close()


def scan_pages_1indexed(scan_pages: list[int]) -> list[int]:
    return [p + 1 for p in scan_pages]


# =============================================================================
# DEFECT 1 hardening — a SECOND, independent pass over the finished tree.
# `_Levels.level_for` above now raises during construction rather than
# guessing, but this module still asserts the outcome structurally: for
# every parent, its "item"-kind children (in document order) must be a
# contiguous, gap-free run from the correct opener. Any gap or unexpected
# reset RAISES with the id + pdf_page, never a warning.
# =============================================================================

_SEQ_NEXT = {"digit": lambda m: str(int(m) + 1), "alpha": _next_alpha, "roman": _next_roman}


def _verify_ordered_lists(node: dict, report: list[dict]) -> None:
    """Kind is read off the list's OWN first marker, never off nesting
    depth: real content nests alpha several levels deep before ever
    reaching roman (verified — art7.22's headingless-section pseudo-headers
    are themselves lettered a-e, and 'e' nests THREE further alpha levels
    before its roman sub-items), which is exactly why `_Levels.level_for`
    above also determines kind by convention (fresh 'a'/'i'/digit) rather
    than by position — this check stays consistent with that, so it can't
    manufacture a false gap out of a legitimately deep alpha nest. Because
    only digit/'a'/'i' are valid list OPENERS, a list truncated down to a
    lone surviving mid-sequence item (e.g. 'c' left over from a-b-c-d-e)
    still fails here: 'c' is not a valid opener for any kind."""
    items = [c for c in node.get("children") or [] if c["kind"] == "item"]
    if items:
        who = node.get("id") or node.get("heading") or node.get("kind")
        first_marker = (items[0]["number"] or "").lower()
        if first_marker.isdigit():
            kind = "digit"
        elif first_marker == "a":
            kind = "alpha"
        elif first_marker == "i":
            kind = "roman"
        else:
            raise ExtractionError(
                f"ordered list under {who!r} (pdf_page "
                f"{items[0]['source_ref']['pdf_page']}) starts with "
                f"{items[0]['number']!r}, expected a digit, 'a', or 'i' — a "
                f"list beginning mid-sequence is exactly the "
                f"truncated/gapped-list failure mode this check exists to catch"
            )
        expected = first_marker
        for it in items:
            marker = (it["number"] or "").lower()
            if marker != expected:
                raise ExtractionError(
                    f"ordered list under {who!r} (pdf_page "
                    f"{it['source_ref']['pdf_page']}): expected {expected!r}, "
                    f"got {marker!r} — gap or unexpected reset in an ordered list"
                )
            nxt = _SEQ_NEXT[kind](expected)
            if nxt is not None:
                expected = nxt
        report.append({
            "parent": who, "kind": kind, "count": len(items),
            "first": items[0]["number"], "last": items[-1]["number"],
        })
    for c in node.get("children") or []:
        _verify_ordered_lists(c, report)


def _assign_ids(article_nodes: list[dict]) -> None:
    def walk(node, prefix, seen_at_this_level):
        if node["kind"] == "article":
            node_id = f"art{node['article']}"
        elif node["number"] is not None:
            node_id = f"{prefix}.{node['number']}"
        else:
            # para/definition/unnumbered leaf — disambiguate by sibling index
            n = seen_at_this_level.get(node["kind"], 0)
            seen_at_this_level[node["kind"]] = n + 1
            slug = re.sub(r"[^a-z0-9]+", "_", (node["heading"] or node["kind"]).lower()).strip("_")[:40]
            node_id = f"{prefix}.{node['kind']}{n}_{slug}" if slug else f"{prefix}.{node['kind']}{n}"
        node["id"] = node_id
        del node["_id"]
        child_seen: dict[str, int] = {}
        for c in node["children"]:
            walk(c, node_id, child_seen)
    for a in article_nodes:
        walk(a, "", {})


# =============================================================================
# Output assembly
# =============================================================================

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _count_nodes(nodes: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    def walk(n):
        counts[n["kind"]] = counts.get(n["kind"], 0) + 1
        for c in n["children"]:
            walk(c)
    for n in nodes:
        walk(n)
    return counts


def build_document(pdf_path: Path = PDF_PATH) -> tuple[dict, dict]:
    articles, stats = build_tree(pdf_path)
    counts = _count_nodes(articles)
    doc = {
        "schema": SCHEMA,
        "ruleset_key": RULESET_KEY,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {"path": "docs/Newcastle Core Zoning Code.pdf",
                    "sha256": _sha256_file(pdf_path)},
        "article_scheme": "adopted",
        "counts": counts,
        "articles": articles,
    }
    return doc, stats


def _atomic_write_json(target: Path, obj: dict) -> None:
    """CONTRACT.md §1.1 S2 posture, applied to this builder too: validate,
    round-trip verify, write via temp file + fsync + os.replace."""
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if json.loads(text) != obj:
        raise RuntimeError("round-trip verification failed before write — refusing to write")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f"{target.name}.tmp-{os.getpid()}-{os.urandom(3).hex()}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink()


def _print_verify_report(stats: dict, counts: dict) -> None:
    print("=" * 78)
    print("ADOPTED CODE EXTRACTION — --verify report")
    print("=" * 78)
    print(f"Node counts: {counts}")
    print()
    print(f"{'Art':>3}  {'Heading':<28} {'Sections':>8}")
    for a in stats["articles_found"]:
        print(f"{a['article']:>3}  {a['heading']:<28} {a['sections']:>8}")
    print()
    print(f"Front matter pages (no ARTICLE tab): {stats['front_matter_pages']}")
    print(f"Skipped district-spread pages ({len(stats['skipped_district_pages'])}): "
          f"{stats['skipped_district_pages']}")
    print()
    print(f"Considered pages:    {stats['considered_pages']}")
    print(f"Attributed pages:    {stats['attributed_pages']}")
    print(f"Coverage:            {stats['coverage_pct']}%")
    if stats["unattributed_pages"]:
        print(f"UNATTRIBUTED pages ({len(stats['unattributed_pages'])}) — "
              f"body content present but no span was assigned to any node:")
        print(f"  {stats['unattributed_pages']}")
    else:
        print("Unattributed pages: none")
    print("=" * 78)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pdf", type=Path, default=PDF_PATH)
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    ap.add_argument("--verify", action="store_true",
                     help="print the coverage/attribution report; does not write output")
    args = ap.parse_args(argv)

    doc, stats = build_document(args.pdf)
    counts = doc["counts"]

    if args.verify:
        _print_verify_report(stats, counts)
        return 0

    _atomic_write_json(args.out, doc)
    print(f"Wrote {args.out}  ({sum(counts.values())} nodes, "
          f"{stats['coverage_pct']}% page coverage)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
