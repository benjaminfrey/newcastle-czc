"""tests/test_silent_error.py -- proves eval/silent_error.py's
silent_error_rate is measured at a layer where a silent error is genuinely
POSSIBLE, and that the rate actually MOVES on bad input (D1 of the W8
tightening round -- see eval/silent_error.py's own module docstring for the
full "why this layer" argument).

THE ACCEPTANCE TEST THIS FILE ANSWERS: can bad input make the number bad?
Every test below either (a) feeds a wrong, unverified fact and asserts the
rate goes NONZERO, or (b) feeds a clean/verified input and asserts it
returns to 0 or "not computable" -- never both directions asserted by the
same test, so a regression in either direction is caught by name.

Does NOT touch ingest/fields.py's FieldCandidate.__post_init__ invariant,
and does not add any escape hatch to it -- see eval/silent_error.py's
docstring for why that invariant is right to leave alone and wrong to
measure at.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from eval import silent_error as se


# --------------------------------------------------------------------------- #
# extract_fact_keys -- the predicate-tree walker the rest of this module
# depends on. Checked against the real shape rulesets/adopted/
# criteria-subdivision.json actually stores (fact_true / numeric_lte / or),
# not an invented shape.
# --------------------------------------------------------------------------- #


class TestExtractFactKeys:
    def test_always_and_never_reference_no_fact(self):
        assert se.extract_fact_keys({"op": "always"}) == frozenset()
        assert se.extract_fact_keys({"op": "never"}) == frozenset()

    def test_fact_true_single_key(self):
        assert se.extract_fact_keys({"op": "fact_true", "key": "site.in_fema_flood_zone"}) == \
            frozenset({"site.in_fema_flood_zone"})

    def test_or_of_fact_true_and_numeric_lte_real_standard_l_shape(self):
        # The real art7.12.f.1.l predicate, verbatim (rulesets/adopted/
        # criteria-subdivision.json) -- two distinct keys under one "or".
        predicate = {
            "op": "or",
            "of": [
                {"op": "fact_true", "key": "site.within_watershed_of_pond_or_lake"},
                {"op": "numeric_lte", "key": "site.distance_to_protected_water_ft", "value": 250},
            ],
        }
        assert se.extract_fact_keys(predicate) == frozenset(
            {"site.within_watershed_of_pond_or_lake", "site.distance_to_protected_water_ft"}
        )

    def test_nested_and_or_not_all_recurse(self):
        predicate = {
            "op": "and",
            "of": [
                {"op": "not", "of": {"op": "fact_true", "key": "a"}},
                {"op": "or", "of": [{"op": "fact_true", "key": "b"}, {"op": "numeric_gt", "key": "c", "value": 1}]},
            ],
        }
        assert se.extract_fact_keys(predicate) == frozenset({"a", "b", "c"})


class TestFactDependentRulesReadLiveFromRuleset:
    """Confirms the 4 fact-dependent standards (l, n, r, t) come from
    actually loading the built ruleset, not a hardcoded list -- so this
    stays correct if the ruleset's conditionals ever change."""

    def test_exactly_four_standards_are_fact_dependent(self):
        with tempfile.TemporaryDirectory(prefix="test-silent-error-") as td:
            conn = se._fresh_conn(Path(td))
            try:
                from app import cases
                from engine import criteria_seed, subdivision_review

                seeded = criteria_seed.sync_subdivision_criteria(
                    conn, ruleset_id=se.RULESET_ID, actor_user_id=se.ACTOR
                )
                rules = subdivision_review.load_rules_for_criteria_set(conn, seeded["criteria_set_id"])
                dependent = se.fact_dependent_rules(rules)
                letters = sorted(r["standard_letter"] for r in dependent)
                assert letters == ["l", "n", "r", "t"]
            finally:
                conn.close()


# --------------------------------------------------------------------------- #
# THE PROOF: inject a wrong value, watch silent_error_rate go nonzero; feed
# clean input, watch it return to 0 / not-computable. Both directions.
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def results():
    """Module-scoped so the (slow-ish, real-DB, real-walk) scenarios run
    once and every assertion below reads from the same three results --
    mirrors eval/silent_error.run_all_scenarios()'s own three-way design."""
    by_name = {r.scenario: r for r in se.run_all_scenarios()}
    assert set(by_name) == {"dirty_unverified_wrong_facts", "verified_human_confirmed_facts",
                             "no_facts_asserted"}
    return by_name


