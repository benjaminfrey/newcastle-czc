"""Tests for engine/deadlines.py (and its app/deadlines.py re-export) --
the W3 statutory deadline clock engine.

Run offline: `cd build/permit-review && python3 -m pytest tests/test_deadlines.py -v`
(the `-m pytest` form puts this directory's parent on sys.path so `import
app`/`import engine` resolve without any project being installed).

The Shattuck reconstruction tests use the REAL ground-truth dates from the
adopted decision PDF (see the W3 task brief):

    application dated 2025-10-02, updated through 2025-12-18
    pre-submittal meeting with the Planning Board 2025-10-16
    application circulated to departments 2025-10-16
    mailed notice (certified) 2025-11-04
    published notice, Lincoln County News 2025-11-06
    public hearing opened 2025-11-20, closed 2025-12-18
    decision 2025-12-18

Ground truth does NOT give an exact date for the ORIGINAL notice mailed
ahead of the Oct 16 meeting (only that one existed and was superseded by a
re-notice once the hearing moved to Nov 20) or for a completeness
determination -- these tests never invent one; where ground truth is silent,
the engine is asserted to stay honestly blank (PENDING_START), never guess.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import db  # noqa: E402
from engine import deadlines as dl  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"


# --------------------------------------------------------------------------- #
# Business-day arithmetic
# --------------------------------------------------------------------------- #


def test_add_business_days_across_a_weekend():
    # Friday 2026-02-06 + 1 business day skips the weekend to Monday 2026-02-09.
    # (Not 2026-01-16 -- that Friday's "next business day" is 2026-01-20, not
    # 01-19, because 2026-01-19 is Martin Luther King, Jr. Day, a Maine legal
    # holiday under 4 M.R.S. §1051; that interaction is its own test below.)
    friday = date(2026, 2, 6)
    assert friday.weekday() == 4
    assert dl.add_business_days(friday, 1) == date(2026, 2, 9)


def test_add_business_days_skips_a_holiday_landing_mid_week():
    # Friday 2026-01-16 + 1 business day: weekend-only arithmetic would give
    # Monday 2026-01-19, but that Monday is Martin Luther King, Jr. Day (4
    # M.R.S. §1051), so the correct next business day is Tuesday 2026-01-20.
    friday = date(2026, 1, 16)
    assert friday.weekday() == 4
    assert dl.maine_legal_holiday_label(date(2026, 1, 19)) == "Martin Luther King, Jr. Day"
    assert dl.add_business_days(friday, 1) == date(2026, 1, 20)


def test_add_business_days_start_day_itself_never_counted():
    # A business-day start that is itself a business day is still day zero.
    monday = date(2026, 1, 19)
    assert dl.add_business_days(monday, 1) == date(2026, 1, 20)


def test_add_business_days_matches_the_real_shattuck_notice_window():
    # §5.c.3: notice mailed within 7 business days of submission. The
    # application is dated Thursday 2025-10-02. A weekend-only count would
    # land on Monday 2025-10-13 -- but that Monday is Indigenous Peoples Day
    # (4 M.R.S. §1051), a Maine legal holiday, so it does not count as a
    # business day and the 7th business day is actually Tuesday 2025-10-14.
    # (DECISIONS-NEEDED D-0006 -- was a documented weekend-only limitation;
    # RESOLVED for the statutory floor.)
    assert dl.add_business_days(date(2025, 10, 2), 7) == date(2025, 10, 14)


def test_add_business_days_rejects_negative():
    with pytest.raises(ValueError):
        dl.add_business_days(date(2026, 1, 1), -1)


def test_is_business_day_excludes_maine_legal_holidays():
    # DECISIONS-NEEDED D-0006: RESOLVED for the statutory floor -- Maine
    # legal holidays under 4 M.R.S. §1051 are now excluded, not just
    # weekends. Thanksgiving 2025-11-27 is a Thursday (a weekday) but IS a
    # §1051 holiday, so it must NOT count as a business day.
    thanksgiving_2025 = date(2025, 11, 27)
    assert thanksgiving_2025.weekday() == 3  # a Thursday, i.e. a weekday
    assert dl.is_business_day(thanksgiving_2025) is False


def test_is_business_day_ordinary_weekday_still_a_business_day():
    # Sanity check the calendar isn't over-broad: an ordinary Tuesday with
    # no holiday nearby is still a business day.
    assert dl.is_business_day(date(2025, 10, 14)) is True


@pytest.mark.parametrize(
    "d, label",
    [
        (date(2025, 1, 1), "New Year's Day"),
        (date(2025, 1, 20), "Martin Luther King, Jr. Day"),
        (date(2025, 2, 17), "Washington's Birthday"),
        (date(2025, 4, 21), "Patriots' Day"),
        (date(2025, 5, 26), "Memorial Day"),
        (date(2025, 6, 19), "Juneteenth"),
        (date(2025, 7, 4), "Independence Day"),
        (date(2025, 9, 1), "Labor Day"),
        (date(2025, 10, 13), "Indigenous Peoples Day"),
        (date(2025, 11, 11), "Veterans Day"),
        (date(2025, 11, 27), "Thanksgiving"),
        (date(2025, 12, 25), "Christmas Day"),
    ],
)
def test_maine_legal_holidays_2025_matches_4_mrs_1051(d, label):
    assert dl.maine_legal_holiday_label(d) == label
    assert dl.is_business_day(d) is False


def test_maine_legal_holiday_fixed_date_sunday_shifts_to_monday():
    # 4 M.R.S. §1051's own closing sentence: a holiday falling on Sunday is
    # observed the following Monday. 2028-01-01 is a Saturday and 2023-01-01
    # is a Sunday -- use a year where New Year's Day actually falls on
    # Sunday: 2028-07-04 is a Tuesday; pick a verified case instead --
    # 2023-01-01 was a Sunday, so New Year's Day 2023 was observed Monday
    # 2023-01-02.
    assert dl.maine_legal_holiday_label(date(2023, 1, 1)) is None
    assert dl.maine_legal_holiday_label(date(2023, 1, 2)) == "New Year's Day (observed; 2023-01-01 is a Sunday)"
    assert dl.is_business_day(date(2023, 1, 2)) is False


# --------------------------------------------------------------------------- #
# Month arithmetic -- the §12.j.1 / §8.f.5 six-month recording clock
# --------------------------------------------------------------------------- #


def test_add_months_six_month_recording_clock():
    # The real Shattuck decision date, 2025-12-18, plus six months.
    assert dl.add_months(date(2025, 12, 18), 6) == date(2026, 6, 18)


def test_add_months_clamps_short_target_month():
    # Aug 31 + 6 months -> Feb 2026 has only 28 days (2026 is not a leap
    # year) -- must clamp to Feb 28, never overflow into March.
    assert dl.add_months(date(2025, 8, 31), 6) == date(2026, 2, 28)


def test_add_months_leap_year_clamp():
    assert dl.add_months(date(2027, 8, 31), 6) == date(2028, 2, 29)  # 2028 is a leap year


# --------------------------------------------------------------------------- #
# Clock data -- rulesets/adopted/clocks.json via ruleset_build/build_clocks.py
# --------------------------------------------------------------------------- #


def test_eighteen_clocks_load():
    # F3: 18 -> 22 clocks (added use_permit_decision §15.d.1, and the three
    # missing §23 appeal-track clocks: administrative_appeal_hearing §23.d.2,
    # administrative_appeal_decision §23.d.3, reconsideration_decision §23.e.4)
    # -- see ruleset_build/build_clocks.py's coverage assertion.
    clocks = dl.load_clocks("adopted")
    assert len(clocks) == 22
    assert len({c.clock_key for c in clocks}) == 22  # no duplicate keys


def test_draft_clocks_are_article_8_same_sections():
    adopted = {c.clock_key: c for c in dl.load_clocks("adopted")}
    draft = {c.clock_key: c for c in dl.load_clocks("draft-v0.22")}
    assert set(adopted) == set(draft)
    for key, a in adopted.items():
        d = draft[key]
        assert a.article == 7
        assert d.article == 8  # RENUM_ADOPTED_TO_DRAFT[7] == 8
        assert a.section == d.section
        assert a.subsection == d.subsection
        assert a.days == d.days
        assert a.basis == d.basis


def test_both_recording_clocks_present_with_the_conflict_carried():
    """CRITICAL requirement: §2.e.1 (90 days) and §8.f.5/§12.j.1 (6 months)
    both ship as real clocks, both citing their own section, and NEITHER is
    silently dropped in favor of the other."""
    clocks = {c.clock_key: c for c in dl.load_clocks("adopted")}
    six_month = clocks["subdivision_plat_recorded_6mo"]
    ninety_day = clocks["subdivision_plat_recorded_90d"]

    assert six_month.basis == "months"
    assert six_month.days == 6
    assert (six_month.section, six_month.subsection) == ("12", "j.1")

    assert ninety_day.basis == "calendar"
    assert ninety_day.days == 90
    assert (ninety_day.section, ninety_day.subsection) == ("2", "e.1")

    # Same conflict group, non-empty conflict note on BOTH, and neither may
    # ever auto-generate a recording condition.
    assert six_month.conflict_group == ninety_day.conflict_group == "subdivision_plat_recording"
    assert six_month.conflict_note and ninety_day.conflict_note
    assert "90 days" in six_month.conflict_note and "six months" in six_month.conflict_note
    assert six_month.never_autogenerate_condition is True
    assert ninety_day.never_autogenerate_condition is True


def test_never_autogenerate_condition_is_false_everywhere_else():
    for c in dl.load_clocks("adopted"):
        if c.clock_key not in ("subdivision_plat_recorded_6mo", "subdivision_plat_recorded_90d"):
            assert c.never_autogenerate_condition is False


def test_auto_approval_consequence_only_on_hearing_or_final_action_clocks():
    # F3: use_permit_decision (§15.d.1 -- "review ... and approve ... or ...
    # grant withdrawal", a final-action duty), administrative_appeal_hearing
    # (§23.d.2 -- "hold a public hearing") and administrative_appeal_decision
    # (§23.d.3 -- "make a decision") were added carrying failure_consequence;
    # reconsideration_decision (§23.e.4) was added WITHOUT it -- a vote on
    # whether to alter an existing decision, not itself characterized as a
    # §8.d.1-bearing duty (see its notes in ruleset_build/build_clocks.py and
    # DECISIONS-NEEDED D-0011).
    clocks = {c.clock_key: c for c in dl.load_clocks("adopted")}
    with_consequence = {k for k, c in clocks.items() if c.failure_consequence}
    assert with_consequence == {
        "small_project_decision",
        "large_project_ceo_decision",
        "large_project_pb_completeness_hearing",
        "large_project_pb_decision",
        "subdivision_hearing_decision",
        "special_permit_review_hearing",
        "special_permit_decision",
        "variance_review_hearing",
        "variance_decision",
        "use_permit_decision",
        "administrative_appeal_hearing",
        "administrative_appeal_decision",
    }
    for c in clocks.values():
        if c.failure_consequence:
            assert "must result in the approval of the application" in c.failure_consequence


# --------------------------------------------------------------------------- #
# 2026-08 clock taxonomy (dissolves N1 and the reconsideration half of N2).
# Every one of the 22 clocks is classified from its OWN governing sentence --
# see each clock's duty_kind_note in ruleset_build/build_clocks.py for the
# quoted text. This test pins the classification table itself.
# --------------------------------------------------------------------------- #


def test_duty_kind_classification_table():
    clocks = {c.clock_key: c for c in dl.load_clocks("adopted")}
    assert set(clocks) == {c.clock_key for c in dl.load_clocks("adopted")}  # sanity

    by_kind: dict[str, set[str]] = {}
    for key, c in clocks.items():
        by_kind.setdefault(c.duty_kind, set()).add(key)

    # party_right: what a private party MAY do (§23.d.1 "may file an
    # appeal"; §23.e.1 "may file a request ... to reconsider"). THIS IS N1's
    # FIX -- administrative_appeal used to be modeled with ordinary duty
    # branching, so an unappealed, decided case silently reported it MISSED.
    assert by_kind["party_right"] == {"administrative_appeal", "reconsideration"}

    # conditional_duty: a real municipal duty that exists ONLY once its
    # predicate (a private party's exercise of their party_right above) is
    # recorded. reconsideration_decision is THE RECONSIDERATION HALF OF N2's
    # FIX -- its own governing sentence is textually conditional ("If the
    # Board of Appeals reconsiders..."), so it must never go MISSED on a
    # case where reconsideration was never requested.
    assert by_kind["conditional_duty"] == {
        "administrative_appeal_hearing",
        "administrative_appeal_decision",
        "reconsideration_decision",
    }
    for key in by_kind["conditional_duty"]:
        assert clocks[key].predicate_event is not None

    # applicant_duty: a private APPLICANT (not the Town, not discretionary)
    # must record something -- §12.j.1/§8.f.5 "The applicant will file...",
    # §2.e.1 (inferred, DECISIONS-NEEDED D-0016), §19.c.3 "the applicant
    # must file...". Distinct from notice_mailed's own §5.c.3/§5.c.4 pairing.
    assert by_kind["applicant_duty"] == {
        "notice_mailed",
        "subdivision_plat_recorded_6mo",
        "subdivision_plat_recorded_90d",
        "variance_certificate_recorded",
    }

    # municipal_duty: everything else -- the Town's own unconditional
    # duties. presents_auto_approval_risk() derives ONLY from this set.
    assert by_kind["municipal_duty"] == set(clocks) - (
        by_kind["party_right"] | by_kind["conditional_duty"] | by_kind["applicant_duty"]
    )
    assert len(by_kind["municipal_duty"]) == 13

    # Every clock's classification is auditable -- a quoted governing
    # sentence, not a bare label.
    for c in clocks.values():
        assert c.duty_kind_note and len(c.duty_kind_note) > 20


def test_duty_kind_predicate_events_name_a_real_casefacts_field():
    for c in dl.load_clocks("adopted"):
        if c.duty_kind == "conditional_duty":
            assert hasattr(dl.CaseFacts("x", "variance"), c.predicate_event)
        else:
            assert c.predicate_event is None


# --------------------------------------------------------------------------- #
# compute_deadlines() -- track applicability, branching, statuses
# --------------------------------------------------------------------------- #


def test_large_project_ceo_track_clock_disappears_once_forwarded_to_pb():
    as_of = date(2026, 1, 1)
    not_forwarded = dl.CaseFacts(
        case_id="c1", review_track="large_project_plan", submitted_at=date(2025, 12, 1)
    )
    forwarded = dl.CaseFacts(
        case_id="c1", review_track="large_project_plan",
        submitted_at=date(2025, 12, 1), forwarded_to_pb_at=date(2025, 12, 5),
    )
    rows_not_forwarded = {d.clock_key: d for d in dl.compute_deadlines(not_forwarded, as_of=as_of)}
    rows_forwarded = {d.clock_key: d for d in dl.compute_deadlines(forwarded, as_of=as_of)}

    # Before forwarding: the CEO clock applies and has started; the PB
    # completeness+hearing clock is still listed (large_project_plan is in
    # its applies_to unconditionally) but honestly PENDING_START, since its
    # own start_event (forwarded_to_pb_at) hasn't happened.
    assert "large_project_ceo_decision" in rows_not_forwarded
    assert rows_not_forwarded["large_project_ceo_decision"].start_date is not None
    assert rows_not_forwarded["large_project_pb_completeness_hearing"].status == dl.ClockStatus.PENDING_START.value

    # After forwarding: requires_absent=["forwarded_to_pb_at"] drops the CEO
    # clock entirely (CONTRACT.md framing -- it never applied to this branch
    # once forwarded, not merely "missed"); the PB clock now has a real start date.
    assert "large_project_ceo_decision" not in rows_forwarded
    assert rows_forwarded["large_project_pb_completeness_hearing"].start_date == date(2025, 12, 5)


def test_pending_start_when_start_event_unknown():
    # 2026-08 clock-taxonomy semantics (deliberate change): every applicable
    # clock is either PENDING_START (a real duty whose start_event hasn't
    # happened) or, for the two conditional_duty §23 appeal clocks
    # (administrative_appeal_hearing, administrative_appeal_decision),
    # NOT_TRIGGERED -- their predicate (an appeal was ever filed) is also
    # honestly absent on a case with nothing recorded, which is a MORE
    # precise statement than PENDING_START ("this duty doesn't exist yet"
    # vs. "this duty applies but hasn't started"). Before the taxonomy pass
    # these two reported PENDING_START like everything else, because
    # NOT_TRIGGERED did not exist as a distinct status.
    case = dl.CaseFacts(case_id="c2", review_track="subdivision")  # nothing recorded yet
    rows = dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)
    assert rows  # applicable clocks still enumerated
    conditional = {"administrative_appeal_hearing", "administrative_appeal_decision"}
    assert all(
        d.status == (
            dl.ClockStatus.NOT_TRIGGERED.value if d.clock_key in conditional
            else dl.ClockStatus.PENDING_START.value
        )
        for d in rows
    )
    assert any(d.clock_key in conditional for d in rows)  # the exception actually exercised
    assert all(d.due_date is None for d in rows)


def test_waived_and_na_overrides_win_over_computed_status():
    case = dl.CaseFacts(
        case_id="c3", review_track="subdivision", submitted_at=date(2025, 1, 1),
        waived_clocks=frozenset({"notice_mailed"}),
        na_clocks=frozenset({"subdivision_completeness"}),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    assert rows["notice_mailed"].status == dl.ClockStatus.WAIVED.value
    assert rows["subdivision_completeness"].status == dl.ClockStatus.NOT_APPLICABLE.value


# --------------------------------------------------------------------------- #
# Missed deadline -> auto-approval consequence surfaced (§8.d.1)
# --------------------------------------------------------------------------- #


def test_missed_deadline_surfaces_the_auto_approval_consequence():
    # A Small Project Plan submitted long enough ago that its 10-day CEO
    # decision clock has blown, with no decision recorded.
    case = dl.CaseFacts(case_id="c4", review_track="small_project_plan", submitted_at=date(2026, 1, 1))
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 2, 1), include_meeting_clocks=False)}
    d = rows["small_project_decision"]

    assert d.status == dl.ClockStatus.MISSED.value
    assert d.failure_consequence is not None
    assert "must result in the approval of the application" in d.failure_consequence
    assert d.auto_approval_alert is not None
    assert "AUTO-APPROVAL" in d.auto_approval_alert
    assert "§8.d.1" in d.auto_approval_alert


def test_missed_notice_clock_does_not_claim_auto_approval():
    # notice_mailed carries no §8.d.1 consequence -- mailing notice is
    # neither "holding a public hearing" nor "taking final action".
    case = dl.CaseFacts(case_id="c5", review_track="subdivision", submitted_at=date(2025, 1, 1))
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    d = rows["notice_mailed"]
    assert d.status == dl.ClockStatus.MISSED.value
    assert d.failure_consequence is None
    assert d.auto_approval_alert is None


def test_upcoming_auto_approval_risk_is_flagged_before_it_is_missed():
    case = dl.CaseFacts(case_id="c6", review_track="small_project_plan", submitted_at=date(2026, 1, 20))
    # due_date = 2026-01-30 (10 calendar days); 3 days out at as_of.
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 27), include_meeting_clocks=False)}
    d = rows["small_project_decision"]
    assert d.status == dl.ClockStatus.OPEN.value
    assert d.auto_approval_alert is not None
    assert "AUTO-APPROVAL RISK" in d.auto_approval_alert


# --------------------------------------------------------------------------- #
# open_deadlines() -- dashboard aggregation across cases
# --------------------------------------------------------------------------- #


def test_open_deadlines_only_returns_open_and_missed_sorted_by_severity():
    as_of = date(2026, 2, 1)
    missed_with_consequence = dl.CaseFacts(
        case_id="missed-auto-approval", review_track="small_project_plan", submitted_at=date(2026, 1, 1)
    )
    open_case = dl.CaseFacts(
        case_id="still-open", review_track="small_project_plan", submitted_at=date(2026, 1, 25)
    )
    met_case = dl.CaseFacts(
        case_id="already-met", review_track="small_project_plan",
        submitted_at=date(2026, 1, 25), decision_at=date(2026, 1, 26),
    )
    pending_case = dl.CaseFacts(case_id="not-started", review_track="subdivision")

    rows = dl.open_deadlines(
        [missed_with_consequence, open_case, met_case, pending_case], as_of=as_of
    )
    by_key = {(d.case_id, d.clock_key): d for d in rows}

    # The clock that was actually satisfied never appears, even though its
    # case has other (meeting/draft_due/decision_filed_with_clerk) clocks
    # still open -- MET is per-CLOCK, not per-case.
    assert ("already-met", "small_project_decision") not in by_key
    assert ("missed-auto-approval", "small_project_decision") in by_key
    assert ("still-open", "small_project_decision") in by_key
    # A case with nothing recorded yet still surfaces its meeting/draft_due
    # clocks (those don't depend on any case-specific fact), but never a
    # statutory clock whose start_event hasn't happened (PENDING_START is
    # excluded from the dashboard, same as MET/WAIVED/N-A).
    assert ("not-started", "meeting") in by_key or ("not-started", "draft_due") in by_key
    assert not any(k[0] == "not-started" and k[1] not in ("meeting", "draft_due") for k in by_key)

    # The missed, auto-approval-carrying clock must sort first.
    assert rows[0].case_id == "missed-auto-approval"
    assert rows[0].clock_key == "small_project_decision"
    assert rows[0].status == dl.ClockStatus.MISSED.value
    assert rows[0].failure_consequence is not None


def test_open_deadlines_requires_exactly_one_of_cases_or_conn():
    with pytest.raises(ValueError):
        dl.open_deadlines()
    with pytest.raises(ValueError):
        dl.open_deadlines([], conn=object())


# --------------------------------------------------------------------------- #
# app/deadlines.py -- naming reconciliation shim
# --------------------------------------------------------------------------- #


def test_app_deadlines_reexports_engine_deadlines_with_no_duplicated_logic():
    from app import deadlines as app_dl

    assert app_dl.compute_deadlines is dl.compute_deadlines
    assert app_dl.open_deadlines is dl.open_deadlines
    assert app_dl.CaseFacts is dl.CaseFacts
    assert app_dl.add_business_days is dl.add_business_days


# --------------------------------------------------------------------------- #
# The real Shattuck subdivision (M003, L059) -- pure CaseFacts reconstruction
# --------------------------------------------------------------------------- #


def _shattuck_case() -> dl.CaseFacts:
    return dl.CaseFacts(
        case_id="shattuck-m003-l059",
        review_track="subdivision",
        label="M003, L059 (White Rd, Shattuck) Subdivision",
        # Ground truth gives no distinct Town "received" date -- the only
        # submission-shaped fact is the date on the application itself.
        submitted_at=date(2025, 10, 2),
        submitted_at_source="application_dated",
        notice_mailed_at=date(2025, 11, 4),
        notice_published_at=date(2025, 11, 6),
        hearing_opened_at=date(2025, 11, 20),
        hearing_closed_at=date(2025, 12, 18),
        decision_at=date(2025, 12, 18),
        # completeness_at deliberately NOT set -- ground truth never states a
        # completeness-determination date; a real re-notice, deliberately
        # NOT smoothed into one date (see the two history rows below).
        history=(
            {"kind": "pre_submittal_meeting", "occurred_on": "2025-10-16", "note": None},
            {"kind": "circulated", "occurred_on": "2025-10-16", "note": None},
            {
                "kind": "notice_mailed", "occurred_on": None,
                "note": "original notice, ahead of the Oct 16 meeting -- superseded; exact date not in the record",
            },
            {
                "kind": "notice_mailed", "occurred_on": "2025-11-04",
                "note": "re-notice after the hearing was rescheduled to Nov 20",
            },
        ),
    )


def test_shattuck_reconstruction_notice_mailed_clock():
    case = _shattuck_case()
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    d = rows["notice_mailed"]
    assert d.start_date == date(2025, 10, 2)
    assert d.due_date == date(2025, 10, 14)          # 7 business days from Oct 2, skipping
                                                       # Indigenous Peoples Day (2025-10-13)
    assert d.satisfied_at == date(2025, 11, 4)        # the only mailed date this app has
    assert d.status == dl.ClockStatus.MISSED.value    # honestly late against the literal rule
    assert d.failure_consequence is None              # not an §8.d.1 hearing/final-action clock
    assert d.citation_short == "Art. 7, Sec. 5.c.3"


def test_shattuck_reconstruction_represents_the_reschedule_not_one_smoothed_date():
    case = _shattuck_case()
    notice_history = [h for h in case.history if h["kind"] == "notice_mailed"]
    assert len(notice_history) == 2  # the original AND the re-notice, not collapsed into one
    assert notice_history[0]["occurred_on"] is None  # honestly unknown, never fabricated
    assert "superseded" in notice_history[0]["note"]
    assert notice_history[1]["occurred_on"] == "2025-11-04"
    assert "rescheduled" in notice_history[1]["note"]


def test_shattuck_reconstruction_completeness_is_honestly_pending():
    # Ground truth never states a completeness-determination date -- the
    # engine must NOT infer one (e.g. from the pre-submittal meeting or the
    # hearing date). §12.e.3's own clock (submitted_at -> completeness_at)
    # DID start (submitted_at is known) and its 30-day window has since
    # passed with no completeness_at on record, so it is honestly MISSED --
    # not smoothed into "pending" just because the record is incomplete.
    # subdivision_hearing_decision's start_event IS completeness_at itself,
    # which is unknown, so THAT clock has no start date at all and stays
    # PENDING_START.
    case = _shattuck_case()
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    completeness = rows["subdivision_completeness"]
    assert completeness.start_date == date(2025, 10, 2)
    assert completeness.due_date == date(2025, 11, 1)
    assert completeness.satisfied_at is None
    assert completeness.status == dl.ClockStatus.MISSED.value

    hearing_decision = rows["subdivision_hearing_decision"]
    assert hearing_decision.status == dl.ClockStatus.PENDING_START.value
    assert hearing_decision.start_date is None
    assert hearing_decision.due_date is None


def test_shattuck_reconstruction_findings_and_recording_clocks():
    case = _shattuck_case()
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}

    findings = rows["subdivision_findings_issued"]
    assert findings.start_date == date(2025, 12, 18)
    assert findings.due_date == date(2026, 1, 17)          # 30 calendar days from decision
    assert findings.status == dl.ClockStatus.OPEN.value    # as_of 2026-01-01 is still before the due date

    six_month = rows["subdivision_plat_recorded_6mo"]
    assert six_month.due_date == date(2026, 6, 18)

    ninety_day = rows["subdivision_plat_recorded_90d"]
    assert ninety_day.due_date == date(2026, 3, 18)

    # Both recording clocks present on this one real case, with the conflict
    # note attached to both, never collapsed to a single "correct" deadline.
    assert six_month.conflict_note == ninety_day.conflict_note
    assert six_month.never_autogenerate_condition and ninety_day.never_autogenerate_condition


def test_shattuck_reconstruction_decision_filed_and_appeal_are_honestly_pending():
    # Ground truth never states a Town Clerk filing date -- decision_filed_at
    # stays unset, so decision_filed_with_clerk (and, downstream,
    # administrative_appeal, which anchors on the CLERK'S date stamp, not the
    # decision date itself) must both stay PENDING_START, never guessed from
    # the decision date.
    case = _shattuck_case()
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    assert rows["decision_filed_with_clerk"].start_date == date(2025, 12, 18)
    assert rows["decision_filed_with_clerk"].due_date == date(2025, 12, 26)  # 5 business days
                                                                               # from Dec 18, skipping
                                                                               # Christmas Day (2025-12-25)
    assert rows["administrative_appeal"].status == dl.ClockStatus.PENDING_START.value
    assert rows["administrative_appeal"].start_date is None


def test_shattuck_full_table_every_applicable_clock_present():
    """A whole-table smoke check: every subdivision-track clock defined in
    clocks.json shows up for the Shattuck case (nothing silently dropped)."""
    case = _shattuck_case()
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1))}
    expected = {
        c.clock_key for c in dl.load_clocks("adopted") if "subdivision" in c.applies_to
    } | {"meeting", "draft_due"}
    assert set(rows) == expected


# --------------------------------------------------------------------------- #
# The real Shattuck subdivision -- rebuilt through the DB layer (cases +
# case_milestones, including a genuine superseded_by re-notice chain), then
# through load_all_case_facts()/open_deadlines(conn=...).
# --------------------------------------------------------------------------- #


def _insert_ruleset(conn, *, ruleset_key="adopted", binding=1) -> str:
    rid = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, adopted_on, built_at,
             builder_version, manifest_path, source_sha_json, is_current, created_at)
        VALUES (?, ?, ?, ?, 'adopted', '2020-11-03', '2026-08-20T00:00:00Z',
                'ruleset_build/2.0.0', 'rulesets/adopted/manifest.json', '{}', ?, '2026-08-20T00:00:00Z')
        """,
        (rid, ruleset_key, ruleset_key, binding, 1 if binding else 0),
    )
    return rid


