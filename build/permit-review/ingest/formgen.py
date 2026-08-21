"""ingest/formgen.py — form-generation + module-set detection.

Implements this workflow's (W4) task brief: "Form-generation and module-set
detection ... runs BEFORE any field extraction." Also implements the
CONTRACT.md §2 `ingest/` scope this belongs to (the sibling of
ingest/triage.py's "PDF page split, text/vision extraction" — this module
does the "which of the two known form layouts is this" half).

NO LLM. NO vision model. NO OCR of handwriting or of any applicant-filled
field value — only two things are ever read here, and only from a small,
fixed set of pages:

    1. the PDF's own embedded (selectable) text layer, wherever it exists
       in the document, searched for two literal, printed, STATIC fingerprint
       strings the town's own form layouts carry (never an applicant's typed
       answer); and
    2. for a document with NO usable text layer anywhere (a pure scan), a
       light OCR pass restricted to the TOP and BOTTOM bands of the first
       few pages only -- printed banner titles / footer version stamps,
       which the task brief itself notes "survive OCR far better than
       handwriting." Tier C/D pages are triaged (ingest/triage.py, W3) but
       this module never reads a field VALUE off one -- it only asks "does
       this narrow band contain one of two known, static, printed strings?"

Detection never guesses. `detect_generation()` returns generation="unknown"
whenever neither fingerprint is found, and UNKNOWN GENERATION MUST FAIL
LOUDLY at the case level (a separate, concurrently-built consumer's job --
see the module docstring's "Scope" note below): this module's own
contribution to that is simply to never default to 'gen1' when it isn't
sure (CONTRACT.md §1 S7 -- no silent guessing).

Scope: this file owns per-DOCUMENT detection (detect_generation()) and the
module-set -> review-type hint (derive_review_type(),
cross_check_review_type()). It does NOT own:
  - the case-level rollup across a case's several documents (that is
    app/extraction.py's not-yet-built case_form_generation(), which this
    module's persist_formgen_result() feeds by writing the per-document
    columns 0009_document_formgen.sql adds);
  - Tier A/B FIELD VALUE extraction (a separate task in this same
    workflow);
  - the operator confirm UI (app/routes/extraction.py).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

# --------------------------------------------------------------------------- #
# Fingerprints — the task brief's own ground truth, verbatim.
# --------------------------------------------------------------------------- #

# GEN-1's reliable fingerprint: a literal typo ("ADMINSTRATION", missing the
# second "I") baked into the printed form itself. Matched case-insensitively
# (a scanned copy's OCR transcription can vary in case) but the MISSPELLING
# itself is required -- this is deliberately NOT "OFFICE ADMIN.{0,2}STRATION"
# or some other fuzzy pattern, because the task brief is explicit that the
# typo, not the general phrase, is what makes this fingerprint reliable
# (a hypothetical corrected reprint of the same form would no longer carry
# it, and should not be assumed to be either generation from this alone).
_GEN1_FINGERPRINT_RE = re.compile(
    r"OFFICE\s+ADMINSTRATION\s+USE\s+ONLY", re.IGNORECASE
)

# A softer, SECONDARY Gen-1 signal: the form's own plain title, which can
# appear elsewhere in a larger submission packet (e.g. a consultant's cover
# letter naming what it has attached: "ATTACHMENT A: ZONING PERMIT
# APPLICATION FORM" -- verified against the real Stantec packet, where the
# actual fingerprint page is an image with no selectable text at all, but
# page 8's cover-letter table of contents names the attachment in plain
# text). Whitespace/newlines are normalized before matching so a title that
# wrapped across two lines in the source ("Zoning Permit\nApplication",
# verified against the real Blood & Sons / Academy Hill OCR transcriptions)
# still matches. This alone is NOT treated as equal-strength evidence to the
# typo'd fingerprint -- see _classify_gen1_evidence below.
_GEN1_TITLE_RE = re.compile(r"ZONING\s+PERMIT\s+APPLICATION", re.IGNORECASE)

# GEN-2's fingerprint: the "PLANNING APPLICATION" cover-sheet title plus a
# footer version stamp `v.YYYY.MM.DD` (observed: v.2024.09.26).
_GEN2_TITLE_RE = re.compile(r"PLANNING\s+APPLICATION", re.IGNORECASE)
# Case-insensitive on the leading 'v' only: verified native (Morrissey:
# "v.2024.09.26") AND OCR'd (Dalton's footer band reads "V.2024.09.26",
# tesseract capitalizing the lone letter) both need to match — the
# YYYY.MM.DD portion itself is digits/dots and carries no case ambiguity.
_VERSION_STAMP_RE = re.compile(r"[vV]\.\d{4}\.\d{2}\.\d{2}")

# The seven GEN-2 a-la-carte module titles (task brief, verbatim) -> the
# module_key vocabulary the task brief's own worked example uses
# ("{cover, subdivision_form} -> subdivision / Planning Board").
MODULE_TITLES: dict[str, str] = {
    "Cover Sheet": "cover",
    "Subdivision Form": "subdivision_form",
    "Use Form": "use_form",
    "Shoreland Zoning Form": "shoreland_form",
    "Building Form": "building_form",
    "Components Section": "components",
    "Other Structures Form": "other_structures",
}
_MODULE_TITLE_PATTERNS: dict[str, re.Pattern[str]] = {
    key: re.compile(r"\b" + r"\s+".join(re.escape(w) for w in title.split()) + r"\b", re.IGNORECASE)
    for title, key in MODULE_TITLES.items()
}

# --------------------------------------------------------------------------- #
# Header/footer-band OCR — the pure-scan fallback ONLY. Bounded to the first
# few pages (generation fingerprint) and a slightly larger, still-small page
# cap for module-title continuation (verified against the real Dalton
# fixture: its "Components Section" module title sits on page 4, past the
# generation-detection window but still well within a single a-la-carte
# form packet's realistic length -- see the real-fixture tests below).
# --------------------------------------------------------------------------- #

_GENERATION_OCR_PAGE_CAP = 3
_MODULE_OCR_PAGE_CAP = 8

# Fractions of page HEIGHT, in the page's own (already-rotated) display
# coordinate space -- fitz.Page.get_pixmap(clip=...) accepts a clip rect in
# that same space, verified empirically against the real (rotated 90/270)
# scanned fixtures: a plain top/bottom slice of page.rect, NOT the
# pre-rotation mediabox, lands on the visually-correct band every time.
_HEADER_BAND_FRACTION = 0.20
_FOOTER_BAND_FRACTION = 0.15

# A whole document below this total native-text character count (summed
# across every page) is treated as a pure scan with no usable text layer
# anywhere -- the OCR fallback path. Real pure-scan fixtures (Blood & Sons,
# Academy Hill, Shattuck, Verney, Dalton) all measure exactly 0; a generous
# margin above that still safely excludes every "Mixed" fixture (Profenno,
# Stantec), both of which carry thousands of native characters on their
# early pages alone.
_PURE_SCAN_TOTAL_CHAR_THRESHOLD = 50

_OCR_ZOOM = 3.0  # ~216 DPI at Letter size -- matches ingest/triage.py's own
# "cheap, deterministic" posture; verified sufficient for tesseract to read
# these forms' printed banner text in the exploration behind this module.


class OcrUnavailable(RuntimeError):
    """The `tesseract` binary is not on PATH. Not a bug -- detect_generation()
    catches this and degrades to generation='unknown' (CONTRACT.md §1 S7:
    an honest "cannot determine," never a guess, and never a crash)."""


def _tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _ocr_band(page: "fitz.Page", *, top: float, bottom: float) -> str:
    """OCR the horizontal band [top, bottom) of `page` (fractions of page
    height, in the page's own already-rotated display coordinate space) and
    return whatever text tesseract reads. Raises OcrUnavailable if the
    `tesseract` binary is not present -- never silently returns empty text,
    which a caller could otherwise mistake for "band was blank."

    PNG bytes are piped to tesseract over stdin/stdout (`tesseract - stdout`)
    -- no temp file is ever written to disk for this (CONTRACT.md §1.1 S5:
    every writer routes through app/paths.py:safe_path(), which this
    deliberately never needs to, because it writes nothing at all).
    """
    if not _tesseract_available():
        raise OcrUnavailable("the `tesseract` binary is not on PATH")

    band = fitz.Rect(0, page.rect.height * top, page.rect.width, page.rect.height * bottom)
    pix = page.get_pixmap(matrix=fitz.Matrix(_OCR_ZOOM, _OCR_ZOOM), clip=band)
    png_bytes = pix.tobytes("png")

    result = subprocess.run(
        ["tesseract", "-", "stdout"],
        input=png_bytes,
        capture_output=True,
        timeout=30,
    )
    return (result.stdout or b"").decode("utf-8", errors="replace")


def _normalize_ws(text: str) -> str:
    """Collapse newlines/runs of whitespace to single spaces so a title that
    happened to wrap across lines in the source (native OR OCR'd) still
    matches a single-line pattern. NFKC-normalizes first so OCR's occasional
    stray combining/soft-hyphen characters don't defeat a match."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


# --------------------------------------------------------------------------- #
# Evidence records + the result shape.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Evidence:
    page: int  # 1-based
    signal: str  # 'gen1_fingerprint' | 'gen1_title' | 'gen2_title' | 'version_stamp' | 'module_title'
    matched: str  # the exact matched (or OCR'd) substring
    source: str  # 'native_text' | 'ocr_header_band' | 'ocr_footer_band'
    detail: str | None = None  # e.g. the module_key, for a 'module_title' signal

    def as_dict(self) -> dict[str, Any]:
        d = {"page": self.page, "signal": self.signal, "matched": self.matched, "source": self.source}
        if self.detail is not None:
            d["detail"] = self.detail
        return d


@dataclass(frozen=True)
class FormGenResult:
    generation: str  # 'gen1' | 'gen2' | 'unknown'
    confidence: str  # 'high' | 'medium' | 'low'
    evidence: list[Evidence] = field(default_factory=list)
    version_stamp: str | None = None
    modules: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "confidence": self.confidence,
            "evidence": [e.as_dict() for e in self.evidence],
            "version_stamp": self.version_stamp,
            "modules": list(self.modules),
        }


def _unknown(evidence: list[Evidence]) -> FormGenResult:
    return FormGenResult(generation="unknown", confidence="low", evidence=evidence, version_stamp=None, modules=[])


# --------------------------------------------------------------------------- #
# Native-text pass — cheap (no OCR), runs across the WHOLE document. This is
# what resolves the real Profenno fixture (fingerprint on native page 6 of
# 25, nowhere near the first 3 pages) and the real Stantec fixture (no
# literal fingerprint anywhere in the text layer -- its one occurrence is
# baked into a scanned image on page 10 -- but the secondary title phrase
# IS present, in plain native text, on page 8's own cover-letter table of
# contents: "ATTACHMENT A: ZONING PERMIT APPLICATION FORM").
# --------------------------------------------------------------------------- #


def _scan_native_text(doc: "fitz.Document") -> tuple[list[Evidence], int]:
    """Returns (evidence found across every page's native text, total native
    char count across every page) -- the latter is also this module's "is
    this a pure scan" signal (see _PURE_SCAN_TOTAL_CHAR_THRESHOLD)."""
    evidence: list[Evidence] = []
    total_chars = 0
    for i in range(doc.page_count):
        raw = doc[i].get_text("text") or ""
        total_chars += len(raw)
        if not raw:
            continue
        text = _normalize_ws(raw)

        m = _GEN1_FINGERPRINT_RE.search(text)
        if m:
            evidence.append(Evidence(i + 1, "gen1_fingerprint", m.group(), "native_text"))
            continue  # the strong signal on this page subsumes the soft one

        m = _GEN1_TITLE_RE.search(text)
        if m:
            evidence.append(Evidence(i + 1, "gen1_title", m.group(), "native_text"))

        m = _GEN2_TITLE_RE.search(text)
        if m:
            evidence.append(Evidence(i + 1, "gen2_title", m.group(), "native_text"))

        m = _VERSION_STAMP_RE.search(raw)  # not whitespace-normalized: '.'/digits only
        if m:
            evidence.append(Evidence(i + 1, "version_stamp", m.group(), "native_text"))

        for title_key, pattern in _MODULE_TITLE_PATTERNS.items():
            mm = pattern.search(text)
            if mm:
                evidence.append(Evidence(i + 1, "module_title", mm.group(), "native_text", detail=title_key))

    return evidence, total_chars


# --------------------------------------------------------------------------- #
# OCR pass — pure-scan fallback only. Header+footer bands of the first
# _GENERATION_OCR_PAGE_CAP pages for the generation fingerprints/version
# stamp; header band only, out to _MODULE_OCR_PAGE_CAP pages, for module
# titles (real fixtures put every module title flush at a page top — see
# this module's docstring / the exploration this was verified against).
# --------------------------------------------------------------------------- #


def _scan_ocr_bands(doc: "fitz.Document") -> list[Evidence]:
    evidence: list[Evidence] = []
    generation_pages = min(doc.page_count, _GENERATION_OCR_PAGE_CAP)
    module_pages = min(doc.page_count, _MODULE_OCR_PAGE_CAP)

    for i in range(module_pages):
        page = doc[i]
        header_raw = _ocr_band(page, top=0.0, bottom=_HEADER_BAND_FRACTION)
        header = _normalize_ws(header_raw)

        if i < generation_pages:
            m = _GEN1_FINGERPRINT_RE.search(header)
            if m:
                evidence.append(Evidence(i + 1, "gen1_fingerprint", m.group(), "ocr_header_band"))
            else:
                m = _GEN1_TITLE_RE.search(header)
                if m:
                    evidence.append(Evidence(i + 1, "gen1_title", m.group(), "ocr_header_band"))

            m = _GEN2_TITLE_RE.search(header)
            if m:
                evidence.append(Evidence(i + 1, "gen2_title", m.group(), "ocr_header_band"))

        for title_key, pattern in _MODULE_TITLE_PATTERNS.items():
            mm = pattern.search(header)
            if mm:
                evidence.append(Evidence(i + 1, "module_title", mm.group(), "ocr_header_band", detail=title_key))

    for i in range(generation_pages):
        page = doc[i]
        footer_raw = _ocr_band(page, top=1.0 - _FOOTER_BAND_FRACTION, bottom=1.0)
        m = _VERSION_STAMP_RE.search(footer_raw)
        if m:
            evidence.append(Evidence(i + 1, "version_stamp", m.group(), "ocr_footer_band"))

    return evidence


# --------------------------------------------------------------------------- #
# Classification — turns a flat evidence list into the FormGenResult.
# --------------------------------------------------------------------------- #


def _classify(evidence: list[Evidence]) -> FormGenResult:
    gen1_fp = [e for e in evidence if e.signal == "gen1_fingerprint"]
    gen1_title = [e for e in evidence if e.signal == "gen1_title"]
    gen2_title = [e for e in evidence if e.signal == "gen2_title"]
    version_stamps = [e for e in evidence if e.signal == "version_stamp"]
    module_hits = [e for e in evidence if e.signal == "module_title"]

    if gen1_fp:
        # The literal typo'd fingerprint is decisive on its own — the task
        # brief's own framing ("that typo is the reliable fingerprint").
        supporting = gen1_fp + gen1_title
        return FormGenResult("gen1", "high", supporting, version_stamp=None, modules=[])

    if gen2_title:
        modules = sorted({e.detail for e in module_hits if e.detail})
        vs = version_stamps[0].matched if version_stamps else None
        confidence = "high" if version_stamps else "medium"
        supporting = gen2_title + version_stamps + module_hits
        return FormGenResult("gen2", confidence, supporting, version_stamp=vs, modules=modules)

    if gen1_title:
        # Corroborating-only: the form's plain title appeared (e.g. a cover
        # letter naming an attachment) but the specific typo'd fingerprint
        # was never found — real Stantec fixture shape. Honest medium
        # confidence, not the full "high" the typo itself would earn.
        return FormGenResult("gen1", "medium", gen1_title, version_stamp=None, modules=[])

    return _unknown(evidence)


# --------------------------------------------------------------------------- #
# The public entry point.
# --------------------------------------------------------------------------- #


def detect_generation(document: str | Path) -> dict[str, Any]:
    """Detect which Newcastle permit-application form generation `document`
    (a path to a PDF file) is, and, for a Gen-2 document, which a-la-carte
    modules it carries.

    Returns a JSON-serializable dict:
        {"generation": "gen1"|"gen2"|"unknown",
         "confidence": "high"|"medium"|"low",
         "evidence": [{"page":int,"signal":str,"matched":str,"source":str,...}],
         "version_stamp": str|None,
         "modules": [str, ...]}

    Strategy, in order:
      1. Native text layer, across the WHOLE document (cheap — no OCR).
         Resolves any document that has a usable text layer anywhere,
         including a Gen-1 form embedded mid-packet (Profenno: fingerprint
         on native page 6 of 25) and a document where only a SECONDARY,
         corroborating signal survives natively even though the primary
         fingerprint itself is trapped inside a scanned image elsewhere in
         the same packet (Stantec).
      2. If nothing was found AND the document's native text is negligible
         everywhere (a pure scan — CONTRACT.md task brief: "the text layer
         is empty"), fall back to a light header/footer-band OCR pass
         bounded to the first few pages (generation fingerprint + version
         stamp) and a slightly larger page cap (module-title continuation).
         This is the one place this module reads a Tier C/D page at all,
         and it never reads anything but a printed banner title / footer
         stamp in a narrow band — never a field value, never handwriting.
      3. If still nothing decisive — including because `tesseract` is not
         installed — returns generation="unknown". This is a CORRECT
         answer per the task brief, not a failure, and this function NEVER
         falls back to assuming 'gen1' for an undetermined document
         (a genuinely unseen third generation must also resolve here, and
         it does, precisely because nothing about this function's logic
         defaults to gen1 — it only returns gen1 when actual gen1 evidence
         was found).
    """
    path = Path(document)
    doc = fitz.open(str(path))
    try:
        if doc.page_count == 0:
            return _unknown([]).as_dict()

        native_evidence, total_native_chars = _scan_native_text(doc)
        result = _classify(native_evidence)
        if result.generation != "unknown":
            return result.as_dict()

        if total_native_chars >= _PURE_SCAN_TOTAL_CHAR_THRESHOLD:
            # Real, substantial text exists somewhere in this document, but
            # none of it matched either fingerprint — an honest "unknown,"
            # not a reason to start reading Tier C/D image content that the
            # task brief reserves for a later, vision-owning workflow.
            return result.as_dict()

        try:
            ocr_evidence = _scan_ocr_bands(doc)
        except OcrUnavailable as exc:
            note = Evidence(0, "ocr_unavailable", str(exc), "ocr_header_band")
            return _unknown([note]).as_dict()

        return _classify(ocr_evidence).as_dict()
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
# Module-set -> review-type hint + the reviews.py cross-check.
#
# "THE MODULE SET GIVES THE REVIEW TYPE FOR FREE" — but only for the ONE
# combination the task brief hands us as verified ground truth:
# {cover, subdivision_form} -> subdivision / Planning Board (Article 12
# subdivision review is always a Planning Board track; presence of the
# Subdivision Form module settles it on its own). Every other module
# combination in the real fixture set turns on WHICH USE or WHICH DISTRICT
# is involved — a fact this module has no data for (it reads PDFs, not the
# use-matrix) — so those return an UNRESOLVED hint naming what still needs
# checking, rather than a guessed authority (CONTRACT.md §1 S7).
# --------------------------------------------------------------------------- #

# cases.application_type's CHECK vocabulary (0002_case_tracking.sql) — the
# hint's application_type is always one of these, never a made-up value.
_SUBDIVISION_MODULES = frozenset({"subdivision_form"})
_USE_MODULES = frozenset({"use_form"})
_SHORELAND_MODULES = frozenset({"shoreland_form"})


@dataclass(frozen=True)
class ReviewTypeHint:
    application_type: str | None  # a cases.application_type value, or None if wholly unresolved
    authority: str | None  # 'CEO' | 'Planning Board' | None
    basis: str
    needs_use_matrix_check: bool
    supplementary_modules: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "application_type": self.application_type,
            "authority": self.authority,
            "basis": self.basis,
            "needs_use_matrix_check": self.needs_use_matrix_check,
            "supplementary_modules": list(self.supplementary_modules),
        }


