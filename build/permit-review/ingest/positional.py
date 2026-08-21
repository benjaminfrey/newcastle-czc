"""ingest/positional.py -- Tier B positional field extraction (the trap).

Implements this workflow's (W4) task brief, "THE TIER B TRAP (real, in the
Stantec packet pp.9-12)": a page that is a SCANNED IMAGE of the Gen-1 form
with the applicant's typed answers laid over it as real text objects.
Native extraction (ingest/native.py) returns VALUES WITH NO LABELS -- the
label text lives only in the scanned image's pixels, never in the PDF's
text layer, so ingest/native.py's label-text search (_find_label) finds
NOTHING for every field, by construction, on a page like this.

This module therefore does NOT search for labels at all. It matches VALUE
spans POSITIONALLY against ingest.native.GEN1_FIELD_MAP's `ref_anchor`
coordinates -- the exact (x, y) each label was measured at on a real,
filled, NATIVE Gen-1 page (Profenno pp.5-8) -- using the SAME relative
value_dx/value_dy windows native.py already declares per field. Reusing one
declared field map for both tiers (rather than a second, independently
hand-tuned map) is deliberate: it is the single source of truth for "where
does this field's value sit on a Gen-1 page", proven once against a native
page with real labels to check it against, then applied unchanged to a page
that has no labels left to check against at all.

Confidence-gated (POSITIONAL_MIN_CONFIDENCE): GEN1_FIELD_MAP fields below
0.7 confidence (compound multi-blank rows this workflow could never
calibrate against a real filled value -- Setbacks front/side/rear, building
Width/Depth/Stories, unit counts, footprint/total-area -- see that map's own
comment) are SKIPPED here entirely, never attempted, regardless of what
text happens to sit in their window. On a label-less page there is no way
for a human OR this code to double-check an uncalibrated position, so
CONTRACT.md's "never guess a legal or dimensional value" applies at full
force: those fields are reported unparseable and pushed to the worklist,
never emitted as a low-confidence guess.

A page contributes ZERO candidates whenever NOTHING in ANY confident
field's window has text -- that page is reported wholly unparseable
(`PositionalExtractionResult.parseable = False`). This is the explicit
"OR is declared unparseable" branch the task brief allows; it is not an
error, it is the honest outcome for e.g. an office-use-only admin page or a
page of bare checkboxes, neither of which this field map covers at all.

Rotation handling: the Stantec fixture's trap pages are stored /Rotate 90
or /Rotate 270 (a sideways-fed scan). PyMuPDF's dict-mode span bboxes are
reported in the page's UNROTATED content-stream space, which is NOT the
same coordinate system GEN1_FIELD_MAP's ref_anchor values were measured in
(a normally-oriented, /Rotate 0 native page). `rotated_page_spans()` applies
`page.rotation_matrix` to every span bbox first, so downstream matching
always happens in the same DISPLAY-oriented coordinate space the reference
anchors use, regardless of the source page's stored rotation.
"""

from __future__ import annotations

from dataclasses import dataclass

import fitz

import re

from ingest.fields import FieldCandidate, normalize_label, parse_numeric, strip_placeholder
from ingest.native import GEN1_FIELD_MAP, FieldSpec

POSITIONAL_MIN_CONFIDENCE = 0.7

# A positional-only match has no label text to confirm it against (unlike
# native.py, where a human reviewer sees the printed label right next to
# the value on the page). Every candidate's own confidence is discounted
# accordingly so it never outranks an equal-or-lower-tier NATIVE match in
# ingest/fields.py's merge rules.
_POSITIONAL_CONFIDENCE_DISCOUNT = 0.85


def rotated_page_spans(page: "fitz.Page") -> list[dict]:
    """Every non-blank text span on `page`, transformed into the page's
    DISPLAY-oriented coordinate space via `page.rotation_matrix` -- i.e.
    the same space a normally-stored (/Rotate 0) page's spans are already
    in, and the same space ingest.native.GEN1_FIELD_MAP's ref_anchor
    values were measured in."""
    M = page.rotation_matrix
    out = []
    for blk in page.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                if sp["text"].strip() == "":
                    continue
                r = fitz.Rect(sp["bbox"]) * M
                out.append(dict(x=round(r.x0, 1), y=round(r.y0, 1), x1=round(r.x1, 1), y1=round(r.y1, 1), t=sp["text"]))
    return out


