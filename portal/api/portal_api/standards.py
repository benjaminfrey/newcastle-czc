"""The Code's district standards as values a program can check, without guessing.

Article 2 states each standard as text ("15 ft min", "2 min. - 3 max.", "60 ft"). A number the
Code gives without saying whether it is a minimum or a maximum, or without a unit, is never
filled in here: it gets a status that says why it can't be checked, and a question for the chair.
"""

import re
from dataclasses import dataclass
from typing import Literal

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


def parse_matrix_cell(row_label: str, raw: str) -> Parsed:
    """One cell of a Permitted Buildings table. The qualifier comes only from the cell's text;
    the unit comes from the cell, or from the row label when the label names a count."""
    text = raw.strip()
    if row_label == "Permitting Authority":
        return Parsed("not_a_number", None, None, None, None)
    if text == "-":
        return Parsed("not_established", None, None, None, None)
    count_unit = _COUNT_UNITS.get(row_label)
    m = _RANGE.match(text)
    if m:
        unit = m["u1"] or m["u2"] or count_unit
        if unit is None:
            return Parsed("needs_unit", None, None, None,
                          f"The Code gives {raw!r} for {row_label} without a unit.")
        return Parsed("checkable", _num(m["lo"]), _num(m["hi"]), unit, None)
    m = _ONE.match(text)
    if not m:
        return Parsed("unresolved", None, None, count_unit,
                      f"The text {raw!r} for {row_label} could not be read as a number.")
    unit = m["unit"] or count_unit
    if unit is None:
        return Parsed("needs_unit", None, None, None,
                      f"The Code gives {raw!r} for {row_label} without a unit.")
    if m["q"] is None:
        return Parsed("needs_qualifier", None, None, unit,
                      f"The Code gives {raw!r} for {row_label} without saying whether it is a "
                      "minimum or a maximum.")
    value = _num(m["n"])
    return Parsed("checkable", value if m["q"] == "min" else None,
                  value if m["q"] == "max" else None, unit, None)
