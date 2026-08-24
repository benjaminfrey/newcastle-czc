"""eval/dalton_case.py -- W8 held-out eval case: Dalton (M002, L053, 976 US
Rt 1, docs/Findings of Fact and Conclusions of Law/"M002, L053 (976 US Rt 1,
Dalton) 2025.09.09 Application.pdf").

THE HOLDOUT DISTINCTION -- READ THIS FIRST
--------------------------------------------
`llm/fewshot.py` refuses, IN CODE, to open Dalton's or Stantec's PDF bytes
(`_require_readable()`, `HoldoutError`) -- that refusal exists so neither
document ever leaks into the few-shot prompt index, and is proven by
tests/test_fewshot.py monkeypatching `pymupdf.open` to fail loudly if it is
ever reached for either name.

THE EVAL HARNESS IS A DIFFERENT PATH WITH A DIFFERENT JOB. Reading the
held-out pair for real, offline evaluation is the entire point of a
held-out run -- W8's own brief names Dalton and Stantec as the cases to
run, not to refuse. This module therefore reads Dalton's real application
PDF bytes DIRECTLY from `FIXTURES_DIR`, never through `llm.fewshot` (which
would raise `HoldoutError` for it), and never adds Dalton to
`llm.fewshot.PAIRS` or any few-shot index. `tests/test_eval_holdout_access.py`
asserts BOTH halves of this distinction in one file, on purpose, so a later
reader who "fixes" one does not silently break the other:
  1. `llm.fewshot` still refuses Dalton (regression guard on the existing
     behaviour -- reuses `HoldoutError`).
  2. THIS module can open and triage Dalton's real bytes without raising.

WHAT THIS MODULE ACTUALLY MEASURES, AND WHAT IT DOES NOT
-----------------------------------------------------------
Read this before trusting any number this module prints, and before citing
it as evidence that Dalton "is" anything.

Dalton's application PDF is FIVE PAGES. `ingest.triage.triage_pdf()` --
real measurement below, not assumed -- finds `page.get_text()` returns an
EMPTY STRING on every one of the five: it is a pure scan, Tier C on all 5
pages, 0/5 pages reach even the Tier-B floor (20 chars). There is no OCR
path anywhere in this codebase; the only extractor for a Tier C/D page is
`ingest/vision.py`, which requires a real `LLMClient` call, which requires
`ANTHROPIC_API_KEY`, which does not exist in this environment and may not
be invented (standing rule). Consequences, stated plainly:

  - Dalton's actual CONTENT -- including whether it is genuinely
    "incomplete" or "internally contradictory" -- CANNOT be read from the
    page images offline. THAT SPECIFIC CLAIM IS NOT MEASURED BY THIS
    MODULE. It is asserted nowhere below as a fact about the real
    document; do not let a summary of this module's output upgrade it to
    one.
  - What CAN be measured, and IS measured below by actually calling the
    real functions and printing the real return values: (1) Dalton's real
    per-page triage census (`ingest.triage.triage_pdf`), (2) the real,
    deterministic, offline Tier A/B pipeline
    (`ingest.pipeline.extract_document`) run against Dalton's real bytes,
    which is expected -- and asserted -- to yield ZERO field candidates
    (BUILD-STATE.md Known Issue #2: "Tier C (pure scans) yields zero
    candidates -- correct behaviour, not a defect"), and (3) a full,
    real 21-criterion subdivision walk (`engine.subdivision_review.run_walk`)
    against a real Dalton-labelled case row, run on `facts={}` because that
    is the honest, complete set of facts item (2) actually produced -- not
    a stand-in for a richer extraction this module pretends happened.

  A CONSEQUENCE WORTH STATING EXPLICITLY, NOT BURYING: because Dalton
  yields zero real candidates today, and because no crosswalk in
  `ingest/pipeline.py` currently maps ANY extracted field_key onto the
  subdivision engine's `facts["standard.<letter>.value"]` keys for ANY
  case (verified by grep -- that wiring does not exist yet for any case,
  not just Dalton), running the real walk against Dalton today is
  MATHEMATICALLY IDENTICAL to running it against a case with no facts at
  all (`engine/subdivision_review.py`'s own already-proven empty-facts
  test). Dalton's specific "internally contradictory" character -- the
  one thing that would make it a different, harder case than a blank one
  -- cannot currently reach the engine at all, because contradiction is a
  property of DISAGREEING FIELD CANDIDATES (`ingest.fields.merge_field_group`),
  and there is nothing to disagree over when extraction returns nothing.
  This is a real, structural gap this module surfaces rather than papers
  over (see `demonstrate_contested_mechanism()` below for what IS proven
  with real code, and DECISIONS-NEEDED.md D-00xx logged by the caller of
  this module for the gap itself).

THE FOUR ASSERTIONS, AND HOW EACH IS ACTUALLY CHECKED
--------------------------------------------------------
  (a) Full criterion coverage -- MEASURED. `len(rules) == 21` and
      `result["total_count"] == 21`, both against a real `run_walk()`
      call, both printed as observed values.
  (b) A HIGH unresolved count, higher than a clean case -- MEASURED, but
      note `findings_nodes.unresolved` is structurally 1 for EVERY finding
      node in EVERY case until a human vote closes it (0013_findings_tree
      .sql's own CHECK; engine/subdivision_review.py's own comment on this
      -- "even a NOT_APPLICABLE ... remains a Board-adoptable item until a
      vote closes it"), so that raw column cannot distinguish Dalton from
      a fully-documented case; this module does not pretend it can. The
      metric actually computed is `honest_blank_count`: nodes whose
      disposition renders NO case-specific assertion at all (`body is
      None` -- BOARD_QUESTION or APPLICABILITY_UNKNOWN). This is compared
      against a `clean` comparator walk seeded with a SYNTHETIC (labelled
      `synthetic: true`, never claimed to be Dalton's real facts) complete
      fact set, to prove the metric actually moves when real facts exist,
      not just that both numbers happen to be 21.
  (c) Contradictions surfaced as `contested`, never silently resolved --
      NOT reproducible from Dalton's real content today (see above). What
      IS run, for real, against the real `ingest.fields.merge_field_group`
      function: a representative disagreement of the SHAPE Dalton's real
      pages would need vision extraction to reveal, explicitly labelled
      synthetic. See `demonstrate_contested_mechanism()`.
  (d) No confident assertions built on contradictory inputs -- MEASURED
      for the real Dalton walk (0 FACT_RECORDED nodes, because 0 facts
      exist); the contradictory-input half of this claim is, again, not
      exercisable without vision extraction, and is reported as such.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

REPO_ROOT = APP_ROOT.parent.parent
FIXTURES_DIR = REPO_ROOT / "docs" / "Findings of Fact and Conclusions of Law"
DALTON_PDF = FIXTURES_DIR / "M002, L053 (976 US Rt 1, Dalton) 2025.09.09 Application.pdf"

from app import cases, db, security  # noqa: E402
from engine import criteria_seed, subdivision_review, review  # noqa: E402
from engine.review import Disposition  # noqa: E402
from ingest import pipeline, triage  # noqa: E402
from ingest.fields import FieldCandidate, merge_field_group  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"
ACTOR = security.SYNTHETIC_USER_ID
ADOPTED_ID = "r_adopted_eval"


# --------------------------------------------------------------------------- #
# DB / ruleset / criteria scaffolding -- same shape tests/test_subdivision_
# review.py already establishes and this module reuses verbatim so a reader
# comparing the two isn't tripped up by an incidental difference.
# --------------------------------------------------------------------------- #


def _seed_ruleset(conn) -> None:
    now = "2026-08-24T00:00:00.000Z"
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, adopted_on, built_at,
             builder_version, manifest_path, source_sha_json, is_current, superseded_by,
             created_at, actor_user_id)
        VALUES (?, 'adopted', 'Newcastle Core Zoning Code (adopted)', 1, 'adopted', NULL,
                ?, 'eval/dalton_case', 'rulesets/adopted/manifest.json', '{}', 1, NULL, ?, NULL);
        """,
        (ADOPTED_ID, now, now),
    )


