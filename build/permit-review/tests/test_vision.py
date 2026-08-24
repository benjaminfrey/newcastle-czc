"""Tests for ingest/vision.py -- the Tier C/D vision REQUEST path.

Offline, no network, no LLM, no key. Every call in this file goes through
either a synthetic in-process PDF (built with PyMuPDF, same technique as
tests/test_triage.py's `_make_pdf`) or a FAKE llm.protocol.LLMClient that
never opens a socket -- exactly the "unit-test the whole path against a
fake transport" the W5 task brief asks for.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import fitz  # noqa: E402

from app import db, security  # noqa: E402
from ingest import vision  # noqa: E402
from llm.redact import ImagePagesNotRedactable  # noqa: E402
from llm.types import LLMRequest, LLMResponse, LLMUsage  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"


@pytest.fixture()
def conn(tmp_path: Path):
    # Same pattern as tests/test_audit.py and tests/test_llm_providers.py --
    # a throwaway migrated temp DB per test, so run_vision_extraction's now-
    # required `conn` argument has an events table (and the audit chain's
    # synthetic actor row) to write into.
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    try:
        yield c
    finally:
        c.close()


def _make_pdf(tmp_path: Path, *, width: float = 612, height: float = 792, text: str = "hello") -> Path:
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    if text:
        page.insert_textbox(fitz.Rect(50, 50, width - 50, height - 50), text, fontsize=11)
    path = tmp_path / "synthetic.pdf"
    doc.save(str(path))
    doc.close()
    return path


# --------------------------------------------------------------------------- #
# A fake LLMClient -- the "fake transport" the whole path is tested against.
# --------------------------------------------------------------------------- #


@dataclass
class FakeLLMClient:
    provider_name: str = "fake"
    canned_text: str = "[]"
    model: str = "fake-model"
    calls: list = None

    def __post_init__(self):
        if self.calls is None:
            self.calls = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(
            text=self.canned_text,
            model=self.model,
            provider=self.provider_name,
            usage=LLMUsage(input_tokens=100, output_tokens=20),
            stop_reason="end_turn",
        )


# --------------------------------------------------------------------------- #
# 1. render_page_image
# --------------------------------------------------------------------------- #


def test_render_page_image_returns_png_bytes_at_200dpi(tmp_path):
    import struct

    pdf_path = _make_pdf(tmp_path, width=612, height=792)  # 8.5in x 11in @ 72dpi
    png = vision.render_page_image(pdf_path, 1)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes

    # 8.5in x 11in at 200 dpi -> 1700 x 2200 px. Read pixel dimensions
    # straight out of the PNG IHDR chunk (bytes 16:24, two big-endian
    # uint32s) -- NOT via fitz's `.rect`, which reports page POINTS at a
    # fixed 72dpi reference and would silently give 1275x1650 here
    # regardless of the image's actual pixel density.
    width_px, height_px = struct.unpack(">II", png[16:24])
    assert width_px == 1700
    assert height_px == 2200


def test_render_page_image_rejects_non_positive_page_number(tmp_path):
    pdf_path = _make_pdf(tmp_path)
    with pytest.raises(ValueError):
        vision.render_page_image(pdf_path, 0)
    with pytest.raises(ValueError):
        vision.render_page_image(pdf_path, -1)


def test_render_page_image_rejects_out_of_range_page(tmp_path):
    pdf_path = _make_pdf(tmp_path)  # 1 page
    with pytest.raises(ValueError):
        vision.render_page_image(pdf_path, 2)


# --------------------------------------------------------------------------- #
# 2. build_vision_request
# --------------------------------------------------------------------------- #


def test_build_vision_request_shape():
    req = vision.build_vision_request(
        b"fake-png-bytes", field_keys=["applicant.name", "parcel.acreage"], page_no=3
    )
    assert req.system is not None and "never" in req.system.lower()
    assert "applicant.name" in req.prompt
    assert "parcel.acreage" in req.prompt
    assert "page 3" in req.prompt
    assert len(req.images) == 1
    assert req.images[0].media_type == "image/png"
    assert req.images[0].data == b"fake-png-bytes"
    assert req.metadata["purpose"] == "vision_extract"
    assert req.metadata["page_no"] == "3"


def test_build_vision_request_requires_field_keys():
    with pytest.raises(ValueError):
        vision.build_vision_request(b"x", field_keys=[], page_no=1)


def test_build_vision_request_includes_extra_context():
    req = vision.build_vision_request(
        b"x", field_keys=["a"], page_no=1, extra_context="This page is a cover sheet."
    )
    assert "cover sheet" in req.prompt


# --------------------------------------------------------------------------- #
# 3. parse_vision_response
# --------------------------------------------------------------------------- #


def _resp(text: str) -> LLMResponse:
    return LLMResponse(
        text=text, model="m", provider="fake", usage=LLMUsage(10, 10), stop_reason="end_turn"
    )


def test_parse_well_formed_response_produces_candidates():
    payload = json.dumps(
        [
            {
                "field_key": "applicant.name",
                "value_raw": "Jane Sample",
                "value_norm": "Jane Sample",
                "unit": None,
                "confidence": 0.8,
                "rationale": "printed label near top of page",
            }
        ]
    )
    result = vision.parse_vision_response(
        _resp(payload), page_no=5, expected_field_keys={"applicant.name"}, document_id="doc-1"
    )
    assert result.ok
    assert result.parse_error is None
    assert len(result.candidates) == 1
    c = result.candidates[0]
    assert c.field_key == "applicant.name"
    assert c.value_raw == "Jane Sample"
    assert c.method == "vision"
    assert c.page_no == 5
    assert c.document_id == "doc-1"
    assert c.needs_confirmation is True  # ALWAYS -- enforced by FieldCandidate itself
    assert c.confidence == 0.8


@pytest.mark.parametrize(
    "bad_text",
    [
        "not json at all",
        "{truncated json",
        '[{"field_key": "a", "value_raw": "x"',  # truncated mid-array
        "",
    ],
)
def test_malformed_or_non_json_response_yields_zero_candidates_and_a_recorded_error(bad_text):
    result = vision.parse_vision_response(
        _resp(bad_text), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    assert result.candidates == ()
    assert result.parse_error is not None
    assert not result.ok


def test_response_that_is_valid_json_but_not_a_list_yields_zero_candidates():
    result = vision.parse_vision_response(
        _resp('{"field_key": "a", "value_raw": "x"}'),
        page_no=1,
        expected_field_keys={"a"},
        document_id=None,
    )
    assert result.candidates == ()
    assert result.parse_error is not None
    assert "array" in result.parse_error.lower()


def test_fenced_json_code_block_is_unfenced_and_parses():
    payload = "```json\n" + json.dumps(
        [{"field_key": "a", "value_raw": "1.2", "value_norm": 1.2, "unit": "acres", "confidence": 0.6, "rationale": "r"}]
    ) + "\n```"
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    assert result.ok
    assert len(result.candidates) == 1


def test_entries_for_unrequested_field_keys_are_skipped_not_erroring():
    payload = json.dumps(
        [
            {"field_key": "not.asked.about", "value_raw": "x", "confidence": 0.9, "rationale": "r"},
            {"field_key": "a", "value_raw": "y", "confidence": 0.9, "rationale": "r"},
        ]
    )
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    assert result.ok
    assert len(result.candidates) == 1
    assert result.candidates[0].field_key == "a"
    assert result.skipped_unknown_field_keys == 1


def test_entry_missing_value_raw_is_skipped():
    payload = json.dumps([{"field_key": "a", "confidence": 0.9, "rationale": "r"}])
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    assert result.ok
    assert result.candidates == ()


def test_missing_confidence_defaults_conservatively():
    payload = json.dumps([{"field_key": "a", "value_raw": "x", "rationale": "r"}])
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    assert result.candidates[0].confidence == vision._DEFAULT_CONFIDENCE_WHEN_UNREPORTED


def test_out_of_range_confidence_falls_back_to_default():
    payload = json.dumps([{"field_key": "a", "value_raw": "x", "confidence": 5.0, "rationale": "r"}])
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    assert result.candidates[0].confidence == vision._DEFAULT_CONFIDENCE_WHEN_UNREPORTED


# --------------------------------------------------------------------------- #
# Handwriting confidence cap -- fires on the bad case, silent on the good one.
# --------------------------------------------------------------------------- #


def test_handwritten_high_self_reported_confidence_is_capped():
    payload = json.dumps(
        [{"field_key": "a", "value_raw": "6106", "confidence": 0.97, "rationale": "r", "handwritten": True}]
    )
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    c = result.candidates[0]
    assert c.confidence <= vision._HANDWRITING_CONFIDENCE_CAP
    assert "handwritten" in c.rationale.lower()


def test_handwritten_low_self_reported_confidence_is_not_raised():
    # The cap only ever LOWERS confidence -- a model that already reported
    # low confidence on a handwritten value must not be bumped UP to the cap.
    payload = json.dumps(
        [{"field_key": "a", "value_raw": "6106", "confidence": 0.1, "rationale": "r", "handwritten": True}]
    )
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    assert result.candidates[0].confidence == 0.1


def test_printed_value_is_not_capped():
    # Silent-on-the-good-case control: an ordinary (non-handwritten) high
    # confidence value must pass through untouched.
    payload = json.dumps(
        [{"field_key": "a", "value_raw": "6106", "confidence": 0.95, "rationale": "r"}]
    )
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    assert result.candidates[0].confidence == 0.95


# --------------------------------------------------------------------------- #
# bbox parsing
# --------------------------------------------------------------------------- #


def test_valid_bbox_is_parsed():
    payload = json.dumps(
        [{"field_key": "a", "value_raw": "x", "confidence": 0.9, "rationale": "r", "bbox": [1, 2, 3, 4]}]
    )
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    assert result.candidates[0].bbox == (1.0, 2.0, 3.0, 4.0)


def test_missing_bbox_uses_honest_placeholder_and_says_so():
    payload = json.dumps([{"field_key": "a", "value_raw": "x", "confidence": 0.9, "rationale": "r"}])
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    c = result.candidates[0]
    assert c.bbox == (0.0, 0.0, 0.0, 0.0)
    assert "no bounding box" in c.rationale.lower()


def test_malformed_bbox_falls_back_to_placeholder():
    payload = json.dumps(
        [{"field_key": "a", "value_raw": "x", "confidence": 0.9, "rationale": "r", "bbox": "not-a-list"}]
    )
    result = vision.parse_vision_response(
        _resp(payload), page_no=1, expected_field_keys={"a"}, document_id=None
    )
    assert result.candidates[0].bbox == (0.0, 0.0, 0.0, 0.0)


# --------------------------------------------------------------------------- #
# every candidate always carries needs_confirmation / method / page_no
# --------------------------------------------------------------------------- #


def test_every_candidate_defaults_needs_confirmation_true_and_method_vision():
    payload = json.dumps(
        [
            {"field_key": "a", "value_raw": "x", "confidence": 0.5, "rationale": "r"},
            {"field_key": "b", "value_raw": "y", "confidence": 0.9, "rationale": "r2", "handwritten": True},
        ]
    )
    result = vision.parse_vision_response(
        _resp(payload), page_no=7, expected_field_keys={"a", "b"}, document_id="doc-9"
    )
    assert len(result.candidates) == 2
    for c in result.candidates:
        assert c.needs_confirmation is True
        assert c.method == "vision"
        assert c.page_no == 7
        assert c.document_id == "doc-9"


# --------------------------------------------------------------------------- #
# 4. run_vision_extraction -- end to end against the fake transport, and
# the redaction gate ordering.
# --------------------------------------------------------------------------- #


def test_run_vision_extraction_end_to_end_with_fake_client(tmp_path, conn):
    pdf_path = _make_pdf(tmp_path)
    payload = json.dumps(
        [{"field_key": "applicant.name", "value_raw": "Jane Sample", "confidence": 0.8, "rationale": "r"}]
    )
    client = FakeLLMClient(canned_text=payload)

    result = vision.run_vision_extraction(
        client,
        conn=conn,
        pdf_path=pdf_path,
        page_number=1,
        field_keys=["applicant.name"],
        document_id="doc-1",
        operator_ticked=True,
    )

    assert result.ok
    assert len(result.candidates) == 1
    assert len(client.calls) == 1
    sent = client.calls[0]
    assert len(sent.images) == 1
    assert sent.images[0].media_type == "image/png"
    assert sent.images[0].data[:8] == b"\x89PNG\r\n\x1a\n"

    # The call was audited -- exactly one `events` row, kind "llm.call",
    # recording success (llm/audited.py wraps `client` before ever calling
    # it; nothing here calls llm/events.py directly).
    rows = conn.execute("SELECT kind, payload_json FROM events").fetchall()
    assert len(rows) == 1
    assert rows[0]["kind"] == "llm.call"
    payload_json = json.loads(rows[0]["payload_json"])
    assert payload_json["success"] is True
    assert payload_json["purpose"] == "vision_extract"
    assert payload_json["provider"] == "fake"
    # Never the prompt text or the image bytes -- only a count.
    assert "prompt" not in payload_json
    assert payload_json["image_count"] == 1
    assert b"\x89PNG" not in json.dumps(payload_json).encode("utf-8")


def test_run_vision_extraction_refuses_without_operator_tick_before_any_call(tmp_path, conn, monkeypatch):
    pdf_path = _make_pdf(tmp_path)
    client = FakeLLMClient()

    def _must_not_render(*args, **kwargs):  # pragma: no cover -- must never run
        raise AssertionError("render_page_image was called despite operator_ticked=False")

    monkeypatch.setattr(vision, "render_page_image", _must_not_render)

    with pytest.raises(ImagePagesNotRedactable):
        vision.run_vision_extraction(
            client,
            conn=conn,
            pdf_path=pdf_path,
            page_number=1,
            field_keys=["applicant.name"],
            document_id="doc-1",
            operator_ticked=False,
        )
    assert client.calls == []  # the fake transport was never reached either
    # The gate fires before any provider call is even attempted, so there
    # is nothing to audit yet -- zero events rows, not a phantom one.
    assert conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"] == 0


def test_run_vision_extraction_default_offline_client_never_touches_network(tmp_path, conn):
    # The default provider (llm.factory.get_client() with no args -> null)
    # must be able to drive this whole path with zero network and zero cost.
    from llm.factory import get_client

    pdf_path = _make_pdf(tmp_path)
    client = get_client()  # null provider by default
    result = vision.run_vision_extraction(
        client,
        conn=conn,
        pdf_path=pdf_path,
        page_number=1,
        field_keys=["applicant.name"],
        document_id="doc-1",
        operator_ticked=True,
    )
    # The null provider always answers "[]" -- zero candidates, not an
    # error; the pipeline runs cleanly end to end with no key and no
    # network either way.
    assert result.ok
    # Still audited, even against the null provider.
    rows = conn.execute("SELECT kind FROM events").fetchall()
    assert len(rows) == 1
    assert rows[0]["kind"] == "llm.call"


def test_run_vision_extraction_records_a_failed_call_too(tmp_path, conn):
    # AuditedClient must write the events row on a raised error too, not
    # only on success -- D-0025's "success or failure alike" requirement.
    pdf_path = _make_pdf(tmp_path)

    class _BoomClient:
        provider_name = "fake-boom"

        def complete(self, request):
            raise RuntimeError("simulated provider failure")

    with pytest.raises(RuntimeError, match="simulated provider failure"):
        vision.run_vision_extraction(
            _BoomClient(),
            conn=conn,
            pdf_path=pdf_path,
            page_number=1,
            field_keys=["applicant.name"],
            document_id="doc-1",
            operator_ticked=True,
        )

    rows = conn.execute("SELECT payload_json FROM events").fetchall()
    assert len(rows) == 1
    payload_json = json.loads(rows[0]["payload_json"])
    assert payload_json["success"] is False
    assert payload_json["error_type"] == "RuntimeError"
    assert payload_json["provider"] == "fake-boom"
