"""Tests ruleset_build/crosswalk.py (article-map.json + crosswalk.json) and
app/citation.py's render_citation() against the W2 task brief.

Offline, no network, no LLM, no PII. Reads docs/Newcastle Core Zoning
Code.pdf (read-only — never writes to docs/) and source/article-0N-*.md.
Writes only into a throwaway tmp_path, never into rulesets/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import citation as cit  # noqa: E402
from ruleset_build import crosswalk as cw  # noqa: E402

PDF_PATH = REPO_ROOT / "docs" / "Newcastle Core Zoning Code.pdf"

requires_pdf = pytest.mark.skipif(not PDF_PATH.exists(), reason=f"adopted PDF not found at {PDF_PATH}")


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def article_map() -> dict:
    return cw.build_article_map()


@pytest.fixture(scope="module")
def crosswalk_doc(tmp_path_factory) -> dict:
    if not PDF_PATH.exists():
        pytest.skip(f"adopted PDF not found at {PDF_PATH}")
    overrides_path = tmp_path_factory.mktemp("crosswalk") / "crosswalk-overrides.json"
    return cw.build_crosswalk(overrides_path=overrides_path)


@pytest.fixture(scope="module", autouse=True)
def _point_citation_at_a_built_article_map(tmp_path_factory, article_map):
    """app.citation.render_citation() reads rulesets/article-map.json off
    disk (RULESETS_DIR). Point it at a throwaway copy of the map this test
    just built, instead of depending on (or writing into) the real
    rulesets/ directory, and restore the cache afterward."""
    tmp_dir = tmp_path_factory.mktemp("rulesets_for_citation")
    (tmp_dir / "article-map.json").write_text(json.dumps(article_map), encoding="utf-8")

    import app.config as config

    original_rulesets_dir = config.RULESETS_DIR
    cit.clear_article_map_cache()
    cit.RULESETS_DIR = tmp_dir  # citation.py imported RULESETS_DIR by reference; rebind it directly
    try:
        yield
    finally:
        cit.RULESETS_DIR = original_rulesets_dir
        cit.clear_article_map_cache()


# --------------------------------------------------------------------------- #
# article-map.json
# --------------------------------------------------------------------------- #


def test_article_map_covers_every_renum_entry(article_map):
    for adopted, draft in cw.RENUM_ADOPTED_TO_DRAFT.items():
        assert article_map["adopted"][str(adopted)]["draft_counterpart"] == draft
        assert article_map["draft"][str(draft)]["adopted_counterpart"] == adopted


def test_article_map_draft_article_3_has_no_adopted_counterpart(article_map):
    assert article_map["draft"]["3"]["name"] == "Thoroughfares"
    assert article_map["draft"]["3"]["adopted_counterpart"] is None


def test_article_map_names_match_source_headings(article_map):
    assert article_map["draft"]["7"]["name"] == "Use Standards"
    assert article_map["draft"]["8"]["name"] == "Administration"
    # Renumbering shifts NUMBERS only — the adopted name is the same string
    # under the mapped draft number (CONTRACT.md §5.3).
    assert article_map["adopted"]["6"]["name"] == article_map["draft"]["7"]["name"]
    assert article_map["adopted"]["7"]["name"] == article_map["draft"]["8"]["name"]


# --------------------------------------------------------------------------- #
# crosswalk.json — match/unmatched counts
# --------------------------------------------------------------------------- #


@requires_pdf
def test_crosswalk_reports_match_and_unmatched_counts(crosswalk_doc):
    counts = crosswalk_doc["counts"]
    assert counts["matches"] == len(crosswalk_doc["matches"]) > 0
    assert counts["unmatched_adopted"] == len(crosswalk_doc["unmatched"]["adopted"])
    assert counts["unmatched_draft"] == len(crosswalk_doc["unmatched"]["draft"])
    # Every matched article pair contributes at least one section-level match.
    assert counts["matches_section_level"] >= len(cw.MATCHED_ADOPTED_ARTICLES)


@requires_pdf
def test_crosswalk_never_matches_across_different_section_numbers(crosswalk_doc):
    for m in crosswalk_doc["matches"]:
        a_sec = m["adopted_id"].split(".s", 1)[1].split(".")[0]
        d_sec = m["draft_id"].split(".s", 1)[1].split(".")[0]
        assert a_sec == d_sec, f"section-number mismatch in a match: {m}"


@requires_pdf
def test_crosswalk_excludes_out_of_scope_articles_by_name_not_silently(crosswalk_doc):
    excluded = crosswalk_doc["excluded_articles"]
    assert "adopted:2" in excluded  # districts.json is blocked on D-0001/D-0002 — must not be touched
    assert "draft:3" in excluded  # Thoroughfares — no adopted counterpart
    assert "adopted:8" in excluded and "draft:9" in excluded  # Definitions — flat term list


@requires_pdf
def test_crosswalk_a7_s12_matches_a8_s12(crosswalk_doc):
    """The task brief's own worked example: adopted Article 7 (Administration)
    §12 (Subdivision) <-> draft Article 8 (Administration) §12."""
    hit = [m for m in crosswalk_doc["matches"] if m["adopted_id"] == "adopted:a7.s12" and m["level"] == "section"]
    assert len(hit) == 1
    assert hit[0]["draft_id"] == "draft:a8.s12"
    assert hit[0]["adopted_title"] == hit[0]["draft_title"] == "SUBDIVISION"
    assert hit[0]["confidence"] == 1.0


# --------------------------------------------------------------------------- #
# round-tripping a node id through the crosswalk and back is stable
# --------------------------------------------------------------------------- #


@requires_pdf
def test_counterpart_round_trip_is_stable(crosswalk_doc):
    sample = [m["adopted_id"] for m in crosswalk_doc["matches"][:25]]
    assert sample, "expected at least some matches to sample"
    for adopted_id in sample:
        draft_id = cw.counterpart(adopted_id, crosswalk_doc)
        assert draft_id is not None
        back = cw.counterpart(draft_id, crosswalk_doc)
        assert back == adopted_id, f"round trip broke: {adopted_id} -> {draft_id} -> {back}"


@requires_pdf
def test_counterpart_returns_none_for_a_genuinely_unknown_id(crosswalk_doc):
    assert cw.counterpart("adopted:a99.s1", crosswalk_doc) is None


@requires_pdf
def test_unmatched_nodes_are_reported_not_silently_dropped(crosswalk_doc):
    """CONTRACT-style discipline: an id that shows up on only one side must
    appear in that side's unmatched list, not vanish."""
    for node in crosswalk_doc["unmatched"]["adopted"][:10]:
        assert cw.counterpart(node["id"], crosswalk_doc) is None
    for node in crosswalk_doc["unmatched"]["draft"][:10]:
        assert cw.counterpart(node["id"], crosswalk_doc) is None


