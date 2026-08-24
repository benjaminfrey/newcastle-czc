"""llm/anthropic_provider.py -- the real provider. NOT exercised by any test
or by --selftest in this repo.

There is no ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN in this environment,
and this module NEVER invents, hardcodes, guesses, or stores one anywhere
(not in code, not in a fixture, not in a .env). `AnthropicClient.complete()`
reads `os.environ["ANTHROPIC_API_KEY"]` at CALL time, every call, and keeps
no copy of it on `self` beyond the single call in progress.

Because there is no key, this module's correctness cannot be proven by
actually calling the API. It is proven BY CONSTRUCTION instead, in three
pieces that are each independently pure and independently unit-tested
against fixtures -- none of them import the `anthropic` package or open a
socket:

    1. `build_message_params()`  -- LLMRequest -> the exact dict
       `client.messages.create(**params)` would take (model, max_tokens,
       messages[].content[] with base64 image blocks + a text block,
       optional system). Request-SHAPE correctness, tested against the
       Anthropic Python SDK's documented request shape (images before the
       text block in the same content array; base64 source with a
       media_type; system as a top-level field only when present).
    2. `parse_message()`  -- a duck-typed response object (matching the
       real SDK's `Message`: `.content[]` blocks with `.type`/`.text`,
       `.model`, `.usage.input_tokens`/`.output_tokens`, `.stop_reason`)
       -> LLMResponse. Tests build a plain fake object with those
       attributes; the real SDK's Message object has the same shape.
    3. `_map_exception()`  -- any exception -> an llm.types.LLMError
       subclass, by class name and (when present) `.status_code`/
       `.response.headers`, matching the real SDK's exception family
       (AuthenticationError, RateLimitError, BadRequestError/NotFoundError,
       APIStatusError >=500, APIConnectionError) documented in the
       claude-api skill's error-handling reference. Tests exercise this
       with small fake exception classes carrying the same attributes --
       the real `anthropic` package is never imported to run these tests.

`AnthropicClient.complete()` composes the three above through an
INJECTABLE `transport` callable (default: a real `client.messages.create`
call, behind a lazy `import anthropic` so this module -- and everything
that imports it, including llm/factory.py -- loads fine in an environment
where the `anthropic` package isn't even installed, which is the case
here: it is deliberately absent from requirements.txt until D-0025's
provider is actually turned on). Every test in this repo passes a FAKE
transport, so `complete()` is exercised end-to-end (params in, retry
policy, response out) without ever reaching `_default_transport`.
"""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

from llm.types import (
    LLMAuthError,
    LLMBadRequestError,
    LLMError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMResponseParseError,
    LLMServerError,
    LLMTransportError,
    LLMUsage,
)

DEFAULT_MODEL = "claude-opus-5"  # claude-api skill: current default model
API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
DEFAULT_MAX_RETRIES = 2  # matches the Anthropic SDK's own client default

Transport = Callable[..., Any]  # (*, api_key: str, params: dict) -> a Message-shaped object


# ---------------------------------------------------------------------------
# 1. Request shape -- pure, no network.
# ---------------------------------------------------------------------------


def build_message_params(request: LLMRequest, *, model: str) -> dict:
    """LLMRequest -> the exact kwargs `client.messages.create(**params)`
    would take. Images are placed before the text block in the same
    content array (claude-api skill's documented ordering for document/
    image content), base64-encoded with no embedded newlines. `system` is
    included only when the request actually has one -- the SDK treats a
    present-but-empty system differently from an absent one, and an
    LLMRequest with `system=None` should produce a request with no
    `system` key at all, not `system=""`.
    """
    content: list[dict] = []
    for img in request.images:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.media_type,
                    "data": base64.standard_b64encode(img.data).decode("ascii"),
                },
            }
        )
    content.append({"type": "text", "text": request.prompt})

    params: dict[str, Any] = {
        "model": model,
        "max_tokens": request.max_tokens,
        "messages": [{"role": "user", "content": content}],
    }
    if request.system:
        params["system"] = request.system
    return params


# ---------------------------------------------------------------------------
# 2. Response parsing -- pure, duck-typed against the SDK's Message shape.
# ---------------------------------------------------------------------------


