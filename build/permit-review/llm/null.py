"""llm/null.py -- the deterministic, offline, zero-cost provider.

THE DEFAULT (llm/factory.py:get_client() with no argument and no
PERMIT_REVIEW_LLM_PROVIDER set). Every test in this repo, and
`run.py --selftest` (CONTRACT.md §1.1 S6: "MUST run with no network, no
LLM"), can construct an LLMClient and call it without ever touching a
network socket or an API key.

`complete()` never inspects `request.images` beyond counting them -- this
provider does no real vision or text understanding. It exists purely so
code that is WRITTEN against `LLMClient` (ingest/vision.py, llm/fewshot.py
few-shot-augmented prompts, a future engine/ call) has something safe to
run against by default. It is intentionally NOT a mock of what a real
model would say about the input; do not write a test that asserts on
NullClient's response *content* meaning anything -- assert on the shape
(it returns a well-formed empty field-candidate JSON envelope) instead.
"""

from __future__ import annotations

import hashlib

from llm.types import LLMRequest, LLMResponse, LLMUsage

MODEL_NAME = "null-stub-v1"

# A syntactically valid, semantically empty field-candidate envelope --
# valid JSON, an empty list, so a caller that always JSON-parses
# LLMResponse.text (e.g. ingest/vision.py) gets "zero candidates found",
# never a parse error, from the default provider.
_EMPTY_ENVELOPE = "[]"


class NullClient:
    provider_name = "null"

    def complete(self, request: LLMRequest) -> LLMResponse:
        # Deterministic: same request -> same (trivial) usage numbers,
        # every run, forever. The hash is never used for anything except
        # making that determinism auditable in a test; it is not a real
        # token count.
        prompt_hash = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()[:8]
        input_tokens = len(request.prompt.split()) + 85 * len(request.images)
        return LLMResponse(
            text=_EMPTY_ENVELOPE,
            model=MODEL_NAME,
            provider=self.provider_name,
            usage=LLMUsage(input_tokens=input_tokens, output_tokens=0),
            stop_reason="end_turn",
            raw={"null_provider": True, "prompt_hash8": prompt_hash},
        )
