"""ingest/native.py -- Tier A native-text field extraction.

Implements this workflow's (W4) task brief, "Tier A/B field extraction"
(the Tier A half) plus form-generation detection needed to select the right
declared field map. Studies and reuses extract/verso.py's span-and-position
idiom verbatim: page.get_text("dict") -> spans carrying x/y/size/font,
label geometry measured FORENSICALLY off a real filled page, label/value
pairing by position (not by reading order, which the "Tier B trap" proves
unreliable even on some nominally-native pages -- see ingest/positional.py
and this module's own GEN1_FIELD_MAP comments).

Two form generations, two DIFFERENT declared field maps -- never ad-hoc
regex over the page's flat text:

    GEN1 "Zoning Permit Application"  (2024 filings)   -> GEN1_FIELD_MAP
    GEN2 "PLANNING APPLICATION" cover sheet (2025+)     -> GEN2_COVER_FIELD_MAP

detect_generation() uses the two literal fingerprints the task brief names:
GEN1's typo'd "OFFICE ADMINSTRATION USE ONLY", GEN2's "PLANNING APPLICATION"
title plus a v\\.\\d{4}\\.\\d{2}\\.\\d{2} footer version stamp. An
undetermined generation returns "unknown" -- per the task brief, "UNKNOWN
GENERATION MUST FAIL LOUDLY: every field to the worklist ... NEVER fall
back to Gen-1 parsing" -- this module never guesses a generation and never
runs one generation's field map against the other's page.

--------------------------------------------------------------------------
Canonical field_key vocabulary (generation-independent; both GEN1_FIELD_MAP
and GEN2_COVER_FIELD_MAP resolve to the SAME keys for the same real-world
fact, so ingest/fields.py's merge_all() can compare a Gen-1 form candidate
against a Gen-2 form candidate, or either against a future plan/survey
candidate, for the identical field):

    applicant.name / .email / .phone / .address
    owner.name / .email / .phone / .address
    parcel.tax_map / .lot / .deed_book / .deed_page
    parcel.street_address / .zoning_district / .special_district_name
    parcel.lot_size_acres / .lot_frontage_ft / .lot_width_ft / .lot_depth_ft
    project.existing_use / .proposed_use / .description
    building.footprint_sf / .total_area_sf / .width_ft / .depth_ft / .stories
    building.existing_units / .proposed_units
    setback.front_ft / .side_ft / .rear_ft

Checkbox/circle-one fields (Gen-1's "District (circle one)", every
Development-Review-Type / project-type checkbox) are deliberately NOT in
either map: a hand-drawn circle or an "X" in a checkbox is not text this
technique can read, and guessing a checked box from surrounding prose is
exactly the kind of guess this workflow exists to refuse. Those stay
Tier C/D worklist items for a later phase.
--------------------------------------------------------------------------
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import fitz

from ingest.fields import FieldCandidate, normalize_label, parse_numeric, strip_placeholder

# ---------------------------------------------------------------------------
# Generation detection
# ---------------------------------------------------------------------------

GEN1_TYPO_FINGERPRINT = "OFFICE ADMINSTRATION USE ONLY"  # verbatim typo, task brief
GEN2_TITLE_FINGERPRINT = "PLANNING APPLICATION"
GEN2_VERSION_RE = re.compile(r"v\.\d{4}\.\d{2}\.\d{2}")

GEN1 = "gen1"
GEN2 = "gen2"
UNKNOWN = "unknown"


def _doc_text(doc: fitz.Document) -> str:
    parts = []
    for i in range(doc.page_count):
        try:
            parts.append(doc[i].get_text("text") or "")
        except Exception:  # noqa: BLE001 -- a single bad page must not abort detection
            parts.append("")
    return "\n".join(parts)


def detect_generation(doc: fitz.Document) -> str:
    """Deterministic, text-layer-only. GEN1 fingerprint wins outright (it is
    unique to that template). GEN2 requires BOTH the title AND the version
    stamp, since "PLANNING APPLICATION" alone is too generic a phrase to
    trust by itself. Anything else -- including a pure scan with no text
    layer at all -- is UNKNOWN, which is the correct answer, not a failure
    (task brief, verbatim)."""
    text = _doc_text(doc)
    if GEN1_TYPO_FINGERPRINT in text:
        return GEN1
    if GEN2_TITLE_FINGERPRINT in text and GEN2_VERSION_RE.search(text):
        return GEN2
    return UNKNOWN


def find_gen1_form_page(doc: fitz.Document) -> int | None:
    """0-based index of the Gen-1 page-1-of-form (TAX MAP / CONTACT
    INFORMATION header block) -- may be any physical page number in a
    larger packet (Profenno: physical page 5 of 25)."""
    for i in range(doc.page_count):
        t = doc[i].get_text("text") or ""
        if "TAX MAP" in t and "CONTACT INFORMATION" in t:
            return i
    return None


def find_gen2_cover_page(doc: fitz.Document) -> int | None:
    """0-based index of the Gen-2 Cover Sheet module page."""
    for i in range(doc.page_count):
        t = doc[i].get_text("text") or ""
        if GEN2_TITLE_FINGERPRINT in t and "Cover Sheet" in t:
            return i
    return None


# ---------------------------------------------------------------------------
# Span geometry -- extract/verso.py's idiom, generalized (public: reused by
# ingest/positional.py, which builds its OWN rotation-corrected span list in
# the same shape and passes it through the same matching engine below).
# ---------------------------------------------------------------------------


def page_spans(page: "fitz.Page") -> list[dict]:
    """Every non-blank text span on `page` as {x, y, x1, y1, t}, already-
    rotated DISPLAY coordinates (PyMuPDF applies a page's own /Rotate to
    dict-mode bboxes when queried this way for an unrotated page -- 0
    rotation is a no-op transform, so this is safe for ordinary native
    pages; ingest/positional.py handles the ROTATED case explicitly, since
    those pages need the rotation matrix applied by hand -- see that
    module's docstring)."""
    out = []
    for blk in page.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                if sp["text"].strip() == "":
                    continue
                out.append(
                    dict(
                        x=round(sp["bbox"][0], 1),
                        y=round(sp["bbox"][1], 1),
                        x1=round(sp["bbox"][2], 1),
                        y1=round(sp["bbox"][3], 1),
                        t=sp["text"],
                    )
                )
    return out


def _lines(spans: list[dict], *, y_tol: float = 1.6) -> list[list[dict]]:
    """Cluster spans into visual lines by near-identical y (anchored to
    each line's FIRST span, not chained -- see this module's own notes:
    chained clustering over-merges two genuinely different lines whose
    consecutive y-gaps are each individually small, which the real Gen-1
    two-column CONTACT INFORMATION block requires avoiding: the left and
    right "Phone Number" labels sit ~6pt apart -- a real difference, not
    layout noise)."""
    ordered = sorted(spans, key=lambda s: (s["y"], s["x"]))
    lines: list[list[dict]] = []
    for s in ordered:
        placed = False
        for ln in lines:
            if abs(ln[0]["y"] - s["y"]) <= y_tol:
                ln.append(s)
                placed = True
                break
        if not placed:
            lines.append([s])
    for ln in lines:
        ln.sort(key=lambda s: s["x"])
    return lines


def _find_label(lines: list[list[dict]], spec: "FieldSpec") -> tuple[list[dict], float, float, list[dict]] | None:
    """Find the line whose joined, normalized text CONTAINS spec.label,
    constrained to spec.search_x / spec.search_y (which disambiguate a
    label that appears more than once on the page, e.g. Gen-1's "Name" /
    "Address" / "Phone Number" / "Email" each appearing once for the
    Applicant block and once for the Property Owner block).

    Returns (line, anchor_x, anchor_y, consumed_spans) where `consumed_spans`
    is ONLY the span(s) whose text actually falls inside the matched label
    substring -- not the whole line -- so a compound line (two field labels
    sharing one printed row, e.g. Gen-1's "Existing Use____Proposed
    Use____") doesn't accidentally swallow the OTHER field's value as
    "part of the label".

    search_x/search_y are checked against the MATCHED SUBSTRING's own
    anchor position, not the line's leftmost span -- a compound line (e.g.
    Gen-2's "Map: 11 Lot: 46A", one line, two fields) would otherwise have
    every field's search_x/search_y compared against the line's overall
    (leftmost) x, which is wrong for whichever field's label sits further
    right on that same line.

    Every OCCURRENCE of the target substring within a line is tried, not
    just the first: two duplicate labels that happen to sit at the exact
    same y (e.g. Gen-1's left "Name" and right "Name" both at y=162.6) get
    clustered into ONE line by _lines(), so "name name" contains the
    target twice -- rejecting the whole line the moment the FIRST
    occurrence fails its search_x/search_y check (which is exactly what
    happens for the owner/right-column field, since the first occurrence
    is always the applicant/left one) would silently make the second
    field unfindable."""
    target = normalize_label(spec.label)
    for ln in lines:
        offsets: list[tuple[int, int, dict]] = []
        cursor = 0
        for i, s in enumerate(ln):
            piece = normalize_label(s["t"])
            if i > 0:
                cursor += 1  # the joining space
            start = cursor
            cursor += len(piece)
            offsets.append((start, cursor, s))
        joined = " ".join(normalize_label(s["t"]) for s in ln)
        search_from = 0
        while True:
            idx = joined.find(target, search_from)
            if idx == -1:
                break
            hi = idx + len(target)
            consumed = [s for (start, end, s) in offsets if start < hi and end > idx]
            anchor = consumed[0] if consumed else ln[0]
            if (
                spec.search_x[0] <= anchor["x"] <= spec.search_x[1]
                and spec.search_y[0] <= anchor["y"] <= spec.search_y[1]
            ):
                return ln, anchor["x"], anchor["y"], consumed
            search_from = idx + 1
    return None


# ---------------------------------------------------------------------------
# FieldSpec -- one declared field, per generation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldSpec:
    field_key: str
    label: str  # text to locate (normalize_label()'d on both sides)
    search_x: tuple[float, float] = (0.0, 1e6)  # constrains WHICH line matches
    search_y: tuple[float, float] = (0.0, 1e6)
    value_dx: tuple[float, float] = (0.0, 150.0)  # value window, relative to the label anchor's x
    value_dy: tuple[float, float] = (-4.0, 10.0)  # value window, relative to the label anchor's y
    unit: str | None = None
    numeric: bool = False  # True only for genuinely dimensional/count fields -- see
    # extract_by_field_map: a numeric=False field's value_norm is ALWAYS normalized
    # text, never a parsed number, so a name/address/phone/email never gets its
    # leading digit run silently sliced off (e.g. "207-555-0142" -> 207.0, or
    # "46A" -> 46.0, dropping the letter suffix -- both real, both wrong).
    confidence: float = 0.85
    # ingest/positional.py ONLY: the label anchor's (x, y), measured once
    # off a real filled Gen-1 native page (Profenno, docs/Findings of Fact
    # and Conclusions of Law), for use when NO label text exists on the
    # page to search for at all (an image+overlay page -- the trap).
    ref_anchor: tuple[float, float] | None = None
    strip_texts: tuple[str, ...] = ()  # known printed instructional/boilerplate
    # substrings (case-insensitive) to remove from a matched value before it is
    # judged empty-or-not -- e.g. Gen-1's "SD - ____(Special District)" blank
    # prints its OWN parenthetical instruction right where a filled-in value
    # would go; unlike a run of pure underscores (strip_placeholder), that
    # instruction is real words and would otherwise read as a false value on
    # every application that leaves the Special District blank unfilled.


# ---------------------------------------------------------------------------
# Generic extraction engine -- shared by both generations, and by
# ingest/positional.py (given a pre-built, rotation-corrected span list).
# ---------------------------------------------------------------------------


def extract_by_field_map(
    spans: list[dict],
    field_map: list[FieldSpec],
    *,
    document_id: str | None,
    page_no: int,
    source_priority: int = 40,
    method: str = "regex",
) -> list[FieldCandidate]:
    """Locate every field_map entry's label (by text search, via
    _find_label) and pair it with whatever OTHER spans fall inside its
    declared value window, excluding any span identified as part of ANY
    field's own label match (so one field's label text is never
    misread as another field's value). A field whose label isn't found,
    or whose value window is empty once placeholder blanks are stripped,
    produces NO candidate -- an honest absence, never a guess.
    """
    lines = _lines(spans)
    matches: dict[str, tuple[float, float]] = {}
    label_span_ids: set[int] = set()
    for spec in field_map:
        found = _find_label(lines, spec)
        if found is None:
            continue
        _ln, ax, ay, consumed = found
        matches[spec.field_key] = (ax, ay)
        for s in consumed:
            label_span_ids.add(id(s))

    candidates: list[FieldCandidate] = []
    for spec in field_map:
        if spec.field_key not in matches:
            continue
        ax, ay = matches[spec.field_key]
        xlo, xhi = ax + spec.value_dx[0], ax + spec.value_dx[1]
        ylo, yhi = ay + spec.value_dy[0], ay + spec.value_dy[1]
        picked = [
            s
            for s in spans
            if id(s) not in label_span_ids and xlo <= s["x"] < xhi and ylo <= s["y"] <= yhi
        ]
        if not picked:
            continue
        picked.sort(key=lambda s: (round(s["y"]), s["x"]))
        joined_raw = " ".join(s["t"] for s in picked)
        for boilerplate in spec.strip_texts:
            joined_raw = re.sub(re.escape(boilerplate), "", joined_raw, flags=re.IGNORECASE)
        raw = strip_placeholder(joined_raw)
        if not raw:
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
                method=method,
                confidence=spec.confidence,
                rationale=(
                    f"label {spec.label!r} located at ~({ax:.1f},{ay:.1f}); value window "
                    f"x[{xlo:.1f},{xhi:.1f}] y[{ylo:.1f},{yhi:.1f}] on page {page_no}"
                ),
                source_priority=source_priority,
            )
        )
    return candidates


