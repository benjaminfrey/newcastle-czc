"""llm/audited.py -- guarantees an `events` row for every provider call
that goes through this wrapper, success or failure alike (D-0025's
non-negotiable safeguard, CONTRACT.md §3.3's audit chain, llm/events.py).

Why a wrapper instead of relying on each call site to remember to call
llm/events.py:record_llm_call() itself: `ingest/vision.py`'s first cut
called `client.complete(request)` directly and left the audit-row write as
a documented expectation on "the caller" -- correct in spirit, but nothing
enforced it, so a future call site could forget and no test would catch
it. Wrapping the client instead makes the audit STRUCTURAL: `AuditedClient`
itself satisfies `llm.protocol.LLMClient` (same `provider_name` + one
`complete()` method), so any code already written against the protocol --
`ingest/vision.py`, `llm/fewshot.py`, a future `engine/` call -- gets an
audited call for free by receiving one of these instead of a raw provider,
with no change to how it calls `.complete()`.

One event per call, always, in this order:
    1. call the wrapped (inner) provider's `complete()`
    2. write exactly one `events` row (kind "llm.call") recording the
       outcome -- success (model/tokens/stop_reason) or failure
       (error_type/error_message) -- via llm/events.py:record_llm_call()
    3. return the response, or re-raise the original exception unchanged

The write in step 2 happens whether step 1 succeeded or raised; a raised
`llm.types.LLMError` propagates to the caller exactly as it would without
this wrapper, only after the audit row lands. Never logs the prompt text,
image bytes, or a credential -- see llm/events.py's own docstring for the
payload shape.

Does NOT mutate the request sent to the inner provider -- `llm/recorded.py`
computes its cassette lookup key from the exact request (including
`metadata`), so this module never adds, removes, or reorders anything in
`request.metadata` before forwarding it to `inner.complete()`. The only
place a `provider` fallback is added is on the COPY passed to
`record_llm_call()` for the audit payload itself, and only when the
caller's original request did not already carry one -- see `_for_audit()`.
"""

from __future__ import annotations

import dataclasses
import sqlite3

from llm.events import LLMCallOutcome, record_llm_call
from llm.protocol import LLMClient
from llm.redact import RedactionReport, empty_report
from llm.types import LLMRequest, LLMResponse


@dataclasses.dataclass
class AuditedClient:
    """Wraps any `LLMClient` so every `complete()` call writes exactly one
    `events` row before returning (success) or re-raising (failure).

    `conn` is the caller's already-open, already-migrated connection
    (autocommit / WAL per app/db.py:connect()) -- this class opens no
    transaction of its own, matching llm/events.py:record_llm_call() and
    app/audit.py:append_event()'s own "caller owns the transaction"
    convention; on an autocommit connection with nothing else pending, the
    audit row simply commits itself, which is correct for a standalone
    LLM call.

    `redaction_report` defaults to `llm.redact.empty_report()` -- a vision
    call (whole page image, never text-redacted -- see llm/redact.py's own
    docstring on that honest limitation) has no text redaction to report;
    a text call that ran `llm.redact.redact_text()` first should pass the
    real `RedactionReport` it got back so the audit row reflects what
    actually left the machine.
    """

    inner: LLMClient
    conn: sqlite3.Connection
    purpose: str
    actor_user_id: str | None = None
    case_id: str | None = None
    redaction_report: RedactionReport = dataclasses.field(default_factory=empty_report)

    @property
    def provider_name(self) -> str:
        return self.inner.provider_name

    def complete(self, request: LLMRequest) -> LLMResponse:
        try:
            response = self.inner.complete(request)
        except Exception as exc:
            record_llm_call(
                self.conn,
                request=self._for_audit(request),
                outcome=LLMCallOutcome.failed(exc),
                redaction_report=self.redaction_report,
                purpose=self.purpose,
                actor_user_id=self.actor_user_id,
                case_id=self.case_id,
            )
            raise
        record_llm_call(
            self.conn,
            request=self._for_audit(request),
            outcome=LLMCallOutcome.ok(response),
            redaction_report=self.redaction_report,
            purpose=self.purpose,
            actor_user_id=self.actor_user_id,
            case_id=self.case_id,
        )
        return response

    def _for_audit(self, request: LLMRequest) -> LLMRequest:
        """The exact `request` if it already names a provider in its
        metadata; otherwise a shallow copy with `metadata["provider"]` set
        to the wrapped client's own `provider_name`, so a FAILED call's
        `events` row still records which provider was asked, even though
        `llm.events.record_llm_call()`'s success path gets `provider` from
        the response instead (which does not exist on a failure). This
        copy is used ONLY for the audit row -- `inner.complete()` above
        always receives the caller's original, unmodified `request`.
        """
        if "provider" in request.metadata:
            return request
        return dataclasses.replace(
            request, metadata={**request.metadata, "provider": self.inner.provider_name}
        )
