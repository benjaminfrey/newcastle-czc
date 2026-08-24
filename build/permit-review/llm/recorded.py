"""llm/recorded.py -- replays a llm/cassette.py CassetteFile.

Deterministic and free: no network, no key, same request -> same response,
every run. Used for reproducible evals (W8) and for exercising real-shaped
prompts end-to-end (llm/fewshot.py, ingest/vision.py) without spending
money or depending on network access.

A `RecordedClient` is built from an already-loaded CassetteFile (or a path,
via `RecordedClient.from_path()`), never from a raw dict -- so it can never
replay something that skipped llm/cassette.py's validation (including the
synthetic-labelling check).
"""

from __future__ import annotations

from pathlib import Path

from llm.cassette import CassetteEntry, CassetteFile, compute_key, load_cassette
from llm.types import LLMRequest, LLMResponse, LLMResponseParseError, LLMUsage


class CassetteMissError(LLMResponseParseError):
    """No entry in the loaded cassette matches this request's computed key.
    Subclasses LLMResponseParseError (not a new error family) because, from
    a caller's point of view, "the cassette has nothing for this input" is
    the same "treat as zero, never guess" situation as a malformed live
    response (llm/types.py:LLMResponseParseError's docstring)."""


class RecordedClient:
    provider_name = "recorded"

    def __init__(self, cassette: CassetteFile):
        self._cassette = cassette
        self._by_key: dict[str, CassetteEntry] = cassette.by_key()

    @classmethod
    def from_path(cls, path: str | Path) -> "RecordedClient":
        return cls(load_cassette(path))

    def complete(self, request: LLMRequest) -> LLMResponse:
        key = compute_key(request)
        entry = self._by_key.get(key)
        if entry is None:
            raise CassetteMissError(
                f"no cassette entry for computed key {key[:12]}... in "
                f"{self._cassette.path} ({len(self._by_key)} entries loaded). "
                "The request text/images/metadata must match a recorded "
                "entry exactly (llm/cassette.py:compute_key) -- this is not "
                "a fuzzy match by design."
            )
        return LLMResponse(
            text=entry.response_text,
            model=entry.model,
            provider=self.provider_name,
            usage=LLMUsage(input_tokens=entry.input_tokens, output_tokens=entry.output_tokens),
            stop_reason=entry.stop_reason,
            raw={"cassette_path": str(self._cassette.path), "cassette_key": key, "synthetic": self._cassette.synthetic},
        )
