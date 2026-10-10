#!/usr/bin/env python3
"""The Use Table Changes document: what changed in Article 2's district
standards and use tables between two versions of the Code.

WHY. Article 2's thirteen district pages are rendered from
source/article-02-data.json by a layout unit, and no redline can mark them:
they appear at their current state, without marks. Until now the only account
of what moved in them was a sentence in the Summary -- which is how a single
changed use cell reached an adopted Code with no reader able to catch it.

WHAT IT REPORTS, in this order:
  1. The use-table legend, FIRST: a changed meaning for an existing status
     code changes every cell that carries it, with no cell diff at all. The
     legend lives in article-02.typ, not in the data.
  2. Changed uses, per district: Use (category): before -> after. A blank
     status is printed "Not allowed", never left blank.
  3. Uses and districts added or removed -- events distinct from a change.
  4. Permitted Buildings matrix changes, by district, row and column.
  5. District standards changes: the description, purpose, dimension,
     placement and design panels, and the district's use standards.
  6. A total that equals the change determination's Article 2 data count
     (czc_diff.py): both come from the same keyed comparator.

The comparator is czc_diff's, imported -- there is one. The legend is read by
a small extractor here rather than by importing the permit-review app's: the
build produces the legal instrument and the app consumes it, so a packet build
must not fail because an app assertion drifted. An agreement test keeps the
two readers together.

Statuses are given in words. The use-table glyphs come from fonts that are not
in style/fonts, so a rendered memo would show them as missing characters.

Exit 0 written; 2 nothing to report (nothing written); 1 refused.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD))

import czc_diff  # noqa: E402

_GLYPHS = re.compile(r'#let\s+glyphs\s*=\s*\(((?:[^)"]|"[^"]*")*)\)')
_GLYPH_ENTRY = re.compile(r'(\w+)\s*:\s*"([^"]*)"')
_ROW = re.compile(r'status\(\s*"(\w+)"\s*\)\s*,\s*\[([^\]]+)\]\s*,\s*\[([^\]]+)\]\s*,')
_STATUS_CALL = re.compile(r'#?status\(\s*"(\w+)"\s*\)')


class LegendError(czc_diff.Refusal):
    """The USE TABLE LEGEND block could not be found or read."""


def _collapse(s: str) -> str:
    """Whitespace-collapse, so a rewrap of the source is not a change."""
    return " ".join(s.split())


def _bracket_end(text: str, open_at: int) -> int:
    """Index of the ']' matching the '[' at open_at (backslash-escaped brackets
    do not count). Refuses an unbalanced block."""
    depth, i = 0, open_at
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise LegendError("article-02.typ: the legend's Note has no closing bracket")


def _note_span(typ_text: str, head: int) -> tuple[int, int, int]:
    """(open, start-of-'Note:', close) of the legend Note's content bracket."""
    at = typ_text.find("Note:", head)
    if at < 0:
        raise LegendError("article-02.typ: the legend's 'Note:' sentence was not found")
    opn = typ_text.rfind("[", head, at)
    if opn < 0 or typ_text[opn + 1:at].strip():
        raise LegendError("article-02.typ: the legend's Note does not open its own bracket")
    return opn, at, _bracket_end(typ_text, opn)


def parse_legend(typ_text: str) -> dict:
    """{"glyphs": {code: glyph}, "rows": {code: (label, authority)},
    "note": str, "block": str}.

    Rows are read only between the USE TABLE LEGEND heading and the legend's
    Note, so a status() call anywhere else in the file is never mistaken for
    one. It fails closed: a duplicate code, or a glyph map and a row list that
    name different codes, is refused -- either a parse failure or a real
    inconsistency in the Code, and both need a person. "block" is the raw
    legend text (glyph map through the Note), whitespace-collapsed: the
    backstop for any change the itemised comparison cannot see.
    """
    glyphs = _GLYPHS.search(typ_text)
    head = typ_text.find("USE TABLE LEGEND")
    if glyphs is None or head < 0:
        raise LegendError("article-02.typ: the USE TABLE LEGEND block or the glyph map was not found")
    opn, note_at, close = _note_span(typ_text, head)
    rows: dict[str, tuple[str, str]] = {}
    for m in _ROW.finditer(typ_text, head, opn):
        if m.group(1) in rows:
            raise LegendError(f"article-02.typ: legend status code `{m.group(1)}` appears twice")
        rows[m.group(1)] = (_collapse(m.group(2)), _collapse(m.group(3)))
    if not rows:
        raise LegendError("article-02.typ: no legend rows were found under USE TABLE LEGEND")
    glyph_map = dict(_GLYPH_ENTRY.findall(glyphs.group(1)))
    if set(glyph_map) != set(rows):
        only_g = sorted(set(glyph_map) - set(rows))
        only_r = sorted(set(rows) - set(glyph_map))
        raise LegendError("article-02.typ: the glyph map and the legend rows name different codes "
                          f"(glyph map only: {only_g}; legend rows only: {only_r})")
    note = _STATUS_CALL.sub(lambda m: m.group(1), typ_text[note_at:close])
    return {"glyphs": glyph_map, "rows": rows, "note": _collapse(note),
            "block": _collapse(glyphs.group(0) + " " + typ_text[head:close + 1])}


def legend_delta(old: dict, new: dict) -> list[str]:
    """What changed in the legend, as plain sentences. Empty means nothing.

    If the itemised comparison finds nothing but the raw legend text differs,
    one sentence says so; legend_block_changed() lets the renderer print both
    blocks.
    """
    out = []
    for code in sorted(set(old["rows"]) | set(new["rows"])):
        o, n = old["rows"].get(code), new["rows"].get(code)
        if o is None:
            out.append(f"Status code `{code}` added: {n[0]} ({n[1]}).")
        elif n is None:
            out.append(f"Status code `{code}` removed (it read {o[0]}, {o[1]}).")
        else:
            if o[0] != n[0]:
                out.append(f"Status code `{code}` now reads \"{n[0]}\" (it read \"{o[0]}\").")
            if o[1] != n[1]:
                out.append(f"Status code `{code}` is now issued by {n[1]} (it was {o[1]}).")
    for code in sorted(set(old["glyphs"]) | set(new["glyphs"])):
        og, ng = old["glyphs"].get(code), new["glyphs"].get(code)
        if og != ng:
            out.append(f"The symbol for `{code}` changed: {og or 'none'} → {ng or 'none'}.")
    if old["note"] != new["note"]:
        out.append(f"The legend's note now reads \"{new['note']}\" (it read \"{old['note']}\").")
    if not out and old["block"] != new["block"]:
        out.append("The legend's text changed in a way this document cannot itemise; "
                   "its before and after text are shown below.")
    return out


def legend_block_changed(old: dict, new: dict) -> bool:
    """True when the legend's raw text differs but nothing could be itemised:
    the renderer then prints both blocks."""
    itemised = [s for s in legend_delta(old, new)
                if not s.startswith("The legend's text changed in a way")]
    return not itemised and old["block"] != new["block"]


def status_words(code: str, legend: dict) -> str:
    """A status code in words. A blank status is "Not allowed": 450 of the 819
    cells carry it, and a blank in a report reads as "nothing here"."""
    if not code.strip():
        return "Not allowed"
    parts = []
    for c in code.split():
        row = legend["rows"].get(c)
        parts.append(f"{row[0].removesuffix(' Required')} ({row[1]})" if row
                     else f"`{c}` (not in the legend)")
    return " + ".join(parts)