def _insert_case(conn, ruleset_id: str) -> str:
    cid = "shattuck-m003-l059-db"
    conn.execute(
        """
        INSERT INTO cases
            (id, label, application_type, ruleset_id, is_scratch, status,
             received_at, created_at, updated_at)
        VALUES (?, ?, 'subdivision', ?, 0, 'decided', NULL, '2025-10-02T00:00:00Z', '2025-12-18T00:00:00Z')
        """,
        (cid, "M003, L059 (White Rd, Shattuck) Subdivision", ruleset_id),
    )
    return cid


def _insert_milestone(conn, case_id: str, kind: str, occurred_on: str, note: str | None = None) -> str:
    mid = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO case_milestones (id, case_id, kind, occurred_on, note, created_at)
        VALUES (?, ?, ?, ?, ?, '2026-08-20T00:00:00Z')
        """,
        (mid, case_id, kind, occurred_on, note),
    )
    return mid


@pytest.fixture()
def shattuck_conn(tmp_path):
    conn = db.connect(tmp_path / "permit-review.db")
    db.migrate(conn, MIGRATIONS_DIR)
    ruleset_id = _insert_ruleset(conn)
    case_id = _insert_case(conn, ruleset_id)

    _insert_milestone(conn, case_id, "application_dated", "2025-10-02")
    _insert_milestone(conn, case_id, "pre_submittal_meeting", "2025-10-16")
    _insert_milestone(conn, case_id, "circulated", "2025-10-16")

    # The re-notice, represented as a genuine superseded_by chain -- the
    # ORIGINAL notice row is superseded by the re-notice row, never deleted,
    # never overwritten, and never collapsed into one date.
    original_notice = _insert_milestone(
        conn, case_id, "notice_mailed", "2025-10-09",  # a plausible pre-Oct-16 mailing date
        "original notice ahead of the Oct 16 meeting",
    )
    renotice = _insert_milestone(
        conn, case_id, "notice_mailed", "2025-11-04",
        "re-notice after the hearing was rescheduled to Nov 20",
    )
    # N3: explicitly a RESCHEDULE, not a CORRECTION -- the original notice
    # genuinely was mailed and genuinely did satisfy the notice duty live at
    # the time; it is only superseded because the hearing itself moved.
    # Without this, engine/deadlines.py's conservative default (an unmarked
    # supersede counts as a CORRECTION, never a RESCHEDULE -- see
    # DECISIONS-NEEDED D-0016) would exclude the original from
    # _first_satisfying_occurrence(), which is wrong for THIS fixture's own
    # documented facts.
    conn.execute(
        "UPDATE case_milestones SET superseded_by = ?, supersede_reason = 'reschedule' WHERE id = ?",
        (renotice, original_notice),
    )

    _insert_milestone(conn, case_id, "notice_published", "2025-11-06")
    _insert_milestone(conn, case_id, "hearing_opened", "2025-11-20")
    _insert_milestone(conn, case_id, "hearing_closed", "2025-12-18")
    _insert_milestone(conn, case_id, "decision_issued", "2025-12-18")

    yield conn, case_id
    conn.close()


def test_shattuck_db_live_milestone_excludes_the_superseded_notice(shattuck_conn):
    conn, case_id = shattuck_conn
    live = conn.execute(
        "SELECT kind, occurred_on FROM case_milestones WHERE case_id = ? AND superseded_by IS NULL AND kind = 'notice_mailed'",
        (case_id,),
    ).fetchall()
    assert len(live) == 1
    assert live[0]["occurred_on"] == "2025-11-04"  # the re-notice, not the original

    # But the original is NOT deleted -- it is still in the table, just not live.
    all_notices = conn.execute(
        "SELECT occurred_on FROM case_milestones WHERE case_id = ? AND kind = 'notice_mailed' ORDER BY occurred_on",
        (case_id,),
    ).fetchall()
    assert [r["occurred_on"] for r in all_notices] == ["2025-10-09", "2025-11-04"]


def test_shattuck_db_case_facts_from_row_matches_the_pure_reconstruction(shattuck_conn):
    conn, case_id = shattuck_conn
    facts = dl.load_all_case_facts(conn)
    case = next(c for c in facts if c.case_id == case_id)

    assert case.review_track == "subdivision"
    assert case.submitted_at == date(2025, 10, 2)
    assert case.submitted_at_source == "application_dated"  # no received_at recorded in this fixture
    assert case.notice_mailed_at == date(2025, 11, 4)        # the LIVE (re-notice) row, not the superseded one
    assert case.notice_published_at == date(2025, 11, 6)
    assert case.hearing_opened_at == date(2025, 11, 20)
    assert case.hearing_closed_at == date(2025, 12, 18)
    assert case.decision_at == date(2025, 12, 18)
    assert case.completeness_at is None  # never recorded -- honestly absent


def test_shattuck_db_open_deadlines_flags_the_real_missed_clocks(shattuck_conn):
    conn, case_id = shattuck_conn
    rows = dl.open_deadlines(conn=conn, as_of=date(2026, 1, 1))
    by_key = {(d.case_id, d.clock_key): d for d in rows}

    # F7 FIX: notice_mailed is now MET, not MISSED -- the ORIGINAL notice
    # (2025-10-09, superseded_by the re-notice for DISPLAY purposes only)
    # genuinely satisfied the 7-business-day window (due 2025-10-13). Before
    # the fix, load_all_case_facts()/case_facts_from_row() read ONLY the live
    # row (superseded_by IS NULL) -- the re-notice, 2025-11-04 -- so the
    # engine never even saw the original notice existed, and reported a
    # deadline missed that a human reading the real record would not have.
    # A MET clock never appears in open_deadlines() at all.
    assert (case_id, "notice_mailed") not in by_key

    # decision_filed_with_clerk never happened in this fixture (no such
    # milestone kind was inserted) and its due date has passed.
    assert (case_id, "decision_filed_with_clerk") in by_key
    assert by_key[(case_id, "decision_filed_with_clerk")].status == dl.ClockStatus.MISSED.value

    # F4 FIX: administrative_appeal's own start_event (decision_filed_at) was
    # never recorded either, so it is PENDING_START -- but its statutory
    # predecessor (decision_filed_with_clerk, whose satisfying_event IS
    # administrative_appeal's start_event) is itself MISSED. Before the fix
    # this clock was silently absent from open_deadlines() (PENDING_START was
    # unconditionally excluded); now it surfaces with a visible reason.
    assert (case_id, "administrative_appeal") in by_key
    appeal = by_key[(case_id, "administrative_appeal")]
    assert appeal.status == dl.ClockStatus.PENDING_START.value
    assert appeal.start_not_recorded_alert is not None
    assert "START NOT RECORDED" in appeal.start_not_recorded_alert
    assert "decision_filed_with_clerk" not in appeal.start_not_recorded_alert  # human label, not the key
    assert "Decision filed with the Town Clerk" in appeal.start_not_recorded_alert


def test_shattuck_db_notice_mailed_satisfied_by_a_genuine_reschedule(shattuck_conn):
    """F7/N3, isolated: compute_deadlines() must consult the FULL milestone
    history (live and superseded), not just the live/latest row, when
    resolving a SATISFYING event -- but ONLY credit a superseded occurrence
    that is explicitly recorded as a genuine RESCHEDULE (supersede_reason
    = 'reschedule', set by shattuck_conn's own fixture -- see its comment).

    N3 REWRITE (was test_shattuck_db_notice_mailed_satisfied_by_the_
    superseded_original): the original version of this test asserted the
    SAME outcome (the earliest date wins) with NO reason recorded at all,
    because engine/deadlines.py used to take the earliest superseded date
    unconditionally -- correct for THIS fixture's facts (a genuine re-notice)
    but for the wrong reason, and it would have produced the identical,
    WRONG 'earliest wins' outcome for a genuine typo-correction too (N3's
    own repro, see test_shattuck_db_notice_mailed_not_satisfied_by_a_
    correction below). This version pins the fixture's explicit
    supersede_reason and asserts on it, so a change to that reason FAILS
    this test instead of silently changing behavior for the wrong reason."""
    conn, case_id = shattuck_conn
    original = conn.execute(
        "SELECT supersede_reason FROM case_milestones "
        "WHERE case_id = ? AND kind = 'notice_mailed' AND occurred_on = '2025-10-09'",
        (case_id,),
    ).fetchone()
    assert original["supersede_reason"] == "reschedule"

    facts = next(c for c in dl.load_all_case_facts(conn) if c.case_id == case_id)
    rows = {d.clock_key: d for d in dl.compute_deadlines(facts, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    notice = rows["notice_mailed"]
    assert notice.satisfied_at == date(2025, 10, 9)  # the ORIGINAL, first GENUINE occurrence
    assert notice.status == dl.ClockStatus.MET.value
    # The scalar CaseFacts field itself still reports the LIVE value, for
    # anything that displays "the current notice date" rather than asking
    # "was the duty performed" -- these are deliberately different questions.
    assert facts.notice_mailed_at == date(2025, 11, 4)


def test_shattuck_db_notice_mailed_not_satisfied_by_a_superseded_correction(tmp_path):
    """N3's own repro: notice_mailed is recorded as 2025-10-04 -- a typo,
    the operator meant 2025-11-04 -- then corrected via supersedes_id with
    supersede_reason='correction'. The typo'd date never really happened as
    recorded, so it must NOT satisfy the notice duty; only the CORRECTED
    2025-11-04 date counts, and that date is genuinely late against the
    7-business-day window (due 2025-10-14, from the 2025-10-02 application
    date) -- so the duty is honestly MISSED, not falsely MET by a
    data-entry error the way it was before this fix (a corrected typo used
    to satisfy a duty that was actually missed)."""
    conn = db.connect(tmp_path / "permit-review.db")
    db.migrate(conn, MIGRATIONS_DIR)
    ruleset_id = _insert_ruleset(conn)
    case_id = _insert_case(conn, ruleset_id)
    _insert_milestone(conn, case_id, "application_dated", "2025-10-02")

    typo_id = _insert_milestone(conn, case_id, "notice_mailed", "2025-10-04", "typo -- meant 2025-11-04")
    correction_id = _insert_milestone(conn, case_id, "notice_mailed", "2025-11-04", "correcting the 2025-10-04 typo")
    conn.execute(
        "UPDATE case_milestones SET superseded_by = ?, supersede_reason = 'correction' WHERE id = ?",
        (correction_id, typo_id),
    )

    facts = next(c for c in dl.load_all_case_facts(conn) if c.case_id == case_id)
    rows = {d.clock_key: d for d in dl.compute_deadlines(facts, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    notice = rows["notice_mailed"]
    assert notice.satisfied_at == date(2025, 11, 4)  # the CORRECTION -- never the typo
    assert notice.status == dl.ClockStatus.MISSED.value  # honestly late
    conn.close()


def test_shattuck_db_notice_mailed_legacy_unmarked_supersede_defaults_conservative(tmp_path):
    """DECISIONS-NEEDED D-0016: a superseded row with NO supersede_reason
    recorded at all (NULL -- e.g. a row written before
    0007_supersede_reason.sql existed) defaults to the SAME conservative
    reading as an explicit 'correction': excluded from satisfying-occurrence
    credit. This is deliberate -- it can only ever make the engine
    UNDER-credit a duty that really was performed on time (an operator can
    always go back and supply the missing reason), never manufacture false
    compliance out of an unverified date the way defaulting to 'reschedule'
    would have."""
    conn = db.connect(tmp_path / "permit-review.db")
    db.migrate(conn, MIGRATIONS_DIR)
    ruleset_id = _insert_ruleset(conn)
    case_id = _insert_case(conn, ruleset_id)
    _insert_milestone(conn, case_id, "application_dated", "2025-10-02")

    original_id = _insert_milestone(conn, case_id, "notice_mailed", "2025-10-04")
    later_id = _insert_milestone(conn, case_id, "notice_mailed", "2025-11-04")
    # No supersede_reason at all -- simulating a legacy pre-0007 row.
    conn.execute("UPDATE case_milestones SET superseded_by = ? WHERE id = ?", (later_id, original_id))
    assert conn.execute(
        "SELECT supersede_reason FROM case_milestones WHERE id = ?", (original_id,)
    ).fetchone()["supersede_reason"] is None

    facts = next(c for c in dl.load_all_case_facts(conn) if c.case_id == case_id)
    rows = {d.clock_key: d for d in dl.compute_deadlines(facts, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    notice = rows["notice_mailed"]
    assert notice.satisfied_at == date(2025, 11, 4)
    assert notice.status == dl.ClockStatus.MISSED.value
    conn.close()


def test_shattuck_db_application_received_milestone_outranks_application_dated(shattuck_conn):
    conn, case_id = shattuck_conn
    # Record a distinct Town receipt date, later than the form's own date --
    # this must now win over 'application_dated' as submitted_at's source.
    _insert_milestone(conn, case_id, "application_received", "2025-10-06")

    facts = dl.load_all_case_facts(conn)
    case = next(c for c in facts if c.case_id == case_id)
    assert case.submitted_at == date(2025, 10, 6)
    assert case.submitted_at_source == "application_received"


# --------------------------------------------------------------------------- #
# Post-reconciliation Shattuck reconstruction -- adds two ground-truth facts
# confirmed directly against the adopted FoF & CoL PDF (docs/Findings of Fact
# and Conclusions of Law/M003, L059 (White Road, Shattuck), Subdivision FoF &
# CoL 2025.12.18.pdf) that shattuck_conn's older fixture leaves unset:
#   - p.11, "Complete Application" motion, carried 7-0 -- completeness was
#     determined at the SAME December 18, 2025 meeting as the decision
#     itself. This is the exact practice D-0012 (F1's residual legal
#     question) names, sourced to "the real Shattuck record, p.13" -- now
#     independently confirmed against the PDF's own page 11 (12 of 16 in the
#     document's own footer numbering).
#   - p.14, "Findings Of Fact" motion ("to accept and adopt the draft
#     findings of fact and conclusions of law, as amended"), carried 7-0 the
#     same meeting -- recorded via F6's first-class 'findings_issued' kind.
# This makes the REAL Shattuck case's own subdivision_hearing_decision clock
# MET (not stalled) -- F1's stalled-subdivision scenario is a distinct,
# hypothetical control case (see test_f1_repro_stalled_subdivision_presents_
# auto_approval_risk above), not something that happened to Shattuck itself.
# --------------------------------------------------------------------------- #


def test_shattuck_db_full_reconstruction_with_completeness_and_findings(shattuck_conn):
    conn, case_id = shattuck_conn
    _insert_milestone(conn, case_id, "completeness_determined", "2025-12-18",
                       "'Complete Application' motion carried 7-0 (FoF & CoL p.11)")
    _insert_milestone(conn, case_id, "findings_issued", "2025-12-18",
                       "Findings of Fact and Conclusions of Law adopted 7-0 (FoF & CoL p.14)")

    facts = next(c for c in dl.load_all_case_facts(conn) if c.case_id == case_id)
    assert facts.completeness_at == date(2025, 12, 18)
    assert facts.findings_issued_at == date(2025, 12, 18)

    rows = {d.clock_key: d for d in dl.compute_deadlines(facts, as_of=date(2026, 1, 15), include_meeting_clocks=False)}

    # subdivision_completeness (§12.e.3, due 2025-11-01) is MET LATE --
    # determined 2025-12-18, after its own 30-day due date -- so MISSED, not
    # PENDING_START and not silently "fine because it eventually happened".
    completeness = rows["subdivision_completeness"]
    assert completeness.satisfied_at == date(2025, 12, 18)
    assert completeness.status == dl.ClockStatus.MISSED.value

    # subdivision_hearing_decision (§12.e.5, the §8.d.1-bearing clock) now
    # STARTS the same day completeness was determined and is satisfied the
    # same day (Newcastle's actual practice) -- MET, comfortably inside the
    # 30-day window from its own start.
    hearing_decision = rows["subdivision_hearing_decision"]
    assert hearing_decision.start_date == date(2025, 12, 18)
    assert hearing_decision.status == dl.ClockStatus.MET.value
    assert dl.presents_auto_approval_risk(hearing_decision) is False  # nothing to warn about here

    # F6: findings issued the same day, via the first-class kind, comfortably
    # inside the 30-day window (due 2026-01-17).
    findings = rows["subdivision_findings_issued"]
    assert findings.satisfied_at == date(2025, 12, 18)
    assert findings.status == dl.ClockStatus.MET.value
    live_kinds = {r["kind"] for r in conn.execute(
        "SELECT kind FROM case_milestones WHERE case_id = ? AND superseded_by IS NULL", (case_id,)
    ).fetchall()}
    assert "findings_issued" in live_kinds


# --------------------------------------------------------------------------- #
# F6 -- 'findings_issued' / 'certificate_recorded' are first-class
# case_milestones.kind values (0005_deadline_engine_fixes.sql); the retired
# 'other'+note-substring bridging convention is gone from the engine.
# --------------------------------------------------------------------------- #


def test_findings_issued_and_certificate_recorded_are_first_class_kinds():
    from app import cases as cases_mod

    assert "findings_issued" in cases_mod.CASE_MILESTONE_KINDS
    assert "certificate_recorded" in cases_mod.CASE_MILESTONE_KINDS
    assert dl._MILESTONE_TO_FIELD["findings_issued"] == "findings_issued_at"
    assert dl._MILESTONE_TO_FIELD["certificate_recorded"] == "certificate_recorded_at"


def test_other_kind_note_no_longer_bridges_to_findings_or_certificate():
    """F6, isolated: a fresh 'other' row, however its note reads, must NEVER
    populate findings_issued_at/certificate_recorded_at any more -- that was
    exactly the undocumented magic-substring behaviour being retired. The
    ONLY way to record either statutory event now is the first-class kind."""
    case = dl.CaseFacts(
        case_id="c-f6", review_track="subdivision",
        history=(
            {"kind": "other", "occurred_on": "2026-01-05",
             "note": "Findings of Fact and Conclusions of Law adopted"},
        ),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    # subdivision_findings_issued's satisfying_event (findings_issued_at) has
    # no scalar value AND no 'findings_issued'-kind history entry -- the
    # 'other' row above, however suggestive its note, must not satisfy it.
    assert rows["subdivision_findings_issued"].satisfied_at is None


def _copy_migrations(src_dir: Path, dst_dir: Path, names: list[str]) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        (dst_dir / name).write_text((src_dir / name).read_text(encoding="utf-8"), encoding="utf-8")


def test_migration_0005_reclassifies_existing_other_rows_conservatively(tmp_path):
    """F6's migration must mirror the RETIRED bridging convention's own
    if/elif precedence (finding checked before certificate) for any
    'other' row already on disk when it runs, so no existing row's
    EFFECTIVE meaning changes -- only its `kind` becomes explicit."""
    pre_0005 = sorted(
        f.name for f in MIGRATIONS_DIR.glob("*.sql") if f.name < "0005_deadline_engine_fixes.sql"
    )
    assert pre_0005, "expected at least one migration before 0005"

    staged_dir = tmp_path / "migrations_pre_0005"
    _copy_migrations(MIGRATIONS_DIR, staged_dir, pre_0005)

    conn = db.connect(tmp_path / "permit-review.db")
    db.migrate(conn, staged_dir)  # everything EXCEPT 0005

    ruleset_id = _insert_ruleset(conn)
    case_id = _insert_case(conn, ruleset_id)
    # A pre-existing 'other' row using the OLD bridging convention's own
    # words -- 'other' is still a legal kind under every pre-0005 CHECK.
    conn.execute(
        "INSERT INTO case_milestones (id, case_id, kind, occurred_on, note, created_at) "
        "VALUES (?, ?, 'other', '2026-01-10', 'Findings of Fact and Conclusions of Law adopted', "
        "'2026-08-20T00:00:00Z')",
        (uuid.uuid4().hex, case_id),
    )
    conn.execute(
        "INSERT INTO case_milestones (id, case_id, kind, occurred_on, note, created_at) "
        "VALUES (?, ?, 'other', '2026-04-01', 'variance certificate recorded at the Registry', "
        "'2026-08-20T00:00:00Z')",
        (uuid.uuid4().hex, case_id),
    )
    # An ordinary 'other' row that matches neither substring -- must pass
    # through UNCHANGED.
    conn.execute(
        "INSERT INTO case_milestones (id, case_id, kind, occurred_on, note, created_at) "
        "VALUES (?, ?, 'other', '2026-01-11', 'applicant called to ask about parking', "
        "'2026-08-20T00:00:00Z')",
        (uuid.uuid4().hex, case_id),
    )

    db.migrate(conn, MIGRATIONS_DIR)  # now apply 0005 (and anything newer) for real

    rows = {
        r["note"]: r["kind"]
        for r in conn.execute(
            "SELECT kind, note FROM case_milestones WHERE case_id = ?", (case_id,)
        ).fetchall()
    }
    assert rows["Findings of Fact and Conclusions of Law adopted"] == "findings_issued"
    assert rows["variance certificate recorded at the Registry"] == "certificate_recorded"
    assert rows["applicant called to ask about parking"] == "other"
    conn.close()


# --------------------------------------------------------------------------- #
# F8 -- draft_due is MET only when a draft ACTUALLY EXISTS (a
# generated_documents row); the dead, unreachable MISSED branch is gone.
# --------------------------------------------------------------------------- #


def test_draft_due_is_open_not_met_before_the_meeting_with_no_draft():
    case = dl.CaseFacts(case_id="c-draft-1", review_track="subdivision", meeting_date=date(2026, 3, 19))
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 3, 1))}
    draft = rows["draft_due"]
    assert draft.due_date == date(2026, 3, 12)  # meeting - 7 days
    assert draft.status == dl.ClockStatus.OPEN.value
    assert draft.satisfied_at is None


def test_draft_due_is_missed_once_due_with_no_generated_draft():
    """THE core F8 repro: before the fix, this clock flipped to MET the
    instant the calendar date passed, with no draft ever generated -- 'the
    deadline the whole app exists to serve' silently reporting success for
    work never done."""
    case = dl.CaseFacts(case_id="c-draft-2", review_track="subdivision", meeting_date=date(2026, 3, 19))
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 3, 13))}
    draft = rows["draft_due"]
    assert draft.due_date == date(2026, 3, 12)
    assert draft.status == dl.ClockStatus.MISSED.value  # NOT met -- no draft_documents at all
    assert draft.satisfied_at is None


def test_draft_due_is_met_once_a_draft_document_exists_on_time():
    case = dl.CaseFacts(
        case_id="c-draft-3", review_track="subdivision", meeting_date=date(2026, 3, 19),
        draft_documents=(date(2026, 3, 10),),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 3, 13))}
    draft = rows["draft_due"]
    assert draft.status == dl.ClockStatus.MET.value
    assert draft.satisfied_at == date(2026, 3, 10)


def test_draft_due_is_missed_when_the_only_draft_is_late():
    case = dl.CaseFacts(
        case_id="c-draft-4", review_track="subdivision", meeting_date=date(2026, 3, 19),
        draft_documents=(date(2026, 3, 15),),  # generated AFTER the due date (Mar 12)
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 3, 16))}
    draft = rows["draft_due"]
    assert draft.status == dl.ClockStatus.MISSED.value
    assert draft.satisfied_at == date(2026, 3, 15)  # honestly recorded, just too late


def test_draft_due_uses_the_first_generated_draft_not_the_latest_f7_role():
    """A redrafted packet (multiple generated_documents rows) is a
    SATISFYING event -- F7's own principle -- so the FIRST on-time draft
    governs, not whatever was regenerated last."""
    case = dl.CaseFacts(
        case_id="c-draft-5", review_track="subdivision", meeting_date=date(2026, 3, 19),
        draft_documents=(date(2026, 3, 11), date(2026, 3, 8)),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 3, 13))}
    draft = rows["draft_due"]
    assert draft.status == dl.ClockStatus.MET.value
    assert draft.satisfied_at == date(2026, 3, 8)


def test_meeting_clock_has_no_missed_state():
    """The dead, unreachable MISSED branch is deleted for BOTH clocks; for
    `meeting` specifically there is no satisfaction data source to replace
    it with (the Town holds its meeting regardless), so this clock is
    OPEN/MET only, by design -- never MISSED."""
    case = dl.CaseFacts(case_id="c-meet-1", review_track="subdivision", meeting_date=date(2026, 3, 19))
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 4, 1))}  # long after
    assert rows["meeting"].status == dl.ClockStatus.MET.value


# --------------------------------------------------------------------------- #
# F9a/F9b -- never_autogenerate_condition gets a real enforcement consumer,
# and deadline_row() no longer drops the conflict metadata on the floor.
# --------------------------------------------------------------------------- #


def test_guard_condition_autogeneration_blocks_the_protected_plat_recording_clocks():
    case = dl.CaseFacts(case_id="c-guard-1", review_track="subdivision", decision_at=date(2025, 12, 18))
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}

    for key in ("subdivision_plat_recorded_6mo", "subdivision_plat_recorded_90d"):
        with pytest.raises(dl.ProtectedClockError):
            dl.guard_condition_autogeneration(rows[key])


def test_guard_condition_autogeneration_is_a_noop_for_an_ordinary_clock():
    case = dl.CaseFacts(case_id="c-guard-2", review_track="subdivision", submitted_at=date(2025, 1, 1))
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    dl.guard_condition_autogeneration(rows["notice_mailed"])  # must not raise


# --------------------------------------------------------------------------- #
# N4 -- a satisfying occurrence must not predate the clock's own start_date.
# --------------------------------------------------------------------------- #


def test_n4_amended_decision_repro_filing_does_not_predate_its_own_start():
    """N4's exact repro. The Board decides 2026-01-15 and files with the
    Clerk 2026-01-20 (correct, on time -- 5 business days is easily met).
    The Board then issues an AMENDED decision 2026-03-05, which is never
    filed. `decision_at` (the CaseFacts scalar -- 'the latest LIVE
    occurrence') is now 2026-03-05; the only decision_filed_at on record,
    2026-01-20, predates that start by 44 days -- it discharged the filing
    duty for the ORIGINAL decision, not the amended one, and cannot satisfy
    a duty that did not yet exist when it happened.

    BEFORE the fix: decision_filed_with_clerk was MET, satisfied 44 days
    before it started -- engine/deadlines.py:637 had no lower bound at all.
    AFTER the fix: the duty reopens (MISSED here, since as_of is well past
    the amended decision's own 5-business-day due date) and, because
    decision_filed_with_clerk `starts_clock` administrative_appeal, the
    appeal window does not start from the stale filing either -- it stays
    honestly PENDING_START, not silently ticking from 2026-01-20."""
    case = dl.CaseFacts(
        case_id="n4-repro",
        review_track="special_permit",
        decision_at=date(2026, 3, 5),         # the operative, AMENDED decision
        decision_filed_at=date(2026, 1, 20),  # filed only against the ORIGINAL 2026-01-15 decision
    )
    rows = {
        d.clock_key: d
        for d in dl.compute_deadlines(case, as_of=date(2026, 3, 20), include_meeting_clocks=False)
    }

    filed = rows["decision_filed_with_clerk"]
    assert filed.start_date == date(2026, 3, 5)
    assert filed.satisfied_at is None                       # the stale filing no longer counts
    assert filed.stale_satisfaction_at == date(2026, 1, 20)  # but is not silently dropped either
    assert filed.due_date == dl.add_business_days(date(2026, 3, 5), 5)
    assert filed.status == dl.ClockStatus.MISSED.value       # NOT MET (as_of is well past due_date)

    appeal = rows["administrative_appeal"]
    assert appeal.start_date is None                         # NOT 2026-01-20
    assert appeal.due_date is None
    assert appeal.status == dl.ClockStatus.PENDING_START.value


def test_n4_a_satisfying_occurrence_on_or_after_start_still_counts():
    """Control for the repro above: a filing recorded ON/AFTER its own
    clock's start_date is unaffected by the N4 fix -- only a satisfaction
    that PREDATES its start is rejected, never an ordinary, correctly
    ordered one. Chaining still hands the validated date to the successor
    clock, matching the un-amended, single-decision case exactly."""
    case = dl.CaseFacts(
        case_id="n4-control",
        review_track="special_permit",
        decision_at=date(2026, 1, 15),
        decision_filed_at=date(2026, 1, 20),
    )
    rows = {
        d.clock_key: d
        for d in dl.compute_deadlines(case, as_of=date(2026, 3, 10), include_meeting_clocks=False)
    }

    filed = rows["decision_filed_with_clerk"]
    assert filed.satisfied_at == date(2026, 1, 20)
    assert filed.stale_satisfaction_at is None
    assert filed.status == dl.ClockStatus.MET.value

    appeal = rows["administrative_appeal"]
    assert appeal.start_date == date(2026, 1, 20)
    assert appeal.due_date == date(2026, 2, 19)


def test_n4_satisfied_exactly_on_start_date_counts_not_stale():
    """Boundary: satisfied_at == start_date (same day) is NOT stale -- the
    guard is a strict `<`, matching every other "day zero doesn't count
    against you, but isn't rejected either" convention in this module (e.g.
    add_business_days' own start-day docstring)."""
    case = dl.CaseFacts(
        case_id="n4-boundary",
        review_track="special_permit",
        decision_at=date(2026, 1, 15),
        decision_filed_at=date(2026, 1, 15),
    )
    rows = {
        d.clock_key: d
        for d in dl.compute_deadlines(case, as_of=date(2026, 1, 16), include_meeting_clocks=False)
    }
    filed = rows["decision_filed_with_clerk"]
    assert filed.satisfied_at == date(2026, 1, 15)
    assert filed.stale_satisfaction_at is None
    assert filed.status == dl.ClockStatus.MET.value


def test_deadline_row_carries_the_conflict_metadata_through():
    case = dl.CaseFacts(case_id="c-row-1", review_track="subdivision", decision_at=date(2025, 12, 18))
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    row = dl.deadline_row(rows["subdivision_plat_recorded_6mo"], id_="x", created_at="2026-01-01T00:00:00.000Z")
    assert row["never_autogenerate_condition"] == 1
    assert row["conflict_group"] == "subdivision_plat_recording"
    assert row["conflict_note"]

    ordinary = dl.deadline_row(rows["notice_mailed"], id_="y", created_at="2026-01-01T00:00:00.000Z")
    assert ordinary["never_autogenerate_condition"] == 0
    assert ordinary["conflict_group"] is None


def test_deadlines_table_has_the_0005_columns(tmp_path):
    conn = db.connect(tmp_path / "permit-review.db")
    db.migrate(conn, MIGRATIONS_DIR)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(deadlines);").fetchall()}
    assert {"conflict_group", "conflict_note", "never_autogenerate_condition"} <= cols
    conn.close()


# --------------------------------------------------------------------------- #
# F4 -- a clock stuck at PENDING_START behind an overdue predecessor is
# surfaced, not silently dropped.
# --------------------------------------------------------------------------- #


def test_start_not_recorded_alert_only_fires_behind_a_genuinely_missed_predecessor():
    # Predecessor itself never started (nothing recorded at all) -- no alert;
    # correctly indistinguishable from "too early to say anything yet".
    untouched = dl.CaseFacts(case_id="c-f4-1", review_track="subdivision")
    rows = {d.clock_key: d for d in dl.compute_deadlines(untouched, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    assert rows["administrative_appeal"].status == dl.ClockStatus.PENDING_START.value
    assert rows["administrative_appeal"].start_not_recorded_alert is None


def test_start_not_recorded_alert_fires_and_is_visible_in_open_deadlines():
    case = dl.CaseFacts(
        case_id="c-f4-2", review_track="subdivision",
        submitted_at=date(2025, 1, 1), decision_at=date(2025, 6, 1),
        # decision_filed_at deliberately never recorded -- decision_filed_with_clerk
        # (due 5 business days after decision_at) is now long MISSED.
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    predecessor = rows["decision_filed_with_clerk"]
    assert predecessor.status == dl.ClockStatus.MISSED.value

    successor = rows["administrative_appeal"]
    assert successor.status == dl.ClockStatus.PENDING_START.value  # never invents a start date
    assert successor.start_not_recorded_alert is not None

    # open_deadlines() must not drop it -- the whole point of F4.
    dashboard_rows = dl.open_deadlines([case], as_of=date(2026, 1, 1))
    by_key = {d.clock_key: d for d in dashboard_rows}
    assert "administrative_appeal" in by_key
    assert by_key["administrative_appeal"].start_not_recorded_alert is not None
    # And it must rank ahead of an ordinary OPEN clock (but behind any real
    # MISSED clock) in dashboard severity order.
    keys_in_order = [d.clock_key for d in dashboard_rows]
    assert keys_in_order.index("decision_filed_with_clerk") < keys_in_order.index("administrative_appeal")


# --------------------------------------------------------------------------- #
# F1 reconciliation gate -- presents_auto_approval_risk(). The adversarial
# review's ORIGINAL F1 repro ("subdivision received 2025-10-02, nothing
# since, as-of 2026-08-21 -> auto_approval_risk=False") was fixed at the
# engine level by F4 (start_not_recorded_alert now fires), but the F4 fix
# alone left a SECOND, narrower instance of the exact same bug: the boolean
# app/main.py:_has_auto_approval_alert() checked only `auto_approval_alert`,
# so the dashboard/case-detail "auto-approval risk" banner still never fired
# for a clock stuck at PENDING_START behind a missed predecessor, even one
# carrying `failure_consequence` (an actual §8.d.1 clock). These tests pin
# the fix at the engine helper both F1 and F4's machinery now share.
# --------------------------------------------------------------------------- #


def test_f1_repro_stalled_subdivision_presents_auto_approval_risk():
    """The task brief's exact F1 repro: subdivision received 2025-10-02,
    nothing recorded since, as-of 2026-08-21. subdivision_hearing_decision
    (the §8.d.1-bearing clock, start_event=completeness_at) never leaves
    PENDING_START because completeness was never determined -- but its
    predecessor duty (subdivision_completeness, due 2025-11-01) is itself
    long MISSED, so this must present as an auto-approval risk."""
    case = dl.CaseFacts(
        case_id="c-f1-repro", review_track="subdivision",
        submitted_at=date(2025, 10, 2), submitted_at_source="received_at",
    )
    rows = dl.compute_deadlines(case, as_of=date(2026, 8, 21))
    by_key = {d.clock_key: d for d in rows}

    hearing_decision = by_key["subdivision_hearing_decision"]
    assert hearing_decision.status == dl.ClockStatus.PENDING_START.value
    assert hearing_decision.failure_consequence is not None  # it IS a §8.d.1 clock
    assert hearing_decision.auto_approval_alert is None  # no due_date to compare -- the old, still-true gap
    assert hearing_decision.start_not_recorded_alert is not None  # F4's visibility fix
    assert "§8.d.1" in hearing_decision.start_not_recorded_alert  # the enriched F1 message

    # The actual gate: the case-wide boolean must be True.
    assert dl.presents_auto_approval_risk(hearing_decision) is True
    assert any(dl.presents_auto_approval_risk(d) for d in rows) is True

    # Identical input on the other v1 review types was NEVER broken (the
    # finding's own repro contrast) -- confirm it still isn't.
    for track in ("special_permit", "variance", "large_project_plan"):
        other = dl.CaseFacts(
            case_id=f"c-f1-control-{track}", review_track=track,
            submitted_at=date(2025, 10, 2), submitted_at_source="received_at",
        )
        other_rows = dl.compute_deadlines(other, as_of=date(2026, 8, 21))
        assert any(dl.presents_auto_approval_risk(d) for d in other_rows) is True


def test_presents_auto_approval_risk_does_not_over_trigger_on_a_non_consequence_predecessor():
    """A start_not_recorded_alert on a clock with NO failure_consequence of
    its own (e.g. administrative_appeal, whose §23.d.1 text has no §8.d.1
    hearing/decision duty) must NOT count as auto-approval risk -- only the
    clock's own failure_consequence matters, never the predecessor's."""
    case = dl.CaseFacts(
        case_id="c-f1-negative", review_track="subdivision",
        submitted_at=date(2025, 1, 1), decision_at=date(2025, 6, 1),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 1), include_meeting_clocks=False)}
    appeal = rows["administrative_appeal"]
    assert appeal.start_not_recorded_alert is not None
    assert appeal.failure_consequence is None
    assert dl.presents_auto_approval_risk(appeal) is False


def test_app_dashboard_and_case_detail_flag_f1_repro_as_auto_approval_risk(tmp_path, monkeypatch):
    """End-to-end through app/main.py's own boolean, not just the engine
    helper -- this is the function the templates actually key off."""
    import app.main as main_mod

    case = dl.CaseFacts(
        case_id="c-f1-app", review_track="subdivision",
        submitted_at=date(2025, 10, 2), submitted_at_source="received_at",
    )
    rows = dl.compute_deadlines(case, as_of=date(2026, 8, 21))
    assert main_mod._has_auto_approval_alert(rows) is True


# --------------------------------------------------------------------------- #
# 2026-08 clock taxonomy -- behavioral proofs. N1 and the reconsideration
# half of N2 were both "a private party's window silently modeled as a Town
# duty with a deadline". These tests exercise the fix end to end: a
# party_right window that elapses unexercised is ELAPSED, never MISSED,
# never an alert, never auto-approval risk; a conditional_duty clock is
# NOT_TRIGGERED until its predicate is actually recorded, then behaves like
# any other duty from that point forward.
# --------------------------------------------------------------------------- #


def test_party_right_elapses_instead_of_missing_when_the_window_closes_unused():
    """N1's exact repro, isolated: a decided, unappealed case, well past the
    30-day administrative_appeal window. Before the fix this reported
    MISSED; it must now report ELAPSED, carry no alert, and never present as
    auto-approval risk."""
    case = dl.CaseFacts(
        case_id="c-party-right-1", review_track="small_project_plan",
        submitted_at=date(2026, 1, 1), decision_at=date(2026, 1, 5),
        decision_filed_at=date(2026, 1, 8),  # so administrative_appeal has a real start_date
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 6, 1), include_meeting_clocks=False)}
    appeal = rows["administrative_appeal"]

    assert appeal.duty_kind == "party_right"
    assert appeal.status == dl.ClockStatus.ELAPSED.value
    assert appeal.status != dl.ClockStatus.MISSED.value
    assert appeal.auto_approval_alert is None
    assert dl.presents_auto_approval_risk(appeal) is False

    # And it can no longer serve as a MISSED predecessor for anything
    # downstream (the other half of the same fix -- see
    # _attach_start_not_recorded_alerts's TAXONOMY GATE).
    hearing = rows["administrative_appeal_hearing"]
    assert hearing.status == dl.ClockStatus.NOT_TRIGGERED.value
    assert hearing.start_not_recorded_alert is None
    assert dl.presents_auto_approval_risk(hearing) is False


def test_party_right_reports_open_while_the_window_is_still_running():
    case = dl.CaseFacts(
        case_id="c-party-right-2", review_track="small_project_plan",
        submitted_at=date(2026, 1, 1), decision_at=date(2026, 1, 5),
        decision_filed_at=date(2026, 1, 8),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 15), include_meeting_clocks=False)}
    appeal = rows["administrative_appeal"]
    assert appeal.status == dl.ClockStatus.OPEN.value