class TestSilentErrorRateMovesOnBadInput:
    # -- direction 1: bad input makes the number bad -----------------------

    def test_dirty_unverified_wrong_facts_is_nonzero(self, results):
        dirty = results["dirty_unverified_wrong_facts"]
        assert dirty.unflagged_count >= 1, (
            "the dirty scenario must actually produce at least one unflagged (no #boardq/#unresolved) "
            "rendered finding -- otherwise this test would prove nothing"
        )
        assert dirty.silent_error_rate is not None
        assert dirty.silent_error_rate > 0.0, (
            "a wrong, unverified fact for a fact-dependent standard reached rendered output with no "
            "board_question and no #unresolved flag -- silent_error_rate MUST be nonzero here"
        )

    def test_dirty_scenario_specific_nodes_are_flagged_silent(self, results):
        dirty = results["dirty_unverified_wrong_facts"]
        silent_letters = {e.standard_letter for e in dirty.exposures if e.silent}
        # Standards n. (Flood Areas) and r. (Spaghetti-Lots) are the two the
        # dirty scenario actually asserts a wrong fact for.
        assert silent_letters == {"n", "r"}
        for e in dirty.exposures:
            if e.standard_letter in ("n", "r"):
                assert e.applicability_verdict == "false"
                assert e.render_types == ("standard", "finding", "raw"), (
                    "the exact render-node types the PDF pipeline would emit for this node -- no "
                    "'boardq', no 'unresolved': a plain, unhighlighted finding paragraph"
                )
                assert "boardq" not in e.render_types
                assert "unresolved" not in e.render_types

    # -- direction 2: clean/verified input makes the number clean again ----

    def test_verified_human_confirmed_facts_is_zero_not_none(self, results):
        verified = results["verified_human_confirmed_facts"]
        # Same underlying facts as "dirty" (still renders unflagged -- the
        # render layer does not change based on provenance), but now every
        # exposed node's fact keys are backed by a real field_values row.
        assert verified.unflagged_count >= 1
        assert verified.silent_error_rate == 0.0, (
            "the SAME facts as the dirty scenario, but now backed by a real, human-attributed "
            "field_values row (app.extraction.override_field) for every referenced fact key -- "
            "unflagged is fine when it is provably attested; silent_error_rate must read 0.0, not "
            "merely 'not computable'"
        )
        assert verified.silent_count == 0

    def test_no_facts_asserted_is_not_computable_not_a_fake_zero(self, results):
        blank = results["no_facts_asserted"]
        assert blank.unflagged_count == 0, (
            "facts={} means every fact-dependent standard's applicability verdict is UNKNOWN, which "
            "the applicability gate always flags with a board question -- nothing should render "
            "unflagged here"
        )
        assert blank.silent_error_rate is None, (
            "0 unflagged nodes means nothing was exposed to grade -- this MUST print as "
            "'not computable', never as a manufactured clean 0.0 (the same insufficient-n discipline "
            "eval/metrics.py's structural-recall aggregate already uses)"
        )

    def test_verified_fact_keys_reads_real_field_values_rows_not_a_flag(self, results):
        """verified_fact_keys() must trace to an ACTUAL field_values row in
        state confirmed/overridden -- not a bare boolean a caller could set
        without going through app.extraction. Proven by writing one for
        real and reading it back through the same helper the scenarios use."""
        with tempfile.TemporaryDirectory(prefix="test-silent-error-verify-") as td:
            conn = se._fresh_conn(Path(td))
            try:
                from app import cases

                case = cases.create_case(
                    conn, application_type="subdivision", map_lot="TEST-verify", situs_address="n/a",
                    applicant_name="test", actor_user_id=se.ACTOR,
                )
                before = se.verified_fact_keys(conn, case["id"])
                assert before == frozenset()

                se.write_verified_fact(
                    conn, case_id=case["id"], field_key="site.in_fema_flood_zone",
                    label="In FEMA 100-year flood hazard area", value=False,
                    reason="test: real override_field write, DB CHECK enforced",
                )
                after = se.verified_fact_keys(conn, case["id"])
                assert after == frozenset({"site.in_fema_flood_zone"})

                # And the write really did go through app.extraction.override_field --
                # confirm the field_values row itself carries the state/actor/reason
                # the DB CHECK constraint (0001_init.sql) requires for 'overridden'.
                row = conn.execute(
                    "SELECT state, confirmed_by, override_reason FROM field_values WHERE case_id = ?;",
                    (case["id"],),
                ).fetchone()
                assert row["state"] == "overridden"
                assert row["confirmed_by"] == se.ACTOR
                assert row["override_reason"]
            finally:
                conn.close()


class TestNoSilentErrorRateAtFieldCandidateLayer:
    """Confirms this module makes NO attempt to weaken or route around
    ingest.fields.FieldCandidate.__post_init__ -- the invariant that makes
    eval.metrics.py's OLD silent_error_rate a tautology is untouched, and
    stays untouched, by this module."""

    def test_field_candidate_still_refuses_needs_confirmation_false(self):
        from ingest.fields import FieldCandidate

        with pytest.raises(ValueError, match="needs_confirmation must always be True"):
            FieldCandidate(
                field_key="x", value_raw="1", value_norm=1.0, unit=None, document_id=None,
                page_no=1, bbox=(0, 0, 1, 1), method="regex", confidence=0.5, rationale="test",
                needs_confirmation=False,
            )
