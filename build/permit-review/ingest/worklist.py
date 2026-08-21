"""ingest/worklist.py — the absence worklist (W4 task brief, verbatim: "a
first-class output, not a byproduct"). Implements CONTRACT.md §3.6's
`field_defs` / `field_candidates` / `field_values` contract for the
case-level fields in a real decision's Project Information / Site
Information / Application Information blocks.

THE CENTRAL DESIGN PRINCIPLE this module exists to serve (task brief,
verbatim): "~30% of the fields in a real decision are not in the
application at all." Those are not gaps to paper over -- they are
`field_values` rows with `state='not_in_application'`, materialized here
and grouped by WHERE a human must go get them. This module never guesses a
value and never promotes a field_candidates row into a field_values row
itself (CONTRACT.md's framing rule: "the operator confirms; the app never
silently promotes a candidate to a value") -- it only asserts the one fact
that is NOT a judgment call: this field has zero candidates from any
document in this case, as of right now.

THE CANONICAL FIELD SET (FIELD_DEF_SEED, below) is transcribed VERBATIM
from five real "Findings of Fact and Conclusions of Law" documents under
`docs/Findings of Fact and Conclusions of Law/` -- not from the application
forms -- because the task brief's instruction is specific: seed the labels
that get "rendered verbatim into the generated document" this app produces
(a Findings draft), not the labels printed on whatever form the applicant
happened to fill out. Read, side by side:
    5.A.x1 ... (Blood and Sons) 2024.10.15 FoF & CoL.pdf                 (Gen-1 case)
    4.B2. ... (Verney) 2025.04.13 FoF & CoL.pdf                          (Gen-2 case)
    4.A2. ... (Buehner) Shoreland Only FoF & CoL 2025.03.18.pdf          (Gen-2 case)
    745 US Route 1 (Midcoast Solar, LLC) FoF & CoL 2024.03.14.pdf        (Gen-1 case, agent variant)
    M003, L059 ... (Shattuck), Subdivision FoF & CoL 2025.12.18.pdf      (Gen-2 case, multi-owner variant)
the "Project Information" / "Site Information" / "Application Information"
labels are near-identical across all five (a handful of drafting variants
noted inline below); FIELD_DEF_SEED is the union, in the order they print.

FORM-GENERATION AWARENESS, WITHOUT BUILDING THE FULL DETECTOR: this
workflow's task list separates "form-generation and module-set detection"
from "the absence worklist" as two different pieces of work. This module
does not do vision, OCR, or module-set detection -- but it cannot correctly
label an absence as "structural" (the form has no such field) versus
"applicant left it blank" (the form asks, nobody answered) without SOME
notion of which generation applied, so it carries the narrow, text-only
half of that job: detect_form_generation() applies the task brief's own
two deterministic fingerprints to whatever native/embedded text is already
on hand (Tier A/B pages -- see ingest/triage.py) and returns "unknown",
never a guess, the moment the signal is not there (e.g. a pure-scan
application with no text layer at all -- case_form_generation() below
degrades to "unknown" gracefully in exactly that case, per the task
brief's own "UNKNOWN GENERATION MUST FAIL LOUDLY" instruction). A caller
that already knows the generation by some other means (an operator's
confirmation, a later OCR/vision pass) may pass `form_generation=` to
worklist() directly rather than relying on the text-only detector.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from app.audit import append_event
from app.citation import Citation

# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #

#: CONTRACT.md task brief: "Group the worklist by WHERE the value must come
#: from." Mirrors app/migrations/0008_field_defs_worklist.sql's
#: field_defs.source_category CHECK exactly.
SOURCE_CATEGORIES: frozenset[str] = frozenset({
    "applicant", "registry", "gis", "plan_survey", "staff", "post_submittal",
})

#: Display labels for each category, in the task brief's own wording, used
#: as the worklist's group headings.
SOURCE_CATEGORY_LABELS: dict[str, str] = {
    "applicant": "The applicant",
    "registry": "Registry of Deeds / Assessing",
    "gis": "GIS or map",
    "plan_survey": "A plan or survey sheet",
    "staff": "Staff determination",
    "post_submittal": "Post-submittal record",
}

FormGeneration = Literal["gen1", "gen2", "unknown"]

#: field_values.state this module ever writes. Every other state in
#: CONTRACT.md §3.6's CHECK ('confirmed', 'overridden', 'not_applicable',
#: 'contested') is a HUMAN decision this module must never make or touch.
STATE_NOT_IN_APPLICATION = "not_in_application"

#: field_values states that mean "a human already resolved this" -- once a
#: field_values row reaches one of these, worklist() leaves it alone even
#: though it still (correctly) has zero field_candidates rows. Excludes
#: 'unconfirmed' and 'contested': a candidate exists behind those, so they
#: cannot arise for a field this module is even considering (see the
#: candidate-count guard in worklist()), but they are listed for clarity of
#: what is deliberately NOT in this set.
_RESOLVED_STATES: frozenset[str] = frozenset({"confirmed", "overridden", "not_applicable"})


# --------------------------------------------------------------------------- #
# FIELD_DEF_SEED — the canonical case-level field set.
#
# Columns, in order:
#   panel_key, panel_title  -- the FoF & CoL block this prints under,
#                              verbatim ("Project Information" /
#                              "Site Information" / "Application
#                              Information").
#   field_key   -- f"{panel_key}.{slug(label)}", unique within a ruleset
#                  (matches the Article-2 dimensional convention,
#                  CONTRACT.md §4.2's field_key = panel_key + "." + slug(label)).
#   label       -- rendered verbatim into the generated Findings draft.
#   value_kind  -- field_defs.value_kind CHECK ('dimension','count','text',
#                  'boolean','use','enum'). Existing/Proposed Use use 'use'
#                  (a taxonomy term, not free text); everything else here is
#                  'text' -- these are administrative/bookkeeping fields,
#                  not §4.2 Article-2 dimensional standards (a §4.2 Acreage
#                  or Street Frontage figure is never checked against a
#                  min/max the way a District's LOT DIMENSIONS panel is;
#                  field_defs.unit's CHECK ('ft','pct','stories','units',
#                  'sqft') has no 'acres' member for exactly this reason --
#                  forcing these into 'dimension' would either violate that
#                  CHECK or silently misstate the unit).
#   source_category -- SOURCE_CATEGORIES; WHERE this value comes from when
#                  the application does not supply it.
#   gen1_absent, gen2_absent -- 1 when that generation's form structurally
#                  has NO field for this label (verified against the real
#                  Gen-1 field list in this workflow's own task brief, and
#                  against the real Gen-2 Cover Sheet / Shoreland Zoning
#                  Form / Building Form images extracted from the Dalton
#                  (M002/L053) and Morrissey (M011/L046-A) applications
#                  under docs/).
#
# NOTES ON EACH ROW'S source_category / gen*_absent CALL, where it is not
# self-evident from the field name alone:
#
#   Owner Deed Reference -- registry, gen1_absent=1, gen2_absent=0. THE
#     canonical example (task brief, design principle #2, verbatim): "The
#     Gen-1 form has no deed field, so the deed reference comes from the
#     Registry." Gen-2's Cover Sheet prints `Deed Book: ___  Page: ___`
#     (verified: Dalton's handwritten "6106" / "101", Morrissey's "5637" /
#     "53") -- so on a Gen-2 case an empty Owner Deed Reference is the
#     applicant simply leaving a present field blank, not a structural gap.
#     source_category stays 'registry' either way: even a filled-in
#     applicant self-report is not the authoritative source for a legal
#     record citation -- the Registry of Deeds is -- so a human confirming
#     this field should always be pointed there, filled in or not.
#
#   Applicant's Agent -- applicant, gen1_absent=1, gen2_absent=0. Gen-1's
#     own field list (this workflow's task brief) has no Agent/Contractor
#     block at all. Gen-2's Cover Sheet has one ("Agent/Contractor (if
#     applicable)"), routinely left blank when there is no agent (verified:
#     both Dalton's and Morrissey's real Gen-2 Cover Sheets ship it empty) --
#     that blank is a true fact ("no agent"), not a missing one; a later
#     workflow's field-extraction pass is expected to read the empty
#     Gen-2 field as a candidate value_text="" / "none" rather than
#     leaving no candidate at all. Until it does, this module correctly
#     treats a candidate-less Agent field as still-needed on a Gen-2 case
#     too (see the Verney/Buehner FoF pattern: "Applicant's Agent: none" is
#     a printed, resolved fact, not a blank).
#
#   Core Zoning District -- gis, gen1_absent=0, gen2_absent=0. Present as a
#     direct applicant self-report on BOTH generations (Gen-1: "District
#     circle one D1-D6 or SD-___"; Gen-2 Cover Sheet: "Zoning District:
#     ___"), so it is rarely a true worklist item -- but when the
#     application is silent (or the self-report needs confirming), the
#     authoritative source is the Town's official District Map / GIS layer,
#     never the applicant's own say-so, hence the 'gis' category even
#     though gen*_absent are both 0.
#
#   Shoreland Zoning -- gis, gen1_absent=1, gen2_absent=0. Absent from
#     Gen-1's own field list entirely. Present on Gen-2 ONLY when the
#     application includes the Shoreland Zoning Form module (task brief:
#     "MODULAR: a required Cover Sheet plus a-la-carte modules") -- a
#     module-conditional presence this two-flag model cannot capture
#     precisely (a Gen-2 case with no shoreland module is not "the form
#     forgot it," it is "not applicable here," which is field_values'
#     `not_applicable` state, a human call this module never makes). This
#     is a documented approximation, not a bug: a later refinement could key
#     Shoreland Zoning's absence off the case's detected module set
#     (a sibling W4 deliverable) rather than generation alone.
#
#   Existing Development -- plan_survey, gen1_absent=1, gen2_absent=1. No
#     field on either real form literally asks for a free-text description
#     of existing site conditions (Gen-2's closest field is the numeric
#     "Number of Existing Dwelling Units"); every FoF & CoL sample states it
#     as an observed fact ("None – undeveloped, forested"; "One existing
#     Residential building and one existing General Accessory building"),
#     which is exactly what a submitted plan/survey sheet shows.
#
#   Proposed Use -- staff, gen1_absent=0, gen2_absent=0. Design principle
#     #3, verbatim: "use-taxonomy mapping is staff judgement." A raw
#     candidate value IS directly extractable from either form (both ask
#     for it), but the value that is actually PRINTED in every FoF & CoL
#     sample read for this seed is already the matched Article-6/7/8 use
#     category name verbatim ("Industrial, Artisan"; "Retail & Service,
#     Heavy"; "Utilities & Services") -- not necessarily the applicant's own
#     words -- so a human must confirm the taxonomy match even when a raw
#     candidate exists. (Existing Use is left 'applicant': every sample read
#     states it as a plain, low-ambiguity description of what is already
#     there -- "Residence", "Undeveloped" -- with no taxonomy judgment call
#     evident in how it is rendered.)
#
#   Documents Included -- staff, gen1_absent=1, gen2_absent=1. Appears in
#     only one of the five FoF & CoL samples read (Blood & Sons) and is a
#     staff-compiled list of what is in the case's own `documents` table,
#     not a value any applicant fills in on either form.
# --------------------------------------------------------------------------- #

_PROJECT = ("project_information", "Project Information")
_SITE = ("site_information", "Site Information")
_APPLICATION = ("application_information", "Application Information")

FIELD_DEF_SEED: tuple[dict[str, Any], ...] = (
    # --- Project Information -----------------------------------------
    {"panel": _PROJECT, "label": "Applicant", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _PROJECT, "label": "Applicant Address", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _PROJECT, "label": "Applicant Phone", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _PROJECT, "label": "Applicant Email", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _PROJECT, "label": "Property Owner", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _PROJECT, "label": "Owner Address", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _PROJECT, "label": "Owner Phone", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _PROJECT, "label": "Owner Email", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _PROJECT, "label": "Owner Deed Reference", "value_kind": "text",
     "source_category": "registry", "gen1_absent": 1, "gen2_absent": 0},
    {"panel": _PROJECT, "label": "Applicant's Agent", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 1, "gen2_absent": 0},

    # --- Site Information ----------------------------------------------
    {"panel": _SITE, "label": "Tax Lot", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _SITE, "label": "Project Address", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _SITE, "label": "Core Zoning District", "value_kind": "text",
     "source_category": "gis", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _SITE, "label": "Shoreland Zoning", "value_kind": "text",
     "source_category": "gis", "gen1_absent": 1, "gen2_absent": 0},
    {"panel": _SITE, "label": "Acreage", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _SITE, "label": "Street Frontage", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _SITE, "label": "Existing Development", "value_kind": "text",
     "source_category": "plan_survey", "gen1_absent": 1, "gen2_absent": 1},

    # --- Application Information ----------------------------------------
    {"panel": _APPLICATION, "label": "Application Date", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _APPLICATION, "label": "Documents Included", "value_kind": "text",
     "source_category": "staff", "gen1_absent": 1, "gen2_absent": 1},
    {"panel": _APPLICATION, "label": "Proposed Development", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _APPLICATION, "label": "Existing Use", "value_kind": "use",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _APPLICATION, "label": "Proposed Building/Structure Type", "value_kind": "text",
     "source_category": "applicant", "gen1_absent": 0, "gen2_absent": 0},
    {"panel": _APPLICATION, "label": "Proposed Use", "value_kind": "use",
     "source_category": "staff", "gen1_absent": 0, "gen2_absent": 0},
)


def _slug(label: str) -> str:
    s = label.casefold().replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


# --------------------------------------------------------------------------- #
# Small internal helpers -- match app/cases.py's own conventions.
# --------------------------------------------------------------------------- #


def _new_id() -> str:
    return uuid.uuid4().hex


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


class WorklistError(Exception):
    """Base for every error this module raises."""


class CaseNotFound(WorklistError, LookupError):
    def __init__(self, case_id: str):
        self.case_id = case_id
        super().__init__(f"no case with id {case_id!r}")


# --------------------------------------------------------------------------- #
# Seeding — field_defs.
# --------------------------------------------------------------------------- #


def seed_field_defs(
    conn: sqlite3.Connection, ruleset_id: str, *, actor_user_id: str | None = None,
) -> list[str]:
    """Idempotently insert FIELD_DEF_SEED's rows for `ruleset_id` (skipping
    any (ruleset_id, field_key) already present -- field_defs' own UNIQUE
    (ruleset_id, district_key, field_key) constraint, mirrored here so a
    second call is a silent no-op rather than an IntegrityError). Returns the
    field_key list of rows NEWLY inserted by this call (empty if the ruleset
    was already fully seeded).

    Every inserted row carries district_key=NULL (CONTRACT.md §3.6:
    "NULL = case-level, not district-scoped") and a Citation struct
    (citation_json is NOT NULL on every field_defs row) pointed at Article 7
    (Administration) -- these are application-intake bookkeeping fields, not
    an Article-2 dimensional standard, so there is no more specific numbered
    subsection to cite; the Citation still records which ruleset/scheme this
    row was seeded under, which is what provenance actually needs here.
    """
    ruleset_row = conn.execute(
        "SELECT ruleset_key, article_scheme FROM rulesets WHERE id = ?;", (ruleset_id,)
    ).fetchone()
    if ruleset_row is None:
        raise WorklistError(f"no ruleset with id {ruleset_id!r}")

    existing_keys = {
        row["field_key"]
        for row in conn.execute(
            "SELECT field_key FROM field_defs WHERE ruleset_id = ? AND district_key IS NULL;",
            (ruleset_id,),
        ).fetchall()
    }

    to_insert = []
    for sort_order, spec in enumerate(FIELD_DEF_SEED, start=10):
        panel_key, panel_title = spec["panel"]
        field_key = f"{panel_key}.{_slug(spec['label'])}"
        if field_key in existing_keys:
            continue
        citation = Citation(
            ruleset_key=ruleset_row["ruleset_key"],
            scheme=ruleset_row["article_scheme"],
            article=7,
            label=spec["label"],
        )
        to_insert.append((sort_order * 10, panel_key, panel_title, field_key, citation, spec))

    if not to_insert:
        return []

    now = _utc_now_iso()
    conn.execute("BEGIN;")
    try:
        inserted_keys: list[str] = []
        for sort_order, panel_key, panel_title, field_key, citation, spec in to_insert:
            conn.execute(
                """
                INSERT INTO field_defs (
                    id, ruleset_id, district_key, field_key, panel_key, panel_title, label,
                    value_kind, unit, applicability, required_json, raw_value, footnote_refs,
                    unresolved, citation_json, sort_order, source_category,
                    typically_absent_gen1, typically_absent_gen2, created_at, actor_user_id
                ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, NULL, 'established', NULL, NULL, NULL,
                          0, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    _new_id(), ruleset_id, field_key, panel_key, panel_title, spec["label"],
                    spec["value_kind"], json.dumps(citation.__dict__, sort_keys=True), sort_order,
                    spec["source_category"], spec["gen1_absent"], spec["gen2_absent"], now,
                    actor_user_id,
                ),
            )
            inserted_keys.append(field_key)

        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="field_defs.seeded",
            payload={"ruleset_id": ruleset_id, "field_keys": inserted_keys},
            entity_table="field_defs",
        )
        conn.execute("COMMIT;")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK;")
        raise

    return inserted_keys