def test_party_right_reports_met_when_actually_exercised():
    case = dl.CaseFacts(
        case_id="c-party-right-3", review_track="small_project_plan",
        submitted_at=date(2026, 1, 1), decision_at=date(2026, 1, 5),
        decision_filed_at=date(2026, 1, 8), appeal_filed_at=date(2026, 1, 20),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 6, 1), include_meeting_clocks=False)}
    appeal = rows["administrative_appeal"]
    assert appeal.status == dl.ClockStatus.MET.value


def test_conditional_duty_not_triggered_until_the_predicate_is_recorded():
    """The reconsideration half of N2's repro, isolated: a variance decided
    long ago, no reconsideration ever requested. reconsideration_decision
    must NOT go MISSED 45 days after the decision -- it must be
    NOT_TRIGGERED, forever, until a reconsideration is actually requested."""
    case = dl.CaseFacts(
        case_id="c-cond-1", review_track="variance",
        submitted_at=date(2026, 1, 1), decision_at=date(2026, 1, 5),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2027, 1, 1), include_meeting_clocks=False)}
    recon_decision = rows["reconsideration_decision"]

    assert recon_decision.duty_kind == "conditional_duty"
    assert recon_decision.status == dl.ClockStatus.NOT_TRIGGERED.value
    assert recon_decision.status != dl.ClockStatus.MISSED.value
    assert recon_decision.auto_approval_alert is None
    assert dl.presents_auto_approval_risk(recon_decision) is False

    # It never reaches the dashboard's at-risk view while untriggered.
    dashboard = dl.open_deadlines([case], as_of=date(2027, 1, 1))
    assert not any(d.clock_key == "reconsideration_decision" for d in dashboard)


