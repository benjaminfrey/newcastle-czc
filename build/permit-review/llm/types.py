"""llm/types.py -- the request/response shapes every provider speaks.

ONE shape in, ONE shape out, regardless of provider (`null` | `anthropic` |
`recorded` | `local`) or call kind (text-only or vision). A caller building
a vision request just populates `images`; nothing about the protocol
differs from a text-only call (llm/protocol.py:LLMClient.complete()).

Design notes carried over from CONTRACT.md §5.1 and the W5 task brief:
  - `LLMResponse.text` is the model's RAW output. It is evidence, not an
    answer -- CONTRACT.md §5.1 forbids treating any model-authored string
    as a citation, and the task brief's output guards (llm/guards.py)
    forbid treating it as a conclusion. Nothing in this module applies
    either rule; that is deliberately downstream, so this module stays a
    plain data-shape layer every provider and every guard can agree on.
  - Images are passed as raw bytes (`ImagePart.data`), never pre-encoded.
    Each provider decides its own wire encoding (the real Anthropic
    provider base64-encodes at the transport boundary; a cassette records
    a content hash, never the bytes -- see llm/cassette.py). Keeping raw
    bytes here means no provider-specific encoding leaks into code that
    only builds requests (ingest/vision.py, llm/fewshot.py).
  - No field on LLMRequest or LLMResponse ever carries a credential.
    Authentication is a provider-construction concern (llm/anthropic_provider.py
    reads ANTHROPIC_API_KEY at call time only -- see that module's docstring).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class ImagePart:
    """One page image, rendered to bytes by the caller (ingest/vision.py
    renders PDF pages at 200 DPI via PyMuPDF; see VISION_DPI there).
    `media_type` is an IANA media type ('image/png'); this module never
    inspects or transcodes the bytes.
    """

    media_type: str
    data: bytes

    def __post_init__(self) -> None:
        if not self.media_type:
            raise ValueError("ImagePart.media_type must be non-empty")
        if not self.data:
            raise ValueError("ImagePart.data must be non-empty bytes")


@dataclass(frozen=True)
class LLMRequest:
    """One call's worth of input. `metadata` is free-form and is never sent
    to a provider's wire API -- it exists so a caller can carry routing/
    audit context (e.g. {"purpose": "vision_extract", "case_id": ...,
    "review_type": ..., "rule_id": ...}) through to llm/events.py's
    `events` row and to llm/recorded.py's cassette lookup key, without the
    provider needing to know what any of it means.
    """

    prompt: str
    system: str | None = None
    images: tuple[ImagePart, ...] = ()
    max_tokens: int = 4096
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.prompt:
            raise ValueError("LLMRequest.prompt must be non-empty")
        if self.max_tokens <= 0:
            raise ValueError(f"LLMRequest.max_tokens must be positive, got {self.max_tokens!r}")


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("LLMUsage token counts must be non-negative")


@dataclass(frozen=True)
class LLMResponse:
    """A provider's answer to ONE LLMRequest. `text` is raw model output --
    evidence, never an answer (see module docstring). `raw` is an optional
    provider-native payload for debugging/cassette recording; it is never
    read by llm/guards.py or ingest/vision.py, and MUST NOT be assumed to
    contain a credential (providers must not put one there)."""

    text: str
    model: str
    provider: str
    usage: LLMUsage
    stop_reason: str
    raw: Mapping[str, object] | None = None


# ---------------------------------------------------------------------------
# Errors -- every provider maps its own transport/SDK exceptions onto this
# family so callers (llm/events.py, ingest/vision.py) never need to know
# which provider raised. Most-specific-first, mirroring the Anthropic SDK's
# own exception chain (claude-api skill: NotFoundError -> RateLimitError ->
# APIStatusError -> APIConnectionError) so a caller written against THIS
# family transfers directly to a caller written against the real SDK.
# ---------------------------------------------------------------------------


class LLMError(RuntimeError):
    """Base class for every error this package raises. Never raised
    directly -- always one of the subclasses below."""


class LLMAuthError(LLMError):
    """Missing or rejected credentials. Never carries the credential value
    itself, even in the message."""


class LLMRateLimitError(LLMError):
    """429 / provider-side rate limiting. `retry_after` is seconds, when the
    provider supplied one."""

    def __init__(self, message: str, *, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class LLMBadRequestError(LLMError):
    """4xx other than auth/rate-limit -- a malformed request this module
    built. Not retryable; a bug, not a transient condition."""


class LLMServerError(LLMError):
    """5xx from the provider. Retryable."""


class LLMTransportError(LLMError):
    """Connection-level failure (DNS, TLS, timeout) before any HTTP status
    was available. Retryable."""


class LLMResponseParseError(LLMError):
    """The provider's response could not be parsed into an LLMResponse (or,
    for a vision/JSON-expecting caller, into the expected structure).
    Callers MUST treat this the same as "no data" -- CONTRACT.md's "no
    silent guessing" posture (S7) extended to model output: a malformed
    response yields zero candidates, never a partial or guessed one (see
    ingest/vision.py)."""
