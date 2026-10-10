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

import argparse
import json
import re
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD))

import czc_diff  # noqa: E402
import manifest  # noqa: E402

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


def display_block(legend: dict) -> str:
    """The legend's raw text as a reader may see it: without the glyph map
    (the symbols are not in style/fonts, ruling 11) and with each status()
    call shown as its bare code."""
    block = legend["block"]
    m = _GLYPHS.match(block)
    if m:
        block = block[m.end():].strip()
    return _STATUS_CALL.sub(lambda c: c.group(1), block)


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


# --- The document --------------------------------------------------------------

DATA = "article-02-data.json"
TYP = "article-02.typ"
USE_COLS = ("use_col1", "use_col2")
STANDARD_FIELDS = {"left": "District description and dimensions",
                   "right": "Building standards",
                   "use_standards": "Use standards"}


def build(old: czc_diff.Side, new: czc_diff.Side, *, doc: dict | None = None) -> dict:
    """Everything the document reports, before it is written down."""
    doc = manifest.load() if doc is None else doc
    sources = doc["2"].get("data_sources", [])
    decl = next((d for d in sources if d.get("path") == DATA), None)
    if decl is None or decl.get("compare") != "json-keyed":
        raise czc_diff.Refusal(f"{DATA} is not declared json-keyed under Article 2 "
                               f"in build/article-manifest.json")
    raw_old, raw_new = old.read(DATA), new.read(DATA)
    typ_old, typ_new = old.read(TYP), new.read(TYP)
    if None in (raw_old, raw_new, typ_old, typ_new):
        raise czc_diff.Refusal(f"{DATA} or {TYP} is missing from {old.label} or {new.label}")
    leg_old, leg_new = parse_legend(typ_old.decode()), parse_legend(typ_new.decode())
    return {
        "old": old.label, "new": new.label,
        "delta": czc_diff.diff_maps(czc_diff.json_leaves(raw_old, decl),
                                    czc_diff.json_leaves(raw_new, decl)),
        "legend": legend_delta(leg_old, leg_new),
        "leg_old": leg_old, "leg_new": leg_new,
        "rec_old": czc_diff.keyed_records(json.loads(raw_old), decl["key"]),
        "rec_new": czc_diff.keyed_records(json.loads(raw_new), decl["key"]),
    }


def _district(key: str) -> str:
    return key.replace(" / ", " ")


def _value(v) -> str:
    if v is None:
        return "(none)"
    if isinstance(v, str):
        return f"“{v}”" if v else "(blank)"
    if v == [] or v == {}:
        return "(empty)"
    return json.dumps(v, ensure_ascii=False)


def _category(record: dict | None, col: str, title: str) -> str:
    """A use category's printed name. The extracted data splits D4's
    TRANSPORTATION & UTILITIES at a soft hyphen into an empty
    'TRANSPORTATION & UTIL\\xad' and an 'ITIES' that carries the cells."""
    titles = [c.get("title") for c in ((record or {}).get(col) or [])]
    if title in titles:
        i = titles.index(title)
        if i > 0 and isinstance(titles[i - 1], str) and titles[i - 1].endswith("\xad"):
            return titles[i - 1].rstrip("\xad") + title
        if title.endswith("\xad") and i + 1 < len(titles) and isinstance(titles[i + 1], str):
            return title.rstrip("\xad") + titles[i + 1]
    return title.rstrip("\xad")


_STRUCTURAL = {"body", "items", "entries", "text"}
_POSITION = re.compile(r"\[(\d+)\]")
_KIND_WORDS = {"lv": "table", "list": "list", "para": "paragraph"}
_KIND_NEW = {"lv": "New table", "list": "New list", "para": "New paragraph"}


def _where(parts, record: dict | None = None) -> str:
    """A leaf's place in the data, in a reader's words: the data file's own
    structural keys are dropped, a position reads "item n", and a use category
    is named whole."""
    parts = list(parts)
    if parts and parts[0] in USE_COLS:
        parts = [_category(record, parts[0], parts[1])] + parts[2:] if len(parts) > 1 else []
    elif parts and parts[0] in STANDARD_FIELDS:
        parts[0] = STANDARD_FIELDS[parts[0]]
    shown = []
    for p in parts:
        if p in _STRUCTURAL:
            continue
        m = _POSITION.fullmatch(p)
        shown.append(f"item {int(m.group(1)) + 1}" if m else "sub-item" if p == "sub" else p)
    return " › ".join(shown).replace("\xad", "")