def test_conditional_duty_still_not_triggered_by_a_bare_request_no_vote():
    """HARD-FINAL round, Finding 6. reconsideration_decision's predicate is
    the §23.e.2/.e.3 VOTE TO RECONSIDER, not the bare §23.e.1 REQUEST --
    §23.e.4's own text ("If the Board of Appeals reconsiders...") is not
    satisfied by an applicant merely asking. A request with no recorded vote
    must stay NOT_TRIGGERED, same as no request at all -- this is the
    over-triggering N2 left in place (a request alone used to flip this
    clock live) that F6 closes."""
    requested_no_vote = dl.CaseFacts(
        case_id="c-cond-2b", review_track="variance",
        submitted_at=date(2026, 1, 1), decision_at=date(2026, 1, 5),
        reconsideration_requested_at=date(2026, 1, 10),
    )
    rows = {
        d.clock_key: d
        for d in dl.compute_deadlines(requested_no_vote, as_of=date(2026, 6, 1), include_meeting_clocks=False)
    }
    recon_decision = rows["reconsideration_decision"]
    assert recon_decision.status == dl.ClockStatus.NOT_TRIGGERED.value
    assert recon_decision.status != dl.ClockStatus.MISSED.value
    assert dl.presents_auto_approval_risk(recon_decision) is False


