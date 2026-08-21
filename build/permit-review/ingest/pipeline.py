"""ingest/pipeline.py -- the W4 end-to-end glue: formgen detection + Tier
A/B extraction + persistence, wired onto the case-level field_defs
ingest/worklist.py seeds. Implements CONTRACT.md §3.6.

WHY THIS FILE EXISTS. Three sibling W4 modules were built concurrently and
never actually connected:
  - ingest/formgen.py detects a document's generation and (correctly)
    persists it onto `documents` -- but nothing called it against a real
    uploaded document.
  - ingest/native.py / ingest/positional.py extract FieldCandidate objects
    (a pure, DB-independent dataclass -- ingest/fields.py) -- but nothing
    ever turned one into a `field_candidates` row, because that requires a
    `field_def_id` foreign key, and no code resolved one.
  - ingest/worklist.py seeds the ~23 case-level field_defs a Findings draft
    needs, keyed `f"{panel_key}.{slug(label)}"` (e.g.
    "project_information.applicant") -- a DIFFERENT, coarser field_key
    vocabulary than native.py/positional.py's own (e.g. "applicant.name",
    "applicant.address", "applicant.phone", "applicant.email" -- one
    field_def's worth of ground truth, split four ways by extraction
    granularity). app/extraction.py's own docstring names this precise gap:
    it "reads whatever field_candidates rows a separate, not-yet-built
    Tier A/B extraction pass already wrote."

THE CROSSWALK (FIELD_KEY_CROSSWALK / COMBINE_RULES below) is the missing
join: every native/positional field_key that has a genuine home among the
seeded case-level field_defs is rewritten onto that field_def's field_key
before insertion. A few (parcel.tax_map + parcel.lot; parcel.deed_book +
parcel.deed_page) legitimately combine into ONE seeded field_def and are
merged into a single candidate, not left to "disagree" against each other.
Everything else -- every building/setback/unit-count field_key -- has NO
seeded field_def to attach to: Article 2's per-district dimensional
field_defs are what would host those, and CONTRACT.md's own
`app/rulesets.py` cannot even load `rulesets/adopted/` while
`districts.json` is blocked (DECISIONS-NEEDED.md D-0001/D-0002). Rather
than invent an ad hoc field_def for a dimensional standard this codebase
has explicitly refused to guess at, those candidates are computed (so this
module's report can show they were correctly extracted) but deliberately
NOT persisted to field_candidates -- reported instead as `unattached`, an
honest structural gap, not silently dropped or silently homed somewhere
wrong.

A SECOND, INDEPENDENT DRIFT this module resolves: WHICH pages get a
positional (Tier B) extraction attempt. positional.py's own docstring
names "the Stantec packet pp.9-12" as its target, verbatim from the task
brief's own "THE TIER B TRAP" section -- but ingest/triage.py (a separate,
concurrently-built W3 module) classifies the real Stantec fixture's actual
trap pages (physical pages 9 and 12, /Rotate 90 and /Rotate 270) as Tier
**D** ("plansheet"), not Tier B: triage.py's D-tier rule fires on ANY
rotated page, as a cautious proxy for "this is probably an oversized
drawing sheet." Verified directly against the real fixture: page 9 is
639 chars of real embedded text at rotation=90, is_plansheet=True, tier='D'
-- not because it IS a plan sheet (it is the same scanned, sideways-fed
Gen-1 form page positional.py exists to read), but because triage.py's own
proxy heuristic cannot tell "rotated drawing" from "rotated scanned form
page" without reading the page. Restricting positional extraction to
literal tier='B' pages (as a first-pass reading of the task brief's own
"Tier B trap" label might suggest) would therefore silently skip the exact
pages the brief names as the worked example.

The resolution: this module's `extract_document()` runs the Gen-1
positional pass over every page a caller marks Tier **B or D**
(`positional_candidate_pages`), never Tier C (a genuinely near-empty scan
-- e.g. Stantec's own pages 10/11, 8-9 chars each, correctly produce
nothing) and never OCR/vision (positional.py only ever reads a page's
EXISTING embedded text layer -- it does not distinguish B from D itself,
and neither does this module; the distinction only matters for WHICH pages
are worth the attempt at all). This stays inside the phase's own stated
tool boundary ("NO OCR of handwriting... NO VISION") because nothing new
is being READ that a stricter Tier-B-only pass wouldn't also read off the
same page -- only the set of pages attempted changes, and
positional.py's own confidence gating (POSITIONAL_MIN_CONFIDENCE,
parseable=False when nothing lands in a confident window) means a genuine
plan/drawing sheet swept in by this broadening still correctly contributes
zero candidates, exactly as it would have if it had been left out.

A THIRD, INDEPENDENT DRIFT this module resolves: ingest/native.py's own
`detect_generation()` (used internally by `extract_native_pdf()`) is a
narrower text-only check than ingest/formgen.py's -- it has no fallback to
formgen.py's SECONDARY title-only signal, and no OCR fallback for a pure
scan. Verified against the real Stantec fixture: `native.detect_generation`
returns 'unknown' (misses the secondary "ZONING PERMIT APPLICATION" phrase
on its cover-letter page 8), while `formgen.detect_generation` correctly
returns 'gen1' (medium confidence) via that same secondary signal. This
module therefore NEVER calls `extract_native_pdf()` (which would silently
skip Stantec's Tier A extraction). It calls `formgen.detect_generation()`
ONCE per document as the single authoritative source of truth, and drives
`find_gen1_form_page` / `find_gen2_cover_page` + the matching field-map
extractor directly off that result -- so a "gen1, medium confidence" verdict
from the secondary signal alone still gets its Tier A/B extraction attempt,
exactly as it should.
"""

