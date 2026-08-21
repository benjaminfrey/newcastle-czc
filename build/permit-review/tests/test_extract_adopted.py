"""Tests ruleset_build/extract_adopted.py — the ADOPTED-PDF extractor.

Offline, no network — reads only the real, committed docs/Newcastle Core
Zoning Code.pdf (repo baseline, read-only). This file did not exist before
the DEFECT 1 hardening pass; it closes the "no tests/test_extract_adopted.py"
gap flagged during that diagnosis and mirrors tests/test_parse_articles.py's
draft-side coverage of the same §12.f APPROVAL STANDARDS trap.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))

from ruleset_build.extract_adopted import (  # noqa: E402
    PDF_PATH,
    ExtractionError,
    _Levels,
    _verify_ordered_lists,
    build_document,
)

pytestmark = pytest.mark.skipif(not PDF_PATH.exists(), reason="adopted PDF baseline not present")


@pytest.fixture(scope="module")
def doc() -> dict:
    d, _stats = build_document()
    return d


def _find(nodes: list[dict], **kw) -> list[dict]:
    return [n for n in nodes if all(n.get(k) == v for k, v in kw.items())]


# ---------------------------------------------------------------------------
# §12 SUBDIVISION — the flood-areas / 21-letters trap, adopted side
# ---------------------------------------------------------------------------


def test_subdivision_approval_standards_has_exactly_21_lettered_items_a_to_u(doc: dict) -> None:
    art7 = next(a for a in doc["articles"] if a["article"] == 7)
    sec12 = next(c for c in art7["children"] if c["kind"] == "section" and c["number"] == "12")
    subf = next(c for c in sec12["children"] if c["kind"] == "subsection" and c["number"] == "f")
    item1 = next(c for c in subf["children"] if c["kind"] == "item" and c["number"] == "1")
    letters = [c["number"] for c in item1["children"] if c["kind"] == "item"]
    expected = [chr(ord("a") + i) for i in range(21)]  # a..u
    assert letters == expected, f"expected a-u (21 letters), got {letters}"


def test_criterion_c_pollution_retains_its_five_roman_sub_items(doc: dict) -> None:
    art7 = next(a for a in doc["articles"] if a["article"] == 7)
    sec12 = next(c for c in art7["children"] if c["kind"] == "section" and c["number"] == "12")
    subf = next(c for c in sec12["children"] if c["kind"] == "subsection" and c["number"] == "f")
    item1 = next(c for c in subf["children"] if c["kind"] == "item" and c["number"] == "1")
    c_item = next(c for c in item1["children"] if c["kind"] == "item" and c["number"] == "c")
    romans = [c["number"] for c in c_item["children"] if c["kind"] == "item"]
    assert romans == ["i", "ii", "iii", "iv", "v"]


# ---------------------------------------------------------------------------
# DEFECT 2 collision guard — a roman 'i' nested under 'c' must never resolve
# in place of the top-level letter 'i'; both must exist as distinct nodes.
# ---------------------------------------------------------------------------


def test_top_level_standard_i_is_distinct_from_nested_c_i(doc: dict) -> None:
    art7 = next(a for a in doc["articles"] if a["article"] == 7)
    sec12 = next(c for c in art7["children"] if c["kind"] == "section" and c["number"] == "12")
    subf = next(c for c in sec12["children"] if c["kind"] == "subsection" and c["number"] == "f")
    item1 = next(c for c in subf["children"] if c["kind"] == "item" and c["number"] == "1")
    top_i = next(c for c in item1["children"] if c["kind"] == "item" and c["number"] == "i")
    c_item = next(c for c in item1["children"] if c["kind"] == "item" and c["number"] == "c")
    nested_i = next(c for c in c_item["children"] if c["kind"] == "item" and c["number"] == "i")
    assert top_i["id"] != nested_i["id"]
    assert top_i["id"] == "art7.12.f.1.i"
    assert nested_i["id"] == "art7.12.f.1.c.i"


# ---------------------------------------------------------------------------
# DEFECT 1 hardening — ordered-list sequence integrity, unit-level
# ---------------------------------------------------------------------------


def _item(number: str, children: list[dict] | None = None) -> dict:
    return {"kind": "item", "number": number, "heading": None, "children": children or [],
            "source_ref": {"pdf_page": 1}}


def _container(children: list[dict]) -> dict:
    return {"kind": "subsection", "number": "x", "heading": "TEST", "children": children,
            "source_ref": {"pdf_page": 1}}


def test_verify_ordered_lists_accepts_a_clean_run() -> None:
    tree = _container([_item("a"), _item("b"), _item("c")])
    report: list[dict] = []
    _verify_ordered_lists(tree, report)
    assert report == [{"parent": "TEST", "kind": "alpha", "count": 3, "first": "a", "last": "c"}]


def test_verify_ordered_lists_raises_on_internal_gap() -> None:
    tree = _container([_item("a"), _item("b"), _item("d")])  # skips 'c'
    with pytest.raises(ExtractionError, match="gap or unexpected reset"):
        _verify_ordered_lists(tree, [])


def test_verify_ordered_lists_raises_on_mid_sequence_start() -> None:
    tree = _container([_item("c"), _item("d")])  # never opens at a valid start
    with pytest.raises(ExtractionError, match="beginning mid-sequence"):
        _verify_ordered_lists(tree, [])


def test_verify_ordered_lists_allows_deep_alpha_nesting_before_roman() -> None:
    # Real shape (art7.22, headingless-section pseudo-headers): alpha can
    # nest several levels deep before roman ever appears. Kind is read off
    # each list's OWN first marker, not off nesting depth — must not
    # manufacture a false gap out of a legitimately deep alpha nest.
    deep = _item("a", children=[_item("a", children=[_item("i"), _item("ii")])])
    tree = _container([deep])
    report: list[dict] = []
    _verify_ordered_lists(tree, report)
    assert [r["kind"] for r in report] == ["alpha", "alpha", "roman"]


def test_levels_level_for_raises_on_unexpected_marker_text() -> None:
    # The former case-3 fallback silently treated an unexpected marker as
    # "a sibling of whatever is currently deepest" -- a guess. It must now
    # raise instead (CONTRACT.md §1 S7: no silent guessing).
    levels = _Levels()
    assert levels.level_for("a", 1) == 0
    with pytest.raises(ExtractionError, match="does not continue any open sequence"):
        levels.level_for("d", 1)  # doesn't continue 'a' (expects 'b'), not a fresh opener


def test_levels_level_for_continues_and_reopens_correctly() -> None:
    levels = _Levels()
    assert levels.level_for("a", 1) == 0
    assert levels.level_for("i", 1) == 1  # opens a fresh roman level under 'a'
    assert levels.level_for("ii", 1) == 1  # continues the roman level
    assert levels.level_for("b", 1) == 0  # returns to alpha, correctly resuming after 'a'


# ---------------------------------------------------------------------------
# Whole-document sanity
# ---------------------------------------------------------------------------


def test_build_document_does_not_raise_and_reports_lists_verified(doc: dict) -> None:
    assert doc["counts"]["item"] > 0
