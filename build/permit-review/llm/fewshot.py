"""llm/fewshot.py -- the 6-matched-pair few-shot index, indexed by
(review_type, rule_id), with a HOLDOUT ENFORCED IN CODE.

W5 task brief, verbatim: "Few-shot from the 6 matched pairs, indexed by
(review_type, rule_id). HOLDOUT ENFORCEMENT IN CODE: pairs marked
'holdout': true (Dalton, Stantec) and build_fewshot.py MUST REFUSE to read
them -- a test must prove the refusal, not a comment claiming it."

--------------------------------------------------------------------------
WHERE THE "6 MATCHED PAIRS" COME FROM
--------------------------------------------------------------------------
`docs/Findings of Fact and Conclusions of Law/` (read-only fixtures, never
modified -- same rule as `docs/*.pdf`) holds real Newcastle Planning Board
records: applications and the Board's own Findings of Fact & Conclusions of
Law decisions. Cross-referencing every file by its tax map/lot against
every other file in that directory gives exactly:

    6 parcels with BOTH an application AND a matching decision on file
      (verney, blood_and_sons, shattuck, profenno, morrissey, academy_hill)
  + 2 parcels with an application but NO decision yet on file
      (dalton, stantec)
  + 3 parcels with a decision but no matching application in this folder
      (buehner, midcoast_solar, uberoi -- not "pairs" at all; excluded
      from PAIRS entirely, never indexed, never held out -- there is
      nothing paired to hold out)

That is `MATCHED_PAIR_COUNT == 6` and exactly the two names BUILD-STATE.md
already names for the W8 held-out eval run ("Dalton, Stantec") -- this
module's holdout set was not invented for this task; it is the same
distinction the rest of the build already draws for the same two files, on
the same underlying fact: no decision exists yet for either one, so no
model-output-shaped few-shot example could honestly be built from them
even without the holdout rule. The rule exists so a future decision FILE
landing in that folder for either parcel doesn't silently start leaking
into the few-shot index the moment it appears, without a deliberate
`holdout=False` edit here first.

--------------------------------------------------------------------------
WHERE (review_type, rule_id) COME FROM
--------------------------------------------------------------------------
Both are read off REAL, ALREADY-VERIFIED data, never invented for this
module:

  - `review_type` is read off each decision's own "Required Review(s)"
    table (a permit_key-shaped slug of it -- e.g. Verney's decision states
    "A Retail & Service, Heavy use ... requires an Expanded Use Permit" ->
    "expanded_use"; Academy Hill's states "Large Project Plan (CZC)" and
    "Subdivision (CZC)" -> both `("large_project_plan", "subdivision")`).
    Verified by hand against each decision's page 2 for this module; a
    pair may legitimately carry more than one review_type.
  - `rule_id` is the resolved Code node id from
    `ruleset_build.verify_citations.build_report()` -- the SAME W2 gate
    that already extracts and resolves every local citation out of these
    nine decisions (157/157 resolved; `run.py --verify-citations`). This
    module does not re-implement citation extraction; it reuses that
    report's `entries[].resolution.detail.id` (e.g. "art7.12.f.1.c") as
    rule_id, and each entry's `context` field (the sentence/paragraph the
    citation was found in) as the decision-side few-shot text. Two
    resolved formats have no articles.json node id at all
    (`article2_use_cell`, `article_district_ref` -- they resolve against
    the use-matrix / district table instead) and get a rule_id built from
    THAT structured detail instead (`use.<district_key>.<use_key>`,
    `district.<district_key>`) -- still real, resolved data, never a
    freeform slug of the citation text itself.

This is a genuinely-populated index (not a placeholder that accepts a
rule_id argument and ignores it): every entry's rule_id traces back to a
`resolution.status == "resolved"` row in the citation report, so
`(review_type, rule_id)` is a real key, not just the shape the task brief
asked for.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.config import APP_ROOT

FIXTURES_DIR = APP_ROOT.parent.parent / "docs" / "Findings of Fact and Conclusions of Law"


class HoldoutError(PermissionError):
    """Raised whenever code attempts to read either document of a pair
    marked `holdout=True`. Subclasses PermissionError (not ValueError) --
    this is a refused ACCESS, not a malformed argument."""


@dataclass(frozen=True)
class PairSpec:
    name: str
    review_types: tuple[str, ...]
    application_filename: str | None
    decision_filename: str | None
    holdout: bool = False

    def __post_init__(self) -> None:
        # Defense in depth: even a hand-miscoded PairSpec whose filenames
        # obviously name Dalton or Stantec refuses to construct with
        # holdout=False, rather than relying solely on PAIRS being
        # correct by convention.
        haystack = f"{self.application_filename or ''} {self.decision_filename or ''}".casefold()
        if ("dalton" in haystack or "stantec" in haystack) and not self.holdout:
            raise ValueError(
                f"PairSpec {self.name!r} names a held-out fixture but holdout=False "
                "-- refusing to construct a pair that would silently defeat the W8 "
                "eval holdout (see module docstring)."
            )
        if self.holdout and self.decision_filename is not None:
            raise ValueError(
                f"PairSpec {self.name!r} is holdout=True but carries a "
                "decision_filename -- a holdout pair has no matching decision by "
                "definition (that is WHY it is held out); set decision_filename=None."
            )


# The 6 matched pairs (holdout=False) + the 2 named holdouts (holdout=True).
# Filenames are verbatim from docs/Findings of Fact and Conclusions of Law/
# -- verified byte-for-byte against `ruleset_build.verify_citations.
# find_decision_pdfs()`'s own listing while building this module.
PAIRS: tuple[PairSpec, ...] = (
    PairSpec(
        name="verney",
        review_types=("expanded_use",),
        application_filename="4.B1. M004, L036 (461 Sheepscot Rd, Verney) Use Application 2025.04.02.pdf",
        decision_filename="4.B2. M004, L036 (461 Sheepscot Rd, Verney) 2025.04.13 FoF & CoL.pdf",
    ),
    PairSpec(
        name="blood_and_sons",
        review_types=("small_project_plan", "use_permit"),
        application_filename="5.A.2 M012, L004 (15 Hall St, Blood and Sons) Zoning Application.pdf",
        decision_filename="5.A.x1 M012, L004 (15 Hall St, Blood and Sons) 2024.10.15 FoF & CoL.pdf",
    ),
    PairSpec(
        name="shattuck",
        review_types=("subdivision",),
        application_filename="4.A.1. M003, L059 (White Rd, Shattuck) Subdivision Application 2025.10.07.pdf",
        decision_filename="M003, L059 (White Rd, Shattuck), Subdivision FoF & CoL 2025.12.18.pdf",
    ),
    PairSpec(
        name="profenno",
        review_types=("shoreland_zoning", "small_project_plan"),
        application_filename="M003, L065-B (Profenno, Perkins Point Rd) Planning Board Application 2024.06.05.pdf",
        decision_filename="M003, L065-B (Profenno, Perkins Point Rd) FoF & CoL 2024.06.13 DRAFT.pdf",
    ),
    PairSpec(
        name="morrissey",
        review_types=("shoreland_zoning", "small_project_plan"),
        application_filename="M011, L046-A (Morrissey, 53 Pleasant Street) SLZ Application, 2025 Submitted Documents.pdf",
        decision_filename="M011, L046-A (Morrissey, Plesant Street) FoF & CoL 2024.05.21.pdf",
    ),
    PairSpec(
        name="academy_hill",
        review_types=("large_project_plan", "subdivision"),
        application_filename="M012, L011 (Z38, 38 Academy Hill Rd) Application 2024.07.03 04 Zoning Permit App.pdf",
        decision_filename="M012, L011 (Z38, 38 Academy Hill Rd) _FoF & CoL 2024.07.11 DRAFT.pdf",
    ),
    PairSpec(
        name="dalton",
        review_types=(),
        application_filename="M002, L053 (976 US Rt 1, Dalton) 2025.09.09 Application.pdf",
        decision_filename=None,
        holdout=True,
    ),
    PairSpec(
        name="stantec",
        review_types=(),
        application_filename="M004, L087 (NT Land III, 684 US Route 1) (Stantec) application 2024.05.08.pdf",
        decision_filename=None,
        holdout=True,
    ),
)

MATCHED_PAIR_COUNT = sum(1 for p in PAIRS if not p.holdout)
HOLDOUT_COUNT = sum(1 for p in PAIRS if p.holdout)
HOLDOUT_NAMES = frozenset(p.name for p in PAIRS if p.holdout)
assert MATCHED_PAIR_COUNT == 6, f"expected exactly 6 matched pairs, got {MATCHED_PAIR_COUNT}"
assert HOLDOUT_COUNT == 2, f"expected exactly 2 holdout pairs, got {HOLDOUT_COUNT}"
assert HOLDOUT_NAMES == {"dalton", "stantec"}, HOLDOUT_NAMES

_BY_NAME: dict[str, PairSpec] = {p.name: p for p in PAIRS}


def get_pair(name: str) -> PairSpec:
    """Look up a pair's METADATA by name. This never touches a file and
    never raises HoldoutError -- knowing a pair exists and is held out is
    not the same as reading its content (that gate is in
    application_pdf_path()/decision_pdf_path() below, and everything that
    calls them)."""
    try:
        return _BY_NAME[name]
    except KeyError:
        raise KeyError(f"no such pair {name!r}; known pairs: {sorted(_BY_NAME)}") from None


def fixtures_available() -> bool:
    """True iff every matched-pair PDF this module names actually exists
    under FIXTURES_DIR (both holdout applications included) -- guards
    tests/tools that need the real files, the same way
    tests/test_triage.py's fixture-presence checks do."""
    for pair in PAIRS:
        if pair.application_filename and not (FIXTURES_DIR / pair.application_filename).exists():
            return False
        if pair.decision_filename and not (FIXTURES_DIR / pair.decision_filename).exists():
            return False
    return True


