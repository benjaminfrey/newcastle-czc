"""llm/factory.py -- the one place that turns a provider NAME into an
LLMClient instance.

Resolution order: explicit `provider` argument > PERMIT_REVIEW_LLM_PROVIDER
environment variable > `"null"`. The default is `null` deliberately --
CONTRACT.md §1.1 S6 requires `--selftest` to run with no network and no
LLM, and every test in this repo constructs clients through here (or
directly, for provider-specific tests), so a bare `get_client()` with no
env var set must never touch a network or a key.
"""

from __future__ import annotations

import os

from llm.anthropic_provider import AnthropicClient
from llm.local import LocalClient
from llm.null import NullClient
from llm.protocol import LLMClient
from llm.recorded import RecordedClient

PROVIDER_ENV_VAR = "PERMIT_REVIEW_LLM_PROVIDER"
DEFAULT_PROVIDER = "null"

_KNOWN_PROVIDERS = frozenset({"null", "anthropic", "recorded", "local"})


class UnknownProviderError(ValueError):
    pass


def get_client(provider: str | None = None, **kwargs) -> LLMClient:
    """Construct an LLMClient for `provider` (or the environment default,
    or 'null'). Extra `**kwargs` are forwarded to the chosen provider's
    constructor -- e.g. `get_client('recorded', cassette=my_cassette)` or
    `get_client('anthropic', model='claude-opus-5')`. `get_client('recorded')`
    with no cassette is a caller error (RecordedClient requires one) and
    raises TypeError from the constructor itself, not from this function.
    """
    name = provider or os.environ.get(PROVIDER_ENV_VAR) or DEFAULT_PROVIDER
    if name not in _KNOWN_PROVIDERS:
        raise UnknownProviderError(
            f"unknown LLM provider {name!r}; expected one of {sorted(_KNOWN_PROVIDERS)}"
        )
    if name == "null":
        return NullClient(**kwargs)
    if name == "anthropic":
        return AnthropicClient(**kwargs)
    if name == "recorded":
        return RecordedClient(**kwargs)
    return LocalClient(**kwargs)
