"""eval/metrics.py -- the four W8 eval metrics, computed separately and
NEVER averaged together (see eval/run_eval.py's report for why, and
BUILD-STATE.md's W8 resume note).

Every function here is a plain, offline computation over real code paths
already built by W1-W7 (engine/, ingest/, ruleset_build/) -- this module
adds no new extraction or judgement logic of its own; it only checks the
existing app's real output against what is actually verifiable without a
model.

--------------------------------------------------------------------------
WHAT IS COMPUTED HERE, AND WHY (READ BEFORE ADDING A METRIC)
--------------------------------------------------------------------------
1. STRUCTURAL RECALL + COVERAGE -- deterministic, no model needed.
   Scoped to the ONE criteria set the engine actually has built today:
   Subdivision (Article 7 Section 12.f.1, 21 lettered standards a-u --
   engine/criteria_seed.py, rulesets/adopted/criteria-subdivision.json).
   Ground truth ("which standards did the real decision actually address")
   comes from `eval.ground_truth.decision_addressed_letters()` -- D-0031,
   2026-08-24 -- which reads the decision PDF's own text directly (the
   lettered "APPROVAL STANDARDS" list every real subdivision decision uses)
   and has ZERO dependency on rulesets/adopted/articles.json or anything
   built from it. See eval/ground_truth.py's own module docstring for the
   full method and its stated failure modes, and
   "GROUND-TRUTH INDEPENDENCE" below for why this replaced the earlier,
   circular derivation. Predicted comes from actually RUNNING
   engine.subdivision_review.run_walk() against that pair (facts={} is
   sufficient: CONTRACT.md's "the criteria walk is always complete"
   invariant means the walk produces all 21 nodes regardless of facts --
   proven directly here, not assumed).

   D-0030 REPLACED PRECISION WITH COVERAGE (2026-08-24) -- READ THIS BEFORE
   RE-ADDING A PRECISION NUMBER. This app is a COMPLETE-WALK design: the
   engine renders every standard in the criteria set on every case,
   unconditionally (dropping a criterion is the worst failure this app can
   make, per CLAUDE.md/the task brief). Under that design,
   precision = |predicted (intersect) truth| / |predicted| is not just
   uninformative, it is BACKWARDS: because |predicted| is pinned at the
   full 21 regardless of what the real decision cited, precision can only
   fall when the app renders a standard the real decision addressed more
   tersely (folded into shared prose, no per-letter citation) -- i.e. it
   penalises exactly the completeness behaviour this app exists to
   guarantee, and it CANNOT detect the actual failure mode we care about
   (a dropped criterion), because dropping standard k from the render
   would shrink |predicted| and |intersection| together and leave
   precision unchanged (proven in
   tests/test_eval_structural_metrics.py::test_precision_is_blind_to_omission,
   kept on file specifically so nobody re-derives precision and rediscovers
   this the hard way).

   What is measured instead, as two SEPARATE numbers, neither of them
   averaged into the other:
     - RECALL = |predicted (intersect) truth| / |truth| -- unchanged from
       before. This one DOES detect a dropped criterion: if the engine's
       predicted set is missing a letter the real decision cited, that
       letter drops out of the intersection while |truth| stays fixed, so
       recall falls (tests/test_eval_structural_metrics.py::
       test_recall_degrades_when_a_criterion_is_dropped_from_predicted
       drops one deterministically and asserts the number moves). Recall
       still needs a nonzero ground-truth set to be defined at all -- see
       "not computable" below.
     - COVERAGE is a new, separate, per-pair boolean assertion, not a rate:
       `predicted_letters == {every standard_letter in the criteria set
       actually loaded for this walk}` (engine/subdivision_review.load_
       rules_for_criteria_set()'s own rule list is the universe, not a
       hardcoded "a".."u" -- so this stays correct if the criteria set's
       size ever changes). Coverage needs NO ground truth, so it is
       reported for every subdivision pair the walk runs against
       (currently both shattuck and academy_hill, even though academy_hill
       has no computable recall -- see below), and it is a completeness
       AUDIT of an invariant that is supposed to always hold, not a
       performance estimate meant to generalise -- see eval/run_eval.py's
       printing code for why it is therefore NOT subject to the same
       minimum-sample-size gate as the recall aggregate (D-0030 in
       DECISIONS-NEEDED.md has the full reasoning).

   GROUND-TRUTH INDEPENDENCE (D-0031, 2026-08-24) -- READ THIS BEFORE
   SWITCHING THE TRUTH SOURCE BACK. The ground truth used to be derived from
   `ruleset_build.verify_citations.build_report()`, which resolves citations
   in the decision's text against `rulesets/adopted/articles.json` -- the
   SAME artifact `engine/criteria_seed.py` builds the criteria set (the
   "predicted" side) from. A node id missing from articles.json would
   silently shrink BOTH sides of the recall fraction at once (the citation
   fails to resolve, AND the criteria set never seeds that standard), so
   the metric could agree with itself even while a real standard vanished
   from the app -- an eval that cannot detect its own most important
   failure mode. `eval/ground_truth.py` replaces that derivation with a
   direct read of the decision PDF's own text, with NO import of
   articles.json, `ruleset_build.verify_citations`, or `engine.criteria_seed`
   anywhere in that module (mechanically checked by
   tests/test_ground_truth.py::test_module_has_no_articles_json_dependency).
   `tests/test_ground_truth.py::test_independence_from_articles_json` proves
   the actual claim this exists for: deleting/corrupting articles.json (or
   monkeypatching engine.criteria_seed to drop a standard) does not change
   eval.ground_truth's answer, because it never reads either one.
   Cross-checked against the OLD method on both real decisions on file: they
   agree (Shattuck 21/21, Academy Hill 0 -- its "CONCLUSIONS OF LAW" section
   is a never-filled-in DRAFT template, so there is genuinely nothing to
   extract by either method). Agreement is a sanity check that the new
   method is not obviously wrong; it is not what proves independence -- the
   test above does that.

   Only 2 of the 6 matched pairs (shattuck, academy_hill) carry
   `"subdivision"` in review_types with a decision on file, so recall is
   computable over at most N=2 pairs today -- the other 4 review types
   (expanded_use, small_project_plan, shoreland_zoning, use_permit,
   large_project_plan) have no criteria set built yet in this engine
   (only Subdivision exists under rulesets/adopted/), so recall/coverage
   for THOSE pairs is reported as "not applicable (no criteria set built
   for this review_type yet)" -- a real engine-capability gap, a
   different reason than "not measured (no API key)".

2. OVER-CONCLUSION RATE -- 0 by construction; this function proves it
   against real output rather than trusting the claim. Runs the same
   subdivision walk as (1) and checks, over every node actually written
   to a real findings_nodes table:
     (a) `disposition` (stored in the node's own provenance JSON) is one
         of the 7 closed engine.review.Disposition members -- never a
         freeform string a future edit could slip a verdict into;
     (b) neither `heading` nor `body` (this app's OWN authored text --
         NOT `quoted_standard_text`, which is the Code's own verbatim
         words and legitimately contains phrases like "in violation of"
         when quoting a standard such as Article 7 Section 12.f.1.u.; an
         earlier version of this check scanned quoted_standard_text too
         and flagged that real Code language as a false positive on both
         Shattuck and Academy Hill every run -- see the inline comment at
         the check itself) contains any banned-verdict substring
         (engine.review.contains_banned_verdict_language);
     (c) the node's own `conclusion` column is NULL (a human, never the
         engine, sets it -- CONTRACT.md 3.6's own CHECK enforces this at
         the schema level; this re-checks it at the data level);
     (d) engine.findings.find_orphan_conclusions() over the whole run
         returns [] (no conclusion anywhere lacks a carried motion behind
         it -- vacuously true here since (c) already holds, checked
         anyway because it is cheap and it is the actual production
         guard, not a re-derivation of it).
   over_conclusion_rate = (violations of a/b/c) / (nodes checked).

3. FACT FIDELITY + SILENT_ERROR_RATE, native-text pairs only. "Fidelity"
   here means GROUNDING: does every ingest.fields.FieldCandidate's
   value_raw actually appear (after whitespace normalization) on the PDF
   page it claims (`page_no`)? This is answerable without any hand-built
   ground truth of "the true field values" (which nobody has labelled for
   these real records) because ingest/native.py's own contract is that
   value_raw is "exactly as concatenated from the source spans" -- i.e.
   grounding is supposed to be true BY CONSTRUCTION, and this function
   checks that claim against real extracted candidates instead of trusting
   the docstring, the same spirit as (2) above.
   silent_error_rate = (ungrounded candidates with needs_confirmation is
   False) / (all candidates). Per ingest/fields.py's own dataclass
   invariant, needs_confirmation is pinned True in __post_init__ -- there
   is NO code path that can construct a False one -- so this is expected
   to be exactly 0.0 for every candidate this module can produce today.
   Reported anyway, computed for real, never assumed.
   Only run for a pair when its application PDF actually has at least one
   Tier A or Tier B page (checked live via ingest.triage, not hardcoded);
   otherwise reported as not-measured (needs the vision/LLM path -- no key).

4. PROSE USEFULNESS -- not implemented here. It needs generated prose
   (which needs an LLM call) and is human-labelled by design (the task
   brief: "DELIBERATELY NOT OPTIMISED... never tune on it"). eval/run_eval.py
   reports it as "not measured (no API key)" without calling into this
   module at all.
"""

