"""eval/ -- the W8 offline eval harness (BUILD-STATE.md W8: structural
recall + coverage, fact fidelity + silent_error_rate, over-conclusion rate,
prose usefulness -- reported SEPARATELY, never averaged). Precision was
removed from the structural metric (D-0030, 2026-08-24) -- see
eval/metrics.py's module docstring section 1 and DECISIONS-NEEDED.md.

Entry point: `eval/run_eval.py` (also reachable as `python3 run.py --eval`).

--------------------------------------------------------------------------
A NOTE ON HOW THIS PACKAGE WAS BUILT (READ BEFORE ASSUMING ONE FILE OWNS
ONE METRIC)
--------------------------------------------------------------------------
This package was written by two build passes running concurrently against
the same W8 task brief and the same directory -- the same kind of
collision BUILD-STATE.md already documents happening once before, during
W5. Rather than one pass overwriting the other, the pieces were
reconciled into one coherent harness (see eval/run_eval.py's own
docstring for how they compose):

  - `pairs.json` / `pairs.py` -- the matched application/decision pair set
    (6 matched + 2 holdout), mirroring `llm.fewshot.PAIRS`, with the
    deliberately UNGATED holdout path helpers the eval harness needs (see
    pairs.py's own docstring for why that gate is intentionally absent
    here and intentionally present in llm/fewshot.py).
  - `metrics.py` -- structural recall + coverage (Subdivision criteria set
    vs. real decision citations; coverage is a per-pair completeness audit,
    not a rate -- precision was removed, see D-0030), over-conclusion rate
    at the raw findings_nodes/DB level, and fact fidelity (grounding) +
    silent_error_rate for the native-text pairs (Morrissey, Profenno, and
    the Stantec holdout).
  - `over_conclusion.py` -- a second, complementary over-conclusion check
    at the RENDERED node level (render/case_findings.py,
    render/demo_findings.py, app.meeting's real drafted motion text, and
    several engine.review sentence-template stress cases), with an
    explicit motion-block carve-out for the house convention of drafting
    "To conclude that..." motion text for a human vote.
  - `dalton_case.py` -- the real Dalton held-out scenario: real triage,
    real (empty, because Dalton is a pure scan) Tier A/B extraction, a
    real subdivision walk against a real Dalton-labelled case, and an
    unusually explicit accounting of exactly what can and cannot be
    measured about Dalton offline -- read its module docstring before
    citing any number it produces.
  - `run_w8_partial.py` -- the original standalone driver for
    `over_conclusion.py` + `dalton_case.py` from that second build pass;
    still runnable directly (`python3 eval/run_w8_partial.py`), and also
    called from inside `run_eval.py` so its output is part of the one
    unified report rather than a second, separate report a caller has to
    remember to also run.

tests/test_eval_pairs.py guards `pairs.json` against drifting from
`llm.fewshot.PAIRS`. tests/test_eval_holdout_boundary.py asserts the
holdout boundary itself: llm/fewshot.py must keep refusing Dalton and
Stantec, and this package must keep being able to read them -- on
purpose, both halves, in one file, so a later edit that collapses the
distinction is caught immediately.
"""