# ---------------------------------------------------------------------------
# GEN1_FIELD_MAP -- "Zoning Permit Application" (2024). Geometry measured
# off docs/Findings of Fact and Conclusions of Law/M003, L065-B (Profenno,
# Perkins Point Rd) Planning Board Application 2024.06.05.pdf, physical
# page 5 (the native, filled, label-and-value Gen-1 page-1-of-form).
#
# confidence < 0.7 marks a field whose VALUE sub-position within a compound
# printed row (several blanks on one line) is a best-effort estimate from
# the printed template's character spacing, not confirmed against an
# actual filled value in either real fixture available to this workflow
# (Profenno leaves these blank; Stantec's page 9 has none either). Kept in
# the map for documentation and for native.py's own use (where a human
# reviewer still sees the label right there on the page to sanity-check
# against), but ingest/positional.py refuses to trust anything below its
# own POSITIONAL_MIN_CONFIDENCE threshold -- see that module.
# ---------------------------------------------------------------------------

_CONTACT_Y = (140.0, 305.0)
_PROPERTY_Y = (280.0, 345.0)
_SECTION1_Y = (345.0, 600.0)

GEN1_FIELD_MAP: list[FieldSpec] = [
    FieldSpec("parcel.tax_map", "TAX MAP", value_dx=(30.0, 70.0), ref_anchor=(404.5, 108.9), confidence=0.9),
    FieldSpec("parcel.lot", "LOT", search_x=(300.0, 1e6), search_y=(100.0, 120.0),
              value_dx=(75.0, 110.0), ref_anchor=(404.5, 108.9), confidence=0.9),

    FieldSpec("applicant.name", "Name", search_x=(0.0, 300.0), search_y=_CONTACT_Y,
              ref_anchor=(72.6, 162.6), confidence=0.9),
    FieldSpec("owner.name", "Name", search_x=(300.0, 1e6), search_y=_CONTACT_Y,
              ref_anchor=(324.6, 162.6), confidence=0.9),
    FieldSpec("applicant.address", "Address", search_x=(0.0, 300.0), search_y=_CONTACT_Y,
              value_dy=(-4.0, 24.0), ref_anchor=(72.6, 183.9), confidence=0.9),
    FieldSpec("owner.address", "Address", search_x=(300.0, 1e6), search_y=_CONTACT_Y,
              value_dy=(-4.0, 24.0), ref_anchor=(324.6, 183.9), confidence=0.9),
    FieldSpec("applicant.phone", "Phone Number", search_x=(0.0, 300.0), search_y=_CONTACT_Y,
              ref_anchor=(72.6, 220.9), confidence=0.9),
    FieldSpec("owner.phone", "Phone Number", search_x=(300.0, 1e6), search_y=_CONTACT_Y,
              ref_anchor=(324.6, 226.9), confidence=0.9),
    FieldSpec("applicant.email", "Email", search_x=(0.0, 300.0), search_y=_CONTACT_Y,
              ref_anchor=(72.6, 242.3), confidence=0.9),
    FieldSpec("owner.email", "Email", search_x=(300.0, 1e6), search_y=_CONTACT_Y,
              ref_anchor=(324.6, 248.3), confidence=0.9),

    FieldSpec("parcel.special_district_name", "SD", search_y=_PROPERTY_Y,
              value_dx=(0.0, 220.0), ref_anchor=(266.7, 297.7), confidence=0.85,
              strip_texts=("(Special District)",)),
    FieldSpec("parcel.street_address", "Street Address", search_y=_PROPERTY_Y,
              value_dx=(0.0, 450.0), ref_anchor=(54.6, 313.1), confidence=0.9),
    FieldSpec("parcel.lot_size_acres", "Lot Size", search_y=_PROPERTY_Y,
              value_dx=(0.0, 175.0), unit="acres", ref_anchor=(54.6, 328.7), confidence=0.9, numeric=True),
    FieldSpec("parcel.lot_frontage_ft", "Lot Frontage", search_y=_PROPERTY_Y,
              value_dx=(0.0, 200.0), unit="ft", ref_anchor=(234.6, 328.7), confidence=0.9, numeric=True),

    FieldSpec("project.existing_use", "Existing Use", search_y=_SECTION1_Y,
              value_dx=(55.0, 95.0), ref_anchor=(54.6, 447.9), confidence=0.85),
    FieldSpec("project.proposed_use", "Proposed Use", search_y=_SECTION1_Y,
              value_dx=(220.0, 320.0), ref_anchor=(54.6, 447.9), confidence=0.85),
    FieldSpec("project.description", "Provide brief description of project", search_y=_SECTION1_Y,
              value_dx=(0.0, 520.0), value_dy=(-4.0, 60.0),
              ref_anchor=(54.6, 585.5), confidence=0.85),

    FieldSpec("building.footprint_sf", "Footprint of proposed structure", search_y=_SECTION1_Y,
              value_dx=(150.0, 210.0), unit="sf", ref_anchor=(90.6, 517.8), confidence=0.5, numeric=True),
    FieldSpec("building.total_area_sf", "Total Building area", search_y=_SECTION1_Y,
              value_dx=(60.0, 140.0), unit="sf", ref_anchor=(328.4, 517.8), confidence=0.5, numeric=True),
    FieldSpec("building.width_ft", "Width", search_x=(0.0, 400.0), search_y=(530.0, 540.0),
              value_dx=(20.0, 60.0), unit="ft", ref_anchor=(90.6, 535.3), confidence=0.5, numeric=True),
    FieldSpec("building.depth_ft", "Depth", search_x=(0.0, 400.0), search_y=(530.0, 540.0),
              value_dx=(110.0, 150.0), unit="ft", ref_anchor=(90.6, 535.3), confidence=0.5, numeric=True),
    FieldSpec("building.stories", "Number of Stories", search_y=(530.0, 540.0),
              value_dx=(230.0, 290.0), ref_anchor=(90.6, 535.3), confidence=0.5, numeric=True),
    FieldSpec("building.existing_units", "Number of Units", search_y=(475.0, 495.0),
              value_dx=(160.0, 210.0), ref_anchor=(53.8, 483.0), confidence=0.5, numeric=True),
    FieldSpec("building.proposed_units", "Proposed", search_x=(0.0, 400.0), search_y=(475.0, 495.0),
              value_dx=(0.0, 60.0), ref_anchor=(233.8, 483.0), confidence=0.5, numeric=True),
    FieldSpec("setback.front_ft", "Front", search_y=(545.0, 560.0),
              value_dx=(55.0, 115.0), unit="ft", ref_anchor=(54.6, 552.6), confidence=0.5, numeric=True),
    FieldSpec("setback.side_ft", "Side", search_y=(545.0, 560.0),
              value_dx=(115.0, 180.0), unit="ft", ref_anchor=(54.6, 552.6), confidence=0.5, numeric=True),
    FieldSpec("setback.rear_ft", "Rear", search_y=(545.0, 560.0),
              value_dx=(180.0, 247.0), unit="ft", ref_anchor=(54.6, 552.6), confidence=0.5, numeric=True),
]


