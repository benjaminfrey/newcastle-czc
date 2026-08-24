"""llm/local.py -- a documented stub seam for a future local model.

W5 task brief, verbatim: "local -- a stub seam documented for a future
local model; may be a NotImplementedError shell, but the protocol must
genuinely admit it." This module is that shell: `LocalClient()` is a real,
constructible object with the right shape (`provider_name` + `complete()`),
so `isinstance(LocalClient(), llm.protocol.LLMClient)` is True and any code
written against the protocol -- llm/factory.py, ingest/vision.py, a future
engine/ call -- type-checks and wires up against it today. Only the actual
network/inference call is unimplemented.

Why this exists now, with nothing behind it: D-0025's option (c) was "defer
W5 and run a local vision model instead (... at a real accuracy cost)".
That option stays genuinely open only if a local provider is a real seam,
not an afterthought bolted on later -- so it is built now, alongside the
other three, even though nothing calls it yet.
"""

from __future__ import annotations

from llm.types import LLMRequest, LLMResponse


class LocalClient:
    provider_name = "local"

    def __init__(self, *, model_path: str | None = None) -> None:
        # Accepted but unused today -- the constructor shape a real local
        # provider (e.g. a llama.cpp / ONNX runtime binding) will need is
        # already here so callers don't have to change when it lands.
        self.model_path = model_path

    def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError(
            "llm.local.LocalClient is a documented stub (W5 task brief) -- no "
            "local model is wired in yet. Use provider='null' for offline "
            "testing or provider='recorded' for cassette-driven evals."
        )
