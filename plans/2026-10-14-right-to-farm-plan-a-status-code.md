# Right to Farm — Plan A: the fifth use-table status ("No Permit Required") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Article 2's use tables can carry a fifth status, `br` / ○ "No Permit Required", and every
reader of the legend accepts it. A cell that combines `br` with another code is refused everywhere.
The permit-review app refuses to build a ruleset containing a `br` cell, rather than misreport it.

**Architecture:** Both legend readers are changed first: the permit app's `ruleset_build/legend.py`
and the build's `use_table_changes.py`, kept in step by an agreement test. Their changes go in
before the legend in `source/article-02.typ`, so no commit leaves the suite red. Each consumer
guards the D3 rule (no `br` alongside another code in one cell): the PDF through a Typst `panic`,
the `.md` and Use Table Changes through `status_words`, and the app through `UseMatrixBuildError`.
No district cell uses `br` in this plan; Plan B (the ordinance) does that.

**Tech Stack:** Python 3.14 + pytest 9.0.3 + PyMuPDF 1.27.2.2 (build suite), Typst 0.14.2, the
permit-review app's own `.venv` (FastAPI stack; its tests are not in CI).

**Spec:** `specs/2026-10-07-right-to-farm-design.md` §3.2, §5.3 · decisions
`plans/2026-10-14-right-to-farm-decisions.md` R1–R5 · release-machinery spec
`specs/2026-10-07-release-deliverables-scope.md` decision D3 (combination illegal) and P15.

## Global Constraints

