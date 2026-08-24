"""ingest/vision.py -- the vision REQUEST path for Tier C/D pages.

W5 task brief, item 5, verbatim: "Vision REQUEST path for Tier C/D pages at
200 dpi: page image -> request construction -> response parsing ->
field_candidates. Build and unit-test the whole path against a fake
transport. Candidates from vision default needs_confirmation=True ALWAYS,
and carry method='vision' plus page_no and confidence, so a human can trace
any value back to the page it came from."

Why W5 (and this module) matter before the review engine (W6): the v1
subdivision case (Shattuck) is 18/18 scanned pages -- Tier C, zero native
text (BUILD-STATE.md). ingest/native.py and ingest/positional.py cannot
find a single field on those pages; this module is the only extraction
path that can.

Pipeline, end to end (`run_vision_extraction` composes the first three):

    1. render_page_image()     PDF page -> PNG bytes at VISION_DPI (200),
                                via PyMuPDF -- no OCR, no tooling install.
    2. build_vision_request()  PNG bytes + the field_keys being asked about
                                -> one llm.types.LLMRequest (system + prompt
                                + one ImagePart). ONE request per page --
                                asking for every field_def on that page's
                                Tier at once, not one call per field.
    3. client.complete(request)            -- an llm.protocol.LLMClient, wrapped in
                                llm.audited.AuditedClient by run_vision_extraction()
                                itself so the call is audited (one `events` row,
                                success or failure) with no chance to forget; the
                                default ('null' provider, llm/factory.py) makes this
                                whole module exercisable offline, with zero network
                                and zero cost, in every test and in --selftest.
    4. parse_vision_response() LLMResponse -> ingest.fields.FieldCandidate
                                rows. A malformed or unparsable response
                                yields ZERO candidates, never a guessed one
                                (CONTRACT.md §1.1 S7) -- the page goes back
                                to the worklist, exactly as if vision had
                                found nothing.

THE ONE ENFORCED GATE. A page image is the one thing llm/redact.py cannot
redact -- its own docstring: "PAGE IMAGES CANNOT BE NAME-REDACTED." D-0025's
safeguard for that honest limitation is an explicit per-document operator
tick, and `run_vision_extraction()` calls
`llm.redact.require_operator_ticked_for_image()` FIRST, before rendering or
sending a single byte -- a caller cannot accidentally skip the gate by
calling the lower-level functions directly in the wrong order, because
`run_vision_extraction` is the one function that owns the order.

EVERY vision-sourced FieldCandidate has needs_confirmation=True (enforced
by ingest.fields.FieldCandidate.__post_init__ itself -- there is no way to
construct one with it False) and method='vision', so nothing this module
produces is ever mistaken for a human-confirmed value.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Sequence

import fitz  # PyMuPDF

from ingest.fields import FieldCandidate
from llm.audited import AuditedClient
from llm.protocol import LLMClient
from llm.redact import require_operator_ticked_for_image
from llm.types import ImagePart, LLMRequest, LLMResponse

VISION_DPI = 200
DEFAULT_MAX_TOKENS = 4096

# A confidence value this module assigns ONLY when the model's JSON entry
# omits `confidence` entirely -- conservative on purpose (below the 0.4
# threshold most native-text extractors use for a plain, unqualified
# label match; see ingest/native.py), and documented so it is never
# mistaken for something the model actually reported.
_DEFAULT_CONFIDENCE_WHEN_UNREPORTED = 0.3

# NOT in the task brief verbatim -- an engineering judgment call, flagged
# as such rather than mis-cited: a model self-reporting confidence=0.95 on
# a HANDWRITTEN value is exactly the case a cap exists for -- its own
# certainty claim about its own reading of cursive is not trustworthy
# evidence on its own. The cap applies AFTER the model's (or the
# unreported-default) value is read, unconditionally, and only ever LOWERS
# the effective confidence, never raises it. Set below ingest/native.py's
# 0.7 "needs a closer look" threshold and above
# _DEFAULT_CONFIDENCE_WHEN_UNREPORTED, so a handwritten read stays
# distinguishable from both a normal machine-read value and a completely
# unreported one.
_HANDWRITING_CONFIDENCE_CAP = 0.4

# No located span within the page exists for a whole-page vision read (v1
# does not ask the model for true bounding-box grounding) -- a model MAY
# still report one (see `_parse_bbox`); when it does not, this is the
# honest placeholder, distinguishable from a real ingest/positional.py
# match by its rationale text.
_NO_BBOX = (0.0, 0.0, 0.0, 0.0)


# --------------------------------------------------------------------------- #
# 1. Render -- PDF page -> PNG bytes at 200 dpi.
# --------------------------------------------------------------------------- #


def render_page_image(pdf_path: str | Path, page_number: int, *, dpi: int = VISION_DPI) -> bytes:
    """Render ONE page (1-indexed, matching pages.page_number throughout
    this app) of `pdf_path` to PNG bytes at `dpi`. No OCR and no external
    tooling -- PyMuPDF's own rasterizer, the same dependency
    ingest/triage.py and ingest/formgen.py already use for page images.
    """
    if page_number <= 0:
        raise ValueError(f"page_number must be positive (1-indexed), got {page_number!r}")
    doc = fitz.open(str(pdf_path))
    try:
        if not (1 <= page_number <= doc.page_count):
            raise ValueError(f"{pdf_path}: page {page_number} out of range (1..{doc.page_count})")
        page = doc[page_number - 1]
        zoom = dpi / 72.0  # PDF points are 72/inch; PyMuPDF's default matrix is 1:1 at 72 dpi
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
# 2. Request construction.
# --------------------------------------------------------------------------- #

_SYSTEM_PROMPT = (
    "You are reading one page image from a Newcastle, Maine Planning Board permit "
    "application. You are extracting REQUESTED FIELDS ONLY -- you never decide "
    "whether the application complies with anything, and you never write a legal "
    "conclusion. Respond with a JSON array ONLY, no prose before or after it. Each "
    "array entry is an object with exactly these keys: "
    '"field_key" (must be one of the requested keys, verbatim), '
    '"value_raw" (the text exactly as it appears on the page), '
    '"value_norm" (a number if the value is numeric, otherwise the same string as '
    "value_raw, or null if you cannot read it), "
    '"unit" (a unit string such as "ft" or "acres", or null), '
    '"confidence" (your own confidence the reading is correct, 0.0 to 1.0), '
    '"rationale" (one short sentence: where on the page and why you read it this way), '
    'and OPTIONALLY "bbox" ([x0, y0, x1, y1] in PDF points, top-left origin, only if '
    'you can localize it) and OPTIONALLY "handwritten" (true if the value is '
    "handwritten rather than printed). Omit an entry entirely for any requested "
    "field you cannot find on this page -- never guess a value."
)


def build_vision_request(
    image_png: bytes,
    *,
    field_keys: Sequence[str],
    page_no: int,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    extra_context: str | None = None,
) -> LLMRequest:
    """One page image + the field_defs.field_key values being asked about ->
    one LLMRequest. ONE request per page, asking for every requested field
    at once -- not one call per field, which would multiply cost with no
    accuracy benefit (the model sees the whole page either way).
    """
    if not field_keys:
        raise ValueError("build_vision_request: field_keys must be non-empty")
    prompt_lines = [
        f"This is page {page_no} of a scanned application document.",
        "Requested fields (respond only about these, using these exact field_key strings):",
    ]
    prompt_lines.extend(f"  - {k}" for k in field_keys)
    if extra_context:
        prompt_lines.append(extra_context)
    prompt_lines.append("Respond with the JSON array now.")
    prompt = "\n".join(prompt_lines)

    return LLMRequest(
        prompt=prompt,
        system=_SYSTEM_PROMPT,
        images=(ImagePart(media_type="image/png", data=image_png),),
        max_tokens=max_tokens,
        metadata={"purpose": "vision_extract", "page_no": str(page_no)},
    )


# --------------------------------------------------------------------------- #
# 3. Response parsing -- LLMResponse -> FieldCandidate rows.
# --------------------------------------------------------------------------- #

# A model asked for "JSON only" sometimes wraps it in a fenced code block
# anyway; strip that before parsing rather than failing on it.
_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _unfence(text: str) -> str:
    m = _FENCE_RE.match(text.strip())
    return m.group(1) if m else text


def _parse_bbox(raw: object) -> tuple[float, float, float, float]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return _NO_BBOX
    try:
        x0, y0, x1, y1 = (float(v) for v in raw)
    except (TypeError, ValueError):
        return _NO_BBOX
    return (x0, y0, x1, y1)


@dataclass(frozen=True)
class VisionExtractionResult:
    """What one page's vision call produced. `parse_error` is set (and
    `candidates` is empty) when the model's response could not be parsed
    into the expected JSON-array shape at all -- an honest "found nothing",
    never a guessed candidate (CONTRACT.md §1.1 S7). A response that parses
    but whose entries don't match a requested field_key is not an error --
    those entries are silently skipped (`skipped_unknown_field_keys` says
    how many), since a model naming a field nobody asked about is not the
    same failure as a model producing unparsable JSON.
    """

    candidates: tuple[FieldCandidate, ...]
    parse_error: str | None
    skipped_unknown_field_keys: int = 0

    @property
    def ok(self) -> bool:
        return self.parse_error is None


def parse_vision_response(
    response: LLMResponse,
    *,
    page_no: int,
    expected_field_keys: Collection[str],
    document_id: str | None,
    source_priority: int = 40,
) -> VisionExtractionResult:
    """Parse one LLMResponse from a vision call into FieldCandidate rows.
    Never raises on malformed model output -- see VisionExtractionResult's
    docstring; a parse failure is reported, not thrown, so a caller
    iterating many pages doesn't need a try/except around every one.
    """
    try:
        data = json.loads(_unfence(response.text))
    except json.JSONDecodeError as exc:
        return VisionExtractionResult(candidates=(), parse_error=f"not valid JSON: {exc}")

    if not isinstance(data, list):
        return VisionExtractionResult(candidates=(), parse_error=f"expected a JSON array, got {type(data).__name__}")

    candidates: list[FieldCandidate] = []
    skipped = 0
    for entry in data:
        if not isinstance(entry, dict):
            skipped += 1
            continue
        field_key = entry.get("field_key")
        if field_key not in expected_field_keys:
            skipped += 1
            continue
        value_raw = entry.get("value_raw")
        if value_raw is None:
            skipped += 1
            continue

        confidence = entry.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            confidence = _DEFAULT_CONFIDENCE_WHEN_UNREPORTED

        rationale = str(entry.get("rationale") or "vision read; no rationale reported")
        if entry.get("handwritten"):
            if confidence > _HANDWRITING_CONFIDENCE_CAP:
                confidence = _HANDWRITING_CONFIDENCE_CAP
            rationale = f"{rationale} (reported as handwritten; confidence capped)"
        bbox = _parse_bbox(entry.get("bbox"))
        if bbox == _NO_BBOX:
            rationale = f"{rationale} -- no bounding box localized on the page"

        candidates.append(
            FieldCandidate(
                field_key=field_key,
                value_raw=str(value_raw),
                value_norm=entry.get("value_norm"),
                unit=entry.get("unit"),
                document_id=document_id,
                page_no=page_no,
                bbox=bbox,
                method="vision",
                confidence=round(float(confidence), 3),
                rationale=rationale,
                source_priority=source_priority,
            )
        )

    return VisionExtractionResult(candidates=tuple(candidates), parse_error=None, skipped_unknown_field_keys=skipped)


# --------------------------------------------------------------------------- #
# End to end -- render, build, call, parse. Owns the redaction-gate order.
# --------------------------------------------------------------------------- #


def run_vision_extraction(
    client: LLMClient,
    *,
    conn: sqlite3.Connection,
    pdf_path: str | Path,
    page_number: int,
    field_keys: Sequence[str],
    document_id: str | None,
    operator_ticked: bool,
    source_priority: int = 40,
    dpi: int = VISION_DPI,
    extra_context: str | None = None,
    actor_user_id: str | None = None,
    case_id: str | None = None,
) -> VisionExtractionResult:
    """The full Tier C/D page -> field_candidates path for ONE page.
    Raises `llm.redact.ImagePagesNotRedactable` before rendering or sending
    anything if `operator_ticked` is False -- D-0025's gate, enforced in
    the one place this module lets a page image leave the process.

    `conn` is REQUIRED, not optional: `client` is wrapped in
    `llm.audited.AuditedClient` before it is ever called, so this function
    -- the one call site in the app that actually invokes a provider's
    `complete()` today -- cannot be used to make an unaudited call even by
    accident. The wrapper writes exactly one `events` row (llm/events.py,
    kind "llm.call") whether the call succeeds or raises; any
    `llm.types.LLMError` the provider raises still propagates to this
    caller un-caught, only after that row lands (see AuditedClient's own
    docstring). Page images are never text-redacted (the honest limitation
    llm/redact.py documents), so the audit row's redaction report is
    empty -- there is nothing to redact-and-report on this path, only the
    operator-tick gate above.
    """
    require_operator_ticked_for_image(document_id or "<no-document-id>", operator_ticked=operator_ticked)

    audited_client = AuditedClient(
        inner=client,
        conn=conn,
        purpose="vision_extract",
        actor_user_id=actor_user_id,
        case_id=case_id,
    )

    image_png = render_page_image(pdf_path, page_number, dpi=dpi)
    request = build_vision_request(
        image_png, field_keys=field_keys, page_no=page_number, extra_context=extra_context
    )
    response = audited_client.complete(request)
    return parse_vision_response(
        response,
        page_no=page_number,
        expected_field_keys=set(field_keys),
        document_id=document_id,
        source_priority=source_priority,
    )