# --------------------------------------------------------------------------- #
# render_citation() — the four golden strings + article-map-driven renumbering
# --------------------------------------------------------------------------- #


def test_render_citation_golden_1_standard_letter():
    c = cit.Citation("adopted", "adopted", 7, section="12", standard_letter="n", standard_title="Flood Areas")
    assert cit.render_citation(c, scheme="adopted") == "Article 7, Section 12, Standard n. (Flood Areas)"


def test_render_citation_golden_2_use_standards_section():
    c = cit.Citation("adopted", "adopted", 6, section="53", section_title="Residence")
    assert cit.render_citation(c, scheme="adopted") == "Article 6 Use Standards, Section 53. Residence"


def test_render_citation_golden_3_bare_article():
    c = cit.Citation("adopted", "adopted", 2)
    assert cit.render_citation(c, scheme="adopted") == "Article 2 District Standards"


def test_render_citation_golden_4_table():
    c = cit.Citation("adopted", "adopted", 7, table="7.1", table_title="Notices & Public Hearings")
    assert cit.render_citation(c, scheme="adopted") == "Table 7.1 Notices & Public Hearings"


def test_render_citation_adopted_a7_s12_and_draft_a8_s12_use_the_right_article_number_and_name():
    c = cit.Citation("adopted", "adopted", 7, section="12", standard_letter="n", standard_title="Flood Areas")
    adopted_rendered = cit.render_citation(c, scheme="adopted")
    draft_rendered = cit.render_citation(c, scheme="draft")
    assert adopted_rendered.startswith("Article 7, Section 12,")
    assert draft_rendered.startswith("Article 8, Section 12,")
    # Section number is preserved verbatim across the renumbering (CONTRACT.md §5.3).
    assert "Section 12" in adopted_rendered and "Section 12" in draft_rendered

    # And the article NAME resolves correctly in both schemes at the
    # granularity where render_citation() shows it (bare article / bare
    # section) — Administration in both, per article-map.json.
    assert cit.article_name("adopted", 7) == "Administration"
    assert cit.article_name("draft", 8) == "Administration"
    bare = cit.Citation("adopted", "adopted", 7)
    assert cit.render_citation(bare, scheme="adopted") == "Article 7 Administration"
    assert cit.render_citation(bare, scheme="draft") == "Article 8 Administration"


def test_render_citation_raises_no_counterpart_for_draft_article_3():
    c = cit.Citation("draft", "draft", 3)
    with pytest.raises(cit.NoCounterpart):
        cit.render_citation(c, scheme="adopted")


def test_render_citation_never_uses_a_section_symbol():
    c = cit.Citation("adopted", "adopted", 7, section="12", standard_letter="n", standard_title="Flood Areas")
    assert "§" not in cit.render_citation(c, scheme="adopted")


def test_render_citation_rejects_unknown_style():
    c = cit.Citation("adopted", "adopted", 2)
    with pytest.raises(ValueError):
        cit.render_citation(c, scheme="adopted", style="inline")


def test_article_name_raises_when_map_missing(tmp_path, monkeypatch):
    cit.clear_article_map_cache()
    monkeypatch.setattr(cit, "RULESETS_DIR", tmp_path)  # empty dir -- no article-map.json
    with pytest.raises(cit.ArticleMapNotFound):
        cit.article_name("adopted", 2)
    cit.clear_article_map_cache()
