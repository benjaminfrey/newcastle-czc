"""Tests ruleset_build/parse_definitions.py (article-09 -> definitions.json)
and the Article 7 uses map ruleset_build/parse_articles.py folds out of the
parsed nodes.

Offline, no network, no LLM, no PII — reads only the real, committed
source/article-0{7,9}-*.md files.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))

from ruleset_build.parse_articles import SOURCE_DIR, build_articles, build_uses_map  # noqa: E402
from ruleset_build.parse_definitions import (  # noqa: E402
    DEFAULT_SRC,
    DefinitionsShapeError,
    build_definitions,
    find_term,
    parse_definitions_file,
)

RULESET_KEY = "draft-v0.22"


@pytest.fixture(scope="module")
def defs_doc() -> dict:
    return build_definitions(RULESET_KEY)


@pytest.fixture(scope="module")
def uses_doc() -> dict:
    articles = build_articles(RULESET_KEY, SOURCE_DIR)
    return build_uses_map(articles["nodes"], RULESET_KEY)


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------


def test_definitions_count_is_272(defs_doc: dict) -> None:
    assert defs_doc["counts"]["terms"] == 272
    assert len(defs_doc["definitions"]) == 272


def test_definitions_terms_are_unique(defs_doc: dict) -> None:
    terms = [e["term"] for e in defs_doc["definitions"]]
    assert len(terms) == len(set(terms))


def test_definition_spot_check_ordinary_entry(defs_doc: dict) -> None:
    e = find_term(defs_doc, "Abandoned")
    assert e is not None
    assert e["definition"].startswith("When a building, commercial unit, or property")
    assert e["source_ref"]["line"] == 9


def test_definition_spot_check_missing_colon_entries(defs_doc: dict) -> None:
    # source lines 679/682 omit the colon inside the bold markers -- the
    # term text must still come out clean, with no trailing ':'.
    for term in ("Single Unit Commercial Building", "Single Unit Residential Building"):
        e = find_term(defs_doc, term)
        assert e is not None, term
        assert e["term"] == term
        assert not e["term"].endswith(":")


def test_definition_spot_check_multi_paragraph_entry(defs_doc: dict) -> None:
    e = find_term(defs_doc, "Significant Street Tree")
    assert e is not None
    assert "Critical Root Zone" in e["definition"]
    assert "Article 3 Section 3.G" in e["definition"]


def test_definitions_raises_on_body_text_before_any_term(tmp_path: Path) -> None:
    bad = tmp_path / "article-09-definitions.md"
    bad.write_text(
        '---\narticle-number: "9"\narticle-name: "Definitions"\n---\n\n'
        "# Article 9 Definitions\n\nstray text with no **Term:** heading above it\n",
        encoding="utf-8",
    )
    with pytest.raises(DefinitionsShapeError):
        parse_definitions_file(bad, RULESET_KEY)


def test_definitions_source_file_is_the_real_committed_file() -> None:
    assert DEFAULT_SRC == REPO_ROOT / "source" / "article-09-definitions.md"
    assert DEFAULT_SRC.exists()


# ---------------------------------------------------------------------------
# Article 7 uses map
# ---------------------------------------------------------------------------


def test_uses_map_has_64_entries(uses_doc: dict) -> None:
    assert uses_doc["counts"]["uses"] == 64
    assert len(uses_doc["uses"]) == 64


def test_uses_map_excludes_framework_sections(uses_doc: dict) -> None:
    # §1 USE STANDARDS and §2 EXPANDED USE STANDARDS are framework text, not
    # uses -- they must not appear as keys.
    assert "USE STANDARDS" not in uses_doc["uses"]
    assert "EXPANDED USE STANDARDS" not in uses_doc["uses"]


def test_uses_map_spot_check_residence(uses_doc: dict) -> None:
    residence = uses_doc["uses"]["RESIDENCE"]
    assert residence["section"] == "53"
    assert "dwelling unit" in residence["definition"].lower()
    assert len(residence["standards"]) == 1
    assert "shopfront" in residence["standards"][0]["text"]


def test_uses_map_spot_check_definition_only_use(uses_doc: dict) -> None:
    # 20 of the 64 uses (verified against the source) have a DEFINITION
    # subsection but no STANDARDS subsection at all -- standards must come
    # out as an empty list, not a missing key or a crash.
    amusement = uses_doc["uses"]["AMUSEMENT, INDOOR"]
    assert amusement["definition"]
    assert amusement["standards"] == []


def test_uses_map_spot_check_nested_standards(uses_doc: dict) -> None:
    adult = uses_doc["uses"]["ADULT ESTABLISHMENT"]
    assert len(adult["standards"]) == 6
    nested = [s for s in adult["standards"] if s["depth"] == 1]
    assert len(nested) == 2  # the two "a."/"b." measurement sub-items under item 1