# --------------------------------------------------------------------------- #
# Form-generation detection — text-only, deterministic, "unknown" over a guess.
# --------------------------------------------------------------------------- #

# Task brief, verbatim: "Detect by the literal typo string 'OFFICE
# ADMINSTRATION USE ONLY' (misspelled in the original -- that typo is the
# reliable fingerprint)." Whitespace-tolerant (a real PDF text layer can
# split a run of spaces oddly) and case-insensitive (the same fingerprint
# read off a header-band OCR pass, a later workflow's job, will not
# reliably preserve case).
_GEN1_FINGERPRINT_RE = re.compile(r"OFFICE\s+ADMINSTRATION\s+USE\s+ONLY", re.IGNORECASE)

# Task brief: "Detect by 'PLANNING APPLICATION' plus a footer version stamp
# matching v\.\d{4}\.\d{2}\.\d{2} (observed: v.2024.09.26)." BOTH signals
# are required -- "PLANNING APPLICATION" alone is not a strong enough
# fingerprint (it is also this app's own generic English description of
# what a permit application IS), so a lone title match without the
# version stamp does not resolve to "gen2".
_GEN2_TITLE_RE = re.compile(r"PLANNING\s+APPLICATION", re.IGNORECASE)
_GEN2_VERSION_STAMP_RE = re.compile(r"v\.\d{4}\.\d{2}\.\d{2}")


