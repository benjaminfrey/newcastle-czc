"""llm/events.py -- one `events` row per LLM call, per D-0025's non-negotiable
safeguard: "Every call writes an `events` row: provider, model, token
counts, prompt hash, redaction report. The record of what left the machine
must be complete and hash-chained."

Composes with app/audit.py:append_event() rather than reinventing the
hash-chain -- this module knows nothing about hashing or triggers, only
about what payload an LLM call should record. Caller still owns the
transaction (same convention as append_event() itself and app/blobs.py's
commit_blob(): "same BEGIN/COMMIT as the mutation it accompanies").

NEVER logs: the prompt text itself, image bytes, or the API key. The
payload carries a SHA-256 hash of the prompt (so a specific call can be
matched to a specific prompt later without the prompt ever having been
written to disk twice) and the redaction REPORT (counts per token class --
see llm/redact.py) rather than any redacted or unredacted value.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass

from app.audit import append_event
from llm.redact import RedactionReport
from llm.types import LLMRequest, LLMResponse

EVENT_KIND = "llm.call"


def _prompt_hash(request: LLMRequest) -> str:
    """SHA-256 of the exact prompt text sent (system + user prompt,
    concatenated with a NUL separator so the two can never collide into
    the same hash as a differently-split pair). Never the text itself."""
    h = hashlib.sha256()
    h.update((request.system or "").encode("utf-8"))
    h.update(b"\x00")
    h.update(request.prompt.encode("utf-8"))
    return h.hexdigest()


@dataclass(frozen=True)
class LLMCallOutcome:
    """What actually happened, for the caller to hand to record_llm_call()
    after a `client.complete(request)` either returns or raises. Exactly
    one of `response`/`error_message` is set."""

    response: LLMResponse | None
    error_type: str | None = None
    error_message: str | None = None

    @classmethod
    def ok(cls, response: LLMResponse) -> "LLMCallOutcome":
        return cls(response=response)

    @classmethod
    def failed(cls, exc: BaseException) -> "LLMCallOutcome":
        return cls(response=None, error_type=type(exc).__name__, error_message=str(exc))


def record_llm_call(
    conn: sqlite3.Connection,
    *,
    request: LLMRequest,
    outcome: LLMCallOutcome,
    redaction_report: RedactionReport,
    purpose: str,
    actor_user_id: str | None,
    case_id: str | None,
) -> str:
    """Append one `events` row for an LLM call, success or failure alike --
    D-0025's safeguard is about auditing everything that left the machine,
    not just the calls that worked. Returns the new event's id.

    `purpose` is a short caller-supplied tag (e.g. 'vision_extract',
    'fewshot_demo') distinct from LLMRequest.metadata['purpose'] only in
    that this is the one guaranteed to be recorded -- metadata is
    free-form and may or may not carry it.
    """
    payload: dict = {
        "purpose": purpose,
        "provider": request.metadata.get("provider", ""),
        "prompt_sha256": _prompt_hash(request),
        "image_count": len(request.images),
        "max_tokens": request.max_tokens,
        "redaction_report": redaction_report.as_payload(),
        "success": outcome.response is not None,
    }
    if outcome.response is not None:
        r = outcome.response
        payload.update(
            {
                "model": r.model,
                "provider": r.provider,
                "stop_reason": r.stop_reason,
                "input_tokens": r.usage.input_tokens,
                "output_tokens": r.usage.output_tokens,
            }
        )
    else:
        payload.update(
            {
                "error_type": outcome.error_type,
                "error_message": outcome.error_message,
            }
        )

    return append_event(
        conn,
        actor_user_id=actor_user_id,
        kind=EVENT_KIND,
        payload=payload,
        case_id=case_id,
    )
