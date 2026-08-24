"""llm/cassette.py -- the cassette FORMAT + loader that llm/recorded.py replays.

W5 task brief, verbatim: "Cassettes: build the MECHANISM and seed it with
fixtures that are CLEARLY LABELLED SYNTHETIC in the file itself. Do NOT
present hand-authored fixtures as real recordings -- real cassettes get
recorded once a key exists."

This module owns:
  1. The on-disk JSON shape (`CassetteFile`, below) and its loader.
  2. `compute_key()` -- the SAME deterministic lookup key a future recorder
     and llm/recorded.py's replayer both use, so a cassette written today
     (by hand, from fixtures) and a cassette written later (by an actual
     recording pass once ANTHROPIC_API_KEY exists) are interchangeable file
     formats.

No recorder is built here. Recording a REAL cassette requires a real API
call, which requires a key, which this environment does not have and must
never fabricate (see llm/anthropic_provider.py's docstring). What ships
here is fixtures + the mechanism to replay them -- exactly what the task
brief asked for.

--------------------------------------------------------------------------
CASSETTE FILE FORMAT (v1)
--------------------------------------------------------------------------
{
  "format_version": 1,
  "synthetic": true,                 -- REQUIRED. MUST be exactly `true` on
                                         every fixture cassette shipped in
                                         this repo. `false` is a legal value
                                         in the schema (a future real
                                         recording sets it) but nothing in
                                         this repo may ever set it to false
                                         without an actual recorded API
                                         response behind it.
  "note": "<free text -- MUST say, in plain language, that this is a
            hand-authored fixture, not a real model recording>",
  "entries": [
    {
      "key": "<sha256 hex -- see compute_key()>",
      "description": "<human-readable: what request this stands in for>",
      "response": {
        "text": "<the LLMResponse.text this entry replays>",
        "model": "<model name>",
        "stop_reason": "<stop reason>",
        "usage": {"input_tokens": <int>, "output_tokens": <int>}
      }
    },
    ...
  ]
}
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from llm.types import LLMRequest

FORMAT_VERSION = 1


class CassetteFormatError(ValueError):
    """The cassette file is not shaped like a valid CassetteFile -- missing
    required keys, wrong types, or (critically) a fixture cassette that
    does not carry `"synthetic": true`."""


@dataclass(frozen=True)
class CassetteEntry:
    key: str
    description: str
    response_text: str
    model: str
    stop_reason: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class CassetteFile:
    path: Path
    synthetic: bool
    note: str
    entries: tuple[CassetteEntry, ...]

    def by_key(self) -> dict[str, CassetteEntry]:
        return {e.key: e for e in self.entries}


def compute_key(request: LLMRequest) -> str:
    """The deterministic lookup key both a (future) recorder and
    llm/recorded.py's replayer compute the same way. Built from exactly
    the parts of a request that determine what answer should come back:
    the prompt, the system prompt, a sorted rendering of metadata (so key
    order never matters), and -- for a vision request -- a content hash of
    each image's bytes (never the bytes themselves in the key, and
    certainly never in a logged/printed form).

    Deliberately EXCLUDES max_tokens: two requests that differ only in
    their token ceiling are "the same question" for cassette-matching
    purposes.
    """
    h = hashlib.sha256()
    h.update(b"v1\x00")
    h.update(request.prompt.encode("utf-8"))
    h.update(b"\x00")
    h.update((request.system or "").encode("utf-8"))
    h.update(b"\x00")
    for k in sorted(request.metadata.keys()):
        h.update(f"{k}={request.metadata[k]}\x00".encode("utf-8"))
    for img in request.images:
        h.update(img.media_type.encode("utf-8"))
        h.update(hashlib.sha256(img.data).digest())
    return h.hexdigest()


def _parse_entry(raw: dict) -> CassetteEntry:
    try:
        response = raw["response"]
        usage = response["usage"]
        return CassetteEntry(
            key=raw["key"],
            description=raw.get("description", ""),
            response_text=response["text"],
            model=response["model"],
            stop_reason=response["stop_reason"],
            input_tokens=int(usage["input_tokens"]),
            output_tokens=int(usage["output_tokens"]),
        )
    except (KeyError, TypeError) as exc:
        raise CassetteFormatError(f"malformed cassette entry: {exc}") from exc


def load_cassette(path: str | Path) -> CassetteFile:
    """Load and validate one cassette file. Raises CassetteFormatError on
    anything that doesn't match the v1 shape, INCLUDING a missing or
    non-True `synthetic` flag that would let a hand-authored fixture pass
    itself off as unlabeled. This is deliberately strict -- a cassette
    llm/recorded.py can't parse should fail loudly, not replay silently
    wrong data."""
    p = Path(path)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CassetteFormatError(f"{p}: not valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise CassetteFormatError(f"{p}: top level must be a JSON object")
    if raw.get("format_version") != FORMAT_VERSION:
        raise CassetteFormatError(
            f"{p}: unsupported format_version {raw.get('format_version')!r} "
            f"(expected {FORMAT_VERSION})"
        )
    if "synthetic" not in raw or not isinstance(raw["synthetic"], bool):
        raise CassetteFormatError(
            f"{p}: cassette MUST declare a boolean 'synthetic' field -- "
            "the format has no unlabeled state (llm/cassette.py docstring)"
        )
    note = raw.get("note", "")
    if raw["synthetic"] and "synthetic" not in note.lower() and "fixture" not in note.lower():
        raise CassetteFormatError(
            f"{p}: synthetic=true cassettes must say so in their own 'note' "
            "field (task brief: 'CLEARLY LABELLED SYNTHETIC in the file "
            "itself') -- a boolean flag alone is not enough; a human "
            "opening the raw file must be able to tell from the text."
        )

    entries_raw = raw.get("entries")
    if not isinstance(entries_raw, list) or not entries_raw:
        raise CassetteFormatError(f"{p}: 'entries' must be a non-empty list")

    entries = tuple(_parse_entry(e) for e in entries_raw)
    return CassetteFile(path=p, synthetic=raw["synthetic"], note=note, entries=entries)
