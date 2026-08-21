"""The statutory deadline engine (W3).

Not itself a CONTRACT.md-numbered section (the deadline clocks were
commissioned by the W3 task brief; CONTRACT.md only sketches the `deadlines`
table's SHAPE, in its §3.4 "deterministic dates" discussion and the
app/migrations/0001_init.sql comment above `CREATE TABLE deadlines`). This
module extends that same posture -- CONTRACT.md §1 S10 ("anything derivable
is computed, never typed in") and §1 S7 ("no silent guessing; ambiguity is
collected, never resolved") -- to the 18 Article 7 (Administration; draft
Article 8) clocks transcribed in rulesets/<ruleset_key>/clocks.json by
ruleset_build/build_clocks.py.

SCOPE BOUNDARY. This module is a PURE COMPUTATION ENGINE: given a case's known
facts (submission date, notice/hearing/decision milestones, ...), it computes
the full set of applicable deadlines and their status. It does not write to
the `deadlines` SQLite table itself -- CONTRACT.md §3.3 requires every
mutating table to carry an `events` audit row in the SAME transaction as the
write, and wiring that (case creation, milestone recording, HTTP endpoints)
is the job of app/main.py and whatever workflow owns `cases`/`case_milestones`
writes, not this module. `open_deadlines(conn)` below only ever SELECTs.
`deadline_row()` shapes a Deadline into the exact dict the `deadlines` table's
columns expect, ready for that future writer to INSERT -- CONTRACT.md's
"A deadline row is created when its start event occurs, and satisfied when
its satisfying event occurs" happens at the DATA level here (a Deadline object
only exists, with a due_date, once its start_event date is known -- see
ClockStatus.PENDING_START below) even though no row reaches the `deadlines`
table from this module directly.

NAMING NOTE FOR WHOEVER RECONCILES THIS LATER (same situation app/dates.py
documents for app/meetings.py): app/migrations/0002_case_tracking.sql's own
docstring says "app/deadlines.py reads the LIVE set (superseded_by IS NULL)
[of case_milestones] as the anchor dates its clocks compute from" -- a
concurrently-written sibling migration named `app/deadlines.py` as this
engine's home. The W3 task brief that commissioned THIS module named
`engine/deadlines.py` instead (CONTRACT.md's own directory layout, §2, marks
`engine/` as "LATER: rules -> criteria sets -> findings_nodes", which is
exactly what this is). Rather than silently pick a winner, the implementation
lives here and `app/deadlines.py` re-exports it under the sibling's expected
name -- see that file. Do not implement this arithmetic a second time in
either location.

CASE FACTS AND case_milestones. `case_milestones.kind` (originally
0002_case_tracking.sql, widened by 0003_case_lifecycle.sql and, as of the F6
adversarial-review fix, 0005_deadline_engine_fixes.sql) carries the full
event vocabulary this module needs, INCLUDING the two statutory events that
used to have no dedicated kind:
  - "findings of fact issued" (§12.e.6) -- distinct from the §12.e.5 decision
  - "variance certificate recorded" (§19.c.3) -- distinct from plat_recorded
Both are now first-class kinds ('findings_issued', 'certificate_recorded'),
handled by the same generic `_MILESTONE_TO_FIELD` loop as every other kind in
case_facts_from_row() below. PRIOR BEHAVIOUR (retired 2026-08, F6): this
module used to bridge both through the generic 'other' kind's free-text
`note` field via a case-insensitive substring match on "finding" /
"certificate" -- an undocumented magic string no operator could discover
from the UI, and one whose if/elif ordering meant a note mentioning both
words silently dropped the certificate. That bridging code, and the
`case_facts_from_milestones()` name once used for it, no longer exist; do
not resurrect the pattern.

N2 (2026-08): 0006_appeal_recordability.sql widened the same CHECK a second
time, adding 'appeal_hearing_opened', 'appeal_hearing_closed',
'appeal_decision', and 'reconsideration_decided' -- the four §23
appeal-track events administrative_appeal_hearing/_decision/
reconsideration_decision have named since F3 but that, before this fix, NO
case_milestones.kind could record at all (not a bridging-convention gap like
F6's; a genuinely missing kind, CASE_MILESTONE_KINDS entry, field mapping,
and UI option, all four). See the CaseFacts dataclass fields below,
_MILESTONE_TO_FIELD, and ruleset_build.verify_structure.
check_clock_event_recordability -- the standing build-time assertion that
now catches this defect class (a clock naming an unrecordable event) before
it ships, over EVERY clock, not just these four.

TWO GENUINE AMBIGUITIES ARE LOGGED IN DECISIONS-NEEDED.md (D-0006, D-0008, D-0009):
  - D-0006: no Maine state holiday calendar -- business-day math only excludes
    weekends (documented limitation, not a guess at which holidays apply).
  - D-0008: which recorded fact is Article 7's "receiving" / "submission of an
    application" that starts every downstream clock -- `cases.received_at`
    (the Town's formal receipt) vs. the `application_dated` milestone (the
    date printed on the form). This module prefers `received_at`, falling
    back to `application_dated_at` -- see CaseFacts.submitted_at_source.
  - D-0009: the §5.c.3 notice clock's literal text ties the 7-business-day
    window to "submission of an application", but for hearing-based tracks
    notice content must include "time, date and location of first scheduled
    meeting" -- impossible to know before a hearing date is set.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import Enum
from functools import lru_cache
from typing import Any, Iterable, Optional

from app import citation
from app.citation import Citation
from app.config import RULESETS_DIR
from app.meetings import draft_due, next_meeting  # reuse, do not reimplement (CONTRACT.md §3.4)

# --------------------------------------------------------------------------- #
# Maine legal holiday calendar -- 4 M.R.S. section 1051 ("Legal holidays")
# --------------------------------------------------------------------------- #
#
# VERIFIED 2026-08-21 directly against the Maine Legislature's own statute
# pages (legislature.maine.gov/statutes/4/title4sec1051-1.html, cross-checked
# against the mirror at mainelegislature.org), current through the section's
# most recent amendment, PL 2021, c. 676, Pt. A, section 2 (the amendment that
# added Juneteenth). DECISIONS-NEEDED D-0006, as originally raised, guessed
# this list might live in Title 1 -- it does not. Title 4 is Judiciary; this
# section's operative sentence is "Court may not be held on Sunday or any day
# designated for the annual Thanksgiving; New Year's Day, ...".
#
# WHAT THE STATUTE ACTUALLY BINDS. Read narrowly, section 1051 (a) forbids
# COURT sessions on these dates, and (b) permits -- does not require --
# "public offices in county buildings" to close. It says nothing about
# municipal/town offices. Applying this list to Newcastle's Town Clerk is
# therefore the best available INFERENCE (this is the one list every Maine
# institution means by "the legal holidays," and no separate Newcastle
# Town Office closure list is on file with this project), not a textual
# certainty -- see DECISIONS-NEEDED D-0010 for the residual, still-open gap
# (Newcastle may also close, e.g., the day after Thanksgiving, which is NOT
# one of the 12 dates below; conversely it may not observe every one of the
# 12 as a full closure).
#
# THE 12 HOLIDAYS, AS ENACTED:
#   New Year's Day .......... January 1
#   Martin Luther King Day ... 3rd Monday in January
#   Washington's Birthday .... 3rd Monday in February
#   Patriots' Day ............ 3rd Monday in April
#   Memorial Day .............. last Monday in May
#     (the statute's own rider -- "but if the Federal Government designates
#     May 30th ... the 30th of May" -- has had no live effect since the 1968
#     Uniform Monday Holiday Act fixed the federal observance as the last
#     Monday in May; not encoded, since encoding it would require guessing a
#     federal designation that in practice never recurs)
#   Juneteenth ................ June 19
#   Independence Day .......... July 4
#   Labor Day .................. 1st Monday in September
#   Indigenous Peoples Day ..... 2nd Monday in October
#   Veterans Day ............... November 11
#   Thanksgiving ................ "any day designated for the annual
#     Thanksgiving" -- the statute names no formula. Encoded here as the 4th
#     Thursday in November, matching both the federal legal holiday (5
#     U.S.C. section 6103) and Maine's own uninterrupted gubernatorial
#     proclamation practice; this is a documented, non-blocking inference,
#     not a guess invented from nothing -- flagged again in D-0010.
#   Christmas Day ............... December 25
#
# SUNDAY-OBSERVANCE RULE, per the statute's own closing sentence: "When any
# one of the holidays named in this section falls on Sunday, the Monday
# following must be observed as a holiday." Only the five FIXED-date
# holidays above can land on a Sunday (every floating holiday is defined as
# a Monday or Thursday already); the rule is applied only to those five.
# Maine's statute states no analogous Saturday-shift rule, and none is
# invented here.


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """The n-th (1-indexed) occurrence of `weekday` (Mon=0..Sun=6) in
    (year, month). E.g. n=3, weekday=0 -> the 3rd Monday."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return date.fromordinal(first.toordinal() + offset + 7 * (n - 1))


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """The LAST occurrence of `weekday` in (year, month)."""
    next_month_first = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    last_day = date.fromordinal(next_month_first.toordinal() - 1)
    offset = (last_day.weekday() - weekday) % 7
    return date.fromordinal(last_day.toordinal() - offset)


_ME_HOLIDAY_CITATION = "4 M.R.S. §1051 (\"Legal holidays\"), PL 2021, c. 676, Pt. A, §2"


def _fixed_me_holidays(year: int) -> dict[date, str]:
    out: dict[date, str] = {}

    def add(d: date, label: str) -> None:
        if d.weekday() == 6:  # Sunday -> the following Monday is observed instead
            observed = date.fromordinal(d.toordinal() + 1)
            out[observed] = f"{label} (observed; {d.isoformat()} is a Sunday)"
        else:
            out[d] = label

    add(date(year, 1, 1), "New Year's Day")
    add(date(year, 6, 19), "Juneteenth")
    add(date(year, 7, 4), "Independence Day")
    add(date(year, 11, 11), "Veterans Day")
    add(date(year, 12, 25), "Christmas Day")
    return out


def _floating_me_holidays(year: int) -> dict[date, str]:
    return {
        _nth_weekday_of_month(year, 1, 0, 3): "Martin Luther King, Jr. Day",
        _nth_weekday_of_month(year, 2, 0, 3): "Washington's Birthday",
        _nth_weekday_of_month(year, 4, 0, 3): "Patriots' Day",
        _last_weekday_of_month(year, 5, 0): "Memorial Day",
        _nth_weekday_of_month(year, 9, 0, 1): "Labor Day",
        _nth_weekday_of_month(year, 10, 0, 2): "Indigenous Peoples Day",
        _nth_weekday_of_month(year, 11, 3, 4): "Thanksgiving",
    }


@lru_cache(maxsize=None)
def maine_legal_holidays(year: int) -> tuple[tuple[date, str], ...]:
    """The 12 Maine legal holidays (4 M.R.S. section 1051) for `year`, as
    `(date, label)` pairs. Cached -- pure function of `year`."""
    merged: dict[date, str] = {}
    merged.update(_fixed_me_holidays(year))
    merged.update(_floating_me_holidays(year))
    return tuple(sorted(merged.items()))


