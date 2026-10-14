"""Right to Farm (specs/2026-10-07-right-to-farm-design.md; decisions in
plans/2026-10-14-right-to-farm-decisions.md). Facts that must agree across
Articles, pinned so a later edit to one Article cannot silently contradict
another."""
import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "source"

NEW_TERMS = [
    "Agriculture", "Home/Personal Agriculture", "Commercial Agriculture",
    "Small Stock", "Medium Stock", "Large Stock", "Farmstand", "Greenhouse",
    "Hoop House", "High Tunnel", "Manure Storage", "Best Management Practices",
    "Agritourism", "On-Farm Processing", "Agricultural Building", "Barn",
]
RETIRED_TERMS = ["Agricultural Buildings", "Agricultural Use", "Large Animals", "Small Animals"]


def _terms() -> list[str]:
    text = (SRC / "article-09-definitions.md").read_text(encoding="utf-8")
    return re.findall(r"^\*\*(.+?):\*\*\s*$", text, flags=re.M)


def test_each_new_term_is_defined_exactly_once():
    terms = _terms()
    for t in NEW_TERMS:
        assert terms.count(t) == 1, f"{t!r} defined {terms.count(t)} times"


def test_retired_terms_are_gone_and_unused():
    assert not set(RETIRED_TERMS) & set(_terms())
    for f in SRC.glob("article-0*.md"):
        body = f.read_text(encoding="utf-8")
        for t in ("Large Animals", "Small Animals", "Agricultural Use"):
            assert t not in body, f"{f.name} still uses {t!r}"


def test_new_terms_sit_alphabetically_between_their_neighbours():
    """Only the new terms: the adopted Article 9 already has 24 out-of-order
    pairs (e.g. 'Abutting' before 'Abutter'), which this amendment does not
    reorder."""
    terms = _terms()
    for t in NEW_TERMS:
        i = terms.index(t)
        before = terms[i - 1].lower() if i > 0 else ""
        after = terms[i + 1].lower() if i + 1 < len(terms) else "￿"
        assert before <= t.lower() <= after, f"{t!r} sits between {terms[i-1]!r} and {terms[i+1]!r}"