def detect_form_generation(text: str) -> FormGeneration:
    """Pure, deterministic, text-only. Applies the task brief's own two
    fingerprints and returns "unknown" -- never a guess -- whenever the
    signal is absent, contradictory, or `text` is empty (a pure-scan page
    with no text layer, or a page that simply is not the cover/first page
    of the application). CONTRACT.md §1 S7: an ambiguity here is reported,
    never resolved by a heuristic tiebreak.
    """
    if not text or not text.strip():
        return "unknown"

    is_gen1 = bool(_GEN1_FINGERPRINT_RE.search(text))
    is_gen2 = bool(_GEN2_TITLE_RE.search(text)) and bool(_GEN2_VERSION_STAMP_RE.search(text))

    if is_gen1 and is_gen2:
        return "unknown"  # contradictory signals in the same text -- never guess
    if is_gen1:
        return "gen1"
    if is_gen2:
        return "gen2"
    return "unknown"


def case_form_generation(conn: sqlite3.Connection, case_id: str) -> FormGeneration:
    """Best-effort generation detection for a real case, using ONLY text
    already sitting on tier A/B pages (ingest/triage.py) of documents this
    case's upload pipeline tagged as the application form itself
    (doc_role='application_form' or kind='form') -- never OCR, never
    vision, matching this workflow's own "NO OCR of handwriting" / "NO
    VISION" scope line. A pure-scan application (no native text layer at
    all -- ingest/triage.py never populates pages.text for one) correctly
    falls through to "unknown" here, which is the honest answer per the
    task brief's own guidance, not a bug: "If you cannot determine the
    generation deterministically, report UNKNOWN."
    """
    rows = conn.execute(
        """
        SELECT p.text
        FROM pages p
        JOIN documents d ON d.id = p.document_id
        WHERE d.case_id = ?
          AND d.superseded_by IS NULL
          AND (d.doc_role = 'application_form' OR d.kind = 'form')
          AND p.tier IN ('A', 'B')
          AND p.text IS NOT NULL
        ORDER BY d.created_at, p.page_number;
        """,
        (case_id,),
    ).fetchall()
    combined = "\n".join(r["text"] for r in rows if r["text"])
    return detect_form_generation(combined)