def _empty_line(kind: str, where: str) -> str | None:
    """An empty list or dict is a placeholder for "this is empty", not an item.
    It is described by meaning, never as its parent being added or removed:
    removed -> it had no entries before (it gained some, which appear as their
    own added lines); added -> it now has none (its former items appear as their
    own removed lines). None when the value is not an empty container."""
    where = where or "this list"
    if kind == "removed":
        return f"{where}: had no entries before"
    if kind == "added":
        return f"{where}: now has no entries"
    return None


def _is_empty(v) -> bool:
    return isinstance(v, (list, dict)) and not v


def _matrix_column(old_rec: dict | None, new_rec: dict | None, index_key: str) -> str:
    """The column a matrix value sits under -- named from BOTH sides, so a column
    inserted or renamed between versions cannot put a value under the wrong
    heading."""
    m = _POSITION.fullmatch(index_key)
    if not m:
        return index_key
    i = int(m.group(1))

    def col(rec):
        cols = ((rec or {}).get("matrix") or {}).get("cols") or []
        return cols[i] if i < len(cols) else None
    o, n = col(old_rec), col(new_rec)
    if o == n and o is not None:
        return o
    return f"column {i + 1} (headed “{o or '—'}” before, “{n or '—'}” now)"


def summary(report: dict) -> dict:
    d = report["delta"]
    per: dict[str, int] = {}
    for path in [*d.changed, *d.added, *d.removed]:
        per[_district(path[0])] = per.get(_district(path[0]), 0) + 1
    return {"changed": len(d.changed), "added": len(d.added), "removed": len(d.removed),
            "total": d.count(), "legend": report["legend"], "districts": per}


def _matrix_item(kind, path, val, key, ro, rn, *, bare=False) -> str:
    """One matrix leaf as a line of text (no bullet). `bare` is a whole matrix
    (or whole district) appearing or disappearing: the leaf is described by what
    it holds, from the one side that has it, without an added/removed word."""
    rec_old, rec_new = ro.get(key), rn.get(key)
    if bare:
        rec_old = rec_new = (rn if kind == "added" else ro).get(key)
    if len(path) >= 4 and path[2] == "cols" and _POSITION.fullmatch(path[3]):
        where = f"Column {int(_POSITION.fullmatch(path[3]).group(1)) + 1}" + \
            (" heading" if kind == "changed" else "")
    elif len(path) == 5 and path[2] == "rows":
        where = f"{path[3]} › {_matrix_column(rec_old, rec_new, path[4])}"
    else:
        where = _where(path[2:]) or "the matrix"
    if kind != "changed" and _is_empty(val):
        return _empty_line(kind, where)
    if kind == "changed":
        return f"{where}: {_value(val[0])} → {_value(val[1])}"
    return f"{where}: {_value(val)}" if bare else f"{where} {kind}: {_value(val)}"


def _standard_item(kind, path, val, rec, *, bare=False) -> str:
    """One leaf of a district's standards panels, as a line of text."""
    if path[-1] == "kind" and len(path) >= 4:
        title = path[2]
        if kind == "added":
            return f"{title}: laid out as a {_KIND_WORDS.get(val, val)}" if bare \
                else f"{_KIND_NEW.get(val, 'New panel')}: {title}"
        if kind == "removed":
            return f"{title}: was laid out as a {_KIND_WORDS.get(val, val)}" if bare \
                else f"Removed: {title}"
        return (f"{title} now laid out as a {_KIND_WORDS.get(val[1], val[1])} "
                f"(was a {_KIND_WORDS.get(val[0], val[0])})")
    where = _where(path[1:], rec)
    if kind != "changed" and _is_empty(val):
        return _empty_line(kind, where)
    if kind == "changed":
        return f"{where}: {_value(val[0])} → {_value(val[1])}"
    return f"{where}: {_value(val)}" if bare else f"{where} {kind}: {_value(val)}"