def maine_legal_holiday_label(d: date) -> Optional[str]:
    """The holiday label if `d` is a Maine legal holiday (4 M.R.S. section
    1051), else None."""
    for hol_date, label in maine_legal_holidays(d.year):
        if hol_date == d:
            return label
    return None


# --------------------------------------------------------------------------- #
# Business-day / month arithmetic
# --------------------------------------------------------------------------- #


def is_business_day(d: date) -> bool:
    """Weekday (Mon-Fri) AND not a Maine legal holiday under 4 M.R.S.
    section 1051 -- see the calendar above. DECISIONS-NEEDED D-0006 is
    RESOLVED for this statutory floor; D-0010 tracks the still-open,
    narrower question of whether Newcastle's own Town Office closures match
    this list exactly (they may close additional days, or not close on
    every one of these)."""
    if d.weekday() >= 5:
        return False
    return maine_legal_holiday_label(d) is None


def add_business_days(start: date, n: int) -> date:
    """`n` business days AFTER `start` (matching "within N business days of
    X" -- X's own date is day zero and is never itself counted, whether or
    not it is a business day). n must be >= 0; every clock in this module
    only ever counts forward."""
    if n < 0:
        raise ValueError("add_business_days: n must be >= 0")
    d = start
    remaining = n
    while remaining > 0:
        d = date.fromordinal(d.toordinal() + 1)
        if is_business_day(d):
            remaining -= 1
    return d


def add_calendar_days(start: date, n: int) -> date:
    return date.fromordinal(start.toordinal() + n)


def add_months(start: date, n: int) -> date:
    """Calendar-month arithmetic (the §12.j.1 / §8.f.5 six-month recording
    clock). Clamps the day-of-month when the target month is shorter (e.g.
    Aug 31 + 6 months -> Feb 28/29, never Mar 3)."""
    month_index = start.month - 1 + n
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    # Last valid day of the target month.
    if month == 12:
        days_in_month = (date(year + 1, 1, 1) - date(year, 12, 1)).days
    else:
        days_in_month = (date(year, month + 1, 1) - date(year, month, 1)).days
    day = min(start.day, days_in_month)
    return date(year, month, day)


# --------------------------------------------------------------------------- #
# Status
# --------------------------------------------------------------------------- #


class ClockStatus(str, Enum):
    PENDING_START = "pending_start"  # start_event hasn't happened yet
    OPEN = "open"                    # started, due date in the future, not yet satisfied
    MET = "met"                      # satisfied on or before the due date
    MISSED = "missed"                # due date passed (satisfied late, or not satisfied at all)
    WAIVED = "waived"                # a human recorded this clock as waived for this case
    NOT_APPLICABLE = "n/a"           # a human recorded this clock as not applicable
    # 2026-08 clock-taxonomy repair round (dissolves N1 and the
    # reconsideration half of N2 -- see the DutyKind docstring below).
    NOT_TRIGGERED = "not_triggered"  # duty_kind=conditional_duty, predicate event not (yet) recorded
    ELAPSED = "elapsed"              # duty_kind=party_right, window closed unexercised -- never a
                                      # duty, never a Town failure, so never MISSED


TERMINAL_STATUSES = {ClockStatus.MET, ClockStatus.WAIVED, ClockStatus.NOT_APPLICABLE}
DASHBOARD_STATUSES = {ClockStatus.OPEN, ClockStatus.MISSED}


# --------------------------------------------------------------------------- #
# Clock definitions -- loaded from rulesets/<ruleset_key>/clocks.json
# (ruleset_build/build_clocks.py). Runtime never re-parses repo source
# (the same posture as app/rulesets.py and app/reviews.py for the §4 rulesets).
# --------------------------------------------------------------------------- #


class DutyKind(str, Enum):
    """The clock taxonomy (2026-08 repair round). Every clock in clocks.json
    carries exactly one of these, classified from its OWN governing sentence
    in articles.json by ruleset_build/build_clocks.py (DUTY_KINDS there is
    the single source of truth for the allowed set; this Enum mirrors it for
    engine-side type safety and MUST stay in sync).

    MUNICIPAL_DUTY   -- the Town (a named official or board) MUST act by a
                         date. Can be MISSED. presents_auto_approval_risk()
                         derives ONLY from clocks of this kind.
    APPLICANT_DUTY   -- a private applicant MUST act by a date (e.g. record
                         an approved plan). Mandatory, so it CAN be missed,
                         but never the Town's failure, never §8.d.1 risk.
    PARTY_RIGHT      -- a private party MAY act within a window (file an
                         appeal, request reconsideration). The window
                         ELAPSES if unused -- never MISSED, never an alert,
                         never a consequence.
    CONDITIONAL_DUTY -- a municipal duty that exists ONLY once a predicate
                         event occurs (an appeal hearing exists only if an
                         appeal was filed). NOT_TRIGGERED until then -- no
                         alert, no at-risk view, while untriggered.
    """

    MUNICIPAL_DUTY = "municipal_duty"
    APPLICANT_DUTY = "applicant_duty"
    PARTY_RIGHT = "party_right"
    CONDITIONAL_DUTY = "conditional_duty"
    INFORMATIONAL = "informational"  # engine-only: the synthetic meeting/
    # draft_due clocks below (not sourced from clocks.json's 22 statutory
    # clocks) -- a derived/advisory date with no duty at all.


@dataclass(frozen=True)
class Clock:
    clock_key: str
    label: str
    article: int
    section: str
    subsection: str
    start_event: str
    satisfying_event: str
    days: int
    basis: str  # "calendar" | "business" | "months"
    applies_to: tuple[str, ...]
    failure_consequence: Optional[str]
    db_kind: str
    duty_kind: str = DutyKind.MUNICIPAL_DUTY.value
    predicate_event: Optional[str] = None
    duty_kind_note: Optional[str] = None
    requires_absent: tuple[str, ...] = ()
    starts_clock: Optional[str] = None
    conflict_group: Optional[str] = None
    conflict_note: Optional[str] = None
    never_autogenerate_condition: bool = False
    notes: Optional[str] = None
    scheme: str = "adopted"

    def citation(self) -> Citation:
        return Citation(
            ruleset_key=self.scheme if self.scheme != "adopted" else "adopted",
            scheme=self.scheme,
            article=self.article,
            section=self.section,
            subsection=self.subsection,
        )


class ClocksNotFound(FileNotFoundError):
    """rulesets/<ruleset_key>/clocks.json hasn't been built yet. Run
    `python -m ruleset_build.build_clocks` from build/permit-review/."""


@lru_cache(maxsize=None)
def load_clocks(ruleset_key: str = "adopted") -> tuple[Clock, ...]:
    path = RULESETS_DIR / ruleset_key / "clocks.json"
    if not path.exists():
        raise ClocksNotFound(
            f"no clocks.json for ruleset {ruleset_key!r} at {path} -- "
            f"run `python -m ruleset_build.build_clocks` first"
        )
    doc = json.loads(path.read_text(encoding="utf-8"))
    scheme = doc.get("article_scheme", "adopted")
    out = []
    for c in doc["clocks"]:
        cit = c["citation"]
        out.append(
            Clock(
                clock_key=c["clock_key"],
                label=c["label"],
                article=cit["article"],
                section=cit["section"],
                subsection=cit["subsection"],
                start_event=c["start_event"],
                satisfying_event=c["satisfying_event"],
                days=c["days"],
                basis=c["basis"],
                applies_to=tuple(c["applies_to"]),
                failure_consequence=c.get("failure_consequence"),
                db_kind=c["db_kind"],
                duty_kind=c["duty_kind"],
                predicate_event=c.get("predicate_event"),
                duty_kind_note=c.get("duty_kind_note"),
                requires_absent=tuple(c.get("requires_absent", []) or []),
                starts_clock=c.get("starts_clock"),
                conflict_group=c.get("conflict_group"),
                conflict_note=c.get("conflict_note"),
                never_autogenerate_condition=bool(c.get("never_autogenerate_condition", False)),
                notes=c.get("notes"),
                scheme=scheme,
            )
        )
    return tuple(out)


# --------------------------------------------------------------------------- #
# FINDING 3 -- which clocks Article 7 §6.e.1 lets the applicant and
# Permitting Authority agree, in writing, to extend. §6.e.1's own text names
# two categories: "(a) The time limit required for commencement of a public
# hearing; (b) The time limit required to make a decision." Neither category
# is spelled out clock-by-clock anywhere in the Code, so mapping it onto the
# 22 clocks in rulesets/adopted/clocks.json is an implementation choice, not
# a textual certainty -- logged as DECISIONS-NEEDED D-0024, not silently
# guessed. The mapping implemented here:
#
#   - only municipal_duty / conditional_duty clocks are eligible at all --
#     §6.e.1 extends a PERMITTING AUTHORITY time limit, never an
#     applicant_duty clock (e.g. the two plat-recording clocks,
#     variance_certificate_recorded) and never a party_right window (e.g.
#     administrative_appeal, reconsideration -- a private party's own right
#     to act, not a Town time limit to extend);
#   - "(a) commencement of a public hearing" -> a clock whose satisfying_event
#     IS a hearing opening (hearing_opened_at, appeal_hearing_opened_at);
#   - "(b) ... to make a decision" -> a clock whose satisfying_event is a
#     decision-family event (decision_at, findings_issued_at,
#     decision_filed_at, appeal_decision_at, reconsideration_decided_at --
#     findings issuance and clerk filing are grouped with "decision" as the
#     Town-side acts that follow directly from deciding, not as their own
#     third category §6.e.1 never names).
# --------------------------------------------------------------------------- #

_EXTENDABLE_DUTY_KINDS: frozenset[str] = frozenset(
    {DutyKind.MUNICIPAL_DUTY.value, DutyKind.CONDITIONAL_DUTY.value}
)
_HEARING_COMMENCEMENT_SATISFYING_EVENTS: frozenset[str] = frozenset(
    {"hearing_opened_at", "appeal_hearing_opened_at"}
)
_DECISION_SATISFYING_EVENTS: frozenset[str] = frozenset(
    {"decision_at", "findings_issued_at", "decision_filed_at", "appeal_decision_at", "reconsideration_decided_at"}
)


def _extension_eligible(duty_kind: str, satisfying_event: str) -> bool:
    if duty_kind not in _EXTENDABLE_DUTY_KINDS:
        return False
    return (
        satisfying_event in _HEARING_COMMENCEMENT_SATISFYING_EVENTS
        or satisfying_event in _DECISION_SATISFYING_EVENTS
    )


def clock_is_extendable(clock: Clock) -> bool:
    """Whether Article 7 §6.e.1 lets this clock be extended by written
    agreement -- see the block comment above and DECISIONS-NEEDED D-0024.
    The single source of truth app.cases.record_dates checks a proposed
    `extension_agreed` entry's target_clock_key against."""
    return _extension_eligible(clock.duty_kind, clock.satisfying_event)


def extendable_clock_keys(ruleset_key: str = "adopted") -> frozenset[str]:
    """Every clock_key in `ruleset_key` eligible for a §6.e.1 extension --
    see clock_is_extendable()."""
    return frozenset(c.clock_key for c in load_clocks(ruleset_key) if clock_is_extendable(c))


