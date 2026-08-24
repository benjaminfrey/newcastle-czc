"""Tests for eval/metrics.py's structural recall + coverage (D-0030) and
eval/run_eval.py's n-policy + closing statement (D4/D5).

THE ACCEPTANCE TEST FOR THIS FILE, PER THE W8 ROUND-2 BRIEF: not "does it
report good numbers" but "can I make each metric report a BAD number by
feeding it bad input". Every test below either (a) feeds a dropped
criterion and asserts the reported number gets worse, or (b) proves in
isolation why the metric it replaced (precision) could NOT do that.

Offline throughout. The `_score_pair` tests use fabricated `run` dicts and
never touch a DB or a PDF. The `structural_recall_and_coverage` end-to-end
test needs the real fixture PDFs (it reads a real decision's ground truth
via eval.ground_truth) and a real subdivision walk against a real
migrated DB; both are already exercised elsewhere in this suite
(tests/test_ground_truth.py, tests/test_subdivision_review.py) so nothing
new is asked of the environment.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from eval import metrics  # noqa: E402
from eval import pairs as eval_pairs  # noqa: E402
from eval import run_eval  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers -- a fabricated `run` dict shaped exactly like
# eval.metrics._run_subdivision_walk()'s real return value, but built by
# hand so these tests need no DB, no engine walk, and no PDF.
# --------------------------------------------------------------------------- #


def _fake_run(letters: str, *, rendered: str | None = None) -> dict:
    """A `run` dict shaped like _run_subdivision_walk()'s real output
    ({"rules": [...], "nodes": [...]}). `letters` is the criteria set's own
    universe (what the engine SEEDED -- always the full set in this app);
    `rendered` (defaults to `letters`) is what actually shows up as a
    findings node -- pass a shorter string to simulate a dropped criterion
    without also shrinking the universe, which is the real-world shape of
    that failure (the criteria set stays the same size; the WALK drops a
    node from it)."""
    rules = [{"standard_letter": ch} for ch in letters]
    nodes = [{"number_label": f"{ch}."} for ch in (rendered if rendered is not None else letters)]
    return {"rules": rules, "nodes": nodes}


FULL_21 = "abcdefghijklmnopqrstu"


# --------------------------------------------------------------------------- #
# D2, part 1 -- precision is blind to omission (documentation/regression
# proof; precision itself was REMOVED from production code -- this
# reimplements the discredited formula inline, on purpose, so the proof
# survives even though nothing in eval/metrics.py computes it any more).
# --------------------------------------------------------------------------- #


class TestPrecisionWasCorrectlyRemoved:
    def test_precision_is_blind_to_omission(self):
        """The exact scenario the round-2 brief names: ground truth is the
        full 21, the app renders all 21 (precision=1.0). Now simulate the
        worst failure this app can make -- criterion k is silently dropped
        from what renders. Under the old formula, precision stays 1.000
        even though a real criterion vanished -- proving precision cannot
        detect the one failure mode this eval exists to catch. Recall,
        computed the same way, DOES catch it (see the next test) -- that
        contrast is the entire D-0030 argument.
        """
        truth = set(FULL_21)
        predicted_before = set(FULL_21)

        def precision(predicted: set[str], truth: set[str]) -> float:
            intersection = predicted & truth
            return len(intersection) / len(predicted) if predicted else 0.0

        precision_before = precision(predicted_before, truth)
        assert precision_before == 1.0

        # Drop standard "k" from what the app rendered -- the worst failure
        # this app can make (CLAUDE.md: dropping a criterion).
        predicted_after = predicted_before - {"k"}
        precision_after = precision(predicted_after, truth)

        assert precision_after == 1.0, (
            "precision must stay unchanged when a criterion silently vanishes from the "
            "render -- that is exactly why it was removed as this app's structural metric"
        )
        assert precision_before == precision_after

    def test_precision_can_be_gamed_by_omitting_a_standard_predicted_by_truth_too(self):
        """A second, sharper version of the same point: if the real
        decision's own prose also happens not to cite standard k (truth
        loses it too), precision can even go UP by omitting -- rewarding
        exactly the failure this app must never make."""

        def precision(predicted: set[str], truth: set[str]) -> float:
            intersection = predicted & truth
            return len(intersection) / len(predicted) if predicted else 0.0

        truth = set(FULL_21) - {"k"}  # the real decision's prose never cited k either
        predicted_full = set(FULL_21)  # correct, complete-walk behaviour
        predicted_dropped = set(FULL_21) - {"k"}  # a real regression: k silently dropped

        precision_full = precision(predicted_full, truth)
        precision_dropped = precision(predicted_dropped, truth)

        assert precision_dropped > precision_full, (
            "precision rewards dropping a criterion here (1.000 vs the correct behaviour's "
            "20/21 = 0.952) -- backwards for a complete-walk design, per D-0030"
        )


# --------------------------------------------------------------------------- #
# D2, part 2 -- recall DOES degrade when a criterion is dropped, and
# coverage independently catches the same failure without needing any
# ground truth at all.
# --------------------------------------------------------------------------- #


class TestScorePairDegradesOnOmission:
    def test_recall_and_coverage_are_perfect_on_a_clean_walk(self):
        run = _fake_run(FULL_21)
        result = metrics._score_pair("clean", run, truth=set(FULL_21))
        assert result.recall == 1.0
        assert result.coverage_ok is True
        assert result.coverage_missing == ()

    def test_recall_degrades_when_a_criterion_is_dropped_from_predicted(self):
        """THE feed-bad-input test D2 requires: drop standard 'k' from what
        the engine rendered (predicted), keep the full 21 in ground truth,
        and assert recall actually MOVES."""
        run_before = _fake_run(FULL_21)
        run_after = _fake_run(FULL_21, rendered=FULL_21.replace("k", ""))  # k silently dropped from the render
        truth = set(FULL_21)

        result_before = metrics._score_pair("before", run_before, truth)
        result_after = metrics._score_pair("after", run_after, truth)

        assert result_before.recall == 1.0
        assert result_after.recall is not None
        assert result_after.recall < result_before.recall
        assert result_after.recall == pytest.approx(20 / 21)

    def test_coverage_fails_independently_of_ground_truth_when_a_criterion_is_dropped(self):
        """Coverage needs NO ground truth at all (D-0030's whole point) --
        prove it catches the identical dropped-criterion failure even when
        truth is empty (the "not computable" case)."""
        run_after = _fake_run(FULL_21, rendered=FULL_21.replace("k", ""))
        result = metrics._score_pair("no-truth", run_after, truth=set())

        assert result.recall is None  # not computable -- no ground truth, never silently 0/1
        assert result.coverage_ok is False
        assert result.coverage_missing == ("k",)

    def test_coverage_passes_when_predicted_equals_universe_even_with_no_truth(self):
        """The non-failing control for the test above -- coverage must not
        report FAIL just because truth happens to be empty."""
        run = _fake_run(FULL_21)
        result = metrics._score_pair("no-truth-clean", run, truth=set())
        assert result.recall is None
        assert result.coverage_ok is True

    def test_recall_not_computable_never_silently_reported_as_zero_or_one(self):
        run = _fake_run(FULL_21)
        result = metrics._score_pair("empty-truth", run, truth=set())
        assert result.recall is None
        assert result.reason is not None


# --------------------------------------------------------------------------- #
# D2, end-to-end -- the real pipeline (structural_recall_and_coverage(),
# not just _score_pair()) also degrades on a dropped node, proving the
# wiring between the walk and the scorer is correct, not just the scorer
# in isolation.
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(
    not eval_pairs.fixtures_available(),
    reason="real Findings-of-Fact fixture PDFs not present under docs/ in this checkout",
)
class TestStructuralRecallAndCoverageEndToEnd:
    def test_dropping_a_node_from_the_real_walk_degrades_recall_and_fails_coverage(self, monkeypatch):
        real_run = metrics._run_subdivision_walk

        def dropped_walk(conn, *, case_label):
            run = real_run(conn, case_label=case_label)
            # Simulate the worst failure this app can make: one rendered
            # node vanishes. Only touch shattuck (recall IS computable for
            # it -- Academy Hill's ground truth is empty by design, see
            # eval/ground_truth.py, so it would not show the effect).
            if case_label == "shattuck":
                run["nodes"] = [n for n in run["nodes"] if n["number_label"] != "a."]
            return run

        monkeypatch.setattr(metrics, "_run_subdivision_walk", dropped_walk)

        shattuck = eval_pairs.get_pair("shattuck")
        results = metrics.structural_recall_and_coverage(pairs=(shattuck,))
        assert len(results) == 1
        r = results[0]

        assert r.applicable is True
        assert r.recall is not None
        assert r.recall < 1.0, "recall must move when a real node is dropped from the real walk"
        assert r.coverage_ok is False
        assert "a" in r.coverage_missing


# --------------------------------------------------------------------------- #
# D4 -- the minimum-n policy for the RATE aggregate (recall), and the
# un-gated coverage tally.
# --------------------------------------------------------------------------- #


def _fake_result(pair_name: str, *, recall: float | None, ground_truth: str = FULL_21,
                  predicted: str = FULL_21, coverage_ok: bool | None = True) -> metrics.StructuralResult:
    return metrics.StructuralResult(
        pair_name=pair_name, applicable=True,
        universe_letters=tuple(FULL_21),
        ground_truth_letters=tuple(ground_truth) if recall is not None else (),
        predicted_letters=tuple(predicted),
        recall=recall,
        coverage_ok=coverage_ok,
    )


class TestAggregateNPolicy:
    def test_refuses_aggregate_below_minimum_n(self):
        results = [_fake_result("a", recall=1.0), _fake_result("b", recall=1.0)]
        assert len(results) < metrics.MIN_AGGREGATE_N
        agg = metrics.aggregate_structural(results)
        assert agg["recall"] is None
        assert agg["insufficient_n_reason"] is not None
        assert "insufficient pairs" in agg["insufficient_n_reason"]
        assert f"n={len(results)}" in agg["insufficient_n_reason"]

    def test_reports_aggregate_once_minimum_n_is_met(self):
        results = [_fake_result(name, recall=1.0) for name in ("a", "b", "c")]
        assert len(results) == metrics.MIN_AGGREGATE_N
        agg = metrics.aggregate_structural(results)
        assert agg["recall"] == 1.0
        assert agg["insufficient_n_reason"] is None
        assert agg["n_pairs_recall_computable"] == 3

    def test_n_is_always_reported_even_when_insufficient(self):
        """D4: 'print n next to every number' -- assert the actual count is
        present in the aggregate dict regardless of whether a number is
        withheld."""
        results = [_fake_result("a", recall=1.0)]
        agg = metrics.aggregate_structural(results)
        assert agg["n_pairs_recall_computable"] == 1

    def test_coverage_tally_is_never_gated_by_the_minimum(self):
        """Coverage is an audit, not a rate estimate -- it must report even
        at n=1, unlike recall."""
        results = [_fake_result("a", recall=None, coverage_ok=True)]
        agg = metrics.aggregate_structural(results)
        assert agg["n_pairs_coverage_computed"] == 1
        assert agg["coverage_pairs_ok"] == 1
        assert agg["coverage_all_ok"] is True
        # recall is still withheld at n=1 -- the two aggregates are independent.
        assert agg["recall"] is None

    def test_coverage_all_ok_is_false_not_true_when_nothing_was_computed(self):
        """An empty result set must not silently report a passing audit."""
        agg = metrics.aggregate_structural([])
        assert agg["n_pairs_coverage_computed"] == 0
        assert agg["coverage_all_ok"] is False

    def test_a_single_coverage_failure_is_visible_in_the_aggregate(self):
        results = [
            _fake_result("a", recall=None, coverage_ok=True),
            _fake_result("b", recall=None, coverage_ok=False),
        ]
        agg = metrics.aggregate_structural(results)
        assert agg["coverage_pairs_ok"] == 1
        assert agg["n_pairs_coverage_computed"] == 2
        assert agg["coverage_all_ok"] is False


# --------------------------------------------------------------------------- #
# D5 -- the closing statement never lets a narrow check stand in for a
# whole-app claim, and the banned phrase is gone from the real output.
# --------------------------------------------------------------------------- #


def _base_structural_agg(*, recall=None, n_recall=1, n_cov=2, coverage_all_ok=True):
    return {
        "n_pairs_applicable": 2,
        "n_pairs_recall_computable": n_recall,
        "recall": recall,
        "insufficient_n_reason": None if recall is not None else f"insufficient pairs (n={n_recall})",
        "n_pairs_coverage_computed": n_cov,
        "coverage_pairs_ok": n_cov if coverage_all_ok else n_cov - 1,
        "coverage_all_ok": coverage_all_ok,
    }


def _fake_fidelity_result(pair_name: str, measured: bool = True, total_candidates: int = 5):
    from eval.metrics import FidelityResult

    return FidelityResult(pair_name=pair_name, measured=measured, total_candidates=total_candidates)


def _fake_silent_error_results():
    from eval.silent_error import SilentErrorResult

    return [
        SilentErrorResult(scenario="dirty_unverified_wrong_facts", description="", exposures=()),
        SilentErrorResult(scenario="verified_human_confirmed_facts", description="", exposures=()),
        SilentErrorResult(scenario="no_facts_asserted", description="", exposures=()),
    ]


class TestClosingStatement:
    def test_banned_reassurance_phrase_is_gone_from_the_source(self):
        """Regression guard: the exact quotable sentence the round-2 brief
        forbids must not appear anywhere run_eval.py could print it."""
        source = Path(run_eval.__file__).read_text(encoding="utf-8")
        printable_lines = [
            line for line in source.splitlines()
            if ("print(" in line or "lines.append(" in line) and not line.strip().startswith("#")
        ]
        for line in printable_lines:
            assert "no stop-ship condition detected" not in line, line

    def test_stop_ship_true_never_prints_a_reassurance(self):
        text = run_eval._closing_statement(
            stop_ship=True, structural_agg=_base_structural_agg(), oc_total_nodes=42, oc_total_viol=1,
            oc_n_pairs=2, render_text_fields=115, fidelity_results=[_fake_fidelity_result("morrissey")],
            silent_error_results=_fake_silent_error_results(),
            dalton_structural_pass=True, dalton_no_confident_pass=True,
        )
        assert "STOP-SHIP" in text
        assert "no violation" not in text.lower()
        assert "no stop-ship condition detected" not in text

    def test_stop_ship_false_names_what_was_not_measured(self):
        """The core D5 requirement: a clean run's closing statement must
        explicitly name real, current gaps -- not just declare victory."""
        text = run_eval._closing_statement(
            stop_ship=False, structural_agg=_base_structural_agg(), oc_total_nodes=42, oc_total_viol=0,
            oc_n_pairs=2, render_text_fields=115, fidelity_results=[_fake_fidelity_result("morrissey")],
            silent_error_results=_fake_silent_error_results(),
            dalton_structural_pass=True, dalton_no_confident_pass=True,
        )
        assert "no stop-ship condition detected" not in text
        assert "NOT MEASURED" in text
        assert "NOT a certification that the app is safe" in text
        # Specific, real, currently-open gaps must be named, not just alluded to:
        assert "D-0029" in text  # facts not wired into run_walk() for any real case
        assert "prose usefulness" in text.lower()
        assert "Dalton" in text

    def test_closing_statement_n_appears_next_to_the_recall_claim(self):
        """D4 applied to the prose report too: whenever recall IS reported,
        its n travels with it."""
        text = run_eval._closing_statement(
            stop_ship=False, structural_agg=_base_structural_agg(recall=0.9, n_recall=3),
            oc_total_nodes=42, oc_total_viol=0, oc_n_pairs=2, render_text_fields=115,
            fidelity_results=[_fake_fidelity_result("morrissey")],
            silent_error_results=_fake_silent_error_results(),
            dalton_structural_pass=True, dalton_no_confident_pass=True,
        )
        assert "n=3 pair(s)" in text
        assert "0.900" in text

    def test_closing_statement_names_insufficient_n_reason_when_recall_withheld(self):
        text = run_eval._closing_statement(
            stop_ship=False, structural_agg=_base_structural_agg(recall=None, n_recall=1),
            oc_total_nodes=42, oc_total_viol=0, oc_n_pairs=2, render_text_fields=115,
            fidelity_results=[_fake_fidelity_result("morrissey")],
            silent_error_results=_fake_silent_error_results(),
            dalton_structural_pass=True, dalton_no_confident_pass=True,
        )
        assert "insufficient pairs (n=1)" in text