# ---------------------------------------------------------------------------
# THE ENFORCEMENT CHOKEPOINT. Every path that would open a holdout pair's
# bytes funnels through _require_readable() FIRST, before any Path is even
# joined to FIXTURES_DIR -- so a monkeypatched pymupdf.open() in a test can
# assert it is never even called for Dalton or Stantec (tests/test_fewshot.py).
# ---------------------------------------------------------------------------


def _require_readable(pair: PairSpec) -> None:
    if pair.holdout:
        raise HoldoutError(
            f"{pair.name!r} is marked holdout=True in llm.fewshot.PAIRS (Dalton "
            "and Stantec are held out for the W8 eval run -- BUILD-STATE.md's "
            "'Eval harness + held-out run (Dalton, Stantec)'). build_fewshot.py "
            f"MUST NOT open either of this pair's documents. Refusing to read "
            f"{pair.name!r} before any file was touched."
        )


def application_pdf_path(pair: PairSpec) -> Path:
    """The pair's application PDF path. Raises HoldoutError for a holdout
    pair -- BEFORE resolving any path -- and ValueError if the pair
    (non-holdout) has no application on file (shouldn't happen for any
    entry in PAIRS today, but a caller passing a hand-built PairSpec could
    hit it)."""
    _require_readable(pair)
    if not pair.application_filename:
        raise ValueError(f"pair {pair.name!r} has no application_filename on record")
    return FIXTURES_DIR / pair.application_filename