def test_conditional_duty_triggers_once_the_predicate_is_recorded():
    """Once the Board actually VOTES to reconsider (§23.e.2/.e.3),
    reconsideration_decision behaves like an ordinary duty from that point
    forward -- PENDING_START is not possible here (start_event is
    decision_at, already recorded), so it goes straight to normal
    OPEN/MET/MISSED branching keyed off the ORIGINAL decision date (its own
    text: 'within 45 days of the original decision', not of the
    reconsideration vote or request)."""
    triggered_late = dl.CaseFacts(
        case_id="c-cond-2", review_track="variance",
        submitted_at=date(2026, 1, 1), decision_at=date(2026, 1, 5),
        reconsideration_requested_at=date(2026, 1, 10),
        reconsideration_voted_at=date(2026, 1, 15),
    )
    rows = {
        d.clock_key: d
        for d in dl.compute_deadlines(triggered_late, as_of=date(2026, 6, 1), include_meeting_clocks=False)
    }
    recon_decision = rows["reconsideration_decision"]
    assert recon_decision.status == dl.ClockStatus.MISSED.value  # 45 days from decision_at passed, never decided
    assert recon_decision.due_date == date(2026, 2, 19)
    # Still never auto-approval risk -- this clock was built WITHOUT
    # failure_consequence (never characterized as a §8.d.1-bearing duty).
    assert recon_decision.failure_consequence is None
    assert dl.presents_auto_approval_risk(recon_decision) is False