# --------------------------------------------------------------------------- #
# Case facts -- the DB-agnostic input to compute_deadlines(). Every field is
# an Optional[date]; a None means "hasn't happened / isn't recorded", which
# is exactly what CONTRACT.md's framing rule wants ("honest blanks beat
# confident guesses") applied to dates instead of dimensional standards.
# --------------------------------------------------------------------------- #

REVIEW_TRACKS = (
    "small_project_plan",
    "large_project_plan",
    "subdivision",
    "special_permit",
    "variance",
    # HARD-FINAL round, Finding 5: use/expanded_use now carry a real §15.d.1
    # decision clock (use_permit_decision, F3) AND the Code's general filing/
    # appeal machinery (decision_filed_with_clerk §8.f.1; administrative_
    # appeal/_hearing/_decision §23.d.1-.d.3) -- see
    # ruleset_build/build_clocks.py's F5 docstring paragraph and
    # _assert_track_coverage(). Before this fix these two application_type
    # values produced zero clocks and were deliberately absent here.
    "use",
    "expanded_use",
    "administrative_appeal",
)


@dataclass
class CaseFacts:
    case_id: str
    review_track: str  # one of REVIEW_TRACKS
    ruleset_key: str = "adopted"
    is_scratch: bool = False
    label: str = ""

    submitted_at: Optional[date] = None
    # "application_received" | "received_at" | "application_dated" -- see D-0008
    submitted_at_source: Optional[str] = None

    forwarded_to_pb_at: Optional[date] = None
    completeness_at: Optional[date] = None
    notice_mailed_at: Optional[date] = None
    notice_published_at: Optional[date] = None
    hearing_opened_at: Optional[date] = None
    hearing_closed_at: Optional[date] = None
    decision_at: Optional[date] = None
    decision_filed_at: Optional[date] = None
    findings_issued_at: Optional[date] = None
    plat_recorded_at: Optional[date] = None
    certificate_recorded_at: Optional[date] = None
    appeal_filed_at: Optional[date] = None
    reconsideration_requested_at: Optional[date] = None
    # F3's §23 appeal-track clocks (administrative_appeal_hearing,
    # administrative_appeal_decision, reconsideration_decision --
    # rulesets/adopted/clocks.json) name these four events. N2 FIX
    # (0006_appeal_recordability.sql + _MILESTONE_TO_FIELD above): each now
    # has a dedicated case_milestones.kind and is genuinely recordable end to
    # end (app.cases.CASE_MILESTONE_KINDS, the migration CHECK constraint,
    # and the operator UI dropdown all carry it -- see
    # ruleset_build.verify_structure.check_clock_event_recordability, the
    # standing build gate that gave this defect class no way back). Before
    # that fix, every one of these four fields was honestly None forever --
    # no case_milestones.kind could ever populate it -- which is why two
    # §8.d.1-bearing clocks (administrative_appeal_hearing, _decision) could
    # never be cleared by a timely appeal hearing/decision.
    appeal_hearing_opened_at: Optional[date] = None
    appeal_hearing_closed_at: Optional[date] = None
    appeal_decision_at: Optional[date] = None
    reconsideration_decided_at: Optional[date] = None
    # HARD-FINAL round, Finding 6: reconsideration_decision's predicate_event
    # (rulesets/adopted/clocks.json) narrowed from reconsideration_requested_at
    # (the §23.e.1 REQUEST, a party_right) to reconsideration_voted_at (the
    # §23.e.2/.e.3 VOTE TO RECONSIDER) -- matching §23.e.4's own conditional
    # ("If the Board of Appeals reconsiders its original decision..."). A
    # request that never reaches a majority vote to reconsider must not flip
    # this clock live; see ruleset_build/build_clocks.py's reconsideration_
    # decision duty_kind_note and app/migrations/0011_reconsideration_vote.sql.
    reconsideration_voted_at: Optional[date] = None

    meeting_date: Optional[date] = None  # explicit calendared PB meeting; else computed

    # Human-recorded overrides -- CONTRACT.md's framing rule (§ "THE FRAMING
    # RULE") applies here too: a clock only ever leaves OPEN/MISSED because a
    # human said so, never because this engine inferred it.
    #
    # FINDING 3 FIX (2026-08, HARD-FINAL round): before this fix, both fields
    # existed here and were read by _evaluate_clock() below, but
    # case_facts_from_row() never populated either one from anything in the
    # database -- no case_milestones.kind, no column, no write path existed
    # for a human to actually record a waiver or an n/a determination. They
    # were reachable only by constructing a CaseFacts directly (tests).
    # 0010_clock_extensions.sql adds the 'clock_waived' / 'clock_not_applicable'
    # case_milestones kinds; case_facts_from_row() below now populates both
    # sets from the LIVE rows of each (app.cases.record_dates is the write
    # path, requiring target_clock_key and a non-empty `note` -- the "why").
    waived_clocks: frozenset[str] = field(default_factory=frozenset)
    na_clocks: frozenset[str] = field(default_factory=frozenset)

    # FINDING 3 (2026-08, HARD-FINAL round). Article 7 §6.e.1: "Upon mutual
    # agreement by the applicant and the Permitting Authority, the following
    # procedural requirements may be extended: (a) The time limit required
    # for commencement of a public hearing; (b) The time limit required to
    # make a decision." §6.e.2 requires the agreement "recorded in writing."
    # §8.d.1 itself is qualified "...within the maximum time requirement OR
    # PERMITTED EXTENSIONS, AS APPLICABLE" -- so a clock genuinely extended
    # under §6.e.1 is, by the Code's own words, not a §8.d.1 failure at all.
    #
    # Maps a clock_key to the TOTAL number of extra days (in that clock's own
    # basis -- calendar/business/months) agreed for it, summed across every
    # LIVE 'extension_agreed' case_milestones row naming it as
    # target_clock_key (case_facts_from_row() below does the summing;
    # multiple written agreements against the same clock ACCUMULATE -- a
    # second agreement is a second extension, not a replacement of the
    # first; §6.e.1 caps neither how many times the parties may agree again
    # nor how many days each agreement may add). _evaluate_clock() adds this
    # to clock.days before computing due_date.
    #
    # EXTENDS vs TOLLS (DECISIONS-NEEDED D-0022, NOT decided here): whether
    # §6.e.1 pushes the due date out by the agreed day count (EXTENDS) or
    # instead pauses the clock for some interval (TOLLS) is a genuine legal
    # question this module does not resolve. The CONSERVATIVE reading is
    # implemented: due_date = due_date + extension_days, in the clock's own
    # basis, from a single recorded day count -- bounded and fully
    # determined by the written agreement itself, never an open-ended
    # suspension. See D-0022 for why this is the conservative choice.
    #
    # ELIGIBILITY (DECISIONS-NEEDED D-0024): only clocks
    # engine.deadlines.clock_is_extendable() accepts -- a municipal_duty or
    # conditional_duty clock whose satisfying_event is a hearing commencement
    # or a decision -- are ever written here; app.cases.record_dates enforces
    # that at the write boundary (a clocks.json/CaseFacts mismatch would
    # otherwise let an operator "extend" e.g. an applicant's own plat-recording
    # duty, which §6.e.1 does not reach).
    clock_extension_days: dict[str, int] = field(default_factory=dict)

    # F7 FIX: no longer "informational only" -- _first_satisfying_occurrence()
    # below reads this to find the FIRST GENUINE recorded occurrence of a
    # SATISFYING event, even one later superseded (a re-notice) for display
    # purposes elsewhere. Each entry is {"kind": <case_milestones.kind>,
    # "occurred_on": <ISO date str, or None if honestly unknown>, "note": ...,
    # "superseded": <bool>, "supersede_reason": <"reschedule"|"correction"|None>}.
    # N3 FIX: `supersede_reason` (0007_supersede_reason.sql) distinguishes a
    # superseded row that genuinely happened and satisfied a live duty
    # ("reschedule") from one that was factually wrong and never satisfied
    # anything ("correction") -- see _first_satisfying_occurrence(). Still
    # carried through unchanged for a caller (dashboard, findings draft) to
    # narrate the case's real history without this engine collapsing it.
    history: tuple[dict[str, Any], ...] = ()

    # F8: every generated_documents row of kind findings_draft/findings_final
    # for this case (its `generated_at` date) -- the draft_due clock's real
    # satisfying event ("a draft actually exists for the packet"), not merely
    # "today is on or after the due date". Empty when built directly (most
    # tests) or when no draft has been generated yet.
    draft_documents: tuple[date, ...] = ()


@dataclass(frozen=True)
class NoticeEvent:
    mailed_at: Optional[date] = None
    published_at: Optional[date] = None
    note: Optional[str] = None


# --------------------------------------------------------------------------- #
# The field resolver -- maps a clock's start_event/satisfying_event string to
# the CaseFacts attribute it names. A KeyError here is a build-time bug in
# clocks.json (an event name with no CaseFacts field), never a runtime guess.
#
# F7 -- EVENT ROLES. A clock names an event TWICE: once as its start_event
# ("when does the clock begin?") and once as its satisfying_event ("was the
# duty performed?"). The SAME CaseFacts field can play either role depending
# on which clock is asking (e.g. decision_at STARTS subdivision_findings_issued
# but SATISFIES subdivision_hearing_decision) -- so the role belongs to the
# CALL, not the field. A STARTING event legitimately moves (a hearing
# reopened and closed again on a later date supersedes the earlier close as
# the operative start for what comes next) -- role="start" reads the plain
# CaseFacts scalar, which is already "the latest LIVE occurrence" per
# case_facts_from_row(). A SATISFYING event asks a yes/no historical
# question -- role="satisfying" consults the FULL milestone history
# (case.history, which -- unlike the scalar fields -- includes rows later
# superseded for display purposes) and returns the EARLIEST dated GENUINE
# occurrence on record, because the duty was performed the first time it
# genuinely happened, not the last time the record was updated. See
# _first_satisfying_occurrence() below and CONTRACT.md §1 S7/S10.
#
# N3 -- "genuine" is doing real work in that sentence. A superseded history
# row is only a genuine occurrence when it was superseded for a RESCHEDULE
# (the original notice really was mailed and really did satisfy the duty
# live at the time; a later re-notice for a moved hearing doesn't erase
# that). A row superseded as a CORRECTION never really happened as recorded
# at all -- it is a typo/data-entry error being fixed -- and must never be
# allowed to satisfy anything, no matter how early its date. Before this
# fix, `_first_satisfying_occurrence()` could not tell the two apart and
# always took the earliest date, full stop; a corrected typo could satisfy a
# duty that was actually missed. See `case_milestones.supersede_reason`
# (0007_supersede_reason.sql) and _is_genuine_history_entry() below.
# --------------------------------------------------------------------------- #


def _is_genuine_history_entry(h: dict[str, Any]) -> bool:
    """N3: whether one `case.history` entry counts as a real occurrence for
    satisfying-role purposes.

    A LIVE row (never superseded) is always genuine -- it is the record's
    current statement of what happened, full stop.

    A SUPERSEDED row is genuine only when it carries
    `supersede_reason == "reschedule"` -- an explicit, human-recorded
    statement that the row really happened and satisfied the duty live at
    the time (app/cases.py:record_dates requires this reason at write time
    going forward; see that module's docstring). Every other case --
    `supersede_reason == "correction"`, OR a legacy/pre-0006 row where the
    reason was never recorded at all (None) -- is NOT genuine: CONTRACT.md's
    framing rule ("honest blanks beat confident guesses") means an
    unverified superseded date must never be allowed to manufacture
    compliance the record cannot actually back up. This is the CONSERVATIVE
    default DECISIONS-NEEDED.md D-0016 documents -- it can only ever make
    the engine under-credit a duty that really was performed on time (an
    operator can always re-supply the missing `supersede_reason` to fix
    that), never over-credit one that was not.
    """
    if not h.get("superseded"):
        return True
    return h.get("supersede_reason") == "reschedule"


