"""llm/protocol.py -- the ONE LLMClient interface every provider implements.

CONTRACT.md §2: "llm/ -- prompt assembly, provenance capture. Never renders
cites." This module is the seam: `engine/`, `ingest/vision.py`, and
`llm/fewshot.py` all depend on `LLMClient`, never on a concrete provider
class, so swapping `null` <-> `anthropic` <-> `recorded` <-> `local` is a
one-line change at the call site (llm/factory.py:get_client()).

Four providers implement this Protocol (W5 task brief, verbatim):
  - `anthropic` (llm/anthropic_provider.py) -- the real provider. Key read
    from the environment at RUNTIME only, never stored. NOT exercised by
    any test in this repo (no network, no key, ever) -- its correctness is
    verified by construction: request-shape, header-assembly, and
    error-mapping are unit-tested against a fake transport that never
    opens a socket.
  - `null` (llm/null.py) -- deterministic, offline, zero-cost. THE DEFAULT
    (llm/factory.py) so `run.py --selftest` and every test in this repo
    runs with no key and no network.
  - `recorded` (llm/recorded.py) -- replays a cassette file for
    deterministic, free evals. Cassettes are clearly labelled synthetic
    until a key exists to record a real one (llm/cassette.py).
  - `local` (llm/local.py) -- a documented stub for a future local model.
    Raises NotImplementedError when actually called, but still genuinely
    satisfies this Protocol (constructible, has the right method shape) --
    a caller can hold a `LLMClient` typed as `local` today and swap in a
    real implementation later without changing any calling code.

A `Protocol`, not an ABC: providers need only structurally match (duck
typing checked by `isinstance(x, LLMClient)` since this is `@runtime_checkable`),
so a test's fake client needs no inheritance -- it just needs the two
attributes below.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from llm.types import LLMRequest, LLMResponse


@runtime_checkable
class LLMClient(Protocol):
    """Every provider is: a name, and one method. `complete()` handles both
    text-only and vision calls -- a vision call is simply an LLMRequest
    with `images` populated (llm/types.py); there is no separate vision
    method, so ingest/vision.py's request path and a plain text call share
    one code path through every provider and every guard downstream.
    """

    provider_name: str

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Raises an llm.types.LLMError subclass on any failure (auth,
        rate limit, bad request, server error, transport, or a response
        the provider itself could not parse). Never returns a partial or
        guessed LLMResponse -- failure is always an exception, never a
        best-effort value (CONTRACT.md §1.1 S7's "no silent guessing",
        extended to the LLM boundary)."""
        ...
