"""llm/redact.py -- KNOWN-TOKEN SUBSTITUTION redaction, not generic NER.

W5 task brief, verbatim: "The case already knows its names, addresses,
phones, emails and deed refs, so substitution beats inference." A case
record already carries these values (field_values, the applicant/owner
rows) before any LLM call is ever made -- there is nothing to *infer*, only
known literal strings to find-and-replace. Generic NER (a model or
statistical tagger guessing "this span looks like a name") is deliberately
NOT used: it would both under-redact (miss a name it doesn't recognize) and
over-redact (flag ordinary text as a name), and either failure mode is
worse than exact substitution when the input is fully known in advance.

NUMBERS, DIMENSIONS, DATES, AND DISTRICTS ARE NEVER REDACTED. They are the
substance of the review (setbacks, acreage, frontage, the district a lot
sits in) -- redacting them would destroy the very thing being extracted.
This is enforced BY CONSTRUCTION, not by a runtime filter that could be
loosened by mistake: `KnownTokens` is a closed dataclass with exactly five
fields (names, addresses, phones, emails, deed_refs) -- there is no field
for "number"/"dimension"/"date"/"district", so there is no call shape that
could ever ask this module to redact one. Adding one is a one-line,
reviewable dataclass change; there is no other way to widen what gets
redacted.

ROUND-TRIP RESTORE. A redacted prompt goes to the model; the model's answer
comes back still talking about "[REDACTED_NAME_1]" -- useful for the guards
(llm/guards.py) and for the audit trail, useless to a human reading the
draft. `redact_text()`'s result carries `token_map` (placeholder -> real
value) and a `.restore()` method (also exposed standalone as
`restore_text()`) so a caller can turn the model's answer back into
readable prose immediately before it is shown to anyone, without ever
having sent the real values to the model. Restoration is EXACT-STRING,
never fuzzy: a placeholder the model mangled (wrong case, extra
whitespace) is left as-is rather than guessed at (CONTRACT.md §1.1 S7).

Honest limitation, stated here and enforced at the one call site that needs
it (ingest/vision.py): PAGE IMAGES CANNOT BE NAME-REDACTED. A name printed
or handwritten into a scanned page is pixels, not text this module can find
and replace. `require_operator_ticked_for_image()` is the enforced gate --
D-0025's safeguard, option (a): images go to a vision call only for
documents an operator has explicitly ticked. This module has no opinion on
the tick itself; it only refuses to pretend one wasn't required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping

# --------------------------------------------------------------------------- #
# KnownTokens -- the closed set of things this module will ever substitute.
# --------------------------------------------------------------------------- #

_TOKEN_CLASSES: tuple[str, ...] = ("name", "address", "phone", "email", "deed_ref")

# Stable, self-describing placeholder tags -- a human or a model reading
# redacted text can tell what KIND of thing was removed, never what it was.
_TAG = {
    "name": "NAME",
    "address": "ADDRESS",
    "phone": "PHONE",
    "email": "EMAIL",
    "deed_ref": "DEEDREF",
}

_PLACEHOLDER_RE = re.compile(r"\[REDACTED_[A-Z]+_\d+\]")

_MONTH_NAMES = frozenset(
    {
        "january", "february", "march", "april", "may", "june", "july",
        "august", "september", "october", "november", "december",
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
    }
)


@dataclass(frozen=True)
class KnownTokens:
    """The case's own known PII values, by class. Every field is a tuple of
    literal strings -- values the caller already has on record (from
    field_values / the applicant-owner-agent rows), never guessed and never
    a regex. Blank and duplicate values are tolerated (skipped / deduped)
    by `redact_text()`, not here -- this dataclass just carries what the
    caller has.
    """

    names: tuple[str, ...] = ()
    addresses: tuple[str, ...] = ()
    phones: tuple[str, ...] = ()
    emails: tuple[str, ...] = ()
    deed_refs: tuple[str, ...] = ()

    def by_class(self) -> dict[str, tuple[str, ...]]:
        return {
            "name": self.names,
            "address": self.addresses,
            "phone": self.phones,
            "email": self.emails,
            "deed_ref": self.deed_refs,
        }

    @classmethod
    def from_field_labels(cls, pairs: Mapping[str, str]) -> "KnownTokens":
        """Classify a {label: value} mapping (e.g. the worklist's own
        field labels: "Applicant", "Applicant Address", "Owner Deed
        Reference", ...) into a KnownTokens by LABEL TEXT, not by
        inspecting the value -- a label that names no PII class (Tax Lot,
        Acreage, Application Date, Core Zoning District, ...) contributes
        nothing, on purpose: this is a classifier over labels the app
        itself defined, not a guesser over arbitrary values.

        Precedence when a label could match more than one keyword ("Owner
        Deed Reference" contains both "owner" and "deed"): the specific
        contact-detail keywords (deed / address / phone / email) win over
        the generic person-role keywords (applicant / owner / agent), so
        "Owner Address" is an address, not a name.
        """
        names: list[str] = []
        addresses: list[str] = []
        phones: list[str] = []
        emails: list[str] = []
        deed_refs: list[str] = []

        for label, value in pairs.items():
            if value is None or not value.strip():
                continue
            low = label.casefold()
            if "deed" in low:
                deed_refs.append(value)
            elif "address" in low:
                addresses.append(value)
            elif "phone" in low:
                phones.append(value)
            elif "email" in low:
                emails.append(value)
            elif "applicant" in low or "owner" in low or "agent" in low:
                names.append(value)
            # else: not a recognized PII label -- contributes nothing.

        return cls(
            names=tuple(names),
            addresses=tuple(addresses),
            phones=tuple(phones),
            emails=tuple(emails),
            deed_refs=tuple(deed_refs),
        )


# --------------------------------------------------------------------------- #
# RedactionReport -- counts only, never values.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RedactionReport:
    """What was replaced, by CLASS and COUNT only -- NEVER the values.
    `occurrences[cls]` is how many substitutions happened;
    `distinct_tokens[cls]` is how many distinct literal values were
    involved (a name repeated three times is 3 occurrences, 1 distinct
    token). This is exactly the shape D-0025 requires be auditable after
    the fact: "what class of token was replaced, how many" -- never the
    values, so the report itself is safe to log, print, or hand to
    llm/events.py's `events` row.
    """

    occurrences: Mapping[str, int] = field(default_factory=dict)
    distinct_tokens: Mapping[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, dict[str, int]]:
        return {
            cls: {"occurrences": self.occurrences[cls], "distinct_tokens": self.distinct_tokens[cls]}
            for cls in self.occurrences
        }

    @property
    def total_occurrences(self) -> int:
        return sum(self.occurrences.values())

    def as_payload(self) -> dict:
        """The exact shape llm/events.py writes into an `events` row's
        payload -- counts and a total, never a value."""
        return {"counts": self.to_dict(), "total": self.total_occurrences}


_EMPTY_REPORT = RedactionReport()


def empty_report() -> RedactionReport:
    return _EMPTY_REPORT


# --------------------------------------------------------------------------- #
# redact_text -- the substitution itself.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RedactionResult:
    text: str
    report: RedactionReport
    token_map: Mapping[str, str]  # placeholder -> original value

    def restore(self, text: str) -> str:
        """De-redact `text` (typically a model's answer that still talks
        about "[REDACTED_NAME_1]") using this result's own token_map."""
        return restore_text(text, self.token_map)


def redact_text(text: str, known: KnownTokens) -> RedactionResult:
    """Replace every occurrence of every known literal value in `text` with
    a class-labelled, numbered placeholder ("[REDACTED_NAME_1]",
    "[REDACTED_ADDRESS_2]", ...).

    Longest-value-first, across ALL classes together: if one known value is
    a substring of another (a first name inside a full name, a street
    address embedded in a longer "address, city, state zip" string), the
    longer string is matched first, so the shorter match never leaves a
    partial, still-identifying fragment behind. Matching is exact-substring,
    case-insensitive and whitespace-tolerant (repeated internal whitespace
    in the known value matches any run of whitespace in the text) on the
    literal value -- never a caller-supplied regex, which could accidentally
    match digits/dates and defeat the number/dimension/date carve-out.

    Blank/whitespace-only known values are skipped. A known value that is
    ALSO nothing but a bare calendar month name (case-insensitive: "May",
    "March", ...) is skipped too -- a degenerate short name value must never
    be allowed to tear a real date in the same document in half.
    """
    counts_occ: dict[str, int] = {}
    counts_distinct: dict[str, int] = {}
    token_map: dict[str, str] = {}

    ordered: list[tuple[str, str]] = []  # (value, cls)
    for cls, values in known.by_class().items():
        for v in values:
            if not v or not v.strip():
                continue
            if v.strip().casefold() in _MONTH_NAMES:
                continue
            ordered.append((v, cls))
    ordered.sort(key=lambda pair: len(pair[0]), reverse=True)

    placeholder_for: dict[tuple[str, str], str] = {}  # (cls, casefolded value) -> placeholder
    per_class_seen: dict[str, int] = {}

    out = text
    for value, cls in ordered:
        dedup_key = (cls, value.casefold())
        if dedup_key not in placeholder_for:
            per_class_seen[cls] = per_class_seen.get(cls, 0) + 1
            placeholder = f"[REDACTED_{_TAG[cls]}_{per_class_seen[cls]}]"
            placeholder_for[dedup_key] = placeholder
        else:
            placeholder = placeholder_for[dedup_key]

        # Whitespace-tolerant: collapse the value's own internal whitespace
        # runs into a `\s+` match, so "Robert   Shattuck" (extra spacing in
        # the text) still matches a known value of "Robert Shattuck".
        pattern = re.compile(
            r"\s+".join(re.escape(part) for part in value.split()), re.IGNORECASE
        )
        out, n_subs = pattern.subn(placeholder, out)
        if n_subs:
            counts_occ[cls] = counts_occ.get(cls, 0) + n_subs
            if placeholder not in token_map:
                counts_distinct[cls] = counts_distinct.get(cls, 0) + 1
                token_map[placeholder] = value

    report = RedactionReport(occurrences=counts_occ, distinct_tokens=counts_distinct)
    return RedactionResult(text=out, report=report, token_map=token_map)


def restore_text(text: str, token_map: Mapping[str, str]) -> str:
    """De-redact `text` by replacing each known placeholder with its real
    value. EXACT-STRING match only -- a placeholder the model reproduced
    with the wrong case or mangled spacing is left untouched rather than
    fuzzily matched (CONTRACT.md §1.1 S7: no silent guessing). Unknown
    placeholders (not in `token_map`) are also left untouched."""
    if not text or not token_map:
        return text
    out = text
    for placeholder, value in token_map.items():
        out = out.replace(placeholder, value)
    return out


# --------------------------------------------------------------------------- #
# The honest image limitation -- enforced, not just documented.
# --------------------------------------------------------------------------- #

IMAGE_REDACTION_SUPPORTED = False
"""Always False. A page image cannot be name-redacted by this module (it
operates on text only)."""


class ImagePagesNotRedactable(RuntimeError):
    """Raised by require_operator_ticked_for_image() when a document's page
    images would be sent to a vision call without the explicit operator
    tick D-0025 requires."""


def require_operator_ticked_for_image(document_id: str, *, operator_ticked: bool) -> None:
    """D-0025's safeguard, enforced in code: page images go to a vision
    call ONLY for a document an operator has explicitly ticked (this
    module cannot redact a name out of pixels, so the tick is the only
    control that exists). Raises ImagePagesNotRedactable if not ticked;
    returns None (no-op) otherwise. The one call site is
    ingest/vision.py -- see its module docstring."""
    if not operator_ticked:
        raise ImagePagesNotRedactable(
            f"document {document_id!r}: page images cannot be name-redacted "
            "(llm/redact.py IMAGE_REDACTION_SUPPORTED=False) and no operator "
            "has ticked this document for a vision call -- refusing to send "
            "its page images to any LLM provider."
        )