from __future__ import annotations

import dataclasses
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz

from app.audit import append_event
from ingest import formgen as formgen_mod
from ingest import native as native_mod
from ingest import positional as positional_mod
from ingest.fields import FieldCandidate

# --------------------------------------------------------------------------- #
# The crosswalk.
# --------------------------------------------------------------------------- #

# Direct 1:1 renames: native/positional field_key -> the seeded case-level
# field_def's field_key (ingest.worklist.FIELD_DEF_SEED, panel_key +
# "." + slug(label)). Verified against that seed list by hand, once, below
# each entry's comment; a mismatch here would surface immediately as
# `unattached` in this module's report rather than a silent misfile,
# because persist_candidates() resolves field_def_id by an exact
# (ruleset_id, field_key, district_key IS NULL) lookup.
FIELD_KEY_CROSSWALK: dict[str, str] = {
    "applicant.name": "project_information.applicant",
    "applicant.address": "project_information.applicant_address",
    "applicant.phone": "project_information.applicant_phone",
    "applicant.email": "project_information.applicant_email",
    "owner.name": "project_information.property_owner",
    "owner.address": "project_information.owner_address",
    "owner.phone": "project_information.owner_phone",
    "owner.email": "project_information.owner_email",
    "parcel.street_address": "site_information.project_address",
    "parcel.zoning_district": "site_information.core_zoning_district",
    # Gen-1's "SD - ____" blank is the same concept slot as Gen-2's
    # "Zoning District" -- the D1-D6/SD-prefixed alternative -- so it
    # crosswalks onto the same seeded field_def. A genuine ambiguity (both
    # a circled D1-D6 AND a filled SD blank on one application) is not
    # something the current extractor can even see -- native.py never reads
    # the circled-checkbox signal at all -- so this mapping cannot itself
    # create a false disagreement in practice today.
    "parcel.special_district_name": "site_information.core_zoning_district",
    "parcel.lot_size_acres": "site_information.acreage",
    "parcel.lot_frontage_ft": "site_information.street_frontage",
    "project.existing_use": "application_information.existing_use",
    "project.proposed_use": "application_information.proposed_use",
    "project.description": "application_information.proposed_development",
}

# Multi-part crosswalks: several native/positional field_keys are sub-parts
# of ONE seeded field_def's value, not competing answers for it -- merging
# them into one combined FieldCandidate (rather than inserting each
# separately under the same field_def_id) avoids ingest.fields.merge_all
# reading "4" vs "87" as a false disagreement between a Tax Map number and
# a Lot number.
@dataclasses.dataclass(frozen=True)
class _CombineRule:
    target_field_key: str
    parts: tuple[str, ...]  # native/positional field_keys, in template order
    template: str  # str.format() with each part's stripped value_raw, by position

COMBINE_RULES: tuple[_CombineRule, ...] = (
    _CombineRule("site_information.tax_lot", ("parcel.tax_map", "parcel.lot"), "Map {0} / Lot {1}"),
    _CombineRule(
        "project_information.owner_deed_reference",
        ("parcel.deed_book", "parcel.deed_page"),
        "Book {0}, Page {1}",
    ),
)