- Legend symbol **○** (U+25CB); data code **`br`**; legend row **`No Permit Required`**, authority **`—`** (U+2014) (R1, R2, R4).
- Note, verbatim: `Note: Uses without ●, ❶, ❷, ✪, or ○ are not allowed in this District. Uses marked ○ require no permit but must meet the standards of Article 7 Section 3.` (R3)
- `br` may not share a cell with any other code: a build error in every consumer (release spec D3).
- Do not edit `docs/*.pdf` (rule 3). Stage files by name; never `git add -A` / `git add .` (rule 2).
- Every commit message ends `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (rule 5). Use the model that actually wrote the change.
- Commit on `right-to-farm` only. **No push** (rule 6 is Ben's call).
- **Plan A must not ship alone** (R5): the Note cites Article 7 Section 3, which Plan B creates. Plan A and Plan B go out together in v1.2-draft.
- No district data changes in this plan: `source/article-02-data.json` is untouched.

## Review Focus

1. **A permit-free cell printed by the app as a prohibition.** `app/citation.py` prints "…is not allowed…" for any cell whose `permit` is falsy. A reasonable person expects the app to refuse a `br` cell, never to invert it. Pinned in Task 1, `test_a_br_cell_is_refused_not_misread`.
2. **`br` combined with another code** (`"br u"`, `"u br"`) in the data. The PDF, the `.md`/Use Table Changes and the app must each refuse with a message naming `br`. Pinned in Task 1 (app), Task 2 (`status_words`) and Task 3 (Typst).
3. **The v1.0 tag's four-code legend must still parse.** Release redlines and the agreement test read `v1.0:source/article-02.typ`. A reader that *requires* `br` breaks every redline against the baseline. Pinned in Tasks 1 and 2 by parsing the tag.
4. **The 13 district rectos still fit.** The extra legend row and the two-sentence Note lengthen column 3 of every use-table page. A district with long use standards could spill. Checked in Task 3: the page count is unchanged and the whole Note is on each legend page.
5. **A misleading wording for `br` in the `.md` and the Use Table Changes.** The generic rule would print "No Permit (—)". Expected: `No Permit Required`. Pinned in Task 2.

---

### Task 1: The permit app reads the fifth legend row and refuses `br` cells

**Files:**
- Modify: `build/permit-review/ruleset_build/legend.py` (the `EXPECTED_LEGEND` block, `_REQUIRED_CODES`, `_NOTE_RE`, the row loop in `parse_legend`, `_assert_matches_expected`)
- Modify: `build/permit-review/ruleset_build/build_use_matrix.py:140-180` (`_multi_status_cell`) and `:222-247` (single-status branch)
- Modify: `build/permit-review/CONTRACT.md` §4.4 (the table at ~line 666 and the paragraph after it)
- Modify: `build/permit-review/DECISIONS-NEEDED.md` (append a new entry)
- Test: `build/permit-review/tests/test_status_br.py` (new)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `ruleset_build.legend.parse_legend(typ_text) -> list[dict]` now returns 5 **or 6** rows. If the `.typ` has a `br` row, the result is u, rc, sp, ex, br, "" in that order. The `br` row is `{"code": "br", "permit": "No Permit", "permit_key": "no", "authority": "—", "authority_key": None, "glyph": "○", "allowed": True}`. Also new: `ruleset_build.legend.NOTE_WITH_BR: str` and `ruleset_build.legend.EXPECTED_BR_ROW: dict`. Task 2's agreement test relies on `permit + " Required" == "No Permit Required"` and `authority == "—"`.

- [ ] **Step 1: Set up the app's venv in this worktree** (it is gitignored, so the worktree has none)

```bash
cd build/permit-review && python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt && .venv/bin/python -m pytest tests/test_use_matrix.py -q; cd -
```
Expected: the existing use-matrix tests pass. If `requirements.txt` fails to install, stop and report; do not continue with system Python (BUILD-STATE.md §"If `.venv` is missing").

- [ ] **Step 2: Write the failing tests**

Create `build/permit-review/tests/test_status_br.py`:

```python
"""The fifth use-table status, `br` / ○ "No Permit Required" (Right to Farm,
plans/2026-10-14-right-to-farm-plan-a-status-code.md; decisions R1-R5).

The app reads the legend row but does not yet model a permit-free cell: its
citation sentence would print a `br` cell as "not allowed". Until the app plan
teaches it, building a ruleset that contains a `br` cell is refused
(DECISIONS-NEEDED.md D-0035). `br` combined with another code is refused for
good (release-machinery spec D3).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))

from ruleset_build.build_use_matrix import UseMatrixBuildError, build_use_matrix  # noqa: E402
from ruleset_build.legend import (  # noqa: E402
    EXPECTED_BR_ROW, NOTE_WITH_BR, LegendParseError, parse_legend,
)

SRC = REPO_ROOT / "source" / "article-02-data.json"

LEGEND_WITH_BR = """
#let glyphs = (u: "●", rc: "❶", sp: "❷", ex: "✪", br: "○")
USE TABLE LEGEND
status("u"), [Use Permit Required], [CEO],
status("rc"), [Residential Companion Permit Required], [CEO],
status("sp"), [Special Permit Required], [Planning Board],
status("ex"), [Expanded Use Permit Required], [Planning Board],
status("br"), [No Permit Required], [—],
)
text(size: 8pt)[Note: Uses without #status("u"), #status("rc"), #status("sp"), #status("ex"), or #status("br") are not allowed in this District. Uses marked #status("br") require no permit but must meet the standards of Article 7 Section 3.]
"""


def _v10_typ() -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", "v1.0:source/article-02.typ"],
        capture_output=True, text=True, check=True).stdout


def test_the_br_row_is_read():
    rows = parse_legend(LEGEND_WITH_BR)
    assert [r["code"] for r in rows] == ["u", "rc", "sp", "ex", "br", ""]
    br = next(r for r in rows if r["code"] == "br")
    assert br == EXPECTED_BR_ROW
    assert br["permit"] + " Required" == "No Permit Required"
    assert br["authority"] == "—" and br["authority_key"] is None


def test_the_two_sentence_note_is_read_whole():
    rows = parse_legend(LEGEND_WITH_BR)
    assert rows[-1]["note"] == NOTE_WITH_BR
    assert NOTE_WITH_BR == ("Uses without u, rc, sp, ex, or br are not allowed in this District. "
                            "Uses marked br require no permit but must meet the standards of "
                            "Article 7 Section 3.")


def test_the_v10_four_code_legend_still_parses():
    rows = parse_legend(_v10_typ())
    assert [r["code"] for r in rows] == ["u", "rc", "sp", "ex", ""]
    assert rows[-1]["note"] == "Uses without u, rc, sp, or ex are not allowed in this District."


def test_an_unknown_legend_code_is_refused():
    bad = LEGEND_WITH_BR.replace('br: "○")', 'br: "○", zz: "◆")').replace(
        'status("br"), [No Permit Required], [—],',
        'status("br"), [No Permit Required], [—],\nstatus("zz"), [Odd Permit Required], [CEO],')
    with pytest.raises(LegendParseError, match="zz"):
        parse_legend(bad)


def test_a_br_row_with_the_wrong_symbol_is_refused():
    with pytest.raises(LegendParseError, match="br"):
        parse_legend(LEGEND_WITH_BR.replace('br: "○"', 'br: "◎"'))


def _data_with(code: str, tmp_path: Path) -> tuple[Path, Path]:
    districts = json.loads(SRC.read_text(encoding="utf-8"))
    districts[0]["use_col1"][0]["entries"][0][1] = code
    data = tmp_path / "article-02-data.json"
    data.write_text(json.dumps(districts), encoding="utf-8")
    typ = tmp_path / "article-02.typ"
    typ.write_text(LEGEND_WITH_BR, encoding="utf-8")
    return data, typ


def test_a_br_cell_is_refused_not_misread(tmp_path):
    data, typ = _data_with("br", tmp_path)
    with pytest.raises(UseMatrixBuildError, match=r"br.*D-0035"):
        build_use_matrix(data, typ, "adopted")


@pytest.mark.parametrize("combo", ["br u", "u br", "rc br"])
def test_br_combined_with_another_code_is_refused(tmp_path, combo):
    data, typ = _data_with(combo, tmp_path)
    with pytest.raises(UseMatrixBuildError, match="br"):
        build_use_matrix(data, typ, "adopted")
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd build/permit-review && .venv/bin/python -m pytest tests/test_status_br.py -q; cd -`
Expected: collection ERROR, `ImportError: cannot import name 'EXPECTED_BR_ROW'`.

- [ ] **Step 4: Teach `legend.py` the optional row and the whole Note**

In `build/permit-review/ruleset_build/legend.py`:

Replace `_REQUIRED_CODES = ("u", "rc", "sp", "ex")` with:

```python
_REQUIRED_CODES = ("u", "rc", "sp", "ex")
# Right to Farm (plans/2026-10-14-right-to-farm-plan-a-status-code.md, R1-R4):
# a fifth, permit-free status. Optional, so the v1.0 tag's four-code legend
# still parses for redlines against the baseline.
_OPTIONAL_CODES = ("br",)
_CANONICAL_ORDER = _REQUIRED_CODES + _OPTIONAL_CODES

EXPECTED_BR_ROW: dict = {
    "code": "br",
    "permit": "No Permit",
    "permit_key": "no",
    "authority": "—",
    "authority_key": None,
    "glyph": "○",
    "allowed": True,
}
NOTE_WITH_BR = ("Uses without u, rc, sp, ex, or br are not allowed in this District. "
                "Uses marked br require no permit but must meet the standards of "
                "Article 7 Section 3.")
```

Replace the `_NOTE_RE` line with one that reads the Note to its closing bracket. The Note may now have two sentences:

```python
_NOTE_RE = re.compile(r"Note:\s*Uses without[^\]]*", re.IGNORECASE)
```

In `parse_legend`, locate the Note **before** the row loop, and scan rows only between the heading and the Note. Replace everything from `tail = typ_text[heading_match.end() :]` down to `rows.sort(...)` with:

```python
    tail = typ_text[heading_match.end() :]
    note_match = _NOTE_RE.search(tail)
    if not note_match:
        raise LegendParseError(
            "could not find the legend's 'Note: Uses without ...' sentence"
        )
    rows: list[dict] = []
    seen_codes: set[str] = set()
    for m in _ROW_RE.finditer(tail, 0, note_match.start()):
        code = m.group("code")
        if not code or code in seen_codes:
            continue
        if code not in _CANONICAL_ORDER:
            raise LegendParseError(
                f"USE TABLE LEGEND has an unknown status code {code!r} — "
                f"not one of {list(_CANONICAL_ORDER)}; CONTRACT.md §4.4 needs a decision first"
            )
        if code not in glyphs:
            raise LegendParseError(f"glyphs dict is missing code {code!r}")
        seen_codes.add(code)

        permit_full = " ".join(m.group("permit").split())
        authority = " ".join(m.group("authority").split())

        if not permit_full.endswith(" Required"):
            raise LegendParseError(
                f"legend row for {code!r} does not end in ' Required': {permit_full!r}"
            )
        permit = permit_full[: -len(" Required")]
        if not permit.endswith(" Permit"):
            raise LegendParseError(
                f"legend row for {code!r} permit label does not end in ' Permit': {permit!r}"
            )
        permit_key = slug(permit[: -len(" Permit")])

        rows.append(
            {
                "code": code,
                "permit": permit,
                "permit_key": permit_key,
                "authority": authority,
                "authority_key": slug(authority) or None,
                "glyph": glyphs[code],
                "allowed": True,
            }
        )

    found_codes = {r["code"] for r in rows}
    missing = [c for c in _REQUIRED_CODES if c not in found_codes]
    if missing:
        raise LegendParseError(
            f"USE TABLE LEGEND block did not yield rows for: {missing} "
            f"(found: {sorted(found_codes)})"
        )
    rows.sort(key=lambda r: _CANONICAL_ORDER.index(r["code"]))  # canonical order
```

Delete the old second `note_match = _NOTE_RE.search(tail)` block that followed the sort. Its "if not note_match: raise" is now above. Keep the note-text post-processing that follows it unchanged (`_STATUS_CALL_RE.sub`, strip `Note:`, collapse whitespace, add the trailing `.`).

`slug("—")` is `""`, hence `or None`. The four existing rows' `authority_key`s are non-empty, so they do not change.

Replace `_assert_matches_expected` with:

```python
def _assert_matches_expected(rows: list[dict]) -> None:
    by_code = {r["code"]: r for r in rows}
    has_br = "br" in by_code
    expected_rows = list(EXPECTED_LEGEND)
    if has_br:
        expected_rows.append(EXPECTED_BR_ROW)
        expected_rows = [dict(e, note=NOTE_WITH_BR) if e["code"] == "" else e
                         for e in expected_rows]
    for expected in expected_rows:
        actual = by_code.get(expected["code"])
        if actual is None:
            raise LegendParseError(f"parsed legend is missing code {expected['code']!r}")
        for key in expected:
            if actual.get(key) != expected[key]:
                raise LegendParseError(
                    f"parsed legend row {expected['code']!r} field {key!r} = "
                    f"{actual.get(key)!r}, expected {expected[key]!r} — "
                    f"article-02.typ's USE TABLE LEGEND changed and "
                    f"EXPECTED_LEGEND (CONTRACT.md §4.4) needs a matching update."
                )
```

Update `parse_legend`'s docstring: "Returns 5 row dicts (u, rc, sp, ex, and the "" prohibited row), or 6 when the legend carries the optional `br` row, in the order u, rc, sp, ex, br, ""."

- [ ] **Step 5: Refuse `br` cells in `build_use_matrix.py`**

In `_multi_status_cell`, inside `for part in parts:`, after the `if row is None or not part:` block, add:

```python
        if row["permit_key"] == "no":
            raise UseMatrixBuildError(
                f"{where}: use-status {code!r} combines {part!r} (No Permit Required) "
                f"with another status — not allowed (release-machinery spec D3)"
            )
```

In the single-status branch, after the `if legend_row is None:` block and before `by_code_counts[code] = ...`, add:

```python
            if legend_row["permit_key"] == "no":
                raise UseMatrixBuildError(
                    f"district {district_key!r}, use {use['label']!r}: status {code!r} "
                    f"(No Permit Required) is not yet modelled by the app — its citation "
                    f"would print the cell as a prohibition. See DECISIONS-NEEDED.md D-0035."
                )
```

- [ ] **Step 6: Run the new tests and the existing use-matrix tests**

Run: `cd build/permit-review && .venv/bin/python -m pytest tests/test_status_br.py tests/test_use_matrix.py -q; cd -`
Expected: all pass. (`test_use_matrix.py` still reads the working tree's four-code legend; Task 3 changes that, and its re-check is in Task 3 Step 7.)

- [ ] **Step 7: Make `test_use_matrix.py` legend-shape-agnostic, ahead of Task 3**

In `build/permit-review/tests/test_use_matrix.py`, replace the body of `test_legend_parses_from_the_typ_file`:

```python
def test_legend_parses_from_the_typ_file(legend_typ_text):
    rows = parse_legend(legend_typ_text)
    codes = {r["code"] for r in rows}
    # u, rc, sp, ex, "" always; br once Right to Farm's legend row is in (Plan A).
    assert KNOWN_STATUS_VALUES <= codes <= KNOWN_STATUS_VALUES | {"br"}
```

In `test_legend_matches_the_documented_mapping`, the prohibited row's `note` changes once `br` is in. Skip the `note` key there; `legend.py` itself asserts it:

```python
def test_legend_matches_the_documented_mapping(legend_typ_text):
    rows = parse_legend(legend_typ_text)
    by_code = {r["code"]: r for r in rows}
    for expected in EXPECTED_LEGEND:
        actual = by_code[expected["code"]]
        for key, value in expected.items():
            if key == "note":
                continue  # asserted inside parse_legend, which knows the br variant
            assert actual[key] == value, f"{expected['code']!r}.{key}"
```

Run: `cd build/permit-review && .venv/bin/python -m pytest -q; cd -`
Expected: the whole app suite passes. Record the pass count in the commit message.

- [ ] **Step 8: Document the fifth row in CONTRACT.md §4.4 and log D-0035**

In `build/permit-review/CONTRACT.md` §4.4, add a row under the `ex` row:

```markdown
| `br` | *(no permit)* — "No Permit Required" | `no` | — | `null` | `○` | true |
```

After the paragraph ending "…Glyphs come from the `#let glyphs = (...)` binding in the same file.", add:

```markdown
The `br` row is **optional** (Right to Farm, `plans/2026-10-14-right-to-farm-plan-a-status-code.md`):
the v1.0 legend has four codes, a draft legend five. With `br` present, the prohibited row's note
reads *"Uses without u, rc, sp, ex, or br are not allowed in this District. Uses marked br require no
permit but must meet the standards of Article 7 Section 3."* `br` may never share a cell with another
code (`UseMatrixBuildError`). A `br` cell is **refused** by `build_use_matrix.py` until the app models
a permit-free cell — see DECISIONS-NEEDED.md D-0035.
```

Confirm the next free decision number: `grep "^## D-00" build/permit-review/DECISIONS-NEEDED.md | tail -1` should print D-0034. If it prints a higher number, use the next one, and change `D-0035` everywhere in this task (the builder message and the tests' `match=`). Append to `build/permit-review/DECISIONS-NEEDED.md`:

```markdown
## D-0035 — The Code is gaining a permit-free use status (`br`, ○ "No Permit Required"), and the app cannot yet represent one

- **Status:** OPEN — for the permit-review app plan; not blocking the CZC.
- **Raised:** 2026-10-14, Right to Farm Plan A (`plans/2026-10-14-right-to-farm-plan-a-status-code.md`).
- **Blocking:** only a ruleset rebuild from draft source once a district cell carries `br` (Right to
  Farm Plan B). The binding ruleset is built from v1.0, which has no `br`.

**The fact.** Right to Farm adds a fifth status to Article 2's legend: ○ *No Permit Required*,
authority —. Its values were decided by the Planning Board chair on 2026-10-14 (decisions R1–R4).
Uses so marked are permitted without any permit, subject to Article 7 Section 3.

**Why the app refuses rather than renders.** `app/citation.py:required_review_row` treats a cell with
no `permit` as prohibited and prints "A <Use> use is not allowed in the <District> District." A `br`
cell would be printed as the opposite of what the Code says. So `ruleset_build/build_use_matrix.py`
refuses any `br` cell, naming this entry, and refuses `br` combined with another code for good
(release-machinery spec D3).

**What the app plan must decide.** The Required Review(s) row for a `br` cell (a row saying no permit
is required, or no row); the sentence (e.g. "A Farmstand use in the D1-Rural District is permitted
without a permit."); and what `app/reviews.py:required_reviews` returns for `permit` and
`permitting_authority`.
```

- [ ] **Step 9: Commit**

```bash
git add build/permit-review/ruleset_build/legend.py build/permit-review/ruleset_build/build_use_matrix.py build/permit-review/tests/test_status_br.py build/permit-review/tests/test_use_matrix.py build/permit-review/CONTRACT.md build/permit-review/DECISIONS-NEEDED.md
git commit -m "permit-review: read the optional br legend row; refuse br cells (D-0035)

<one line: app suite pass count from Step 7>

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The build's legend reader words `br` and refuses a combined cell

**Files:**
- Modify: `build/use_table_changes.py` (`status_words`, ~line 179)
- Test: `build/tests/test_use_table_changes.py` (append)

**Interfaces:**
- Consumes: Task 1's `parse_legend` (app). The existing `_agree()` helper in this test file calls it.
- Produces: `use_table_changes.status_words(code, legend) -> str` returns `"No Permit Required"` for `br`, and raises `use_table_changes.LegendError` (a `czc_diff.Refusal`) for any multi-code cell containing a code whose legend authority is `—`. `czc_md` calls `status_words` for every cell, so the `.md` build refuses too.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_use_table_changes.py`:

```python
# --- The fifth status, br / ○ "No Permit Required" (Right to Farm Plan A) ------

def _typ_with_br() -> str:
    """The v1.0 legend with Right to Farm's fifth row and Note (decisions R1-R4)."""
    t = _typ()
    t = t.replace('ex: "✪")', 'ex: "✪", br: "○")', 1)
    ex_row = 'status("ex"), [Expanded Use Permit Required], [Planning Board],'
    assert ex_row in t
    t = t.replace(ex_row, ex_row + '\n        status("br"), [No Permit Required], [—],', 1)
    old_note = ('Note: Uses without #status("u"), #status("rc"), #status("sp"), or '
                '#status("ex") are not allowed in this District]')
    assert old_note in t
    return t.replace(old_note,
                     'Note: Uses without #status("u"), #status("rc"), #status("sp"), '
                     '#status("ex"), or #status("br") are not allowed in this District. '
                     'Uses marked #status("br") require no permit but must meet the '
                     'standards of Article 7 Section 3.]', 1)


def test_the_br_row_is_read_and_both_readers_agree():
    leg = _agree(_typ_with_br())
    assert leg["rows"]["br"] == ("No Permit Required", "—")
    assert leg["glyphs"]["br"] == "○"


def test_br_is_worded_no_permit_required():
    leg = utc.parse_legend(_typ_with_br())
    assert utc.status_words("br", leg) == "No Permit Required"
    assert utc.status_words("u", leg) == "Use Permit (CEO)"          # unchanged


@pytest.mark.parametrize("combo", ["br u", "u br", "rc br"])
def test_br_combined_with_another_code_is_refused(combo):
    leg = utc.parse_legend(_typ_with_br())
    with pytest.raises(utc.LegendError, match="br"):
        utc.status_words(combo, leg)


def test_adding_br_is_reported_as_a_legend_change():
    delta = utc.legend_delta(utc.parse_legend(_typ()), utc.parse_legend(_typ_with_br()))
    assert "Status code `br` added: No Permit Required (—)." in delta
    assert any(s.startswith("The legend's note now reads") for s in delta)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_use_table_changes.py -q -k "br"`
Expected: `test_the_br_row_is_read_and_both_readers_agree` and `test_adding_br_is_reported_as_a_legend_change` PASS (both readers already handle it after Task 1). `test_br_is_worded_no_permit_required` FAILS: the result is `'No Permit (—)'`. The three `combined` cases FAIL: DID NOT RAISE.

- [ ] **Step 3: Implement**

Replace `status_words` in `build/use_table_changes.py` with:

```python
def status_words(code: str, legend: dict) -> str:
    """A status code in words. A blank status is "Not allowed": 450 of the 819
    cells carry it, and a blank in a report reads as "nothing here".

    A permit-free status (authority "—"; Right to Farm's `br`) reads as its
    own label, "No Permit Required" -- "No Permit (—)" would read as a permit.
    It may not share a cell with another status (release-machinery spec D3):
    that is refused, so the .md and this document fail closed with the PDF."""
    if not code.strip():
        return "Not allowed"
    codes = code.split()
    free = [c for c in codes if legend["rows"].get(c, ("", ""))[1] == "—"]
    if free and len(codes) > 1:
        raise LegendError(f"use status `{code}` combines `{free[0]}` (no permit required) "
                          "with another status -- not allowed (release-machinery spec D3)")
    parts = []
    for c in codes:
        row = legend["rows"].get(c)
        if row and row[1] == "—":
            parts.append(row[0])
        else:
            parts.append(f"{row[0].removesuffix(' Required')} ({row[1]})" if row
                         else f"`{c}` (not in the legend)")
    return " + ".join(parts)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_use_table_changes.py build/tests/test_czc_md.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add build/use_table_changes.py build/tests/test_use_table_changes.py
git commit -m "use tables: word br as No Permit Required; refuse br in a combined cell

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Article 2's legend gains the fifth row, its Note, and a Typst guard

**Files:**
- Modify: `source/article-02.typ:216` (glyph map), `:221-225` (`status`), `:325-331` (legend rows and Note)
- Test: `build/tests/test_status_br_typst.py` (new)
- Modify: `CLAUDE.md` (the Wave 4c open item), `HISTORY.md` (a dated entry)

**Interfaces:**
- Consumes: Tasks 1 and 2 (both readers accept the working tree's new legend, and `_agree` runs on it in `test_this_reader_agrees_with_the_permit_review_apps`).
- Produces: `status("br")` renders ○; `status("<anything containing br plus another code>")` panics with a message containing `br`. Plan B writes `"br"` into `source/article-02-data.json` cells.

- [ ] **Step 1: Record the "before" page count of Article 2** (for Step 6)

```bash
OUT_DIR="$TMPDIR/rtf-a-before" bash build/build-standalone.sh 2 v1.2-draft >/dev/null && python3 -c "import pymupdf,glob; p=glob.glob('$TMPDIR/rtf-a-before/*.pdf')[0]; print(pymupdf.open(p).page_count)" | tee "$TMPDIR/rtf-a-before.count"
```
Expected: one integer. Keep it.

- [ ] **Step 2: Write the failing Typst tests**

Create `build/tests/test_status_br_typst.py`:

```python
"""article-02.typ renders the fifth status (○ "No Permit Required", Right to
Farm Plan A) and refuses a cell combining `br` with another code (release-
machinery spec D3). Compiles a throwaway copy of the unit with edited data."""
import json
import shutil
import subprocess
from pathlib import Path

import pymupdf
import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "source"


def _compile(tmp_path: Path, code: str | None) -> subprocess.CompletedProcess:
    shutil.copy(SRC / "article-02.typ", tmp_path / "article-02.typ")
    data = json.loads((SRC / "article-02-data.json").read_text(encoding="utf-8"))
    if code is not None:
        data[0]["use_col1"][0]["entries"][0][1] = code
    (tmp_path / "article-02-data.json").write_text(json.dumps(data), encoding="utf-8")
    return subprocess.run(
        ["typst", "compile", "--root", str(tmp_path), "--font-path", str(REPO / "style" / "fonts"),
         str(tmp_path / "article-02.typ"), str(tmp_path / "out.pdf")],
        capture_output=True, text=True)


def test_the_legend_shows_the_fifth_row_and_the_new_note(tmp_path):
    r = _compile(tmp_path, None)
    assert r.returncode == 0, r.stderr
    doc = pymupdf.open(tmp_path / "out.pdf")
    legend_pages = [p for p in doc if "USE TABLE LEGEND" in p.get_text()]
    assert len(legend_pages) == 13
    for p in legend_pages:
        text = " ".join(p.get_text().split())
        assert "No Permit Required" in text
        # The glyph itself is not asserted: its extracted text depends on the
        # fonts present (Apple Symbols locally, a fallback on CI).
        assert "Uses marked" in text
        assert "require no permit but must meet the standards of Article 7 Section 3." in text


def test_a_br_cell_renders(tmp_path):
    r = _compile(tmp_path, "br")
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("combo", ["br u", "u br"])
def test_br_combined_with_another_code_is_refused(tmp_path, combo):
    r = _compile(tmp_path, combo)
    assert r.returncode != 0
    assert "br" in r.stderr and "cannot share a cell" in r.stderr
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_status_br_typst.py -q`
Expected: `test_the_legend_shows…` FAILS ("No Permit Required" not in text). `test_a_br_cell_renders` FAILS (Typst error: dictionary does not contain key "br"). The combined case FAILS on the message assert.

- [ ] **Step 4: Edit `source/article-02.typ`**

Glyph map (line 216):

```typst
#let glyphs = (u: "●", rc: "❶", sp: "❷", ex: "✪", br: "○")
```

`status` (lines 221–225). Add one comment line above it, keeping the existing comment, and a guard:

```typst
// `br` (○ No Permit Required, Right to Farm) may never share a cell with
// another status (release-machinery spec D3): that is a build error.
#let status(code) = {
  if code == none or code == "" { return [] }
  let parts = code.split(" ")
  if parts.len() > 1 and parts.contains("br") {
    panic("use status " + repr(code) + ": br (No Permit Required) cannot share a cell with another status")
  }
  text(font: glyph_font, fill: body_dark, size: 8pt,
       parts.map(c => glyphs.at(c)).join(h(2pt)))
}
```

Legend rows and Note (lines 325–331). Add the row after `ex`, and replace the Note:

```typst
        status("ex"), [Expanded Use Permit Required], [Planning Board],
        status("br"), [No Permit Required], [—],
      )
      v(2pt)
      text(size: 8pt)[Note: Uses without #status("u"), #status("rc"), #status("sp"), #status("ex"), or #status("br") are not allowed in this District. Uses marked #status("br") require no permit but must meet the standards of Article 7 Section 3.]
```

- [ ] **Step 5: Run the Typst tests and both legend readers' tests**

Run: `python3 -m pytest build/tests/test_status_br_typst.py build/tests/test_use_table_changes.py -q && (cd build/permit-review && .venv/bin/python -m pytest tests/test_use_matrix.py tests/test_status_br.py -q)`
Expected: all pass. `test_this_reader_agrees_with_the_permit_review_apps` now runs the agreement on the working tree's six-row legend.

- [ ] **Step 6: Check the 13 rectos still fit**

```bash
OUT_DIR="$TMPDIR/rtf-a-after" bash build/build-standalone.sh 2 v1.2-draft >/dev/null && python3 -c "import pymupdf,glob; p=glob.glob('$TMPDIR/rtf-a-after/*.pdf')[0]; print(pymupdf.open(p).page_count)" > "$TMPDIR/rtf-a-after.count"; diff "$TMPDIR/rtf-a-before.count" "$TMPDIR/rtf-a-after.count" && echo SAME
```
Expected: `SAME`. Then render each legend page and look at it:

```bash
python3 -c "
import pymupdf,glob
d=pymupdf.open(glob.glob('$TMPDIR/rtf-a-after/*.pdf')[0])
for i,p in enumerate(d):
    if 'USE TABLE LEGEND' in p.get_text(): p.get_pixmap(dpi=80).save(f'$TMPDIR/rtf-a-legend-{i+1:03}.png')
"
```
Open the 13 PNGs. Expected: ○ appears in the legend; column 3 ends above the footer on every page; nothing overlaps. If a page count changed or a column overflows, **stop and report** which district. Shrinking the Note or the type is a layout decision for Ben.

- [ ] **Step 7: Run the app suite, then the full build suite**

Run: `(cd build/permit-review && .venv/bin/python -m pytest -q)` — expected: all pass.
Run: `python3 -m pytest build/tests -q` (15–20 min; a subagent may run it and report the summary line).
Expected: all pass. Known risk: tests that pin Article 2's working-tree legend text or a `.typ` hash. If any fail, read the failure. If it pins the old legend deliberately, as a guard against unreviewed change, update it to the new values with a comment citing decisions R1–R4. If it is a real regression, stop and report.

- [ ] **Step 8: Update CLAUDE.md and HISTORY.md**

In `CLAUDE.md`, replace the Wave 4c bullet under "Open items" with:

```markdown
- **Wave 4c done on `right-to-farm`** — the fifth status `br` / ○ "No Permit Required" is in the
  legend and both readers (Plan A, decisions R1–R5). No cell uses it until Plan B; it ships only
  with Right to Farm (its Note cites Article 7 Section 3). The app refuses `br` cells (D-0035).
```

Append to `HISTORY.md` a short dated entry in the file's existing style: "2026-10-<dd> — Right to Farm Plan A (Wave 4c): …" naming the three commits and the D-0035 entry.

- [ ] **Step 9: Commit**

```bash
git add source/article-02.typ build/tests/test_status_br_typst.py CLAUDE.md HISTORY.md
git commit -m "Article 2: the fifth use status, ○ No Permit Required (Wave 4c, R1-R4)

Legend row, glyph, two-sentence Note, and a Typst guard refusing br in a
combined cell (release-machinery spec D3). No cell uses br yet (Plan B).
Article 2 standalone page count unchanged: <n>.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## After Plan A

- One fresh-context review of Plan A's three commits against this plan and decisions R1–R5, before Plan B starts.
- At release, `czc_diff` marks Article 2 **NEEDS-CALL**, because `article-02.typ` changed. The written call is **substantive**: the legend gained a status. That is recorded at release time (czc-release skill), not here.
