"""Implements CONTRACT.md §4.1 (districts.json) and §4.2 (dimensions[] — the
normalizer).

build_districts() reads source/article-02-data.json (the 13 districts' left/
right panels, matrix, use_standards) plus overrides/dimension-qualifiers.json
(the ONLY place an unqualified dimensional value may be resolved, §4.2.4),
and returns the full newcastle.districts/1.0.0 dict.

FAIL LOUDLY (§4.2.3): a dimensional clause with a number and no min/max
qualifier, and no resolving entry in overrides/dimension-qualifiers.json,
raises AmbiguousDimension and aborts the whole build. Nothing is written.
That is intended behaviour, not a bug — see DECISIONS-NEEDED.md D-0001/D-0002.

Runtime (app/) never imports this module or re-parses repo source; it only
reads the committed rulesets/<ruleset_key>/districts.json this module writes.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ruleset_build.slugs import (
    DISTRICT_KEYS,
    DISTRICT_TABLE,
    assert_district_table,
    display_name,
    slug,
)

SCHEMA = "newcastle.districts/1.0.0"

# Exactly these panel titles are dimensional and feed dimensions[] (§4.1.3).
# Every other `lv` panel (in practice only DESIGN STANDARDS) is prose: its
# values are carried verbatim in panels[] and never parsed or raised on.
DIMENSIONAL_PANEL_TITLES = {
    "LOT DIMENSIONS",
    "PRIMARY BUILDING PLACEMENT",
    "ACCESSORY BUILDING PLACEMENT",
    "BUILDING PLACEMENT",
}

# §4.2.1 — case-insensitive, trimmed.
_NOT_ESTABLISHED = {"", "n/a", "-", "—", "none"}

# §4.2.2 grammar:
#   value  := clause ("," clause)*
#   clause := number unit? qualifier? footnote?
#   number := digits ("." digits)?
#   unit   := "ft" | "%"
#   qualifier := "min"|"minimum"|"max"|"maximum"   (case-insensitive, optional)
#   footnote  := "(" digits ")"                    (optional)
# qualifier is optional in the grammar itself; its absence is what triggers
# the ambiguity check in normalize_dimension (not a grammar failure).
_CLAUSE_RE = re.compile(
    r"""^\s*
        (?P<number>\d+(?:\.\d+)?)
        \s*(?P<unit>ft|%)?
        \s*(?P<qualifier>min(?:imum)?|max(?:imum)?)?
        \s*(?:\((?P<footnote>\d+)\))?
        \s*$""",
    re.IGNORECASE | re.VERBOSE,
)


class SourceShapeError(RuntimeError):
    """Raised when source/article-02-data.json (or a dimensional value inside
    it) doesn't shape up the way CONTRACT.md §4.1/§4.2 documents — a hard
    build failure, never a silent guess."""


class AmbiguousDimension(RuntimeError):
    """Raised when a dimensional clause carries a number and no qualifier,
    and overrides/dimension-qualifiers.json has no entry that resolves it
    (CONTRACT.md §4.2.3/§4.2.4). Aborts the whole build — no districts.json
    is written. Carries structured fields so the caller can log the ledger
    entry (DECISIONS-NEEDED.md, §7) without re-parsing the message.
    """

    def __init__(self, *, district_key: str, field_key: str, label: str, raw: str, clause: str):
        self.district_key = district_key
        self.field_key = field_key
        self.label = label
        self.raw = raw
        self.clause = clause
        super().__init__(
            f"{district_key}: {field_key} ({label!r}) — unqualified value {clause!r} "
            f"in raw {raw!r}; no resolving entry in "
            f"overrides/dimension-qualifiers.json under "
            f"'{district_key}:{field_key}'. See CONTRACT.md §4.2.3/§4.2.4 and "
            f"DECISIONS-NEEDED.md — the build produces nothing until a human resolves it."
        )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# §4.2 — the dimensions[] normalizer
# ---------------------------------------------------------------------------

def _split_clauses(raw: str) -> list[str]:
    """Split on top-level commas. No clause in the verified source contains a
    nested comma (§4.2.2's grammar has none), so a plain split is exact."""
    return [c.strip() for c in raw.split(",") if c.strip()]


def _parse_clause(clause: str) -> dict:
    m = _CLAUSE_RE.match(clause)
    if not m:
        raise SourceShapeError(
            f"clause does not match the §4.2.2 dimensional grammar: {clause!r}"
        )
    qualifier = m.group("qualifier")
    if qualifier:
        qualifier = "min" if qualifier.lower().startswith("min") else "max"
    unit = m.group("unit")
    value = float(m.group("number"))
    if unit == "%":
        # "20% min" -> {value: 0.20, unit: "pct"} (task brief's worked example).
        unit = "pct"
        value = value / 100.0
    return {
        "value": value,
        "unit": unit,
        "qualifier": qualifier,
        "footnote_ref": m.group("footnote"),
    }


def normalize_dimension(
    district_key: str,
    panel_key: str,
    label: str,
    raw: str,
    overrides: dict,
) -> dict:
    """Implements CONTRACT.md §4.2 for one [label, value] pair out of a
    dimensional panel (§4.1.3). `overrides` is the parsed 'entries' object of
    overrides/dimension-qualifiers.json (§4.2.4) — NOT the whole file.

    Returns a dict with the §4.2 fields EXCEPT `panel_title` and `citation`,
    which the caller (build_district) fills in — this function is not given
    the panel's display title or the district's code/name.

    Raises AmbiguousDimension (never guesses) per §4.2.3.
    """
    field_key = f"{panel_key}.{slug(label)}"
    raw_stripped = raw.strip()

    if raw_stripped.casefold() in _NOT_ESTABLISHED:
        return {
            "field_key": field_key,
            "panel_key": panel_key,
            "label": label,
            "raw": raw,
            "applicability": "not_established",
            "unit": None,
            "constraints": [],
            "footnote_refs": [],
            "unresolved": False,
            "notes": [],
        }

    override_key = f"{district_key}:{field_key}"
    override_entry = overrides.get(override_key)

    constraints: list[dict] = []
    footnote_refs: list[str] = []
    notes: list[str] = []

    for clause_text in _split_clauses(raw_stripped):
        parsed = _parse_clause(clause_text)
        qualifier = parsed["qualifier"]
        source = "literal"

        if qualifier is None:
            resolved = (
                override_entry is not None
                and override_entry.get("qualifier") in ("min", "max")
                and override_entry.get("decided_by")
                and override_entry.get("basis")
            )
            if not resolved:
                raise AmbiguousDimension(
                    district_key=district_key,
                    field_key=field_key,
                    label=label,
                    raw=raw,
                    clause=clause_text,
                )
            qualifier = override_entry["qualifier"]
            source = "override"
            decided_at = override_entry.get("decided_at")
            notes.append(
                f"Qualifier resolved by override: decided_by="
                f"{override_entry['decided_by']}, basis={override_entry['basis']}"
                + (f", decided_at={decided_at}" if decided_at else "")
            )

        if parsed["footnote_ref"]:
            footnote_refs.append(parsed["footnote_ref"])

        constraints.append(
            {
                "qualifier": qualifier,
                "value": parsed["value"],
                "unit": parsed["unit"],
                "footnote_ref": parsed["footnote_ref"],
                "source": source,
            }
        )

    units = {c["unit"] for c in constraints if c["unit"]}
    unit = next(iter(units)) if len(units) == 1 else (None if not units else sorted(units)[0])

    unresolved = bool(footnote_refs)
    if unresolved:
        marks = ", ".join(f"({r})" for r in footnote_refs)
        notes.append(
            f"Footnote text for {marks} is not present in the Article 2 extract "
            f"(source/article-02-data.json). See DECISIONS-NEEDED.md."
        )

    return {
        "field_key": field_key,
        "panel_key": panel_key,
        "label": label,
        "raw": raw,
        "applicability": "established",
        "unit": unit,
        "constraints": constraints,
        "footnote_refs": footnote_refs,
        "unresolved": unresolved,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# §4.1.2 — panels[], verbatim carry-through
# ---------------------------------------------------------------------------

def _build_panels(district_raw: dict) -> list[dict]:
    panels: list[dict] = []
    ordinal = 0
    for side in ("left", "right"):
        seen: dict[str, int] = {}
        for index, p in enumerate(district_raw.get(side, [])):
            title = p["title"]
            base_key = slug(title)
            count = seen.get(base_key, 0)
            seen[base_key] = count + 1
            panel_key = base_key if count == 0 else f"{base_key}_{count + 1}"
            panels.append(
                {
                    "side": side,
                    "index": index,
                    "ordinal": ordinal,
                    "panel_key": panel_key,
                    "title": title,
                    "kind": p["kind"],
                    "body": p["body"],
                }
            )
            ordinal += 1
    return panels


def _extract_description_purpose(panels: list[dict]) -> tuple[str | None, list[str]]:
    """DESCRIPTION and PURPOSE are ordinary left[] panels (verbatim in
    panels[]) AND get lifted to top-level `description`/`purpose` convenience
    fields (§4.1 example) since every downstream consumer wants them without
    walking panels[]."""
    description: str | None = None
    purpose: list[str] = []
    for p in panels:
        if p["side"] != "left":
            continue
        if p["title"] == "DESCRIPTION" and p["kind"] == "para":
            description = p["body"]
        elif p["title"] == "PURPOSE" and p["kind"] == "list":
            purpose = list(p["body"])
    return description, purpose


# ---------------------------------------------------------------------------
# §4.1.4 — building_matrix and its absence
# ---------------------------------------------------------------------------

def _build_building_matrix(matrix_raw: dict | None, district_display_name: str) -> tuple[dict | None, dict | None]:
    if matrix_raw is None:
        return None, {
            "finding": "Article 2 does not establish building dimensional standards for this District.",
            "unresolved": True,
            "board_question": (
                f"Article 2 establishes no building dimensional standards for the "
                f"{district_display_name} District. What dimensional standards, if any, "
                f"does the Board apply to this proposal?"
            ),
        }
    return (
        {
            "title": matrix_raw.get("title"),
            "cols": list(matrix_raw.get("cols", [])),
            "rows": [list(row) for row in matrix_raw.get("rows", [])],
        },
        None,
    )


# ---------------------------------------------------------------------------
# use_standards — gotcha 2: coerce the polymorphic items[] on read
# ---------------------------------------------------------------------------

def _coerce_use_item(item: Any) -> dict:
    if isinstance(item, str):
        return {"text": item, "sub": []}
    if isinstance(item, dict):
        return {"text": item.get("text", ""), "sub": list(item.get("sub", []))}
    raise SourceShapeError(f"unexpected use_standards item type: {type(item).__name__}")


def _build_use_standards(use_standards_raw: dict | None) -> dict:
    if not use_standards_raw:
        return {"title": None, "items": []}
    items_raw = use_standards_raw.get("items", [])
    return {
        "title": use_standards_raw.get("title"),
        "items": [_coerce_use_item(it) for it in items_raw],
    }


# ---------------------------------------------------------------------------
# §7 — idempotent DECISIONS-NEEDED.md logging for a caught AmbiguousDimension
# ---------------------------------------------------------------------------

def _decisions_needed_path() -> Path:
    return Path(__file__).resolve().parent.parent / "DECISIONS-NEEDED.md"

def _next_decision_id(text: str) -> str:
    ids = [int(m) for m in re.findall(r"^## D-(\d{4})", text, re.MULTILINE)]
    return f"D-{(max(ids) + 1) if ids else 1:04d}"

def _already_logged(text: str, district_key: str, field_key: str, raw: str) -> bool:
    """Idempotency check: a block mentioning this district_key, this
    field_key, AND this raw string is treated as the same open question,
    so re-running the builder never appends a duplicate ledger entry."""
    for block in text.split("\n## "):
        if f"`{district_key}`" in block and f"`{field_key}`" in block and raw in block:
            return True
    return False

def ensure_ambiguous_dimension_logged(
    exc: AmbiguousDimension, *, panel_title: str, district_display_name: str
) -> bool:
    """§7.3 format. Appends a new D-NNNN entry to DECISIONS-NEEDED.md unless
    one already covers this (district_key, field_key, raw) — never edits an
    existing entry except by a human filling in Resolution (§7.3). Returns
    True if a new entry was appended."""
    path = _decisions_needed_path()
    text = path.read_text(encoding="utf-8") if path.exists() else "# DECISIONS-NEEDED\n"
    if _already_logged(text, exc.district_key, exc.field_key, exc.raw):
        return False
    decision_id = _next_decision_id(text)
    today = datetime.now(timezone.utc).date().isoformat()
    entry = f"""
## {decision_id} — {district_display_name} · {exc.label} · unqualified "{exc.raw}"

- **Status:** OPEN
- **Raised:** {today}, by `ruleset_build/build_districts.py`
- **Ruleset:** `adopted`
- **District:** `{exc.district_key}` ({district_display_name})
- **Field:** `{exc.field_key}` — panel `{panel_title}`, label `{exc.label}`
- **Raw string:** `{exc.raw}`
- **Why ambiguous:** Article 2 states the number with no `min` or `max` qualifier.
- **What we will NOT do:** infer from sibling districts, default to `min`, infer from the
  field name, or emit the value unqualified.
- **Blocking:** **yes** — `ruleset_build` raises `AmbiguousDimension` and writes no
  `districts.json` until this is resolved in `overrides/dimension-qualifiers.json`.
- **Needs:** a human reading the adopted Article 2 {district_display_name} spread.
- **Resolution:** _(pending — record `qualifier`, `decided_by`, `decided_at`, `basis`)_
"""
    with path.open("a", encoding="utf-8") as f:
        f.write(entry)
    return True


# ---------------------------------------------------------------------------
# One district
# ---------------------------------------------------------------------------

def build_district(
    source_index: int,
    code: str,
    name: str,
    district_key: str,
    raw: dict,
    overrides: dict,
) -> dict:
    district_display_name = f"{code} - {display_name(name)}"
    panels = _build_panels(raw)
    description, purpose = _extract_description_purpose(panels)

    dimensions: list[dict] = []
    for p in panels:
        if p["kind"] != "lv" or p["title"] not in DIMENSIONAL_PANEL_TITLES:
            continue
        for label, value in p["body"]:
            try:
                dim = normalize_dimension(district_key, p["panel_key"], label, value, overrides)
            except AmbiguousDimension as exc:
                ensure_ambiguous_dimension_logged(
                    exc, panel_title=p["title"], district_display_name=district_display_name
                )
                raise
            dim["panel_title"] = p["title"]
            dim["citation"] = {
                "article": 2,
                "district": code,
                "panel": p["title"],
                "label": label,
            }
            dimensions.append(dim)

    building_matrix, building_matrix_absent = _build_building_matrix(
        raw.get("matrix"), district_display_name
    )

    return {
        "district_key": district_key,
        "source_index": source_index,
        "code": code,
        "name": name,
        "display_name": district_display_name,
        "group": raw.get("group"),
        "color": raw.get("color"),
        "band_text": raw.get("band_text"),
        "description": description,
        "purpose": purpose,
        "panels": panels,
        "dimensions": dimensions,
        "building_matrix": building_matrix,
        "building_matrix_absent": building_matrix_absent,
        "use_standards": _build_use_standards(raw.get("use_standards")),
        "citation": {"article": 2, "district": code, "district_name": display_name(name)},
    }


# ---------------------------------------------------------------------------
# All districts
# ---------------------------------------------------------------------------

def build_districts(src: Path, overrides: Path, ruleset_key: str) -> dict:
    """Implements CONTRACT.md §4.1 end-to-end.

    Writes nothing itself — returns the full newcastle.districts/1.0.0 dict;
    the caller (ruleset_build/lift_districts.py) decides where/whether to
    persist it. Raises SourceShapeError or AmbiguousDimension (and, for the
    latter, appends a DECISIONS-NEEDED.md entry) rather than guessing.
    """
    raw_list = _load_json(src)
    assert_district_table(raw_list)

    overrides_doc = _load_json(overrides)
    entries = overrides_doc.get("entries", {})

    districts = [
        build_district(source_index, code, name, district_key, raw, entries)
        for (source_index, code, name), district_key, raw in zip(
            DISTRICT_TABLE, DISTRICT_KEYS, raw_list
        )
    ]

    assert len(districts) == 13
    assert len({d["district_key"] for d in districts}) == 13

    return {
        "schema": SCHEMA,
        "ruleset_key": ruleset_key,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {"path": "source/article-02-data.json", "sha256": _sha256_file(src)},
        "article": {"adopted": 2, "draft": 2},
        "counts": {
            "districts": len(districts),
            "dimensions": sum(len(d["dimensions"]) for d in districts),
            "unresolved": sum(
                1 for d in districts for dim in d["dimensions"] if dim["unresolved"]
            ),
        },
        "districts": districts,
    }
