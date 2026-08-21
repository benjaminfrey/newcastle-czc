"""Tests for app/meetings.py — the deterministic Planning Board schedule.

Run offline: `cd build/permit-review && python3 -m pytest tests/test_meetings.py -v`
(the `-m pytest` form puts this directory's parent on sys.path so `import app`
resolves without any project being installed).
"""

from __future__ import annotations

import sys
from datetime import date, datetime, time
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import meetings  # noqa: E402


# --------------------------------------------------------------------------- #
# meeting_date() / _third_thursday() — the core rule, exercised across every
# weekday the 1st of the month can fall on, per CONTRACT.md §3.4.
# --------------------------------------------------------------------------- #


def test_meeting_date_when_first_of_month_is_a_thursday():
    # January 2026: the 1st is a Thursday. The 3rd Thursday must be the 15th
    # (1st, 8th, 15th), NOT the 22nd — an off-by-one here would silently push
    # every meeting a week late.
    assert date(2026, 1, 1).weekday() == 3  # sanity: confirms the fixture
    assert meetings.meeting_date(2026, 1) == date(2026, 1, 15)
    assert meetings.meeting_date(2026, 1).weekday() == 3


def test_meeting_date_when_first_of_month_is_a_friday():
    # May 2026: the 1st is a Friday, so the first Thursday is the 7th and the
    # 3rd Thursday is the 21st.
    assert date(2026, 5, 1).weekday() == 4  # sanity: confirms the fixture
    assert meetings.meeting_date(2026, 5) == date(2026, 5, 21)
    assert meetings.meeting_date(2026, 5).weekday() == 3


def test_meeting_date_is_always_a_thursday_across_a_full_year():
    for month in range(1, 13):
        d = meetings.meeting_date(2026, month)
        assert d.weekday() == 3, f"2026-{month:02d}: {d} is not a Thursday"
        assert d.day in range(15, 22), f"2026-{month:02d}: {d} is not the 3rd Thursday"


# --------------------------------------------------------------------------- #
# draft_due() / draft_due_date() — packet due 7 days before the meeting.
# --------------------------------------------------------------------------- #


def test_draft_due_is_seven_days_before_the_meeting():
    meeting = meetings.meeting_date(2026, 1)
    assert meetings.draft_due(meeting) == date(2026, 1, 8)


def test_draft_due_date_accepts_a_date_or_a_datetime():
    meeting_d = date(2026, 5, 21)
    meeting_dt = datetime.combine(meeting_d, time(18, 30))
    assert meetings.draft_due_date(meeting_d) == date(2026, 5, 14)
    assert meetings.draft_due_date(meeting_dt) == date(2026, 5, 14)


# --------------------------------------------------------------------------- #
# next_meeting() / next_meeting_date() — rolling forward, including the
# meeting-day-itself boundary and the December -> January year rollover.
# --------------------------------------------------------------------------- #


def test_next_meeting_before_this_months_meeting_returns_this_month():
    assert meetings.next_meeting(date(2026, 1, 1)) == date(2026, 1, 15)


def test_next_meeting_on_meeting_day_returns_the_same_day():
    assert meetings.next_meeting(date(2026, 1, 15)) == date(2026, 1, 15)


def test_next_meeting_after_this_months_meeting_rolls_to_next_month():
    assert meetings.next_meeting(date(2026, 1, 16)) == meetings.meeting_date(2026, 2)


def test_next_meeting_rolls_over_the_year_boundary():
    assert meetings.next_meeting(date(2026, 12, 20)) == meetings.meeting_date(2027, 1)


def test_next_meeting_date_returns_a_datetime_at_1830():
    result = meetings.next_meeting_date(date(2026, 1, 1))
    assert result == datetime(2026, 1, 15, 18, 30)


def test_next_meeting_date_accepts_a_datetime_input():
    result = meetings.next_meeting_date(datetime(2026, 1, 1, 9, 0))
    assert result == datetime(2026, 1, 15, 18, 30)


def test_next_meeting_date_defaults_to_today():
    # Undated call must not raise and must land on a Thursday at 18:30.
    result = meetings.next_meeting_date()
    assert result.weekday() == 3
    assert result.time() == time(18, 30)
    assert result.date() >= date.today()


# --------------------------------------------------------------------------- #
# End-to-end: the twelve 2026 meeting dates, spot-checked against a
# hand-computed calendar (guards the whole table, not just two months).
# --------------------------------------------------------------------------- #

_EXPECTED_2026_MEETINGS = {
    1: date(2026, 1, 15), 2: date(2026, 2, 19), 3: date(2026, 3, 19),
    4: date(2026, 4, 16), 5: date(2026, 5, 21), 6: date(2026, 6, 18),
    7: date(2026, 7, 16), 8: date(2026, 8, 20), 9: date(2026, 9, 17),
    10: date(2026, 10, 15), 11: date(2026, 11, 19), 12: date(2026, 12, 17),
}


def test_all_twelve_2026_meeting_dates():
    for month, expected in _EXPECTED_2026_MEETINGS.items():
        assert meetings.meeting_date(2026, month) == expected, month