def test_conditional_duty_met_when_reconsidered_and_decided_on_time():
    on_time = dl.CaseFacts(
        case_id="c-cond-3", review_track="variance",
        submitted_at=date(2026, 1, 1), decision_at=date(2026, 1, 5),
        reconsideration_requested_at=date(2026, 1, 10),
        reconsideration_voted_at=date(2026, 1, 15),
        reconsideration_decided_at=date(2026, 2, 1),
    )
    rows = {
        d.clock_key: d
        for d in dl.compute_deadlines(on_time, as_of=date(2026, 6, 1), include_meeting_clocks=False)
    }
    assert rows["reconsideration_decision"].status == dl.ClockStatus.MET.value


def test_administrative_appeal_hearing_conditional_duty_triggers_on_appeal_filed():
    case = dl.CaseFacts(
        case_id="c-cond-4", review_track="small_project_plan",
        submitted_at=date(2026, 1, 1), decision_at=date(2026, 1, 5),
        decision_filed_at=date(2026, 1, 8), appeal_filed_at=date(2026, 1, 20),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 1, 22), include_meeting_clocks=False)}
    hearing = rows["administrative_appeal_hearing"]
    assert hearing.duty_kind == "conditional_duty"
    assert hearing.status == dl.ClockStatus.OPEN.value  # triggered, started, still within its 30 days
    assert hearing.start_date == date(2026, 1, 20)


