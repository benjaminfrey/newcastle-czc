"""Tests ruleset_build/build_subdivision_criteria.py -- the W6 "criteria
set" builder. Offline, reads only rulesets/adopted/articles.json (already
built, committed source), writes only into a temp directory (never the
real rulesets/adopted/criteria-subdivision.json a developer may have on
disk -- see the `tmp_out` fixture).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.citation import Citation, render_citation  # noqa: E402
from ruleset_build import build_subdivision_criteria as bsc  # noqa: E402


@pytest.fixture()
def artifact(tmp_path, monkeypatch):
    out = tmp_path / "criteria-subdivision.json"
    monkeypatch.setattr(bsc, "OUT_PATH", out)
    return bsc.build(write=True)


def test_exactly_21_rules_a_through_u(artifact):
    letters = sorted(r["standard_letter"] for r in artifact["rules"])
    assert letters == list("abcdefghijklmnopqrstu")
    assert artifact["counts"]["rules"] == 21


def test_judgement_count_is_14_and_matches_kind_field(artifact):
    judgement_rows = [r for r in artifact["rules"] if r["kind"] == "judgement"]
    assert len(judgement_rows) == 14
    assert sorted(r["standard_letter"] for r in judgement_rows) == artifact["counts"]["judgement_letters"]
    # every judgement row must carry at least one tell; nothing else may.
    for r in artifact["rules"]:
        if r["kind"] == "judgement":
            assert r["judgement_tells"], r["rule_key"]
        else:
            assert r["judgement_tells"] == [], r["rule_key"]


def test_kind_distribution_matches_manual_classification(artifact):
    by_letter = {r["standard_letter"]: r["kind"] for r in artifact["rules"]}
    assert by_letter == {
        "a": "procedural", "b": "procedural",
        "c": "judgement", "d": "judgement", "e": "judgement", "f": "judgement",
        "g": "judgement", "h": "judgement", "i": "judgement", "j": "judgement",
        "k": "judgement", "l": "judgement", "m": "judgement",
        "n": "procedural",
        "o": "boolean", "p": "boolean",
        "q": "judgement",
        "r": "numeric",
        "s": "judgement", "t": "judgement",
        "u": "boolean",
    }


def test_source_text_is_verbatim_against_articles_json(artifact):
    """The two single-sentence standards (o, p) must appear byte-for-byte
    in criteria-subdivision.json -- no rewording, no summarising."""
    articles = json.loads((bsc.RULESETS_DIR / "adopted" / "articles.json").read_text())
    node = bsc._find_node(articles["articles"], bsc.ART7_12_F_1_ID)
    by_letter = {c["number"]: c["text"] for c in node["children"]}

    for r in artifact["rules"]:
        letter = r["standard_letter"]
        if letter == "c":
            continue  # c is the one standard with sub-items, checked separately below
        assert r["source_text"] == by_letter[letter], letter


def test_standard_c_source_text_contains_every_subitem_verbatim(artifact):
    row = next(r for r in artifact["rules"] if r["standard_letter"] == "c")
    articles = json.loads((bsc.RULESETS_DIR / "adopted" / "articles.json").read_text())
    node = bsc._find_node(articles["articles"], bsc.ART7_12_F_1_ID)
    c_node = next(c for c in node["children"] if c["number"] == "c")

    assert row["source_text"].startswith(c_node["text"])
    for sub in c_node["children"]:
        assert sub["text"] in row["source_text"]


def test_only_standard_n_mandates_a_condition(artifact):
    mandated = [r["standard_letter"] for r in artifact["rules"] if r["mandates_condition"] is not None]
    assert mandated == ["n"]
    n = next(r for r in artifact["rules"] if r["standard_letter"] == "n")
    assert n["mandates_condition"]["fires"] == "always"
    assert "three feet" in n["mandates_condition"]["text"]
    assert "100-year flood elevation" in n["mandates_condition"]["text"]


def test_no_rule_carries_a_textual_exception(artifact):
    # None of the 21 standards' own text names an exception/waiver clause --
    # exceptions must be present as a real (empty) list, never omitted.
    for r in artifact["rules"]:
        assert r["exceptions"] == []


def test_four_rules_carry_a_real_applicability_gate_the_rest_are_unconditional(artifact):
    gated = {r["standard_letter"] for r in artifact["rules"] if r["applicability"] != {"op": "always"}}
    assert gated == {"l", "n", "r", "t"}


def test_rule_r_has_a_numeric_test(artifact):
    r = next(r for r in artifact["rules"] if r["standard_letter"] == "r")
    assert r["test_json"]["comparison"] == "lte"
    assert r["test_json"]["threshold"] == 5.0


def test_citations_render_in_the_real_decisions_style(artifact):
    for row in artifact["rules"]:
        c = Citation(**row["citation"])
        rendered = render_citation(c, scheme="adopted")
        assert rendered.startswith(f"Article 7, Section 12, Standard {row['standard_letter']}.")
        assert "§" not in rendered

    # Spot-check against the exact strings observed in both real subdivision
    # decisions' Conclusions of Law sections.
    n = next(r for r in artifact["rules"] if r["standard_letter"] == "n")
    c_ = Citation(**n["citation"])
    assert render_citation(c_, scheme="adopted") == "Article 7, Section 12, Standard n. (Flood Areas)"

    r_ = next(r for r in artifact["rules"] if r["standard_letter"] == "r")
    c_ = Citation(**r_["citation"])
    assert render_citation(c_, scheme="adopted") == "Article 7, Section 12, Standard r. (Spaghetti-Lots)"


def test_criteria_set_is_planning_board_subdivision(artifact):
    cs = artifact["criteria_set"]
    assert cs["set_key"] == "subdivision"
    assert cs["application_type"] == "subdivision"
    assert cs["authority"] == "planning_board"


def test_build_is_deterministic_modulo_generated_at(tmp_path, monkeypatch):
    out = tmp_path / "criteria-subdivision.json"
    monkeypatch.setattr(bsc, "OUT_PATH", out)
    a1 = bsc.build(write=True)
    a2 = bsc.build(write=True)
    a1 = {k: v for k, v in a1.items() if k != "generated_at"}
    a2 = {k: v for k, v in a2.items() if k != "generated_at"}
    assert a1 == a2


def test_extract_standards_raises_loudly_on_a_drifted_shape(monkeypatch):
    """Simulates the source article node losing a letter -- must raise
    SubdivisionCriteriaBuildError, never silently reclassify or drop it."""

    def fake_load_articles():
        return {
            "articles": [
                {
                    "id": bsc.ART7_12_F_1_ID,
                    "children": [
                        {"number": letter, "text": f"Standard {letter}.", "children": []}
                        for letter in "abcdefghijklmnopqrst"  # only 20 -- missing 'u'
                    ],
                }
            ]
        }

    monkeypatch.setattr(bsc, "_load_articles", fake_load_articles)
    with pytest.raises(bsc.SubdivisionCriteriaBuildError):
        bsc.extract_standards()
