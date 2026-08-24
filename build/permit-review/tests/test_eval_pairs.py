"""Tests for eval/pairs.py -- eval/pairs.json's consistency against
llm.fewshot.PAIRS (the older, already-tested source of truth for this same
fixture set) and the basic pair-set shape the W8 eval brief asked for.

Offline; reads only eval/pairs.json and llm/fewshot.py's in-memory PAIRS
tuple (never opens a fixture PDF -- that is tests/test_eval_holdout_boundary.py's
job).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from eval import pairs as eval_pairs  # noqa: E402
from llm import fewshot  # noqa: E402


def test_exactly_six_matched_and_two_holdout():
    assert len(eval_pairs.MATCHED_PAIRS) == 6
    assert len(eval_pairs.HOLDOUT_PAIRS) == 2
    assert eval_pairs.HOLDOUT_NAMES == {"dalton", "stantec"}


def test_pair_names_match_fewshot_exactly():
    assert {p.name for p in eval_pairs.load_pairs()} == {p.name for p in fewshot.PAIRS}


@pytest.mark.parametrize("name", [p.name for p in fewshot.PAIRS])
def test_every_pair_field_matches_llm_fewshot_field_for_field(name):
    """The drift guard: eval/pairs.json must mirror llm.fewshot.PAIRS
    exactly for review_types / application_filename / decision_filename /
    holdout. If this fails, either eval/pairs.json was hand-edited out of
    sync, or llm/fewshot.py changed and eval/pairs.json needs the same
    change -- fix whichever one is actually wrong, don't just make this
    test pass.
    """
    fs_pair = fewshot.get_pair(name)
    ev_pair = eval_pairs.get_pair(name)
    assert ev_pair.holdout == fs_pair.holdout
    assert set(ev_pair.review_types) == set(fs_pair.review_types)
    assert ev_pair.application_filename == fs_pair.application_filename
    assert ev_pair.decision_filename == fs_pair.decision_filename


def test_excluded_decision_only_are_the_three_orphans():
    names = {e.name for e in eval_pairs.load_excluded_decision_only()}
    assert names == {"buehner", "midcoast_solar", "uberoi"}
    # None of the 3 orphans may also appear in pairs[] -- they are not pairs.
    assert names.isdisjoint({p.name for p in eval_pairs.load_pairs()})


def test_fixtures_dir_matches_llm_fewshot_fixtures_dir():
    assert eval_pairs.FIXTURES_DIR == fewshot.FIXTURES_DIR
