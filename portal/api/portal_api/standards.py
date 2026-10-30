"""The Code's district standards as values a program can check, without guessing.

Article 2 states each standard as text ("15 ft min", "2 min. - 3 max.", "60 ft"). A number the
Code gives without saying whether it is a minimum or a maximum, or without a unit, is never
filled in here: it gets a status that says why it can't be checked, and a question for the chair.
"""

import functools
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .ruleset import load_ruleset

Status = Literal["checkable", "needs_qualifier", "needs_unit", "not_established",
                 "unresolved", "not_a_number"]

# Rows whose label names a count, so the label itself is the unit.
_COUNT_UNITS = {"Total Stories": "stories", "Number of Units": "units"}
_NUMBER = r"(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?"
_ONE = re.compile(rf"^(?P<n>{_NUMBER})\s*(?P<unit>ft|sf)?\s*(?:(?P<q>min|max)\.?)?$")
_RANGE = re.compile(rf"^(?P<lo>{_NUMBER})\s*(?P<u1>ft|sf)?\s*min\.?\s*-\s*(?P<hi>{_NUMBER})\s*(?P<u2>ft|sf)?\s*max\.?$")


@dataclass(frozen=True)
class Parsed:
    status: Status
    min: float | None
    max: float | None
    unit: str | None
    note: str | None


def _num(text: str) -> float:
    return float(text.replace(",", ""))


@dataclass(frozen=True)
class _Read:
    lo: float | None          # a stated minimum (or the number, when unqualified)
    hi: float | None          # a stated maximum
    qualifier: Literal["min", "max", "range"] | None
    unit: str | None


def _read(raw: str) -> _Read | None:
    """The number, unit and qualifier the cell's text states, and nothing it doesn't."""
    text = raw.strip()
    m = _RANGE.match(text)
    if m:
        return _Read(_num(m["lo"]), _num(m["hi"]), "range", m["u1"] or m["u2"])
    m = _ONE.match(text)
    if not m:
        return None
    n = _num(m["n"])
    return _Read(n if m["q"] != "max" else None, n if m["q"] == "max" else None, m["q"], m["unit"])


def parse_matrix_cell(row_label: str, raw: str) -> Parsed:
    """One cell of a Permitted Buildings table. The qualifier comes only from the cell's text;
    the unit comes from the cell, or from the row label when the label names a count."""
    if row_label == "Permitting Authority":
        return Parsed("not_a_number", None, None, None, None)
    if raw.strip() == "-":
        return Parsed("not_established", None, None, None, None)
    count_unit = _COUNT_UNITS.get(row_label)
    r = _read(raw)
    if r is None:
        return Parsed("unresolved", None, None, count_unit,
                      f"The text {raw!r} for {row_label} could not be read as a number.")
    unit = r.unit or count_unit
    if unit is None:
        return Parsed("needs_unit", None, None, None,
                      f"The Code gives {raw!r} for {row_label} without a unit.")
    if r.qualifier is None:
        return Parsed("needs_qualifier", None, None, unit,
                      f"The Code gives {raw!r} for {row_label} without saying whether it is a "
                      "minimum or a maximum.")
    return Parsed("checkable", r.lo, r.hi, unit, None)

# --- every district's standards ---

_HERE = Path(__file__).resolve().parent
_OVERRIDES = "standards_overrides.json"
_PROVENANCE = ("decided_by", "decided_at", "basis")


class OverrideError(Exception):
    pass


@dataclass(frozen=True)
class Standard:
    key: str
    district_key: str
    source: Literal["dimension", "building_matrix"]
    building: str | None
    field: str
    label: str
    raw: str
    status: Status
    min: float | None
    max: float | None
    unit: str | None
    provenance: Literal["literal", "override"] | None
    citation: dict
    note: str | None