def derive_review_type(generation: str, modules: list[str]) -> dict[str, Any]:
    """The module-set -> review-type hint (task brief: "the module set gives
    the review type for free"). Gen-1 has no module concept (a fixed,
    non-modular form) — its review type instead comes from the form's own
    DEVELOPMENT REVIEW TYPE checkboxes (a Tier A/B field-extraction concern,
    not this module's), so this always returns an unresolved hint for
    generation != 'gen2'.

    NEVER returns a guessed authority. Only the one combination the task
    brief hands us as verified ground truth resolves authority outright;
    every other real module combination returns needs_use_matrix_check=True
    naming what cross_check_review_type() needs to settle it once a case's
    District + Use are known (from field extraction, out of this module's
    scope).
    """
    mods = frozenset(modules)

    if generation != "gen2" or not mods:
        return ReviewTypeHint(
            application_type=None,
            authority=None,
            basis="not a Gen-2 module set — no module-derived review-type hint applies",
            needs_use_matrix_check=False,
        ).as_dict()

    supplementary = sorted(m for m in mods if m not in {"cover"})

    if _SUBDIVISION_MODULES <= mods:
        return ReviewTypeHint(
            application_type="subdivision",
            authority="Planning Board",
            basis=(
                "the Subdivision Form module is present — Article 12 subdivision review "
                "is a Planning Board track regardless of District or Use (task brief "
                "ground truth: '{cover, subdivision_form} -> subdivision / Planning Board')"
            ),
            needs_use_matrix_check=False,
            supplementary_modules=[m for m in supplementary if m != "subdivision_form"],
        ).as_dict()

    if _USE_MODULES <= mods:
        return ReviewTypeHint(
            application_type="use",
            authority=None,
            basis=(
                "the Use Form module is present, establishing a Use Permit review — but "
                "WHICH authority (CEO vs Planning Board) depends on the specific District "
                "+ Use, per the Article 2 use-status legend (CONTRACT.md §4.4). Not "
                "decidable from the module set alone."
            ),
            needs_use_matrix_check=True,
            supplementary_modules=[m for m in supplementary if m != "use_form"],
        ).as_dict()

    if _SHORELAND_MODULES <= mods:
        return ReviewTypeHint(
            application_type="shoreland",
            authority=None,
            basis=(
                "the Shoreland Zoning Form module is present ('Required for all work done "
                "within the Shoreland Zone'), establishing that Shoreland Zoning review "
                "applies — but the issuing authority is not derivable from the module set "
                "alone (this module has no Shoreland-administration data; the Article 2 "
                "use-matrix this app loads covers the base Use, not the Shoreland overlay)."
            ),
            needs_use_matrix_check=True,
            supplementary_modules=[m for m in supplementary if m != "shoreland_form"],
        ).as_dict()

    # A module set with only supplementary/structural modules (building_form,
    # other_structures, components) and no primary driver present at all.
    return ReviewTypeHint(
        application_type=None,
        authority=None,
        basis=(
            f"module set {sorted(mods)!r} carries no recognized primary review-driving "
            "module (subdivision_form / use_form / shoreland_form) — cannot derive a "
            "review type from the module set alone"
        ),
        needs_use_matrix_check=True,
        supplementary_modules=supplementary,
    ).as_dict()


