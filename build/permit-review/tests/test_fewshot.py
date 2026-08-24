"""Tests for llm/fewshot.py -- the 6-matched-pair few-shot index and its
ENFORCED-IN-CODE holdout of Dalton and Stantec.

Offline, no network, no LLM. Reads only the local, real
`docs/Findings of Fact and Conclusions of Law/` fixtures (never modified)
and re-derives the citation index via ruleset_build.verify_citations --
the same already-verified extraction `run.py --verify-citations` uses.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from llm import fewshot  # noqa: E402


# --------------------------------------------------------------------------- #
# The pair manifest itself
# --------------------------------------------------------------------------- #


def test_exactly_six_matched_pairs_and_two_holdouts():
    assert fewshot.MATCHED_PAIR_COUNT == 6
    assert fewshot.HOLDOUT_COUNT == 2
    assert len(fewshot.PAIRS) == 8


def test_holdout_names_are_dalton_and_stantec():
    assert fewshot.HOLDOUT_NAMES == {"dalton", "stantec"}
    for name in ("dalton", "stantec"):
        assert fewshot.get_pair(name).holdout is True


def test_matched_pairs_are_not_holdout_and_carry_review_types():
    for name in ("verney", "blood_and_sons", "shattuck", "profenno", "morrissey", "academy_hill"):
        pair = fewshot.get_pair(name)
        assert pair.holdout is False
        assert pair.decision_filename is not None
        assert pair.application_filename is not None
        assert len(pair.review_types) >= 1


def test_get_pair_unknown_name_raises_keyerror():
    with pytest.raises(KeyError):
        fewshot.get_pair("not-a-real-pair")


def test_fixtures_dir_resolves_to_the_real_shared_docs_folder():
    assert fewshot.FIXTURES_DIR.name == "Findings of Fact and Conclusions of Law"
    assert fewshot.FIXTURES_DIR.is_dir()


def test_every_non_holdout_pairs_files_actually_exist_on_disk():
    for pair in fewshot.PAIRS:
        if pair.holdout:
            continue
        assert (fewshot.FIXTURES_DIR / pair.application_filename).is_file(), pair.name
        assert (fewshot.FIXTURES_DIR / pair.decision_filename).is_file(), pair.name


def test_holdout_pairs_application_files_exist_but_no_decision_is_recorded():
    # The files exist on disk (that's WHY they're held out -- an
    # application with no matching decision yet) but PairSpec deliberately
    # carries no decision_filename for either.
    for name in ("dalton", "stantec"):
        pair = fewshot.get_pair(name)
        assert (fewshot.FIXTURES_DIR / pair.application_filename).is_file()
        assert pair.decision_filename is None


# --------------------------------------------------------------------------- #
# HOLDOUT ENFORCEMENT IN CODE -- the refusal itself, proven by attempting
# the read and asserting it raises, with the underlying file I/O primitive
# monkeypatched to blow up if it is EVER reached for a holdout pair.
# --------------------------------------------------------------------------- #


def test_holdout_pairs_refuse_application_read_before_touching_any_file(monkeypatch):
    import pymupdf

    def _must_not_be_called(*args, **kwargs):  # pragma: no cover -- must never run
        raise AssertionError(
            "pymupdf.open() was called for a holdout pair -- the holdout "
            "guard must refuse BEFORE any file I/O, not merely raise "
            "after reading."
        )

    monkeypatch.setattr(pymupdf, "open", _must_not_be_called)

    for name in ("dalton", "stantec"):
        pair = fewshot.get_pair(name)
        with pytest.raises(fewshot.HoldoutError):
            fewshot.read_application_text(pair)


def test_holdout_pairs_refuse_decision_read_too(monkeypatch):
    import pymupdf

    def _must_not_be_called(*args, **kwargs):  # pragma: no cover
        raise AssertionError("pymupdf.open() was called for a holdout pair's decision read")

    monkeypatch.setattr(pymupdf, "open", _must_not_be_called)

    for name in ("dalton", "stantec"):
        pair = fewshot.get_pair(name)
        # decision_filename is None for both -- application_pdf_path's
        # holdout check must fire BEFORE the "no decision on file" check,
        # so this still raises HoldoutError, not ValueError.
        with pytest.raises(fewshot.HoldoutError):
            fewshot.read_decision_text(pair)


def test_holdout_path_helpers_raise_before_resolving_a_path(monkeypatch):
    """application_pdf_path()/decision_pdf_path() themselves refuse --
    proving the gate sits ahead of path resolution, not just ahead of the
    eventual pymupdf.open() call."""
    for name in ("dalton", "stantec"):
        pair = fewshot.get_pair(name)
        with pytest.raises(fewshot.HoldoutError):
            fewshot.application_pdf_path(pair)
        with pytest.raises(fewshot.HoldoutError):
            fewshot.decision_pdf_path(pair)


def test_non_holdout_pair_application_read_actually_returns_real_text():
    # Positive control: the same function DOES work, and returns real
    # extracted text, for a non-holdout pair -- proving the holdout tests
    # above are testing a real gate, not a function that always raises.
    # Profenno's application (unlike some of the other 5, which are
    # scanned-image pages with no text layer -- ordinary Tier C behavior,
    # see ingest/triage.py) has real native text to assert against.
    pair = fewshot.get_pair("profenno")
    text = fewshot.read_application_text(pair)
    assert len(text) > 200
    assert "Profenno" in text or "Perkins Point" in text


# --------------------------------------------------------------------------- #
# The index itself
# --------------------------------------------------------------------------- #


def test_build_index_only_ever_uses_the_six_matched_pairs():
    index = fewshot.build_index()
    assert index  # non-empty against the real fixtures
    pair_names = {ex.pair_name for examples in index.values() for ex in examples}
    assert pair_names <= {
        "verney", "blood_and_sons", "shattuck", "profenno", "morrissey", "academy_hill",
    }
    assert "dalton" not in pair_names
    assert "stantec" not in pair_names


def test_build_index_keys_are_review_type_rule_id_pairs():
    index = fewshot.build_index()
    for review_type, rule_id in index:
        assert isinstance(review_type, str) and review_type
        assert isinstance(rule_id, str) and rule_id


def test_build_index_examples_carry_real_decision_text_and_provenance():
    index = fewshot.build_index()
    # Spot-check one bucket known to exist from the real fixtures.
    key = ("expanded_use", "art2")
    assert key in index
    examples = index[key]
    assert len(examples) >= 1
    ex = examples[0]
    assert ex.pair_name == "verney"
    assert ex.review_type == "expanded_use"
    assert ex.rule_id == "art2"
    assert len(ex.decision_excerpt) > 10
    assert "FoF & CoL" in ex.source_document
    assert ex.page >= 1


def test_lookup_respects_limit_and_returns_empty_tuple_for_unknown_key():
    index = fewshot.build_index()
    key = max(index, key=lambda k: len(index[k]))
    assert len(fewshot.lookup(index, key[0], key[1], limit=1)) == 1
    assert fewshot.lookup(index, "not-a-real-review-type", "not-a-real-rule") == ()


def test_build_index_accepts_pre_fetched_entries_without_re_querying():
    # Passing entries= directly (as build_fewshot.py's --demonstrate-holdout
    # path implicitly relies on, and as a caller wanting to avoid re-running
    # the citation extraction would) must produce the same shape.
    entries = fewshot.citation_entries()
    index = fewshot.build_index(entries=entries)
    assert index
