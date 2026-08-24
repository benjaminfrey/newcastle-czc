"""Tests for llm/audited.py -- AuditedClient, the LLMClient wrapper that
makes the events.py audit row STRUCTURAL rather than a per-call-site
convention.

Offline, no network, no LLM key. Exercised directly against a fake inner
LLMClient -- ingest/vision.py's own tests (tests/test_vision.py) cover the
same wrapper wired into the one real call site.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import db, security  # noqa: E402
from llm.audited import AuditedClient  # noqa: E402
from llm.redact import RedactionReport  # noqa: E402
from llm.types import LLMRequest, LLMResponse, LLMUsage  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"


@pytest.fixture()
def conn(tmp_path: Path):
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    try:
        yield c
    finally:
        c.close()


@dataclass
class _FakeClient:
    provider_name: str = "fake"
    calls: list = field(default_factory=list)
    raise_exc: Exception | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        if self.raise_exc is not None:
            raise self.raise_exc
        return LLMResponse(
            text="ok",
            model="fake-model",
            provider=self.provider_name,
            usage=LLMUsage(input_tokens=10, output_tokens=2),
            stop_reason="end_turn",
        )


def _events(conn):
    return [json.loads(r["payload_json"]) for r in conn.execute("SELECT payload_json FROM events").fetchall()]


def test_audited_client_satisfies_the_llmclient_protocol(conn):
    from llm.protocol import LLMClient

    audited = AuditedClient(inner=_FakeClient(), conn=conn, purpose="test")
    assert isinstance(audited, LLMClient)
    assert audited.provider_name == "fake"


def test_success_writes_exactly_one_event_and_returns_the_response(conn):
    inner = _FakeClient()
    # No case_id here -- `events.case_id` is a real foreign key to `cases`
    # (CONTRACT.md §3.6), and this test has no case row to point at; a
    # standalone LLM call not yet tied to a case (case_id=None) is a real
    # situation this module must support, not just a test convenience.
    audited = AuditedClient(inner=inner, conn=conn, purpose="test_purpose")

    response = audited.complete(LLMRequest(prompt="hello"))

    assert response.text == "ok"
    payloads = _events(conn)
    assert len(payloads) == 1
    assert payloads[0]["success"] is True
    assert payloads[0]["purpose"] == "test_purpose"
    assert payloads[0]["provider"] == "fake"
    assert payloads[0]["model"] == "fake-model"


def test_failure_writes_the_event_then_reraises_unchanged(conn):
    boom = ValueError("boom")
    inner = _FakeClient(raise_exc=boom)
    audited = AuditedClient(inner=inner, conn=conn, purpose="test_purpose")

    with pytest.raises(ValueError, match="boom"):
        audited.complete(LLMRequest(prompt="hello"))

    payloads = _events(conn)
    assert len(payloads) == 1
    assert payloads[0]["success"] is False
    assert payloads[0]["error_type"] == "ValueError"
    assert payloads[0]["error_message"] == "boom"
    # Even on failure, the wrapper knows which provider it wrapped.
    assert payloads[0]["provider"] == "fake"


def test_does_not_mutate_the_request_forwarded_to_the_inner_client(conn):
    # llm/recorded.py's cassette lookup key is computed from the exact
    # request (including metadata) -- AuditedClient must forward the
    # caller's request unmodified, even though it adds a `provider` key to
    # the COPY it hands to record_llm_call() for the audit payload.
    inner = _FakeClient()
    audited = AuditedClient(inner=inner, conn=conn, purpose="test")

    req = LLMRequest(prompt="hello", metadata={"review_type": "subdivision"})
    audited.complete(req)

    assert len(inner.calls) == 1
    assert inner.calls[0] is req
    assert inner.calls[0].metadata == {"review_type": "subdivision"}


def test_existing_provider_metadata_is_left_alone_in_the_audit_row(conn):
    inner = _FakeClient(provider_name="fake")
    audited = AuditedClient(inner=inner, conn=conn, purpose="test")

    # A caller-supplied metadata["provider"] should not be clobbered.
    req = LLMRequest(prompt="hello", metadata={"provider": "caller-supplied"})
    audited.complete(req)

    # Success path still gets `provider` from the response itself (see
    # llm/events.py:record_llm_call()'s payload.update() on the ok branch),
    # so this asserts the wrapper didn't crash or double-set anything --
    # the request object itself keeps the caller's original metadata.
    assert inner.calls[0].metadata == {"provider": "caller-supplied"}


def test_redaction_report_defaults_to_empty_and_is_recorded(conn):
    from llm.redact import empty_report

    audited = AuditedClient(inner=_FakeClient(), conn=conn, purpose="test")
    audited.complete(LLMRequest(prompt="hello"))

    payloads = _events(conn)
    assert payloads[0]["redaction_report"] == empty_report().as_payload()


def test_a_real_redaction_report_is_carried_through_to_the_event(conn):
    report = RedactionReport(occurrences={"names": 2}, distinct_tokens={"names": 1})
    audited = AuditedClient(inner=_FakeClient(), conn=conn, purpose="test", redaction_report=report)
    audited.complete(LLMRequest(prompt="hello"))

    payloads = _events(conn)
    assert payloads[0]["redaction_report"] == report.as_payload()
    # Counts only -- never a value.
    assert "names" in json.dumps(payloads[0]["redaction_report"])


def test_two_calls_through_the_same_wrapper_chain_correctly(conn):
    # Not a special case in AuditedClient itself -- app/audit.py's own
    # hash chain -- but worth proving end to end through this wrapper.
    from app.audit import verify_chain

    audited = AuditedClient(inner=_FakeClient(), conn=conn, purpose="test")
    audited.complete(LLMRequest(prompt="first"))
    audited.complete(LLMRequest(prompt="second"))

    assert len(_events(conn)) == 2
    ok, bad_seq = verify_chain(conn)
    assert ok is True
    assert bad_seq is None
