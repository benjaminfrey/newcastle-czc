"""ingest/fields.py -- the FieldCandidate dataclass + merge rules.

Implements this workflow's (W4) task brief, "THE CENTRAL DESIGN PRINCIPLE":

    A field candidate is EVIDENCE, never an answer. field_candidates rows
    carry {value_raw, value_norm, unit, document_id, page_no, bbox, method,
    confidence, rationale} and default needs_confirmation=TRUE ALWAYS.
    field_values rows are DECISIONS a human made. The operator confirms;
    the app never silently promotes a candidate to a value.

FieldCandidate below mirrors app/migrations/0001_init.sql's `field_candidates`
table shape (CONTRACT.md 3.6) closely enough that a caller can insert one
almost column-for-column, but it is a plain, DB-independent dataclass: this
module (and ingest/native.py, ingest/positional.py) never opens a database
connection. `method` is field_candidates.extractor's exact 5-value enum
('regex' | 'table' | 'vision' | 'llm' | 'manual'); ingest/native.py's
label-text-driven matches use 'regex' (a declared label PATTERN is located
and paired with its value), ingest/positional.py's geometry-only matches
(no label text exists to search for) use 'table' -- there is no cleaner fit
in that fixed enum for "matched by position against a known layout", and
'table' is at least closer in kind (structured-by-position) than
'regex'/'vision'/'llm'/'manual'. `needs_confirmation` is enforced to be
literally always True in `__post_init__` -- there is no code path that can
construct a FieldCandidate with it False.

Merge rules (task brief, "MERGE RULES", restated in the docstrings below):
candidates for the same field_key from different source_priority tiers that
DISAGREE -> contested, both retained. Same tier (or different tiers)
agreeing -> still unconfirmed, NEVER auto-confirmed -- there is no code path
in this module that produces a 'confirmed' state; only a human does that
(field_values.state, CONTRACT.md 3.6).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Sequence

# ---------------------------------------------------------------------------
# FieldCandidate
# ---------------------------------------------------------------------------

_EXTRACTORS = frozenset({"regex", "table", "vision", "llm", "manual"})


@dataclass(frozen=True)
class FieldCandidate:
    """One value ONE source offered for ONE field. Never deleted, never
    overwritten, never silently promoted to an answer (CONTRACT.md 3.6's
    field_candidates / field_values split). `needs_confirmation` is pinned
    True in __post_init__ -- there is no way to construct one with it False.
    """

    field_key: str  # e.g. 'applicant.name', 'parcel.lot_size_acres' -- see
    # ingest/native.py's module docstring for the canonical, generation-
    # independent field_key vocabulary this module's callers use.
    value_raw: str  # exactly as concatenated from the source spans
    value_norm: float | str | None  # parsed number, or normalized text
    unit: str | None
    document_id: str | None
    page_no: int
    bbox: tuple[float, float, float, float]
    method: str  # field_candidates.extractor: 'regex'|'table'|'vision'|'llm'|'manual'
    confidence: float
    rationale: str
    subject_key: str | None = None  # per-lot scope; None = whole application
    source_priority: int = 40  # documents.source_priority at extraction time
    needs_confirmation: bool = True

    def __post_init__(self) -> None:
        if self.needs_confirmation is not True:
            raise ValueError(
                "FieldCandidate.needs_confirmation must always be True -- "
                "a candidate is evidence, never an answer (task brief, THE "
                "CENTRAL DESIGN PRINCIPLE). This is not a caller option."
            )
        if self.method not in _EXTRACTORS:
            raise ValueError(f"method {self.method!r} not in {sorted(_EXTRACTORS)}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence {self.confidence!r} out of [0,1]")
        if not self.field_key:
            raise ValueError("field_key must be non-empty")
        if self.page_no <= 0:
            raise ValueError(f"page_no must be positive, got {self.page_no!r}")


# ---------------------------------------------------------------------------
# Text / numeric normalization shared by native.py and positional.py
# ---------------------------------------------------------------------------

_PLACEHOLDER_TOKEN_RE = re.compile(r"^[_.\-]+$")


def strip_placeholder(raw: str) -> str:
    """Drop tokens that are pure blank-line placeholder glyphs ('____',
    '....', '----', or a single bare '-') -- the printed Gen-1/Gen-2
    template's own unfilled blanks, which PyMuPDF returns as ordinary text
    spans. A lone '-' is included deliberately: CONTRACT.md 4.2.1 already
    treats a bare '-' as one of the Code's own "not established" tokens,
    not a real value, and the identical printed convention shows up on
    these permit-application templates (e.g. the leading '-' printed
    before an unfilled "SD - ____(Special District)" blank). Never touches
    real content -- every character in the token must be a placeholder
    glyph.
    """
    tokens = [t for t in raw.split() if not _PLACEHOLDER_TOKEN_RE.match(t)]
    return re.sub(r"\s+", " ", " ".join(tokens)).strip(" ,")


def normalize_label(s: str) -> str:
    """Casefold, NFKD, drop punctuation (colons especially -- a label like
    'Address:' and the haystack text 'Address:' must compare equal to a
    bare 'address'), collapse whitespace. Shared by the label-text search
    in ingest/native.py."""
    s = unicodedata.normalize("NFKD", s)
    s = s.replace(":", " ")
    s = re.sub(r"[^a-z0-9 ]", " ", s.casefold())
    return re.sub(r"\s+", " ", s).strip()


_NUM_RE = re.compile(r"[+-]?\d[\d,]*\.?\d*")
_UNIT_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("acres", re.compile(r"\bacres?\b")),
    ("sf", re.compile(r"\bsf\b|\bsq\.?\s*ft\b|\bsquare feet\b")),
    ("ft", re.compile(r"\bft\b|\bfeet\b")),
)


def parse_numeric(raw: str, unit_hint: str | None = None) -> tuple[float | None, str | None, str]:
    """Best-effort numeric parse of a raw value string. Returns
    (value_num, unit, text) -- value_num is None when no digit run is
    found (free text stays free text; this NEVER raises and NEVER guesses
    a unit that isn't either declared or textually present)."""
    text = raw.strip()
    unit = unit_hint
    if unit is None:
        low = text.lower()
        for u, pat in _UNIT_PATTERNS:
            if pat.search(low):
                unit = u
                break
    m = _NUM_RE.search(text)
    value_num: float | None = None
    if m:
        try:
            value_num = float(m.group(0).replace(",", ""))
        except ValueError:
            value_num = None
    return value_num, unit, text


# ---------------------------------------------------------------------------
# Merge rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MergeResult:
    """The resolution of every FieldCandidate offered for ONE
    (field_key, subject_key). Mirrors field_values' shape (CONTRACT.md 3.6)
    closely enough to seed one row, but -- like FieldCandidate -- this is a
    plain dataclass; no state here is ever 'confirmed'. Only a human acting
    through the operator-confirm UI produces that state.
    """

    field_key: str
    subject_key: str | None
    candidates: tuple[FieldCandidate, ...]  # ALL, highest source_priority/confidence first
    chosen: FieldCandidate  # the one field_values.chosen_candidate_id would point at
    state: str  # 'unconfirmed' | 'contested' -- NEVER 'confirmed', NEVER 'overridden'
    contested_with: tuple[FieldCandidate, ...] = ()


def _values_agree(a: FieldCandidate, b: FieldCandidate) -> bool:
    """Numeric candidates agree within a small tolerance AND the same unit
    (None counts as matching None only -- a bare number and an explicitly
    unitless number agree; a number with a stated unit and one without do
    NOT silently agree, since that is exactly the kind of ambiguity
    CONTRACT.md 1 S7 exists to surface, not paper over). Text candidates
    agree when their normalized (casefold, whitespace-collapsed) text is
    identical."""
    a_num = a.value_norm if isinstance(a.value_norm, (int, float)) else None
    b_num = b.value_norm if isinstance(b.value_norm, (int, float)) else None
    if a_num is not None and b_num is not None:
        return abs(a_num - b_num) < 1e-6 and a.unit == b.unit
    if a_num is not None or b_num is not None:
        return False  # one parsed numeric, the other didn't -- a disagreement, not a match
    a_text = normalize_label(a.value_raw)
    b_text = normalize_label(b.value_raw)
    return a_text == b_text


def merge_field_group(candidates: Sequence[FieldCandidate]) -> MergeResult:
    """Merge every candidate offered for ONE (field_key, subject_key).
    CONTRACT.md 3.6 / task brief MERGE RULES:
      - candidates from DIFFERENT source_priority tiers that disagree
        -> state='contested', BOTH retained (contested_with holds the
        losers).
      - candidates that all agree (same tier or not) -> state='unconfirmed'.
        NEVER auto-confirmed -- there is no branch here that returns
        'confirmed'.
    `chosen` is always the highest-(source_priority, confidence) candidate
    -- "the form is wrong, the plan governs" (CONTRACT.md 3.6) -- even when
    contested, so a contested field_value's displayed value is still the
    higher-priority one, with the loser(s) surfaced via contested_with for
    the Board to see, never silently dropped.
    """
    if not candidates:
        raise ValueError("merge_field_group requires at least one candidate")
    field_key = candidates[0].field_key
    subject_key = candidates[0].subject_key
    for c in candidates:
        if c.field_key != field_key or c.subject_key != subject_key:
            raise ValueError(
                "merge_field_group requires all candidates to share one "
                f"(field_key, subject_key); got {c.field_key!r}/{c.subject_key!r} "
                f"alongside {field_key!r}/{subject_key!r}"
            )
    ordered = tuple(sorted(candidates, key=lambda c: (-c.source_priority, -c.confidence)))
    chosen = ordered[0]
    disagreeing = tuple(c for c in ordered[1:] if not _values_agree(chosen, c))
    state = "contested" if disagreeing else "unconfirmed"
    return MergeResult(
        field_key=field_key,
        subject_key=subject_key,
        candidates=ordered,
        chosen=chosen,
        state=state,
        contested_with=disagreeing,
    )


def merge_all(candidates: Iterable[FieldCandidate]) -> dict[tuple[str, str | None], MergeResult]:
    """Group candidates by (field_key, subject_key) and merge each group.
    The convenience entry point a caller with a flat candidate list (e.g.
    every candidate extracted across every document on a case) actually
    calls."""
    groups: dict[tuple[str, str | None], list[FieldCandidate]] = {}
    for c in candidates:
        groups.setdefault((c.field_key, c.subject_key), []).append(c)
    return {key: merge_field_group(group) for key, group in groups.items()}


# ---------------------------------------------------------------------------
# ORIENTATION CHECK -- the real Blood & Sons swap (task brief, verbatim)
# ---------------------------------------------------------------------------

ARTICLE9_WIDTH_DEFINITION = (
    "Article 9 (Definitions): Building Width is the building dimension "
    "measured along (parallel to) the lot's frontage; Building Depth is "
    "measured perpendicular to the frontage, from the front of the "
    "building toward the rear."
)


def check_width_depth_orientation(
    width: FieldCandidate | None, depth: FieldCandidate | None
) -> str | None:
    """Task brief, ORIENTATION CHECK: 'if a building width > depth, raise a
    check quoting the Article 9 definition (width is measured along the
    frontage) and force confirmation. This is the real Blood & Sons swap.'

    In the one sample pair where both a form and a plan existed (Blood &
    Sons), the applicant's form had width and depth SWAPPED precisely
    because the Code measures width along the frontage and the form-filler
    didn't. Returns a human-readable warning string (quoting Article 9)
    when `width`'s value exceeds `depth`'s; returns None when the check
    doesn't trigger, or either input is missing/non-numeric.

    This function does not and cannot change any field_values.state --
    field_candidates.needs_confirmation is already pinned True on every
    candidate (see FieldCandidate.__post_init__), so there is nothing
    further to "force"; this exists to hand the operator-confirm UI a
    citation-grade rationale string to surface alongside the two candidates
    so the Board's reviewer sees WHY this pair needs a second look, not
    just that it does.
    """
    if width is None or depth is None:
        return None
    w = width.value_norm if isinstance(width.value_norm, (int, float)) else None
    d = depth.value_norm if isinstance(depth.value_norm, (int, float)) else None
    if w is None or d is None:
        return None
    if w > d:
        return (
            f"ORIENTATION CHECK: the extracted building width ({w:g} ft) exceeds the "
            f"extracted building depth ({d:g} ft). {ARTICLE9_WIDTH_DEFINITION} A width "
            "greater than depth is exactly the pattern seen when width/depth were "
            "swapped on the source document (Blood & Sons) -- confirm both values "
            "against the plan, not just the form, before accepting either."
        )
    return None