def decision_pdf_path(pair: PairSpec) -> Path:
    """The pair's decision PDF path. Raises HoldoutError for a holdout pair
    -- BEFORE resolving any path -- and ValueError if the pair has no
    decision on file (true of dalton/stantec, but those already raise
    HoldoutError first; a caller cannot reach the ValueError branch for
    either without first defeating the holdout check some other way)."""
    _require_readable(pair)
    if not pair.decision_filename:
        raise ValueError(f"pair {pair.name!r} has no decision_filename on record")
    return FIXTURES_DIR / pair.decision_filename


def _extract_pdf_text(path: Path) -> str:
    import pymupdf

    doc = pymupdf.open(str(path))
    try:
        return "\n".join(doc[i].get_text() for i in range(doc.page_count))
    finally:
        doc.close()


def read_application_text(pair: PairSpec) -> str:
    """Open + extract this pair's APPLICATION pdf's full text. Raises
    HoldoutError, with NO file I/O of any kind, for a holdout pair -- this
    is the function tests/test_fewshot.py calls directly (with
    pymupdf.open monkeypatched to assert it is never invoked) to prove the
    refusal in code, not merely by comment."""
    path = application_pdf_path(pair)  # raises HoldoutError first, for holdout pairs
    return _extract_pdf_text(path)


def read_decision_text(pair: PairSpec) -> str:
    """Same as read_application_text(), for the decision PDF."""
    path = decision_pdf_path(pair)  # raises HoldoutError first, for holdout pairs
    return _extract_pdf_text(path)