# --------------------------------------------------------------------------- #
# The worklist itself.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class WorklistItem:
    field_def_id: str
    field_key: str
    label: str
    panel_key: str
    panel_title: str
    source_category: str
    source_category_label: str
    structurally_absent: bool | None  # None = form generation unknown, not scored
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "field_def_id": self.field_def_id,
            "field_key": self.field_key,
            "label": self.label,
            "panel_key": self.panel_key,
            "panel_title": self.panel_title,
            "source_category": self.source_category,
            "source_category_label": self.source_category_label,
            "structurally_absent": self.structurally_absent,
            "reason": self.reason,
        }


def _reason_for(label: str, generation: FormGeneration, structurally_absent: bool | None) -> str:
    if generation == "unknown":
        return (
            f"Form generation could not be determined for this case, so it is unknown whether "
            f"{label!r} is structurally absent from the submitted form or simply left blank; "
            f"routed to the worklist either way."
        )
    gen_name = "Gen-1 (Zoning Permit Application)" if generation == "gen1" else "Gen-2 (Planning Application)"
    if structurally_absent:
        return f"The {gen_name} form has no field for {label!r}; this value must come from elsewhere."
    return f"The {gen_name} form asks for {label!r}, but no source in this case has supplied a value yet."


def worklist(
    conn: sqlite3.Connection,
    case_id: str,
    *,
    actor_user_id: str | None = None,
    form_generation: FormGeneration | None = None,
) -> dict[str, Any]:
    """The absence worklist for one case (CONTRACT.md §3.6; this
    workflow's task brief).

    For every case-level field_def (district_key IS NULL) on this case's
    ruleset (seeding it first via seed_field_defs() if not already done --
    idempotent, safe to call every time):
      - if this case has at least one field_candidates row for it, it is
        NOT a worklist item (there is evidence; a human still has to
        confirm it, but that is the operator-confirm UI's job, not this
        module's);
      - otherwise, if an existing field_values row for it already carries
        a HUMAN-resolved state (confirmed / overridden / not_applicable),
        it is likewise NOT a worklist item -- a human already decided this,
        and this module never overwrites that decision;
      - otherwise it IS a worklist item: a field_values row with
        state='not_in_application' is written (if one is not already
        there) and the field is included in the returned worklist, grouped
        by source_category.

    `form_generation`, if given, overrides case_form_generation()'s
    text-only best-effort detection -- the escape hatch for a caller that
    already knows the generation by some other means (an operator's
    confirmation; a later OCR/vision pass on a pure-scan application this
    module cannot read on its own).

    Raises CaseNotFound if `case_id` does not exist. Writes nothing on
    failure (CONTRACT.md §1 S1).
    """
    case_row = conn.execute(
        "SELECT id, ruleset_id, label FROM cases WHERE id = ?;", (case_id,)
    ).fetchone()
    if case_row is None:
        raise CaseNotFound(case_id)

    ruleset_id = case_row["ruleset_id"]
    seed_field_defs(conn, ruleset_id, actor_user_id=actor_user_id)

    generation: FormGeneration = form_generation or case_form_generation(conn, case_id)

    field_defs = conn.execute(
        """
        SELECT * FROM field_defs
        WHERE ruleset_id = ? AND district_key IS NULL
        ORDER BY sort_order;
        """,
        (ruleset_id,),
    ).fetchall()

    now = _utc_now_iso()
    items: list[WorklistItem] = []
    newly_materialized: list[str] = []

    conn.execute("BEGIN;")
    try:
        for fd in field_defs:
            candidate_count = conn.execute(
                "SELECT COUNT(*) AS n FROM field_candidates WHERE case_id = ? AND field_def_id = ?;",
                (case_id, fd["id"]),
            ).fetchone()["n"]
            if candidate_count > 0:
                continue  # evidence exists; not an absence

            existing_fv = conn.execute(
                """
                SELECT id, state FROM field_values
                WHERE case_id = ? AND field_def_id = ? AND subject_key IS NULL;
                """,
                (case_id, fd["id"]),
            ).fetchone()

            if existing_fv is not None and existing_fv["state"] in _RESOLVED_STATES:
                continue  # a human already resolved this; leave it alone, not a worklist item

            if generation == "gen1":
                structurally_absent: bool | None = bool(fd["typically_absent_gen1"])
            elif generation == "gen2":
                structurally_absent = bool(fd["typically_absent_gen2"])
            else:
                structurally_absent = None

            if existing_fv is None:
                conn.execute(
                    """
                    INSERT INTO field_values (
                        id, case_id, field_def_id, subject_key, chosen_candidate_id,
                        value_num, value_text, unit, state, override_reason,
                        contested_with_json, confirmed_by, confirmed_at,
                        created_at, updated_at, actor_user_id
                    ) VALUES (?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, NULL, NULL, NULL, NULL,
                              ?, ?, ?);
                    """,
                    (_new_id(), case_id, fd["id"], STATE_NOT_IN_APPLICATION, now, now, actor_user_id),
                )
                newly_materialized.append(fd["field_key"])

            items.append(WorklistItem(
                field_def_id=fd["id"],
                field_key=fd["field_key"],
                label=fd["label"],
                panel_key=fd["panel_key"],
                panel_title=fd["panel_title"],
                source_category=fd["source_category"],
                source_category_label=SOURCE_CATEGORY_LABELS.get(fd["source_category"], fd["source_category"]),
                structurally_absent=structurally_absent,
                reason=_reason_for(fd["label"], generation, structurally_absent),
            ))

        if newly_materialized:
            append_event(
                conn,
                actor_user_id=actor_user_id,
                kind="worklist.materialized",
                case_id=case_id,
                entity_table="field_values",
                payload={
                    "case_id": case_id,
                    "form_generation": generation,
                    "field_keys": newly_materialized,
                },
            )
        conn.execute("COMMIT;")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK;")
        raise

    total = len(field_defs)
    needed = len(items)
    grouped: dict[str, list[dict[str, Any]]] = {cat: [] for cat in SOURCE_CATEGORIES}
    for item in items:
        grouped.setdefault(item.source_category, []).append(item.as_dict())

    return {
        "case_id": case_id,
        "case_label": case_row["label"],
        "form_generation": generation,
        "summary": {
            "needed": needed,
            "total": total,
            "headline": f"{needed} of {total} fields still needed",
        },
        "items": [i.as_dict() for i in items],
        "grouped": grouped,
    }