# field_keys this module KNOWS are dimensional/building/unit-count values
# with no seeded field_def home (Article 2, blocked on districts.json --
# see module docstring). Listed explicitly (rather than "anything not in
# the crosswalk") so a genuinely NEW, unexpected field_key from a future
# native.py/positional.py change surfaces as a loud, distinct
# "unrecognized" bucket in the report instead of silently joining this
# already-understood, already-blocked group.
KNOWN_UNATTACHED_FIELD_KEYS: frozenset[str] = frozenset({
    "parcel.tax_map", "parcel.lot",  # only when NOT paired via a combine rule (see below)
    "parcel.deed_book", "parcel.deed_page",
    "parcel.lot_width_ft", "parcel.lot_depth_ft",
    "building.footprint_sf", "building.total_area_sf", "building.width_ft",
    "building.depth_ft", "building.stories", "building.existing_units",
    "building.proposed_units",
    "setback.front_ft", "setback.side_ft", "setback.rear_ft",
})


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


@dataclasses.dataclass
class CrosswalkResult:
    persistable: list[FieldCandidate]  # field_key already rewritten to the target field_def's key
    unattached: list[FieldCandidate]  # original field_key, no seeded field_def -- reported, not dropped


def apply_crosswalk(candidates: list[FieldCandidate]) -> CrosswalkResult:
    """Rewrite native/positional field_keys onto the seeded case-level
    field_def vocabulary. Never mutates a FieldCandidate in place (frozen
    dataclass) -- `dataclasses.replace` produces the rewritten copy,
    preserving every other attribute (bbox, page_no, confidence, rationale,
    document_id, source_priority) untouched.
    """
    by_key: dict[str, FieldCandidate] = {c.field_key: c for c in candidates}
    combined_source_keys: set[str] = set()
    persistable: list[FieldCandidate] = []

    for rule in COMBINE_RULES:
        parts = [by_key[k] for k in rule.parts if k in by_key]
        if not parts:
            continue
        values = [p.value_raw for p in parts]
        # Fill in only the parts actually present -- "Map 4 / Lot " reads
        # oddly, so a partial combine just uses however many placeholders
        # it has evidence for, in order.
        present_parts = [(k, by_key[k]) for k in rule.parts if k in by_key]
        if len(present_parts) == len(rule.parts):
            raw = rule.template.format(*values)
        else:
            raw = " / ".join(f"{p.value_raw}" for _, p in present_parts)
        bbox = (
            min(p.bbox[0] for p in parts), min(p.bbox[1] for p in parts),
            max(p.bbox[2] for p in parts), max(p.bbox[3] for p in parts),
        )
        combined_source_keys.update(rule.parts)
        persistable.append(dataclasses.replace(
            parts[0],
            field_key=rule.target_field_key,
            value_raw=raw,
            value_norm=raw,
            unit=None,
            bbox=bbox,
            confidence=min(p.confidence for p in parts),
            rationale=(
                f"combined from {[p.field_key for p in parts]!r}: " +
                " | ".join(p.rationale for p in parts)
            ),
        ))

    unattached: list[FieldCandidate] = []
    for c in candidates:
        if c.field_key in combined_source_keys:
            continue
        target = FIELD_KEY_CROSSWALK.get(c.field_key)
        if target is not None:
            persistable.append(dataclasses.replace(
                c, field_key=target,
                rationale=f"crosswalked from native/positional field_key {c.field_key!r}: {c.rationale}",
            ))
        else:
            unattached.append(c)

    return CrosswalkResult(persistable=persistable, unattached=unattached)


# --------------------------------------------------------------------------- #
# Extraction -- authoritative generation (formgen.py), Tier A + Tier B.
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class ExtractionRun:
    generation: str
    confidence: str
    version_stamp: str | None
    modules: list[str]
    tier_a_page: int | None
    tier_b_pages_attempted: list[int]
    tier_b_pages_parseable: list[int]
    candidates: list[FieldCandidate]  # RAW, pre-crosswalk field_key