# --------------------------------------------------------------------------- #
# THE PROOF THAT MATTERS. A complete, perfectly on-time case with every
# milestone recorded -- decided, decision filed on time, and the appeal (and,
# for variance, reconsideration) window elapsed WITHOUT anyone exercising it
# -- must show auto_approval_risk = FALSE on ALL FIVE v1 review types. Before
# the taxonomy fix, every one of these was a FALSE POSITIVE (N1): the
# unexercised administrative_appeal window went MISSED, which cascaded into
# administrative_appeal_hearing's start_not_recorded_alert, which
# presents_auto_approval_risk() then read as risk -- on every single clean
# case, which is exactly why N1 shipped green (the suite had no clean-case
# test at all).
# --------------------------------------------------------------------------- #


def _complete_on_time_case(track: str) -> dl.CaseFacts:
    submitted = date(2026, 1, 5)
    kwargs: dict[str, Any] = dict(
        case_id=f"c-clean-{track}", review_track=track,
        submitted_at=submitted, notice_mailed_at=dl.add_business_days(submitted, 3),
    )

    if track == "small_project_plan":
        kwargs["decision_at"] = dl.add_calendar_days(submitted, 8)
    elif track == "large_project_plan":
        kwargs["decision_at"] = dl.add_calendar_days(submitted, 40)
        kwargs["plat_recorded_at"] = dl.add_calendar_days(kwargs["decision_at"], 5)
    elif track == "subdivision":
        kwargs["completeness_at"] = dl.add_calendar_days(submitted, 20)
        kwargs["decision_at"] = dl.add_calendar_days(kwargs["completeness_at"], 20)
        kwargs["findings_issued_at"] = dl.add_calendar_days(kwargs["decision_at"], 10)
        kwargs["plat_recorded_at"] = dl.add_calendar_days(kwargs["decision_at"], 5)
    elif track == "special_permit":
        kwargs["hearing_opened_at"] = dl.add_calendar_days(submitted, 20)
        kwargs["hearing_closed_at"] = kwargs["hearing_opened_at"]
        kwargs["decision_at"] = dl.add_calendar_days(kwargs["hearing_closed_at"], 30)
    elif track == "variance":
        kwargs["hearing_opened_at"] = dl.add_calendar_days(submitted, 20)
        kwargs["hearing_closed_at"] = kwargs["hearing_opened_at"]
        kwargs["decision_at"] = dl.add_calendar_days(kwargs["hearing_closed_at"], 30)
        kwargs["certificate_recorded_at"] = dl.add_calendar_days(kwargs["decision_at"], 30)
        # reconsideration deliberately NEVER requested -- the party_right window elapses.
    else:
        raise AssertionError(track)

    kwargs["decision_filed_at"] = dl.add_business_days(kwargs["decision_at"], 3)
    # appeal_filed_at deliberately NEVER recorded -- the party_right window elapses.
    return dl.CaseFacts(**kwargs)


@pytest.mark.parametrize(
    "track", ["small_project_plan", "large_project_plan", "subdivision", "special_permit", "variance"]
)
def test_clean_on_time_unappealed_case_never_presents_auto_approval_risk(track):
    case = _complete_on_time_case(track)
    # Far enough past decision_filed_at that BOTH the 30-day administrative_
    # appeal window and (for variance) the 10-day reconsideration window have
    # elapsed unexercised -- MET clocks are unaffected by how far as_of runs
    # (satisfied_at <= due_date is independent of as_of), so this is safe.
    as_of = dl.add_calendar_days(case.decision_at, 400)
    rows = dl.compute_deadlines(case, as_of=as_of)
    by_key = {d.clock_key: d for d in rows}

    assert not any(dl.presents_auto_approval_risk(d) for d in rows), [
        (d.clock_key, d.status, d.auto_approval_alert, d.start_not_recorded_alert) for d in rows
        if dl.presents_auto_approval_risk(d)
    ]

    # The party_right window(s) genuinely elapsed, not silently PENDING_START.
    assert by_key["administrative_appeal"].status == dl.ClockStatus.ELAPSED.value
    if track == "variance":
        assert by_key["reconsideration"].status == dl.ClockStatus.ELAPSED.value
        assert by_key["reconsideration_decision"].status == dl.ClockStatus.NOT_TRIGGERED.value

    # The conditional_duty appeal clocks never triggered (no appeal filed).
    assert by_key["administrative_appeal_hearing"].status == dl.ClockStatus.NOT_TRIGGERED.value
    assert by_key["administrative_appeal_decision"].status == dl.ClockStatus.NOT_TRIGGERED.value

    # Every clock that DOES apply to this track and IS a real duty was
    # actually satisfied -- this is a genuinely clean case, not one that
    # merely has no applicable clocks. Exception: on the large_project_plan
    # CEO track (no forwarded_to_pb_at), the Planning-Board-track clocks are
    # still enumerated (applies_to is unconditional) but honestly
    # PENDING_START forever, same as test_large_project_ceo_track_clock_
    # disappears_once_forwarded_to_pb documents -- a real "this branch was
    # never taken" fact, not a taxonomy defect this test is checking for.
    never_started_on_this_branch = {"large_project_pb_completeness_hearing", "large_project_pb_decision"}
    duty_clocks = [
        d for d in rows
        if d.duty_kind in ("municipal_duty", "applicant_duty")
        and d.clock_key not in ("meeting", "draft_due")
        and d.clock_key not in never_started_on_this_branch
    ]
    assert duty_clocks  # the parametrization actually exercises real duties
    assert all(d.status == dl.ClockStatus.MET.value for d in duty_clocks), [
        (d.clock_key, d.status) for d in duty_clocks if d.status != dl.ClockStatus.MET.value
    ]
    if track == "large_project_plan":
        for key in never_started_on_this_branch:
            assert by_key[key].status == dl.ClockStatus.PENDING_START.value


def test_f1_repro_still_true_alongside_the_clean_case_fix():
    """BOTH directions, per the task brief: the taxonomy fix must not
    dampen a REAL stalled-duty signal while it suppresses the false one.
    Re-proves test_f1_repro_stalled_subdivision_presents_auto_approval_risk's
    exact scenario still reports True after the taxonomy rework."""
    case = dl.CaseFacts(
        case_id="c-f1-repro-taxonomy", review_track="subdivision",
        submitted_at=date(2025, 10, 2), submitted_at_source="received_at",
    )
    rows = dl.compute_deadlines(case, as_of=date(2026, 8, 21))
    assert any(dl.presents_auto_approval_risk(d) for d in rows) is True


# --------------------------------------------------------------------------- #
# F11 -- a CLOSED case's post-decision statutory duties (plat recording, the
# appeal window) stay visible to load_all_case_facts()/open_deadlines();
# only 'withdrawn' (which, per app/cases.py:ALLOWED_TRANSITIONS, can only be
# reached BEFORE a decision -- there is no decided/closed -> withdrawn path)
# is excluded entirely.
# --------------------------------------------------------------------------- #


def test_closed_case_still_surfaces_its_open_recording_and_appeal_clocks(shattuck_conn):
    conn, case_id = shattuck_conn
    conn.execute("UPDATE cases SET status = 'closed' WHERE id = ?", (case_id,))

    rows = dl.open_deadlines(conn=conn, as_of=date(2026, 1, 1))
    by_key = {(d.case_id, d.clock_key): d for d in rows}
    # The subdivision plat-recording clocks (started by decision_at, which
    # IS recorded in this fixture) are still open obligations after closure.
    assert (case_id, "subdivision_plat_recorded_6mo") in by_key
    assert (case_id, "subdivision_plat_recorded_90d") in by_key


def test_withdrawn_case_is_excluded_from_load_all_case_facts(shattuck_conn):
    conn, case_id = shattuck_conn
    conn.execute("UPDATE cases SET status = 'withdrawn' WHERE id = ?", (case_id,))
    facts = dl.load_all_case_facts(conn)
    assert case_id not in {c.case_id for c in facts}


# --------------------------------------------------------------------------- #
# F1 WIDENING (2026-08 round 2 adversarial review) -- a TRIGGERED
# conditional_duty clock is a LIVE municipal duty for §8.d.1 auto-approval
# purposes; only an UNTRIGGERED one (status NOT_TRIGGERED) is exempt. Before
# this fix presents_auto_approval_risk() excluded every conditional_duty
# clock unconditionally, so a Board that let an appeal hearing or appeal
# decision go MISSED after the appeal was actually filed showed
# auto_approval_risk=False -- the exact opposite of what CONTRACT.md's
# framing rule requires from the view whose job is to make this unmissable.
# ATTACK A/B/C are the adversarial review's own repros.
# --------------------------------------------------------------------------- #


