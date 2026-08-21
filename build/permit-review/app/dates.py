"""Implements CONTRACT.md §3.4 (deterministic Planning Board dates).

CONTRACT.md §2 names this module's canonical home `app/dates.py` with
signatures `meeting_date(year, month) -> date`, `draft_due(meeting) -> date`,
and `next_meeting(on) -> date`. A concurrently-built sibling task shipped the
identical 3rd-Thursday/-7-days arithmetic under `app/meetings.py` instead
(see that module's own reconciliation note). Per the integration rule ("the
CONTRACT wins"), this module is the canonical CONTRACT-named entry point --
but it does not re-implement the rule a second time (a wrong meeting date is
a wrong legal deadline, and two copies of the same arithmetic is exactly the
drift CONTRACT.md §3.4 warns against). It simply re-exports app.meetings'
already-correct implementation under the CONTRACT names.
"""

from __future__ import annotations

from datetime import date

from app.meetings import (  # noqa: F401  (re-exported, not just used locally)
    DRAFT_DUE_LEAD_DAYS,
    MEETING_TIME,
    MEETING_WEEKDAY,
    draft_due,
    meeting_date,
    next_meeting,
)

__all__ = [
    "MEETING_WEEKDAY",
    "MEETING_TIME",
    "DRAFT_DUE_LEAD_DAYS",
    "meeting_date",
    "draft_due",
    "next_meeting",
]
