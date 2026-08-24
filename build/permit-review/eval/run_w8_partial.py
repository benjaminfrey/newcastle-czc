"""eval/run_w8_partial.py -- runnable driver for the two things this pass
was scoped to measure: the over-conclusion scan, and the Dalton held-out
case. NOT the full W8 harness (structural recall/precision, fact fidelity
on the native-text applications, and the Stantec side of the holdout are
still open -- see BUILD-STATE.md).

Every number this prints comes from an actual function call against real
code, executed when this script runs -- not a cached/assumed value. Run:

    cd build/permit-review && .venv/bin/python3 eval/run_w8_partial.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from eval import dalton_case, over_conclusion  # noqa: E402
from render import case_findings, demo_findings  # noqa: E402
from render.findings_to_md import render_nodes  # noqa: E402
from engine import subdivision_review, criteria_seed, review  # noqa: E402
from app import cases, security  # noqa: E402


def _hr(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def section_over_conclusion(conn) -> dict:
    """Scans REAL rendered output from several real, distinct code paths:
    (1) the empty-facts subdivision walk (already engine-proven in
    tests/test_subdivision_review.py, re-run here so THIS script's report
    is self-contained), rendered through the real render/case_findings.py
    pipeline, including the real motion-block path; (2) the same walk
    seeded with a numeric criterion that FAILS its comparison (proposed >
    required) plus a fired exception escape hatch and the mandatory flood
    condition, to stress-test the sentence templates most likely to leak a
    verdict word; (3) render/demo_findings.py's own real sample node list,
    the same one already used to prove the render pipeline works end to
    end; (4) real drafted motion text via app.meeting.draft_text_for_node,
    scanned on its own so the module docstring's "expected, motion-bucket"
    claim is checked against actual output, not asserted."""
    reports = []

    # (1) empty-facts subdivision case, rendered via the REAL findings
    # pipeline (render_case_findings.build_case_findings_nodes), which also
    # exercises the real (empty, per no meeting yet) motion-block path.
    seeded = criteria_seed.sync_subdivision_criteria(
        conn, ruleset_id=dalton_case.ADOPTED_ID, actor_user_id=dalton_case.ACTOR,
    )
    empty_case = cases.create_case(
        conn, application_type="subdivision", map_lot="EVAL-OC-EMPTY",
        applicant_name="(over-conclusion scan fixture)", is_scratch=True,
        actor_user_id=dalton_case.ACTOR,
    )
    rules = subdivision_review.load_rules_for_criteria_set(conn, seeded["criteria_set_id"])
    subdivision_review.run_walk(
        conn, case_id=empty_case["id"], criteria_set_id=seeded["criteria_set_id"],
        rules=rules, facts={}, default_ruleset_key="adopted", actor_user_id=dalton_case.ACTOR,
        parent_citation={"article": 7, "section": "12", "subsection": "f.1"},
    )
    nodes, _unresolved = case_findings.build_case_findings_nodes(conn, empty_case["id"])
    r1 = over_conclusion.scan_nodes(nodes, label="real findings render, empty-facts subdivision walk")
    over_conclusion.print_report(r1)
    reports.append(r1)

    # (2) a walk stress-testing the numeric/exception/condition sentence
    # templates directly (engine.review, not just the DB round-trip) --
    # a numeric criterion that FAILS (180 < 250, the real Buehner shape),
    # rendered through findings_to_md.render_nodes() as real markdown.
    numeric_fail = review.evaluate_numeric_criterion(
        label="Structure setback", rule_category="setback", proposed=180, required=250,
        unit="ft", comparator=">=", citation="Shoreland Zoning III.B",
    )
    exception_fired = review.evaluate_numeric_criterion(
        label="Structure setback", rule_category="setback", proposed=180, required=250,
        unit="ft", comparator=">=", citation="Shoreland Zoning III.B",
        context=review.ReviewContext(
            review_path="special_exception", excepted_categories=frozenset({"setback"}),
            exception_citation="Shoreland Zoning I.M",
        ),
    )
    condition = review.evaluate_flood_condition_criterion()
    judgement = review.evaluate_judgement_criterion(
        rule_category="pollution", subject="the proposed subdivision",
        code_text="will not result in undue water or air pollution",
    )
    stress_nodes = [
        {"type": "para", "text": t}
        for t in (
            numeric_fail.body, exception_fired.body, condition.body, judgement.board_question,
        )
        if t
    ]
    r2 = over_conclusion.scan_nodes(stress_nodes, label="engine.review sentence templates (numeric fail / exception / condition / judgement)")
    over_conclusion.print_report(r2)
    reports.append(r2)

    # (3) the existing demo render, real node list already used to prove
    # the render pipeline end to end.
    demo_nodes = demo_findings.build_demo_nodes()
    r3 = over_conclusion.scan_nodes(demo_nodes, label="render/demo_findings.py sample document")
    over_conclusion.print_report(r3)
    reports.append(r3)

    # (4) drafted motion text on its own, via the real app.meeting path,
    # to check the module docstring's claim about where "consistent with"
    # actually lives in this app's real output.
    from app import meeting as meeting_mod
    motion_texts = []
    for row in conn.execute(
        "SELECT * FROM findings_nodes WHERE case_id = ? AND node_type = 'finding' ORDER BY sort_order;",
        (empty_case["id"],),
    ).fetchall():
        node = dict(row)
        text, proposed = meeting_mod.draft_text_for_node(node)
        motion_texts.append({"type": "motionblock", "motion": text, "result": None})
    r4 = over_conclusion.scan_nodes(motion_texts, label="app.meeting.draft_text_for_node output (real motion drafts, unvoted)")
    over_conclusion.print_report(r4)
    reports.append(r4)

    total_prose_hits = sum(len(r.prose_hits) for r in reports)
    total_fields = sum(r.total_text_fields_scanned for r in reports)
    return {
        "sections": [r.label for r in reports],
        "total_prose_hits": total_prose_hits,
        "total_text_fields_scanned": total_fields,
        "over_conclusion_rate_overall": (total_prose_hits / total_fields) if total_fields else 0.0,
        "motion_hits_total": sum(len(r.motion_hits) for r in reports),
        "quoted_standard_hits_total": sum(len(r.quoted_hits) for r in reports),
        "board_question_hits_total": sum(len(r.question_hits) for r in reports),
    }


def section_dalton(conn) -> dict:
    _hr("DALTON HELD-OUT CASE")
    print(f"Reading Dalton's real bytes directly (bypassing llm.fewshot, by design): {dalton_case.DALTON_PDF.name}")

    triage_report = dalton_case.real_triage_report()
    print("\n-- (1) real triage of Dalton's real PDF --")
    print(json.dumps(triage_report, indent=2))

    extraction_report = dalton_case.real_extraction_attempt()
    print("\n-- (2) real Tier A/B extraction attempt (ingest.pipeline.extract_document) --")
    print(json.dumps(extraction_report, indent=2))
    if extraction_report["candidate_count"] != 0:
        print("!! UNEXPECTED: extraction produced candidates -- Dalton is not a pure scan after all; "
              "re-derive the rest of this report's claims, they assumed 0.")

    print("\n-- (3) real subdivision walk, facts={} (the honest set given (2)) --")
    dalton_measured = dalton_case.run_dalton_eval(conn)
    print(json.dumps(dalton_measured, indent=2))

    print("\n-- clean SYNTHETIC comparator (labelled synthetic -- NOT Dalton's real facts) --")
    clean_measured = dalton_case.run_clean_comparator(conn)
    print(json.dumps(clean_measured, indent=2))

    print("\n-- (c) contested-mechanism demonstration (real ingest.fields.merge_field_group, synthetic inputs) --")
    contested = dalton_case.demonstrate_contested_mechanism()
    print(json.dumps(contested, indent=2))
    agree = dalton_case.demonstrate_agreement_is_not_contested()
    print(json.dumps(agree, indent=2))

    assertions = {
        "(a) full_criterion_coverage": {
            "measured": True,
            "observed_total_count": dalton_measured["total_count"],
            "expected": 21,
            "pass": dalton_measured["total_count"] == 21 and dalton_measured["every_standard_quoted_verbatim"],
        },
        "(b) honest_blank_count_higher_than_clean": {
            "measured": True,
            "dalton_honest_blank_count": dalton_measured["honest_blank_count"],
            "clean_comparator_honest_blank_count": clean_measured["honest_blank_count"],
            "pass": dalton_measured["honest_blank_count"] > clean_measured["honest_blank_count"],
            "caveat": (
                "findings_nodes.unresolved itself is structurally 1 for every node in both "
                "cases pre-vote (see module docstring) -- this compares honest_blank_count "
                "(no case-specific assertion rendered), not that column."
            ),
        },
        "(c) contradictions_surfaced_as_contested": {
            "measured_on_dalton_real_content": False,
            "reason": "Dalton is a pure scan (0/5 pages reach even the Tier-B floor); no OCR "
                      "path exists in this codebase; vision extraction needs ANTHROPIC_API_KEY, "
                      "which is not set in this environment. NOT MEASURED on Dalton's real content.",
            "mechanism_measured_on_synthetic_data": True,
            "synthetic_disagreement_state": contested["state"],
            "synthetic_agreement_state": agree["state"],
            "pass_mechanism_proof": contested["state"] == "contested" and agree["state"] != "contested",
        },
        "(d) no_confident_assertions_on_dalton": {
            "measured": True,
            "fact_recorded_letters": dalton_measured["fact_recorded_letters"],
            "pass": dalton_measured["fact_recorded_letters"] == [],
        },
    }
    print("\n-- THE FOUR ASSERTIONS --")
    print(json.dumps(assertions, indent=2))
    return {
        "triage": triage_report, "extraction": extraction_report,
        "dalton_walk": dalton_measured, "clean_comparator": clean_measured,
        "contested_mechanism": contested, "assertions": assertions,
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        conn = dalton_case.build_db(Path(tmp))
        try:
            _hr("OVER-CONCLUSION SCAN")
            oc_summary = section_over_conclusion(conn)
            dalton_summary = section_dalton(conn)
        finally:
            conn.close()

    _hr("SUMMARY")
    print(json.dumps({"over_conclusion": oc_summary}, indent=2))
    print(json.dumps({"dalton_assertions": dalton_summary["assertions"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
