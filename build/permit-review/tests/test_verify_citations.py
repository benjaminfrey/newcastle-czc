"""Regression tests for the Defect-2 letter-resolution fix in
ruleset_build/verify_citations.py.

Implements the fix's own brief: resolution must be DEPTH-SCOPED (the
lettered-standards level under an APPROVAL STANDARDS subsection, never a
descendant one level further down) and must surface — never silently
guess past — a letter that is genuinely ambiguous at that level.

The five REAL citations exercised here are drawn from the actual sentence
in the Shattuck 2025 decision (White Rd, M003/L059, "Subdivision FoF & CoL
2025.12.18.pdf", p.12): "Article 7, Section 12, Standards c, d, e, f, h,
i, k, l, m, p, q, s, t, and u." Letters i and c are the two that expose
the bug (i collides with the roman numeral i. nested under criterion c;
c is the parent that nesting lives under); n, r, and j are plain
top-level letters included so the fix is shown not to have broken the
ordinary case.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ruleset_build.verify_citations import (
    Candidate,
    _find_standard_letter,
    _standard_level_items,
    load_node_index,
    resolve_candidate,
)

RULESET_KEY = "adopted"


def _standard_candidate(letter: str) -> Candidate:
    """Builds the same Candidate shape _m_article_section_standards()
    produces for "Article 7, Section 12, Standard <letter>." — i.e. a real
    parsed citation, not a hand-rolled shortcut."""
    raw = f"Article 7, Section 12, Standard {letter}."
    parsed = {"article": 7, "section": "12", "standard": letter, "standard_name": None}
    return Candidate("article_section_standard", 0, len(raw), raw, parsed)


@pytest.fixture(scope="module")
def idx():
    index = load_node_index(RULESET_KEY)
    if index.articles is None:
        pytest.skip(f"rulesets/{RULESET_KEY}/articles.json not present: {index.articles_error}")
    return index


# ---------------------------------------------------------------------- #
# The core bug: "Standard i." must resolve to the top-level criterion,
# never to the roman numeral i. nested under criterion c. Pollution.
# ---------------------------------------------------------------------- #

def test_standard_i_resolves_to_top_level_municipal_solid_waste(idx):
    before_buggy_target = "art7.12.f.1.c.i"  # what first-match-wins depth-first returned
    after_correct_target = "art7.12.f.1.i"  # Municipal Solid Waste Disposal

    result = resolve_candidate(_standard_candidate("i"), idx)

    assert result["status"] == "resolved", result
    assert result["detail"]["id"] == after_correct_target
    assert result["detail"]["id"] != before_buggy_target
    assert "municipal solid waste" in result["detail"]["text_preview"].casefold()


def test_standard_i_never_matches_the_nested_roman_under_pollution(idx):
    """Direct check on the depth-scoped level function itself: the roman
    numeral i. living at art7.12.f.1.c.i must not even be a CANDIDATE for
    letter 'i' — not filtered out after the fact, structurally absent from
    the level the search considers."""
    by_id = idx.article_nodes_by_id
    appstd = by_id["art7.12.f"]
    level_ids = {item["id"] for item in _standard_level_items(appstd)}

    assert "art7.12.f.1.i" in level_ids
    assert "art7.12.f.1.c.i" not in level_ids  # one level too deep — never a candidate

    matches = _find_standard_letter(appstd, "i")
    assert [m["id"] for m in matches] == ["art7.12.f.1.i"]


# ---------------------------------------------------------------------- #
# c. itself: the parent criterion, not swallowed by its own children.
# ---------------------------------------------------------------------- #

def test_standard_c_resolves_to_pollution_criterion_itself(idx):
    result = resolve_candidate(_standard_candidate("c"), idx)

    assert result["status"] == "resolved", result
    assert result["detail"]["id"] == "art7.12.f.1.c"
    assert "pollution" in result["detail"]["text_preview"].casefold()


# ---------------------------------------------------------------------- #
# Plain top-level letters unaffected by the roman-numeral collision must
# still resolve correctly — the fix must not have broken the ordinary case.
# ---------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "letter,expected_id,expected_text_fragment",
    [
        ("n", "art7.12.f.1.n", "flood areas"),
        ("r", "art7.12.f.1.r", "spaghetti-lots"),
        ("j", "art7.12.f.1.j", "aesthetic, cultural"),
    ],
)
def test_standard_plain_letters_resolve_correctly(idx, letter, expected_id, expected_text_fragment):
    result = resolve_candidate(_standard_candidate(letter), idx)

    assert result["status"] == "resolved", result
    assert result["detail"]["id"] == expected_id
    assert expected_text_fragment in result["detail"]["text_preview"].casefold()


# ---------------------------------------------------------------------- #
# 'v' must resolve honestly to "no such top-level standard" now that the
# nested roman numeral v. (also under criterion c) can no longer stand in
# for it — before the fix this silently "resolved" to a false match.
# ---------------------------------------------------------------------- #

def test_standard_v_has_no_top_level_match_and_is_reported_honestly(idx):
    result = resolve_candidate(_standard_candidate("v"), idx)

    assert result["status"] == "unresolved"
    assert result["code"] == "no_standard_letter"
    assert "art7.12.f.1.c.v" not in result["reason"]  # never silently offered as a fallback match


# ---------------------------------------------------------------------- #
# The second head named in the brief: art7.19.d VARIANCE has no single
# standards level (Undue Hardship a-d under item 3, Practical Difficulty
# a-g under item 4) — a bare "Standard c." is genuinely ambiguous between
# the two and must be reported as such, never silently picked.
# ---------------------------------------------------------------------- #

def test_variance_standard_c_is_reported_ambiguous_not_guessed(idx):
    candidate = Candidate(
        "article_section_standard",
        0,
        0,
        "Article 7, Section 19, Standard c.",
        {"article": 7, "section": "19", "standard": "c", "standard_name": None},
    )
    result = resolve_candidate(candidate, idx)

    assert result["status"] == "unresolved"
    assert result["code"] == "ambiguous_standard_letter"
    candidate_ids = {c["id"] for c in result["detail"]["candidates"]}
    assert candidate_ids == {"art7.19.d.3.c", "art7.19.d.4.c"}


def test_variance_standard_a_also_ambiguous_across_items_2_3_and_4(idx):
    """'a' appears under item 2 (general grounds), item 3 (Undue Hardship),
    AND item 4 (Practical Difficulty) — the same latent collision,
    exercised at a different letter, to confirm the ambiguity check isn't
    hard-coded to 'c' and generalizes to an n-way collision, not just 2."""
    by_id = idx.article_nodes_by_id
    appstd = by_id["art7.19.d"]
    matches = _find_standard_letter(appstd, "a")
    assert {m["id"] for m in matches} == {
        "art7.19.d.2.a",
        "art7.19.d.3.a",
        "art7.19.d.4.a",
    }
