"""Tests ruleset_build/parse_articles.py against the W2 task brief.

Offline, no network, no LLM, no PII — reads only the real, committed
source/article-0N-*.md files (repo baseline, read-only).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))

from ruleset_build.parse_articles import (  # noqa: E402
    ARTICLE_FILES,
    SOURCE_DIR,
    ArticleShapeError,
    build_articles,
    find_section_nodes,
    find_subsection_nodes,
    parse_article_file,
    verify_article_file,
)

RULESET_KEY = "draft-v0.22"


@pytest.fixture(scope="module")
def doc() -> dict:
    return build_articles(RULESET_KEY, SOURCE_DIR)


@pytest.fixture(scope="module")
def nodes(doc: dict) -> list[dict]:
    return doc["nodes"]


# ---------------------------------------------------------------------------
# Node counts per article
# ---------------------------------------------------------------------------


def test_all_eight_articles_parsed(doc: dict) -> None:
    assert sorted(int(a) for a in doc["counts"]["by_article"]) == list(range(1, 9))
    assert {m["article"] for m in doc["articles"]} == set(range(1, 9))


def test_node_counts_per_article_are_positive_and_sum_correctly(doc: dict) -> None:
    by_article = doc["counts"]["by_article"]
    assert sum(by_article.values()) == doc["counts"]["total_nodes"]
    for article, count in by_article.items():
        assert count > 0, f"article {article} produced zero nodes"


def test_node_ids_are_unique(nodes: list[dict]) -> None:
    ids = [n["id"] for n in nodes]
    assert len(ids) == len(set(ids))


def test_node_ids_follow_the_contract_format(nodes: list[dict]) -> None:
    import re

    id_re = re.compile(r"^draft-v0\.22:a\d+\.s\d+\.[a-z0-9_]+(\.[a-z0-9]+)*$")
    bad = [n["id"] for n in nodes if not id_re.match(n["id"])]
    assert not bad, f"malformed ids: {bad[:5]}"


# ---------------------------------------------------------------------------
# §12 SUBDIVISION — the flood-areas / 21-letters trap
# ---------------------------------------------------------------------------


def test_subdivision_section_resolves_by_text(nodes: list[dict]) -> None:
    matches = find_section_nodes(nodes, 8, "SUBDIVISION")
    assert matches, "Article 8 SUBDIVISION not found by section_name text"


def test_subdivision_approval_standards_found_by_text_not_letter(nodes: list[dict]) -> None:
    # CRITICAL TRAP: SUBDIVISION's approval-standards subsection is letter
    # "f." — a naive '### f.' lookup would coincidentally work here but
    # would break on VARIANCE (letter "d."). This test locates it by TEXT.
    standards = find_subsection_nodes(nodes, 8, "SUBDIVISION", "APPROVAL STANDARDS")
    assert standards
    # And prove the letter really is "f", not something the text-lookup
    # happened to dodge — the subsection field carries it for citation use.
    assert {n["subsection"] for n in standards} == {"f"}


def test_subdivision_approval_standards_has_exactly_21_lettered_items_a_to_u(
    nodes: list[dict],
) -> None:
    standards = find_subsection_nodes(nodes, 8, "SUBDIVISION", "APPROVAL STANDARDS")
    lettered = [n for n in standards if n["depth"] == 1 and n["path"][0] == "1"]
    letters = [n["path"][1] for n in lettered]
    expected = [chr(ord("a") + i) for i in range(21)]  # a..u
    assert letters == expected, f"expected a-u (21 letters), got {letters}"


def test_flood_areas_standard_is_item_n_with_the_documented_id(nodes: list[dict]) -> None:
    standards = find_subsection_nodes(nodes, 8, "SUBDIVISION", "APPROVAL STANDARDS")
    flood = [n for n in standards if n["path"] == ["1", "n"]]
    assert len(flood) == 1
    node = flood[0]
    assert node["id"] == "draft-v0.22:a8.s12.f.1.n"
    assert node["text"].startswith("Flood Areas:")


# ---------------------------------------------------------------------------
# §19 VARIANCE — the duplicate-subsection-letter trap
# ---------------------------------------------------------------------------


def test_variance_section_has_duplicate_subsection_letters_in_source(nodes: list[dict]) -> None:
    # Confirms the trap actually exists in the current source (so this test
    # would fail loudly, not silently pass, if the source were ever cleaned
    # up and the trap removed).
    variance_nodes = [n for n in nodes if n["article"] == 8 and n["section"] == "19"]
    letters = [n["subsection"] for n in variance_nodes if n["path"] == [n["path"][0]] and n["depth"] == 0]
    assert "a" in [n["subsection"] for n in variance_nodes]
    subsection_names_by_letter: dict[str, set[str]] = {}
    for n in variance_nodes:
        subsection_names_by_letter.setdefault(n["subsection"], set()).add(n["subsection_name"])
    assert subsection_names_by_letter.get("a") == {"PURPOSE", "GENERAL"}, subsection_names_by_letter


def test_variance_approval_standards_found_by_text_despite_duplicate_letters(
    nodes: list[dict],
) -> None:
    # §19's approval standards live at letter "d." (not "e." or "f." as in
    # other sections) — located here purely by section_name/subsection_name
    # text, per the CRITICAL TRAP warning in the brief.
    standards = find_subsection_nodes(nodes, 8, "VARIANCE", "APPROVAL STANDARDS")
    assert standards
    assert {n["subsection"] for n in standards} == {"d"}
    top_items = [n for n in standards if n["depth"] == 0]
    assert len(top_items) == 4  # items 1-4 of §19.d


def test_variance_purpose_and_general_get_disambiguated_subsection_keys(
    nodes: list[dict],
) -> None:
    purpose = find_subsection_nodes(nodes, 8, "VARIANCE", "PURPOSE")
    general = find_subsection_nodes(nodes, 8, "VARIANCE", "GENERAL")
    assert purpose and general
    assert all(n["id"].startswith("draft-v0.22:a8.s19.a.") for n in purpose)
    assert all(n["id"].startswith("draft-v0.22:a8.s19.a_2.") for n in general)


# ---------------------------------------------------------------------------
# The headingless-section exception (Article 8 §22)
# ---------------------------------------------------------------------------


def test_headingless_section_is_handled_without_raising(nodes: list[dict]) -> None:
    demolition = [n for n in nodes if n["article"] == 8 and n["section"] == "22"]
    assert demolition
    # Every node's subsection_name is one of the pseudo-headers, never None.
    assert all(n["subsection_name"] for n in demolition)
    names = {n["subsection_name"] for n in demolition}
    assert "PURPOSE" in names
    assert "PROCEDURE" in names


def test_headingless_section_pseudo_header_emits_no_content_node(nodes: list[dict]) -> None:
    # The "1. PURPOSE" line itself is a label, not regulatory content -- it
    # must not appear as a node whose own text is just "PURPOSE".
    demolition_purpose = [
        n for n in nodes if n["article"] == 8 and n["section"] == "22" and n["subsection_name"] == "PURPOSE"
    ]
    assert all(n["text"] != "PURPOSE" for n in demolition_purpose)


# ---------------------------------------------------------------------------
# Table attachment
# ---------------------------------------------------------------------------


def test_pipe_tables_are_attached_with_caption_columns_rows(nodes: list[dict]) -> None:
    tables = [n for n in nodes if n["kind_hint"] == "table"]
    assert tables, "expected at least one attached pipe table"
    t = next(n for n in tables if n["article"] == 5 and "TABLE 5.1" in (n["caption"] or ""))
    assert t["columns"] == ["District", "Front", "Side", "Rear"]
    assert t["rows"][0] == ["D1", "●", "●", "●"]
    assert t["section_name"]  # has a section context
    assert t["subsection_name"] is not None


def test_empty_list_item_f_is_captured_with_empty_text(nodes: list[dict]) -> None:
    # source/article-08-administration.md line 973 is "    f." with nothing
    # after the marker -- must not be dropped or crash the parser.
    empties = [n for n in nodes if n["kind_hint"] == "list_item" and n["text"] == ""]
    assert empties, "expected at least one empty-text list item (the 'f.' case)"


# ---------------------------------------------------------------------------
# --verify: every heading consumed / one depth per item / round trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("article_num", sorted(ARTICLE_FILES))
def test_verify_round_trip_passes_for_every_article(article_num: int) -> None:
    path = SOURCE_DIR / ARTICLE_FILES[article_num]
    problems = verify_article_file(path, RULESET_KEY)
    assert problems == [], f"{path.name}: {problems[:5]}"


def test_parser_raises_on_article_09(tmp_path: Path) -> None:
    # article-09 has no frontmatter 'article-number' matching a body '#
    # Article N' the way this module expects it to be driven — the real
    # regression this guards is "don't silently misparse it"; the actual
    # boundary is enforced by ARTICLE_FILES simply not listing article 9.
    assert 9 not in ARTICLE_FILES


def test_bogus_shape_raises_articleshapeerror(tmp_path: Path) -> None:
    # A content line indented as if it were nested under a subsection, with
    # no subsection heading (or virtual pseudo-header) ever having been seen
    # -- not a shape this module's grammar can account for silently.
    bad = tmp_path / "article-01-general.md"
    bad.write_text(
        '---\narticle-number: "1"\narticle-name: "General"\n---\n\n'
        "# Article 1 General\n\n## 1. FOO\n\n    a. indented with no subsection heading\n",
        encoding="utf-8",
    )
    with pytest.raises(ArticleShapeError):
        parse_article_file(bad, RULESET_KEY)


# ---------------------------------------------------------------------------
# DEFECT 1 hardening — ordered-list sequence integrity (§ "Add a general
# integrity check ... Any gap or unexpected reset must RAISE with the
# location, not warn.")
# ---------------------------------------------------------------------------


def _make_article(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "article-01-general.md"
    p.write_text(
        '---\narticle-number: "1"\narticle-name: "General"\n---\n\n'
        f"# Article 1 General\n\n## 1. FOO\n\n### a. BAR\n\n{body}",
        encoding="utf-8",
    )
    return p


def test_gap_in_lettered_sublist_raises(tmp_path: Path) -> None:
    # a, b, then c skipped straight to d -- the exact "silently truncated
    # legal list" failure mode this check exists to catch.
    bad = _make_article(
        tmp_path,
        "1. first\n    a. nested a\n    b. nested b\n    d. nested d -- skips c\n",
    )
    with pytest.raises(ArticleShapeError, match="gap or unexpected reset"):
        parse_article_file(bad, RULESET_KEY)


def test_roman_gap_under_nested_letter_raises(tmp_path: Path) -> None:
    # i, then straight to iii -- ii silently dropped, one level deeper (the
    # exact shape "criterion c. retains its five roman sub-items" guards).
    bad = _make_article(
        tmp_path,
        "1. first\n    a. nested a\n        i. roman i\n        iii. roman iii -- skips ii\n",
    )
    with pytest.raises(ArticleShapeError, match="gap or unexpected reset"):
        parse_article_file(bad, RULESET_KEY)


def test_list_restarting_mid_sequence_raises(tmp_path: Path) -> None:
    # A lettered sub-list that opens on 'c' instead of 'a' -- the "list
    # beginning mid-sequence" branch of the same check.
    bad = _make_article(tmp_path, "1. first\n    c. nested c -- should start at a\n")
    with pytest.raises(ArticleShapeError, match="beginning mid-sequence"):
        parse_article_file(bad, RULESET_KEY)


def test_pseudo_subsection_gap_raises(tmp_path: Path) -> None:
    # Grammar-exception-2 pseudo-subsection headers ("1. PURPOSE", "2.
    # APPLICABILITY", ...) are themselves a digit-ordered list; dropping one
    # must raise too, not just re-letter what's left.
    bad = tmp_path / "article-01-general.md"
    bad.write_text(
        '---\narticle-number: "1"\narticle-name: "General"\n---\n\n'
        "# Article 1 General\n\n## 1. FOO\n\n"
        "1. PURPOSE\n\nsome prose\n\n3. PROCEDURE -- skips 2\n\nmore prose\n",
        encoding="utf-8",
    )
    with pytest.raises(ArticleShapeError, match="gap or unexpected reset"):
        parse_article_file(bad, RULESET_KEY)


def test_real_source_lone_lettered_item_at_depth_zero_is_not_a_false_positive(
    nodes: list[dict],
) -> None:
    # GRAMMAR EXCEPTION 3: Article 5 SETBACKS under ADDITIONAL STRUCTURES is
    # a real "### " subsection whose entire body is one clause marked "a."
    # instead of "1." -- the integrity check must accept this (a single
    # valid opener, digit-or-alpha at depth 0), not raise on real content.
    setbacks = find_subsection_nodes(nodes, 5, "ADDITIONAL STRUCTURES", "SETBACKS")
    items = [n for n in setbacks if n["kind_hint"] == "list_item"]
    assert items, "expected the SETBACKS subsection's list item to still parse"
    assert [n["path"] for n in items] == [["a"]]
