"""llm/ -- prompt assembly, provenance capture. Never renders cites
(CONTRACT.md §2, §5.1).

    llm/types.py               LLMRequest / LLMResponse / ImagePart / errors
    llm/protocol.py            the ONE LLMClient Protocol every provider implements
    llm/null.py                default provider -- deterministic, offline, zero-cost
    llm/anthropic_provider.py  the real provider -- NOT exercised in this repo
    llm/recorded.py            cassette replay -- deterministic, free evals
    llm/cassette.py            the cassette FILE FORMAT + loader
    llm/local.py                documented stub seam for a future local model
    llm/factory.py             get_client(provider) -- the one place a name becomes a client
    llm/redact.py               known-token substitution (never numbers/dates/districts)
    llm/guards.py               the three output guards (numeral grounding, citation
                                stripping, conclusion-verb downgrade)
    llm/events.py               one `events` row per LLM call (D-0025's audit safeguard)
    llm/audited.py               LLMClient wrapper that makes the events.py write STRUCTURAL --
                                any call routed through it is audited, not just calls a site
                                remembered to log by hand (see its own docstring)
    llm/fewshot.py              the 6-matched-pair few-shot index, with enforced holdout
"""
