"""Re-exports engine.deadlines under the name app/migrations/
0002_case_tracking.sql's own docstring expects ("app/deadlines.py reads the
LIVE set [of case_milestones] as the anchor dates its clocks compute from").

RECONCILIATION NOTE (same pattern as app/dates.py <-> app/meetings.py). Two
concurrently-written parts of this project named this engine differently:
CONTRACT.md's directory layout (§2) marks `engine/` as the home for
"rules -> criteria sets -> findings_nodes" work, and the W3 task brief that
commissioned the statutory deadline clocks asked for `engine/deadlines.py`
there. A sibling migration (0002_case_tracking.sql, also W3) was written
expecting `app/deadlines.py` instead. Per the same rule app/dates.py states
("the CONTRACT wins, but don't re-implement the arithmetic a second time"):
the real implementation lives in engine/deadlines.py; this module is a thin
re-export so `from app import deadlines` (or `import app.deadlines`) also
works, with zero duplicated logic. Nothing here is a second copy of a rule --
a wrong deadline is a wrong legal deadline, and two copies of the same
arithmetic is exactly the drift CONTRACT.md warns against for meeting dates.
"""

from __future__ import annotations

from engine.deadlines import (  # noqa: F401  (re-exported, not just used locally)
    AUTO_APPROVAL_WARNING_DAYS,
    REVIEW_TRACKS,
    CaseFacts,
    Clock,
    ClocksNotFound,
    ClockStatus,
    Deadline,
    DutyKind,
    NoticeEvent,
    add_business_days,
    add_calendar_days,
    add_months,
    case_facts_from_row,
    clock_is_extendable,
    compute_deadlines,
    deadline_is_extendable,
    deadline_row,
    event_recordable_kinds,
    extendable_clock_keys,
    is_business_day,
    load_all_case_facts,
    load_clocks,
    maine_legal_holiday_label,
    maine_legal_holidays,
    open_deadlines,
    parse_date_or_none,
    presents_auto_approval_risk,
)

__all__ = [
    "AUTO_APPROVAL_WARNING_DAYS",
    "REVIEW_TRACKS",
    "CaseFacts",
    "Clock",
    "ClocksNotFound",
    "ClockStatus",
    "Deadline",
    "DutyKind",
    "NoticeEvent",
    "add_business_days",
    "add_calendar_days",
    "add_months",
    "case_facts_from_row",
    "clock_is_extendable",
    "compute_deadlines",
    "deadline_is_extendable",
    "deadline_row",
    "event_recordable_kinds",
    "extendable_clock_keys",
    "is_business_day",
    "load_all_case_facts",
    "load_clocks",
    "maine_legal_holiday_label",
    "maine_legal_holidays",
    "open_deadlines",
    "parse_date_or_none",
    "presents_auto_approval_risk",
]