def build_fewshot_block(pair: PairSpec, *, max_chars_each: int = 2000) -> str:
    """Render one matched pair's application + decision excerpts into a
    single prompt-ready text block (application context paired with the
    Board's own decision language, the shape a few-shot-augmented prompt
    actually wants). Refuses on a holdout pair via read_application_text/
    read_decision_text's own gate -- there is no separate check here to
    keep in sync."""
    application_text = read_application_text(pair)
    decision_text = read_decision_text(pair)
    return (
        f"--- Example: {pair.name} ({', '.join(pair.review_types)}) ---\n"
        f"Application excerpt:\n{application_text[:max_chars_each]}\n\n"
        f"Board decision excerpt:\n{decision_text[:max_chars_each]}\n"
    )


# ---------------------------------------------------------------------------
# The index itself, built from ruleset_build.verify_citations's already-
# verified citation extraction over these same nine real decisions.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FewshotExample:
    pair_name: str
    review_type: str
    rule_id: str
    decision_excerpt: str  # real sentence/paragraph from the Board's OWN decision text
    source_document: str
    page: int
    citation_raw: str  # the citation text AS WRITTEN in the decision -- provenance only;
    # NEVER re-emitted as a rendered citation (CONTRACT.md §5.1 -- only
    # app/citation.py may render one).


def _pairs_by_decision_filename() -> dict[str, PairSpec]:
    return {p.decision_filename: p for p in PAIRS if not p.holdout and p.decision_filename}


def _rule_id_for_entry(entry: dict) -> str | None:
    """Real, resolved structured data only -- never a slug of the raw
    citation text. Returns None (skip this entry) when the resolution
    carries nothing usable as a stable id."""
    resolution = entry.get("resolution") or {}
    if resolution.get("status") != "resolved":
        return None
    detail = resolution.get("detail") or {}
    node_id = detail.get("id")
    if node_id:
        return str(node_id)
    fmt = entry.get("format")
    if fmt == "article2_use_cell":
        district_key, use_key = detail.get("district_key"), detail.get("use_key")
        return f"use.{district_key}.{use_key}" if district_key and use_key else None
    if fmt == "article_district_ref":
        district_key = detail.get("district_key")
        return f"district.{district_key}" if district_key else None
    return None


def citation_entries() -> list[dict]:
    """Fresh (never a possibly-stale on-disk report) citation extraction
    over all nine real decisions, via the already-built, already-verified
    W2 gate. Deliberately re-runs it rather than reading
    data/citation-report.json, so this module's index can never silently
    drift from what --verify-citations currently proves resolves."""
    from ruleset_build import verify_citations

    report = verify_citations.build_report(ruleset_key="adopted")
    return list(report["entries"])


def build_index(
    entries: Sequence[dict] | None = None,
) -> dict[tuple[str, str], tuple[FewshotExample, ...]]:
    """Build the (review_type, rule_id) -> examples index over the 6
    matched pairs ONLY. Never touches dalton/stantec -- they are excluded
    structurally (`_pairs_by_decision_filename()` only includes non-holdout
    pairs with a decision_filename), on top of the fact that
    `citation_entries()` only ever processes documents whose filename
    contains "FoF & CoL" in the first place (find_decision_pdfs()), which
    neither holdout pair's application does.
    """
    if entries is None:
        entries = citation_entries()
    by_doc = _pairs_by_decision_filename()

    grouped: dict[tuple[str, str], list[FewshotExample]] = {}
    for entry in entries:
        pair = by_doc.get(entry.get("source_document"))
        if pair is None:
            continue  # not one of our 6 matched pairs (e.g. Buehner/Midcoast/Uberoi)
        rule_id = _rule_id_for_entry(entry)
        if not rule_id:
            continue
        for review_type in pair.review_types:
            example = FewshotExample(
                pair_name=pair.name,
                review_type=review_type,
                rule_id=rule_id,
                decision_excerpt=entry.get("context", ""),
                source_document=entry.get("source_document", ""),
                page=int(entry.get("page", 0)),
                citation_raw=entry.get("raw", ""),
            )
            grouped.setdefault((review_type, rule_id), []).append(example)

    return {key: tuple(v) for key, v in grouped.items()}


def lookup(
    index: dict[tuple[str, str], tuple[FewshotExample, ...]],
    review_type: str,
    rule_id: str,
    *,
    limit: int = 3,
) -> tuple[FewshotExample, ...]:
    return tuple(index.get((review_type, rule_id), ()))[:limit]