def _first_satisfying_occurrence(case: CaseFacts, field_name: str) -> Optional[date]:
    """F7/N3: the EARLIEST dated GENUINE occurrence of `field_name` in
    `case.history` (matched via `_MILESTONE_TO_FIELD`'s kind->field mapping;
    genuineness via `_is_genuine_history_entry()` -- see the block comment
    above), ignoring entries with an honestly-unknown date (occurred_on None
    -- never treated as "counts as day zero") OR a malformed one (never
    raises -- history can hold a SUPERSEDED row this module never validated
    at write time, and F5's write-time validation is the right place to
    reject a bad value, not this read-only lookup; a row so malformed it
    can't be parsed simply doesn't count as an occurrence, same as one with
    no date at all). Falls back to the plain CaseFacts scalar when history
    has no dated GENUINE match at all -- the common case for a CaseFacts
    built directly (most tests, and every field that appears at most once),
    where first == latest == the one value on record, and for a CaseFacts
    whose `history` simply wasn't populated with that kind."""
    dated = sorted(
        d
        for h in case.history
        if _MILESTONE_TO_FIELD.get(h.get("kind")) == field_name and _is_genuine_history_entry(h)
        for d in (parse_date_or_none(h.get("occurred_on")),)
        if d is not None
    )
    if dated:
        return dated[0]
    return getattr(case, field_name)


def _resolve_event(case: CaseFacts, event_name: str, *, role: str = "start") -> Optional[date]:
    if not hasattr(case, event_name):
        raise AttributeError(
            f"clocks.json names event {event_name!r}, which CaseFacts has no "
            f"field for -- this is a clocks.json/CaseFacts mismatch, not a "
            f"missing case fact"
        )
    if role == "satisfying":
        return _first_satisfying_occurrence(case, event_name)
    return getattr(case, event_name)


# --------------------------------------------------------------------------- #
# Deadline -- one clock, evaluated against one case's facts.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Deadline:
    case_id: str
    clock_key: str
    label: str
    citation_long: str
    citation_short: str
    rule_key: str  # e.g. "art7.clock.notice_mailed" -- deadlines.rule_key shape
    db_kind: str  # the closest app/migrations/0001_init.sql deadlines.kind bucket
    duty_kind: str  # DutyKind value -- see that Enum's docstring
    basis: str
    days: int
    start_event: str
    start_date: Optional[date]
    satisfying_event: str
    satisfied_at: Optional[date]
    due_date: Optional[date]
    status: str  # ClockStatus value
    failure_consequence: Optional[str]
    auto_approval_alert: Optional[str]
    conflict_group: Optional[str]
    conflict_note: Optional[str]
    never_autogenerate_condition: bool
    notes: Optional[str]
    # F4: set only when this clock is PENDING_START AND its statutory
    # predecessor (the clock whose satisfying_event IS this clock's
    # start_event) is itself MISSED -- see _attach_start_not_recorded_alerts().
    # Never invents a start date; it only makes an otherwise-silent stall
    # visible. Defaults to None for every other Deadline.
    start_not_recorded_alert: Optional[str] = None
    # N4: set only when a satisfying occurrence WAS found but PREDATES this
    # clock's own start_date, so it could not count (see _evaluate_clock's
    # N4 FIX comment) -- "the duty reopens" made visible, the same honest-
    # blank-over-confident-guess posture as start_not_recorded_alert above,
    # for the opposite situation (too EARLY a date, not a missing one).
    # `satisfied_at` is None whenever this is set; the rejected date lives
    # here instead, so a caller can still say "a filing DID happen, on X --
    # it just doesn't count for the current duty" rather than looking like
    # nothing was ever recorded.
    stale_satisfaction_at: Optional[date] = None
    # FINDING 3: the total case.clock_extension_days already folded into
    # `due_date` above (0 for every clock with no recorded §6.e.1 agreement,
    # which is every clock on every case before this fix existed). Carried
    # separately, rather than leaving a caller to infer it by comparing
    # against clock.days, so "this due date was moved by a written
    # extension" is a fact the deadlines table/UI can state directly (the
    # Finding 3 task's "see which clocks it moved").
    extension_days_applied: int = 0


def deadline_is_extendable(d: Deadline) -> bool:
    """The Deadline-shaped twin of clock_is_extendable() -- same eligibility
    test (DECISIONS-NEEDED D-0024), for a caller (the case-detail UI's
    extension form) that already has a computed Deadline and shouldn't have
    to re-load clocks.json to ask the same question a second way."""
    return _extension_eligible(d.duty_kind, d.satisfying_event)


AUTO_APPROVAL_WARNING_DAYS = 7


def _auto_approval_alert(clock: Clock, status: ClockStatus, due_date: Optional[date], as_of: date) -> Optional[str]:
    if clock.failure_consequence is None or due_date is None:
        return None
    if status == ClockStatus.MISSED:
        return (
            f"AUTO-APPROVAL: the deadline for '{clock.label}' "
            f"({citation.render(clock.citation(), style='short')}) passed on {due_date.isoformat()} "
            f"without action. Article 7 §8.d.1: {clock.failure_consequence}"
        )
    if status == ClockStatus.OPEN and (due_date - as_of).days <= AUTO_APPROVAL_WARNING_DAYS:
        return (
            f"AUTO-APPROVAL RISK: '{clock.label}' "
            f"({citation.render(clock.citation(), style='short')}) is due {due_date.isoformat()} "
            f"({(due_date - as_of).days} day(s) away). A missed deadline auto-approves the "
            f"application under Article 7 §8.d.1."
        )
    return None


def presents_auto_approval_risk(d: Deadline) -> bool:
    """RECONCILIATION FIX (2026-08, post-adversarial-review merge). True if
    `d` should count toward a case's `auto_approval_risk` flag -- the
    boolean app/main.py's dashboard/case-detail banner and row-highlight
    key off, via `_has_auto_approval_alert()`.

    Deliberately broader than `bool(d.auto_approval_alert)`. F1's own repro
    (subdivision received, nothing recorded since, months later) produces
    exactly a clock that (a) carries `failure_consequence` -- it IS an
    §8.d.1-bearing clock -- but (b) is stuck at PENDING_START, so
    `_auto_approval_alert()` never fires for it (no due_date to compare
    against `as_of`); the F4 fix instead gives it a `start_not_recorded_alert`
    naming the overdue predecessor duty. Before this function existed,
    `_has_auto_approval_alert()` checked only `auto_approval_alert`, so F1's
    exact scenario still produced `auto_approval_risk=False` even after F4 --
    the alert had become visible in the deadlines TABLE but never reached the
    banner/highlight/sort that CONTRACT.md's task brief says must make this
    "unmissable". Per the task's explicit conservative instruction ("surface
    the risk whenever any statutory duty on a case is overdue... even if the
    precise legal trigger is later narrowed"), a stalled §8.d.1-bearing clock
    behind a missed predecessor duty counts as risk, without deciding
    D-0012's underlying legal question of exactly which duty §8.d.1 attaches
    to.

    TAXONOMY GATE (2026-08, dissolves N1). Auto-approval risk derives ONLY
    from municipal_duty clocks -- the Town's own, unconditional duties. A
    party_right clock (administrative_appeal, reconsideration) is what a
    PRIVATE PARTY may choose to do, never the Town's failure, so it can never
    itself trigger this; a conditional_duty clock (administrative_appeal_
    hearing/_decision, reconsideration_decision) is a real municipal duty but
    one that does not yet EXIST for this case until its predicate is
    recorded (see DutyKind/ClockStatus.NOT_TRIGGERED), so it does not feed
    the case-level risk banner either -- narrower than a plain municipal_duty
    clock on purpose, not an oversight. This is the fix for N1's exact
    defect: administrative_appeal used to be evaluated with ordinary
    PENDING_START/OPEN/MET/MISSED branching, so 'nobody appealed' silently
    became MISSED 30 days after every decision was filed, which the F4
    predecessor-alert machinery below then read as a stalled statutory duty
    behind administrative_appeal_hearing -- a false auto-approval alarm on
    every decided, unappealed case. Excluding non-municipal_duty clocks here
    is the second, independent layer of that fix (the first is that
    party_right clocks now report ELAPSED, never MISSED, at all -- see
    _evaluate_clock).

    F1 WIDENING (2026-08, adversarial review round 2). The TAXONOMY GATE
    above was itself one notch too narrow: it read "conditional_duty is
    never risk", full stop, which is correct ONLY while the duty is
    NOT_TRIGGERED. Once its predicate_event IS recorded (an appeal was
    actually filed; reconsideration was actually requested), a
    conditional_duty clock is a LIVE municipal duty exactly like an
    ordinary municipal_duty one, carrying the same §8.d.1 consequence when
    it names one (administrative_appeal_hearing, administrative_appeal_
    decision both do). Repro: variance decided and filed on time, appeal
    filed 2026-02-20, the Board never held the §23.d.2 hearing -- months
    later, administrative_appeal_hearing sits MISSED with
    failure_consequence set and auto_approval_alert already carrying the
    §8.d.1 text, yet this function still returned False, because the
    duty_kind gate above stops a triggered conditional_duty clock as hard
    as an untriggered one. `triggered_conditional` is exactly
    _evaluate_clock's own NOT_TRIGGERED test (duty_kind is
    conditional_duty AND status is not NOT_TRIGGERED) -- reusing that same
    condition here, rather than re-deriving it from predicate_event/
    predicate dates, keeps this function's notion of "triggered" identical
    to the one _evaluate_clock already computed into `d.status`. Verified
    against every existing scenario: all five clean on-time tracks
    (administrative_appeal_hearing/_decision NOT_TRIGGERED, since nobody
    appealed) stay False; N2a (reconsideration_decision, no
    failure_consequence at all) stays False; the F1 subdivision repro
    (municipal_duty, untouched by this change) stays True; this new repro
    (triggered administrative_appeal_hearing, MISSED, past its due date)
    now correctly flips True. The identical widening is applied to the F4
    predecessor gate in _attach_start_not_recorded_alerts() below, via the
    same _is_live_municipal_duty() helper, so a triggered conditional_duty
    predecessor can also anchor a downstream start_not_recorded_alert."""
    triggered_conditional = (
        d.duty_kind == DutyKind.CONDITIONAL_DUTY.value
        and d.status != ClockStatus.NOT_TRIGGERED.value
    )
    if d.duty_kind != DutyKind.MUNICIPAL_DUTY.value and not triggered_conditional:
        return False
    if d.auto_approval_alert:
        return True
    return bool(d.start_not_recorded_alert) and bool(d.failure_consequence)