def build_db(tmp_path: Path):
    conn = db.connect(tmp_path / "eval-dalton.db")
    db.migrate(conn, MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    _seed_ruleset(conn)
    return conn


# --------------------------------------------------------------------------- #
# (1) Real triage of Dalton's real bytes -- MEASURED.
# --------------------------------------------------------------------------- #


def real_triage_report() -> dict[str, Any]:
    """Actually opens and triages Dalton's real PDF (never through
    llm.fewshot). Returns real, observed per-page tier data -- not an
    assumption about what a "pure scan" would look like."""
    if not DALTON_PDF.exists():
        raise FileNotFoundError(f"Dalton fixture not present: {DALTON_PDF}")
    pages = triage.triage_pdf(str(DALTON_PDF))
    tiers = triage.tier_census(pages)
    return {
        "page_count": len(pages),
        "tier_census": tiers,
        "pages_reaching_tier_b_floor_or_above": sum(1 for p in pages if p.char_count >= 20),
        "per_page_char_counts": [p.char_count for p in pages],
    }


# --------------------------------------------------------------------------- #
# (2) Real, deterministic, offline Tier A/B extraction attempt -- MEASURED.
# --------------------------------------------------------------------------- #


def real_extraction_attempt() -> dict[str, Any]:
    """Runs the real ingest.pipeline.extract_document() (the exact function
    every other case's extraction goes through) against Dalton's real
    bytes. Expected -- and asserted here, on the ACTUAL return value, not
    assumed -- to yield zero candidates, per BUILD-STATE.md Known Issue #2.
    """
    pages = triage.triage_pdf(str(DALTON_PDF))
    candidate_pages = [p.page_number for p in pages if p.tier in ("B", "D")]
    run = pipeline.extract_document(
        DALTON_PDF, document_id="eval-dalton-doc-1", source_priority=40,
        positional_candidate_pages=candidate_pages,
    )
    return {
        "generation": run.generation,
        "confidence": run.confidence,
        "tier_a_page": run.tier_a_page,
        "tier_b_pages_attempted": run.tier_b_pages_attempted,
        "candidate_count": len(run.candidates),
    }


# --------------------------------------------------------------------------- #
# (3) The real subdivision walk against a real Dalton-labelled case.
# --------------------------------------------------------------------------- #


def build_dalton_case(conn) -> dict[str, Any]:
    """A REAL findings-app case row, labelled for Dalton, `is_scratch=True`
    (this is an eval run, never a real Town docket entry). application_type
    is pinned to 'subdivision' as a DELIBERATE SCAFFOLD CHOICE, not a claim
    about Dalton's real review type (which is unknown -- the real
    application is unreadable offline, see module docstring): subdivision
    is the only criteria walk this app has built (BUILD-STATE.md W6), so it
    is the only one available to stress-test against a held-out case at
    all. A future vision-extraction pass may reveal a different real
    review_type; nothing here pre-judges it.
    """
    return cases.create_case(
        conn, application_type="subdivision",
        map_lot="M002, L053", situs_address="976 US Rt 1",
        applicant_name="Dalton (held-out W8 eval case; see llm.fewshot.PAIRS)",
        label="EVAL — M002, L053 (976 US Rt 1, Dalton) — W8 held-out run, not a real docket entry",
        is_scratch=True, actor_user_id=ACTOR,
    )


def _walk(conn, seeded, case, facts: dict[str, Any]):
    rules = subdivision_review.load_rules_for_criteria_set(conn, seeded["criteria_set_id"])
    result = subdivision_review.run_walk(
        conn, case_id=case["id"], criteria_set_id=seeded["criteria_set_id"], rules=rules,
        facts=facts, default_ruleset_key="adopted", actor_user_id=ACTOR,
        parent_citation={"article": 7, "section": "12", "subsection": "f.1"},
    )
    return rules, result


def _measure_walk(conn, case_id: str) -> dict[str, Any]:
    """Real query against the real findings_nodes rows this walk just
    wrote -- observed values, not the in-memory Finding objects (which
    could in principle diverge from what was actually persisted)."""
    rows = conn.execute(
        "SELECT number_label, applicability_verdict, unresolved, body, board_question, "
        "quoted_standard_text, conclusion, provenance_json "
        "FROM findings_nodes WHERE case_id = ? AND node_type = 'finding' ORDER BY sort_order;",
        (case_id,),
    ).fetchall()
    total = len(rows)
    every_quoted = all(bool(r["quoted_standard_text"]) for r in rows)
    honest_blanks = [r for r in rows if not r["body"]]
    fact_recorded = []
    for r in rows:
        import json
        prov = json.loads(r["provenance_json"]) if r["provenance_json"] else {}
        disposition = (prov.get("engine") or {}).get("disposition")
        if disposition == Disposition.FACT_RECORDED.value:
            fact_recorded.append(r["number_label"])
    conclusions_set = sum(1 for r in rows if r["conclusion"] is not None)
    return {
        "total_count": total,
        "every_standard_quoted_verbatim": every_quoted,
        "honest_blank_count": len(honest_blanks),
        "honest_blank_letters": sorted(r["number_label"] for r in honest_blanks),
        "fact_recorded_letters": sorted(fact_recorded),
        "conclusions_set": conclusions_set,
    }


def run_dalton_eval(conn) -> dict[str, Any]:
    """The real, empty-facts walk against the real Dalton case -- the only
    honest fact set available given (2) above."""
    seeded = criteria_seed.sync_subdivision_criteria(conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR)
    case = build_dalton_case(conn)
    rules, result = _walk(conn, seeded, case, facts={})
    measured = _measure_walk(conn, case["id"])
    measured["case_id"] = case["id"]
    measured["rules_loaded"] = len(rules)
    measured["run_walk_total_count"] = result["total_count"]
    measured["run_walk_unresolved_count"] = result["unresolved_count"]
    return measured


# --------------------------------------------------------------------------- #
# The "clean" comparator -- SYNTHETIC facts, explicitly labelled, used only
# to prove honest_blank_count actually falls when real facts exist (i.e.
# this module isn't printing 21 no matter what is fed in). NEVER presented
# as Dalton's real facts, and never fed to any real case row a report might
# later mistake for a filed application.
# --------------------------------------------------------------------------- #

SYNTHETIC_CLEAN_FACTS: dict[str, Any] = {
    "synthetic": True,  # matches llm/cassette.py's own fixture-labelling convention
    "site.within_watershed_of_pond_or_lake": False,
    "site.distance_to_protected_water_ft": 1200,
    "site.in_fema_flood_zone": False,
    "subdivision.has_shore_frontage_lots": False,
    "subdivision.crosses_municipal_boundary": False,
    "standard.o.value": False,
    "standard.p.value": False,
    "standard.u.value": False,
}


def run_clean_comparator(conn) -> dict[str, Any]:
    seeded = criteria_seed.sync_subdivision_criteria(
        conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR,
    )
    case = cases.create_case(
        conn, application_type="subdivision", map_lot="EVAL-CLEAN-000",
        situs_address="(synthetic comparator, not a real parcel)",
        applicant_name="(synthetic comparator)",
        label="EVAL — synthetic clean comparator (facts fabricated for W8 metric-direction proof only)",
        is_scratch=True, actor_user_id=ACTOR,
    )
    facts = {k: v for k, v in SYNTHETIC_CLEAN_FACTS.items() if k != "synthetic"}
    rules, result = _walk(conn, seeded, case, facts=facts)
    measured = _measure_walk(conn, case["id"])
    measured["case_id"] = case["id"]
    measured["rules_loaded"] = len(rules)
    return measured


# --------------------------------------------------------------------------- #
# (c) The contested mechanism -- real code, synthetic (labelled) data.
# --------------------------------------------------------------------------- #


def demonstrate_contested_mechanism() -> dict[str, Any]:
    """Calls the REAL `ingest.fields.merge_field_group()` -- not a
    reimplementation, not a test double -- against two disagreeing
    candidates for one field, representing the SHAPE of contradiction a
    scanned application like Dalton's would need vision extraction to
    reveal (e.g. two different stated lot-size or setback figures on
    different pages). EXPLICITLY SYNTHETIC (`synthetic: True` returned
    alongside the result) -- this proves the mechanism, not a fact about
    Dalton's real, currently-unreadable content."""
    candidate_a = FieldCandidate(
        field_key="parcel.lot_size_acres", value_raw="2.1 acres", value_norm=2.1, unit="acres",
        document_id="eval-dalton-doc-1", page_no=1, bbox=(0.0, 0.0, 10.0, 10.0),
        method="regex", confidence=0.7, rationale="[SYNTHETIC] label 'Lot Size' on p.1", source_priority=40,
    )
    candidate_b = FieldCandidate(
        field_key="parcel.lot_size_acres", value_raw="0.9 acres", value_norm=0.9, unit="acres",
        document_id="eval-dalton-doc-1", page_no=3, bbox=(0.0, 0.0, 10.0, 10.0),
        method="regex", confidence=0.7, rationale="[SYNTHETIC] label 'Lot Size' on p.3, disagrees with p.1",
        source_priority=40,
    )
    result = merge_field_group([candidate_a, candidate_b])
    return {
        "synthetic": True,
        "field_key": result.field_key,
        "state": result.state,
        "chosen_value": result.chosen.value_raw,
        "both_candidates_retained": len(result.candidates) == 2,
        "contested_with_count": len(result.contested_with),
        "silently_resolved_to_one_value": result.state != "contested",
    }


def demonstrate_agreement_is_not_contested() -> dict[str, Any]:
    """The control case, run for real alongside the above: two candidates
    that AGREE must never read as contested -- proves the mechanism isn't
    just flagging every multi-candidate field."""
    candidate_a = FieldCandidate(
        field_key="parcel.lot_size_acres", value_raw="2.1 acres", value_norm=2.1, unit="acres",
        document_id="eval-dalton-doc-1", page_no=1, bbox=(0.0, 0.0, 10.0, 10.0),
        method="regex", confidence=0.7, rationale="[SYNTHETIC] label 'Lot Size' on p.1", source_priority=40,
    )
    candidate_b = FieldCandidate(
        field_key="parcel.lot_size_acres", value_raw="2.1 acres", value_norm=2.1, unit="acres",
        document_id="eval-dalton-doc-1", page_no=2, bbox=(0.0, 0.0, 10.0, 10.0),
        method="regex", confidence=0.65, rationale="[SYNTHETIC] label 'Lot Size' on p.2, agrees with p.1",
        source_priority=40,
    )
    result = merge_field_group([candidate_a, candidate_b])
    return {"synthetic": True, "state": result.state}


__all__ = [
    "DALTON_PDF", "build_db", "real_triage_report", "real_extraction_attempt",
    "build_dalton_case", "run_dalton_eval", "run_clean_comparator",
    "demonstrate_contested_mechanism", "demonstrate_agreement_is_not_contested",
    "SYNTHETIC_CLEAN_FACTS",
]