def cross_check_review_type(
    module_hint: dict[str, Any],
    *,
    district_key: str | None,
    use_key: str | None,
    ruleset_key: str = "adopted",
) -> dict[str, Any]:
    """Cross-check a derive_review_type() hint against the ACTUAL required
    review from app.reviews.required_reviews() (CONTRACT.md §4.4, the
    use-status legend) once a case's District + Use are known.

    Returns one of three shapes, never silently preferring one derivation
    over the other when they disagree:

        {"status": "insufficient_data", ...}
            district_key or use_key is None (not yet extracted/confirmed),
            OR the module hint itself was unresolved (needs_use_matrix_check
            AND application_type is None) with nothing to compare against
            yet. No comparison was possible.

        {"status": "agree", "module_derivation": ..., "use_matrix_derivation": ...}
            Both derivations name the same permitting authority.

        {"status": "disagree", "module_derivation": ..., "use_matrix_derivation": ...,
         "needs_operator_resolution": True}
            They name different authorities (or the module hint asserted an
            authority the use-matrix contradicts). BOTH are returned in
            full — this function never picks a winner (CONTRACT.md §1 S7).

    Raises nothing of app.reviews' own (UnknownDistrict/UnknownUse) — those
    propagate to the caller, which already has better context (the actual
    case) to decide how to surface a bad district_key/use_key.
    """
    if district_key is None or use_key is None:
        return {
            "status": "insufficient_data",
            "reason": "district_key and use_key are both required to look up the actual "
            "required review (CONTRACT.md §4.4); at least one is not yet known",
            "module_derivation": module_hint,
            "use_matrix_derivation": None,
        }

    from app import reviews  # deferred: keeps this module importable with no app/ dependency

    rows = reviews.required_reviews(district_key, use_key, ruleset_key=ruleset_key)
    use_matrix_row = rows[0]
    use_matrix_derivation = {
        "application_type": None,  # reviews.py has no cases.application_type concept
        "authority": use_matrix_row["permitting_authority"],
        "permit": use_matrix_row["permit"],
        "basis": use_matrix_row["applicability_text"],
    }

    module_authority = module_hint.get("authority")
    if module_authority is None:
        return {
            "status": "insufficient_data",
            "reason": "the module-derived hint did not resolve an authority on its own "
            "(needs_use_matrix_check); this cross-check now SUPPLIES the missing "
            "authority from the use-matrix rather than comparing two guesses",
            "module_derivation": module_hint,
            "use_matrix_derivation": use_matrix_derivation,
        }

    agrees = module_authority == use_matrix_derivation["authority"]
    return {
        "status": "agree" if agrees else "disagree",
        "module_derivation": module_hint,
        "use_matrix_derivation": use_matrix_derivation,
        **({"needs_operator_resolution": True} if not agrees else {}),
    }