def _is_live_municipal_duty(duty_kind: str, status: str) -> bool:
    """Shared predicate behind the F1 widening above: true for an ordinary
    MUNICIPAL_DUTY clock, or a CONDITIONAL_DUTY clock whose predicate has
    already been triggered (any status other than NOT_TRIGGERED -- a
    conditional_duty clock can only ever REACH a status like MISSED/OPEN/
    MET after triggering, per _evaluate_clock's NOT_TRIGGERED-before-
    PENDING_START branch order, so this is equivalent to, but doesn't
    re-derive, "has the predicate_event actually been recorded"). Used by
    both presents_auto_approval_risk() (is THIS clock live risk?) and
    _attach_start_not_recorded_alerts()'s F4 predecessor gate (is the
    PREDECESSOR clock a live enough duty to anchor a downstream alert?) so
    the two stay in sync by construction rather than by two independently
    maintained conditions."""
    if duty_kind == DutyKind.MUNICIPAL_DUTY.value:
        return True
    return duty_kind == DutyKind.CONDITIONAL_DUTY.value and status != ClockStatus.NOT_TRIGGERED.value


def _clock_applies(clock: Clock, case: CaseFacts) -> bool:
    if case.review_track not in clock.applies_to:
        return False
    for req in clock.requires_absent:
        if _resolve_event(case, req) is not None:
            return False
    return True


def _add(basis: str, start: date, n: int) -> date:
    if basis == "business":
        return add_business_days(start, n)
    if basis == "months":
        return add_months(start, n)
    return add_calendar_days(start, n)


#: N4 chaining sentinel -- distinguishes "no override given, resolve
#: start_event normally" from "override the start to None" (a chained
#: predecessor duty exists but is not, or no longer, genuinely satisfied --
#: see _apply_starts_clock_chaining() below). `None` itself is a legitimate
#: override value, so it cannot double as the "no override" marker.
_NO_START_OVERRIDE = object()


def _evaluate_clock(
    clock: Clock, case: CaseFacts, *, as_of: date, start_override: Any = _NO_START_OVERRIDE,
) -> Deadline:
    cit = clock.citation()
    rule_key = f"art{cit.article}.clock.{clock.clock_key}"

    if start_override is _NO_START_OVERRIDE:
        start_date = _resolve_event(case, clock.start_event, role="start")
    else:
        # N4 chaining -- see _apply_starts_clock_chaining(): this clock's
        # start_event is also another clock's satisfying_event
        # (Clock.starts_clock links them), so its true start is that
        # predecessor's own VALIDATED satisfaction, not a fresh, independent
        # read of the same-named CaseFacts field.
        start_date = start_override
    raw_satisfied_at = _resolve_event(case, clock.satisfying_event, role="satisfying")

    # FINDING 3 -- Article 7 §6.e.1: a written agreement extends "the time
    # limit required for commencement of a public hearing" or "... to make a
    # decision" by however many days the agreement states. `days_extended`
    # is the SUM of every LIVE 'extension_agreed' case_milestones row naming
    # this clock (case_facts_from_row() below does the summing; see
    # CaseFacts.clock_extension_days's own docstring for the EXTENDS-vs-
    # TOLLS choice this implements and DECISIONS-NEEDED D-0022). 0 for every
    # clock with no recorded agreement -- the pre-existing, unextended
    # behavior is exactly reproduced when this dict is empty.
    days_extended = case.clock_extension_days.get(clock.clock_key, 0)
    effective_days = clock.days + days_extended
    due_date = _add(clock.basis, start_date, effective_days) if start_date is not None else None

    # N4 FIX. Before: a satisfying occurrence counted no matter how early it
    # was -- `status = MET if satisfied_at <= due_date else MISSED` had no
    # LOWER bound against start_date. A duty cannot be discharged before it
    # exists: e.g. the Town Clerk's date-stamp on an ORIGINAL decision does
    # not satisfy the §8.f.1 filing duty for a LATER, AMENDED decision --
    # that duty didn't exist yet when the stamp happened. An occurrence
    # dated before the clock's own start_date is therefore not a
    # satisfaction at all; the duty is exactly as unperformed as if nothing
    # had been recorded ("the duty reopens") and falls through to the same
    # OPEN/MISSED branching as an honestly-unsatisfied clock. The rejected
    # date is not silently dropped -- see Deadline.stale_satisfaction_at --
    # CONTRACT.md's framing rule ("honest blanks beat confident guesses")
    # means the record should say a filing DID happen, just not one that
    # counts for the CURRENT (reopened) duty.
    stale_satisfaction_at: Optional[date] = None
    if raw_satisfied_at is not None and start_date is not None and raw_satisfied_at < start_date:
        stale_satisfaction_at = raw_satisfied_at
        satisfied_at = None
    else:
        satisfied_at = raw_satisfied_at

    # 2026-08 clock-taxonomy repair round -- see DutyKind's docstring and
    # presents_auto_approval_risk()'s TAXONOMY GATE comment.
    #
    # party_right (administrative_appeal, reconsideration): a private
    # party's WINDOW to act, not a Town duty. It is never "missed" -- an
    # unexercised window simply ELAPSES. THIS IS THE N1 FIX: before it, this
    # branch fell through to the generic `missed_status = MISSED` case below,
    # so a decided-and-unappealed case reported administrative_appeal MISSED
    # 30 days after filing, every time -- see presents_auto_approval_risk()
    # for how that false MISSED cascaded into a false auto-approval alarm.
    #
    # conditional_duty (administrative_appeal_hearing/_decision,
    # reconsideration_decision): a real municipal duty, but one that exists
    # ONLY once its predicate_event has actually been recorded (an appeal
    # hearing duty exists only if an appeal was filed; a reconsideration
    # decision duty only if reconsideration was requested -- each clock's own
    # duty_kind_note in clocks.json quotes the governing sentence). Absent
    # the predicate, the clock is NOT_TRIGGERED -- checked BEFORE the
    # ordinary PENDING_START test, so "no appeal was ever filed" reads as
    # "this duty doesn't exist for this case" rather than "stalled". THIS IS
    # THE RECONSIDERATION HALF OF THE N2 FIX: before it, reconsideration_
    # decision started unconditionally from decision_at and went MISSED 45
    # days after EVERY decision whenever no reconsideration was ever
    # requested -- directly contrary to this clock's own pre-existing notes.
    is_party_right = clock.duty_kind == DutyKind.PARTY_RIGHT.value
    is_conditional = clock.duty_kind == DutyKind.CONDITIONAL_DUTY.value
    missed_status = ClockStatus.ELAPSED if is_party_right else ClockStatus.MISSED

    predicate_triggered = True
    if is_conditional:
        predicate_triggered = _resolve_event(case, clock.predicate_event, role="satisfying") is not None

    if clock.clock_key in case.waived_clocks:
        status = ClockStatus.WAIVED
    elif clock.clock_key in case.na_clocks:
        status = ClockStatus.NOT_APPLICABLE
    elif is_conditional and not predicate_triggered:
        status = ClockStatus.NOT_TRIGGERED
    elif start_date is None:
        status = ClockStatus.PENDING_START
    elif satisfied_at is not None:
        status = ClockStatus.MET if satisfied_at <= due_date else missed_status
    elif as_of > due_date:
        status = missed_status
    else:
        status = ClockStatus.OPEN

    return Deadline(
        case_id=case.case_id,
        clock_key=clock.clock_key,
        label=clock.label,
        citation_long=citation.render(cit, style="long"),
        citation_short=citation.render(cit, style="short"),
        rule_key=rule_key,
        db_kind=clock.db_kind,
        duty_kind=clock.duty_kind,
        basis=clock.basis,
        days=clock.days,
        start_event=clock.start_event,
        start_date=start_date,
        satisfying_event=clock.satisfying_event,
        satisfied_at=satisfied_at,
        due_date=due_date,
        status=status.value,
        failure_consequence=clock.failure_consequence,
        auto_approval_alert=_auto_approval_alert(clock, status, due_date, as_of),
        conflict_group=clock.conflict_group,
        conflict_note=clock.conflict_note,
        never_autogenerate_condition=clock.never_autogenerate_condition,
        notes=clock.notes,
        stale_satisfaction_at=stale_satisfaction_at,
        extension_days_applied=days_extended,
    )


# --------------------------------------------------------------------------- #
# meeting / draft_due -- derived via app.meetings (app/dates.py's canonical
# implementation), never reimplemented here (CONTRACT.md §3.4).
# --------------------------------------------------------------------------- #


def _meeting_and_draft_due_deadlines(case: CaseFacts, *, as_of: date) -> list[Deadline]:
    meeting = case.meeting_date or next_meeting(as_of)
    due = draft_due(meeting)

    # F8 FIX. Before: `status = MET if as_of >= due else OPEN`, followed by an
    # `elif ... and as_of > due: status = MISSED` that could never execute
    # (the `>=` above already claims that whole range as MET) -- so this
    # clock flipped to MET the instant the calendar date passed, whether or
    # not a draft existed. "Board meeting happens" is a calendar fact this
    # software doesn't own or fail at (the Town holds it regardless), so
    # `meeting` keeps simple date-passed MET/OPEN semantics -- the dead
    # branch is just deleted, not replaced with an invented satisfying event.
    # `draft_due` is different: it is a duty THIS APP's user owes (get a
    # draft into the packet), so it earns real satisfaction semantics --
    # MET only when a findings_draft/findings_final document was actually
    # generated (case.draft_documents, F8), exactly mirroring every other
    # clock's own MET/MISSED/OPEN branching in _evaluate_clock() above (a
    # late draft is MISSED, not silently MET; no draft past the due date is
    # MISSED, not "still fine because nobody checked").
    meeting_status = ClockStatus.MET if as_of >= meeting else ClockStatus.OPEN

    draft_dates = sorted(d for d in case.draft_documents if d is not None)
    draft_satisfied_at = draft_dates[0] if draft_dates else None
    if draft_satisfied_at is not None:
        draft_status = ClockStatus.MET if draft_satisfied_at <= due else ClockStatus.MISSED
    elif as_of > due:
        draft_status = ClockStatus.MISSED
    else:
        draft_status = ClockStatus.OPEN

    return [
        Deadline(
            case_id=case.case_id, clock_key="meeting", label="Planning Board meeting",
            citation_long="", citation_short="", rule_key="pb.third_thursday", db_kind="meeting",
            duty_kind=DutyKind.INFORMATIONAL.value,
            basis="calendar", days=0, start_event="meeting_date", start_date=meeting,
            satisfying_event="meeting_date", satisfied_at=meeting if meeting_status == ClockStatus.MET else None,
            due_date=meeting, status=meeting_status.value, failure_consequence=None,
            auto_approval_alert=None, conflict_group=None, conflict_note=None,
            never_autogenerate_condition=False,
            notes=(
                "The 3rd Thursday of the month, 18:30 America/New_York (app/dates.py). "
                "This clock tracks only whether the calendared date has passed -- it has "
                "no MISSED state, because the Town holds its meeting regardless of "
                "anything this software does or fails to do."
            ),
        ),
        Deadline(
            case_id=case.case_id, clock_key="draft_due", label="Findings draft due in the packet",
            citation_long="", citation_short="", rule_key="pb.draft_due_minus_7", db_kind="draft_due",
            duty_kind=DutyKind.INFORMATIONAL.value,
            basis="calendar", days=7, start_event="meeting_date", start_date=meeting,
            satisfying_event="draft_document_generated",
            satisfied_at=draft_satisfied_at,
            due_date=due, status=draft_status.value, failure_consequence=None,
            auto_approval_alert=None, conflict_group=None, conflict_note=None,
            never_autogenerate_condition=False,
            notes=(
                "meeting_date - 7 days (app/dates.py). MET only when a findings_draft/"
                "findings_final row exists in generated_documents on or before this date "
                "(F8) -- the date passing alone no longer counts as satisfaction."
            ),
        ),
    ]