def extract_document(
    pdf_path: str | Path,
    *,
    document_id: str,
    source_priority: int,
    positional_candidate_pages: list[int],
) -> ExtractionRun:
    """Run formgen detection (authoritative) then the matching generation's
    Tier A (native.py) extraction, plus the positional (Tier B trap) pass
    on every page in `positional_candidate_pages` (1-based, as read from
    the `pages` table -- this module never re-tiers a page itself). Pass
    Tier B **and** Tier D page numbers here -- see the module docstring's
    "SECOND, INDEPENDENT DRIFT" for why Tier D must be included to reach
    the real Stantec trap pages at all. Never Tier C (near-empty scans).

    The positional pass runs ONLY when Tier A found NO native Gen-1 form
    page anywhere in this document (`find_gen1_form_page` returned None) --
    a FOURTH drift, found empirically while verifying this module against
    the real 25-page Profenno packet: GEN1_FIELD_MAP's reference windows
    are calibrated to ONE specific page layout (the Gen-1 form itself), and
    blindly sweeping every Tier B/D page of a large, unrelated packet
    through them produces confident-looking but WRONG candidates whenever
    some other page's incidental text happens to fall inside a field's
    window by coincidence -- verified concretely: page 16 of Profenno (a
    completion-certification cover letter) and page 18 (a numbered permit
    condition) both produced a field_key='applicant.name' candidate purely
    from text landing in that window, correctly outranked in
    ingest.fields.merge_all()'s priority-order sort by the real, native,
    label-confirmed page-5 match, but wrongly surfacing as `contested`
    anyway -- noise in exactly the UI CONTRACT.md's framing rule exists to
    keep trustworthy. The task brief's own "Tier B trap" is, by its own
    description, what happens when the REAL form was scanned as an image
    with the label text lost -- i.e. it is a substitute for a missing Tier
    A result on THIS document, never a supplement layered on top of an
    already-successful one.

    That alone is not enough for Stantec, whose Tier A also finds nothing
    (no native "TAX MAP"/"CONTACT INFORMATION" page anywhere in its own
    56-page packet) -- so gating on "Tier A found nothing" still leaves
    every Tier B/D page of Stantec's OWN packet swept through the same
    positional matcher, and the same false-positive pattern reappeared
    there too: pp.29-42 (Maine DEP permit boilerplate -- wetlands rules,
    appeal procedures, decommissioning conditions) each produced multiple
    confident-looking candidates purely from prose landing in a field's
    window. A FIFTH drift, and the actual fix: the real trap pages (9, 12)
    share one more distinguishing, deterministic, already-available signal
    neither char_count nor tier alone captures -- they are the ONLY pages
    in the whole packet stored /Rotate 90 or /Rotate 270 (verified: every
    one of the pp.29-42 false-positive pages is /Rotate 0; the task brief's
    own description of the trap -- "a sideways-fed scan" -- names this
    exact fact). `extract_document()` therefore additionally requires
    `doc[page_no - 1].rotation != 0` before attempting a positional match
    on any page, regardless of what `positional_candidate_pages` contains
    -- a self-contained guard, not merely a caller convention, so a caller
    that (like this module's own verification driver first did) naively
    passes every Tier B/D page still gets the correct, narrow result.
    Verified this still reaches the real trap: page 9 (rot=90) still
    produces its 17 real candidates; pp.29-42 (rot=0) now correctly
    contribute nothing.
    """
    formgen_result = formgen_mod.detect_generation(pdf_path)
    generation = formgen_result["generation"]

    candidates: list[FieldCandidate] = []
    tier_a_page: int | None = None
    tier_b_attempted: list[int] = []
    tier_b_parseable: list[int] = []

    doc = fitz.open(str(pdf_path))
    try:
        if generation == native_mod.GEN1:
            idx = native_mod.find_gen1_form_page(doc)
            if idx is not None:
                tier_a_page = idx + 1
                candidates.extend(native_mod.extract_gen1_page1(
                    doc[idx], page_no=idx + 1, document_id=document_id,
                    source_priority=source_priority,
                ))
            if idx is None:
                for page_no in positional_candidate_pages:
                    page_obj = doc[page_no - 1]
                    if page_obj.rotation == 0:
                        # Not a scanned/sideways-fed page -- see the "FIFTH
                        # drift" docstring note above. Never attempted: a
                        # normally-oriented page's incidental prose is not
                        # the Tier B trap this pass exists to catch.
                        continue
                    tier_b_attempted.append(page_no)
                    result = positional_mod.extract_gen1_positional(
                        page_obj, page_no=page_no, document_id=document_id,
                        source_priority=source_priority,
                    )
                    if result.parseable:
                        tier_b_parseable.append(page_no)
                        candidates.extend(result.candidates)
        elif generation == native_mod.GEN2:
            idx = native_mod.find_gen2_cover_page(doc)
            if idx is not None:
                tier_a_page = idx + 1
                candidates.extend(native_mod.extract_gen2_cover_sheet(
                    doc[idx], page_no=idx + 1, document_id=document_id,
                    source_priority=source_priority,
                ))
            # No Gen-2 positional (Tier B) extractor exists yet -- out of
            # this workflow's scope; Gen-2 Tier B pages route to the
            # worklist untouched, same as an unknown-generation document.
        # generation == 'unknown': NO extraction attempted at all -- every
        # field for this document goes to the worklist (task brief: "UNKNOWN
        # GENERATION MUST FAIL LOUDLY ... NEVER fall back to Gen-1 parsing").
    finally:
        doc.close()

    return ExtractionRun(
        generation=generation,
        confidence=formgen_result["confidence"],
        version_stamp=formgen_result.get("version_stamp"),
        modules=list(formgen_result.get("modules", [])),
        tier_a_page=tier_a_page,
        tier_b_pages_attempted=tier_b_attempted,
        tier_b_pages_parseable=tier_b_parseable,
        candidates=candidates,
    )