# ---------------------------------------------------------------------------
# GEN2_COVER_FIELD_MAP -- "PLANNING APPLICATION" Cover Sheet (2025+).
# Geometry measured off docs/Findings of Fact and Conclusions of Law/
# M011, L046-A (Morrissey, 53 Pleasant Street) SLZ Application, 2025
# Submitted Documents.pdf, physical page 1.
# ---------------------------------------------------------------------------

_COVER_TOP_Y = (85.0, 155.0)
_COVER_CONTACT_Y = (155.0, 300.0)
_COVER_SITE_Y = (425.0, 500.0)

GEN2_COVER_FIELD_MAP: list[FieldSpec] = [
    FieldSpec("parcel.street_address", "Street Address", search_y=_COVER_TOP_Y,
              value_dx=(0.0, 250.0), value_dy=(-4.0, 14.0), ref_anchor=(316.3, 120.0), confidence=0.9),
    FieldSpec("parcel.tax_map", "Map", search_y=_COVER_TOP_Y,
              value_dx=(0.0, 80.0), ref_anchor=(54.0, 115.1), confidence=0.9),
    FieldSpec("parcel.lot", "Lot", search_x=(140.0, 1e6), search_y=_COVER_TOP_Y,
              value_dx=(0.0, 80.0), ref_anchor=(158.5, 115.1), confidence=0.9),
    FieldSpec("parcel.deed_book", "Deed Book", search_y=_COVER_TOP_Y,
              value_dx=(0.0, 100.0), ref_anchor=(53.8, 144.4), confidence=0.9),
    FieldSpec("parcel.deed_page", "Page", search_x=(140.0, 1e6), search_y=_COVER_TOP_Y,
              value_dx=(0.0, 80.0), ref_anchor=(182.7, 144.4), confidence=0.85),

    FieldSpec("applicant.name", "Name", search_x=(0.0, 300.0), search_y=_COVER_CONTACT_Y,
              ref_anchor=(54.0, 205.2), confidence=0.9),
    FieldSpec("owner.name", "Name", search_x=(300.0, 1e6), search_y=_COVER_CONTACT_Y,
              ref_anchor=(315.0, 205.4), confidence=0.9),
    FieldSpec("applicant.email", "Email", search_x=(0.0, 300.0), search_y=_COVER_CONTACT_Y,
              ref_anchor=(54.0, 226.4), confidence=0.9),
    FieldSpec("owner.email", "Email", search_x=(300.0, 1e6), search_y=_COVER_CONTACT_Y,
              ref_anchor=(315.0, 226.6), confidence=0.9),
    FieldSpec("applicant.phone", "Phone", search_x=(0.0, 300.0), search_y=_COVER_CONTACT_Y,
              ref_anchor=(54.0, 247.5), confidence=0.9),
    FieldSpec("owner.phone", "Phone", search_x=(300.0, 1e6), search_y=_COVER_CONTACT_Y,
              ref_anchor=(315.0, 247.8), confidence=0.9),
    FieldSpec("applicant.address", "Address", search_x=(0.0, 300.0), search_y=_COVER_CONTACT_Y,
              value_dy=(-4.0, 24.0), ref_anchor=(54.0, 268.7), confidence=0.9),
    FieldSpec("owner.address", "Address", search_x=(300.0, 1e6), search_y=_COVER_CONTACT_Y,
              value_dy=(-4.0, 24.0), ref_anchor=(315.0, 269.0), confidence=0.9),

    # NOTE: these four labels deliberately include the printed unit-in-
    # parens suffix ("(acres)"/"(ft)") -- on the Cover Sheet that suffix is
    # its OWN trailing span (e.g. "Lot" + "Width*" + "(ft):" as three
    # separate spans on one line), and a label match must CONSUME every
    # span that is part of the printed label, or the unconsumed "(ft):"
    # span -- sitting well inside the value window -- leaks into the
    # extracted value text (e.g. "153" would extract as "(ft): 153").
    FieldSpec("parcel.lot_size_acres", "Lot Area (acres)", search_y=_COVER_SITE_Y,
              value_dx=(0.0, 150.0), unit="acres", ref_anchor=(385.9, 452.7), confidence=0.9, numeric=True),
    FieldSpec("parcel.lot_frontage_ft", "Street Frontage (ft)", search_y=_COVER_SITE_Y,
              value_dx=(0.0, 150.0), unit="ft", ref_anchor=(385.9, 470.9), confidence=0.9, numeric=True),
    FieldSpec("parcel.zoning_district", "Zoning District", search_y=_COVER_SITE_Y,
              value_dx=(0.0, 120.0), ref_anchor=(198.6, 433.3), confidence=0.85),
    FieldSpec("parcel.lot_width_ft", "Lot Width (ft)", search_y=_COVER_SITE_Y,
              value_dx=(0.0, 100.0), unit="ft", ref_anchor=(53.8, 450.9), confidence=0.85, numeric=True),
    FieldSpec("parcel.lot_depth_ft", "Lot Depth (ft)", search_y=_COVER_SITE_Y,
              value_dx=(0.0, 100.0), unit="ft", ref_anchor=(53.8, 468.0), confidence=0.85, numeric=True),
    FieldSpec("building.existing_units", "Number of Existing Dwelling Units", search_y=_COVER_SITE_Y,
              value_dx=(0.0, 200.0), ref_anchor=(53.8, 485.2), confidence=0.85, numeric=True),

    FieldSpec("project.description", "Description of Proposed Project", search_y=(540.0, 600.0),
              value_dx=(0.0, 400.0), value_dy=(-4.0, 30.0),
              ref_anchor=(46.5, 546.6), confidence=0.85),
]


