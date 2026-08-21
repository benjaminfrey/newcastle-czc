"""Required-review lookups against rulesets/<ruleset_key>/use-matrix.json.

This is the runtime-facing half of CONTRACT.md §4.4 (the use-status legend):
given a district and a use, what permit (if any) does Article 2 require, and
who issues it? That IS the "Required Review(s)" table at the head of every
real Newcastle decision (CONTRACT.md §6.2 point 1).

Sentence construction is delegated to app.citation.required_review_row — this
module never builds citation prose itself (CONTRACT.md §5.1: citations are
rendered by app/citation.py, THE ONLY renderer, never from a stored string).

v1 scope note: `review_type` is a constant, "Zoning Use Permit", for every
row this module produces — the only kind of review Phase 1 knows about.
Referral reviews (Road Commissioner / Fire Chief / Life Safety / GSBSWD) are
explicitly out of v1 (CONTRACT.md §1.2, §3.5); when/if they arrive in a later
workflow, `review_type` is the field a referral row would set to something
else (e.g. "Referral: Fire Chief") to distinguish it from a zoning-use row.

Runtime only reads the committed rulesets/<key>/use-matrix.json build output
(CONTRACT.md §4: "Runtime never re-parses repo source"). The one exception is
ruleset_build.slugs.DISTRICT_TABLE, imported here for its static (code, name)
lookup only — not a file re-parse — because districts.json (built separately
by ruleset_build/build_districts.py) is not a Phase 1 dependency of this
module and, as of this writing, is blocked pending DECISIONS-NEEDED D-0001/
D-0002.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app import citation
from app.config import RULESETS_DIR
from ruleset_build.slugs import DISTRICT_KEYS, DISTRICT_TABLE, display_name

# district_key -> (code, display_name), e.g. "d1" -> ("D1", "Rural").
_DISTRICT_CODE_NAME: dict[str, tuple[str, str]] = {
    district_key: (code, display_name(name))
    for district_key, (_, code, name) in zip(DISTRICT_KEYS, DISTRICT_TABLE)
}

REVIEW_TYPE = "Zoning Use Permit"


class UnknownDistrict(KeyError):
    """district_key isn't one of the 13 in DISTRICT_KEYS."""


class UnknownUse(KeyError):
    """`use` didn't match any use_key or label in the loaded use-matrix."""


@lru_cache(maxsize=None)
def _load_use_matrix(ruleset_key: str) -> dict[str, Any]:
    path = RULESETS_DIR / ruleset_key / "use-matrix.json"
    if not path.exists():
        raise FileNotFoundError(
            f"no use-matrix.json for ruleset {ruleset_key!r} at {path} — "
            f"run `python -m ruleset_build.lift_use_matrix` first"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_use(matrix: dict[str, Any], use: str) -> dict[str, Any]:
    """Match `use` against a use_key first (exact), then a label
    (case-insensitive exact). Raises UnknownUse if neither matches."""
    for u in matrix["uses"]:
        if u["use_key"] == use:
            return u
    folded = use.casefold()
    for u in matrix["uses"]:
        if u["label"].casefold() == folded:
            return u
    raise UnknownUse(
        f"{use!r} did not match any use_key or label in ruleset "
        f"{matrix['ruleset_key']!r}'s use-matrix.json"
    )


def _find_cell(matrix: dict[str, Any], district_key: str, use_key: str) -> dict[str, Any]:
    for cell in matrix["cells"]:
        if cell["district_key"] == district_key and cell["use_key"] == use_key:
            return cell
    # Unreachable if use-matrix.json is dense per CONTRACT.md §4.3 (districts x
    # uses, no gaps) and district_key/use_key both validated by the caller.
    raise UnknownUse(
        f"no cell for district_key={district_key!r}, use_key={use_key!r} — "
        f"use-matrix.json is not dense (CONTRACT.md §4.3 violated)"
    )


def _district_stub(ruleset_key: str, district_key: str) -> dict[str, Any]:
    if district_key not in _DISTRICT_CODE_NAME:
        raise UnknownDistrict(
            f"{district_key!r} is not one of the 13 districts: {DISTRICT_KEYS}"
        )
    code, name = _DISTRICT_CODE_NAME[district_key]
    return {
        "district_key": district_key,
        "code": code,
        "name": name.upper(),
        "citation": {"article": 2, "district": code, "district_name": name},
        "ruleset_key": ruleset_key,
    }


def required_reviews(
    district_key: str, use: str, *, ruleset_key: str = "adopted"
) -> list[dict[str, Any]]:
    """The Required Review(s) row(s) for one (district, use) pair.

    `use` may be a use_key ("residence") or a label ("Residence"),
    case-insensitive on the label. Returns exactly one row (v1 has no
    referral reviews, so each (district, use) resolves to exactly one
    determination — allowed-with-permit, or prohibited):

        [{"review_type": "Zoning Use Permit",
          "permit": "Use Permit" | None,
          "permitting_authority": "CEO" | "Planning Board" | None,
          "applicability_text": "A Residence use in the D1-Rural District "
                                 "requires a Use Permit which can be issued "
                                 "by the CEO."}]

    A prohibited cell returns `permit` and `permitting_authority` as `None`
    and an applicability_text in the CONTRACT.md §5.5 prohibited form
    ("A <Use> use is not allowed in the <Code>-<Name> District.").

    Raises UnknownDistrict / UnknownUse rather than guessing — never emits
    a made-up row for input that doesn't resolve (CONTRACT.md §1 S7).
    """
    matrix = _load_use_matrix(ruleset_key)
    district = _district_stub(ruleset_key, district_key)
    use_entry = _resolve_use(matrix, use)
    cell = _find_cell(matrix, district_key, use_entry["use_key"])

    row = citation.required_review_row(district, use_entry, cell)

    return [
        {
            "review_type": REVIEW_TYPE,
            "permit": row["permit"],
            "permitting_authority": row["authority"],
            "applicability_text": row["sentence"],
        }
    ]
