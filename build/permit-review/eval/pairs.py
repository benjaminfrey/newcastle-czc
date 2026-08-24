"""eval/pairs.py -- loads eval/pairs.json: the matched application/decision
pairs this W8 eval harness runs against, INCLUDING the two held-out ones
(Dalton, Stantec).

--------------------------------------------------------------------------
THE HOLDOUT BOUNDARY -- READ THIS BEFORE TOUCHING application_pdf_path() OR
decision_pdf_path() BELOW.
--------------------------------------------------------------------------
`llm/fewshot.py` (the few-shot PROMPT builder) and this module (the EVAL
HARNESS) look at the exact same fixture set and the exact same two
held-out names, but they have OPPOSITE obligations:

  - llm/fewshot.py MUST REFUSE to read Dalton's or Stantec's PDF bytes,
    anywhere, ever -- because doing so would leak the held-out pair into a
    few-shot prompt, which is the one thing a held-out eval set exists to
    prevent. That refusal lives in `llm.fewshot._require_readable()` and is
    unconditional: it fires for EVERY caller, with no override.

  - THIS module is the eval harness itself. Reading Dalton and Stantec is
    the entire POINT of a held-out run -- an eval that could not open its
    own holdout set could not evaluate anything on it. So
    application_pdf_path()/decision_pdf_path() below carry NO holdout gate.
    They resolve a path for ANY pair, holdout included, exactly the way a
    non-holdout pair resolves one.

Do not "fix" this by adding a gate here to match llm/fewshot.py, and do not
"fix" llm/fewshot.py by removing its gate to match this module -- they are
supposed to disagree. tests/test_eval_holdout_boundary.py asserts BOTH
halves in one file, heavily commented, precisely so a future edit that
collapses this distinction gets caught immediately rather than silently
reintroducing a leak (or silently breaking the eval).

--------------------------------------------------------------------------
WHERE eval/pairs.json COMES FROM
--------------------------------------------------------------------------
`llm/fewshot.py`'s `PAIRS` tuple is the older, already-tested source of
truth for this exact fixture set (6 matched pairs + 2 holdout, cross-
referenced by tax map/lot against every file in
`docs/Findings of Fact and Conclusions of Law/` -- see that module's own
docstring for the derivation). `eval/pairs.json` mirrors it field-for-field
rather than importing it directly, so the eval harness has its own
plain-data artifact (inspectable, diffable, not import-coupled to `llm/`)
-- but `tests/test_eval_pairs.py` asserts the mirror has not drifted:
every name/review_types/application_filename/decision_filename/holdout
tuple must match `llm.fewshot.PAIRS` exactly. If you deliberately change
one, change both and let that test tell you whether you did it consistently.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import APP_ROOT

EVAL_DIR = Path(__file__).resolve().parent
PAIRS_JSON_PATH = EVAL_DIR / "pairs.json"

# Same computation as llm.fewshot.FIXTURES_DIR -- both point at the one
# real, read-only fixture directory. Computed independently (not imported
# from llm.fewshot) so this module has no import-time dependency on `llm/`.
FIXTURES_DIR = APP_ROOT.parent.parent / "docs" / "Findings of Fact and Conclusions of Law"


@dataclass(frozen=True)
class PairRecord:
    name: str
    holdout: bool
    review_types: tuple[str, ...]
    application_filename: str | None
    decision_filename: str | None


@dataclass(frozen=True)
class ExcludedDecisionOnly:
    """A decision on file with no matching application -- not a pair (see
    llm/fewshot.py's own docstring: buehner, midcoast_solar, uberoi).
    Carried here purely for documentation/reporting; the eval harness never
    runs against these."""

    name: str
    decision_filename: str
    reason: str


def _load_raw() -> dict[str, Any]:
    with PAIRS_JSON_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_pairs() -> tuple[PairRecord, ...]:
    """All 8 pairs (6 matched + 2 holdout), in eval/pairs.json order."""
    raw = _load_raw()
    return tuple(
        PairRecord(
            name=p["name"],
            holdout=p["holdout"],
            review_types=tuple(p["review_types"]),
            application_filename=p["application_filename"],
            decision_filename=p["decision_filename"],
        )
        for p in raw["pairs"]
    )


def load_excluded_decision_only() -> tuple[ExcludedDecisionOnly, ...]:
    raw = _load_raw()
    return tuple(
        ExcludedDecisionOnly(name=e["name"], decision_filename=e["decision_filename"], reason=e["reason"])
        for e in raw["excluded_decision_only"]
    )


_ALL: tuple[PairRecord, ...] = load_pairs()
_BY_NAME: dict[str, PairRecord] = {p.name: p for p in _ALL}

MATCHED_PAIRS: tuple[PairRecord, ...] = tuple(p for p in _ALL if not p.holdout)
HOLDOUT_PAIRS: tuple[PairRecord, ...] = tuple(p for p in _ALL if p.holdout)
HOLDOUT_NAMES: frozenset[str] = frozenset(p.name for p in HOLDOUT_PAIRS)

assert len(MATCHED_PAIRS) == 6, f"expected 6 matched pairs, got {len(MATCHED_PAIRS)}"
assert len(HOLDOUT_PAIRS) == 2, f"expected 2 holdout pairs, got {len(HOLDOUT_PAIRS)}"
assert HOLDOUT_NAMES == {"dalton", "stantec"}, HOLDOUT_NAMES


def get_pair(name: str) -> PairRecord:
    try:
        return _BY_NAME[name]
    except KeyError:
        raise KeyError(f"no such pair {name!r}; known pairs: {sorted(_BY_NAME)}") from None


def fixtures_available() -> bool:
    """True iff every pair's application PDF this file names actually
    exists on disk under FIXTURES_DIR (decision PDFs too, for matched
    pairs). Mirrors llm.fewshot.fixtures_available()'s check, independently."""
    for pair in _ALL:
        if pair.application_filename and not (FIXTURES_DIR / pair.application_filename).exists():
            return False
        if pair.decision_filename and not (FIXTURES_DIR / pair.decision_filename).exists():
            return False
    return True


# --------------------------------------------------------------------------- #
# THE UNGATED PATH HELPERS. No HoldoutError. See the module docstring above
# -- this asymmetry with llm.fewshot.application_pdf_path()/
# decision_pdf_path() is deliberate, not an oversight.
# --------------------------------------------------------------------------- #


def application_pdf_path(pair: PairRecord) -> Path:
    if not pair.application_filename:
        raise ValueError(f"pair {pair.name!r} has no application_filename on record")
    return FIXTURES_DIR / pair.application_filename


def decision_pdf_path(pair: PairRecord) -> Path:
    if not pair.decision_filename:
        raise ValueError(
            f"pair {pair.name!r} has no decision_filename on record "
            f"(holdout={pair.holdout} -- true of both holdout pairs, by definition)"
        )
    return FIXTURES_DIR / pair.decision_filename
