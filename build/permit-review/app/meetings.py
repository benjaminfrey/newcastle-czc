"""Deterministic Newcastle Planning Board meeting schedule.

The Planning Board meets the 3rd Thursday of every month at 6:30pm; a draft
must be in the packet 7 days before the meeting. Both dates are *computed*,
never typed by a user and never produced by a model — the same rule
CONTRACT.md §3.4 states for app/dates.py's meeting_date()/draft_due()/
next_meeting() trio.

NAMING NOTE FOR WHOEVER RECONCILES THIS LATER: this project's CONTRACT.md §2
names the canonical home for this logic `app/dates.py`, with signatures
`meeting_date(year, month) -> date`, `draft_due(meeting: date) -> date`, and
`next_meeting(on: date) -> date`. The task brief that commissioned this render
pipeline instead asked for `app/meetings.py` with `next_meeting_date(from_date)`
and `draft_due_date(meeting_date)`. Both were live asks; rather than silently
pick a winner, this module implements the single 3rd-Thursday/-7-days rule
once and exposes it under BOTH naming conventions, so it is a no-op to delete
whichever module turns out not to be the one downstream code settles on. If
`app/dates.py` already exists (or comes to exist) with its own copy of this
same arithmetic, that is a duplication worth collapsing — the two must never
be allowed to drift, since a wrong meeting date is a wrong legal deadline.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

# --------------------------------------------------------------------------- #
# The rule
# --------------------------------------------------------------------------- #

MEETING_WEEKDAY: int = 3  # Thursday; Python's date.weekday() is Monday=0
MEETING_TIME: time = time(18, 30)  # 6:30pm
DRAFT_DUE_LEAD_DAYS: int = 7


def _third_thursday(year: int, month: int) -> date:
    first_of_month = date(year, month, 1)
    days_to_first_thursday = (MEETING_WEEKDAY - first_of_month.weekday()) % 7
    first_thursday = first_of_month + timedelta(days=days_to_first_thursday)
    return first_thursday + timedelta(days=14)


# --------------------------------------------------------------------------- #
# CONTRACT.md §3.4 naming (meeting_date / draft_due / next_meeting)
# --------------------------------------------------------------------------- #


def meeting_date(year: int, month: int) -> date:
    """The 3rd Thursday of the given year/month — the Planning Board's
    regular meeting date (CONTRACT.md §3.4)."""
    return _third_thursday(year, month)


def draft_due(meeting: date) -> date:
    """The packet deadline: `meeting` minus 7 days (CONTRACT.md §3.4)."""
    return meeting - timedelta(days=DRAFT_DUE_LEAD_DAYS)


def next_meeting(on: date | None = None) -> date:
    """The next regular meeting date on or after `on` (default: today).

    If `on` itself is the 3rd Thursday of its month, `on` is returned (a case
    that matters for draft-due-date math run on meeting day itself).
    """
    reference = on if on is not None else date.today()
    candidate = _third_thursday(reference.year, reference.month)
    if candidate >= reference:
        return candidate
    year, month = reference.year, reference.month + 1
    if month > 12:
        year, month = year + 1, 1
    return _third_thursday(year, month)


# --------------------------------------------------------------------------- #
# Task-brief naming (next_meeting_date / draft_due_date)
# --------------------------------------------------------------------------- #


def next_meeting_date(from_date: date | datetime | None = None) -> datetime:
    """The next 3rd-Thursday meeting on/after `from_date`, as a datetime at
    18:30 (6:30pm) — the render-pipeline task brief's entry point. Thin
    wrapper over next_meeting(); see that function for the "on or after"
    boundary rule.
    """
    reference = from_date.date() if isinstance(from_date, datetime) else from_date
    return datetime.combine(next_meeting(reference), MEETING_TIME)


def draft_due_date(meeting: date | datetime) -> date:
    """The packet deadline for `meeting`: 7 days before it. Accepts either a
    date or a datetime (e.g. the return value of next_meeting_date()) — the
    render-pipeline task brief's entry point, thin wrapper over draft_due().
    """
    meeting_day = meeting.date() if isinstance(meeting, datetime) else meeting
    return draft_due(meeting_day)