# --------------------------------------------------------------------------- #
# F4 -- a clock stuck at PENDING_START because its start_event was never
# recorded is otherwise invisible: excluded from open_deadlines() with no
# trace at all. When the clock whose SATISFYING event would have STARTED it
# (its statutory predecessor -- found by matching satisfying_event to
# start_event among this case's own applicable clocks) is itself MISSED, an
# operator needs to see "you have not recorded X" instead of silence. This
# never invents a start date -- the clock stays honestly PENDING_START; it
# only adds a visible reason to chase (CONTRACT.md §1 S7/the framing rule).
#
# F2 SECOND ARM (2026-08, adversarial review round 2). The FIRST arm above
# depends on there being some OTHER clock whose satisfying_event equals `c`'s
# own start_event -- but three §8.d.1-bearing decision clocks
# (large_project_pb_decision, special_permit_decision, variance_decision, all
# start_event="hearing_closed_at") and administrative_appeal_decision
# (start_event="appeal_hearing_closed_at") have NO such predecessor at all:
# no clock in clocks.json is ever satisfied by a "*_closed_at" field (the
# sibling HEARING clocks -- special_permit_review_hearing et al -- are
# satisfied by "*_opened_at" instead). by_satisfying.get(c.start_event) is
# therefore always [] for these four clocks, so the first arm can NEVER fire
# for them, no matter how long the hearing has sat open -- a hearing opened
# on time and never closed produces total silence: PENDING_START, no
# auto_approval_alert (no due_date to compare), no start_not_recorded_alert.
# Repro (ATTACK F): special_permit hearing opened 2025-02-03, never closed,
# evaluated 18 months later -> special_permit_decision PENDING_START,
# due=None, no alert at all, presents_auto_approval_risk()=False. Identical
# for variance_decision and large_project_pb_decision.
#
# Article 7 §6.e.1 lets the applicant and Permitting Authority mutually
# agree to extend "the time limit required to make a decision" -- so an
# open-ended hearing is a Code-CONTEMPLATED normal event (a continuance), not
# inherently pathological, and this arm must not report it as MISSED or
# invent a due_date. It only needs to stop being SILENT once the hearing has
# been open long enough that quiet stops looking like an ordinary
# continuance and starts looking like a stall nobody is tracking.
# _HEARING_OPENED_COUNTERPART names, for each affected start_event, the
# CaseFacts field recording when that SAME hearing opened (these are the
# only two "*_closed_at"/"*_opened_at" pairs clocks.json's own clocks use --
# see special_permit_review_hearing/administrative_appeal_hearing's
# satisfying_event above); STALE_HEARING_WARNING_DAYS is the "long enough"
# threshold. §6.e.1 states NO outer bound on a mutual-agreement extension --
# this app will not invent a legal maximum, so this number is an
# OPERATIONAL placeholder to prevent permanent silence, not a Code-derived
# deadline; it is logged, not guessed-and-hidden, at DECISIONS-NEEDED
# D-0017, and never feeds a MISSED status, a due_date, or an
# auto_approval_alert -- only this same start_not_recorded_alert channel
# F4's first arm already uses for "something is stalled, go look".
# --------------------------------------------------------------------------- #

_HEARING_OPENED_COUNTERPART: dict[str, str] = {
    "hearing_closed_at": "hearing_opened_at",
    "appeal_hearing_closed_at": "appeal_hearing_opened_at",
}

#: D-0017 (DECISIONS-NEEDED.md) -- not derived from the Code; §6.e.1 permits
#: a mutual-agreement extension with no stated outer bound. Chosen as a
#: conservative "this has clearly stopped looking like an ordinary
#: continuance" marker, not a legal maximum.
STALE_HEARING_WARNING_DAYS = 180


def _attach_start_not_recorded_alerts(
    clocks: list[Clock], deadlines: list[Deadline], case: CaseFacts, *, as_of: date,
) -> list[Deadline]:
    by_satisfying: dict[str, list[tuple[Clock, Deadline]]] = {}
    for c, d in zip(clocks, deadlines):
        by_satisfying.setdefault(c.satisfying_event, []).append((c, d))

    out: list[Deadline] = []
    for c, d in zip(clocks, deadlines):
        if d.status != ClockStatus.PENDING_START.value:
            out.append(d)
            continue
        # TAXONOMY GATE (2026-08, dissolves N1; widened 2026-08 round 2 for
        # F1 -- see _is_live_municipal_duty()). A predecessor only counts as
        # "a genuinely overdue statutory duty worth chasing" when it is
        # itself a LIVE municipal duty: an ordinary municipal_duty clock, or
        # a conditional_duty clock whose predicate has actually triggered
        # (a MISSED status is itself proof of triggering -- see
        # _evaluate_clock's NOT_TRIGGERED-before-PENDING_START branch order,
        # so pd.status == MISSED already implies "not NOT_TRIGGERED" and
        # _is_live_municipal_duty's second branch is satisfied whenever the
        # first `pd.status == MISSED` guard below is). A party_right clock
        # (e.g. administrative_appeal) can no longer even REPORT MISSED (it
        # reports ELAPSED instead -- see _evaluate_clock), so it can never
        # match here either way.
        predecessor = next(
            (
                pd
                for (pc, pd) in by_satisfying.get(c.start_event, [])
                if pd.status == ClockStatus.MISSED.value and _is_live_municipal_duty(pc.duty_kind, pd.status)
            ),
            None,
        )
        if predecessor is not None:
            msg = (
                f"START NOT RECORDED: '{c.label}' ({d.citation_short}) cannot begin until "
                f"'{predecessor.label}' ({predecessor.citation_short}) is recorded. That duty's "
                f"own deadline passed on {predecessor.due_date.isoformat()} with no record of it "
                f"happening -- follow up before this clock can even start."
            )
            if c.failure_consequence:
                # RECONCILIATION FIX (F1, see presents_auto_approval_risk above):
                # this clock itself carries the §8.d.1 consequence -- make that
                # explicit in the same message the deadline table/banner render,
                # not just in the separate boolean the banner keys off.
                msg += (
                    f" '{c.label}' is itself an Article 7 §8.d.1 auto-approval clock "
                    f"({citation.render(c.citation(), style='short')}) -- once its start event IS "
                    f"recorded, a missed deadline on IT would auto-approve the application."
                )
            out.append(replace(d, start_not_recorded_alert=msg))
            continue

        # F2 SECOND ARM -- see the block comment above. Only reachable when
        # the first arm found nothing (by_satisfying has no entry at all for
        # c.start_event, for the four clocks this applies to).
        opened_field = _HEARING_OPENED_COUNTERPART.get(c.start_event) if c.failure_consequence else None
        opened_at = getattr(case, opened_field, None) if opened_field else None
        if opened_at is not None and (as_of - opened_at).days >= STALE_HEARING_WARNING_DAYS:
            days_open = (as_of - opened_at).days
            msg = (
                f"STALLED: '{c.label}' ({d.citation_short}) cannot begin until the hearing is "
                f"closed. The hearing opened on {opened_at.isoformat()} ({days_open} days ago as "
                f"of {as_of.isoformat()}) and no closing has been recorded -- Article 7 §6.e.1 "
                f"permits an open hearing to run by mutual agreement, but this has gone long "
                f"enough that it needs a human to confirm it is a genuine continuance and not a "
                f"forgotten one. '{c.label}' is itself an Article 7 §8.d.1 auto-approval clock "
                f"({citation.render(c.citation(), style='short')}) -- once the hearing IS closed "
                f"and this clock starts, a missed deadline on it would auto-approve the "
                f"application. (The {STALE_HEARING_WARNING_DAYS}-day threshold is an operational "
                f"placeholder, not a Code-stated limit -- see DECISIONS-NEEDED.md D-0017.)"
            )
            out.append(replace(d, start_not_recorded_alert=msg))
            continue

        out.append(d)
    return out


# --------------------------------------------------------------------------- #
# N4 -- Clock.starts_clock chaining. A clock can name a successor clock that
# it starts (e.g. decision_filed_with_clerk's `starts_clock:
# "administrative_appeal"` -- the Clerk's date-stamp on the decision is what
# starts the appeal window). Before this fix that field was pure metadata:
# the successor independently re-read the SAME-NAMED CaseFacts field
# (`_resolve_event(..., role="start")`) as a raw scalar, with no idea
# whether the PREDECESSOR clock's own satisfaction had just been rejected as
# stale (N4's core fix, in _evaluate_clock above). That let a satisfied-
# against-the-wrong-decision filing keep starting the appeal window even
# after the filing duty itself had reopened -- the amended-decision repro
# this fix exists for: a decision filed on time, then amended; the appeal
# window for the AMENDED decision must not run from the STALE filing.
#
# This pass hands the successor the predecessor's own VALIDATED
# satisfied_at (None if rejected as stale, or never recorded at all)
# instead, so "the duty reopens" propagates downstream instead of stopping
# at the one clock N4's lower bound directly touches. Single-hop only --
# nothing in rulesets/adopted/clocks.json chains `starts_clock` more than
# one level deep today; a future multi-hop chain would need this run to a
# fixed point (or topologically), not assumed correct by one pass.
# --------------------------------------------------------------------------- #


def _apply_starts_clock_chaining(
    clocks: list[Clock], deadlines: list[Deadline], case: CaseFacts, *, as_of: date,
) -> list[Deadline]:
    by_key: dict[str, tuple[int, Clock, Deadline]] = {
        c.clock_key: (i, c, d) for i, (c, d) in enumerate(zip(clocks, deadlines))
    }
    out = list(deadlines)
    for predecessor_clock, predecessor_deadline in zip(clocks, deadlines):
        if not predecessor_clock.starts_clock:
            continue
        successor = by_key.get(predecessor_clock.starts_clock)
        if successor is None:
            # The named successor isn't applicable to this case/track (e.g.
            # its own applies_to excludes case.review_track) -- nothing to
            # chain onto; leave the predecessor's own (already-evaluated)
            # deadline exactly as it was.
            continue
        idx, successor_clock, _successor_deadline = successor
        if successor_clock.start_event != predecessor_clock.satisfying_event:
            # A clocks.json authoring mismatch (starts_clock points at a
            # clock whose start_event isn't actually the field this clock
            # satisfies) -- don't guess a link that isn't really there;
            # leave the successor's own independent resolution in place.
            continue
        out[idx] = _evaluate_clock(
            successor_clock, case, as_of=as_of, start_override=predecessor_deadline.satisfied_at,
        )
    return out


# --------------------------------------------------------------------------- #
# compute_deadlines() -- the pure function this module exists to provide.
# --------------------------------------------------------------------------- #