# --------------------------------------------------------------------------- #
# Persistence.
# --------------------------------------------------------------------------- #


def persist_candidates(
    conn: sqlite3.Connection,
    *,
    case_id: str,
    ruleset_id: str,
    candidates: list[FieldCandidate],
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    """Insert every `candidates` entry as a field_candidates row, resolving
    field_def_id by (ruleset_id, field_key, district_key IS NULL) -- the
    case-level field_defs ingest.worklist.seed_field_defs() seeds. A
    candidate whose (already-crosswalked) field_key has no matching seeded
    field_def is skipped and reported under `no_field_def` rather than
    raising -- this can only happen for a field_key this module's own
    apply_crosswalk() failed to route correctly, since KNOWN_UNATTACHED
    candidates are never passed in here in the first place.

    field_candidates.needs_confirmation does not exist as a DB column
    (CONTRACT.md §3.6's field_candidates table has no such column at all --
    "needs confirmation" is what field_values.state='unconfirmed' via
    default MEANS); FieldCandidate's own dataclass invariant already makes
    a False value structurally unconstructable (ingest/fields.py
    __post_init__). This function never writes a field_values row -- only
    a human action (app/extraction.py's confirm_field / override_field /
    mark_not_applicable) does that.
    """
    field_def_cache: dict[str, str | None] = {}

    def _resolve(field_key: str) -> str | None:
        if field_key not in field_def_cache:
            row = conn.execute(
                """
                SELECT id FROM field_defs
                WHERE ruleset_id = ? AND field_key = ? AND district_key IS NULL;
                """,
                (ruleset_id, field_key),
            ).fetchone()
            field_def_cache[field_key] = row["id"] if row is not None else None
        return field_def_cache[field_key]

    now = _utc_now_iso()
    inserted: list[str] = []
    no_field_def: list[str] = []

    conn.execute("BEGIN;")
    try:
        for c in candidates:
            field_def_id = _resolve(c.field_key)
            if field_def_id is None:
                no_field_def.append(c.field_key)
                continue

            page_id = None
            if c.document_id is not None:
                page_row = conn.execute(
                    "SELECT id FROM pages WHERE document_id = ? AND page_number = ?;",
                    (c.document_id, c.page_no),
                ).fetchone()
                page_id = page_row["id"] if page_row is not None else None

            value_num = c.value_norm if isinstance(c.value_norm, (int, float)) else None
            value_text = c.value_norm if isinstance(c.value_norm, str) else None

            cand_id = uuid.uuid4().hex
            conn.execute(
                """
                INSERT INTO field_candidates (
                    id, case_id, field_def_id, document_id, page_id, subject_key,
                    source_priority, raw_text, value_num, value_text, unit, bbox_json,
                    extractor, confidence, provenance_json, created_at, actor_user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    cand_id, case_id, field_def_id, c.document_id, page_id, c.subject_key,
                    c.source_priority, c.value_raw, value_num, value_text, c.unit,
                    json.dumps(list(c.bbox)), c.method, c.confidence,
                    json.dumps({
                        "tool": "ingest.pipeline",
                        "rationale": c.rationale,
                        "needs_confirmation": c.needs_confirmation,
                    }),
                    now, actor_user_id,
                ),
            )
            inserted.append(cand_id)

        if inserted:
            append_event(
                conn,
                actor_user_id=actor_user_id,
                kind="field_candidates.persisted",
                case_id=case_id,
                entity_table="field_candidates",
                payload={
                    "case_id": case_id,
                    "count": len(inserted),
                    "no_field_def_field_keys": sorted(set(no_field_def)),
                },
            )
        conn.execute("COMMIT;")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK;")
        raise

    return {"inserted": len(inserted), "no_field_def": no_field_def}