def _whole_district_item(kind, path, val, rec, leg, key, ro, rn) -> str:
    """One item of a district that was wholly added or removed, in words."""
    if len(path) == 5 and path[1] in USE_COLS and path[3] == "entries":
        return (f"use **{path[4]}** ({_category(rec, path[1], path[2])}): "
                f"{status_words(val, leg)}")
    if path[1] == "matrix":
        if len(path) == 2:
            return "No Permitted Buildings matrix" if val is None else \
                f"Permitted Buildings matrix: {_value(val)}"
        return _matrix_item(kind, path, val, key, ro, rn, bare=True)
    if path[1] in USE_COLS:
        where = _where(path[1:], rec)
        return _empty_line(kind, where) if _is_empty(val) else f"{where}: {_value(val)}"
    return _standard_item(kind, path, val, rec, bare=True)


def render(report: dict) -> str | None:
    """The document as markdown, or None when there is nothing to report."""
    d, legend = report["delta"], report["legend"]
    if not d.count() and not legend:
        return None
    ro, rn, lo, ln = report["rec_old"], report["rec_new"], report["leg_old"], report["leg_new"]
    whole_added = [k for k in rn if k not in ro]
    whole_removed = [k for k in ro if k not in rn]
    whole = set(whole_added) | set(whole_removed)

    events = [("changed", p, v) for p, v in d.changed.items()] \
        + [("added", p, v) for p, v in d.added.items()] \
        + [("removed", p, v) for p, v in d.removed.items()]
    uses, matrices, standards = [], [], []
    for kind, path, val in events:
        if path[0] in whole:
            continue
        if path[1] in USE_COLS:
            uses.append((kind, path, val))
        elif path[1] == "matrix":
            matrices.append((kind, path, val))
        else:
            standards.append((kind, path, val))

    def by_district(items):
        grouped: dict[str, list] = {}
        for item in items:
            grouped.setdefault(item[1][0], []).append(item)
        return grouped

    out = ["# Use Table Changes", "",
           f"**Article 2 — district standards and use tables: {report['old']} → {report['new']}**", "",
           "Every change to the district data that Article 2's thirteen district pages are printed "
           "from. The redline shows those pages at their current state, without marks, so this is "
           "the only place their changes are listed item by item.", ""]

    out += ["## 1. Use table legend", ""]
    out += [f"- {s}" for s in legend] if legend else \
        ["No change to the legend: every status code means what it meant before."]
    out.append("")
    if legend_block_changed(lo, ln):
        out += ["Before:", "", "```", display_block(lo), "```", "",
                "After:", "", "```", display_block(ln), "```", ""]

    out += ["## 2. Changed uses", ""]
    changed_uses = [u for u in uses if u[0] == "changed" and len(u[1]) == 5 and u[1][3] == "entries"]
    if not changed_uses:
        out += ["No use changed its status.", ""]
    for key, items in by_district(changed_uses).items():
        out += [f"### {_district(key)} — {len(items)} change{'s' if len(items) != 1 else ''}", ""]
        for _, path, (o, n) in items:
            cat = _category(rn.get(key), path[1], path[2])
            out.append(f"- **{path[4]}** ({cat}): {status_words(o, lo)} → {status_words(n, ln)}")
        out.append("")

    out += ["## 3. Uses and districts added or removed", ""]
    lines: list[str] = []
    for kind, keys, leaves, rec_map, leg in (("added", whole_added, d.added, rn, ln),
                                             ("removed", whole_removed, d.removed, ro, lo)):
        for k in keys:
            mine = [(p, v) for p, v in leaves.items() if p[0] == k]
            lines.append(f"- District {kind}: **{_district(k)}** — {len(mine)} "
                         f"item{'s' if len(mine) != 1 else ''}{':' if mine else '.'}")
            lines += [f"  - {_whole_district_item(kind, p, v, rec_map.get(k), leg, k, ro, rn)}"
                      for p, v in mine]
    lead = []
    if len(whole_added) == 1 and len(whole_removed) == 1:
        a, r = rn[whole_added[0]], ro[whole_removed[0]]
        if isinstance(a, dict) and isinstance(r, dict) and a.get("code") is not None \
                and a.get("code") == r.get("code"):
            lead = [f"These may be one district renamed (code {a['code']}): "
                    f"compare the two lists below.", ""]
    for kind, path, val in uses:
        if kind == "changed" and len(path) == 5 and path[3] == "entries":
            continue
        if len(path) == 5 and path[3] == "entries":
            rec, leg = (rn, ln) if kind == "added" else (ro, lo)
            cat = _category(rec.get(path[0]), path[1], path[2])
            lines.append(f"- {_district(path[0])}: use **{path[4]}** ({cat}) {kind} — "
                         f"{status_words(val, leg)}.")
        else:
            rec = rn.get(path[0]) if kind != "removed" else ro.get(path[0])
            where = _where(path[1:], rec)
            if kind == "changed":
                lines.append(f"- {_district(path[0])}: {where} changed: "
                             f"{_value(val[0])} → {_value(val[1])}.")
            elif _is_empty(val):
                lines.append(f"- {_district(path[0])}: {_empty_line(kind, where)}.")
            else:
                lines.append(f"- {_district(path[0])}: {where} {kind}: {_value(val)}.")
    out += lead
    out += lines if lines else ["No use was added or removed, and no district was added or removed."]
    out.append("")

    out += ["## 4. Permitted Buildings matrix", ""]
    if not matrices:
        out.append("No change to any Permitted Buildings matrix.")
    for key, items in by_district(matrices).items():
        out += ["", f"### {_district(key)}", ""]
        # A matrix that wholly appears or disappears (null <-> a table) is ONE
        # event with its rows and columns beneath it, never a per-cell churn.
        whole_kind = None
        for kind, path, val in items:
            if path[1:] == ("matrix",) and val is None and kind in ("added", "removed"):
                whole_kind = "removed" if kind == "added" else "added"
        if whole_kind:
            out.append(f"- Permitted Buildings matrix {whole_kind}:")
            for kind, path, val in items:
                if path[1:] == ("matrix",) or path[2:] == ("title",):
                    continue
                out.append("  - " + _matrix_item(kind, path, val, key, ro, rn, bare=True))
            continue
        for kind, path, val in items:
            out.append("- " + _matrix_item(kind, path, val, key, ro, rn))
    no_matrix = [_district(k) for k, r in rn.items() if isinstance(r, dict) and r.get("matrix") is None]
    out += ["", f"No Permitted Buildings matrix: {', '.join(no_matrix)}." if no_matrix else
            "Every district has a Permitted Buildings matrix.", ""]

    out += ["## 5. District standards", ""]
    if not standards:
        out += ["No change to any district's standards.", ""]
    for key, items in by_district(standards).items():
        out += [f"### {_district(key)}", ""]
        for kind, path, val in items:
            rec = rn.get(key) if kind != "removed" else ro.get(key)
            out.append("- " + _standard_item(kind, path, val, rec))
        out.append("")

    s = summary(report)
    out += ["## 6. Total", "",
            f"{s['total']} item{'s' if s['total'] != 1 else ''} of district data changed "
            f"({s['changed']} changed, {s['added']} added, {s['removed']} removed). "
            f"This is the figure the change determination reports for Article 2's district data.",
            ""]
    return "\n".join(out).replace("\xad", "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Write the Use Table Changes document for Article 2.")
    ap.add_argument("old_ref", help="the old version: a git ref")
    ap.add_argument("out", help="where to write the markdown")
    side = ap.add_mutually_exclusive_group()
    side.add_argument("--new-ref", help="the new version as a git ref")
    side.add_argument("--new-dir", help="the new version as a source directory (default: source/)")
    ap.add_argument("--json", help="also write the counts as JSON to this path")
    a = ap.parse_args(argv)
    try:
        old = czc_diff.Side(ref=a.old_ref)
        new = (czc_diff.Side(ref=a.new_ref) if a.new_ref
               else czc_diff.Side(root=Path(a.new_dir) if a.new_dir else czc_diff.SOURCE))
        report = build(old, new)
    except czc_diff.Refusal as exc:
        print(f"use_table_changes: refusing -- {exc}", file=sys.stderr)
        return 1
    text = render(report)
    if text is None:
        print(f"use_table_changes: nothing changed in Article 2's district data or legend "
              f"({report['old']} -> {report['new']}); nothing written.")
        return 2
    Path(a.out).write_text(text)
    if a.json:
        Path(a.json).write_text(json.dumps(summary(report), indent=2, ensure_ascii=False) + "\n")
    s = summary(report)
    print(f"use_table_changes: {s['total']} change(s) to Article 2's district data"
          f"{', and a legend change' if report['legend'] else ''} -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
