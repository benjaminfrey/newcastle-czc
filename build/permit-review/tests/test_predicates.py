"""Tests engine/predicates.py -- the three-valued applicability predicate
language (W6 task brief: "THE APPLICABILITY GATE"). Offline, no DB, no
network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import predicates as p  # noqa: E402


# --------------------------------------------------------------------------- #
# always / never
# --------------------------------------------------------------------------- #


def test_always_is_true_regardless_of_facts():
    assert p.evaluate({"op": "always"}, {}) is p.Verdict.TRUE
    assert p.evaluate({"op": "always"}, {"anything": "at all"}) is p.Verdict.TRUE


def test_never_is_false_regardless_of_facts():
    assert p.evaluate({"op": "never"}, {}) is p.Verdict.FALSE


# --------------------------------------------------------------------------- #
# fact_true -- the core "clearly applies / clearly does not / unknown" triad,
# using the real fact this project's rule t (Impact on Adjoining
# Municipality) is built on: "subdivision.crosses_municipal_boundary".
# --------------------------------------------------------------------------- #


def test_fact_true_clearly_applies():
    node = {"op": "fact_true", "key": "subdivision.crosses_municipal_boundary"}
    facts = {"subdivision.crosses_municipal_boundary": True}
    assert p.evaluate(node, facts) is p.Verdict.TRUE


def test_fact_true_clearly_does_not_apply():
    node = {"op": "fact_true", "key": "subdivision.crosses_municipal_boundary"}
    facts = {"subdivision.crosses_municipal_boundary": False}
    assert p.evaluate(node, facts) is p.Verdict.FALSE


def test_fact_true_unknown_when_key_absent():
    node = {"op": "fact_true", "key": "subdivision.crosses_municipal_boundary"}
    assert p.evaluate(node, {}) is p.Verdict.UNKNOWN


def test_fact_true_unknown_when_value_is_none():
    node = {"op": "fact_true", "key": "subdivision.crosses_municipal_boundary"}
    facts = {"subdivision.crosses_municipal_boundary": None}
    assert p.evaluate(node, facts) is p.Verdict.UNKNOWN


def test_fact_true_rejects_non_bool_value():
    node = {"op": "fact_true", "key": "k"}
    with pytest.raises(p.PredicateError):
        p.evaluate(node, {"k": "yes"})


# --------------------------------------------------------------------------- #
# numeric comparisons -- rule l's 250 ft proximity gate and rule r's 5:1
# ratio both need these.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "op,value,threshold,expected",
    [
        ("numeric_lte", 250, 250, p.Verdict.TRUE),
        ("numeric_lte", 251, 250, p.Verdict.FALSE),
        ("numeric_lt", 249, 250, p.Verdict.TRUE),
        ("numeric_lt", 250, 250, p.Verdict.FALSE),
        ("numeric_gte", 5.0, 5.0, p.Verdict.TRUE),
        ("numeric_gte", 4.99, 5.0, p.Verdict.FALSE),
        ("numeric_gt", 5.01, 5.0, p.Verdict.TRUE),
        ("numeric_gt", 5.0, 5.0, p.Verdict.FALSE),
    ],
)
def test_numeric_comparisons_both_directions(op, value, threshold, expected):
    node = {"op": op, "key": "distance_ft", "value": threshold}
    assert p.evaluate(node, {"distance_ft": value}) is expected


def test_numeric_comparison_unknown_when_fact_absent():
    node = {"op": "numeric_lte", "key": "distance_ft", "value": 250}
    assert p.evaluate(node, {}) is p.Verdict.UNKNOWN


def test_numeric_comparison_rejects_non_numeric_and_bool():
    node = {"op": "numeric_lte", "key": "distance_ft", "value": 250}
    with pytest.raises(p.PredicateError):
        p.evaluate(node, {"distance_ft": "close"})
    with pytest.raises(p.PredicateError):
        # bool is technically an int subclass in Python -- must be rejected
        # explicitly, not silently treated as 0/1.
        p.evaluate(node, {"distance_ft": True})


# --------------------------------------------------------------------------- #
# in
# --------------------------------------------------------------------------- #


def test_in_true_and_false():
    node = {"op": "in", "key": "zone", "values": ["AE", "VE", "A"]}
    assert p.evaluate(node, {"zone": "AE"}) is p.Verdict.TRUE
    assert p.evaluate(node, {"zone": "X"}) is p.Verdict.FALSE


def test_in_unknown_when_absent():
    node = {"op": "in", "key": "zone", "values": ["AE"]}
    assert p.evaluate(node, {}) is p.Verdict.UNKNOWN


# --------------------------------------------------------------------------- #
# not -- Kleene NOT
# --------------------------------------------------------------------------- #


def test_not_true_becomes_false_and_vice_versa():
    assert p.evaluate({"op": "not", "of": {"op": "always"}}, {}) is p.Verdict.FALSE
    assert p.evaluate({"op": "not", "of": {"op": "never"}}, {}) is p.Verdict.TRUE


def test_not_unknown_stays_unknown():
    inner = {"op": "fact_true", "key": "missing"}
    assert p.evaluate({"op": "not", "of": inner}, {}) is p.Verdict.UNKNOWN


# --------------------------------------------------------------------------- #
# and / or -- Kleene truth tables, including the asymmetric UNKNOWN cases
# (FALSE-anything AND = FALSE even with an UNKNOWN operand; TRUE-anything
# OR = TRUE even with an UNKNOWN operand).
# --------------------------------------------------------------------------- #

TRUE_ = {"op": "always"}
FALSE_ = {"op": "never"}
UNK_ = {"op": "fact_true", "key": "nope"}


@pytest.mark.parametrize(
    "clauses,expected",
    [
        ([TRUE_, TRUE_], p.Verdict.TRUE),
        ([TRUE_, FALSE_], p.Verdict.FALSE),
        ([FALSE_, UNK_], p.Verdict.FALSE),  # known-false clause decides AND regardless of UNKNOWN
        ([TRUE_, UNK_], p.Verdict.UNKNOWN),
        ([UNK_, UNK_], p.Verdict.UNKNOWN),
    ],
)
def test_and_kleene_truth_table(clauses, expected):
    assert p.evaluate({"op": "and", "of": clauses}, {}) is expected


@pytest.mark.parametrize(
    "clauses,expected",
    [
        ([FALSE_, FALSE_], p.Verdict.FALSE),
        ([TRUE_, FALSE_], p.Verdict.TRUE),
        ([TRUE_, UNK_], p.Verdict.TRUE),  # known-true clause decides OR regardless of UNKNOWN
        ([FALSE_, UNK_], p.Verdict.UNKNOWN),
        ([UNK_, UNK_], p.Verdict.UNKNOWN),
    ],
)
def test_or_kleene_truth_table(clauses, expected):
    assert p.evaluate({"op": "or", "of": clauses}, {}) is expected


def test_and_or_reject_empty_or_non_list_of():
    with pytest.raises(p.PredicateError):
        p.evaluate({"op": "and", "of": []}, {})
    with pytest.raises(p.PredicateError):
        p.evaluate({"op": "or", "of": "not-a-list"}, {})


# --------------------------------------------------------------------------- #
# rule l's real compound predicate: OR(within watershed, within 250 ft) --
# exercised end to end with all three verdicts.
# --------------------------------------------------------------------------- #

SURFACE_WATERS_PREDICATE = {
    "op": "or",
    "of": [
        {"op": "fact_true", "key": "site.within_watershed_of_pond_or_lake"},
        {"op": "numeric_lte", "key": "site.distance_to_protected_water_ft", "value": 250},
    ],
}


def test_surface_waters_predicate_clearly_applies_by_distance():
    facts = {
        "site.within_watershed_of_pond_or_lake": False,
        "site.distance_to_protected_water_ft": 40,
    }
    assert p.evaluate(SURFACE_WATERS_PREDICATE, facts) is p.Verdict.TRUE


def test_surface_waters_predicate_clearly_does_not_apply():
    facts = {
        "site.within_watershed_of_pond_or_lake": False,
        "site.distance_to_protected_water_ft": 4000,
    }
    assert p.evaluate(SURFACE_WATERS_PREDICATE, facts) is p.Verdict.FALSE


def test_surface_waters_predicate_unknown_when_no_facts_supplied():
    assert p.evaluate(SURFACE_WATERS_PREDICATE, {}) is p.Verdict.UNKNOWN


# --------------------------------------------------------------------------- #
# malformed data never falls through to eval/exec/getattr -- it is a hard
# PredicateError, not a silent False/UNKNOWN.
# --------------------------------------------------------------------------- #


def test_unknown_op_raises():
    with pytest.raises(p.PredicateError):
        p.evaluate({"op": "__import__"}, {})


def test_non_dict_node_raises():
    with pytest.raises(p.PredicateError):
        p.evaluate("os.system('rm -rf /')", {})  # type: ignore[arg-type]


def test_missing_required_key_raises():
    with pytest.raises(p.PredicateError):
        p.evaluate({"op": "fact_true"}, {})


# --------------------------------------------------------------------------- #
# Verdict itself refuses to be used as a Python bool -- guards against
# 'UNKNOWN' silently behaving as truthy or falsy anywhere downstream.
# --------------------------------------------------------------------------- #


def test_verdict_has_no_truthiness():
    with pytest.raises(TypeError):
        bool(p.Verdict.UNKNOWN)
    with pytest.raises(TypeError):
        if p.Verdict.TRUE:  # pragma: no branch
            pass


def test_verdict_string_values_match_findings_nodes_check_constraint():
    # app/migrations/0013_findings_tree.sql: applicability_verdict IN
    # ('true','false','unknown') -- Verdict must serialize to exactly these.
    assert p.Verdict.TRUE.value == "true"
    assert p.Verdict.FALSE.value == "false"
    assert p.Verdict.UNKNOWN.value == "unknown"
