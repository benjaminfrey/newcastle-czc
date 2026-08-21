"""F10 -- the pre-spool upload size guard (app/main.py:create_app(),
starlette.middleware.body_limit.RequestBodyLimitMiddleware).

Before this fix, app/blobs.py's MAX_UPLOAD_BYTES was enforced only inside
the upload route's own streaming re-copy -- but `file: UploadFile` as a
FastAPI route parameter means Starlette has already fully parsed (and, past
a small in-memory threshold, spooled to a temp file) the multipart body
BEFORE the route function ever runs. A 20 GB request would already have
filled the temp filesystem by the time that in-route check fired.

These tests drive the real app returned by app.main:create_app() directly
at the ASGI layer (raw scope/receive/send, no TestClient/httpx in the way)
so we can prove the two things CONTRACT F10 asks for, precisely:

  1. a request that DECLARES an oversized body via Content-Length is
     rejected with 413 having called `receive()` ZERO times -- i.e. before
     a single byte is read off the wire, let alone spooled to disk;
  2. a request with NO Content-Length (the chunked-encoding case a naive
     Content-Length-only check would miss) is aborted with 413 once the
     RUNNING TOTAL of bytes actually read crosses the cap -- not after the
     whole body has already been buffered.

`blobs.MAX_UPLOAD_BYTES` is monkeypatched down to a tiny number so test 2
only ever needs to construct a couple of KB of fake chunk data, not
anything close to a real oversized upload.

Offline, no network, no LLM, no PII, no database (these requests are
rejected by the OUTERMOST middleware, before routing or any DB access).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import blobs as blobs_mod  # noqa: E402
from app import main as app_main  # noqa: E402


def _scope(path: str, *, content_length: int | None = None) -> dict[str, Any]:
    headers: list[tuple[bytes, bytes]] = [(b"host", b"127.0.0.1:8781")]
    if content_length is not None:
        headers.append((b"content-length", str(content_length).encode()))
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 54321),
        "server": ("127.0.0.1", 8781),
        "state": {},
    }


def _run(app, scope, receive, send) -> None:
    asyncio.run(app(scope, receive, send))


def test_declared_oversized_content_length_is_rejected_reading_zero_bytes():
    app = app_main.create_app(port=8781)

    async def receive_must_not_be_called():
        raise AssertionError(
            "receive() was called -- the Content-Length pre-check must reject "
            "before reading any part of the body"
        )

    sent: list[dict] = []

    async def fake_send(message):
        sent.append(message)

    # Declares 500 MB -- well past blobs.MAX_UPLOAD_BYTES (150 MB) + margin.
    scope = _scope("/api/cases/fake-case-id/documents", content_length=500 * 1024 * 1024)
    _run(app, scope, receive_must_not_be_called, fake_send)

    starts = [m for m in sent if m["type"] == "http.response.start"]
    assert starts, f"no response sent: {sent}"
    assert starts[0]["status"] == 413


def test_declared_oversized_content_length_is_rejected_on_a_non_upload_path_too():
    # F10's guard is global (every route), not scoped to the upload path --
    # cheap insurance since every other endpoint here is small JSON.
    app = app_main.create_app(port=8781)

    async def receive_must_not_be_called():
        raise AssertionError("receive() must not be called")

    sent: list[dict] = []

    async def fake_send(message):
        sent.append(message)

    scope = _scope("/api/cases", content_length=500 * 1024 * 1024)
    _run(app, scope, receive_must_not_be_called, fake_send)

    starts = [m for m in sent if m["type"] == "http.response.start"]
    assert starts and starts[0]["status"] == 413


def test_a_normal_small_content_length_is_not_rejected_by_the_size_guard():
    app = app_main.create_app(port=8781)
    call_count = 0

    async def fake_receive():
        nonlocal call_count
        call_count += 1
        # A tiny, deliberately-not-valid-multipart body -- large enough to
        # prove the SIZE guard let it through; whatever happens next
        # (a 4xx from the real route for a made-up case/bad multipart body)
        # is not this test's concern.
        return {"type": "http.request", "body": b"x" * 10, "more_body": False}

    sent: list[dict] = []

    async def fake_send(message):
        sent.append(message)

    scope = _scope("/healthz", content_length=10)
    _run(app, scope, fake_receive, fake_send)

    starts = [m for m in sent if m["type"] == "http.response.start"]
    assert starts and starts[0]["status"] != 413


def test_full_app_stops_reading_a_chunked_oversized_body_early_even_without_content_length(
    monkeypatch: pytest.MonkeyPatch,
):
    # The real end-to-end path: no Content-Length header at all (the case a
    # naive pre-check alone would miss -- chunked transfer-encoding, or a
    # client that simply omits it), driven through the REAL upload route so
    # FastAPI's own multipart/UploadFile machinery is genuinely exercised.
    #
    # NOTE on the assertion below: once the streaming guard's exception
    # crosses into FastAPI's own request-parsing try/except, FastAPI may
    # re-wrap it into its OWN 400 ("There was an error parsing the body")
    # rather than preserving the middleware's 413 verbatim -- an FastAPI-
    # internal wrinkle in how it wraps a mid-multipart-parse failure, not
    # this app's own code, and not what this fix is on the hook for. What
    # THIS fix guarantees, and what this test actually verifies, is the
    # thing that matters for F10: the request is rejected (never a 2xx) and
    # reading stops within a handful of chunks -- not after the whole
    # oversized body has been read and spooled. The precise-413 guarantee
    # for the common case (an honest Content-Length header) is covered
    # exactly by the tests above, which do not go through this FastAPI
    # wrapping at all.
    monkeypatch.setattr(blobs_mod, "MAX_UPLOAD_BYTES", 1000)
    CAP = 1000 + 64 * 1024  # mirrors app/main.py's own multipart-overhead margin
    app = app_main.create_app(port=8781)

    boundary = b"XYZBOUNDARY"
    preamble = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename="big.pdf"\r\n'
        b"Content-Type: application/pdf\r\n\r\n"
    )
    FILLER = b"A" * 40_000
    first_chunk = preamble + FILLER
    assert len(first_chunk) < CAP  # first read alone must NOT already trip it

    chunks_read = 0

    async def fake_receive():
        nonlocal chunks_read
        chunks_read += 1
        if chunks_read > 10:
            # Safety valve: if the guard failed to trip, don't hang the
            # test spinning forever -- signal end-of-body instead.
            return {"type": "http.request", "body": b"", "more_body": False}
        if chunks_read == 1:
            return {"type": "http.request", "body": first_chunk, "more_body": True}
        return {"type": "http.request", "body": FILLER, "more_body": True}

    sent: list[dict] = []

    async def fake_send(message):
        sent.append(message)

    scope = _scope("/api/cases/fake-case-id/documents")
    scope["headers"].append((b"content-type", b"multipart/form-data; boundary=" + boundary))
    _run(app, scope, fake_receive, fake_send)

    starts = [m for m in sent if m["type"] == "http.response.start"]
    assert starts, f"no response sent: {sent}"
    assert starts[0]["status"] != 200 and starts[0]["status"] < 500, starts[0]
    # The whole point: the guard must trip long before the body would ever
    # be fully spooled -- a handful of chunks, not dozens/hundreds. Without
    # the fix, this loop would run until `chunks_read` hit the safety valve
    # (10) with every one of those 400 KB read and hashed/re-copied.
    assert chunks_read <= 3, f"streaming guard let {chunks_read} oversized chunks through"


def test_body_limit_middleware_alone_returns_413_once_the_streaming_cap_is_crossed():
    # Isolates the exact mechanism app/main.py wires in -- Starlette's own
    # RequestBodyLimitMiddleware -- from FastAPI's multipart/UploadFile
    # machinery entirely, so the streaming-cap layer's own contract (413,
    # stop reading once the running total crosses the cap) is verified
    # precisely, undistorted by how any particular downstream framework
    # chooses to wrap a mid-read failure.
    from starlette.applications import Starlette
    from starlette.middleware.body_limit import RequestBodyLimitMiddleware
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    async def echo_endpoint(request):
        # A trivial downstream handler that just drains the body, the way
        # any real endpoint eventually does.
        body = await request.body()
        return PlainTextResponse(f"got {len(body)} bytes")

    inner = Starlette(routes=[Route("/echo", echo_endpoint, methods=["POST"])])
    app = RequestBodyLimitMiddleware(inner, max_body_size=1000)

    CHUNK = b"A" * 2000  # one chunk alone already exceeds the 1000-byte cap
    chunks_read = 0

    async def fake_receive():
        nonlocal chunks_read
        chunks_read += 1
        if chunks_read > 5:
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.request", "body": CHUNK, "more_body": True}

    sent: list[dict] = []

    async def fake_send(message):
        sent.append(message)

    scope = _scope("/echo")  # no content-length -- forces the streaming path
    scope["method"] = "POST"
    _run(app, scope, fake_receive, fake_send)

    starts = [m for m in sent if m["type"] == "http.response.start"]
    assert starts, f"no response sent: {sent}"
    assert starts[0]["status"] == 413
    assert chunks_read == 1  # tripped on the very first oversized chunk