# --------------------------------------------------------------------------- #
# Persistence — writes detect_generation()'s result onto the owning
# documents row (0009_document_formgen.sql) and appends the audit event
# (CONTRACT.md §3.3 S9: every mutation appends an events row in the same
# transaction as the write it records).
# --------------------------------------------------------------------------- #


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def persist_formgen_result(
    conn: Any,
    *,
    document_id: str,
    case_id: str,
    result: dict[str, Any],
    actor_user_id: str | None,
) -> None:
    """UPDATE documents SET generation=..., version_stamp=..., module_set=...,
    formgen_confidence=..., formgen_evidence_json=... WHERE id=?, plus an
    events row (kind='document.formgen_detected'). Caller owns the
    transaction (BEGIN/COMMIT) — this function issues no BEGIN/COMMIT of its
    own, matching app/routes/documents.py's own convention for a
    multi-statement write.
    """
    from app import audit  # deferred, same reasoning as the reviews import above

    module_set_json = json.dumps(sorted(result.get("modules", [])), separators=(",", ":"))
    evidence_json = json.dumps(result.get("evidence", []), separators=(",", ":"))

    conn.execute(
        """
        UPDATE documents
        SET generation = ?, version_stamp = ?, module_set = ?,
            formgen_confidence = ?, formgen_evidence_json = ?
        WHERE id = ?;
        """,
        (
            result["generation"],
            result.get("version_stamp"),
            module_set_json,
            result["confidence"],
            evidence_json,
            document_id,
        ),
    )

    audit.append_event(
        conn,
        actor_user_id=actor_user_id,
        kind="document.formgen_detected",
        case_id=case_id,
        entity_table="documents",
        entity_id=document_id,
        payload={
            "document_id": document_id,
            "generation": result["generation"],
            "confidence": result["confidence"],
            "version_stamp": result.get("version_stamp"),
            "modules": sorted(result.get("modules", [])),
        },
    )