def _snake(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _dimension(district: dict, dim: dict) -> Standard:
    lo = hi = None
    prov = None
    if dim["unresolved"]:
        status: Status = "unresolved"
    elif dim["applicability"] == "not_established":
        status = "not_established"
    else:
        status = "checkable"
        for c in dim["constraints"]:
            if c["qualifier"] == "min":
                lo = c["value"]
            elif c["qualifier"] == "max":
                hi = c["value"]
        sources = {c["source"] for c in dim["constraints"]}
        prov = "override" if "override" in sources else "literal"
    return Standard(
        key=f"{district['district_key']}/dimension/{dim['field_key']}",
        district_key=district["district_key"], source="dimension", building=None,
        field=dim["field_key"], label=dim["label"], raw=dim["raw"], status=status,
        min=lo, max=hi, unit=dim["unit"] if status == "checkable" else dim.get("unit"),
        provenance=prov, citation=dim["citation"],
        note=" ".join(dim["notes"]) or None)


def _matrix(district: dict) -> list[Standard]:
    m = district["building_matrix"]
    if not m:
        return []
    out = []
    for row in m["rows"]:
        label, cells = row[0], row[1:]
        for building, raw in zip(m["cols"], cells):
            p = parse_matrix_cell(label, raw)
            field = _snake(label)
            out.append(Standard(
                key=f"{district['district_key']}/building/{building}/{field}",
                district_key=district["district_key"], source="building_matrix",
                building=building, field=field, label=label, raw=raw, status=p.status,
                min=p.min, max=p.max, unit=p.unit,
                provenance="literal" if p.status == "checkable" else None,
                citation={**district["citation"], "panel": m["title"], "label": label,
                          "building": building},
                note=p.note))
    return out


def _apply(standards: list[Standard], entries: list[dict]) -> list[Standard]:
    """The chair's recorded answers fill in only what a cell leaves out (its qualifier or its
    unit). What the Code states (the number, a stated qualifier, a stated unit) is never changed."""
    out = list(standards)
    for e in entries:
        missing = [k for k in _PROVENANCE if not e.get(k)]
        if missing:
            raise OverrideError(f"override {e!r} lacks {', '.join(missing)}")
        if e.get("qualifier") not in (None, "min", "max"):
            raise OverrideError(f"override {e!r} needs a qualifier of min or max")
        hits = [i for i, s in enumerate(out)
                if s.source == "building_matrix" and s.field == e.get("field")
                and e.get("district_key") in ("*", s.district_key)
                and e.get("building") in ("*", s.building)
                and s.status in ("needs_qualifier", "needs_unit")]
        if not hits:
            raise OverrideError(f"override {e!r} matches no standard that needs one")
        for i in hits:
            s = out[i]
            r = _read(s.raw)
            if r is None:
                raise OverrideError(f"override {e!r}: {s.key} has no number to qualify")
            unit = s.unit or e.get("unit")
            if unit is None:
                raise OverrideError(f"override {e!r} must give a unit for {s.key}")
            if r.qualifier and e.get("qualifier"):
                raise OverrideError(f"override {e!r}: the Code already states {s.raw!r} for {s.key}")
            qualifier = r.qualifier or e.get("qualifier")
            if qualifier is None:
                raise OverrideError(f"override {e!r} must give a qualifier for {s.key}")
            if qualifier == "range":
                lo, hi = r.lo, r.hi
            else:
                n = r.lo if r.lo is not None else r.hi
                lo, hi = (n, None) if qualifier == "min" else (None, n)
            out[i] = Standard(**{**s.__dict__, "status": "checkable", "unit": unit, "min": lo,
                                 "max": hi, "provenance": "override",
                                 "note": f"Decided by {e['decided_by']} on {e['decided_at']}: {e['basis']}"})
    return out

@functools.cache
def _load(root: Path) -> tuple[Standard, ...]:
    standards: list[Standard] = []
    for d in load_ruleset().districts:
        standards += [_dimension(d, dim) for dim in d["dimensions"]]
        standards += _matrix(d)
    entries = json.loads((root / _OVERRIDES).read_text())["overrides"]
    return tuple(_apply(standards, entries))


def load_standards(root: Path | None = None) -> tuple[Standard, ...]:
    """Every district standard in the pinned ruleset, with the chair's recorded overrides."""
    return _load((root or _HERE).resolve())


def standards_for(district_key: str) -> tuple[Standard, ...]:
    return tuple(s for s in load_standards() if s.district_key == district_key)


def check(standard: Standard, value: float) -> Literal["within", "outside", "cannot_check"]:
    """Whether a value fits a standard. Anything not checkable is never a "no"."""
    if standard.status != "checkable":
        return "cannot_check"
    if standard.min is not None and value < standard.min:
        return "outside"
    if standard.max is not None and value > standard.max:
        return "outside"
    return "within"


def missing_buildings_table(district_key: str) -> str | None:
    """The Board's question for a district whose Article 2 page has no Permitted Buildings table."""
    for d in load_ruleset().districts:
        if d["district_key"] == district_key and d["building_matrix_absent"]:
            return d["building_matrix_absent"]["board_question"]
    return None


def main(argv: list[str] | None = None) -> None:
    import argparse
    from datetime import date

    from .standards_audit import render_audit

    p = argparse.ArgumentParser(prog="python -m portal_api.standards")
    sub = p.add_subparsers(dest="cmd", required=True)
    audit = sub.add_parser("audit", help="write the rules coverage memo")
    audit.add_argument("--out", required=True)
    args = p.parse_args(argv)
    Path(args.out).write_text(render_audit(date.today().isoformat()) + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
