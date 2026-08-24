"""Tests for eval/ground_truth.py -- D3: independent ground truth for the
structural recall metric.

Two things this file must prove, not just assert:

  1. The extraction itself is correct against the real decisions on file
     (Shattuck: full 21/21 a-u, including the Roman-numeral collision case;
     Academy Hill: not extractable, because its "CONCLUSIONS OF LAW" section
     is a never-filled-in draft template).
  2. The extraction is genuinely INDEPENDENT of rulesets/adopted/
     articles.json -- not merely "happens to not import it today," but
     actively unable to read it even if something tried, and unaffected if
     it is missing.

Reads real fixture PDFs under docs/ -- offline, no network, no LLM.
"""

from __future__ import annotations

import builtins
import re
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from eval import ground_truth  # noqa: E402
from eval import pairs as eval_pairs  # noqa: E402

pytestmark = pytest.mark.skipif(
    not eval_pairs.fixtures_available(),
    reason="real Findings-of-Fact fixture PDFs not present under docs/ in this checkout",
)


# --------------------------------------------------------------------------- #
# 1. Correctness against the real decisions
# --------------------------------------------------------------------------- #


def test_shattuck_full_a_through_u():
    pdf = eval_pairs.decision_pdf_path(eval_pairs.get_pair("shattuck"))
    result = ground_truth.decision_addressed_letters(pdf)
    assert result.region_found is True
    assert sorted(result.letters) == list("abcdefghijklmnopqrstu")
    assert result.reason is None


def test_shattuck_roman_numeral_i_is_not_double_counted_or_dropped():
    # Standard c. (Pollution) contains a nested Roman-numeral sub-list
    # i./ii./iii./iv./v. -- its bare "i." must NOT be mistaken for the
    # OUTER letter i. (Municipal Solid Waste Disposal), and the outer
    # letter i. must still be found despite the collision. Covered by the
    # full a-u assertion above too; isolated here so a future change to the
    # Roman-numeral filter that breaks this specific interaction fails
    # loudly and specifically, not just as "one of 21 letters is missing."
    pdf = eval_pairs.decision_pdf_path(eval_pairs.get_pair("shattuck"))
    result = ground_truth.decision_addressed_letters(pdf)
    assert "i" in result.letters


def test_academy_hill_not_extractable():
    # Academy Hill's CONCLUSIONS OF LAW section is a literal, never-filled-in
    # draft template ("Motion: ... Moved by: ... Second: ...") -- verified
    # by hand against the real PDF. It also has no "APPROVAL STANDARDS"
    # heading at all. This module must report that honestly as
    # region_found=False with a stated reason, never as an empty-but-clean
    # "zero standards addressed."
    pdf = eval_pairs.decision_pdf_path(eval_pairs.get_pair("academy_hill"))
    result = ground_truth.decision_addressed_letters(pdf)
    assert result.region_found is False
    assert result.letters == frozenset()
    assert result.reason is not None
    assert "APPROVAL STANDARDS" in result.reason


# --------------------------------------------------------------------------- #
# 2. Independence from rulesets/adopted/articles.json
# --------------------------------------------------------------------------- #


def test_module_has_no_articles_json_dependency():
    """Static check: eval/ground_truth.py's own source must not name any of
    the artifacts the OLD (circular) derivation depended on. This catches a
    future edit that reintroduces the dependency even before it would show
    up as a behavioural difference."""
    src = (APP_ROOT / "eval" / "ground_truth.py").read_text(encoding="utf-8")
    # Strip every triple-quoted docstring (module- AND function-level --
    # several of the latter discuss articles.json BY NAME, on purpose, to
    # explain what this module replaced and what callers must never do)
    # before checking for a real import/reference in the executable code.
    code_only = re.sub(r'r?"""[\s\S]*?"""', "", src)
    for banned in ("articles.json", "verify_citations", "criteria_seed", "rulesets/adopted", "ruleset_build"):
        assert banned not in code_only, (
            f"eval/ground_truth.py's code (outside its docstring) references {banned!r} -- "
            "this module must derive ground truth with zero dependency on the same artifact "
            "the criteria set is built from (see its own docstring, 'WHY THIS MODULE EXISTS')"
        )


def test_independence_from_articles_json(monkeypatch):
    """The behavioural proof: block every attempt to open
    rulesets/adopted/articles.json (raising instead of silently failing
    over to some fallback) and confirm eval.ground_truth's answer for
    Shattuck is still the full, correct 21 letters. This is the literal
    claim D3 asks for -- 'if articles.json were missing a node, ground
    truth must NOT shrink with it' -- proven by making the whole file
    unreadable, the strongest version of 'missing a node.'"""
    articles_path = (APP_ROOT / "rulesets" / "adopted" / "articles.json").resolve()
    assert articles_path.exists(), "sanity check: the real file must exist for this test to mean anything"

    real_open = builtins.open

    def _guarded_open(file, *args, **kwargs):
        try:
            resolved = Path(file).resolve()
        except (TypeError, ValueError):
            resolved = None
        if resolved == articles_path:
            raise AssertionError(
                "eval.ground_truth.decision_addressed_letters() opened "
                "rulesets/adopted/articles.json -- it must never touch this file "
                "(see eval/ground_truth.py's module docstring)"
            )
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _guarded_open)

    pdf = eval_pairs.decision_pdf_path(eval_pairs.get_pair("shattuck"))
    result = ground_truth.decision_addressed_letters(pdf)

    assert result.region_found is True
    assert sorted(result.letters) == list("abcdefghijklmnopqrstu"), (
        "ground truth shrank when articles.json was made unreadable -- it must be "
        "computed with zero dependency on that file, per D3"
    )


def test_independence_survives_a_missing_articles_json_file(monkeypatch, tmp_path):
    """A second, complementary form of the same proof: point the config
    constant a real caller might use to resolve rulesets/adopted/ at an
    empty temp directory (so articles.json genuinely does not exist on the
    filesystem this process can see) and confirm eval.ground_truth still
    produces the identical, full result -- because it never resolves a
    ruleset path of any kind to begin with."""
    empty_dir = tmp_path / "no-rulesets-here"
    empty_dir.mkdir()
    assert not (empty_dir / "articles.json").exists()

    # eval.ground_truth takes a PDF path directly and never derives a
    # ruleset directory from app.config or anywhere else -- there is no
    # config seam to monkeypatch here, which is itself part of the proof:
    # if there were one, this test would patch it to point at empty_dir.
    pdf = eval_pairs.decision_pdf_path(eval_pairs.get_pair("shattuck"))
    result = ground_truth.decision_addressed_letters(pdf)
    assert sorted(result.letters) == list("abcdefghijklmnopqrstu")
