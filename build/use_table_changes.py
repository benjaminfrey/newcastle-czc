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

_GLYPHS = re.compile(r"#let\s+glyphs\s*=\s*\(([^)]*)\)")
_GLYPH_ENTRY = re.compile(r'(\w+)\s*:\s*"([^"]*)"')
_ROW = re.compile(r'status\(\s*"(\w+)"\s*\)\s*,\s*\[([^\]]+)\]\s*,\s*\[([^\]]+)\]\s*,')
_NOTE = re.compile(r"Note:\s*Uses without[^\]]*not allowed in this District")
_STATUS_CALL = re.compile(r'#?status\(\s*"(\w+)"\s*\)')


class LegendError(czc_diff.Refusal):
    """The USE TABLE LEGEND block could not be found or read."""


def parse_legend(typ_text: str) -> dict:
    """{"glyphs": {code: glyph}, "rows": {code: (label, authority)}, "note": str}.

    Rows are read only between the USE TABLE LEGEND heading and the legend's
    Note, so a status() call anywhere else in the file is never mistaken for one.
    """
    glyphs = _GLYPHS.search(typ_text)
    head = typ_text.find("USE TABLE LEGEND")
    if glyphs is None or head < 0:
        raise LegendError("article-02.typ: the USE TABLE LEGEND block or the glyph map was not found")
    note = _NOTE.search(typ_text, head)
    if note is None:
        raise LegendError("article-02.typ: the legend's 'Note: Uses without ...' sentence was not found")
    rows = {m.group(1): (m.group(2).strip(), m.group(3).strip())
            for m in _ROW.finditer(typ_text, head, note.start())}
    if not rows:
        raise LegendError("article-02.typ: no legend rows were found under USE TABLE LEGEND")
    return {"glyphs": dict(_GLYPH_ENTRY.findall(glyphs.group(1))),
            "rows": rows,
            "note": _STATUS_CALL.sub(lambda m: m.group(1), note.group(0))}


def legend_delta(old: dict, new: dict) -> list[str]:
    """What changed in the legend, as plain sentences. Empty means nothing."""
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
    return out


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
