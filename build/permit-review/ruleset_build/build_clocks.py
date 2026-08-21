"""Builds rulesets/adopted/clocks.json and rulesets/<draft-key>/clocks.json --
the W3 statutory deadline clock data engine/deadlines.py loads at runtime.

This module is the ONE place the Article 7 (Administration) statutory clocks
are transcribed from Code prose into structured data (22 clocks as of the F3
coverage pass below; was 18 before it). Every clock's `citation` is validated
against the already-built rulesets/adopted/articles.json extraction (§4/§4.5's
"Runtime never re-parses repo source" posture, applied here at BUILD time
instead: the transcription is checked against the extracted tree, not against
the PDF/markdown directly) --  a wrong section number or a transcribed
day-count that doesn't match the extracted sentence text is a hard build
failure, not a silent guess (this mirrors CONTRACT.md §1 S7's "no silent
guessing" even though clocks.json itself is outside CONTRACT.md's four
ruleset schemas).

F3 COVERAGE ASSERTION (added alongside 4 new clocks -- §15.d.1, §23.d.2,
§23.d.3, §23.e.4 -- and one citation fix, administrative_appeal §23.b.1 ->
§23.d.1): `_assert_coverage()` walks every Article 7 sentence containing
"within ... days"/"within ... business days" and requires each to be either
a clock's `citation` above or a documented entry in `EXCLUDED_DUTIES`, so a
future edit that silently drops or forgets a statutory clock (the exact
defect class an adversarial review found in the original 18: three §23
appeal-track clocks existed in the Code text but nowhere in this file) fails
the build instead of shipping quietly. See `_assert_coverage`'s own
docstring/comment block below.

The draft-v0.22 clocks.json is DERIVED from the adopted one by the same
article renumbering app/citation.py uses (RENUM_ADOPTED_TO_DRAFT: Article 7
Administration -> draft Article 8), never hand-duplicated -- verified in this
project's Article 7/8 text dump, the two articles' Administration prose is
byte-identical modulo the article number, so a second hand-authored file
would be exactly the kind of duplicated arithmetic app/dates.py's own
docstring warns against ("a wrong meeting date is a wrong legal deadline").

F5 (2026-08, HARD-FINAL round, Finding 5). `use`/`expanded_use`
are real `cases.application_type` values with a real §15.d.1 decision clock
(`use_permit_decision`, added at F3) -- but the Code's OWN filing/appeal
machinery around that decision was never widened to match: §8.f.1 ("Decisions
will be filed by the Permitting Authority AS INDICATED FOR EACH TYPE OF
development review ... within five business days") and §23.d.1/.d.2/.d.3 (the
Appellate Authority's authority-neutral "any aggrieved party ... may file an
appeal" machinery) are not scoped to particular review tracks in their OWN
text -- they are the Code's general filing/appeal apparatus, reached by every
decision this app models, use/expanded_use included, exactly as §15.d.1
itself already commands ("... and file the decision with the Town Clerk").
`decision_filed_with_clerk`, `administrative_appeal`,
`administrative_appeal_hearing`, and `administrative_appeal_decision` now
list `use`/`expanded_use` in `applies_to`. `_assert_track_coverage()` (new,
run alongside `_assert_coverage()`) makes this a standing build gate: any of
these four track-agnostic clocks that omits a real review-track
application_type from `applies_to` fails the build, so this exact defect
class -- a statutorily-commanded clock silently missing for one review track
-- cannot ship quietly again. `reconsideration`/`reconsideration_decision`
are DELIBERATELY NOT widened -- see their own duty_kind_note/notes: §23.e is,
by its own text, specific to BOARD OF APPEALS decisions (variance,
administrative_appeal), and this app has no way to know, absent
rulesets/adopted/districts.json (BLOCKED -- see CONTRACT.md and this repo's
own standing instructions), whether the Board of Appeals is ever the
"designated permitting authority" §15.d.1 names for a Use Permit -- guessing
either way would be exactly the silent-guess CONTRACT.md §1 S7 forbids.

F6 (2026-08, HARD-FINAL round, Finding 6). `reconsideration_
decision`'s `predicate_event` narrows from `reconsideration_requested_at`
(the §23.e.1 REQUEST) to `reconsideration_voted_at` (the §23.e.2/.e.3 VOTE TO
RECONSIDER) -- matching §23.e.4's own conditional ("If the Board of Appeals
RECONSIDERS its original decision..."), not the mere fact that someone asked.
A request with no vote is not yet a duty at all under the clock's own
governing sentence. See that clock's duty_kind_note below and
engine/deadlines.py's CaseFacts.reconsideration_voted_at.

Run: `python -m ruleset_build.build_clocks` from build/permit-review/.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
RULESETS_DIR = APP_ROOT / "rulesets"

SCHEMA = "newcastle.clocks/1.1.0"

# --------------------------------------------------------------------------- #
# duty_kind -- the clock taxonomy (2026-08 repair round; dissolves adversarial-
# review findings N1 and the reconsideration half of N2 -- see
# engine/deadlines.py's module docstring for the full story). Every clock is
# classified from ITS OWN governing sentence in rulesets/adopted/articles.json
# -- who bears the obligation, and whether the verb is mandatory ("must"/
# "shall"/"will") or permissive ("may") -- never guessed. Each clock's
# `duty_kind_note` quotes that sentence so the classification is auditable.
#
#   municipal_duty   -- the Town (a named official or board) MUST act by a
#                        date. Can be MISSED. Only municipal_duty clocks feed
#                        engine/deadlines.py's presents_auto_approval_risk().
#   applicant_duty   -- a private applicant MUST act by a date (e.g. record an
#                        approved plan). Mandatory, so it CAN be genuinely
#                        missed, but it is never the Town's failure and never
#                        contributes to §8.d.1 auto-approval risk.
#   party_right      -- a private party MAY act within a window (file an
#                        appeal, request reconsideration). The window ELAPSES,
#                        unexercised, if unused -- it is never "missed" and
#                        never a Town failure.
#   conditional_duty -- a municipal duty that exists ONLY once a predicate
#                        event occurs (an appeal hearing exists only if an
#                        appeal was filed; a reconsideration decision only if
#                        reconsideration was requested). `predicate_event`
#                        names the CaseFacts field that must be recorded
#                        before the clock is anything other than
#                        NOT_TRIGGERED.
# --------------------------------------------------------------------------- #

DUTY_KINDS = ("municipal_duty", "applicant_duty", "party_right", "conditional_duty")

RENUM_ADOPTED_TO_DRAFT: dict[int, int] = {1: 1, 2: 2, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9}


class ClockBuildError(RuntimeError):
    """A clock's transcribed citation/day-count doesn't match the extracted
    Article 7 text, or a structural invariant (unique clock_key, valid
    basis/applies_to/db_kind) failed. Aborts the whole build -- no partial
    clocks.json is written (CONTRACT.md §1 S1's validate-all-then-write
    posture, applied here even though clocks.json is a build artifact, not a
    runtime write)."""


# --------------------------------------------------------------------------- #
# The 18 clocks, transcribed from the ADOPTED Article 7 (Administration) text
# in rulesets/adopted/articles.json. `days` is a magnitude; interpreted as
# literal days when basis is "calendar"/"business", and as MONTHS when basis
# is "months" (kept as one field named `days` per the W3 task brief's data
# shape: "{clock_key, citation, label, start_event, days, basis, applies_to,
# failure_consequence}").
#
# `applies_to` values are the case-review tracks app/migrations/
# 0002_case_tracking.sql widened cases.application_type to carry:
#   small_project_plan | large_project_plan | subdivision | special_permit |
#   variance | administrative_appeal (a Board-of-Appeals review of a CEO
#   action/inaction under §23, not a `cases.application_type` value -- see
#   engine/deadlines.py's module docstring).
#
# `db_kind` is the closest bucket in 0001_init.sql's deadlines.kind CHECK
# (('meeting','draft_due','completeness_review','notice','abutter_notice',
# 'decision_due','appeal','condition_compliance')) -- that enum predates this
# clock list and is not a legal citation, so several clocks share an
# imperfect-but-closest bucket; the exact statutory identity always survives
# in `rule_key`/`citation`, never collapsed into `db_kind` alone.
#
# `failure_consequence` carries the verbatim §8.d.1 sentence ONLY on clocks
# that are actually "hold a public hearing or take final action" deadlines --
# see engine/deadlines.py's AUTO_APPROVAL_TEXT and the reasoning in its
# module docstring for which clocks that is and isn't.
# --------------------------------------------------------------------------- #

AUTO_APPROVAL_TEXT = (
    "Failure by a Permitting Authority to hold a public hearing or take final "
    "action on an application within the maximum time requirement or "
    "permitted extensions, as applicable, must result in the approval of the "
    "application at the expiration of said time periods."
)

RECORDING_CONFLICT_NOTE = (
    "Article 7 §2.e.1 requires recording within 90 days of approval, while "
    "§8.f.5 and §12.j.1 require recording within six months. This app carries "
    "BOTH clocks with their own citations and never auto-generates a 90-day "
    "recording condition -- the conflict is surfaced on the case, not resolved "
    "by this software (CONTRACT.md §1 S7)."
)

CLOCKS_ADOPTED: list[dict[str, Any]] = [
    {
        "clock_key": "notice_mailed",
        "label": "Notice of application mailed",
        "citation": {"article": 7, "section": "5", "subsection": "c.3"},
        "source_text": (
            "Notices must be mailed within 7 business days of submission of an "
            "application."
        ),
        "start_event": "submitted_at",
        "satisfying_event": "notice_mailed_at",
        "days": 7,
        "basis": "business",
        "applies_to": [
            "large_project_plan", "subdivision",
            "special_permit", "variance",
        ],
        "duty_kind": "applicant_duty",
        "duty_kind_note": (
            "§5.c.3: \"The applicant must develop a notice containing pertinent information ...\" together with §5.c.4, \"Applicant must provide copy of mailing receipt to the Office of the Code Enforcement Officer\" -- the mailing duty runs to the applicant, not the Town; no Town official is ever named as the mailer. Not municipal_duty: a missed mailing is the applicant's own failure. LEDGER CORRECTION (2026-08-21, HARD-FINAL round): the transcribed clock text itself (\"Notices must be mailed within 7 business days...\") is, read alone, exactly as passive-voice/actor-unstated as §2.e.1 (subdivision_plat_recorded_90d, logged as DECISIONS-NEEDED D-0015) -- this entry originally declared the applicant-as-mailer reading \"not genuinely arguable\" and logged nothing, which was an inconsistent application of this project's own D-0015 rule (log a passive-voice actor inference; do not silently resolve it, however confident the inference feels). Now logged at DECISIONS-NEEDED D-0020 for consistency, though the evidentiary basis here IS stronger than D-0015's: \"the applicant must develop a notice...\" is the IMMEDIATELY PRECEDING sentence in the SAME §5.c.3 subsection (the notice the applicant just built is the thing that then \"must be mailed\"), not a cross-reference to a separate, only-parallel provision the way D-0015's §12.j.1/§8.f.5 inference is. See D-0020 for the full comparison."
        ),
        "failure_consequence": None,
        "db_kind": "notice",
        "notes": (
            "The literal text ties the 7-business-day window to 'submission of "
            "an application'. For hearing-based tracks (subdivision, the Large "
            "Project Plan Planning Board track, special permit, variance) "
            "notice content includes 'time, date and location of first "
            "scheduled meeting' (§5.c.3), which cannot be known before a "
            "hearing date is set -- see DECISIONS-NEEDED D-0009. "
            "FINDING 4 CORRECTION (2026-08-21, HARD-FINAL round): applies_to "
            "narrowed to drop 'small_project_plan'. Table 7.1 (NOTICES & "
            "PUBLIC HEARINGS, art7.6.e.7.1, §5.c.1/§6.b.1's own authority for "
            "which application types require notice/a hearing -- 'Application "
            "types that are not listed, do not require a Public Hearing') "
            "marks BOTH the Notice and Public Hearing columns blank for Small "
            "Project plan; every other row this clock's applies_to reaches "
            "(Large Project Plan, Subdivision Plan, Special Permit, Variance) "
            "is marked '●' (Required) in the Notice column. "
            "'small_project_plan' was included by hand-transcription error, "
            "not from the table; leaving it in produced a PERMANENT false "
            "MISSED notice_mailed clock on the CEO track (§10.d.4, the "
            "app's most common permit type -- no notice, no hearing, no "
            "Planning Board involvement at all). Per Finding 4's own rule "
            "(where the table and a hand-transcribed applies_to conflict, "
            "the table governs), applies_to is corrected to match the table; "
            "ruleset_build.verify_structure.check_table_7_1_applies_to now "
            "checks this agreement as a standing invariant."
        ),
    },
    {
        "clock_key": "small_project_decision",
        "label": "Small Project Plan decision (CEO)",
        "citation": {"article": 7, "section": "10", "subsection": "d.4"},
        "source_text": (
            "Within 10 days after receiving a completed application for a Small "
            "Project Plan that does not require any further type of development "
            "review, the Code Enforcement Officer must issue a Zoning Permit or "
            "transmit in writing to the Applicant the reasons for failure to "
            "issue such permit."
        ),
        "start_event": "submitted_at",
        "satisfying_event": "decision_at",
        "days": 10,
        "basis": "calendar",
        "applies_to": ["small_project_plan"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§10.d.4: \"...the Code Enforcement Officer must issue a Zoning Permit or transmit in writing to the Applicant the reasons for failure to issue such permit.\" Named Town official (CEO), mandatory verb (\"must\") -- municipal_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "decision_due",
        "notes": None,
    },
    {
        "clock_key": "large_project_ceo_decision",
        "label": "Large Project Plan decision (CEO track)",
        "citation": {"article": 7, "section": "11", "subsection": "d.3"},
        "source_text": (
            "Within 45 days after receiving a completed application for a Large "
            "Project Plan that does not require any further type of development "
            "review, the Code Enforcement Officer must issue a Zoning Permit or "
            "transmit in writing to the Applicant the reasons for failure to "
            "issue such permit."
        ),
        "start_event": "submitted_at",
        "satisfying_event": "decision_at",
        "days": 45,
        "basis": "calendar",
        "applies_to": ["large_project_plan"],
        "requires_absent": ["forwarded_to_pb_at"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§11.d.3, the identical \"the Code Enforcement Officer must issue ... or transmit ... reasons for failure\" pattern as small_project_decision -- municipal_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "decision_due",
        "notes": "Only applies when the CEO does NOT forward the application to the Planning Board (§11.d.4) -- see requires_absent.",
    },
    {
        "clock_key": "large_project_pb_completeness_hearing",
        "label": "Large Project Plan completeness review + public hearing (Planning Board track)",
        "citation": {"article": 7, "section": "11", "subsection": "d.4.a"},
        "source_text": (
            "Within 30 days after receiving an application for Large Project "
            "Plan approval, the Planning Board must review the application for "
            "completeness and hold a public hearing."
        ),
        "start_event": "forwarded_to_pb_at",
        "satisfying_event": "hearing_opened_at",
        "days": 30,
        "basis": "calendar",
        "applies_to": ["large_project_plan"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§11.d.4.a: \"...the Planning Board must review the application for completeness and hold a public hearing.\" Town body, mandatory verb -- municipal_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "completeness_review",
        "notes": None,
    },
    {
        "clock_key": "large_project_pb_decision",
        "label": "Large Project Plan decision (Planning Board track)",
        "citation": {"article": 7, "section": "11", "subsection": "d.4.b"},
        "source_text": (
            "Within thirty 30 days of the closing of the public hearing, the "
            "Planning Board must make a decision to approve, approve with "
            "conditions, deny, or grant withdrawal of the application in "
            "accordance with this section."
        ),
        "start_event": "hearing_closed_at",
        "satisfying_event": "decision_at",
        "days": 30,
        "basis": "calendar",
        "applies_to": ["large_project_plan"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§11.d.4.b: \"...the Planning Board must make a decision to approve, approve with conditions, deny, or grant withdrawal...\" -- municipal_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "decision_due",
        "notes": None,
    },
    {
        "clock_key": "subdivision_completeness",
        "label": "Subdivision Plan completeness determination",
        "citation": {"article": 7, "section": "12", "subsection": "e.3"},
        "source_text": (
            "Within 30 days after receiving an application for Subdivision "
            "Plan approval, the Planning Board must determine if the "
            "application is complete and ready for review at a public "
            "hearing."
        ),
        "start_event": "submitted_at",
        "satisfying_event": "completeness_at",
        "days": 30,
        "basis": "calendar",
        "applies_to": ["subdivision"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§12.e.3: \"...the Planning Board must determine if the application is complete and ready for review at a public hearing.\" Town body, mandatory verb -- municipal_duty, independent of the separate, still-open D-0012 question of whether §8.d.1's own consequence text reaches this particular duty (that is failure_consequence's question, not duty_kind's)."
        ),
        "failure_consequence": None,
        "db_kind": "completeness_review",
        "notes": "A completeness determination is neither 'holding a public hearing' nor 'taking final action', so §8.d.1 auto-approval is not attached to this clock.",
    },
    {
        "clock_key": "subdivision_hearing_decision",
        "label": "Subdivision Plan public hearing + decision",
        "citation": {"article": 7, "section": "12", "subsection": "e.5"},
        "source_text": (
            "Within 30 days after determining application completeness, the "
            "Planning Board must hold a public hearing and make a decision to "
            "approve, approve with modifications, deny, or grant withdrawal "
            "without prejudice the application for final plat plan approval."
        ),
        "start_event": "completeness_at",
        "satisfying_event": "decision_at",
        "days": 30,
        "basis": "calendar",
        "applies_to": ["subdivision"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§12.e.5: \"...the Planning Board must hold a public hearing and make a decision...\" -- municipal_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "decision_due",
        "notes": None,
    },
    {
        "clock_key": "subdivision_findings_issued",
        "label": "Subdivision findings of fact issued",
        "citation": {"article": 7, "section": "12", "subsection": "e.6"},
        "source_text": (
            "Within 30 days, the Planning Board must issue findings of fact "
            "and provide a copy to the applicant and the Office of the Code "
            "Enforcement Officer."
        ),
        "start_event": "decision_at",
        "satisfying_event": "findings_issued_at",
        "days": 30,
        "basis": "calendar",
        "applies_to": ["subdivision"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§12.e.6: \"...the Planning Board must issue findings of fact and provide a copy...\" Town body, mandatory verb -- municipal_duty (a documentation duty, not itself hearing/final-action, so §8.d.1 stays unattached -- see failure_consequence)."
        ),
        "failure_consequence": None,
        "db_kind": "decision_due",
        "notes": "Issuing findings of fact is a documentation duty following the §12.e.5 decision, not itself 'taking final action' -- §8.d.1 auto-approval is not attached to this clock.",
    },
    {
        "clock_key": "subdivision_plat_recorded_6mo",
        "label": "Subdivision plat recorded (six-month clock)",
        "citation": {"article": 7, "section": "12", "subsection": "j.1"},
        "source_text": (
            "The applicant will file a copy of the approved subdivision plat "
            "at the Lincoln County Registry of Deeds within 6 months of "
            "approval by the Planning Board."
        ),
        "start_event": "decision_at",
        "satisfying_event": "plat_recorded_at",
        "days": 6,
        "basis": "months",
        "applies_to": ["subdivision", "large_project_plan"],
        "duty_kind": "applicant_duty",
        "duty_kind_note": (
            "§12.j.1 (also §8.f.5): \"The applicant will file a copy of the approved subdivision plat at the Lincoln County Registry of Deeds ...\" -- the actor is explicitly the applicant, not a Town body; mandatory (\"will file\"). applicant_duty: not party_right (there is no discretion here -- the applicant MUST record), not municipal_duty (the Town cannot itself cause this to be missed)."
        ),
        "failure_consequence": None,
        "db_kind": "condition_compliance",
        "conflict_group": "subdivision_plat_recording",
        "conflict_note": RECORDING_CONFLICT_NOTE,
        "never_autogenerate_condition": True,
        "notes": (
            "§8.f.5 (general plan recording) states the same six-month rule; "
            "§12.j.1 is the subdivision-specific citation used here. See "
            "conflict_note. F9c: applies_to widened from ['subdivision'] to also "
            "include large_project_plan -- §8.f.5's own text is 'Plans approved "
            "and signed by the Planning Board', which is not subdivision-specific; "
            "a Large Project Plan decided on the Planning Board track (§11.d.4, "
            "large_project_pb_decision) is squarely 'approved and signed by the "
            "Planning Board' too. Not widened to special_permit (§18 decisions are "
            "also Planning Board decisions and arguably meet the same text) -- "
            "logged, not silently decided, in DECISIONS-NEEDED D-0013."
        ),
    },
    {
        "clock_key": "subdivision_plat_recorded_90d",
        "label": "Subdivision plat recorded (90-day clock -- CONFLICTS with the six-month clock)",
        "citation": {"article": 7, "section": "2", "subsection": "e.1"},
        "source_text": (
            "Plans containing lots, virtual lot lines, or building groups must "
            "be recorded in the Lincoln County Registry of Deeds within 90 "
            "days of the granting of an approval, variance, or a permit."
        ),
        "start_event": "decision_at",
        "satisfying_event": "plat_recorded_at",
        "days": 90,
        "basis": "calendar",
        "applies_to": ["subdivision", "large_project_plan"],
        "duty_kind": "applicant_duty",
        "duty_kind_note": (
            "§2.e.1: \"Plans containing lots, virtual lot lines, or building groups must be recorded in the Lincoln County Registry of Deeds within 90 days...\" -- passive voice, no actor named explicitly. Classified applicant_duty by inference from the parallel §12.j.1/§8.f.5 clock above (the same underlying act -- recording an approved plan -- whose actor IS named there as \"the applicant\"), not from this subsection's own text alone. Because the actor is genuinely unstated in §2.e.1 itself, this inference is logged at DECISIONS-NEEDED D-0015 rather than silently assumed."
        ),
        "failure_consequence": None,
        "db_kind": "condition_compliance",
        "conflict_group": "subdivision_plat_recording",
        "conflict_note": RECORDING_CONFLICT_NOTE,
        "never_autogenerate_condition": True,
        "notes": (
            "This is the SHORTER, conflicting clock. NEVER used, alone, to "
            "auto-generate a recording condition on a decision -- see "
            "conflict_note and CaseFacts docs. F9c: applies_to widened from "
            "['subdivision'] to also include large_project_plan -- §2.e.1's own "
            "text is 'Plans containing lots, virtual lot lines, or building "
            "groups', a FACT about the plan's content, not a subdivision-specific "
            "rule; a Large Project Plan that creates building groups meets it "
            "exactly as a subdivision plat does. This clock's applies_to is "
            "necessarily coarser than the actual §2.e.1 trigger (not every large_"
            "project_plan creates lots/virtual lot lines/building groups) -- "
            "engine/deadlines.py should treat this the same way it already must "
            "treat large_project_ceo_decision's requires_absent condition, i.e. as "
            "a track-eligible-but-fact-gated clock, not an unconditional one."
        ),
    },
    {
        "clock_key": "special_permit_review_hearing",
        "label": "Special Permit review + public hearing",
        "citation": {"article": 7, "section": "18", "subsection": "d.1"},
        "source_text": (
            "Within 30 days after receiving a completed application for "
            "development review that requires a special permit, the Planning "
            "Board must review the application and hold a public hearing."
        ),
        "start_event": "submitted_at",
        "satisfying_event": "hearing_opened_at",
        "days": 30,
        "basis": "calendar",
        "applies_to": ["special_permit"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§18.d.1: \"...the Planning Board must review the application and hold a public hearing.\" -- municipal_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "completeness_review",
        "notes": None,
    },
    {
        "clock_key": "special_permit_decision",
        "label": "Special Permit decision",
        "citation": {"article": 7, "section": "18", "subsection": "d.2"},
        "source_text": (
            "Within 45 days after closing of the public hearing, the Planning "
            "Board must make a decision to approve, approve with "
            "modifications, deny, or grant withdrawal the application for a "
            "special permit, and file said decision with the Town Clerk."
        ),
        "start_event": "hearing_closed_at",
        "satisfying_event": "decision_at",
        "days": 45,
        "basis": "calendar",
        "applies_to": ["special_permit"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§18.d.2: \"...the Planning Board must make a decision to approve, approve with modifications, deny, or grant withdrawal the application ... and file said decision with the Town Clerk.\" -- municipal_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "decision_due",
        "notes": None,
    },
    {
        "clock_key": "variance_review_hearing",
        "label": "Variance review + public hearing (Board of Appeals)",
        "citation": {"article": 7, "section": "19", "subsection": "c.1"},
        "source_text": (
            "Within 30 days after receiving a completed application for a "
            "Zoning Permit that requires a variance, the Board of Appeals "
            "must review the application and hold a public hearing."
        ),
        "start_event": "submitted_at",
        "satisfying_event": "hearing_opened_at",
        "days": 30,
        "basis": "calendar",
        "applies_to": ["variance"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§19.c.1: \"...the Board of Appeals must review the application and hold a public hearing.\" -- municipal_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "completeness_review",
        "notes": None,
    },
    {
        "clock_key": "variance_decision",
        "label": "Variance decision (Board of Appeals)",
        "citation": {"article": 7, "section": "19", "subsection": "c.2"},
        "source_text": (
            "Within 45 days of the closing of the public hearing, the Board "
            "of Appeals must make a decision to approve, approve with "
            "conditions, deny, or grant withdrawal of the application for a "
            "variance and issue a certificate to the applicant stating the "
            "following:"
        ),
        "start_event": "hearing_closed_at",
        "satisfying_event": "decision_at",
        "days": 45,
        "basis": "calendar",
        "applies_to": ["variance"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§19.c.2: \"...the Board of Appeals must make a decision to approve, approve with conditions, deny, or grant withdrawal ... and issue a certificate...\" -- municipal_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "decision_due",
        "notes": None,
    },
    {
        "clock_key": "use_permit_decision",
        "label": "Use Permit decision (designated permitting authority)",
        "citation": {"article": 7, "section": "15", "subsection": "d.1"},
        "source_text": (
            "Within 30 days of receiving a completed application for a Use "
            "Permit, the designated permitting authority shall review the "
            "application and approve, approve with modifications, deny, or "
            "grant withdrawal of the application and file the decision with "
            "the Town Clerk."
        ),
        "start_event": "submitted_at",
        "satisfying_event": "decision_at",
        "days": 30,
        "basis": "calendar",
        "applies_to": ["use", "expanded_use"],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§15.d.1: \"...the designated permitting authority shall review the application and approve, approve with modifications, deny, or grant withdrawal of the application and file the decision with the Town Clerk.\" -- \"shall\" is mandatory and the actor is a designated Town permitting authority -- municipal_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "decision_due",
        "notes": (
            "F3 NEW CLOCK (coverage-assertion gap). §16.c.1 ('Expanded Use Permit "
            "Authority and Procedure follow those of Article 7 Section 15.C and "
            "15.D respectively') incorporates this same 30-day duty for Expanded "
            "Use Permit by cross-reference, so applies_to includes both `use` and "
            "`expanded_use` -- the two application_type values CONTRACT.md's use-"
            "matrix legend (permit_key `u`/`ex`) already ties to this procedure. "
            "§17.c.1 makes the identical cross-reference for Residential Companion "
            "Use Permit, but `residential_companion` is not a `cases.application_"
            "type` value in the v1 schema, so this clock cannot yet apply to that "
            "track -- a schema gap, not a Code ambiguity, so not filed in "
            "DECISIONS-NEEDED (CONTRACT.md §7.2). The 30-day period may be "
            "extended by the permitting authority per §15.d.2.a -- see that "
            "citation's EXCLUDED_DUTIES entry below."
        ),
    },
    {
        "clock_key": "variance_certificate_recorded",
        "label": "Variance certificate recorded",
        "citation": {"article": 7, "section": "19", "subsection": "c.3"},
        "source_text": (
            "Within 90 days of issuance of a certificate, the applicant must "
            "file a copy of the decision with the Lincoln County Registry of "
            "Deeds."
        ),
        "start_event": "decision_at",
        "satisfying_event": "certificate_recorded_at",
        "days": 90,
        "basis": "calendar",
        "applies_to": ["variance"],
        "duty_kind": "applicant_duty",
        "duty_kind_note": (
            "§19.c.3: \"Within 90 days of issuance of a certificate, the applicant must file a copy of the decision with the Lincoln County Registry of Deeds.\" -- explicit actor \"the applicant\", mandatory (\"must file\") -- applicant_duty."
        ),
        "failure_consequence": None,
        "db_kind": "condition_compliance",
        "notes": None,
    },
    {
        "clock_key": "decision_filed_with_clerk",
        "label": "Decision filed with the Town Clerk",
        "citation": {"article": 7, "section": "8", "subsection": "f.1"},
        "source_text": (
            "Decisions will be filed by the Permitting Authority as indicated "
            "for each type of development review with the Town Clerk within "
            "five business days after the decision is made. The Town Clerk "
            "will date stamp the decision, beginning the time period for "
            "which an appeal may be filed."
        ),
        "start_event": "decision_at",
        "satisfying_event": "decision_filed_at",
        "days": 5,
        "basis": "business",
        "applies_to": [
            "small_project_plan", "large_project_plan", "subdivision",
            "special_permit", "variance", "use", "expanded_use",
        ],
        "duty_kind": "municipal_duty",
        "duty_kind_note": (
            "§8.f.1: \"Decisions will be filed by the Permitting Authority as indicated for each type of development review with the Town Clerk within five business days...\" -- explicit actor \"the Permitting Authority\" -- municipal_duty."
        ),
        "failure_consequence": None,
        "db_kind": "decision_due",
        "starts_clock": "administrative_appeal",
        "notes": (
            "This is a filing duty, not a 'hold a hearing or take final action' "
            "deadline -- §8.d.1 is not attached. Its satisfying event (the Clerk's "
            "date stamp) is the anchor for the administrative_appeal clock below. "
            "F5: applies_to widened to include use/expanded_use -- §8.f.1's own text "
            "is 'as indicated for each type of development review', not scoped to "
            "particular tracks, and §15.d.1 (use_permit_decision) itself commands "
            "'file the decision with the Town Clerk' in the SAME sentence as the "
            "decision, the identical pattern special_permit_decision/variance_"
            "decision already carry alongside this general clock. Enforced going "
            "forward by _assert_track_coverage()."
        ),
    },
    {
        "clock_key": "administrative_appeal",
        "label": "Administrative appeal window",
        "citation": {"article": 7, "section": "23", "subsection": "d.1"},
        "source_text": (
            "Within 30 days of an action or failure to act, any aggrieved "
            "party may file an appeal with the Appellate Authority."
        ),
        "start_event": "decision_filed_at",
        "satisfying_event": "appeal_filed_at",
        "days": 30,
        "basis": "calendar",
        "applies_to": [
            "small_project_plan", "large_project_plan", "subdivision",
            "special_permit", "variance", "use", "expanded_use",
            "administrative_appeal",
        ],
        "duty_kind": "party_right",
        "duty_kind_note": (
            "§23.d.1: \"Within 30 days of an action or failure to act, any aggrieved party may file an appeal with the Appellate Authority.\" -- \"may\", permissive, and the actor is a private aggrieved party, not the Town. party_right: this is what an aggrieved party is entitled to do, not a duty the Town can fail. THIS IS THE N1 FIX -- previously modeled with the same PENDING_START/OPEN/MET/MISSED branching as a real duty, so 'nobody appealed' silently became MISSED 30 days after filing, which the F4 predecessor-alert machinery then read as a stalled statutory duty behind administrative_appeal_hearing, which F1's broadened presents_auto_approval_risk() then reported as risk -- a false alarm on every decided, unappealed case. Under party_right semantics this clock reports OPEN while the window runs and ELAPSED (never MISSED) once it passes unexercised: it can no longer serve as a 'missed predecessor duty' for anything downstream, and duty_kind alone now excludes it from presents_auto_approval_risk()."
        ),
        "failure_consequence": None,
        "db_kind": "appeal",
        "notes": (
            "F3 CITATION FIX (was §23.b.1): §23.b.1's text is expressly limited to "
            "'action or failure to act ... by a Code Enforcement Officer', but this "
            "clock is applied to every review track, including subdivision and "
            "large_project_plan's Planning Board track -- decisions the CEO never "
            "makes. §23.d.1 states the identical 30-day window in authority-neutral "
            "terms ('any aggrieved party may file an appeal with the Appellate "
            "Authority'), and §23.c.2 confirms the Board of Appeals hears appeals of "
            "Planning Board decisions too, so §23.d.1 is the correct citation for a "
            "clock that applies across all tracks. §8.f.1 ties the appeal window's "
            "start to the Town Clerk's date-stamp on the filed decision, not to the "
            "decision date itself -- start_event is decision_filed_at, not decision_at. "
            "F5: applies_to widened to include use/expanded_use -- §23.d.1's own text "
            "is authority-neutral ('any aggrieved party ... an action or failure to "
            "act'), not scoped to particular tracks, and a Use Permit decision filed "
            "under decision_filed_with_clerk above is exactly such an action. "
            "Enforced going forward by _assert_track_coverage()."
        ),
    },
    {
        "clock_key": "administrative_appeal_hearing",
        "label": "Appeal review + public hearing (Appellate Authority)",
        "citation": {"article": 7, "section": "23", "subsection": "d.2"},
        "source_text": (
            "Within 30 days of receiving an appeal, the Appellate Authority "
            "must review the application and hold a public hearing."
        ),
        "start_event": "appeal_filed_at",
        "satisfying_event": "appeal_hearing_opened_at",
        "days": 30,
        "basis": "calendar",
        "applies_to": [
            "small_project_plan", "large_project_plan", "subdivision",
            "special_permit", "variance", "use", "expanded_use",
            "administrative_appeal",
        ],
        "duty_kind": "conditional_duty",
        "predicate_event": "appeal_filed_at",
        "duty_kind_note": (
            "§23.d.2: \"Within 30 days of receiving an appeal, the Appellate Authority must review the application and hold a public hearing.\" -- mandatory verb, Town body (the Board of Appeals acting as Appellate Authority) -- but the duty to hold this hearing exists ONLY once an appeal has actually been filed (the party_right at §23.d.1, immediately above). This is the taxonomy's own paradigm case (\"an appeal hearing exists only if an appeal was filed\") -- conditional_duty, predicate_event=appeal_filed_at (here the same field as this clock's own start_event). NOT_TRIGGERED, not PENDING_START, while no appeal has been filed -- the common case for a decided, unappealed application. failure_consequence stays attached per the conservative D-0011 reading (whether 'Appellate Authority' is a 'Permitting Authority' for §8.d.1 purposes remains open, logged, not decided here); presents_auto_approval_risk() now derives ONLY from municipal_duty clocks, so this conditional_duty clock does not feed the case-level risk banner even once triggered -- appropriate given its own satisfying event still cannot be recorded under the current schema (see N2, out of this task's scope)."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "completeness_review",
        "notes": (
            "F3 NEW CLOCK. Matches applies_to to the administrative_appeal clock "
            "above -- an appeal of ANY track's decision (§23.c.1 CEO actions "
            "de novo, §23.c.2 Planning Board decisions on appeal) starts this "
            "clock once the appeal is filed. satisfying_event is deliberately "
            "appeal_hearing_opened_at, NOT the shared hearing_opened_at field -- "
            "the underlying case may already have its OWN hearing_opened_at from "
            "its original review (e.g. special_permit_review_hearing, "
            "variance_review_hearing); reusing that field for the Appellate "
            "Authority's later, separate hearing would silently overwrite the "
            "original hearing's date and corrupt that clock's own status if ever "
            "recomputed. engine/deadlines.py's CaseFacts and the case_milestones.kind "
            "CHECK constraint (app/migrations/0003_case_lifecycle.sql) do not yet "
            "carry appeal_hearing_opened_at / an 'appeal_hearing_opened' milestone "
            "kind -- adding them is a prerequisite for this clock to compute, not "
            "a clocks.json concern. Whether 'Appellate Authority' is a species of "
            "the defined 'Permitting Authority' §8.d.1 speaks of is logged, "
            "non-blocking, in DECISIONS-NEEDED (see D-0011); this clock is built "
            "conservatively assuming yes, per the app's stated posture of surfacing "
            "auto-approval risk rather than narrowing it. F5: applies_to widened to "
            "include use/expanded_use -- an appeal of a Use Permit decision (filed "
            "under decision_filed_with_clerk / administrative_appeal above, both now "
            "reaching use/expanded_use) triggers this same 30-day review-and-hearing "
            "duty exactly as an appeal of any other track's decision does. Enforced "
            "going forward by _assert_track_coverage()."
        ),
    },
    {
        "clock_key": "administrative_appeal_decision",
        "label": "Appeal decision (Appellate Authority)",
        "citation": {"article": 7, "section": "23", "subsection": "d.3"},
        "source_text": (
            "Within 45 days after the closing of the public hearing, the "
            "Appellate Authority must make a decision to uphold or reverse "
            "the decision of the Code Enforcement Officer, and file said "
            "decision with the Town Clerk."
        ),
        "start_event": "appeal_hearing_closed_at",
        "satisfying_event": "appeal_decision_at",
        "days": 45,
        "basis": "calendar",
        "applies_to": [
            "small_project_plan", "large_project_plan", "subdivision",
            "special_permit", "variance", "use", "expanded_use",
            "administrative_appeal",
        ],
        "duty_kind": "conditional_duty",
        "predicate_event": "appeal_filed_at",
        "duty_kind_note": (
            "§23.d.3: \"Within 45 days after the closing of the public hearing, the Appellate Authority must make a decision to uphold or reverse the decision of the Code Enforcement Officer, and file said decision with the Town Clerk.\" -- mandatory verb, Town body -- but, like administrative_appeal_hearing immediately above, this entire duty branch exists only if an appeal was filed at all. predicate_event is the ROOT gate (appeal_filed_at), deliberately distinct from this clock's own start_event (appeal_hearing_closed_at, a later event downstream of the predicate): once an appeal IS filed, this clock behaves as an ordinary PENDING_START/OPEN/MET/MISSED duty from that point forward; it is NOT_TRIGGERED only while no appeal exists at all. conditional_duty."
        ),
        "failure_consequence": AUTO_APPROVAL_TEXT,
        "db_kind": "decision_due",
        "notes": (
            "F3 NEW CLOCK. The Town Clerk filing is bundled into the same "
            "sentence/duty as the decision (mirrors special_permit_decision and "
            "variance_decision's pattern above) -- no separate filing clock is "
            "spawned. start_event/satisfying_event are the appeal-specific "
            "appeal_hearing_closed_at / appeal_decision_at fields for the same "
            "reason given on administrative_appeal_hearing's notes (avoiding "
            "collision with the underlying case's own hearing_closed_at / "
            "decision_at). The literal text says 'uphold or reverse the decision "
            "of the Code Enforcement Officer' even though §23.c.2 also gives the "
            "Board of Appeals appellate jurisdiction over Planning Board decisions; "
            "treated as the same 45-day duty regardless of which authority's "
            "decision is under appeal, since §23.d.3 states one procedure for "
            "'the Appellate Authority' generally and the CEO-specific phrase reads "
            "as an incomplete edit, not a substantive limit -- not logged to "
            "DECISIONS-NEEDED because it does not change any qualifier, day count, "
            "or citation, only which decisions this clock's plain description "
            "covers. F5: applies_to widened to include use/expanded_use, for the "
            "same reason as administrative_appeal_hearing immediately above -- "
            "enforced going forward by _assert_track_coverage()."
        ),
    },
    {
        "clock_key": "reconsideration",
        "label": "Board of Appeals reconsideration window",
        "citation": {"article": 7, "section": "23", "subsection": "e.1"},
        "source_text": (
            "In accordance with MRSA Title 30 Section 2691, an applicant may "
            "file a request to the Board of Appeals to reconsider its "
            "decision within 10 days of the decision."
        ),
        "start_event": "decision_at",
        "satisfying_event": "reconsideration_requested_at",
        "days": 10,
        "basis": "calendar",
        "applies_to": ["variance", "administrative_appeal"],
        "duty_kind": "party_right",
        "duty_kind_note": (
            "§23.e.1: \"...an applicant may file a request to the Board of Appeals to reconsider its decision within 10 days of the decision.\" -- \"may\", permissive, private-party actor (the applicant) -- party_right, the same reasoning as administrative_appeal above. Reports OPEN while the window runs, ELAPSED (never MISSED) once it passes with no request filed."
        ),
        "failure_consequence": None,
        "db_kind": "appeal",
        "notes": "Reconsideration is specific to Board of Appeals decisions (variance, administrative appeal), not Planning Board decisions.",
    },
    {
        "clock_key": "reconsideration_decision",
        "label": "Board of Appeals reconsideration -- conclude + vote",
        "citation": {"article": 7, "section": "23", "subsection": "e.4"},
        "source_text": (
            "If the Board of Appeals reconsiders its original decision, the "
            "Board must conclude its deliberations and vote within 45 days "
            "of the original decision."
        ),
        "start_event": "decision_at",
        "satisfying_event": "reconsideration_decided_at",
        "days": 45,
        "basis": "calendar",
        "applies_to": ["variance", "administrative_appeal"],
        "duty_kind": "conditional_duty",
        "predicate_event": "reconsideration_voted_at",
        "duty_kind_note": (
            "§23.e.4: \"If the Board of Appeals reconsiders its original decision, the Board must conclude its deliberations and vote within 45 days of the original decision.\" -- the clock's own governing sentence is textually conditional (\"If ... reconsiders\"), and \"reconsiders\" is a defined step upstream: §23.e.2 (\"The Board of Appeals will hold a public hearing, and vote to reconsider its decision\") and §23.e.3 (\"If a majority of Board members who originally voted on the decision vote to reconsider, the Board of Appeals may conduct additional hearings...\") -- i.e. the Board actually RECONSIDERS only once that majority VOTE TO RECONSIDER passes, not merely once someone REQUESTS it under §23.e.1. F6 FIX (HARD-FINAL round, Finding 6): predicate_event narrowed from reconsideration_requested_at (the §23.e.1 REQUEST -- an applicant's party_right, which the Board may or may not act on) to reconsideration_voted_at (the §23.e.2/.e.3 VOTE TO RECONSIDER), so this clock's NOT_TRIGGERED/triggered boundary now matches its OWN governing sentence's actual conditional, not merely the fact that an applicant asked. A request that never reaches a vote -- or a vote that fails the §23.e.3 majority threshold -- correctly stays NOT_TRIGGERED forever, exactly as it should: §23.e.4 imposes no duty at all unless the Board reconsiders. This IS THE RECONSIDERATION HALF OF THE ORIGINAL N2 FIX, refined -- previously (pre-N2) this clock started unconditionally from decision_at and went MISSED 45 days after EVERY decision; N2 first gated it on the REQUEST, which stopped the false MISSED but over-triggered relative to the clock's own \"if ... reconsiders\" text (a request with no vote still flipped this clock live); F6 closes that remaining gap. failure_consequence stays None (unchanged; never characterized as an §8.d.1-bearing duty -- see notes)."
        ),
        "failure_consequence": None,
        "db_kind": "appeal",
        "notes": (
            "F3 NEW CLOCK, deliberately WITHOUT failure_consequence -- unlike "
            "administrative_appeal_hearing (§23.d.2) and administrative_appeal_"
            "decision (§23.d.3), this is not characterized as a §8.d.1-bearing "
            "duty: it is a vote on whether to alter a decision the Board has "
            "ALREADY made, not itself 'holding a public hearing' (that is §23.e.2, "
            "which carries no day count) or unambiguously 'taking final action on "
            "an application' in the §8.d.1 sense when an action was already taken. "
            "start_event is decision_at (the ORIGINAL decision, per the text's own "
            "'within 45 days of the original decision' -- not reconsideration_"
            "voted_at or reconsideration_requested_at). satisfying_event is "
            "reconsideration_decided_at, distinct from reconsideration_voted_at "
            "(the predicate -- §23.e.2/.e.3's VOTE TO RECONSIDER), reconsideration_"
            "requested_at (the §23.e.1 REQUEST), and decision_at (the ORIGINAL "
            "decision this clock's due date is computed from) -- four genuinely "
            "different events, never collapsed into one another. F6 (2026-08, "
            "HARD-FINAL round, Finding 6): predicate_event is now "
            "reconsideration_voted_at, a first-class, independently recordable "
            "CaseFacts field / case_milestones.kind ('reconsideration_voted') -- "
            "see engine/deadlines.py's CaseFacts and _MILESTONE_TO_FIELD, and "
            "app/migrations/0010_reconsideration_vote.sql. Before F6, this clock's "
            "own comment here candidly said 'engine/deadlines.py should treat an "
            "OPEN status here as informational only until that [vote] fact is "
            "captured, not as an active deadline on every reconsideration request' "
            "-- that gap is now closed structurally (NOT_TRIGGERED, not merely an "
            "informational OPEN) rather than left as a caller-side caveat. See "
            "DECISIONS-NEEDED D-0011 for the still-open, unrelated §8.d.1-"
            "attachment question (whether the Appellate Authority is a "
            "\"Permitting Authority\"), logged rather than decided."
        ),
    },
]

# --------------------------------------------------------------------------- #
# F3 coverage assertion (build_clocks.build_clocks -> _assert_coverage).
#
# Every Article 7 sentence containing the word "within" near a day-count
# ("Within N days", "within N business days", "sign mylars within 14 days",
# ...) is either (a) represented by a clock_key's citation in CLOCKS_ADOPTED
# above, or (b) named here with a documented reason it is NOT a clock in this
# v1 app. A citation matching the scan pattern that is in NEITHER set is a
# silently-missing statutory clock -- exactly the class of defect F1/F3 found
# (a clock nobody wrote is a clock that can never warn anyone) -- and fails
# the build (ClockBuildError), same posture as _validate's citation/text check.
#
# This is deliberately a dumb, auditable regex sweep over the FULL extracted
# Article 7 text (literal "within ... days"/"within ... day"), not an "is this
# a Permitting Authority duty" classifier -- classifying actors reliably from
# prose is exactly the kind of judgment call CONTRACT.md §1 S7 says not to
# silently automate. It intentionally does NOT catch deadline-shaped language
# that never uses the word "within" (e.g. §3.c.1/§4.c.1's pre-submittal/
# neighborhood-meeting "at least N days prior" lead times, §15.d.2.a's "may
# extend ... by an additional 30 days", §22's historic-demolition "no less
# than 90 days"/"during the 90 day time period" waiting periods) -- those are
# out of THIS assertion's stated scope (literal "within ... days" clauses),
# not silently swept in and then silently excluded. Every match the regex
# DOES find, including applicant-side deadlines already carried by an
# existing clock (e.g. §2.e.1, §19.c.3), is accounted for explicitly below so
# the sweep's own completeness is checkable by a human at a glance; a
# citation named in EXCLUDED_DUTIES that stops matching the regex (source
# text moved, or the entry was mis-transcribed) is itself a build failure --
# see the "stale exclusion" check in `_assert_coverage`.
# --------------------------------------------------------------------------- #

WITHIN_DAYS_RE = __import__("re").compile(r"\bwithin\b.{0,30}?\bdays?\b", __import__("re").I)

EXCLUDED_DUTIES: dict[tuple[int, str, str], str] = {
    (7, "7", "d.1"): (
        "Written Interpretation (§7) is a petition for the CEO's opinion, not a "
        "development-review application. It has no corresponding "
        "`cases.application_type` value and no case_milestones support in the v1 "
        "schema (app/migrations/0001-0003) -- this app does not model it as a "
        "reviewable case at all, so no clock can ever be applied to one."
    ),
    (7, "10", "g.1.c"): (
        "§10.G is AMENDMENTS to an already-approved Small Project Plan -- a "
        "post-decision review cycle. The v1 case model is one case, one initial "
        "review; case_milestones.kind has no 'amendment submitted' / second "
        "completeness-determination kind distinct from the original application's "
        "own submitted_at/decision_at. A clock reusing those fields for an "
        "amendment would silently corrupt the original application's own clocks "
        "(the same collision class documented on administrative_appeal_hearing "
        "above), so this is excluded rather than mis-modeled."
    ),
    (7, "11", "g.1.c"): (
        "§11.G is AMENDMENTS to an already-approved Large Project Plan -- same "
        "post-decision-amendment-cycle gap as §10.G.1.c above."
    ),
    (7, "13", "d.2"): (
        "Master Plan (§13) has no corresponding `cases.application_type` value -- "
        "0002/0003_*.sql widened application_type to add small_project_plan/"
        "large_project_plan/variance to the pre-existing subdivision/special_permit "
        "values, but never added master_plan. Not a reviewable case type in v1."
    ),
    (7, "13", "d.4"): "Same gap as §13.d.2 -- Master Plan is not a modeled case type.",
    (7, "14", "d.1"): (
        "Plan Revision (§14) is a post-decision amendment-classification process "
        "(de minimis vs. major amendment determination on an ALREADY-approved "
        "plan), not a modeled `cases.application_type` / case_milestones flow -- "
        "same class of gap as §10.G/§11.G's AMENDMENTS clauses."
    ),
    (7, "14", "d.6"): (
        "Same Plan Revision gap as §14.d.1 -- 'the Planning Board must make itself "
        "available ... to sign mylars within 14 days' is a ministerial step in the "
        "same unmodeled amendment cycle, not a hearing/decision deadline in any "
        "event (it is closer in kind to the recording clocks already excluded from "
        "§8.d.1 auto-approval than to a completeness/hearing/decision clock)."
    ),
    (7, "20", "d.1"): (
        "Land Conveyance (§20) is the Board of Selectmen accepting or declining "
        "land -- not 'project review and approval' under Article 9's Permitting "
        "Authority definition, and not a `cases.application_type` value. Out of "
        "this app's v1 scope (permit applications the Board drafts Findings for)."
    ),
    (7, "21", "d.2"): (
        "Zoning Amendment (§21) is the Town's own legislative text/map-amendment "
        "process (petition -> Planning Board review -> Town Meeting warrant), not "
        "an applicant's permit review, and not a `cases.application_type` value -- "
        "it is not an 'application' §8.d.1 could ever auto-approve."
    ),
    (7, "21", "d.3"): "Same Zoning Amendment gap as §21.d.2.",
    (7, "21", "d.4"): "Same Zoning Amendment gap as §21.d.2.",
    (7, "23", "b.1"): (
        "Superseded citation (F3): §23.b.1's 'aggrieved party ... within 30 days' "
        "text is the CEO-only-scoped predecessor of the authority-neutral §23.d.1, "
        "which the administrative_appeal clock now cites instead -- see that "
        "clock's notes. Not a second, separately-tracked deadline; carrying both "
        "citations as clocks would double-count the same 30-day window."
    ),
}


def _duty_citations_in_text(nodes: list[dict[str, Any]]) -> set[tuple[int, str, str]]:
    found: set[tuple[int, str, str]] = set()
    for n in nodes:
        if n["article"] != 7:
            continue
        text = n["text"] or ""
        if WITHIN_DAYS_RE.search(text):
            subsection = ".".join([n["subsection"], *n["path"]]) if n["path"] else n["subsection"]
            found.add((n["article"], n["section"], subsection))
    return found


def _assert_coverage(clocks: list[dict[str, Any]]) -> dict[str, Any]:
    """F3: fails the build if any 'Within N days'/'within N business days' Article 7
    clause is neither a clock in `clocks` nor a documented EXCLUDED_DUTIES entry.
    Returns a small report dict for the caller to print."""
    nodes = _load_adopted_nodes()
    found = _duty_citations_in_text(nodes)

    clock_citations = {
        (c["citation"]["article"], c["citation"]["section"], c["citation"]["subsection"])
        for c in clocks
    }

    excluded = set(EXCLUDED_DUTIES.keys())

    stale_exclusions = excluded - found
    if stale_exclusions:
        raise ClockBuildError(
            "EXCLUDED_DUTIES contains citations that no longer match any Article 7 "
            "'within ... days' clause (stale exclusion -- the source text moved or "
            "the exclusion was mis-transcribed): "
            + ", ".join(f"§{s}.{sub}" for _, s, sub in sorted(stale_exclusions))
        )

    uncovered = found - clock_citations - excluded
    if uncovered:
        raise ClockBuildError(
            "F3 coverage assertion failed -- the following Article 7 'within ... "
            "days' clauses are neither a clock in CLOCKS_ADOPTED nor a documented "
            "EXCLUDED_DUTIES entry in ruleset_build/build_clocks.py: "
            + ", ".join(f"§{s}.{sub}" for _, s, sub in sorted(uncovered))
        )

    return {
        "found": len(found),
        "covered_by_clock": len(found & clock_citations),
        "excluded": len(found & excluded),
    }


# --------------------------------------------------------------------------- #
# F5 track coverage assertion (build_clocks.build_clocks -> _assert_track_
# coverage). `_assert_coverage` above catches a statutory CLAUSE that never
# became a clock at all; this catches a different defect class -- a clock
# that DOES exist but whose `applies_to` silently omits a real review track
# it textually reaches. Finding 5's repro (use/expanded_use had a decision
# clock but no filing/appeal clocks) is exactly this shape: nothing about
# _assert_coverage's citation sweep would ever have caught it, because §8.f.1
# and §23.d.1/.d.2/.d.3 WERE already clocks -- they just didn't list every
# track their own track-agnostic text reaches.
#
# DECISION_TRACKS is every `cases.application_type` (app/cases.py.
# APPLICATION_TYPES) that is a genuine Permitting-Authority DECISION this app
# models end to end -- i.e., one whose decision is filed with the Town Clerk
# under §8.f.1 and is therefore appealable under §23.d.1. Deliberately
# EXCLUDES: `zoning`, `shoreland`, `site_plan`, `other` (catch-all/unmodeled
# application_type values with no Article 7 clock set of their own -- see
# engine/deadlines.py's "REVIEW_TRACKS" comment); `administrative_appeal`
# (the appeal TRACK ITSELF, already present in each of these clocks'
# applies_to as its own entry -- an appeal is not a first-instance decision
# that itself gets appealed under this app's v1 model).
#
# UNIVERSAL_DUTY_CLOCKS names the clocks whose OWN governing sentence is
# track-agnostic on its face ("as indicated for EACH TYPE OF development
# review", "ANY aggrieved party") -- as opposed to a clock like
# special_permit_decision, whose citation (§18.d.2) is intrinsically scoped
# to one track by the Code's own section structure. Only a clock in THIS
# list is required to cover every DECISION_TRACKS value; the section-scoped
# decision clocks are correctly narrow and must not be swept in here.
# --------------------------------------------------------------------------- #

DECISION_TRACKS: tuple[str, ...] = (
    "small_project_plan", "large_project_plan", "subdivision",
    "special_permit", "variance", "use", "expanded_use",
)

UNIVERSAL_DUTY_CLOCKS: tuple[str, ...] = (
    "decision_filed_with_clerk",       # §8.f.1
    "administrative_appeal",           # §23.d.1
    "administrative_appeal_hearing",   # §23.d.2
    "administrative_appeal_decision",  # §23.d.3
)


def _assert_track_coverage(clocks: list[dict[str, Any]]) -> dict[str, Any]:
    """F5: fails the build if any UNIVERSAL_DUTY_CLOCKS entry's `applies_to`
    is missing a real DECISION_TRACKS value. Returns a small report dict for
    the caller to print."""
    by_key = {c["clock_key"]: c for c in clocks}

    problems: list[str] = []
    checked = 0
    for key in UNIVERSAL_DUTY_CLOCKS:
        clock = by_key.get(key)
        if clock is None:
            raise ClockBuildError(
                f"F5 track coverage: UNIVERSAL_DUTY_CLOCKS names {key!r}, which is "
                f"not a clock_key in CLOCKS_ADOPTED (stale entry -- the clock was "
                f"renamed or removed)"
            )
        checked += 1
        applies_to = set(clock["applies_to"])
        missing = [t for t in DECISION_TRACKS if t not in applies_to]
        if missing:
            problems.append(f"{key} (§{clock['citation']['section']}.{clock['citation']['subsection']}): missing {missing}")

    if problems:
        raise ClockBuildError(
            "F5 coverage assertion failed -- the following statutorily-"
            "commanded, track-agnostic clocks are missing a real review track "
            "from their applies_to: " + "; ".join(problems)
        )

    return {"universal_clocks_checked": checked, "tracks_required": len(DECISION_TRACKS)}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_json(target: Path, obj: dict) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    json.loads(text)  # round-trip verify (CONTRACT.md §1 S2 posture)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(target)


def _load_adopted_nodes() -> list[dict[str, Any]]:
    path = RULESETS_DIR / "adopted" / "articles.json"
    if not path.exists():
        raise ClockBuildError(f"{path} not found -- build rulesets/adopted first")
    doc = json.loads(path.read_text(encoding="utf-8"))
    # Flatten the adopted tree (nested children) into (article, section,
    # subsection, path, text) rows, the same shape the draft ruleset already
    # stores flat in its own "nodes" list -- so both are validated the same way.
    flat: list[dict[str, Any]] = []

    def walk(node: dict[str, Any], article: int, section: str | None, subsection: str | None, path: list[str]) -> None:
        kind = node.get("kind")
        num = node.get("number")
        if kind == "section":
            section, subsection, path = num, None, []
        elif kind == "subsection":
            subsection, path = num, []
        elif num is not None and subsection is not None:
            path = path + [num]
        text = node.get("text")
        if text:
            flat.append({"article": article, "section": section, "subsection": subsection, "path": path, "text": text})
        for c in node.get("children", []) or []:
            walk(c, article, section, subsection, path)

    for art in doc["articles"]:
        walk(art, art["article"], None, None, [])
    return flat


def _find_text(nodes: list[dict[str, Any]], article: int, section: str, subsection: str) -> str | None:
    sub_parts = subsection.split(".")
    sub, path = sub_parts[0], sub_parts[1:]
    for n in nodes:
        if n["article"] == article and n["section"] == section and n["subsection"] == sub and n["path"] == path:
            return n["text"]
    return None


def _validate(clocks: list[dict[str, Any]]) -> None:
    nodes = _load_adopted_nodes()
    seen_keys: set[str] = set()
    for c in clocks:
        key = c["clock_key"]
        if key in seen_keys:
            raise ClockBuildError(f"duplicate clock_key {key!r}")
        seen_keys.add(key)

        if c["basis"] not in ("calendar", "business", "months"):
            raise ClockBuildError(f"{key}: invalid basis {c['basis']!r}")
        if not isinstance(c["days"], int) or c["days"] <= 0:
            raise ClockBuildError(f"{key}: days must be a positive int")
        if not c["applies_to"]:
            raise ClockBuildError(f"{key}: applies_to must be non-empty")

        duty_kind = c.get("duty_kind")
        if duty_kind not in DUTY_KINDS:
            raise ClockBuildError(
                f"{key}: duty_kind must be one of {DUTY_KINDS!r}, got {duty_kind!r} "
                f"-- every clock must be classified (see the DUTY_KINDS comment above)"
            )
        if not (c.get("duty_kind_note") or "").strip():
            raise ClockBuildError(
                f"{key}: duty_kind_note must quote the governing sentence that "
                f"justifies its duty_kind -- classification must be auditable"
            )
        predicate_event = c.get("predicate_event")
        if duty_kind == "conditional_duty":
            if not predicate_event or not predicate_event.endswith("_at"):
                raise ClockBuildError(
                    f"{key}: duty_kind=conditional_duty requires a predicate_event "
                    f"naming the CaseFacts field whose recording triggers the duty "
                    f"(got {predicate_event!r})"
                )
        elif predicate_event is not None:
            raise ClockBuildError(
                f"{key}: predicate_event is only meaningful on a conditional_duty "
                f"clock (duty_kind is {duty_kind!r})"
            )

        cit = c["citation"]
        found = _find_text(nodes, cit["article"], cit["section"], cit["subsection"])
        if found is None:
            raise ClockBuildError(
                f"{key}: citation Article {cit['article']} §{cit['section']}.{cit['subsection']} "
                f"not found in rulesets/adopted/articles.json"
            )
        # The transcribed source_text must be a substring of the extracted
        # sentence (verbatim-enough to catch a mis-transcribed day count or
        # a copy/paste from the wrong subsection) without demanding an exact
        # match (a few clocks quote only the operative sentence of a longer
        # extracted paragraph).
        if c["source_text"].strip() not in found:
            raise ClockBuildError(
                f"{key}: source_text does not match the extracted Article "
                f"{cit['article']} §{cit['section']}.{cit['subsection']} text.\n"
                f"  extracted: {found!r}\n"
                f"  clock:     {c['source_text']!r}"
            )


def _renumber_for_draft(clocks: list[dict[str, Any]], *, draft_article: int) -> list[dict[str, Any]]:
    out = []
    for c in clocks:
        c2 = dict(c)
        c2["citation"] = dict(c["citation"])
        c2["citation"]["article"] = draft_article
        out.append(c2)
    return out


def build_clocks(*, adopted_dir: str = "adopted", draft_dir: str = "draft-v0.22") -> dict[str, Path]:
    """Validates CLOCKS_ADOPTED against rulesets/adopted/articles.json, then
    writes rulesets/<adopted_dir>/clocks.json and rulesets/<draft_dir>/
    clocks.json (article 7 -> 8 renumbered, per app.citation.
    RENUM_ADOPTED_TO_DRAFT). Raises ClockBuildError and writes NOTHING on any
    validation failure (CONTRACT.md §1 S1 posture) -- including F3's coverage
    assertion (`_assert_coverage`) and F5's track-coverage assertion
    (`_assert_track_coverage`), both run after per-clock validation so a
    citation/text mismatch is reported before either coverage gap.
    """
    _validate(CLOCKS_ADOPTED)
    coverage = _assert_coverage(CLOCKS_ADOPTED)
    track_coverage = _assert_track_coverage(CLOCKS_ADOPTED)

    adopted_path = RULESETS_DIR / adopted_dir / "articles.json"
    source_sha = _sha256_file(adopted_path)

    adopted_doc = {
        "schema": SCHEMA,
        "ruleset_key": adopted_dir,
        "article_scheme": "adopted",
        "generated_at": _now_iso(),
        "source": {"path": f"rulesets/{adopted_dir}/articles.json", "sha256": source_sha},
        "counts": {"clocks": len(CLOCKS_ADOPTED)},
        "clocks": CLOCKS_ADOPTED,
    }

    draft_article = RENUM_ADOPTED_TO_DRAFT[7]
    draft_clocks = _renumber_for_draft(CLOCKS_ADOPTED, draft_article=draft_article)
    draft_doc = {
        "schema": SCHEMA,
        "ruleset_key": draft_dir,
        "article_scheme": "draft",
        "generated_at": _now_iso(),
        "source": {
            "derived_from": f"rulesets/{adopted_dir}/clocks.json",
            "renumbering": f"adopted Article 7 -> draft Article {draft_article} (RENUM_ADOPTED_TO_DRAFT)",
        },
        "counts": {"clocks": len(draft_clocks)},
        "clocks": draft_clocks,
    }

    out_adopted = RULESETS_DIR / adopted_dir / "clocks.json"
    out_draft = RULESETS_DIR / draft_dir / "clocks.json"
    _atomic_write_json(out_adopted, adopted_doc)
    _atomic_write_json(out_draft, draft_doc)
    print(
        f"F3 coverage: {coverage['found']} Article 7 'within ... days' clauses found "
        f"-> {coverage['covered_by_clock']} covered by a clock, "
        f"{coverage['excluded']} explicitly excluded (documented), 0 uncovered."
    )
    print(
        f"F5 track coverage: {track_coverage['universal_clocks_checked']} track-agnostic "
        f"clocks checked against {track_coverage['tracks_required']} review tracks, 0 missing."
    )
    return {"adopted": out_adopted, "draft": out_draft}


if __name__ == "__main__":
    paths = build_clocks()
    for k, p in paths.items():
        print(f"wrote {k}: {p}")