def compute_deadlines(
    case: CaseFacts,
    *,
    ruleset_key: Optional[str] = None,
    as_of: Optional[date] = None,
    include_meeting_clocks: bool = True,
) -> list[Deadline]:
    """The full set of statutory deadlines that apply to `case`, each
    evaluated against `case`'s known facts as of `as_of` (default: today).

    A clock whose `applies_to` doesn't include case.review_track, or whose
    `requires_absent` fact IS present (the Large Project Plan CEO-track clock
    once forwarded_to_pb_at is set), is simply not in the returned list --
    it never applied to this case, which is different from PENDING_START
    (applies, but hasn't started).
    """
    as_of = as_of or date.today()
    key = ruleset_key or case.ruleset_key
    clocks = load_clocks(key)

    applicable = [clock for clock in clocks if _clock_applies(clock, case)]
    evaluated = [_evaluate_clock(clock, case, as_of=as_of) for clock in applicable]
    evaluated = _apply_starts_clock_chaining(applicable, evaluated, case, as_of=as_of)
    out = _attach_start_not_recorded_alerts(applicable, evaluated, case, as_of=as_of)
    if include_meeting_clocks:
        out.extend(_meeting_and_draft_due_deadlines(case, as_of=as_of))
    return out


def deadline_row(d: Deadline, *, id_: str, created_at: str, actor_user_id: Optional[str] = None) -> dict[str, Any]:
    """Shapes a Deadline into the exact column set app/migrations/
    0001_init.sql + 0005_deadline_engine_fixes.sql's `deadlines` table
    expects, for a future writer to INSERT (this module never performs that
    INSERT itself -- see the module docstring's SCOPE BOUNDARY).

    F9b FIX: previously dropped conflict_group / conflict_note /
    never_autogenerate_condition entirely -- once persisted, a protected,
    conflicted clock (the two subdivision plat-recording clocks) would have
    been indistinguishable from any ordinary deadline row. All three now
    carry through to the columns 0005_deadline_engine_fixes.sql adds.
    """
    return {
        "id": id_,
        "case_id": d.case_id,
        "kind": d.db_kind,
        "due_date": d.due_date.isoformat() if d.due_date else None,
        "due_time": "18:30" if d.clock_key == "meeting" else None,
        "tz": "America/New_York",
        "rule_key": d.rule_key,
        "computed_from": d.start_date.isoformat() if d.start_date else None,
        "satisfied_at": d.satisfied_at.isoformat() if d.satisfied_at else None,
        "created_at": created_at,
        "actor_user_id": actor_user_id,
        "conflict_group": d.conflict_group,
        "conflict_note": d.conflict_note,
        "never_autogenerate_condition": 1 if d.never_autogenerate_condition else 0,
    }


# --------------------------------------------------------------------------- #
# F9a -- the single enforcement point for Clock.never_autogenerate_condition.
# Before this function existed the field had ZERO code consumer (only tests
# and the dataclass referenced it) -- nothing would stop a future
# condition-generator (engine/'s "rules -> criteria sets -> findings_nodes"
# work, not yet built -- CONTRACT.md §2) from auto-drafting a recording
# condition off ONE of the two conflicting subdivision plat-recording clocks
# and silently picking a side in a genuine Code conflict this app must never
# resolve on its own (CONTRACT.md §1 S7).
# --------------------------------------------------------------------------- #


class ProtectedClockError(Exception):
    """Raised by guard_condition_autogeneration() for a Deadline whose Clock
    is marked never_autogenerate_condition. There is no override -- a human
    drafts that condition by hand."""


def guard_condition_autogeneration(deadline: Deadline) -> None:
    """Any code that turns a Deadline into an auto-drafted `conditions` row
    MUST call this first. Raises ProtectedClockError if the clock is
    protected; otherwise returns None and does nothing."""
    if deadline.never_autogenerate_condition:
        raise ProtectedClockError(
            f"{deadline.clock_key} ({deadline.citation_short}) is marked "
            f"never_autogenerate_condition and MUST NOT auto-generate a condition -- "
            + (deadline.conflict_note or "a human must draft this condition by hand.")
        )


# --------------------------------------------------------------------------- #
# open_deadlines() -- the dashboard query. Two forms:
#   - open_deadlines(cases=[...])            in-memory / test form
#   - open_deadlines(conn=sqlite3.Connection) DB-backed form (reads only)
# --------------------------------------------------------------------------- #


def _severity_key(d: Deadline) -> tuple[int, date]:
    # MISSED-with-auto-approval first, then other MISSED, then a F4
    # start-not-recorded alert (a PENDING_START clock stalled behind an
    # overdue predecessor -- still worth chasing even with no due_date of
    # its own), then OPEN by due date.
    if d.status == ClockStatus.MISSED.value and d.failure_consequence:
        rank = 0
    elif d.status == ClockStatus.MISSED.value:
        rank = 1
    elif d.start_not_recorded_alert:
        rank = 2
    else:
        rank = 3
    return (rank, d.due_date or date.max)


def open_deadlines(
    cases: Optional[Iterable[CaseFacts]] = None,
    *,
    conn: Optional[sqlite3.Connection] = None,
    as_of: Optional[date] = None,
) -> list[Deadline]:
    """Aggregates compute_deadlines() across many cases, keeping the rows a
    dashboard needs to act on: OPEN, MISSED, and (F4) any PENDING_START clock
    carrying a start_not_recorded_alert -- never a plain, silent
    PENDING_START, MET, WAIVED, or N/A. Sorted so a MISSED clock carrying the
    §8.d.1 auto-approval consequence leads (CONTRACT.md's brief: "the
    dashboard must make an approaching auto-approval unmissable"), then other
    MISSED clocks, then a start-not-recorded alert, then OPEN clocks by
    soonest due_date.

    Exactly one of `cases` or `conn` must be given. `conn` reads `cases`
    JOIN `rulesets` (for ruleset_key) and every non-withdrawn case's FULL
    `case_milestones` history (live and superseded -- F7 needs both) via
    load_all_case_facts() -- SELECT only, per this module's SCOPE BOUNDARY.
    """
    as_of = as_of or date.today()
    if (cases is None) == (conn is None):
        raise ValueError("open_deadlines: pass exactly one of cases= or conn=")

    if conn is not None:
        cases = list(load_all_case_facts(conn))

    out: list[Deadline] = []
    for case in cases:
        out.extend(compute_deadlines(case, as_of=as_of))

    relevant = [
        d for d in out
        if d.status in (ClockStatus.OPEN.value, ClockStatus.MISSED.value)
        or d.start_not_recorded_alert is not None
    ]
    relevant.sort(key=_severity_key)
    return relevant


# --------------------------------------------------------------------------- #
# DB adapter -- reads cases + case_milestones (0002_case_tracking.sql).
# Read-only. See module docstring for the milestone-kind bridging convention.
# --------------------------------------------------------------------------- #

_MILESTONE_TO_FIELD: dict[str, str] = {
    "notice_mailed": "notice_mailed_at",
    "notice_published": "notice_published_at",
    "completeness_determined": "completeness_at",
    "hearing_opened": "hearing_opened_at",
    "hearing_closed": "hearing_closed_at",
    "forwarded_to_planning_board": "forwarded_to_pb_at",
    "decision_issued": "decision_at",
    "decision_filed": "decision_filed_at",
    "plat_recorded": "plat_recorded_at",
    "appeal_filed": "appeal_filed_at",
    "reconsideration_requested": "reconsideration_requested_at",
    # F6: promoted from the retired 'other'+note-substring bridging
    # convention to first-class case_milestones.kind values
    # (0005_deadline_engine_fixes.sql). Handled by the SAME generic
    # kind->field loop as every other row below -- no special-casing.
    "findings_issued": "findings_issued_at",
    "certificate_recorded": "certificate_recorded_at",
    # N2: the four §23 appeal-track events administrative_appeal_hearing/
    # _decision/reconsideration_decision (rulesets/adopted/clocks.json) have
    # named since F3, newly recordable via 0006_appeal_recordability.sql.
    # Before this migration+mapping landed, these four CaseFacts fields could
    # only ever be None -- two of the three clocks they feed carry the
    # §8.d.1 auto-approval consequence, so a Board of Appeals that held its
    # hearing and decided an appeal exactly on time still showed a
    # permanent, un-clearable alarm. See
    # ruleset_build.verify_structure.check_clock_event_recordability, which
    # now asserts as a standing build gate that every clocks.json event
    # resolves through this dict (or the documented _SPECIAL_EVENT_SOURCES
    # exception below) to a genuinely recordable case_milestones.kind.
    "appeal_hearing_opened": "appeal_hearing_opened_at",
    "appeal_hearing_closed": "appeal_hearing_closed_at",
    "appeal_decision": "appeal_decision_at",
    "reconsideration_decided": "reconsideration_decided_at",
    # HARD-FINAL round, Finding 6: the §23.e.2/.e.3 VOTE TO RECONSIDER, now
    # reconsideration_decision's predicate_event (rulesets/adopted/
    # clocks.json) in place of the mere §23.e.1 request. See CaseFacts.
    # reconsideration_voted_at above and app/migrations/0011_reconsideration_
    # vote.sql.
    "reconsideration_voted": "reconsideration_voted_at",
}

# --------------------------------------------------------------------------- #
# N2 -- event recordability. A clocks.json start_event/satisfying_event is a
# CaseFacts FIELD NAME (e.g. "submitted_at"), not a case_milestones.kind --
# most fields are populated by the generic _MILESTONE_TO_FIELD loop above
# (one kind, one field), but `submitted_at` is a documented exception:
# case_facts_from_row() resolves it via its own DECISIONS-NEEDED D-0008
# ranking (the 'application_received' milestone, falling back to
# cases.received_at, falling back to the 'application_dated' milestone) --
# see that function's own "submitted_at source ranking" comment -- rather
# than the generic loop, because the ranking picks the FRESHEST of three
# candidate sources, which a simple one-kind-to-one-field dict entry cannot
# express. Recorded here, once, so a build-time recordability check (and any
# other future caller) doesn't have to special-case that private code path
# for itself -- every kind listed below is independently a real, recordable
# case_milestones.kind (CASE_MILESTONE_KINDS, the migration CHECK
# constraint, and the operator UI dropdown all already carry it).
# --------------------------------------------------------------------------- #

_SPECIAL_EVENT_SOURCES: dict[str, tuple[str, ...]] = {
    "submitted_at": ("application_received", "application_dated"),
}


def event_recordable_kinds(field_name: str) -> tuple[str, ...]:
    """The case_milestones.kind value(s) that populate CaseFacts.<field_name>,
    for build-time recordability checking (see
    ruleset_build.verify_structure.check_clock_event_recordability). Checks
    `_SPECIAL_EVENT_SOURCES` first (a documented multi-source field like
    `submitted_at`), then the generic `_MILESTONE_TO_FIELD` mapping.

    Returns an EMPTY tuple if no case_milestones.kind records this field at
    all -- e.g. `meeting_date` / `draft_document_generated`, which
    `_meeting_and_draft_due_deadlines()` sources from the `cases` row /
    `generated_documents` directly and which are never named as a clocks.json
    event (they are NOT in play for this function's actual callers, but the
    empty-tuple return is the honest answer if one ever were)."""
    special = _SPECIAL_EVENT_SOURCES.get(field_name)
    if special:
        return special
    return tuple(kind for kind, f in _MILESTONE_TO_FIELD.items() if f == field_name)

