"""Tests for the llm/ provider infrastructure: types, protocol, the four
providers (null/anthropic/recorded/local), factory resolution, cassette
loading, and events.py's audit-row recording.

Offline, no network, no LLM key, ever. The `anthropic` provider is
exercised ONLY against an injected fake transport (never the real
`anthropic` package, which is not even installed in this environment) --
its correctness is proven by construction (request shape / response
parsing / error mapping), exactly as llm/anthropic_provider.py's own
docstring describes.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import audit, db, security  # noqa: E402
from llm import anthropic_provider, cassette, events, factory, local, null, protocol, recorded  # noqa: E402
from llm.types import (  # noqa: E402
    ImagePart,
    LLMAuthError,
    LLMBadRequestError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMResponseParseError,
    LLMServerError,
    LLMTransportError,
    LLMUsage,
)

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"
FIXTURE_CASSETTE = APP_ROOT / "llm" / "cassettes" / "fixtures" / "demo_text_and_vision.json"


@pytest.fixture()
def conn(tmp_path: Path):
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    try:
        yield c
    finally:
        c.close()


# --------------------------------------------------------------------------- #
# llm/types.py
# --------------------------------------------------------------------------- #


def test_llm_request_rejects_empty_prompt():
    with pytest.raises(ValueError):
        LLMRequest(prompt="")


def test_llm_request_rejects_non_positive_max_tokens():
    with pytest.raises(ValueError):
        LLMRequest(prompt="hi", max_tokens=0)


def test_image_part_rejects_empty_bytes_or_media_type():
    with pytest.raises(ValueError):
        ImagePart(media_type="image/png", data=b"")
    with pytest.raises(ValueError):
        ImagePart(media_type="", data=b"x")


def test_llm_usage_rejects_negative_counts():
    with pytest.raises(ValueError):
        LLMUsage(input_tokens=-1, output_tokens=0)


def test_error_hierarchy():
    assert issubclass(LLMAuthError, Exception)
    assert issubclass(LLMRateLimitError, Exception)
    err = LLMRateLimitError("slow down", retry_after=12.5)
    assert err.retry_after == 12.5


# --------------------------------------------------------------------------- #
# llm/protocol.py -- structural typing
# --------------------------------------------------------------------------- #


class _BareObject:
    pass


class _ShapedButWrongType:
    provider_name = 123  # runtime_checkable only checks attribute PRESENCE, not type

    def complete(self, request):
        ...


def test_llm_client_is_runtime_checkable_and_matches_shape():
    assert isinstance(null.NullClient(), protocol.LLMClient)
    assert isinstance(_ShapedButWrongType(), protocol.LLMClient)
    assert not isinstance(_BareObject(), protocol.LLMClient)


# --------------------------------------------------------------------------- #
# llm/null.py
# --------------------------------------------------------------------------- #


def test_null_client_is_deterministic_and_offline():
    client = null.NullClient()
    req = LLMRequest(prompt="describe this application")
    r1 = client.complete(req)
    r2 = client.complete(req)
    assert r1.text == r2.text == "[]"
    assert r1.usage == r2.usage
    assert r1.provider == "null"


def test_null_client_counts_images_into_input_tokens():
    client = null.NullClient()
    img = ImagePart(media_type="image/png", data=b"x" * 10)
    no_image = client.complete(LLMRequest(prompt="a b c"))
    with_image = client.complete(LLMRequest(prompt="a b c", images=(img,)))
    assert with_image.usage.input_tokens > no_image.usage.input_tokens


# --------------------------------------------------------------------------- #
# llm/local.py -- a real seam that genuinely satisfies the protocol
# --------------------------------------------------------------------------- #


def test_local_client_satisfies_protocol_but_raises_when_called():
    client = local.LocalClient()
    assert isinstance(client, protocol.LLMClient)
    with pytest.raises(NotImplementedError):
        client.complete(LLMRequest(prompt="hi"))


# --------------------------------------------------------------------------- #
# llm/factory.py
# --------------------------------------------------------------------------- #


def test_factory_default_is_null_with_no_env_and_no_argument(monkeypatch):
    monkeypatch.delenv(factory.PROVIDER_ENV_VAR, raising=False)
    client = factory.get_client()
    assert isinstance(client, null.NullClient)


def test_factory_explicit_provider_overrides_env(monkeypatch):
    monkeypatch.setenv(factory.PROVIDER_ENV_VAR, "local")
    client = factory.get_client("null")
    assert isinstance(client, null.NullClient)


def test_factory_reads_env_var_when_no_explicit_provider(monkeypatch):
    monkeypatch.setenv(factory.PROVIDER_ENV_VAR, "local")
    client = factory.get_client()
    assert isinstance(client, local.LocalClient)


def test_factory_unknown_provider_raises():
    with pytest.raises(factory.UnknownProviderError):
        factory.get_client("made-up-provider")


def test_factory_recorded_requires_a_cassette_argument():
    with pytest.raises(TypeError):
        factory.get_client("recorded")


def test_factory_recorded_with_cassette_kwarg_works():
    cf = cassette.load_cassette(FIXTURE_CASSETTE)
    client = factory.get_client("recorded", cassette=cf)
    assert isinstance(client, recorded.RecordedClient)


# --------------------------------------------------------------------------- #
# llm/cassette.py
# --------------------------------------------------------------------------- #


def test_fixture_cassette_loads_and_is_labelled_synthetic():
    cf = cassette.load_cassette(FIXTURE_CASSETTE)
    assert cf.synthetic is True
    assert "synthetic" in cf.note.lower()
    assert len(cf.entries) >= 2


def test_compute_key_is_deterministic_and_sensitive_to_content():
    r1 = LLMRequest(prompt="hello", system="sys", metadata={"a": "1"})
    r2 = LLMRequest(prompt="hello", system="sys", metadata={"a": "1"})
    r3 = LLMRequest(prompt="hello", system="sys", metadata={"a": "2"})
    assert cassette.compute_key(r1) == cassette.compute_key(r2)
    assert cassette.compute_key(r1) != cassette.compute_key(r3)


def test_compute_key_ignores_max_tokens():
    r1 = LLMRequest(prompt="hello", max_tokens=100)
    r2 = LLMRequest(prompt="hello", max_tokens=9000)
    assert cassette.compute_key(r1) == cassette.compute_key(r2)


def test_compute_key_metadata_key_order_does_not_matter():
    r1 = LLMRequest(prompt="hello", metadata={"a": "1", "b": "2"})
    r2 = LLMRequest(prompt="hello", metadata={"b": "2", "a": "1"})
    assert cassette.compute_key(r1) == cassette.compute_key(r2)


def test_load_cassette_rejects_non_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    with pytest.raises(cassette.CassetteFormatError):
        cassette.load_cassette(bad)


def test_load_cassette_rejects_missing_synthetic_flag(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"format_version": 1, "entries": []}', encoding="utf-8")
    with pytest.raises(cassette.CassetteFormatError):
        cassette.load_cassette(bad)


def test_load_cassette_rejects_synthetic_true_with_no_label_in_note(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        '{"format_version": 1, "synthetic": true, "note": "just some notes", '
        '"entries": [{"key": "k", "response": {"text": "t", "model": "m", '
        '"stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 1}}}]}',
        encoding="utf-8",
    )
    with pytest.raises(cassette.CassetteFormatError):
        cassette.load_cassette(bad)


def test_load_cassette_rejects_empty_entries(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        '{"format_version": 1, "synthetic": true, "note": "synthetic fixture", "entries": []}',
        encoding="utf-8",
    )
    with pytest.raises(cassette.CassetteFormatError):
        cassette.load_cassette(bad)


# --------------------------------------------------------------------------- #
# llm/recorded.py
# --------------------------------------------------------------------------- #


def test_recorded_client_replays_the_seeded_text_fixture():
    client = recorded.RecordedClient.from_path(FIXTURE_CASSETTE)
    req = LLMRequest(
        prompt=(
            "Extract field candidates as a JSON list from the application text below.\n\n"
            "FIELDS: applicant.name, parcel.acreage\n\nTEXT:\nApplicant: Jane Sample\n"
            "Acreage: 2.5 acres"
        ),
        system=(
            "You are a permit-review field extraction assistant. Return ONLY a JSON "
            "list, no prose, no citations, no conclusions."
        ),
        metadata={"purpose": "fewshot_demo", "review_type": "use_permit", "rule_id": "art7.34"},
    )
    response = client.complete(req)
    assert "Jane Sample" in response.text
    assert response.provider == "recorded"
    assert response.raw["synthetic"] is True


def test_recorded_client_replays_the_seeded_vision_fixture():
    client = recorded.RecordedClient.from_path(FIXTURE_CASSETTE)
    img = ImagePart(media_type="image/png", data=b"SYNTHETIC-FIXTURE-PNG-BYTES-NOT-A-REAL-IMAGE")
    req = LLMRequest(
        prompt=(
            "Extract field candidates from this scanned application page as a JSON list. "
            "FIELDS: applicant.name, parcel.acreage."
        ),
        system=(
            "You are a permit-review vision extraction assistant. Return ONLY a JSON list, "
            "no prose, no citations, no conclusions."
        ),
        images=(img,),
        metadata={"purpose": "vision_extract", "page_no": "3", "tier": "C"},
    )
    response = client.complete(req)
    assert "handwritten" in response.text.lower() or "0.55" in response.text


def test_recorded_client_raises_on_unmatched_request():
    client = recorded.RecordedClient.from_path(FIXTURE_CASSETTE)
    with pytest.raises(recorded.CassetteMissError):
        client.complete(LLMRequest(prompt="something that was never recorded, ever"))


def test_recorded_client_miss_is_a_response_parse_error_subclass():
    assert issubclass(recorded.CassetteMissError, LLMResponseParseError)


# --------------------------------------------------------------------------- #
# llm/anthropic_provider.py -- request shape, response parsing, error
# mapping. NEVER imports or calls the real `anthropic` package.
# --------------------------------------------------------------------------- #


def test_build_message_params_puts_images_before_text_and_omits_absent_system():
    img = ImagePart(media_type="image/png", data=b"pngbytes")
    req = LLMRequest(prompt="what is this?", images=(img,))
    params = anthropic_provider.build_message_params(req, model="claude-opus-5")

    assert params["model"] == "claude-opus-5"
    assert params["max_tokens"] == req.max_tokens
    assert "system" not in params
    content = params["messages"][0]["content"]
    assert content[0]["type"] == "image"
    assert content[0]["source"]["media_type"] == "image/png"
    assert content[-1] == {"type": "text", "text": "what is this?"}


def test_build_message_params_includes_system_when_present():
    req = LLMRequest(prompt="hi", system="be terse")
    params = anthropic_provider.build_message_params(req, model="claude-opus-5")
    assert params["system"] == "be terse"


def test_build_message_params_base64_has_no_newlines():
    img = ImagePart(media_type="image/png", data=b"\x00" * 200)
    req = LLMRequest(prompt="hi", images=(img,))
    params = anthropic_provider.build_message_params(req, model="claude-opus-5")
    data = params["messages"][0]["content"][0]["source"]["data"]
    assert "\n" not in data


class _FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeThinkingBlock:
    type = "thinking"
    thinking = "internal reasoning, never surfaced"


class _FakeUsage:
    def __init__(self, i, o):
        self.input_tokens = i
        self.output_tokens = o


class _FakeMessage:
    def __init__(self, content, model="claude-opus-5", stop_reason="end_turn", usage=(10, 5)):
        self.content = content
        self.model = model
        self.stop_reason = stop_reason
        self.usage = _FakeUsage(*usage)


def test_parse_message_concatenates_text_blocks_and_skips_thinking():
    msg = _FakeMessage([_FakeThinkingBlock(), _FakeTextBlock("hello "), _FakeTextBlock("world")])
    resp = anthropic_provider.parse_message(msg, provider_name="anthropic")
    assert resp.text == "hello world"
    assert "internal reasoning" not in resp.text
    assert resp.usage.input_tokens == 10
    assert resp.usage.output_tokens == 5
    assert resp.stop_reason == "end_turn"


def test_parse_message_raises_response_parse_error_on_shape_mismatch():
    with pytest.raises(LLMResponseParseError):
        anthropic_provider.parse_message(object(), provider_name="anthropic")


class _FakeAnthropicExc(Exception):
    def __init__(self, message, *, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _make_exc(name, **kwargs):
    cls = type(name, (_FakeAnthropicExc,), {})
    return cls("boom", **kwargs)


@pytest.mark.parametrize(
    "exc_name,status,expected",
    [
        ("AuthenticationError", 401, LLMAuthError),
        ("PermissionDeniedError", 403, LLMAuthError),
        ("RateLimitError", 429, LLMRateLimitError),
        ("BadRequestError", 400, LLMBadRequestError),
        ("NotFoundError", 404, LLMBadRequestError),
        ("APIConnectionError", None, LLMTransportError),
        ("APITimeoutError", None, LLMTransportError),
        ("SomeBrandNewExceptionType", None, LLMTransportError),  # unclassified -> safest bucket
    ],
)
def test_map_exception_classifies_by_name_and_status(exc_name, status, expected):
    exc = _make_exc(exc_name, status_code=status)
    mapped = anthropic_provider._map_exception(exc)
    assert isinstance(mapped, expected)


def test_map_exception_classifies_bare_5xx_status_as_server_error():
    exc = _make_exc("APIStatusError", status_code=503)
    assert isinstance(anthropic_provider._map_exception(exc), LLMServerError)


def test_map_exception_extracts_retry_after_when_present():
    class _Resp:
        headers = {"retry-after": "7"}

    exc = _make_exc("RateLimitError", status_code=429)
    exc.response = _Resp()
    mapped = anthropic_provider._map_exception(exc)
    assert isinstance(mapped, LLMRateLimitError)
    assert mapped.retry_after == 7.0


def test_anthropic_client_missing_api_key_raises_auth_error_without_calling_transport(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls = []

    def _transport(**kwargs):
        calls.append(kwargs)
        raise AssertionError("transport must not be called with no API key")

    client = anthropic_provider.AnthropicClient(transport=_transport)
    with pytest.raises(LLMAuthError):
        client.complete(LLMRequest(prompt="hi"))
    assert calls == []


def test_anthropic_client_success_path_with_fake_transport(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")

    def _transport(*, api_key, params):
        assert api_key == "sk-test-not-real"
        assert params["model"] == anthropic_provider.DEFAULT_MODEL
        return _FakeMessage([_FakeTextBlock("ok")])

    client = anthropic_provider.AnthropicClient(transport=_transport)
    resp = client.complete(LLMRequest(prompt="hi"))
    assert resp.text == "ok"
    assert resp.provider == "anthropic"


def test_anthropic_client_never_stores_the_api_key_on_self(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-super-secret-value")
    client = anthropic_provider.AnthropicClient(
        transport=lambda **kw: _FakeMessage([_FakeTextBlock("ok")])
    )
    client.complete(LLMRequest(prompt="hi"))
    for value in vars(client).values():
        assert "sk-super-secret-value" not in repr(value)


def test_anthropic_client_retries_transient_errors_then_succeeds(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    attempts = {"n": 0}
    sleeps = []

    def _transport(**kwargs):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise _make_exc("APIConnectionError")
        return _FakeMessage([_FakeTextBlock("recovered")])

    client = anthropic_provider.AnthropicClient(
        transport=_transport, max_retries=3, sleep_fn=lambda s: sleeps.append(s)
    )
    resp = client.complete(LLMRequest(prompt="hi"))
    assert resp.text == "recovered"
    assert attempts["n"] == 3
    assert len(sleeps) == 2  # slept before the 2nd and 3rd attempts


def test_anthropic_client_bad_request_is_not_retried(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    attempts = {"n": 0}

    def _transport(**kwargs):
        attempts["n"] += 1
        raise _make_exc("BadRequestError", status_code=400)

    client = anthropic_provider.AnthropicClient(
        transport=_transport, max_retries=3, sleep_fn=lambda s: (_ for _ in ()).throw(AssertionError("must not sleep"))
    )
    with pytest.raises(LLMBadRequestError):
        client.complete(LLMRequest(prompt="hi"))
    assert attempts["n"] == 1


def test_anthropic_client_exhausts_retries_and_raises_last_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    def _transport(**kwargs):
        raise _make_exc("APIConnectionError")

    client = anthropic_provider.AnthropicClient(
        transport=_transport, max_retries=2, sleep_fn=lambda s: None
    )
    with pytest.raises(LLMTransportError):
        client.complete(LLMRequest(prompt="hi"))


def test_anthropic_client_respects_already_typed_error_from_transport_without_remapping(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    def _transport(**kwargs):
        raise LLMBadRequestError("already classified by a test's fake transport")

    client = anthropic_provider.AnthropicClient(transport=_transport)
    with pytest.raises(LLMBadRequestError, match="already classified"):
        client.complete(LLMRequest(prompt="hi"))


def test_anthropic_client_response_parse_error_on_malformed_transport_return(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    client = anthropic_provider.AnthropicClient(transport=lambda **kw: object())
    with pytest.raises(LLMResponseParseError):
        client.complete(LLMRequest(prompt="hi"))


def test_default_transport_when_anthropic_package_is_unavailable_raises_clear_transport_error(monkeypatch):
    # `anthropic` is NOT in requirements.txt -- this repo's own hard rule is
    # that provider is never exercised for real. Force the "package not
    # importable" branch deterministically (setting sys.modules['anthropic']
    # to None makes `import anthropic` raise ImportError, the standard
    # technique for this -- see importlib docs) rather than actually
    # calling the default transport: if the `anthropic` package DOES happen
    # to be present in this environment's venv, calling the real default
    # transport unmocked would attempt an actual network request, which
    # must never happen in any test here, regardless of what's installed.
    monkeypatch.setitem(sys.modules, "anthropic", None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    client = anthropic_provider.AnthropicClient()  # default transport, not injected
    with pytest.raises(LLMTransportError, match="anthropic"):
        client.complete(LLMRequest(prompt="hi"))


# --------------------------------------------------------------------------- #
# llm/events.py
# --------------------------------------------------------------------------- #


def test_record_llm_call_success_writes_one_event_with_expected_payload(conn: sqlite3.Connection):
    req = LLMRequest(prompt="hello", system="sys", max_tokens=999, metadata={"provider": "null"})
    resp = LLMResponse(
        text="[]", model="null-stub-v1", provider="null",
        usage=LLMUsage(input_tokens=3, output_tokens=0), stop_reason="end_turn",
    )
    from llm.redact import RedactionReport

    event_id = events.record_llm_call(
        conn,
        request=req,
        outcome=events.LLMCallOutcome.ok(resp),
        redaction_report=RedactionReport(),
        purpose="test_call",
        actor_user_id=security.SYNTHETIC_USER_ID,
        case_id=None,
    )
    assert event_id

    row = conn.execute("SELECT kind, payload_json FROM events WHERE id = ?", (event_id,)).fetchone()
    assert row["kind"] == "llm.call"
    import json as _json

    payload = _json.loads(row["payload_json"])
    assert payload["purpose"] == "test_call"
    assert payload["success"] is True
    assert payload["model"] == "null-stub-v1"
    assert payload["input_tokens"] == 3
    assert payload["max_tokens"] == 999
    assert "hello" not in row["payload_json"]  # never the raw prompt text

    ok, bad_seq = audit.verify_chain(conn)
    assert ok, bad_seq


def test_record_llm_call_failure_writes_error_details_not_a_fabricated_success(conn: sqlite3.Connection):
    req = LLMRequest(prompt="hello")
    from llm.redact import RedactionReport

    exc = LLMTransportError("connection reset")
    event_id = events.record_llm_call(
        conn,
        request=req,
        outcome=events.LLMCallOutcome.failed(exc),
        redaction_report=RedactionReport(),
        purpose="test_call_failure",
        actor_user_id=security.SYNTHETIC_USER_ID,
        case_id=None,
    )
    import json as _json

    row = conn.execute("SELECT payload_json FROM events WHERE id = ?", (event_id,)).fetchone()
    payload = _json.loads(row["payload_json"])
    assert payload["success"] is False
    assert payload["error_type"] == "LLMTransportError"
    assert "connection reset" in payload["error_message"]
    assert "model" not in payload  # no fabricated success fields on a failure row


def test_record_llm_call_never_writes_the_prompt_text(conn: sqlite3.Connection):
    secret_prompt = "the applicant's actual full name is Robert Shattuck"
    req = LLMRequest(prompt=secret_prompt)
    resp = LLMResponse(
        text="[]", model="m", provider="null", usage=LLMUsage(1, 0), stop_reason="end_turn"
    )
    from llm.redact import RedactionReport

    events.record_llm_call(
        conn,
        request=req,
        outcome=events.LLMCallOutcome.ok(resp),
        redaction_report=RedactionReport(),
        purpose="p",
        actor_user_id=security.SYNTHETIC_USER_ID,
        case_id=None,
    )
    all_payloads = conn.execute("SELECT payload_json FROM events").fetchall()
    for row in all_payloads:
        assert "Robert Shattuck" not in row["payload_json"]
        assert secret_prompt not in row["payload_json"]