# ---------------------------------------------------------------------------
# Page-level entry points
# ---------------------------------------------------------------------------


def extract_gen1_page1(
    page: "fitz.Page", *, page_no: int, document_id: str | None = None, source_priority: int = 40
) -> list[FieldCandidate]:
    return extract_by_field_map(
        page_spans(page), GEN1_FIELD_MAP,
        document_id=document_id, page_no=page_no, source_priority=source_priority, method="regex",
    )


def extract_gen2_cover_sheet(
    page: "fitz.Page", *, page_no: int, document_id: str | None = None, source_priority: int = 40
) -> list[FieldCandidate]:
    return extract_by_field_map(
        page_spans(page), GEN2_COVER_FIELD_MAP,
        document_id=document_id, page_no=page_no, source_priority=source_priority, method="regex",
    )


@dataclass(frozen=True)
class NativeExtractionResult:
    generation: str  # 'gen1' | 'gen2' | 'unknown'
    candidates: tuple[FieldCandidate, ...]
    page_used: int | None  # 1-based; None when no matching page was found


def extract_native_pdf(
    path: str, *, document_id: str | None = None, source_priority: int = 40
) -> NativeExtractionResult:
    """Top-level convenience: open `path`, detect its generation, locate
    the right page, run that generation's declared field map. Unknown
    generation -> zero candidates, generation='unknown' (never falls back
    to Gen-1 parsing -- task brief, verbatim)."""
    doc = fitz.open(str(path))
    try:
        gen = detect_generation(doc)
        if gen == GEN1:
            idx = find_gen1_form_page(doc)
            if idx is None:
                return NativeExtractionResult(GEN1, (), None)
            cands = extract_gen1_page1(
                doc[idx], page_no=idx + 1, document_id=document_id, source_priority=source_priority
            )
            return NativeExtractionResult(GEN1, tuple(cands), idx + 1)
        if gen == GEN2:
            idx = find_gen2_cover_page(doc)
            if idx is None:
                return NativeExtractionResult(GEN2, (), None)
            cands = extract_gen2_cover_sheet(
                doc[idx], page_no=idx + 1, document_id=document_id, source_priority=source_priority
            )
            return NativeExtractionResult(GEN2, tuple(cands), idx + 1)
        return NativeExtractionResult(UNKNOWN, (), None)
    finally:
        doc.close()
