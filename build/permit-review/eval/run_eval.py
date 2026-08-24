#!/usr/bin/env python3
"""eval/run_eval.py -- the W8 eval harness entry point.

    python3 eval/run_eval.py                       # run everything measurable offline, print the report
    python3 eval/run_eval.py --quiet                # print only the final summary lines
    python3 eval/run_eval.py --out PATH             # also write the full report as JSON
    python3 eval/run_eval.py --demonstrate-holdout-read
                                                     # prove, live, that THIS module (unlike
                                                     # build_fewshot.py) can read Dalton/Stantec

Also reachable as `python3 run.py --eval` (run.py dispatches straight into
run(), same as its --verify-citations / --verify-structure flags).

Offline, always: no network call, no ANTHROPIC_API_KEY read, no LLM client
constructed anywhere in this module. Every metric that needs a model is
reported as "not measured (no API key)" rather than skipped silently,
computed as a placeholder 0/1, or folded into anything else -- see the task
brief this module implements (CLAUDE.md-adjacent orchestrator brief, W8) and
BUILD-STATE.md's W8 resume note.

--------------------------------------------------------------------------
WHY FOUR METRICS AND NEVER ONE NUMBER
--------------------------------------------------------------------------
Structural recall + coverage (precision was removed -- see eval/metrics.py's
module docstring section 1 and DECISIONS-NEEDED.md D-0030), fact fidelity +
silent_error_rate, over-conclusion rate, and prose usefulness measure four
different, mostly unrelated failure modes:
  - dropping a criterion the real record addressed, or that the criteria
    set itself defines (structural: recall against ground truth, coverage
    against the criteria set's own universe)
  - a WRONG value that reaches the reader UNFLAGGED (silent_error_rate --
    target 0, any nonzero on a REAL case is stop-ship; distinct from fact
    fidelity, which also counts wrong-but-flagged values. Measured at the
    findings-node/render layer -- eval/silent_error.py -- not at
    field_candidates, which cannot fail by construction; see that module's
    docstring for the full argument. Currently a PROVEN MECHANISM run on
    controlled scenarios, not yet a measurement of any real case's facts --
    see METRIC 3c below and D-0029)
  - the engine drawing a verdict it has no authority to draw (over-
    conclusion -- 0 by construction; nonzero means a guard broke)
  - whether the drafted prose is actually useful to a human reader (never
    tunable against; human-labelled only)
Averaging these into one score would let a great score on one hide a
stop-ship failure on another -- exactly the "eval that can be gamed" this
harness exists to not be. Every report below prints each metric under its
own name and never combines them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from eval import dalton_case, metrics, pairs as pairs_mod, run_w8_partial, silent_error  # noqa: E402

NOT_MEASURED = "not measured (no API key)"

# The 3 pairs whose application PDF has native (Tier A/B) text on at least
# one page, per this build's own findings (BUILD-STATE.md / tests/test_triage.py
# / tests/test_formgen.py): Morrissey (4pp, all Tier A), Profenno (Tier A
# page 5), Stantec (56pp mixed, pp.9-12 native -- a HOLDOUT, included
# deliberately; see the module docstring and eval/pairs.py's own docstring
# for why the harness may read it here). This list is a hint for what to
# ATTEMPT; eval.metrics.fact_fidelity_and_silent_error() re-checks tier
# membership live via ingest.triage rather than trusting this comment, and
# reports "not measured" itself for any name that turns out scan-only.
NATIVE_TEXT_CANDIDATE_NAMES: tuple[str, ...] = ("morrissey", "profenno", "stantec")


def _pair_set_summary() -> dict[str, Any]:
    all_pairs = pairs_mod.load_pairs()
    excluded = pairs_mod.load_excluded_decision_only()
    return {
        "total_pairs": len(all_pairs),
        "matched": [p.name for p in pairs_mod.MATCHED_PAIRS],
        "holdout": sorted(pairs_mod.HOLDOUT_NAMES),
        "excluded_decision_only": [e.name for e in excluded],
        "fixtures_available": pairs_mod.fixtures_available(),
    }


def _print_pair_set(summary: dict[str, Any]) -> None:
    print("=" * 78)
    print("PAIR SET")
    print("=" * 78)
    print(f"  matched (application+decision): {len(summary['matched'])} -- {', '.join(summary['matched'])}")
    print(f"  holdout (application only)    : {len(summary['holdout'])} -- {', '.join(summary['holdout'])}")
    print(f"  excluded (decision only, not a pair): {len(summary['excluded_decision_only'])} -- "
          f"{', '.join(summary['excluded_decision_only'])}")
    print(f"  all fixture files present on disk: {summary['fixtures_available']}")
    print()


def _print_structural(results, aggregate: dict[str, Any]) -> None:
    print("=" * 78)
    print("METRIC 1 / 4 -- STRUCTURAL RECALL + COVERAGE  (target: recall >= 0.95; coverage 100% always)")
    print("=" * 78)
    print("  Deterministic. Scoped to the one criteria set the engine has built so far: Subdivision.")
    print("  PRECISION WAS REMOVED (D-0030, see DECISIONS-NEEDED.md): this app is a complete-walk")
    print("  design (every standard renders on every case), so precision = hit/predicted can only")
    print("  fall when the app renders MORE than the real decision's prose happened to cite -- it")
    print("  cannot detect the failure that matters (a dropped criterion), and dropping one would")
    print("  leave it unchanged. See eval/metrics.py's module docstring, section 1, for the proof.")
    for r in results:
        if not r.applicable:
            print(f"  {r.pair_name:<16} not applicable -- {r.reason}")
            continue
        n_universe = len(r.universe_letters) or "?"
        cov_status = "PASS" if r.coverage_ok else "FAIL"
        cov_line = (
            f"coverage={cov_status} ({len(r.predicted_letters)}/{n_universe} standards rendered)"
            + ("" if r.coverage_ok else f"  MISSING={list(r.coverage_missing)}")
        )
        if r.recall is None:
            print(f"  {r.pair_name:<16} recall not computable (n_truth=0) -- {r.reason}")
            print(f"  {'':<16} {cov_line}")
            continue
        print(f"  {r.pair_name:<16} recall={r.recall:.3f}  (n_truth={len(r.ground_truth_letters)}/{n_universe} "
              f"standards the real decision cited)")
        print(f"  {'':<16} {cov_line}")
    print()
    n_recall = aggregate["n_pairs_recall_computable"]
    if aggregate["recall"] is not None:
        print(f"  AGGREGATE RECALL (micro-averaged, n={n_recall} pair(s) with computable ground truth): "
              f"recall={aggregate['recall']:.3f}")
    else:
        print(f"  AGGREGATE RECALL: {aggregate['insufficient_n_reason']}")
    n_cov = aggregate["n_pairs_coverage_computed"]
    if n_cov:
        cov_agg_status = "" if aggregate["coverage_all_ok"] else "  !! COVERAGE FAILURE -- see per-pair MISSING above !!"
        print(f"  AGGREGATE COVERAGE (n={n_cov} pair(s); a completeness audit, NOT a rate -- "
              f"never gated by a minimum n, see MIN_AGGREGATE_N in eval/metrics.py): "
              f"{aggregate['coverage_pairs_ok']}/{n_cov} pairs rendered every standard{cov_agg_status}")
    else:
        print("  AGGREGATE COVERAGE: no pair yielded a coverage value")
    print("  NOTE: ground truth is read directly from each decision's own PDF text (D-0031,")
    print("        eval/ground_truth.py) -- independent of rulesets/adopted/articles.json, so it")
    print("        no longer agrees with itself by construction. It still has its own stated")
    print("        failure modes (a regex-based house-style reader, n<=2 real decisions to check")
    print("        it against) -- see eval/ground_truth.py's module docstring and the closing")
    print("        summary below before treating a low recall as either app defect or ground-")
    print("        truth artifact without checking which.")
    print()


def _print_over_conclusion(results) -> None:
    print("=" * 78)
    print("METRIC 2 / 4 -- OVER-CONCLUSION RATE  (target: 0, BY CONSTRUCTION)")
    print("=" * 78)
    print("  Deterministic. Runs the real subdivision walk and checks actual output, not the claim.")
    total_nodes = sum(r.nodes_checked for r in results)
    total_violations = sum(len(r.violations) for r in results)
    for r in results:
        status = "OK" if not r.violations else "!! VIOLATIONS !!"
        print(f"  {r.pair_name:<16} nodes_checked={r.nodes_checked:<3} violations={len(r.violations):<3} {status}")
        for v in r.violations:
            print(f"      - {v}")
    rate = total_violations / total_nodes if total_nodes else 0.0
    print(f"  AGGREGATE: over_conclusion_rate = {rate:.4f}  ({total_violations}/{total_nodes} nodes, "
          f"n={len(results)} pair(s))")
    if total_violations:
        print("  STOP-SHIP: nonzero over-conclusion rate means a guard failed.")
    print()


def _print_fidelity(results) -> None:
    print("=" * 78)
    print("METRIC 3a / 5 -- FACT FIDELITY (grounding), native-text pairs")
    print("=" * 78)
    print("  Does every extracted field_candidate's value_raw actually appear on the page it claims?")
    print("  The 'ungrounded, needs_confirmation=False' column below is printed for completeness only --")
    print("  it is STRUCTURALLY 0 by ingest/fields.py:FieldCandidate.__post_init__ (an unflagged candidate")
    print("  cannot be constructed at all), so it is NOT this app's real silent_error_rate -- that number")
    print("  cannot move, so it cannot mean anything as a safety signal. See METRIC 3c for the real one.")
    for r in results:
        if not r.measured:
            print(f"  {r.pair_name:<16} {NOT_MEASURED} -- {r.reason}")
            continue
        if r.total_candidates == 0:
            print(f"  {r.pair_name:<16} 0 candidates extracted{' -- ' + r.reason if r.reason else ''}")
            continue
        holdout_note = " [HOLDOUT -- application text only, no decision compared]" \
            if r.pair_name in pairs_mod.HOLDOUT_NAMES else ""
        print(f"  {r.pair_name:<16} n={r.total_candidates:<4} "
              f"grounded_strict={r.grounded_strict_rate:.3f}  grounded_loose={r.grounded_loose_rate:.3f}  "
              f"ungrounded_and_unflagged=0/{r.total_candidates} (structurally cannot be nonzero){holdout_note}")
    print("  METRIC 3b / 5 -- PROSE USEFULNESS: " + NOT_MEASURED + " (human-labelled by design; needs")
    print("                    generated prose, which needs an LLM call. Deliberately never tuned on.)")
    print()


def _print_silent_error(results) -> None:
    print("=" * 78)
    print("METRIC 3c / 5 -- SILENT_ERROR_RATE, measured at the findings-node/render layer")
    print("                 (target: 0 on any REAL case; nonzero there is stop-ship)")
    print("=" * 78)
    print("  'Did a wrong value reach RENDERED OUTPUT without a flag?' -- checked against the REAL")
    print("  render.case_findings._finding_node_to_render_nodes() output for real findings_nodes rows a")
    print("  real engine.subdivision_review.run_walk() wrote. See eval/silent_error.py's module docstring")
    print("  for why field_candidates/field_values cannot be this surface, and why the applicability-FALSE")
    print("  -> NOT_APPLICABLE disposition (no #boardq/#unresolved box; a bare #finding paragraph) is.")
    print()
    print("  THREE CONTROLLED SCENARIOS (not real-case data -- proof that the metric MOVES, not a")
    print("  measurement of any actual application; see the NOTE below):")
    for r in results:
        n = r.fact_dependent_checked
        unflagged = r.unflagged_count
        rate = r.silent_error_rate
        rate_str = f"{rate:.4f}" if rate is not None else f"not computable (unflagged={unflagged} < " \
                                                            f"{silent_error.MIN_UNFLAGGED_FOR_RATE})"
        print(f"  {r.scenario:<32} fact_dependent_checked={n}  unflagged={unflagged}  "
              f"silent_count={r.silent_count}  silent_error_rate={rate_str}")
        for e in r.exposures:
            if not e.flagged:
                mark = "SILENT (unverified)" if e.silent else "unflagged but human-verified"
                print(f"      standard {e.standard_letter}. ({e.rule_key}): verdict={e.applicability_verdict} "
                      f"render_types={e.render_types} -- {mark}")
    print()
    print("  NOTE: this proves the mechanism -- inject a wrong, unverified fact for a fact-dependent")
    print("  applicability standard and the rate goes nonzero (dirty_unverified_wrong_facts); back the SAME")
    print("  fact with a real, human-attributed field_values row (app.extraction.override_field) and it")
    print("  returns to 0.0, not merely 'not computable' (verified_human_confirmed_facts); assert nothing")
    print("  and nothing renders unflagged at all (no_facts_asserted). It has NOT yet been run against any")
    print("  real case's facts, because no case's extracted field_keys are wired into run_walk() yet")
    print("  (DECISIONS-NEEDED.md D-0029) -- so real-case silent-error risk remains UNMEASURED, not zero.")
    print()


def _run_render_level_over_conclusion_and_dalton() -> tuple[dict[str, Any], str]:
    """Reuses eval/over_conclusion.py + eval/dalton_case.py (via eval/run_w8_partial.py's
    own orchestration of them) DIRECTLY rather than re-implementing -- a second,
    independently-built pass wrote these against this same W8 brief (both landed in this
    directory concurrently with this module; eval/__init__.py's docstring notes the
    reconciliation). They cover ground eval.metrics does not:

      - `eval.over_conclusion.scan_nodes()` checks REAL RENDERED node output (through
        render/case_findings.py, render/demo_findings.py, and app.meeting's real drafted
        motion text) across several sentence-template stress cases, one layer downstream
        of the raw findings_nodes rows eval.metrics.over_conclusion_rate() checks --
        complementary evidence for the same "0 by construction" claim, not a duplicate.
      - `eval.dalton_case` runs the actual Dalton holdout scenario the orchestrator's task
        brief centers on (BUILD-STATE.md's W8 line names Dalton by name) -- real triage,
        real Tier A/B extraction attempt, a real subdivision walk against Dalton's real
        case row, and an honest, explicit accounting of what CAN and CANNOT be measured
        offline for it (Dalton's application is a pure scan; see that module's own
        docstring). Nothing here is fabricated or asserted as a decided fact about
        Dalton's real content -- see eval/dalton_case.py's own extensive caveats.

    Reads Dalton's real PDF bytes directly (never through llm.fewshot) -- the same
    holdout-boundary distinction eval/pairs.py documents and
    tests/test_eval_holdout_boundary.py asserts.
    """
    import contextlib
    import io
    import tempfile

    buf = io.StringIO()
    with tempfile.TemporaryDirectory(prefix="eval-holdout-render-") as td:
        conn = dalton_case.build_db(Path(td))
        try:
            with contextlib.redirect_stdout(buf):
                oc_summary = run_w8_partial.section_over_conclusion(conn)
                dalton_summary = run_w8_partial.section_dalton(conn)
        finally:
            conn.close()

    header = (
        "=" * 78 + "\n"
        "METRIC 2 (continued) + HOLDOUT -- render-level over-conclusion scan + the real Dalton run\n"
        "(from eval/over_conclusion.py + eval/dalton_case.py -- see this function's own docstring)\n"
        + "=" * 78 + "\n"
    )
    return {"over_conclusion_render_level": oc_summary, "dalton_holdout": dalton_summary}, header + buf.getvalue()


# --------------------------------------------------------------------------- #
# D-0030 / D5 -- the closing statement.
#
# "RESULT: no stop-ship condition detected" is exactly the sentence a reader
# would lift out of this report and hand to a Board -- and every metric that
# feeds `stop_ship` can currently only prove a NEGATIVE over a narrow, named
# surface (silent_error_rate is 0 by construction over field_candidates, not
# over field_values/rendered prose; structural recall's ground truth is
# derived from the same articles.json the engine is built from; prose
# usefulness and most of Dalton are not measured at all). A bare "no
# stop-ship condition detected" would let a true statement about a narrow
# check stand in for a claim about the whole app, which nothing here
# licenses. Below, "no violation" is stated only about what was actually
# run, and every named gap is printed in the SAME output, not buried in a
# docstring a reader of the terminal output will never see.
# --------------------------------------------------------------------------- #


def _closing_statement(
    *, stop_ship: bool, structural_agg: dict[str, Any], oc_total_nodes: int, oc_total_viol: int,
    oc_n_pairs: int, render_text_fields: int, fidelity_results, silent_error_results,
    dalton_structural_pass: bool, dalton_no_confident_pass: bool,
) -> str:
    lines: list[str] = []
    if stop_ship:
        lines.append("RESULT: STOP-SHIP -- a real violation was detected by one of the checks above.")
        lines.append("        Do not treat any other metric in this report as compensating for it.")
        return "\n".join(lines)

    n_fidelity_measured = [r.pair_name for r in fidelity_results if r.measured and r.total_candidates]
    n_cov = structural_agg["n_pairs_coverage_computed"]
    n_recall = structural_agg["n_pairs_recall_computable"]

    lines.append(
        "RESULT: no violation was detected in what this run actually measured. This is NOT a "
        "certification that the app is safe on a real case -- it is an accounting of the checks "
        "below, and only those checks."
    )
    lines.append("")
    lines.append("MEASURED this run (offline, deterministic, no model call):")
    lines.append(
        f"  - over-conclusion, DB level: {oc_total_viol}/{oc_total_nodes} findings-tree nodes "
        f"(n={oc_n_pairs} pair(s)) carried banned-verdict language, a non-closed disposition, a "
        f"set conclusion, or an orphan conclusion."
    )
    lines.append(f"  - over-conclusion, render level: 0/{render_text_fields} rendered text fields flagged.")
    lines.append(
        f"  - grounding (field_candidate value_raw actually appears on its claimed page): measured "
        f"for {len(n_fidelity_measured)} native-text pair(s) ({', '.join(n_fidelity_measured) or 'none'}). "
        f"NOTE: this is grounding, not silent_error_rate -- see the silent-error line below for that."
    )
    se_by_scenario = {r.scenario: r for r in silent_error_results}
    se_summary = ", ".join(
        f"{name}={'not computable' if r.silent_error_rate is None else f'{r.silent_error_rate:.4f}'}"
        for name, r in se_by_scenario.items()
    )
    lines.append(
        f"  - silent_error_rate MECHANISM proof, findings-node/render layer (eval/silent_error.py, "
        f"3 controlled scenarios, not real-case data): {se_summary}. Proves the rate moves nonzero "
        f"on an unverified wrong fact and returns to 0.0 once a human confirms it via "
        f"app.extraction.override_field -- a real mechanism, not yet a measurement of any real "
        f"case (see below)."
    )
    lines.append(
        f"  - subdivision coverage (every standard in the criteria set rendered): "
        f"{structural_agg['coverage_pairs_ok']}/{n_cov} pair(s), never gated by sample size."
    )
    lines.append(
        f"  - subdivision recall against ground truth read directly from each decision's own PDF "
        f"text (D-0031, independent of rulesets/adopted/articles.json): "
        + (f"n={n_recall} pair(s), aggregate={structural_agg['recall']:.3f}" if structural_agg["recall"] is not None
           else structural_agg["insufficient_n_reason"])
    )
    lines.append(
        f"  - Dalton holdout: full-criterion coverage on an empty case={dalton_structural_pass}, "
        f"no confident (fact_recorded) assertions on Dalton's unread content={dalton_no_confident_pass}."
    )
    lines.append("")
    lines.append("NOT MEASURED here, and therefore NOT RULED OUT by this run:")
    lines.append(
        "  - a WRONG value reaching rendered output UNFLAGGED, on any REAL case's facts. The "
        "silent_error_rate printed above (over field_candidates) is 0 by construction "
        "(FieldCandidate.__post_init__ makes an unflagged candidate impossible to build at all), "
        "so it cannot be nonzero and proves nothing about safety on its own -- see eval/"
        "silent_error.py for where a silent error is genuinely possible (a NOT_APPLICABLE finding "
        "renders identically to an already-reviewed one, with no board_question/#unresolved box) "
        "and its proof that the mechanism itself works against controlled synthetic scenarios. That "
        "proof is not yet exercised against any real case's extracted facts (no case's field_keys "
        "reach run_walk()'s facts dict yet -- D-0029), so whether a real Newcastle case can trigger "
        "it is still not measured here."
    )
    lines.append(
        "  - whether the subdivision ground-truth EXTRACTION itself is correct beyond the 2 real "
        "decisions on file: eval/ground_truth.py reads each decision PDF directly (no longer "
        "derived from rulesets/adopted/articles.json -- D-0031 fixed that circularity), but it is "
        "a regex-based house-style reader with its own stated failure modes (a pure-scan or "
        "differently-templated decision, an out-of-order or skipped letter, a novel Roman-numeral "
        "collision) -- see eval/ground_truth.py's own docstring. A low recall could still mean the "
        "ground-truth reader missed a letter, not that the app dropped a criterion; the per-pair "
        "MISSING/coverage detail above is what distinguishes the two, not the recall number alone."
    )
    lines.append(
        "  - the 4 non-subdivision review types (expanded_use, small_project_plan, "
        "shoreland_zoning, use_permit, large_project_plan) -- no criteria set is built for them, so "
        "recall/coverage is not applicable and not measured for any pair under those types."
    )
    lines.append(
        "  - prose usefulness: " + NOT_MEASURED + " -- needs a real LLM call and is human-labelled "
        "by design; this run never generates or judges prose."
    )
    lines.append(
        "  - Dalton's real application content beyond triage: it is a pure scan (0/5 pages reach "
        "even the Tier-B floor), so whether it is actually incomplete or contradictory is not "
        "verifiable offline; that needs the vision path and an API key, neither available here."
    )
    lines.append(
        "  - whether any real case's extracted facts actually reach the subdivision engine: no "
        "case's field_keys are wired into run_walk()'s facts dict yet (see DECISIONS-NEEDED.md "
        "D-0029), so contradiction-detection has not been exercised end-to-end on real content."
    )
    return "\n".join(lines)


def run(*, out_path: Path | None, quiet: bool, demonstrate_holdout_read: bool) -> int:
    if demonstrate_holdout_read:
        print("Demonstrating the eval-harness side of the holdout boundary (reading Dalton/Stantec):")
        for name in sorted(pairs_mod.HOLDOUT_NAMES):
            pair = pairs_mod.get_pair(name)
            path = pairs_mod.application_pdf_path(pair)  # no HoldoutError here -- see eval/pairs.py
            import pymupdf
            doc = pymupdf.open(str(path))
            try:
                print(f"  {name}: read OK -- {doc.page_count} pages, "
                      f"{len(doc[0].get_text())} chars on page 1 (llm/fewshot.py refuses this same read)")
            finally:
                doc.close()
        print()

    summary = _pair_set_summary()
    if not summary["fixtures_available"]:
        print("!! one or more fixture PDFs under docs/Findings of Fact and Conclusions of Law/ "
              "is missing -- cannot run the harness. !!", file=sys.stderr)
        return 2

    structural_results = metrics.structural_recall_and_coverage()
    structural_agg = metrics.aggregate_structural(structural_results)
    over_conclusion_results = metrics.over_conclusion_rate()
    fidelity_results = metrics.fact_fidelity_and_silent_error(NATIVE_TEXT_CANDIDATE_NAMES)
    silent_error_results = silent_error.run_all_scenarios()
    holdout_and_render, holdout_and_render_text = _run_render_level_over_conclusion_and_dalton()

    render_oc_prose_hits = holdout_and_render["over_conclusion_render_level"]["total_prose_hits"]
    render_oc_text_fields = holdout_and_render["over_conclusion_render_level"]["total_text_fields_scanned"]
    dalton_assertions = holdout_and_render["dalton_holdout"]["assertions"]
    dalton_structural_pass = dalton_assertions["(a) full_criterion_coverage"]["pass"]
    dalton_no_confident_pass = dalton_assertions["(d) no_confident_assertions_on_dalton"]["pass"]

    # Coverage failing is a real, structural, detectable stop-ship condition
    # (a dropped criterion) -- but only when at least one pair's coverage was
    # actually computed; an empty set must not read as a failure (see
    # aggregate_structural()'s own docstring for why coverage_all_ok is
    # False-by-default on an empty set).
    coverage_failed = structural_agg["n_pairs_coverage_computed"] > 0 and not structural_agg["coverage_all_ok"]

    oc_total_nodes = sum(r.nodes_checked for r in over_conclusion_results)
    oc_total_viol = sum(len(r.violations) for r in over_conclusion_results)

    stop_ship = (
        any(len(r.violations) for r in over_conclusion_results)
        or any(r.measured and r.ungrounded_and_unflagged for r in fidelity_results)
        or render_oc_prose_hits > 0
        or not dalton_structural_pass
        or not dalton_no_confident_pass
        or coverage_failed
    )

    closing = _closing_statement(
        stop_ship=stop_ship, structural_agg=structural_agg, oc_total_nodes=oc_total_nodes,
        oc_total_viol=oc_total_viol, oc_n_pairs=len(over_conclusion_results),
        render_text_fields=render_oc_text_fields, fidelity_results=fidelity_results,
        silent_error_results=silent_error_results,
        dalton_structural_pass=dalton_structural_pass, dalton_no_confident_pass=dalton_no_confident_pass,
    )

    if quiet:
        if structural_agg["recall"] is not None:
            structural_line = (f"structural_recall(n={structural_agg['n_pairs_recall_computable']})="
                                f"{structural_agg['recall']:.3f}")
        else:
            structural_line = f"structural_recall: {structural_agg['insufficient_n_reason']}"
        n_cov = structural_agg["n_pairs_coverage_computed"]
        coverage_line = f"coverage(n={n_cov})={structural_agg['coverage_pairs_ok']}/{n_cov}" if n_cov else "coverage(n=0)=n/a"
        oc_rate = (oc_total_viol / oc_total_nodes) if oc_total_nodes else 0.0
        n_fidelity_measured = sum(1 for r in fidelity_results if r.measured)
        se_dirty = next(r for r in silent_error_results if r.scenario == "dirty_unverified_wrong_facts")
        se_verified = next(r for r in silent_error_results if r.scenario == "verified_human_confirmed_facts")
        se_line = (
            f"silent_error_rate(mechanism proof, not real-case data): "
            f"dirty={se_dirty.silent_error_rate:.4f} verified={se_verified.silent_error_rate:.4f}"
        )
        print(
            f"EVAL: {structural_line} | {coverage_line} | "
            f"over_conclusion_rate={oc_rate:.4f} (db-level, n={len(over_conclusion_results)} pairs) / "
            f"{render_oc_prose_hits}/{render_oc_text_fields} (render-level) | "
            f"fidelity: {n_fidelity_measured}/{len(fidelity_results)} measured | "
            f"{se_line} | "
            f"dalton_holdout: full_coverage={dalton_structural_pass} no_confident_assertions={dalton_no_confident_pass} | "
            f"prose_usefulness={NOT_MEASURED} | "
            f"{'STOP-SHIP' if stop_ship else 'no violation in what was measured -- see full report for what was not measured'}"
        )
    else:
        _print_pair_set(summary)
        _print_structural(structural_results, structural_agg)
        _print_over_conclusion(over_conclusion_results)
        _print_fidelity(fidelity_results)
        _print_silent_error(silent_error_results)
        print(holdout_and_render_text)
        print("=" * 78)
        print(closing)
        print("=" * 78)

    if out_path is not None:
        payload = {
            "pair_set": summary,
            "structural_recall_and_coverage": {
                "per_pair": [r.__dict__ for r in structural_results],
                "aggregate": structural_agg,
            },
            "over_conclusion_rate": {
                "per_pair": [
                    {"pair_name": r.pair_name, "nodes_checked": r.nodes_checked,
                     "violations": r.violations, "rate": r.rate}
                    for r in over_conclusion_results
                ],
            },
            "fact_fidelity_and_silent_error_rate": {
                "per_pair": [r.__dict__ for r in fidelity_results],
            },
            "silent_error_rate_findings_node_layer": {
                "note": "3 controlled scenarios proving the mechanism moves on injected bad input; NOT "
                        "yet a measurement of any real case's facts -- see eval/silent_error.py and D-0029.",
                "scenarios": [
                    {
                        "scenario": r.scenario, "description": r.description,
                        "fact_dependent_checked": r.fact_dependent_checked, "unflagged_count": r.unflagged_count,
                        "silent_count": r.silent_count, "silent_error_rate": r.silent_error_rate,
                        "exposures": [
                            {
                                "rule_key": e.rule_key, "standard_letter": e.standard_letter, "title": e.title,
                                "fact_keys": sorted(e.fact_keys), "applicability_verdict": e.applicability_verdict,
                                "render_types": list(e.render_types), "flagged": e.flagged,
                                "verified": e.verified, "silent": e.silent,
                            }
                            for e in r.exposures
                        ],
                    }
                    for r in silent_error_results
                ],
            },
            "over_conclusion_render_level_and_dalton_holdout": holdout_and_render,
            "prose_usefulness": NOT_MEASURED,
            "stop_ship": stop_ship,
            "closing_statement": closing,
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_name(out_path.name + f".tmp-{os.getpid()}")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(tmp, out_path)
        if not quiet:
            print(f"\nFull report written to {out_path}")

    return 1 if stop_ship else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="W8 eval harness -- structural recall + coverage, "
                                                   "over-conclusion rate, fact fidelity + silent_error_rate; "
                                                   "prose usefulness always reported as not-measured here")
    parser.add_argument("--out", type=Path, default=None, help="also write the full report as JSON")
    parser.add_argument("--quiet", action="store_true", help="print only the final summary line(s)")
    parser.add_argument(
        "--demonstrate-holdout-read", action="store_true", dest="demonstrate_holdout_read",
        help="prove live that this harness (unlike build_fewshot.py) can read Dalton/Stantec",
    )
    args = parser.parse_args(argv)
    return run(out_path=args.out, quiet=args.quiet, demonstrate_holdout_read=args.demonstrate_holdout_read)


if __name__ == "__main__":
    raise SystemExit(main())