# `application_type` values that are also REVIEW_TRACKS pass straight
# through; the rest (`zoning`, `shoreland`, `site_plan`, `other`) have no
# Article 7 clock set defined and simply produce zero clocks (not an error --
# a scratch/other-type case legitimately has none of these). HARD-FINAL
# round, Finding 5: `use` and `expanded_use` used to be in that same "zero
# clocks" bucket -- they are REVIEW_TRACKS now (use_permit_decision §15.d.1,
# plus decision_filed_with_clerk/administrative_appeal/_hearing/_decision,
# widened at F5) and produce a real clock set like every other track.


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return datetime.fromisoformat(s[:10]).date()


def parse_date_or_none(s: Optional[str]) -> Optional[date]:
    """Public, NEVER-raising counterpart to `_parse_date`, for read-only
    display code that needs to check whether a stored
    `case_milestones.occurred_on` value is well-formed without that check
    itself becoming another way a single malformed historical row can crash
    a page (F5 -- app/cases.py:record_dates now rejects a bad value at
    write time, but this lets a read path recognize an already-stored one,
    e.g. to flag it for correction). Returns None for anything falsy AND
    for anything that fails to parse; never raises.
    """
    if not s:
        return None
    try:
        return _parse_date(s)
    except ValueError:
        return None


def case_facts_from_row(
    case_row: Any,
    milestone_rows: Iterable[Any],
    *,
    draft_documents: Iterable[date] | None = None,
) -> CaseFacts:
    """Builds CaseFacts for one case from its `cases` row and its
    `case_milestones` rows.

    F7 FIX -- `milestone_rows` should now be EVERY row for this case, LIVE
    *and* superseded (load_all_case_facts() below no longer filters
    `superseded_by IS NULL` in its own query). The scalar "latest" fields
    below (used for a clock's START role -- see _resolve_event()'s role
    docs) are still built from LIVE rows ONLY, exactly as before; `history`
    now genuinely carries every recorded occurrence, because
    _first_satisfying_occurrence() reads history, not the scalar fields, to
    find the FIRST time a SATISFYING duty was actually performed -- even one
    a later, unrelated correction/re-notice superseded for display purposes
    elsewhere. Passing only-live rows still works (a superseded row simply
    never appears in history, i.e. the previous, narrower behaviour) --
    this signature change is backward compatible.

    F6 FIX -- 'findings_issued' and 'certificate_recorded' are now
    first-class kinds (0005_deadline_engine_fixes.sql), handled by the same
    generic `_MILESTONE_TO_FIELD` loop as every other kind; the old
    'other'+note-substring bridging convention is gone.

    `application_dated` and `received_at` -- see DECISIONS-NEEDED D-0008:
    `cases.received_at` is preferred; the `application_dated` milestone is
    used only when `received_at` is NULL.
    """
    fields: dict[str, Any] = {}
    application_dated_at: Optional[date] = None
    application_received_at: Optional[date] = None
    history: list[dict[str, Any]] = []
    # FINDING 3 -- accumulated from LIVE 'extension_agreed' / 'clock_waived' /
    # 'clock_not_applicable' rows below. See CaseFacts.clock_extension_days'
    # own docstring for why extensions against the same clock_key ACCUMULATE
    # (summed) rather than the latest-wins rule the scalar `fields` dict uses.
    clock_extension_days: dict[str, int] = {}
    waived_clocks: set[str] = set()
    na_clocks: set[str] = set()

    for m in milestone_rows:
        kind = m["kind"]
        # F5 -- this loop used to call the RAISING _parse_date here, so a
        # single malformed case_milestones.occurred_on value (written before
        # app/cases.py:record_dates validated at the boundary, or however
        # else one slipped in) crashed CaseFacts construction for the WHOLE
        # case -- every read path built on it (the dashboard, case detail,
        # load_all_case_facts) 500'd. F7 made that worse by widening
        # `milestone_rows` to include superseded rows too, so even a row the
        # F5 repair path (supersedes_id) had already superseded still hit
        # this line. parse_date_or_none never raises: an unparseable value
        # is carried into `history` for display (below), same as before, but
        # contributes an honestly-unknown None date instead of crashing.
        occurred = parse_date_or_none(m["occurred_on"])
        note = m["note"] if "note" in m.keys() else None
        is_live = ("superseded_by" not in m.keys()) or (m["superseded_by"] is None)
        # N3: carry `superseded_by`/`supersede_reason` through to `history`
        # too -- `_first_satisfying_occurrence()` needs BOTH, per row, to
        # tell a genuine RESCHEDULE/RE-NOTICE occurrence (still counts, F7)
        # from a factually-wrong CORRECTION (never counts, N3) apart. A
        # checkout without the 0007_supersede_reason.sql column simply never
        # has the key, and `.get()` reads that the same as an honestly
        # unknown/legacy NULL -- see _first_satisfying_occurrence()'s own
        # docstring for the conservative default that follows from that.
        history.append({
            "kind": kind,
            "occurred_on": m["occurred_on"],
            "note": note,
            "superseded": not is_live,
            "supersede_reason": m["supersede_reason"] if "supersede_reason" in m.keys() else None,
            # FINDING 3 -- carried through unconditionally, same `.keys()`
            # guard as supersede_reason above (a checkout that predates
            # 0010_clock_extensions.sql simply never has these keys; that
            # reads the same as an honestly absent value, never a crash).
            # None for every kind except the three this migration adds.
            "target_clock_key": m["target_clock_key"] if "target_clock_key" in m.keys() else None,
            "extension_days": m["extension_days"] if "extension_days" in m.keys() else None,
            "written_agreement_ref": m["written_agreement_ref"] if "written_agreement_ref" in m.keys() else None,
        })
        if not is_live:
            # F7: still recorded in `history` above (a satisfying-role clock
            # may need it); excluded from the LIVE scalar fields below,
            # unchanged from this module's original behaviour. FINDING 3:
            # this is deliberate for extension/waiver/n-a rows too -- a
            # superseded (corrected) extension or waiver must not still
            # count, exactly like every other superseded row.
            continue

        if kind == "extension_agreed":
            # FINDING 3 -- app.cases.record_dates is the write path and
            # already validates target_clock_key/extension_days at the
            # boundary (S1); this read side stays defensive anyway (F5's own
            # posture) rather than trusting that invariant enough to crash a
            # whole case's deadline computation on a malformed legacy row.
            target = m["target_clock_key"] if "target_clock_key" in m.keys() else None
            days_val = m["extension_days"] if "extension_days" in m.keys() else None
            if target and isinstance(days_val, int) and not isinstance(days_val, bool) and days_val > 0:
                clock_extension_days[target] = clock_extension_days.get(target, 0) + days_val
            continue
        if kind == "clock_waived":
            target = m["target_clock_key"] if "target_clock_key" in m.keys() else None
            if target:
                waived_clocks.add(target)
            continue
        if kind == "clock_not_applicable":
            target = m["target_clock_key"] if "target_clock_key" in m.keys() else None
            if target:
                na_clocks.add(target)
            continue

        if kind == "application_dated":
            application_dated_at = occurred
            continue
        if kind == "application_received":
            # 0003_case_lifecycle.sql: the Town's formal receipt, distinct
            # from the date printed on the form (application_dated) -- the
            # most authoritative of the three possible submitted_at sources
            # (see the ranking below). Added by app/migrations/
            # 0003_case_lifecycle.sql; may not exist on an older checkout,
            # which is fine -- this loop simply never sees the kind.
            # F5: `occurred` can now be None (an unparseable historical
            # value) -- never let that win over, or crash comparing against,
            # a real date already on record.
            if occurred is not None and (application_received_at is None or occurred > application_received_at):
                application_received_at = occurred
            continue
        if kind == "meeting":
            # A Board session this case was taken up at (e.g. a hearing
            # opened at one meeting, closed at a later one). Informational
            # only -- already captured in `history` above; no CaseFacts
            # field consumes individual meeting occurrences (case.meeting_date
            # is the NEXT/calendared one, sourced from the `cases` row).
            continue
        field_name = _MILESTONE_TO_FIELD.get(kind)
        if field_name is not None:
            existing = fields.get(field_name)
            # F5: same None-safety as application_received_at above.
            if occurred is not None and (existing is None or occurred > existing):
                fields[field_name] = occurred

    # submitted_at source ranking (DECISIONS-NEEDED D-0008): the
    # 'application_received' milestone (the Town's own receipt event) is the
    # freshest, most authoritative source; cases.received_at is a denormalized
    # mirror of it (0003_case_lifecycle.sql's own words) so it is the second
    # choice if the milestone row itself isn't present on this checkout; the
    # 'application_dated' milestone (the date printed on the form) is the
    # last-resort fallback -- never silently treated as equivalent to receipt.
    # F5: defensive here too -- cases.received_at/meeting_date are mirrored
    # from validated occurred_on values by app/cases.py, but a read path
    # should never trust that invariant enough to crash on it (a hand-edited
    # DB row, an older checkout, ...).
    received_at = parse_date_or_none(case_row["received_at"]) if "received_at" in case_row.keys() else None
    if application_received_at is not None:
        submitted_at, submitted_source = application_received_at, "application_received"
    elif received_at is not None:
        submitted_at, submitted_source = received_at, "received_at"
    elif application_dated_at is not None:
        submitted_at, submitted_source = application_dated_at, "application_dated"
    else:
        submitted_at, submitted_source = None, None

    return CaseFacts(
        case_id=case_row["id"],
        review_track=case_row["application_type"],
        ruleset_key=case_row["ruleset_key"] if "ruleset_key" in case_row.keys() else "adopted",
        is_scratch=bool(case_row["is_scratch"]),
        label=case_row["label"] if "label" in case_row.keys() else "",
        submitted_at=submitted_at,
        submitted_at_source=submitted_source,
        meeting_date=parse_date_or_none(case_row["meeting_date"]) if "meeting_date" in case_row.keys() else None,
        history=tuple(history),
        draft_documents=tuple(draft_documents) if draft_documents is not None else (),
        clock_extension_days=clock_extension_days,
        waived_clocks=frozenset(waived_clocks),
        na_clocks=frozenset(na_clocks),
        **fields,
    )


def load_all_case_facts(conn: sqlite3.Connection) -> list[CaseFacts]:
    """Read-only: every non-withdrawn case, joined to its ruleset_key, with
    the FULL (live + superseded -- F7) case_milestones history and (F8) its
    generated_documents draft dates. SELECT only -- see module docstring
    SCOPE BOUNDARY."""
    case_rows = conn.execute(
        """
        SELECT c.*, r.ruleset_key AS ruleset_key
        FROM cases c
        JOIN rulesets r ON r.id = c.ruleset_id
        WHERE c.status != 'withdrawn'
        """
    ).fetchall()

    out = []
    for row in case_rows:
        milestone_rows = conn.execute(
            "SELECT * FROM case_milestones WHERE case_id = ? ORDER BY occurred_on",
            (row["id"],),
        ).fetchall()
        draft_rows = conn.execute(
            """
            SELECT generated_at FROM generated_documents
            WHERE case_id = ? AND kind IN ('findings_draft', 'findings_final')
            """,
            (row["id"],),
        ).fetchall()
        draft_documents = [
            d for d in (_parse_date(r["generated_at"]) for r in draft_rows) if d is not None
        ]
        out.append(case_facts_from_row(row, milestone_rows, draft_documents=draft_documents))
    return out
