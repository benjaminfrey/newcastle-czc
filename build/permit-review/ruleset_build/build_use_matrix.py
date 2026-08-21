"""Implements CONTRACT.md §4.3 (use-matrix.json) and §4.3.2 (the D4
soft-hyphen merge).

build_use_matrix() reads source/article-02-data.json (the 13 districts'
use_col1/use_col2 arrays) and source/article-02.typ (the USE TABLE LEGEND,
via ruleset_build.legend), and returns the full newcastle.use-matrix/1.0.0
dict — dense, 13 districts x 63 uses = 819 cells, prohibited cells included.

Runtime (app/) never imports this module or re-parses repo source; it only
reads the committed rulesets/<ruleset_key>/use-matrix.json this module writes.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from ruleset_build.legend import parse_legend
from ruleset_build.slugs import DISTRICT_KEYS, assert_district_table, display_name, slug

SCHEMA = "newcastle.use-matrix/1.0.0"

# The soft hyphen (U+00AD) that splits one D4 category across two entries
# (CONTRACT.md §4.3.2). Detected on the category title, not hard-coded to
# "TRANSPORTATION & UTIL­" specifically, so the same logic would catch any
# future extraction artifact shaped the same way.
_SOFT_HYPHEN = "\xad"


class UseMatrixBuildError(RuntimeError):
    """Raised when source/article-02-data.json doesn't shape up the way
    CONTRACT.md §4.3 documents — a hard build failure, never a silent guess."""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _merged_categories(district: dict) -> list[dict]:
    """Concatenate use_col1 + use_col2 in source order, merging a soft-hyphen
    split category with the category immediately following it (§4.3.2).

    A split category has entries == [] and a title ending in the soft hyphen;
    the merge joins the two titles (dropping the hyphen) and adopts the next
    category's entries, then drops the now-empty fragment.
    """
    raw = list(district.get("use_col1", [])) + list(district.get("use_col2", []))
    merged: list[dict] = []
    i = 0
    while i < len(raw):
        cat = raw[i]
        title = cat["title"]
        if title.endswith(_SOFT_HYPHEN) and len(cat.get("entries", [])) == 0:
            if i + 1 >= len(raw):
                raise UseMatrixBuildError(
                    f"district {district.get('code')!r}: category "
                    f"{title!r} looks like a soft-hyphen split (empty "
                    f"entries, trailing soft hyphen) but there is no "
                    f"following category to merge it with"
                )
            nxt = raw[i + 1]
            merged.append(
                {
                    "title": title.rstrip(_SOFT_HYPHEN) + nxt["title"],
                    "entries": nxt["entries"],
                }
            )
            i += 2
        else:
            merged.append(cat)
            i += 1
    return merged


def _category_columns(district: dict, merged: list[dict]) -> list[int]:
    """Column (1 or 2) for each entry in `merged`. A merged category's column
    is that of its FIRST raw category (a merge only ever folds the category
    immediately following a split fragment into it — §4.3.2 — so this is
    correct even if a future split straddled the col1/col2 boundary)."""
    col1_len = len(district.get("use_col1", []))
    raw = list(district.get("use_col1", [])) + list(district.get("use_col2", []))
    cols: list[int] = []
    raw_i = 0
    for cat in merged:
        # Each merged category consumed either 1 or 2 raw categories.
        title = raw[raw_i]["title"]
        consumed_here = 1
        if title.endswith(_SOFT_HYPHEN) and len(raw[raw_i].get("entries", [])) == 0:
            consumed_here = 2
        col = 1 if raw_i < col1_len else 2
        cols.append(col)
        raw_i += consumed_here
    return cols


def _district_uses(district: dict) -> tuple[list[dict], list[dict]]:
    """Return (categories, uses) for one district's merged use table, each
    use/category carrying its 1-indexed global `order` and `column`."""
    merged = _merged_categories(district)
    cols = _category_columns(district, merged)

    categories: list[dict] = []
    uses: list[dict] = []
    use_order = 0
    for cat_order, (cat, col) in enumerate(zip(merged, cols), start=1):
        cat_key = slug(cat["title"])
        categories.append(
            {
                "category_key": cat_key,
                "title": cat["title"],
                "column": col,
                "order": cat_order,
            }
        )
        for label, code in cat["entries"]:
            use_order += 1
            uses.append(
                {
                    "use_key": slug(label),
                    "label": label,
                    "category_key": cat_key,
                    "column": col,
                    "order": use_order,
                    "_code": code,  # carried for cell-building; stripped before output
                }
            )
    return categories, uses


def build_use_matrix(src: Path, legend_typ: Path, ruleset_key: str) -> dict:
    """Implements CONTRACT.md §4.3. `src` = source/article-02-data.json,
    `legend_typ` = source/article-02.typ. Raises on any structural mismatch
    with what CONTRACT.md §4 documents as verified fact — never guesses."""
    districts_raw = json.loads(src.read_text(encoding="utf-8"))
    assert_district_table(districts_raw)  # (index, code, name) vs DISTRICT_TABLE

    legend_rows = parse_legend(legend_typ.read_text(encoding="utf-8"))
    legend_by_code = {row["code"]: row for row in legend_rows}

    # Build the canonical (categories, uses) shape from d1 (index 0), then
    # assert every other district's merged shape matches it exactly — this is
    # the "13 districts x 63 uses, identical use_key set/order" invariant
    # (CONTRACT.md §4.3).
    canonical_categories, canonical_uses = _district_uses(districts_raw[0])
    canonical_shape = [(u["use_key"], u["category_key"], u["column"], u["order"]) for u in canonical_uses]

    per_district_uses: dict[str, list[dict]] = {}
    for idx, district in enumerate(districts_raw):
        district_key = DISTRICT_KEYS[idx]
        categories, uses = _district_uses(district)
        shape = [(u["use_key"], u["category_key"], u["column"], u["order"]) for u in uses]
        if shape != canonical_shape:
            raise UseMatrixBuildError(
                f"district {district_key!r} ({district.get('code')} "
                f"{district.get('name')}) does not present the same 63 uses, "
                f"in the same order, as d1 — CONTRACT.md §4.3 requires an "
                f"identical use_key set/order across all 13 districts"
            )
        if len(uses) != 63:
            raise UseMatrixBuildError(
                f"district {district_key!r}: expected 63 uses after the "
                f"§4.3.2 merge, got {len(uses)}"
            )
        per_district_uses[district_key] = uses

    # cells[] — dense: 13 x 63 = 819, prohibited cells included as positive facts.
    cells: list[dict] = []
    by_code_counts: dict[str, int] = {"u": 0, "rc": 0, "sp": 0, "ex": 0, "": 0}
    for district_key in DISTRICT_KEYS:
        for use in per_district_uses[district_key]:
            code = use["_code"]
            legend_row = legend_by_code.get(code)
            if legend_row is None:
                raise UseMatrixBuildError(
                    f"district {district_key!r}, use {use['label']!r}: "
                    f"unknown use-status code {code!r} — not one of "
                    f"{sorted(c for c in legend_by_code if c)} or '' (prohibited)"
                )
            by_code_counts[code] = by_code_counts.get(code, 0) + 1
            cells.append(
                {
                    "district_key": district_key,
                    "use_key": use["use_key"],
                    "code": code,
                    "permit": legend_row["permit"],
                    "permit_key": legend_row["permit_key"],
                    "authority": legend_row["authority"],
                    "authority_key": legend_row["authority_key"],
                    "allowed": legend_row["allowed"],
                }
            )

    if len(cells) != len(DISTRICT_KEYS) * 63:
        raise UseMatrixBuildError(
            f"expected {len(DISTRICT_KEYS) * 63} cells, built {len(cells)}"
        )

    output_categories = [
        {k: v for k, v in c.items()} for c in canonical_categories
    ]
    output_uses = [
        {k: v for k, v in u.items() if k != "_code"} for u in canonical_uses
    ]

    return {
        "schema": SCHEMA,
        "ruleset_key": ruleset_key,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "data_path": "source/article-02-data.json",
            "data_sha256": _sha256_file(src),
            "legend_path": "source/article-02.typ",
            "legend_sha256": _sha256_file(legend_typ),
        },
        "legend": legend_rows,
        "categories": output_categories,
        "uses": output_uses,
        "district_keys": list(DISTRICT_KEYS),
        "cells": cells,
        "counts": {
            "districts": len(DISTRICT_KEYS),
            "uses": len(output_uses),
            "cells": len(cells),
            "by_code": by_code_counts,
        },
    }