def parse_message(message: Any, *, provider_name: str) -> LLMResponse:
    """Real `anthropic.types.Message` (or any object shaped like one) ->
    LLMResponse. Concatenates every `text`-type content block (a response
    may also carry `thinking` blocks, which are deliberately skipped here
    -- LLMResponse.text is the model's answer, never its reasoning).
    Raises LLMResponseParseError if the object isn't shaped as expected --
    NEVER returns a partially-filled LLMResponse.
    """
    try:
        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        usage = LLMUsage(
            input_tokens=int(message.usage.input_tokens),
            output_tokens=int(message.usage.output_tokens),
        )
        return LLMResponse(
            text=text,
            model=str(message.model),
            provider=provider_name,
            usage=usage,
            stop_reason=str(message.stop_reason),
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise LLMResponseParseError(
            f"could not parse an Anthropic Message-shaped response: {type(exc).__name__}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# 3. Error mapping -- pure, by exception class name + duck-typed attributes.
#    Matches the claude-api skill's documented exception chain:
#    NotFoundError -> RateLimitError -> APIStatusError(status_code) ->
#    APIConnectionError, plus AuthenticationError / PermissionDeniedError /
#    BadRequestError.
# ---------------------------------------------------------------------------

_AUTH_NAMES = frozenset({"AuthenticationError", "PermissionDeniedError"})
_RATE_LIMIT_NAMES = frozenset({"RateLimitError"})
_BAD_REQUEST_NAMES = frozenset({"BadRequestError", "NotFoundError", "UnprocessableEntityError"})
_TRANSPORT_NAMES = frozenset({"APIConnectionError", "APITimeoutError", "APIConnectionTimeoutError"})


def _retry_after_from(exc: BaseException) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw = None
    try:
        raw = headers.get("retry-after")
    except AttributeError:
        return None
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _map_exception(exc: BaseException) -> LLMError:
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    message = str(exc)

    if name in _AUTH_NAMES or status in (401, 403):
        return LLMAuthError(message)
    if name in _RATE_LIMIT_NAMES or status == 429:
        return LLMRateLimitError(message, retry_after=_retry_after_from(exc))
    if name in _BAD_REQUEST_NAMES or (status is not None and 400 <= status < 500):
        return LLMBadRequestError(message)
    if name in _TRANSPORT_NAMES:
        return LLMTransportError(message)
    if status is not None and status >= 500:
        return LLMServerError(message)
    if name == "APIStatusError":
        # A status-carrying error we didn't classify above (status is None,
        # which the real SDK shouldn't produce for this class, but handle
        # it rather than mis-bucket) -- treat as a server-side condition,
        # the safer of the two retryable buckets for an unclassified 5xx-ish
        # status error.
        return LLMServerError(message)
    # Anything else (an exception type this module has never seen) is
    # treated as a transport-level failure -- the safest "assume retryable,
    # assume nothing about the response" bucket, never assumed to be a bad
    # request (which would stop retries a real transient failure needs).
    return LLMTransportError(message)


# ---------------------------------------------------------------------------
# Default transport -- the only place this module touches the real SDK, and
# only when actually called (never at import time, never in a test, since
# every test injects its own `transport`).
# ---------------------------------------------------------------------------


def _default_transport(*, api_key: str, params: dict) -> Any:
    try:
        import anthropic  # local import: only required on this exact path
    except ImportError as exc:
        raise LLMTransportError(
            "the 'anthropic' package is not installed in this environment. "
            "Add it to requirements.txt and install it before selecting "
            "provider='anthropic' for a real call."
        ) from exc
    client = anthropic.Anthropic(api_key=api_key)
    return client.messages.create(**params)


_RETRYABLE = (LLMRateLimitError, LLMServerError, LLMTransportError)


@dataclass
class AnthropicClient:
    """The real provider. `transport` defaults to `_default_transport`
    (a real network call, lazily importing `anthropic`) but every caller in
    this repo -- and every test -- passes its own `transport`, so no test
    or --selftest run ever imports `anthropic` or opens a socket.
    """

    provider_name: str = "anthropic"
    model: str = DEFAULT_MODEL
    api_key_env_var: str = API_KEY_ENV_VAR
    max_retries: int = DEFAULT_MAX_RETRIES
    transport: Transport = _default_transport
    sleep_fn: Callable[[float], None] = time.sleep
    backoff_base_seconds: float = 1.0

    def complete(self, request: LLMRequest) -> LLMResponse:
        api_key = os.environ.get(self.api_key_env_var)
        if not api_key:
            raise LLMAuthError(
                f"{self.api_key_env_var} is not set. AnthropicClient reads "
                "credentials from the environment at call time only and "
                "never stores or logs them -- export the key before making "
                "a real call, or use provider='null'/'recorded' otherwise."
            )
        params = build_message_params(request, model=self.model)

        last_error: LLMError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                raw_message = self.transport(api_key=api_key, params=params)
            except LLMError:
                # The injected transport already mapped its own failure
                # (a test's fake transport raising e.g. LLMRateLimitError
                # directly) -- respect that classification as-is rather
                # than re-mapping an already-typed error.
                raise
            except Exception as exc:  # noqa: BLE001 -- mapped immediately below
                mapped = _map_exception(exc)
                last_error = mapped
                if isinstance(mapped, _RETRYABLE) and attempt < self.max_retries:
                    delay = (
                        mapped.retry_after
                        if isinstance(mapped, LLMRateLimitError) and mapped.retry_after is not None
                        else self.backoff_base_seconds * (2**attempt)
                    )
                    self.sleep_fn(delay)
                    continue
                raise mapped from exc
            return parse_message(raw_message, provider_name=self.provider_name)

        assert last_error is not None  # loop always returns or raises above
        raise last_error
