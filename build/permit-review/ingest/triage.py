"""ingest/triage.py — CONTRACT.md §2's `ingest/` home ("upload, PDF page
split, text/vision extraction"). This module does the "PDF page split" +
classification half only: a per-page CENSUS (char count, image count,
rotation, dimensions, a deterministic content hash) and a tier assignment.

Triage classifies pages; it does not read them. NO field-value extraction,
NO OCR, NO vision, NO LLM call happens anywhere in this module -- later
workflows own those (this workflow's task brief, restated here so it can't
be missed mid-refactor).

Tiers (task brief, verbatim):
    A native      char_count >= 200 and label-like tokens present
    B hybrid      20 <= char_count < 200, OR text present but no label
                  tokens present (the "values with no labels" trap)
    C scan        char_count < 20
    D plansheet   page area > tabloid, OR high vector-line density, OR
                  rotated -- and FORCES the owning document's
                  source_priority to 100 (see app/routes/documents.py,
                  which owns that force since it is a document-level fact,
                  not a page-level one)

page_sha256 is a hash of the page's RENDERED content (a fixed-DPI pixmap),
not of raw PDF bytes -- so later vision passes can cache a result per page
even across two PDFs whose page looks the same but was produced by a
different tool (task brief: "page_sha256 exists so later vision results
can be cached per page ... computed from the rendered page content
deterministically").
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

# Tier C (scan) ceiling / tier B floor -- task brief: "C scan: char_count <
# 20". Named once and reused by the plansheet rotation heuristic below so
# the two stay in sync by construction.
_SCAN_TIER_MAX_CHARS = 20

# ---------------------------------------------------------------------------
# Tier-D ("plansheet") heuristics.
# ---------------------------------------------------------------------------

# Tabloid = 11in x 17in = 792pt x 1224pt (72 pt/in). Any page whose area
# exceeds this is presumptively a plan/drawing sheet rather than a text
# document, regardless of orientation (area is compared, not width/height
# individually, so a landscape tabloid and a portrait tabloid are treated
# the same).
_TABLOID_AREA_PT2 = (11 * 72) * (17 * 72)

# A page with at least this many distinct vector path objects is treated as
# "high vector-line density" -- the drafting-heavy look of a civil/site plan
# sheet (property lines, contours, hatching, symbol legends) versus a page
# of prose or a scanned/typed form. A plain business letter or application
# form has ~0 vector paths; a real site plan commonly has hundreds.
_HIGH_VECTOR_DENSITY_THRESHOLD = 60

# ---------------------------------------------------------------------------
# Tier-A ("native") label-token heuristic -- the vocabulary a real Newcastle
# application form uses (Applicant, Owner, Map/Lot, Date, Address, Acreage,
# District, Setback, Signature, ...). A page carrying at least one of these
# immediately followed by a colon/dash/underscore is "label-like": text WITH
# structure, distinct from a page of unstructured prose and distinct from
# the tier-B "values with no labels" trap the task brief names explicitly
# (e.g. a table of bare numbers with no header row).
#
# A bare date (10/10/2025) is treated as label-like too, even with no
# adjacent keyword: real submission correspondence (a cover letter, an
# abutter comment) is still a dated, addressed, official document -- not
# free-flowing prose -- and the task brief's own real-file ground truth
# requires this (the Morrissey file's page 4 is a one-paragraph cover
# letter with a leading date and a return address, no "Label:" pattern
# anywhere, and must still triage to tier A).
# ---------------------------------------------------------------------------
_LABEL_KEYWORDS = (
    "applicant", "owner", "date", "map", "lot", "block", "address",
    "acreage", "zone", "zoning", "district", "setback", "signature",
    "permit", "parcel", "phone", "email", "town", "state", "surveyor",
    "engineer", "deed", "book", "page", "project", "description",
    "scale", "sheet", "drawn", "checked", "revision", "certification",
    "witness", "notary", "applicant's", "owner's", "title", "county",
)
_LABEL_RE = re.compile(r"\b(" + "|".join(_LABEL_KEYWORDS) + r")\b\s*[:\-_]", re.IGNORECASE)
_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")


def has_label_tokens(text: str) -> bool:
    """True if `text` contains at least one recognized form-label token
    immediately followed by ':' / '-' / '_' (a labeled field, e.g.
    "Applicant:", "Map/Lot -"), or a bare numeric date."""
    return bool(_LABEL_RE.search(text)) or bool(_DATE_RE.search(text))


@dataclass(frozen=True)
class PageCensus:
    page_number: int  # 1-based
    char_count: int
    image_count: int
    rotation: int  # 0, 90, 180, or 270
    width_pt: float
    height_pt: float
    vector_path_count: int
    has_label_tokens: bool
    is_plansheet: bool
    tier: str  # "A" | "B" | "C" | "D"
    page_sha256: str

    def as_row(self) -> dict:
        """Column-name-keyed dict matching pages' 0004_page_triage.sql
        columns, for a caller building an INSERT."""
        return {
            "page_number": self.page_number,
            "width_pt": self.width_pt,
            "height_pt": self.height_pt,
            "char_count": self.char_count,
            "image_count": self.image_count,
            "rotation": self.rotation,
            "vector_path_count": self.vector_path_count,
            "page_sha256": self.page_sha256,
            "tier": self.tier,
            "has_label_tokens": int(self.has_label_tokens),
            "is_plansheet": int(self.is_plansheet),
        }


class UnreadablePdf(ValueError):
    """The file could not be opened as a PDF at all (corrupt, truncated, or
    not actually a PDF despite passing the upload-time magic-byte sniff).
    Distinct from any tier -- there is no page census to report."""


def _render_page_sha256(page: "fitz.Page") -> str:
    """Deterministic hash of the page's rendered pixels at a fixed 72-DPI
    identity matrix (never the raw PDF bytes, which can differ for two
    pages that render identically due to incidental encoding differences).
    Same page content -> same bytes -> same hash, every run, which is
    exactly what a later per-page vision-result cache needs.
    """
    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
    return hashlib.sha256(pix.samples).hexdigest()


def _classify_tier(char_count: int, labeled: bool, plansheet: bool) -> str:
    if plansheet:
        return "D"
    if char_count < _SCAN_TIER_MAX_CHARS:
        return "C"
    if char_count >= 200 and labeled:
        return "A"
    # 20 <= char_count < 200 (hybrid), OR char_count >= 200 with no label
    # tokens (the "values with no labels" trap) -- both are tier B.
    return "B"


def census_page(page: "fitz.Page", *, page_number: int) -> PageCensus:
    """Census exactly one already-open fitz page. Read-only."""
    text = page.get_text("text") or ""
    char_count = len(text)
    image_count = len(page.get_images(full=True))
    rotation = int(page.rotation or 0)
    rect = page.rect
    width_pt, height_pt = float(rect.width), float(rect.height)
    vector_path_count = len(page.get_drawings())

    area = width_pt * height_pt
    # "rotated" is a plansheet signal only alongside SOME page content
    # (char_count >= the tier-C floor). A page rotation flag on an
    # otherwise blank/all-image scanned page is overwhelmingly just a
    # scanner orientation artifact (a whole scanned application carried at
    # /Rotate 270 because it was fed sideways), not evidence of an
    # oversized engineering drawing -- and the task brief's own real-file
    # ground truth requires such a page to triage as C (scan), not D. A
    # rotated page that ALSO carries real text (a title block, notes) is a
    # much stronger plansheet signal and keeps triggering D.
    is_plansheet = (
        area > _TABLOID_AREA_PT2
        or vector_path_count >= _HIGH_VECTOR_DENSITY_THRESHOLD
        or (rotation != 0 and char_count >= _SCAN_TIER_MAX_CHARS)
    )
    labeled = has_label_tokens(text)
    tier = _classify_tier(char_count, labeled, is_plansheet)
    page_sha256 = _render_page_sha256(page)

    return PageCensus(
        page_number=page_number,
        char_count=char_count,
        image_count=image_count,
        rotation=rotation,
        width_pt=width_pt,
        height_pt=height_pt,
        vector_path_count=vector_path_count,
        has_label_tokens=labeled,
        is_plansheet=is_plansheet,
        tier=tier,
        page_sha256=page_sha256,
    )


def triage_pdf(path: str | Path) -> list[PageCensus]:
    """Open the PDF at `path` and return one PageCensus per page, 1-indexed
    in document order. Read-only -- never mutates the source file.

    Raises UnreadablePdf if the file cannot be opened as a PDF at all (a
    caller should treat this as a validation failure and write nothing --
    CONTRACT.md §1.1 S1 -- rather than a partial/empty triage result).
    """
    try:
        doc = fitz.open(str(path))
    except Exception as exc:  # noqa: BLE001 -- fitz raises its own exception types
        raise UnreadablePdf(f"{path}: {type(exc).__name__}: {exc}") from exc
    try:
        if doc.page_count == 0:
            raise UnreadablePdf(f"{path}: PDF has zero pages")
        return [census_page(doc[i], page_number=i + 1) for i in range(doc.page_count)]
    finally:
        doc.close()


def tier_census(pages: list[PageCensus]) -> dict[str, int]:
    """{"A": n, "B": n, "C": n, "D": n} counts over `pages`."""
    counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for p in pages:
        counts[p.tier] += 1
    return counts


def any_plansheet(pages: list[PageCensus]) -> bool:
    """True if any page triaged to tier D -- the signal that forces the
    owning document's source_priority to 100 (app/routes/documents.py)."""
    return any(p.tier == "D" for p in pages)
