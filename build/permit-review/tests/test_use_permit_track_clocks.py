"""Tests for HARD-FINAL round Finding 5 -- `use`/`expanded_use` cases getting
their missing statutory clocks.

Before this fix, `use` and `expanded_use` (both real `cases.application_type`
values -- app/cases.py:APPLICATION_TYPES, 0003_case_lifecycle.sql) received
exactly ONE clock (`use_permit_decision`, §15.d.1) even though §15.d.1 itself
commands "...and file the decision with the Town Clerk" and §8.f.1 covers
"each type of development review" -- so `decision_filed_with_clerk` (§8.f.1)
and the §23 appeal window/hearing/decision clocks (§23.d.1/.d.2/.d.3) never
applied to a Use Permit decision at all. A Use Permit applicant had no
recordable filing duty and no appeal machinery in this app, no matter how the
Town actually handled the case.

Deliberately a SEPARATE module from tests/test_deadlines.py (which other,
concurrent fixes to this same deadline engine are actively editing) -- same
isolation posture tests/test_appeal_recordability.py documents for the N2 fix.

Offline, no network, no LLM, no PII.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from engine import deadlines as dl  # noqa: E402
from ruleset_build import build_clocks as bc  # noqa: E402

# --------------------------------------------------------------------------- #
# 1. Static data -- applies_to widened, and the new build-time gate.
# --------------------------------------------------------------------------- #


def test_use_and_expanded_use_reach_the_four_universal_duty_clocks():
    clocks = {c.clock_key: c for c in dl.load_clocks("adopted")}
    for key in (
        "decision_filed_with_clerk",
        "administrative_appeal",
        "administrative_appeal_hearing",
        "administrative_appeal_decision",
    ):
        assert "use" in clocks[key].applies_to, key
        assert "expanded_use" in clocks[key].applies_to, key


def test_use_and_expanded_use_still_excluded_from_reconsideration():
    """§23.e is, by its own text, specific to BOARD OF APPEALS decisions --
    this app has no way to know (rulesets/adopted/districts.json is BLOCKED
    on a human) whether the Board of Appeals is ever the "designated
    permitting authority" §15.d.1 names for a Use Permit, so
    reconsideration/reconsideration_decision are deliberately NOT widened.
    Guessing either way would be exactly the silent guess CONTRACT.md §1 S7
    forbids -- see ruleset_build/build_clocks.py's F5 docstring paragraph."""
    clocks = {c.clock_key: c for c in dl.load_clocks("adopted")}
    for key in ("reconsideration", "reconsideration_decision"):
        assert "use" not in clocks[key].applies_to, key
        assert "expanded_use" not in clocks[key].applies_to, key


def test_track_coverage_assertion_fails_the_build_if_a_track_goes_missing():
    """Regression proof for _assert_track_coverage() itself -- the standing
    build gate the task brief asks for ("extend build_clocks.py coverage so
    a review type missing a statutorily-commanded clock fails the build").
    Mutate a COPY of the real clock list to silently drop `use` from one
    universal-duty clock's applies_to and confirm the build gate catches it,
    naming the exact clock."""
    mutated = [dict(c) for c in bc.CLOCKS_ADOPTED]
    for c in mutated:
        if c["clock_key"] == "decision_filed_with_clerk":
            c["applies_to"] = [t for t in c["applies_to"] if t != "use"]

    try:
        bc._assert_track_coverage(mutated)
        assert False, "expected ClockBuildError for the missing 'use' track"
    except bc.ClockBuildError as e:
        assert "decision_filed_with_clerk" in str(e)
        assert "use" in str(e)

    # The REAL, unmutated list still passes.
    bc._assert_track_coverage(bc.CLOCKS_ADOPTED)


def test_use_permit_decision_itself_unchanged():
    """F3's original clock -- untouched by F5, still there, still §15.d.1,
    still applies_to exactly use/expanded_use (F5 widens the SURROUNDING
    filing/appeal machinery, not this clock's own scope)."""
    clocks = {c.clock_key: c for c in dl.load_clocks("adopted")}
    c = clocks["use_permit_decision"]
    assert set(c.applies_to) == {"use", "expanded_use"}
    assert c.section == "15" and c.subsection == "d.1"
    assert c.duty_kind == "municipal_duty"
    assert c.failure_consequence is not None


# --------------------------------------------------------------------------- #
# 2. compute_deadlines() -- a `use` track case actually computes the newly
#    widened clocks, end to end.
# --------------------------------------------------------------------------- #


def test_use_track_case_gets_decision_filed_and_appeal_clocks():
    case = dl.CaseFacts(
        case_id="c-use-1", review_track="use",
        submitted_at=date(2026, 1, 5),
        decision_at=date(2026, 1, 30),
        decision_filed_at=date(2026, 2, 3),
        appeal_filed_at=date(2026, 2, 10),
        appeal_hearing_opened_at=date(2026, 2, 25),
        appeal_hearing_closed_at=date(2026, 2, 25),
        appeal_decision_at=date(2026, 3, 15),
    )
    rows = {
        d.clock_key: d
        for d in dl.compute_deadlines(case, as_of=date(2026, 6, 1), include_meeting_clocks=False)
    }

    # F5's four newly-reachable clocks -- all present, all MET, no alarm.
    for key in (
        "use_permit_decision", "decision_filed_with_clerk",
        "administrative_appeal", "administrative_appeal_hearing",
        "administrative_appeal_decision",
    ):
        assert key in rows, f"{key} missing from a 'use' track case's clocks"
        d = rows[key]
        assert d.status == dl.ClockStatus.MET.value, f"{key}: expected MET, got {d.status}"
        assert d.auto_approval_alert is None, f"{key}: unexpected auto_approval_alert"
        assert dl.presents_auto_approval_risk(d) is False

    # reconsideration/reconsideration_decision were never widened -- a `use`
    # track case has no such clocks at all (applies_to excludes it).
    assert "reconsideration" not in rows
    assert "reconsideration_decision" not in rows

    assert any(dl.presents_auto_approval_risk(d) for d in rows.values()) is False


def test_use_track_case_missed_filing_now_presents_auto_approval_risk_path():
    """Before F5, a Use Permit decision that was never filed with the Town
    Clerk produced NO clock at all for that duty (decision_filed_with_clerk
    did not apply_to `use`) -- the failure was invisible. Now it is an
    ordinary, visible MISSED municipal_duty clock (decision_filed_with_clerk
    itself carries no failure_consequence -- see its own notes -- but it is
    no longer silently absent)."""
    case = dl.CaseFacts(
        case_id="c-use-2", review_track="use",
        submitted_at=date(2026, 1, 5),
        decision_at=date(2026, 1, 30),
        # decision_filed_at never recorded.
    )
    rows = {
        d.clock_key: d
        for d in dl.compute_deadlines(case, as_of=date(2026, 6, 1), include_meeting_clocks=False)
    }
    assert "decision_filed_with_clerk" in rows
    d = rows["decision_filed_with_clerk"]
    assert d.status == dl.ClockStatus.MISSED.value
    assert d.duty_kind == "municipal_duty"


def test_use_and_expanded_use_are_in_review_tracks():
    assert "use" in dl.REVIEW_TRACKS
    assert "expanded_use" in dl.REVIEW_TRACKS
