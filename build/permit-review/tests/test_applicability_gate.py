"""Tests engine/applicability.py against the real 21-rule subdivision
criteria artifact -- the W6 task brief's explicit requirement: "Tests BOTH
directions: a criterion that clearly applies, one that clearly does not,
and one that is UNKNOWN -- and prove UNKNOWN still RENDERS the node and
asks, rather than dropping it."
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import applicability as ag  # noqa: E402
from engine.predicates import Verdict  # noqa: E402
from ruleset_build import build_subdivision_criteria as bsc  # noqa: E402


@pytest.fixture(scope="module")
def rules():
    return bsc.build(write=False)["rules"]


def _rule(rules, letter):
    return next(r for r in rules if r["standard_letter"] == letter)


# --------------------------------------------------------------------------- #
# rule t (Impact on Adjoining Municipality) -- gated on
# subdivision.crosses_municipal_boundary. Real subdivision sample facts:
# Shattuck ("approximately 1.9 miles from the nearest municipal boundary")
# and Uberoi ("approximately 1.8 miles") both establish FALSE in practice;
# this test supplies a hypothetical TRUE case instead, to exercise the
# "clearly applies" direction the real samples happen not to contain.
# --------------------------------------------------------------------------- #


def test_clearly_applies_true_verdict_no_board_question(rules):
    rule_t = _rule(rules, "t")
    result = ag.gate_one(rule_t, {"subdivision.crosses_municipal_boundary": True})
    assert result.verdict is Verdict.TRUE
    assert result.board_question is None
    assert result.finding_text is None


# --------------------------------------------------------------------------- #
# rule r (Spaghetti-Lots) -- gated on subdivision.has_shore_frontage_lots.
# Both real subdivision decisions found this FALSE ("This is not applicable
# as none of the proposed lots have any frontage on a river, stream, brook,
# great pond or coastal wetland."). Reproduced here as the "clearly does not
# apply" direction.
# --------------------------------------------------------------------------- #


def test_clearly_does_not_apply_false_verdict_has_finding_text():
    rule_r = _rule(bsc.build(write=False)["rules"], "r")
    result = ag.gate_one(rule_r, {"subdivision.has_shore_frontage_lots": False})
    assert result.verdict is Verdict.FALSE
    assert result.board_question is None
    assert result.finding_text is not None
    assert "Spaghetti-Lots" in result.finding_text
    assert "does not apply" in result.finding_text


# --------------------------------------------------------------------------- #
# rule l (Surface Waters) -- gated on OR(within-watershed, distance<=250ft).
# No fact supplied at all -- UNKNOWN, must still render a result and ask.
# --------------------------------------------------------------------------- #


def test_unknown_verdict_when_no_facts_supplied(rules):
    rule_l = _rule(rules, "l")
    result = ag.gate_one(rule_l, {})
    assert result.verdict is Verdict.UNKNOWN
    assert result.finding_text is None
    assert result.board_question is not None
    assert "Surface Waters" in result.board_question


def test_unknown_verdict_asks_a_first_person_style_question(rules):
    rule_n = _rule(rules, "n")
    result = ag.gate_one(rule_n, {})
    assert result.verdict is Verdict.UNKNOWN
    # A real board_question, not a placeholder -- and it names the standard.
    assert result.board_question
    assert "Flood Areas" in result.board_question
    assert result.board_question.strip().endswith("?")


# --------------------------------------------------------------------------- #
# THE decisive assertion: gate_all() over all 21 rules with NO facts at all
# still returns 21 results -- the four gated rules come back UNKNOWN (never
# silently dropped), the 17 unconditional rules come back TRUE. Nothing is
# missing from the list; nothing is suppressed.
# --------------------------------------------------------------------------- #


def test_gate_all_with_no_facts_renders_all_21_never_drops_the_unknown_ones(rules):
    results = ag.gate_all(rules, facts={})

    assert len(results) == 21
    assert {r.rule_key for r in results} == {r["rule_key"] for r in rules}

    by_key = {r.rule_key: r for r in results}
    for letter in ("l", "n", "r", "t"):
        gated = by_key[f"art7.12.f.1.{letter}"]
        assert gated.verdict is Verdict.UNKNOWN, letter
        assert gated.board_question is not None, letter  # rendered AND asks -- not dropped

    for r in results:
        if r.rule_key not in {f"art7.12.f.1.{l}" for l in ("l", "n", "r", "t")}:
            assert r.verdict is Verdict.TRUE, r.rule_key


def test_gate_all_with_full_facts_resolves_every_gate_one_way_or_the_other(rules):
    facts = {
        "site.within_watershed_of_pond_or_lake": False,
        "site.distance_to_protected_water_ft": 4000,
        "site.in_fema_flood_zone": False,
        "subdivision.has_shore_frontage_lots": False,
        "subdivision.crosses_municipal_boundary": False,
    }
    results = ag.gate_all(rules, facts=facts)
    assert len(results) == 21
    assert all(r.verdict is not Verdict.UNKNOWN for r in results)
    for letter in ("l", "n", "r", "t"):
        gated = next(r for r in results if r.rule_key == f"art7.12.f.1.{letter}")
        assert gated.verdict is Verdict.FALSE
        assert gated.finding_text is not None


def test_gate_all_preserves_rule_order(rules):
    results = ag.gate_all(rules, facts={})
    assert [r.rule_key for r in results] == [r["rule_key"] for r in rules]