from __future__ import annotations

import re
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app import db, security
from app.config import MIGRATIONS_DIR
from engine import criteria_seed, subdivision_review
from engine.findings import find_orphan_conclusions
from engine.review import Disposition, contains_banned_verdict_language
from ingest import pipeline, triage

from eval import ground_truth
from eval.pairs import MATCHED_PAIRS, PairRecord, application_pdf_path, decision_pdf_path

ACTOR = security.SYNTHETIC_USER_ID
ADOPTED_RULESET_ID = "eval_r_adopted"


# --------------------------------------------------------------------------- #
# Shared: a fresh, throwaway, fully-migrated DB -- same shape as
# tests/test_subdivision_review.py's `conn`/`seeded` fixtures, inlined here
# because this module is runtime code, not a test, and must not import
# from tests/.
# --------------------------------------------------------------------------- #


def _seed_ruleset_row(conn: sqlite3.Connection) -> None:
    now = "2026-08-24T00:00:00.000Z"
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, adopted_on, built_at,
             builder_version, manifest_path, source_sha_json, is_current, superseded_by,
             created_at, actor_user_id)
        VALUES (?, 'adopted', 'Newcastle Core Zoning Code (adopted)', 1, 'adopted', NULL,
                ?, 'eval/metrics.py', 'rulesets/adopted/manifest.json', '{}', 1, NULL, ?, NULL);
        """,
        (ADOPTED_RULESET_ID, now, now),
    )


def _fresh_conn(tmp_dir: Path) -> sqlite3.Connection:
    conn = db.connect(tmp_dir / "eval.db")
    db.migrate(conn, MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    _seed_ruleset_row(conn)
    return conn


def _run_subdivision_walk(conn: sqlite3.Connection, *, case_label: str) -> dict[str, Any]:
    """Runs the real W6 subdivision walk (facts={}) for one throwaway case
    and returns {"rules": [...], "walk": {...}, "nodes": [<row dicts>]}."""
    from app import cases

    seeded = criteria_seed.sync_subdivision_criteria(conn, ruleset_id=ADOPTED_RULESET_ID, actor_user_id=ACTOR)
    case = cases.create_case(
        conn, application_type="subdivision", map_lot=f"EVAL-{case_label}", situs_address="n/a",
        applicant_name=case_label, actor_user_id=ACTOR,
    )
    rules = subdivision_review.load_rules_for_criteria_set(conn, seeded["criteria_set_id"])
    walk = subdivision_review.run_walk(
        conn, case_id=case["id"], criteria_set_id=seeded["criteria_set_id"], rules=rules,
        facts={}, default_ruleset_key="adopted", actor_user_id=ACTOR,
        parent_citation={"article": 7, "section": "12", "subsection": "f.1"},
    )
    node_rows = [
        dict(r) for r in conn.execute(
            "SELECT * FROM findings_nodes WHERE case_id = ? AND node_type = 'finding';",
            (case["id"],),
        ).fetchall()
    ]
    return {"rules": rules, "walk": walk, "nodes": node_rows, "case_id": case["id"]}


# --------------------------------------------------------------------------- #
# 1. Structural recall + coverage (D-0030: precision was removed here --
# see the module docstring section 1 for the full reasoning and
# tests/test_eval_structural_metrics.py for the proof).
# --------------------------------------------------------------------------- #

# The minimum number of pairs a RATE-ESTIMATE aggregate (recall) may be
# reported over. Below this, run_eval prints "insufficient pairs (n=N); no
# aggregate reported" instead of a number -- see aggregate_structural()'s
# own docstring for the justification. Coverage is NOT gated by this
# constant: it is a per-pair completeness AUDIT of an invariant that is
# supposed to hold on every single case, not a rate meant to generalise
# across a sample, so even n=1 is a real, legible answer to "did the
# invariant hold" -- suppressing it below some n would hide a genuine
# stop-ship signal for no honest reason. See DECISIONS-NEEDED.md D-0030.
MIN_AGGREGATE_N = 3


@dataclass
class StructuralResult:
    pair_name: str
    applicable: bool  # False = no criteria set built for this pair's review_type(s)
    reason: str | None = None
    universe_letters: tuple[str, ...] = ()  # every standard_letter in the criteria set actually loaded
    ground_truth_letters: tuple[str, ...] = ()
    predicted_letters: tuple[str, ...] = ()
    recall: float | None = None  # None = not computable (no ground truth) -- never silently 0 or 1
    coverage_ok: bool | None = None  # predicted_letters == universe_letters; None only when not applicable
    coverage_missing: tuple[str, ...] = ()  # universe_letters - predicted_letters, for diagnosis


def _decision_addressed_letters(decision_pdf: Path) -> tuple[set[str], str | None]:
    """D-0031: reads the decision PDF directly via eval.ground_truth -- see
    that module's docstring for the method and this module's docstring
    section "GROUND-TRUTH INDEPENDENCE" for why. Returns (letters, reason);
    `reason` is set (and `letters` empty) whenever the letters could not be
    derived at all (`region_found is False`) OR were derivable but came back
    empty -- both are "not computable," never silently reported as 0."""
    gt = ground_truth.decision_addressed_letters(decision_pdf)
    if not gt.region_found:
        return set(), gt.reason
    if not gt.letters:
        return set(), gt.reason
    return set(gt.letters), None


def structural_recall_and_coverage(pairs: tuple[PairRecord, ...] = MATCHED_PAIRS) -> list[StructuralResult]:
    """Structural recall (rate, needs ground truth) + coverage (per-pair
    completeness assertion, needs no ground truth). Replaces the old
    structural_recall_precision() -- see module docstring section 1.
    """
    subdivision_pairs = [
        p for p in pairs if "subdivision" in p.review_types and p.decision_filename
    ]
    non_subdivision_pairs = [p for p in pairs if p not in subdivision_pairs]

    results: list[StructuralResult] = [
        StructuralResult(
            pair_name=p.name, applicable=False,
            reason=f"no criteria set built yet for review_type(s) {list(p.review_types)!r} "
                   f"(only 'subdivision' has one under rulesets/adopted/)",
        )
        for p in non_subdivision_pairs
    ]

    if not subdivision_pairs:
        return results

    for pair in subdivision_pairs:
        truth, not_computable_reason = _decision_addressed_letters(decision_pdf_path(pair))

        with tempfile.TemporaryDirectory(prefix="eval-structural-") as td:
            conn = _fresh_conn(Path(td))
            try:
                run = _run_subdivision_walk(conn, case_label=pair.name)
            finally:
                conn.close()

        results.append(_score_pair(pair.name, run, truth, not_computable_reason=not_computable_reason))

    return results


def _score_pair(
    pair_name: str, run: dict[str, Any], truth: set[str], *, not_computable_reason: str | None = None,
) -> StructuralResult:
    """The pure(ish) scoring step, factored out of structural_recall_and_coverage()
    so it can be exercised directly with a hand-built `run["nodes"]` in
    tests -- see test_recall_degrades_when_a_criterion_is_dropped_from_predicted,
    which calls structural_recall_and_coverage() end-to-end with a monkeypatched
    _run_subdivision_walk(), and test_score_pair_* below, which call this
    function directly with a fabricated predicted set for a faster, more
    targeted proof of the same behaviour.
    """
    universe = {rule["standard_letter"] for rule in run["rules"]}
    predicted = {row["number_label"].rstrip(".") for row in run["nodes"] if row["number_label"]}
    coverage_ok = predicted == universe
    coverage_missing = tuple(sorted(universe - predicted))

    if not truth:
        return StructuralResult(
            pair_name=pair_name, applicable=True,
            reason=not_computable_reason
                   or "no lettered standards found in this decision's own text "
                      "-- recall undefined (division by zero avoided, not silently reported as 0 or 1)",
            universe_letters=tuple(sorted(universe)),
            predicted_letters=tuple(sorted(predicted)),
            coverage_ok=coverage_ok, coverage_missing=coverage_missing,
        )

    intersection = predicted & truth
    recall = len(intersection) / len(truth)

    return StructuralResult(
        pair_name=pair_name, applicable=True,
        universe_letters=tuple(sorted(universe)),
        ground_truth_letters=tuple(sorted(truth)),
        predicted_letters=tuple(sorted(predicted)),
        recall=recall,
        coverage_ok=coverage_ok, coverage_missing=coverage_missing,
    )


def aggregate_structural(results: list[StructuralResult]) -> dict[str, Any]:
    """Two independent aggregates, neither one gating the other:

    - recall: a MICRO-AVERAGED rate (pool intersection/truth counts across
      pairs rather than mean-of-ratios, so one small pair can't dominate),
      reported ONLY when at least MIN_AGGREGATE_N pairs have a computable
      recall (nonzero ground truth). Below that, `recall` is None and
      `insufficient_n_reason` explains why -- run_eval.py prints that
      sentence instead of a number rather than silently omitting one or
      printing a misleadingly precise n=1/n=2 figure. n=3 is chosen as the
      floor deliberately low, not as a statistically comfortable bar: n=1
      is a single anecdote (cannot show whether the number is typical or a
      fluke), n=2 cannot distinguish a real pattern from a coin flip
      between two data points, n=3 is the smallest sample at which a lone
      outlier pair can no longer single-handedly define the reported
      figure. It is a floor, not a target -- raising real n needs more
      matched pairs with a built criteria set, not a lower bar here.
    - coverage: a TALLY, not a rate estimate (see MIN_AGGREGATE_N's own
      docstring above) -- "how many of the pairs the walk actually ran
      against rendered every standard in their criteria set" -- reported
      for every applicable pair regardless of n, because it is a pass/fail
      completeness audit, not a claim about how the app performs on
      average.
    """
    applicable = [r for r in results if r.applicable]
    recall_measured = [r for r in applicable if r.recall is not None]
    coverage_measured = [r for r in applicable if r.coverage_ok is not None]

    out: dict[str, Any] = {
        "n_pairs_applicable": len(applicable),
        "n_pairs_recall_computable": len(recall_measured),
        "recall": None,
        "insufficient_n_reason": None,
        "n_pairs_coverage_computed": len(coverage_measured),
        "coverage_pairs_ok": sum(1 for r in coverage_measured if r.coverage_ok),
        "coverage_all_ok": bool(coverage_measured) and all(r.coverage_ok for r in coverage_measured),
    }

    if len(recall_measured) < MIN_AGGREGATE_N:
        out["insufficient_n_reason"] = (
            f"insufficient pairs (n={len(recall_measured)}); no aggregate reported "
            f"-- minimum is {MIN_AGGREGATE_N} (see MIN_AGGREGATE_N's docstring in eval/metrics.py)"
        )
        return out

    total_truth = sum(len(r.ground_truth_letters) for r in recall_measured)
    total_pred_hit = sum(len(set(r.ground_truth_letters) & set(r.predicted_letters)) for r in recall_measured)
    out["recall"] = total_pred_hit / total_truth if total_truth else None
    return out


# --------------------------------------------------------------------------- #
# 2. Over-conclusion rate
# --------------------------------------------------------------------------- #


@dataclass
class OverConclusionResult:
    pair_name: str
    nodes_checked: int
    violations: list[str] = field(default_factory=list)

    @property
    def rate(self) -> float:
        return len(self.violations) / self.nodes_checked if self.nodes_checked else 0.0


def over_conclusion_rate(pairs: tuple[PairRecord, ...] = MATCHED_PAIRS) -> list[OverConclusionResult]:
    subdivision_pairs = [p for p in pairs if "subdivision" in p.review_types]
    results: list[OverConclusionResult] = []
    disposition_values = {d.value for d in Disposition}

    for pair in subdivision_pairs:
        with tempfile.TemporaryDirectory(prefix="eval-overconclusion-") as td:
            conn = _fresh_conn(Path(td))
            try:
                run = _run_subdivision_walk(conn, case_label=pair.name)
                violations: list[str] = []

                for row in run["nodes"]:
                    label = row["number_label"] or row["id"]

                    if row["conclusion"] is not None:
                        violations.append(f"{label}: conclusion set by the engine walk itself")
                        continue  # the checks below assume no conclusion; skip them for this node

                    # `quoted_standard_text` and `board_question` are deliberately NOT
                    # scanned here: the first is the Code's OWN verbatim words (Article 7
                    # standard u., for example, legitimately contains "in violation of" --
                    # that is the ordinance quoting itself, not this app drawing a
                    # verdict), and the second is a question PUT TO the Board, not an
                    # assertion the engine is making. Scanning either would produce
                    # exactly the false-positive eval/over_conclusion.py's own module
                    # docstring warns about ("burying a scanner in false positives is its
                    # own way of making it untrustworthy") -- confirmed empirically while
                    # building this check: an earlier version of this loop DID include
                    # quoted_standard_text and flagged Shattuck/Academy Hill standard u.'s
                    # own Code language every time, a false positive, not a real finding.
                    # Only `heading` and `body` are this app's OWN authored text.
                    for field_name in ("heading", "body"):
                        text = row.get(field_name)
                        if text:
                            hit = contains_banned_verdict_language(text)
                            if hit:
                                violations.append(f"{label}: banned verdict substring {hit!r} in {field_name}")

                    import json as _json
                    provenance = _json.loads(row["provenance_json"]) if row["provenance_json"] else {}
                    disposition = provenance.get("engine", {}).get("disposition")
                    if disposition is not None and disposition not in disposition_values:
                        violations.append(f"{label}: disposition {disposition!r} not in the closed Disposition set")

                orphans = find_orphan_conclusions(conn, case_id=run["case_id"])
                for o in orphans:
                    violations.append(f"{o['number_label'] or o['id']}: orphan conclusion (no carried motion)")

                results.append(OverConclusionResult(
                    pair_name=pair.name, nodes_checked=len(run["nodes"]), violations=violations,
                ))
            finally:
                conn.close()

    return results


# --------------------------------------------------------------------------- #
# 3. Fact fidelity (grounding) + silent_error_rate, native-text pairs only
# --------------------------------------------------------------------------- #


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


def _page_text_cache(pdf_path: Path) -> dict[int, str]:
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    try:
        return {i + 1: doc[i].get_text() for i in range(doc.page_count)}
    finally:
        doc.close()


@dataclass
class FidelityResult:
    pair_name: str
    measured: bool
    reason: str | None = None
    total_candidates: int = 0
    grounded_strict: int = 0
    grounded_loose: int = 0
    ungrounded_and_unflagged: int = 0  # the silent_error_rate numerator

    @property
    def grounded_strict_rate(self) -> float | None:
        return self.grounded_strict / self.total_candidates if self.total_candidates else None

    @property
    def grounded_loose_rate(self) -> float | None:
        return self.grounded_loose / self.total_candidates if self.total_candidates else None

    @property
    def silent_error_rate(self) -> float | None:
        return self.ungrounded_and_unflagged / self.total_candidates if self.total_candidates else None


def fact_fidelity_and_silent_error(names: tuple[str, ...]) -> list[FidelityResult]:
    """`names` is passed explicitly by the caller (eval/run_eval.py), not
    defaulted to MATCHED_PAIRS -- this is the one metric the task brief
    says should ALSO run on a holdout (Stantec pp.9-12 are native text;
    holdout means 'no decision to grade recall/precision against', not
    'the harness may not look at its own application PDF's own text').
    """
    from eval.pairs import get_pair

    results: list[FidelityResult] = []

    for name in names:
        pair = get_pair(name)
        pdf_path = application_pdf_path(pair)
        pages = triage.triage_pdf(str(pdf_path))
        tier_counts = triage.tier_census(pages)
        if tier_counts.get("A", 0) == 0 and tier_counts.get("B", 0) == 0:
            results.append(FidelityResult(
                pair_name=name, measured=False,
                reason="no Tier A or Tier B (native-text) page found -- extraction here would "
                       "require the Tier C/D vision path, which needs an LLM call",
            ))
            continue

        candidate_pages = [p.page_number for p in pages if p.tier in ("B", "D")]
        run = pipeline.extract_document(
            pdf_path, document_id="eval-doc", source_priority=40,
            positional_candidate_pages=candidate_pages,
        )

        if not run.candidates:
            results.append(FidelityResult(
                pair_name=name, measured=True, total_candidates=0,
                reason="native-text page(s) found but zero field candidates were extracted",
            ))
            continue

        page_text = _page_text_cache(pdf_path)
        grounded_strict = 0
        grounded_loose = 0
        silent = 0

        for cand in run.candidates:
            page = page_text.get(cand.page_no, "")
            page_norm = _normalize_ws(page)
            value_norm = _normalize_ws(cand.value_raw)

            strict = bool(value_norm) and value_norm in page_norm
            if strict:
                grounded_strict += 1
                grounded_loose += 1
                continue

            tokens = _TOKEN_RE.findall(value_norm)
            loose = bool(tokens) and all(t in page_norm for t in tokens)
            if loose:
                grounded_loose += 1
            elif not cand.needs_confirmation:
                # Structurally unreachable today (FieldCandidate.__post_init__
                # pins needs_confirmation True) -- checked directly anyway,
                # per the task brief: never trust a docstring's claim.
                silent += 1

        results.append(FidelityResult(
            pair_name=name, measured=True,
            total_candidates=len(run.candidates),
            grounded_strict=grounded_strict,
            grounded_loose=grounded_loose,
            ungrounded_and_unflagged=silent,
        ))

    return results
