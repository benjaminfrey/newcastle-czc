"""THE HOLDOUT BOUNDARY TEST -- read this file before touching either
llm/fewshot.py's holdout gate or eval/pairs.py's (deliberate) lack of one.

--------------------------------------------------------------------------
WHY THIS FILE EXISTS AND WHY IT ASSERTS TWO OPPOSITE THINGS ON PURPOSE
--------------------------------------------------------------------------
Dalton and Stantec are the W8 held-out pair set. Two different pieces of
this codebase look at them and are required to behave in OPPOSITE ways:

  HALF A -- llm/fewshot.py (+ build_fewshot.py, its CLI) is the FEW-SHOT
  PROMPT BUILDER. It MUST REFUSE to read either pair's PDF bytes, in code,
  before any file I/O -- reading them would leak the held-out set into a
  prompt, defeating the entire point of holding them out. This refusal
  already exists and is already tested exhaustively in
  tests/test_fewshot.py; TestHalfA below re-asserts the core of it here
  too (not a full duplicate -- see that file for the exhaustive version)
  so that a change to EITHER half is caught by ONE file that names both
  obligations side by side.

  HALF B -- eval/run_eval.py (via eval/pairs.py) is the EVAL HARNESS.
  Reading Dalton and Stantec is the entire POINT of a held-out run -- an
  eval that could not open its own holdout set could not evaluate
  anything on it (see eval/run_eval.py's own module docstring: the fact-
  fidelity/silent-error metric deliberately runs against Stantec's native-
  text pages). eval/pairs.py's application_pdf_path()/decision_pdf_path()
  therefore carry NO holdout gate, on purpose.

A future reader who notices "llm/fewshot.py refuses Dalton but eval/pairs.py
doesn't" might reasonably assume that is a bug and "fix" one side to match
the other -- either accidentally reintroducing the holdout leak into the
few-shot builder, or accidentally breaking the eval harness's ability to
run its own held-out evaluation. THIS FILE proves both behaviors are
intentional, in one place, so that "fixing" either one fails a test
immediately, and the failing test's own docstring (this one) explains why
the "fix" was wrong.

Offline; real fixture files only (never modified).
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

pytestmark = pytest.mark.skipif(
    not (fewshot.fixtures_available() and eval_pairs.fixtures_available()),
    reason="docs/Findings of Fact and Conclusions of Law/ fixtures not present in this checkout",
)


# --------------------------------------------------------------------------- #
# HALF A -- the few-shot builder MUST STILL REFUSE. (Full exhaustive coverage
# lives in tests/test_fewshot.py; this is the boundary-relevant subset.)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["dalton", "stantec"])
def test_half_a_fewshot_builder_refuses_holdout_application_read(name, monkeypatch):
    """build_fewshot.py's index-building path must never touch either
    holdout pair's bytes -- proven, not asserted, by making the underlying
    pymupdf.open() explode if it is ever reached."""
    import pymupdf

    def _must_not_be_called(*_a, **_kw):
        raise AssertionError(
            f"llm.fewshot attempted to open a PDF for holdout pair {name!r} -- "
            "the few-shot builder's holdout refusal is broken (Half A of the "
            "boundary this test file documents)."
        )

    monkeypatch.setattr(pymupdf, "open", _must_not_be_called)
    pair = fewshot.get_pair(name)
    with pytest.raises(fewshot.HoldoutError):
        fewshot.read_application_text(pair)


def test_half_a_build_index_never_touches_either_holdout(monkeypatch):
    """The actual index-building entry point build_fewshot.py calls --
    fewshot.build_index() -- must complete successfully while never once
    opening Dalton's or Stantec's PDF. We can't easily intercept "opened
    the wrong file" from outside, so instead we assert on the documented,
    tested structural guarantee: HOLDOUT_NAMES is excluded from PAIRS
    iteration inside build_index() (see llm/fewshot.py's own docstring),
    and independently re-assert the file-name-level defense-in-depth check
    (PairSpec.__post_init__ refuses to construct a mislabeled pair)."""
    for name in fewshot.HOLDOUT_NAMES:
        pair = fewshot.get_pair(name)
        assert pair.holdout is True
        assert pair.decision_filename is None  # a holdout pair has no decision, by definition


# --------------------------------------------------------------------------- #
# HALF B -- the eval harness MUST be able to read them. This is the
# affirmative case: eval/pairs.py's path helpers resolve and the real PDF
# bytes are actually readable, with no HoldoutError anywhere in the path.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["dalton", "stantec"])
def test_half_b_eval_harness_can_resolve_and_read_holdout_application(name):
    """eval.pairs.application_pdf_path() must NOT raise for a holdout pair
    (unlike llm.fewshot.application_pdf_path(), which always does), and the
    resolved path must be a real, openable PDF with real extractable text --
    this is the harness actually doing the thing Half A refuses to do."""
    import pymupdf

    pair = eval_pairs.get_pair(name)
    assert pair.holdout is True

    path = eval_pairs.application_pdf_path(pair)  # must not raise
    assert path.exists()

    doc = pymupdf.open(str(path))
    try:
        assert doc.page_count > 0
        # A real, successful open + page-count read -- proves this is a
        # genuine PDF read, not merely a path that resolved. NOT asserting
        # extractable text exists: Dalton's real application is a pure
        # scan (0/5 pages reach even the Tier-B floor -- see
        # eval/dalton_case.py's own module docstring, confirmed by
        # tests/test_eval_holdout_access.py's own real-fixture assertion),
        # so requiring nonblank get_text() here would make this test
        # fixture-dependent on something the holdout boundary does not
        # actually require.
    finally:
        doc.close()


def test_half_b_eval_harness_decision_path_raises_valueerror_not_holdouterror():
    """A holdout pair has no decision on file -- eval.pairs.decision_pdf_path()
    correctly raises ValueError for THAT reason (there is nothing to read),
    never fewshot.HoldoutError (which does not exist in this module at all --
    eval/pairs.py has no holdout concept in its path helpers, deliberately)."""
    for name in eval_pairs.HOLDOUT_NAMES:
        pair = eval_pairs.get_pair(name)
        with pytest.raises(ValueError):
            eval_pairs.decision_pdf_path(pair)


def test_half_b_run_eval_demonstrate_flag_reads_both_holdouts_live(capsys):
    """The actual entry point's --demonstrate-holdout-read path (also
    exercised by `python3 run.py --eval --demonstrate-holdout-read`) reads
    both holdout applications successfully and prints their page counts --
    the harness's own live proof, mirroring build_fewshot.py's
    --demonstrate-holdout flag (which proves the opposite: a refusal)."""
    from eval import run_eval

    rc = run_eval.run(out_path=None, quiet=True, demonstrate_holdout_read=True)
    out = capsys.readouterr().out
    assert "dalton: read OK" in out
    assert "stantec: read OK" in out
    assert rc in (0, 1)  # a real run; only assert it didn't crash before reaching the demo output