def test_attack_a_triggered_appeal_hearing_missed_now_presents_risk():
    """ATTACK A: variance decided and filed on time, appeal filed
    2026-02-20, the Board never held the §23.d.2 hearing, as-of 2026-08-21.
    Before the fix: status=missed, failure_consequence set,
    auto_approval_alert TEXT PRESENT, but presents_auto_approval_risk()
    False. After: True."""
    case = dl.CaseFacts(
        case_id="c-attack-a", review_track="variance",
        submitted_at=date(2025, 10, 1),
        hearing_opened_at=date(2025, 10, 25), hearing_closed_at=date(2025, 10, 25),
        decision_at=date(2025, 11, 24), decision_filed_at=date(2025, 11, 26),
        appeal_filed_at=date(2026, 2, 20),
        # appeal_hearing_opened_at deliberately never recorded -- the hearing
        # was never held.
    )
    as_of = date(2026, 8, 21)
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=as_of, include_meeting_clocks=False)}
    hearing = rows["administrative_appeal_hearing"]

    # BEFORE / the unchanged facts the finding pins:
    assert hearing.duty_kind == "conditional_duty"
    assert hearing.status == dl.ClockStatus.MISSED.value
    assert hearing.status != dl.ClockStatus.NOT_TRIGGERED.value  # it WAS triggered
    assert hearing.failure_consequence is not None
    assert hearing.auto_approval_alert is not None
    assert "§8.d.1" in hearing.auto_approval_alert

    # AFTER / the fix:
    assert dl.presents_auto_approval_risk(hearing) is True
    assert any(dl.presents_auto_approval_risk(d) for d in rows.values()) is True


def test_attack_b_triggered_appeal_decision_missed_now_presents_risk():
    """ATTACK B: the same defect on administrative_appeal_decision -- the
    appeal hearing WAS held and closed on time, but the Appellate Authority
    never issued its §23.d.3 decision within 45 days of the closing."""
    case = dl.CaseFacts(
        case_id="c-attack-b", review_track="special_permit",
        submitted_at=date(2025, 6, 1),
        hearing_opened_at=date(2025, 6, 20), hearing_closed_at=date(2025, 6, 20),
        decision_at=date(2025, 8, 4), decision_filed_at=date(2025, 8, 6),
        appeal_filed_at=date(2025, 9, 1),
        appeal_hearing_opened_at=date(2025, 9, 20), appeal_hearing_closed_at=date(2025, 9, 20),
        # appeal_decision_at deliberately never recorded.
    )
    as_of = date(2026, 8, 21)
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=as_of, include_meeting_clocks=False)}
    decision = rows["administrative_appeal_decision"]

    assert decision.duty_kind == "conditional_duty"
    assert decision.status == dl.ClockStatus.MISSED.value
    assert decision.status != dl.ClockStatus.NOT_TRIGGERED.value
    assert decision.failure_consequence is not None
    assert decision.auto_approval_alert is not None

    assert dl.presents_auto_approval_risk(decision) is True
    assert any(dl.presents_auto_approval_risk(d) for d in rows.values()) is True


def test_attack_c_triggered_appeal_hearing_missed_on_the_appeal_track_itself():
    """ATTACK C: the identical defect reproduces on a case whose own
    review_track IS 'administrative_appeal' (not merely an appeal recorded
    against some other track's case) -- confirms the fix is not accidentally
    scoped to a single review_track."""
    case = dl.CaseFacts(
        case_id="c-attack-c", review_track="administrative_appeal",
        submitted_at=date(2025, 10, 1),
        decision_at=date(2025, 10, 15), decision_filed_at=date(2025, 10, 17),
        appeal_filed_at=date(2026, 2, 20),
    )
    as_of = date(2026, 8, 21)
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=as_of, include_meeting_clocks=False)}
    hearing = rows["administrative_appeal_hearing"]

    assert hearing.status == dl.ClockStatus.MISSED.value
    assert dl.presents_auto_approval_risk(hearing) is True
    assert any(dl.presents_auto_approval_risk(d) for d in rows.values()) is True


def test_triggered_appeal_hearing_and_decision_on_time_still_no_risk():
    """The other direction, per the task brief: TRIGGERING a conditional
    duty must not, by itself, manufacture risk. An appeal that was actually
    heard and decided within its own statutory windows must still present
    False -- the widening only reaches a triggered duty that is genuinely
    overdue, not every triggered one."""
    case = dl.CaseFacts(
        case_id="c-attack-control", review_track="variance",
        submitted_at=date(2025, 10, 1),
        hearing_opened_at=date(2025, 10, 25), hearing_closed_at=date(2025, 10, 25),
        decision_at=date(2025, 11, 24), decision_filed_at=date(2025, 11, 26),
        appeal_filed_at=date(2025, 12, 10),
        appeal_hearing_opened_at=date(2025, 12, 30), appeal_hearing_closed_at=date(2025, 12, 30),
        appeal_decision_at=date(2026, 1, 20),
    )
    as_of = date(2026, 8, 21)
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=as_of, include_meeting_clocks=False)}
    hearing = rows["administrative_appeal_hearing"]
    decision = rows["administrative_appeal_decision"]

    assert hearing.status == dl.ClockStatus.MET.value
    assert decision.status == dl.ClockStatus.MET.value
    assert dl.presents_auto_approval_risk(hearing) is False
    assert dl.presents_auto_approval_risk(decision) is False
    assert not any(dl.presents_auto_approval_risk(d) for d in rows.values())


def test_untriggered_conditional_duty_still_never_presents_risk_after_the_widening():
    """Guards the OTHER edge of the F1 widening: a conditional_duty clock
    that has NOT triggered (status stays NOT_TRIGGERED) must still be
    excluded -- the widening only admits a TRIGGERED conditional_duty, never
    an untriggered one. Re-proves the N2/taxonomy-gate tests still hold."""
    case = dl.CaseFacts(
        case_id="c-untriggered", review_track="variance",
        submitted_at=date(2026, 1, 1), decision_at=date(2026, 1, 5),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2027, 1, 1), include_meeting_clocks=False)}
    recon = rows["reconsideration_decision"]
    hearing = rows["administrative_appeal_hearing"]
    assert recon.status == dl.ClockStatus.NOT_TRIGGERED.value
    assert hearing.status == dl.ClockStatus.NOT_TRIGGERED.value
    assert dl.presents_auto_approval_risk(recon) is False
    assert dl.presents_auto_approval_risk(hearing) is False


# --------------------------------------------------------------------------- #
# F2 SECOND ARM -- a §8.d.1-bearing clock stuck at PENDING_START behind a
# hearing that opened but was never closed (no clocks.json predecessor
# exists for these four clocks -- see the block comment above
# _attach_start_not_recorded_alerts()) must eventually surface a
# start_not_recorded_alert once it has gone stale long enough, instead of
# staying silent forever. ATTACK F is the adversarial review's own repro.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "track,decision_clock_key,extra_kwargs",
    [
        ("special_permit", "special_permit_decision", {}),
        ("variance", "variance_decision", {}),
        ("large_project_plan", "large_project_pb_decision", {"forwarded_to_pb_at": date(2025, 1, 10)}),
    ],
)
def test_attack_f_hearing_opened_never_closed_eventually_raises_risk(track, decision_clock_key, extra_kwargs):
    """ATTACK F: hearing opened on time 2025-02-03 (or, for large_project_
    plan, forwarded to the Board 2025-01-10 and heard 2025-02-03), never
    closed, evaluated 18 months later. Before the fix: the decision clock
    sits at PENDING_START with due=None and NO alert of any kind --
    presents_auto_approval_risk() False. After: a start_not_recorded_alert
    fires and the clock (a plain municipal_duty clock throughout) presents
    risk."""
    kwargs: dict[str, Any] = dict(
        case_id=f"c-attack-f-{track}", review_track=track,
        submitted_at=date(2025, 1, 1), hearing_opened_at=date(2025, 2, 3),
        # hearing_closed_at deliberately never recorded.
    )
    kwargs.update(extra_kwargs)
    case = dl.CaseFacts(**kwargs)
    as_of = date(2026, 8, 21)  # ~18 months after the hearing opened
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=as_of, include_meeting_clocks=False)}
    decision = rows[decision_clock_key]

    assert decision.duty_kind == "municipal_duty"
    assert decision.status == dl.ClockStatus.PENDING_START.value  # never invents a start date
    assert decision.due_date is None
    assert decision.auto_approval_alert is None  # no due_date to compare -- still true
    assert decision.failure_consequence is not None

    # THE FIX:
    assert decision.start_not_recorded_alert is not None
    assert "hearing" in decision.start_not_recorded_alert.lower()
    assert "§8.d.1" in decision.start_not_recorded_alert
    assert dl.presents_auto_approval_risk(decision) is True
    assert any(dl.presents_auto_approval_risk(d) for d in rows.values()) is True

    # open_deadlines() must not drop it -- the whole point of the F4 channel
    # this arm reuses.
    dashboard_rows = dl.open_deadlines([case], as_of=as_of)
    assert any(d.clock_key == decision_clock_key for d in dashboard_rows)


def test_attack_f_app_dashboard_flags_the_stalled_hearing_as_risk(tmp_path, monkeypatch):
    """End to end through app/main.py's own boolean, not just the engine
    helper."""
    import app.main as main_mod

    case = dl.CaseFacts(
        case_id="c-attack-f-app", review_track="special_permit",
        submitted_at=date(2025, 1, 1), hearing_opened_at=date(2025, 2, 3),
    )
    rows = dl.compute_deadlines(case, as_of=date(2026, 8, 21))
    assert main_mod._has_auto_approval_alert(rows) is True


def test_stalled_hearing_second_arm_silent_before_the_staleness_threshold():
    """The other direction for F2: a hearing that has been open only a
    short while (well under STALE_HEARING_WARNING_DAYS) is an ordinary,
    Code-contemplated §6.e.1 continuance-in-progress, not a stall -- no
    alert, no risk. Never invents a MISSED status or a due_date either."""
    case = dl.CaseFacts(
        case_id="c-not-yet-stale", review_track="special_permit",
        submitted_at=date(2026, 1, 1), hearing_opened_at=date(2026, 1, 20),
        # hearing_closed_at never recorded, but only ~60 days have passed.
    )
    as_of = date(2026, 3, 21)
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=as_of, include_meeting_clocks=False)}
    decision = rows["special_permit_decision"]

    assert decision.status == dl.ClockStatus.PENDING_START.value
    assert decision.due_date is None
    assert decision.auto_approval_alert is None
    assert decision.start_not_recorded_alert is None
    assert dl.presents_auto_approval_risk(decision) is False


def test_stalled_hearing_second_arm_silent_once_the_hearing_actually_closes():
    """Once hearing_closed_at IS recorded, the clock leaves PENDING_START
    entirely (start_date is now known) -- the second arm only ever applies
    to a still-PENDING_START clock, so a closed-but-not-yet-decided hearing
    gets ordinary OPEN/MISSED branching instead of a stall alert, no matter
    how long ago it opened."""
    case = dl.CaseFacts(
        case_id="c-closed-normally", review_track="special_permit",
        submitted_at=date(2025, 1, 1), hearing_opened_at=date(2025, 2, 3),
        hearing_closed_at=date(2026, 8, 1),  # closed just recently, after a long continuance
    )
    as_of = date(2026, 8, 21)
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=as_of, include_meeting_clocks=False)}
    decision = rows["special_permit_decision"]

    assert decision.status == dl.ClockStatus.OPEN.value
    assert decision.start_date == date(2026, 8, 1)
    assert decision.start_not_recorded_alert is None
    assert dl.presents_auto_approval_risk(decision) is False


def test_clean_on_time_hearing_and_decision_no_stall_alert():
    """A hearing opened AND closed the same day, decision made on time --
    the ordinary happy path used throughout this suite's clean-case tests --
    must never trip the second arm."""
    case = _complete_on_time_case("special_permit")
    as_of = dl.add_calendar_days(case.decision_at, 400)
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=as_of, include_meeting_clocks=False)}
    decision = rows["special_permit_decision"]
    assert decision.status == dl.ClockStatus.MET.value
    assert decision.start_not_recorded_alert is None
    assert dl.presents_auto_approval_risk(decision) is False
