"""An entry of the explanation library, its kinds and statuses, and the live rule (design 2, §4–5).

An entry reaches the public only when it is live: ratified by the Planning Board after the chair
approved it, and not pulled. The words the chair approved before this design are live as they
stand (decision 15). The rule lives in the data; no setting reaches it.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Kind = Literal["standard", "interpretation", "template", "word"]
Status = Literal["draft", "approved", "ratified", "pulled"]
KINDS = frozenset(Kind.__args__)
STATUSES = frozenset(Status.__args__)

# Approved before the library's design (2026-11-08): live without the Board (the chair, decision 15).
GRANDFATHERED_BEFORE = date(2026, 11, 8)


# Words that read as the Town's decision (spec §10.3), approved by the chair as proposed (2026-11-05).
NEVER_WORDS = re.compile(r"\b(approved|denied|granted|rejected|permit issued|compliant|violates)\b", re.IGNORECASE)


class LibraryError(Exception):
    pass


@dataclass(frozen=True)
class LibraryEntry:
    id: str
    kind: Kind
    overline: str
    answer: str
    detail: str
    why: str
    cites: tuple[str, ...]
    version: int
    status: Status
    batch: str                                  # the file's stem, set by the loader
    standards: tuple[str, ...] = ()             # the standard keys it explains (render.standard_key)
    slots: dict = field(default_factory=dict)   # name -> {standard, part}, filled from the standards
    terms: tuple[str, ...] = ()                 # Article 9 defined terms used in the text
    district_notes: dict = field(default_factory=dict)  # district key -> an approved note
    picture: str | None = None
    picture_alt: str | None = None
    ruleset: str = "adopted-v1.0"               # the ruleset it was approved against
    approved_by: str | None = None
    approved_on: date | None = None
    ratified_on: date | None = None
    ratified_by: str | None = None
    decided_by: str | None = None               # interpretations: who ruled, when, and where it's recorded
    decided_on: date | None = None
    source: str | None = None
    pulled_on: date | None = None
    pulled_by: str | None = None
    pulled_why: str | None = None
    review_note: str | None = None              # the chair's note when he sent it back


def as_date(v) -> date | None:
    return None if v is None else v if isinstance(v, date) else date.fromisoformat(str(v))


def is_live(e: LibraryEntry, pulled: frozenset[str] = frozenset()) -> bool:
    if e.id in pulled or e.status == "pulled":
        return False
    if e.status == "ratified":
        return True
    return e.status == "approved" and e.approved_on is not None and as_date(e.approved_on) < GRANDFATHERED_BEFORE


@dataclass(frozen=True)
class Library:
    entries: dict[str, LibraryEntry]
    open_questions: dict[str, tuple[str, ...]]
    digest: str
    flags: dict[str, tuple[str, ...]] = field(default_factory=dict)