@dataclass(frozen=True)
class PositionalExtractionResult:
    page_no: int
    parseable: bool
    candidates: tuple[FieldCandidate, ...]
    unparseable_field_keys: tuple[str, ...]  # confident-map fields with no value found here
    low_confidence_field_keys: tuple[str, ...]  # below POSITIONAL_MIN_CONFIDENCE, never attempted
    note: str


def extract_gen1_positional(
    page: "fitz.Page",
    *,
    page_no: int,
    document_id: str | None = None,
    source_priority: int = 40,
    field_map: list[FieldSpec] = GEN1_FIELD_MAP,
    min_confidence: float = POSITIONAL_MIN_CONFIDENCE,
) -> PositionalExtractionResult:
    """Positionally match `page` (a Tier-B "values with no labels" Gen-1
    page) against `field_map`'s reference anchors. NEVER emits a candidate
    for a bare, unattributed value -- every candidate produced here carries
    a real field_key, bbox, and a rationale naming which reference anchor
    it was matched against; a span that doesn't land inside any confident
    field's window is simply never touched, exactly as on a native page.
    """
    spans = rotated_page_spans(page)
    low_confidence = [s.field_key for s in field_map if s.confidence < min_confidence]
    confident = [s for s in field_map if s.confidence >= min_confidence and s.ref_anchor is not None]

    candidates: list[FieldCandidate] = []
    unparseable: list[str] = []
    for spec in confident:
        ax, ay = spec.ref_anchor  # type: ignore[misc]
        xlo, xhi = ax + spec.value_dx[0], ax + spec.value_dx[1]
        ylo, yhi = ay + spec.value_dy[0], ay + spec.value_dy[1]
        picked = [s for s in spans if xlo <= s["x"] < xhi and ylo <= s["y"] <= yhi]
        if not picked:
            unparseable.append(spec.field_key)
            continue
        picked.sort(key=lambda s: (round(s["y"]), s["x"]))
        joined_raw = " ".join(s["t"] for s in picked)
        for boilerplate in spec.strip_texts:
            joined_raw = re.sub(re.escape(boilerplate), "", joined_raw, flags=re.IGNORECASE)
        raw = strip_placeholder(joined_raw)
        if not raw:
            unparseable.append(spec.field_key)
            continue
        if spec.numeric:
            value_num, unit, value_text = parse_numeric(raw, spec.unit)
            value_norm: float | str = value_num if value_num is not None else value_text
        else:
            unit = spec.unit
            value_norm = normalize_label(raw)
        bbox = (
            min(s["x"] for s in picked),
            min(s["y"] for s in picked),
            max(s["x1"] for s in picked),
            max(s["y1"] for s in picked),
        )
        candidates.append(
            FieldCandidate(
                field_key=spec.field_key,
                value_raw=raw,
                value_norm=value_norm,
                unit=unit,
                document_id=document_id,
                page_no=page_no,
                bbox=bbox,
                method="table",  # positional/geometric match -- no label text on this page at all
                confidence=round(spec.confidence * _POSITIONAL_CONFIDENCE_DISCOUNT, 3),
                rationale=(
                    f"POSITIONAL match (no label text on this page -- image+overlay): "
                    f"value found at ~({bbox[0]:.1f},{bbox[1]:.1f}) inside the reference window "
                    f"for {spec.field_key!r}, anchored to the label position measured on a real "
                    f"native Gen-1 page (Profenno pp.5-8) at ~({ax:.1f},{ay:.1f})."
                ),
                source_priority=source_priority,
            )
        )

    parseable = len(candidates) > 0
    if parseable:
        note = (
            f"{len(candidates)} field(s) positionally matched with confidence >= "
            f"{min_confidence}; {len(unparseable)} confident field(s) had no value in their "
            f"window on this page; {len(low_confidence)} field(s) skipped as too low-"
            "confidence to trust without a label to confirm against."
        )
    else:
        note = (
            "No confident field produced a value on this page -- declared UNPARSEABLE. "
            "Every field on it belongs on the operator worklist."
        )
    return PositionalExtractionResult(
        page_no=page_no,
        parseable=parseable,
        candidates=tuple(candidates),
        unparseable_field_keys=tuple(unparseable),
        low_confidence_field_keys=tuple(low_confidence),
        note=note,
    )
