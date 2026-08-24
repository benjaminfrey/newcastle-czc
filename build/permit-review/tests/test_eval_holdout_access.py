"""tests/test_eval_holdout_access.py -- THE HOLDOUT TRAP, made explicit.

Two paths in this codebase touch Dalton's/Stantec's real PDF bytes for two
DIFFERENT reasons, and must NOT be reconciled into one rule:

  1. `llm/fewshot.py` (the few-shot prompt index) MUST REFUSE to read
     either -- already covered by tests/test_fewshot.py; reasserted here,
     alongside its opposite, so nobody "fixes" one file without noticing
     the other exists.
  2. `eval/dalton_case.py` (the W8 eval harness) MUST BE ABLE to read
     Dalton's real bytes directly -- reading the held-out pair for real,
     offline evaluation is the entire point of a held-out run.

If a future change makes `eval/dalton_case.py` route through
`llm.fewshot.read_application_text()` (or otherwise inherit its refusal),
this file's second test fails loudly instead of the eval harness silently
losing its only real fixture. If a future change loosens `llm/fewshot.py`'s
refusal "to make the eval harness's job easier", this file's first test
fails loudly instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from llm import fewshot  # noqa: E402
from eval import dalton_case  # noqa: E402


def test_llm_fewshot_still_refuses_dalton_bytes():
    """Half 1 of the distinction: the few-shot builder's refusal is
    unaffected by eval/ existing at all."""
    pair = fewshot.get_pair("dalton")
    assert pair.holdout is True
    with pytest.raises(fewshot.HoldoutError):
        fewshot.read_application_text(pair)


def test_llm_fewshot_still_refuses_stantec_bytes():
    pair = fewshot.get_pair("stantec")
    assert pair.holdout is True
    with pytest.raises(fewshot.HoldoutError):
        fewshot.read_application_text(pair)


def test_eval_harness_can_read_dalton_bytes_directly():
    """Half 2 of the distinction: eval/dalton_case.py reads Dalton's real
    PDF directly (never through llm.fewshot), and this must actually work,
    not merely fail to raise. Skips (does not fail) if the real fixture
    folder isn't present on this checkout -- same convention as
    tests/test_pipeline.py's `requires_fixtures`."""
    if not dalton_case.DALTON_PDF.exists():
        pytest.skip("real Dalton fixture PDF not present under docs/")
    report = dalton_case.real_triage_report()
    assert report["page_count"] == 5
    # Real, measured fact about this real file -- not assumed. If a future
    # revision of the fixture ever gains a text layer, this assertion
    # should be revisited deliberately, not silently left stale.
    assert report["tier_census"]["C"] == 5
    assert report["pages_reaching_tier_b_floor_or_above"] == 0


def test_eval_harness_never_imports_or_calls_through_llm_fewshot():
    """Structural guard: eval/dalton_case.py's own module CODE (not its
    prose docstrings, which legitimately discuss llm.fewshot by name to
    explain the distinction) must not import or call through llm.fewshot
    -- it has its own, separate, direct read path (FIXTURES_DIR /
    DALTON_PDF), not a bypass built ON TOP of llm.fewshot's refusal."""
    import ast

    import eval.dalton_case as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
    assert not any(m == "fewshot" or m.endswith(".fewshot") for m in imported_modules), imported_modules
    assert "fewshot" not in mod.__dict__


def test_eval_dalton_pdf_and_llm_fewshot_dalton_pdf_are_the_same_real_file():
    """Both paths must ultimately point at the identical real fixture --
    this isn't two different "Dalton"s that happen to share a refusal
    story."""
    pair = fewshot.get_pair("dalton")
    assert dalton_case.DALTON_PDF.name == pair.application_filename
    assert dalton_case.DALTON_PDF.parent == fewshot.FIXTURES_DIR
