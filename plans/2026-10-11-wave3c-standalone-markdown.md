# Wave 3c — Honest Standalone Markdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every standalone Article `.md` an honest document — readable text, its tables as tables, a plain note wherever the PDF has a page the markdown cannot hold, Article 2's thirteen district pages as a generated appendix, and no stale draft chrome — and make the adopted edition's residue check read the markdown too.

**Architecture:** `build/typst_tables.py` converts Article 3's raw-Typst tables to markdown pipe tables, refusing anything outside the measured grammar. `build/czc_md.py` builds a standalone `.md` from an Article's prose and the ownership map: it keeps the Article's own text, drops build chrome, converts tables, writes pointer notes for native units, and (Article 2) appends a generated data appendix that reads the legend through `use_table_changes.parse_legend`. `build-standalone.sh` calls it instead of `cp`. The integrated `.md`'s pointer notes become edition-neutral, and `build-adopted.sh` runs the residue check over the adopted `.md` bytes.

**Tech Stack:** Python 3.14, bash, pytest; pandoc (only to prove the markdown parses).

**Spec:** `specs/2026-10-07-release-deliverables-scope.md` — §2 P12, §0 decisions D1, D2, D5. Ben Frey's rulings of 2026-10-10: fix Article 3's leftover footer in its own commit; Wave 3 continues as 3c (this plan).

## Global Constraints

- **NEVER commit unless explicitly asked.** The operator authorises this plan's commit steps: implementers commit locally, by name, on branch `wave3c-standalone-markdown`. Nothing is pushed. **No `git stash`.**
- **NEVER `git add -A` or `git add .`** — stage files by name, exactly as each commit step lists them.
- **Never modify anything in `docs/` or `releases/`.** In `source/`, ONLY the one line Task 1 changes, in its own commit. Tests write only under `tmp_path`.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` — **project standing rule 5**.
- Build tests: `python3 -m pytest build/tests -q` from the repository root. **470 tests** at the start of this wave, about 6 minutes. CI runs the same suite on the PR (Linux, GNU coreutils). **Report the count you actually see.**
- **Untouched by this wave** (prove with `git diff --stat main -- <these>` printing nothing): `build/adoption-map.json`, `build/adoption_map.py`, `build/baseline_selfcheck.py`, `build/section_map.py`, `build/normalize_for_diff.py`, `build/redline_resolve.py`, `build/redline-stage.sh`, `build/adoption-footer.sh`, `build/adoption-name.sh`, `build/use_table_changes.py`, `build/split-article-03.py`, `build/build-redline-standalone.sh`, `build/permit-review/`.
- **Never pin the live working tree.** Counts come from the `v1.0` tag or a tree materialised from it (`section_fixtures.copy_full_source`). Test versions use `v0.98-draft`.
- **Measured facts** (2026-10-11, HEAD 82d097b):
  - Article 3's four raw-Typst blocks all share one shape: optional `//` comment lines, `#block(breakable: false)[`, a caption line `TABLE n.m TITLE`, a blank line, `#table(`, `columns: (<fr list>),`, `align: left,`, ONE `table.header([..], …),` line, body rows one per line as `[cell], [cell], …,`, `)`, `]`. No colspan, rowspan, `table.cell`, `#` inside a cell, `$`, or backslash. Sizes (rows incl. header × cols): 3.4 = 15×2, 3.5 = 4×3, 3.2 = 9×2, 3.3 = 8×6. Table 3.3 has `*Construction*` and `*Hot Bituminous Pavement*` (Typst bold) with five empty `[]` cells each, and the characters ″ and ½. Cells contain `,` and `;`. The caption exists only inside the block.
  - The precedent for a markdown table in the Code is a caption paragraph `TABLE 4.1 SCREENING FORMULA`, a blank line, then a pipe table with a `| :--- |`-style left-aligned separator (Article 4:180-188; Article 4 pads its dashes, which is cosmetic).
  - Only Article 3 has whole-line HTML comments: three (lines 70 and 205 are the split markers `TYPE-PAGES` and `STREET-TYPE-EXHIBITS`; line 144 is an editorial note).
  - Every Article's frontmatter has exactly `article-number`, `article-name`, `footer-date`. Article 3's reads `footer-date: "Draft v0.2-draft"`; the others read `"Adopted: November 3, 2020"`. The build overrides `footer-date` for every PDF; only the `.md` shows the source value.
  - Article 2's data: 13 records; `left`/`right` panels of kind `lv` (label/value pairs), `list` (strings or `{text, sub}`), `para`; `matrix` is null for SD CONSERVATION, SD CAMPUS, SD MARINE; use cells in `use_col1`/`use_col2` categories, **819** in all; D4's TRANSPORTATION & UTILITIES category is split at a soft hyphen into an empty first half and `ITIES`. Strings contain `&` and `#` but no `|`, `*`, `_`, `<`, `>` or backslash.
  - `adopted_residue.check(text)` flags `CHROME` strings (case-insensitive) and demands `"drafts the official map"` be present — a string only Article 8 contains. Today the shipped adopted integrated `.md` would fail on `INTEGRATED DRAFT` (the pointer notes say "See the Integrated Draft PDF", `build-full-czc.sh:410, :418`) and `Draft v` (Article 3's frontmatter). `build-adopted.sh:170-174` passes the `.md` only as a FILENAME, never its bytes.

### Ten rulings this plan makes in writing

1. **Tables are converted, strictly.** `typst_tables.to_markdown` accepts exactly the measured grammar and returns `None` for anything else; `czc_md` then writes a pointer naming the table. Garbled output is never acceptable; a pointer is.
2. **Typst `*x*` becomes markdown `**x**`** (both mean bold); `|` in a cell is escaped; a cell containing `#`, `$` or `\` is refused (Typst code).
3. **The `.md`'s frontmatter keeps `article-number` and `article-name` and drops `footer-date`**, which is page chrome. A provenance line follows it, mode-aware and free of every residue string the mode must not carry: draft "a working draft (v…)", meeting "the Town Meeting edition (v…)", adopted "adopted (v…)".
4. **Every standalone `.md` says it is an extract**: "The integrated Code is the document the Town adopts; this extract does not govern." (Standing rule 4.)
5. **`md_completeness` is declared per Article** in the manifest: 1 `prose-only` (District Maps), 2 `prose-plus-appendix`, 3 `prose-only` (Type pages and Exhibits 3.1/3.2), 4–9 `complete`. `czc_md` refuses a declaration that contradicts the Article's units (units present but `complete`; no units but not `complete`; `prose-plus-appendix` with no appendix generator).
6. **A pointer note stands where each native unit sits in the PDF**, named by its manifest `label`: at the split marker for an at-marker unit, after the prose for an after-prose unit — and a short note under the provenance line names everything absent and says the PDF edition is authoritative for it.
7. **Article 2's appendix is generated from the same data file and the same legend the PDF uses**, reading the legend through `use_table_changes.parse_legend` (one reader), statuses in words via `use_table_changes.status_words`, D4's split category printed whole.
8. **Whole-line HTML comments are dropped** (build structure and editorial notes, invisible in the PDF). A split marker is replaced by its pointer note.
9. **The adopted edition's residue check reads the `.md` bytes for CHROME only** (not the "drafts the official map" damage check, which belongs to the PDF text). The integrated `.md`'s pointer notes become edition-neutral ("See the PDF edition of this Code"), so an adopted `.md` can pass.
10. **The standalone REDLINE `.md` is unchanged** — it is built from the plain-marked stage through `OUT_MD_SOURCE` and is a marked document, not an extract.

## Review Focus

1. **A converted table must keep every cell, in place** — a cell holding `,` or `;`, an empty cell, a bold cell, ″ or ½. Pinned in Task 2 (`test_the_four_tables_convert_exactly`).
2. **A table outside the grammar must become a pointer, never garbled text.** Pinned in Task 2 (`test_anything_unrecognised_is_refused`) and Task 3.
3. **The Article 2 appendix must carry all 819 cells with the right status words.** Pinned in Task 4.
4. **A failing `.md` build must not leave a half-written release directory.** Pinned in Task 3 (`test_a_refused_md_leaves_no_release_dir`).
5. **The residue check must not flag the Code's own "drafts the official map" in a `.md`, and must flag real chrome.** Pinned in Task 5.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `source/article-03-streets-roads-driveways.md` | Article 3 | One line: `footer-date` (Task 1, own commit) |
| `build/structural_note.py`, `build/czc_diff.py`, `build/redline-text.py` | Carried wording slips + bold-on-bold | Task 1 |
| `build/typst_tables.py` | **New.** Raw-Typst table → markdown | Task 2 |
| `build/czc_md.py` | **New.** Honest standalone markdown | Tasks 3, 4 |
| `build/article-manifest.json` | Ownership map | `md_completeness` per Article (Task 3) |
| `build/build-standalone.sh` | Standalone build | `.md` from `czc_md.py` (Task 3) |
| `build/build-full-czc.sh` | Integrated build | Edition-neutral pointer wording (Task 5) |
| `build/adopted_residue.py`, `build/build-adopted.sh` | Adopted gate | Residue-only scan of the `.md` (Task 5) |
| `build/tests/test_typst_tables.py`, `build/tests/test_czc_md.py` | **New** | Tasks 2–4 |
| `build/tests/test_build_adopted.py`, `build/tests/test_redline_plain.py`, `build/tests/test_structural_note.py` | Extended | Tasks 1, 5 |

---

## Task 1: Article 3's footer, and the slips carried from Wave 3b

**Files:**
- Modify: `source/article-03-streets-roads-driveways.md` (line 4 only) — **its own commit**
- Modify: `build/structural_note.py`, `build/czc_diff.py`, `build/redline-text.py`
- Modify: `build/tests/test_structural_note.py`, `build/tests/test_redline_plain.py`

- [ ] **Step 1: Fix the footer (own commit)**

Change line 4 of `source/article-03-streets-roads-driveways.md` from `footer-date: "Draft v0.2-draft"` to `footer-date: "Adopted: September 14, 2026"` (the date Article 3 was adopted, matching how the other Articles' footers read). Nothing else in `source/`. Verify `python3 build/czc_diff.py --old v1.0` still reports Article 3 `UNCHANGED` (footer-date is chrome) and commit alone:

```bash
git add source/article-03-streets-roads-driveways.md
git commit -m "$(cat <<'EOF'
source: Article 3's footer no longer reads "Draft v0.2-draft"

The frontmatter footer-date was left over from the second draft. The build
overrides it on every PDF page, but the markdown deliverables carried it -- it
sits in the adopted v1.0 edition's markdown -- and it trips the adopted
edition's draft-chrome check. It now reads "Adopted: September 14, 2026", the
date Article 3 was adopted, matching how the other Articles' footers read.
Page chrome only: the change determination does not count it. Approved by Ben
Frey, 2026-10-10.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 2: Write the failing tests for the slips**

Append to `build/tests/test_structural_note.py` (reuse its existing `_note` helper and `tree` fixture):

```python
def test_a_layout_change_note_reads_in_the_plural_for_plural_pages(tmp_path, tree):
    p = tree / "article-02.typ"
    p.write_text(p.read_text() + "\n// x\n")
    text, _ = _note(tmp_path, "--scope", "article:2", "--old", "v1.0", "--new-dir", str(tree))
    text = _flat(text)                       # PDF text wraps; the file's own helper joins it
    assert "their layout changed" in text
    assert "its layout changed" not in text
    assert "lives in this file" not in text
    assert "The use-table legend is part of these pages." in text
```

Append to `build/tests/test_redline_plain.py`:

```python
def test_an_added_line_that_starts_bold_has_no_quadruple_asterisks(tmp_path):
    """v0.21-draft -> v0.22-draft added lines such as '**Planting.** Street trees ...';
    wrapping them in ** produced '****Planting.**'."""
    import subprocess as sp
    def show(ref):
        return sp.run(["git", "-C", str(REPO), "show",
                       f"{ref}:source/article-03-streets-roads-driveways.md"],
                      capture_output=True, text=True, check=True).stdout
    out, _ = run_files(tmp_path, show("v0.21-draft"), show("v0.22-draft"), "--source", "--plain")
    assert "****" not in out
    assert "Planting." in out
```

(Read `test_redline_plain.py`'s top for the exact names of `REPO` and the `run_files` helper's return shape; adapt only those names.)

- [ ] **Step 3: Run them to verify they fail**

Run: `python3 -m pytest build/tests/test_structural_note.py build/tests/test_redline_plain.py -k "plural or quadruple" -v` — expected: both FAIL.

- [ ] **Step 4: Fix the slips**

- `build/structural_note.py` (around line 332, where "a layout unit changed." is rewritten to "its layout changed."): when the unit's label names plural pages (it begins "the thirteen", "the ten", or otherwise ends in "pages"/"Maps"), say "their layout changed"; else "its layout changed".
- `build/czc_diff.py` (lines 572-574): the layout-unit note's parenthetical for `article-02.typ` reads "(The use-table legend is part of these pages.)" instead of "(The use-table legend lives in this file.)".
- `build/redline-text.py`: in plain mode, `wrap_bold` must not wrap a core that already contains `**` in another `**…**`. When the core contains `**`, wrap with `__…__` instead (pandoc and GFM nest `__` around `**` correctly, and no `****` appears). Leave PDF mode untouched.

- [ ] **Step 5: Run, prove the untouched files, run the full suite, commit**

```bash
python3 -m pytest build/tests/test_structural_note.py build/tests/test_redline_plain.py build/tests/test_redline_markers.py -q
git diff --stat main -- build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py build/section_map.py build/normalize_for_diff.py build/redline_resolve.py build/redline-stage.sh build/adoption-footer.sh build/adoption-name.sh build/use_table_changes.py build/split-article-03.py build/build-redline-standalone.sh build/permit-review/
python3 -m pytest build/tests -q
git add build/structural_note.py build/czc_diff.py build/redline-text.py build/tests/test_structural_note.py build/tests/test_redline_plain.py
git commit -m "$(cat <<'EOF'
redline: three wording slips carried from Wave 3b

The district pages' layout note read "its layout changed" for plural pages; the
legend aside pointed at "this file" after the file name was removed from the
sentence; and a plain-mode addition starting in bold came out as
"****Planting.**". Now "their layout", "(The use-table legend is part of these
pages.)", and an addition already holding bold is wrapped in __ instead.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
Expected: tests pass; the `git diff` prints nothing; the suite reports about 472 passed.

---

## Task 2: Article 3's tables as markdown

**Files:**
- Create: `build/typst_tables.py`
- Create: `build/tests/test_typst_tables.py`

**Interfaces:**
- Produces: `typst_tables.to_markdown(block: str) -> str | None` — `block` is one fenced ```` ```{=typst} ```` block INCLUDING its fence lines; returns the caption paragraph + blank line + pipe table, or `None` if the block is outside the measured grammar.

- [ ] **Step 1: Write the failing tests**

Create `build/tests/test_typst_tables.py`:

```python
"""build/typst_tables.py -- Article 3's raw-Typst tables as readable markdown.
Strict: anything outside the measured grammar is refused (None), so czc_md
writes a pointer instead of garbled text."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import czc_diff  # noqa: E402
import typst_tables as tt  # noqa: E402

REPO = BUILD.parent
ART3 = "article-03-streets-roads-driveways.md"


def _blocks():
    text = subprocess.run(["git", "-C", str(REPO), "show", f"v1.0:source/{ART3}"],
                          capture_output=True, text=True, check=True).stdout
    return czc_diff.split_markdown(text)[2]


def _table(md):
    lines = md.split("\n")
    rows = [ln for ln in lines if ln.startswith("| ")]
    return lines[0], rows


def test_the_four_tables_convert_exactly():
    got = [tt.to_markdown(b) for b in _blocks()]
    assert None not in got
    shapes = []
    for md in got:
        caption, rows = _table(md)
        assert md.split("\n")[1] == ""
        cols = rows[0].count(" | ") + 1
        shapes.append((caption.split()[1], len(rows) - 1, cols))   # minus the separator row
    assert shapes == [("3.4", 15, 2), ("3.5", 4, 3), ("3.2", 9, 2), ("3.3", 8, 6)]
    t34, t35, t32, t33 = got
    assert "| D1 Rural | R2 Rural Road; R3 Rural Lane on low-volume segments; R1 Connector Road on transition segments |" in t34
    assert "| Design Speed (MPH) | Sight Distance (FT) |" in t32
    assert "| 60 | 645 |" in t32
    assert "| **Construction** |  |  |  |  |  |" in t33
    assert "| Total HBP thickness | 2½″ | 2″ | 2½″ | 2″ or gravel surface | n/a |" in t33
    assert "| :--- | :--- | :--- |" in t35
    assert "engineer's stamp" in t35


def test_the_converted_tables_parse_as_tables():
    if not shutil.which("pandoc"):
        pytest.skip("pandoc not installed")
    for md in (tt.to_markdown(b) for b in _blocks()):
        r = subprocess.run(["pandoc", "-f", "markdown", "-t", "html"], input=md,
                           capture_output=True, text=True)
        assert r.returncode == 0 and "<table" in r.stdout


@pytest.mark.parametrize("edit", [
    lambda b: b.replace("#table(", "#table(stroke: none,\n    #table(", 1),
    lambda b: b.replace("[20], [155],", "table.cell(colspan: 2)[20],", 1),
    lambda b: b.replace("[20]", "[#strong[20]]", 1),
    lambda b: b.replace("TABLE 3.2 SIGHT DISTANCE", "Sight distance", 1),
    lambda b: b.replace("[20], [155],", "[20],", 1),               # a short row
])
def test_anything_unrecognised_is_refused(edit):
    sight = next(b for b in _blocks() if "TABLE 3.2" in b)
    assert tt.to_markdown(sight) is not None                        # the control
    assert tt.to_markdown(edit(sight)) is None


def test_a_pipe_in_a_cell_is_escaped():
    sight = next(b for b in _blocks() if "TABLE 3.2" in b)
    md = tt.to_markdown(sight.replace("[20]", "[20 | 25]", 1))
    assert "| 20 \\| 25 | 155 |" in md
```

- [ ] **Step 2: Run them to verify they fail** — `python3 -m pytest build/tests/test_typst_tables.py -v`: collection ERROR (`ModuleNotFoundError`).

- [ ] **Step 3: Write `typst_tables.py`**

```python
#!/usr/bin/env python3
"""Article 3's raw-Typst tables, as readable markdown tables.

Article 3 authors Tables 3.2-3.5 as raw-Typst blocks so each caption stays locked
to its grid in the PDF. In a markdown deliverable those blocks are Typst source,
not a table a resident can read. This converts the ONE measured shape:

    ```{=typst}
    // optional comment lines
    #block(breakable: false)[
      TABLE n.m TITLE

      #table(
        columns: (<fr list>),
        align: left,
        table.header([A], [B], ...),
        [cell], [cell], ...,
        ...
      )
    ]
    ```

into a caption paragraph and a pipe table, the form the Code's markdown tables
already take (Article 4's TABLE 4.1). Anything else -- another argument, a
table.cell, a span, Typst code in a cell, a short row -- returns None, and the
caller writes a note naming the table instead. Garbled output is never right; a
note is.
"""
from __future__ import annotations

import re

_CAPTION = re.compile(r"((?:TABLE|FIGURE|EXHIBIT)\s+\d+(?:\.\d+)?[A-Za-z]?\b.*)")
_COLUMNS = re.compile(r"columns\s*:\s*\(([^()]*)\)\s*,?")
_ALIGN = re.compile(r"align\s*:\s*left\s*,?")
_HEADER = re.compile(r"table\.header\((.*)\)\s*,?")
_ROW = re.compile(r"(?:\[[^\[\]]*\]\s*,\s*)*\[[^\[\]]*\]\s*,?")
_CELL = re.compile(r"\[([^\[\]]*)\]")
_BOLD = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])")


def _cell(text: str) -> str | None:
    text = " ".join(text.split())
    if any(ch in text for ch in "#$\\"):
        return None                                # Typst code, not text: refuse
    return _BOLD.sub(r"**\1**", text).replace("|", r"\|")


def to_markdown(block: str) -> str | None:
    lines = block.split("\n")
    if len(lines) < 3 or not lines[0].strip().startswith("```{=typst}") or lines[-1].strip() != "```":
        return None
    body = [ln.strip() for ln in lines[1:-1]]
    body = [ln for ln in body if ln and not ln.startswith("//")]
    if len(body) < 6 or body[0] != "#block(breakable: false)[" or body[-1] != "]":
        return None
    m = _CAPTION.fullmatch(body[1])
    if not m or body[2] != "#table(" or body[-2] != ")":
        return None
    caption = " ".join(m.group(1).split())
    ncols, header, rows = None, None, []
    for ln in body[3:-2]:
        c = _COLUMNS.fullmatch(ln)
        if c:
            ncols = len([x for x in c.group(1).split(",") if x.strip()])
            continue
        if _ALIGN.fullmatch(ln):
            continue
        h = _HEADER.fullmatch(ln)
        if h:
            if header is not None or not _ROW.fullmatch(h.group(1).strip()):
                return None
            header = _CELL.findall(h.group(1))
            continue
        if _ROW.fullmatch(ln):
            rows.append(_CELL.findall(ln))
            continue
        return None
    if not ncols or header is None or len(header) != ncols or not rows:
        return None
    if any(len(r) != ncols for r in rows):
        return None
    cells = [[_cell(x) for x in r] for r in [header, *rows]]
    if any(x is None for r in cells for x in r):
        return None
    out = [caption, "",
           "| " + " | ".join(cells[0]) + " |",
           "| " + " | ".join(":---" for _ in range(ncols)) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in cells[1:]]
    return "\n".join(out)
```

Note: an empty cell renders as `|  |` (two spaces) — the exact-output assertions above rely on it.

- [ ] **Step 4: Run** `python3 -m pytest build/tests/test_typst_tables.py -v` (all pass). If a real table's shape differs from the expected list, STOP and report the four shapes.

- [ ] **Step 5: Untouched-files diff (empty); full suite; commit**

```bash
git add build/typst_tables.py build/tests/test_typst_tables.py
git commit -m "$(cat <<'EOF'
build: Article 3's raw-Typst tables as readable markdown tables

Tables 3.2-3.5 are authored as raw-Typst blocks so each caption stays locked to
its grid in the PDF; in a markdown deliverable they were Typst source, not a
table. typst_tables converts the one measured shape into a caption paragraph and
a pipe table, as the Code's other markdown tables are written, and refuses
anything else so the caller can write a note naming the table instead of
garbled text.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: The honest standalone markdown

> **Plan amendment (controller, 2026-10-10, before execution):** the wiring into `build-standalone.sh` and its two build tests moved to Task 4. Article 2 refuses until Task 4 registers its appendix, and `test_standalone_seams.py::test_after_prose_path_honours_both_seams` builds the Article 2 standalone — wiring here would leave this task's commit red. In this task `czc_md.py` is a module and CLI only; the standalone build still copies the source until Task 4.

**Files:**
- Create: `build/czc_md.py`
- Modify: `build/article-manifest.json` (`md_completeness` per Article)
- Create: `build/tests/test_czc_md.py`

**Interfaces:**
- Consumes: Task 2's `typst_tables.to_markdown`; `structure_text.block_caption`; `manifest.load`.
- Produces:
  - `czc_md.MdError(Exception)`
  - `czc_md.render(nn: int, *, src_dir: Path = SOURCE, mode: str = "draft", version: str = "", doc: dict | None = None) -> str`
  - `czc_md.APPENDICES: dict[int, callable]` — Task 4 registers Article 2's.
  - CLI: `python3 build/czc_md.py <article-NN> <out.md> [--src-dir DIR] [--mode draft|meeting|adopted] [--version V]` — exit 0 written, 1 refused (nothing written).

- [ ] **Step 1: Declare `md_completeness`**

In `build/article-manifest.json`, add `"md_completeness"` to each Article: `"1": "prose-only"`, `"2": "prose-plus-appendix"`, `"3": "prose-only"`, `"4"`–`"9": "complete"`. Add one line to the `_ownership_comment` (or a new `_md_completeness_note`): "md_completeness declares what a standalone .md holds: complete (all of the Article), prose-only (its text; native pages are named by pointer notes), prose-plus-appendix (its text plus a generated appendix of its native pages). build/czc_md.py refuses a declaration that contradicts the Article's units."

- [ ] **Step 2: Write the failing tests**

Create `build/tests/test_czc_md.py`:

```python
"""build/czc_md.py -- the honest standalone markdown."""
import copy
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
BUILD = TESTS.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(TESTS))

import czc_md  # noqa: E402
import manifest  # noqa: E402
import section_fixtures as fx  # noqa: E402

REPO = BUILD.parent
VER = "v0.98-draft"


@pytest.fixture(scope="module")
def base_tree(tmp_path_factory):
    return fx.copy_full_source(tmp_path_factory.mktemp("v1") / "source")


def md(tree, n, mode="draft"):
    return czc_md.render(n, src_dir=tree, mode=mode, version=VER)


def test_frontmatter_keeps_the_article_and_drops_the_footer(base_tree):
    out = md(base_tree, 7)
    assert out.startswith('---\narticle-number: "7"\narticle-name: "Use Standards"\n---\n')
    assert "footer-date" not in out


@pytest.mark.parametrize("mode", ["draft", "meeting", "adopted"])
def test_no_draft_chrome_in_any_mode(base_tree, mode):
    out = md(base_tree, 3, mode)
    assert "Draft v" not in out
    assert "this extract does not govern" in out


def test_article_3_tables_are_tables_and_no_typst_or_comments_remain(base_tree):
    out = md(base_tree, 3)
    assert "{=typst}" not in out and "#table(" not in out and "<!--" not in out
    assert "TABLE 3.2 SIGHT DISTANCE\n\n| Design Speed (MPH) | Sight Distance (FT) |" in out


def test_article_3_points_to_its_native_pages_where_they_sit(base_tree):
    out = md(base_tree, 3)
    assert "the ten Thoroughfare Type pages" in out
    assert "Exhibit 3.1, the Thoroughfare Inventory" in out
    assert "Exhibit 3.2, the Thoroughfare Type Map" in out
    # the plates' pointer sits where the TYPE-PAGES marker was: before the Driveway subsection
    plates = out.index("the ten Thoroughfare Type pages —")
    assert out.index("## ") < plates


def test_article_1_names_the_district_maps(base_tree):
    out = md(base_tree, 1)
    assert "the District Maps" in out
    assert "PDF edition" in out


def test_a_pure_prose_article_is_its_text(base_tree):
    out = md(base_tree, 7)
    src = (base_tree / "article-07-use-standards.md").read_text()
    body = src.split("\n---\n", 1)[1]
    assert body.strip() in out


def test_a_table_outside_the_grammar_becomes_a_pointer(tmp_path, base_tree):
    tree = Path(shutil.copytree(base_tree, tmp_path / "source"))
    p = tree / "article-03-streets-roads-driveways.md"
    p.write_text(p.read_text().replace("[20], [155],", "table.cell(colspan: 2)[20],", 1))
    out = md(tree, 3)
    assert "TABLE 3.2 SIGHT DISTANCE — shown in the PDF edition" in out
    assert "#table(" not in out


def test_completeness_that_contradicts_the_units_is_refused(base_tree):
    """The negative control the spec names: claiming 'complete' for an Article
    with native pages would ship the gap silently."""
    doc = copy.deepcopy(manifest.load())
    doc["2"]["md_completeness"] = "complete"
    with pytest.raises(czc_md.MdError, match="complete"):
        czc_md.render(2, src_dir=base_tree, doc=doc)
    doc = copy.deepcopy(manifest.load())
    doc["7"]["md_completeness"] = "prose-only"
    with pytest.raises(czc_md.MdError):
        czc_md.render(7, src_dir=base_tree, doc=doc)


def test_an_appendix_with_no_generator_is_refused(base_tree, monkeypatch):
    monkeypatch.setattr(czc_md, "APPENDICES", {})
    with pytest.raises(czc_md.MdError, match="appendix"):
        md(base_tree, 2)
```

- [ ] **Step 3: Run them to verify they fail** — collection ERROR (`ModuleNotFoundError: czc_md`).

- [ ] **Step 4: Write `czc_md.py`**

Write the module with this behaviour (the docstring states the why: the standalone `.md` was a byte copy of the source — raw Typst, build comments, a stale "Draft v0.2-draft" footer, and for Article 2 none of the thirteen district pages):

1. `render(nn, *, src_dir, mode, version, doc)`:
   - Look up the Article; refuse (`MdError`) if absent, if `md_completeness` is missing or not one of the three values, if it contradicts the units (ruling 5), or if it is `prose-plus-appendix` and `nn not in APPENDICES`.
   - Read the prose (manifest `prose` where present — Articles 4–9 have no `prose` key — else the `article-0{nn}-*.md` glob in `src_dir`, as `manifest.PROSE_RE` defines; refuse if none or more than one). `manifest.load()` also holds non-Article keys (`_comment`, `shared`, `ignored`, …): look Articles up by `str(nn)`.
   - Split the frontmatter; keep only the `article-number:` and `article-name:` lines (ruling 3).
   - Walk the body line by line: a fenced ```` ```{=typst} ```` block → `typst_tables.to_markdown(block)`, else the pointer `*[{block_caption} — shown in the PDF edition; it could not be reproduced as text here.]*`; any other fenced block → verbatim; a whole-line HTML comment containing a split marker of this Article (`entry.get("split_markers", [])` — only Article 3 has any) → one pointer per unit whose `splice` is `at-marker:<that marker>`: `*[{label} — in the PDF edition; not reproduced in this markdown version.]*`; any other whole-line HTML comment → dropped (ruling 8); everything else verbatim.
   - After the body: for each unit with `splice == "after-prose"` → its pointer, unless the Article is `prose-plus-appendix` (then `APPENDICES[nn](src_dir)` is appended instead, preceded by a blank line).
   - Assemble: frontmatter (`---` + kept lines + `---`), blank line, the provenance line (ruling 3, 4) — `*This is a standalone extract of one Article of the Newcastle Core Zoning Code — {phrase}. The integrated Code is the document the Town adopts; this extract does not govern.*` with `{phrase}` = `a working draft ({version})` / `the Town Meeting edition ({version})` / `adopted ({version})` — then, if the Article is not `complete`, one line: `*The PDF edition also contains {labels joined with "; "}; {they are named below where they appear | the district pages are reproduced below as a generated appendix}. The PDF edition is authoritative for them.*`, then the body.
2. `main`: parse the CLI; write the file only after `render` returns; on `MdError` print `czc_md: refusing -- …` to stderr and return 1.
3. `APPENDICES = {}` at module level (Task 4 fills it).

- [ ] **Step 5: Run** `python3 -m pytest build/tests/test_czc_md.py build/tests/test_manifest_ownership.py -v` — all pass, including `test_an_appendix_with_no_generator_is_refused` (Article 2 refuses: `APPENDICES` is empty until Task 4).

- [ ] **Step 6: Untouched-files diff (empty); full suite (it must be fully green: nothing calls `czc_md` from a build yet); commit**

```bash
git add build/czc_md.py build/article-manifest.json build/tests/test_czc_md.py
git commit -m "$(cat <<'EOF'
build: czc_md, the honest standalone markdown (not yet wired in)

The standalone markdown is a byte copy of the Article's source: raw Typst,
build comments, a stale "Draft v0.2-draft" footer. czc_md builds it instead: the
Article's own text, its tables as tables, a note naming each page the PDF has
and the markdown cannot hold, at the place it sits, and a line saying the
integrated Code governs and this extract does not. What each Article's .md holds
is declared in the manifest (md_completeness), and a declaration that
contradicts the Article's pages is refused. The standalone build calls it in
the next commit, once Article 2's appendix exists.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Article 2's district pages as a generated appendix

**Files:**
- Modify: `build/czc_md.py` (the Article 2 appendix, registered in `APPENDICES`)
- Modify: `build/build-standalone.sh` (the `.md` deliverable — moved here from Task 3)
- Modify: `build/tests/test_czc_md.py`

**Interfaces:**
- Consumes: `use_table_changes.parse_legend(typ_text) -> dict`, `use_table_changes.status_words(code, legend) -> str`, `use_table_changes._category(record, col, title) -> str` (the soft-hyphen join).
- Produces: `czc_md.article2_appendix(src_dir: Path) -> str`; `APPENDICES[2] = article2_appendix`.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_czc_md.py`:

```python
# --- Article 2's appendix ------------------------------------------------------

import json  # noqa: E402
import re  # noqa: E402

USE_ROW = re.compile(r"^\| (.+) \| (.+) \|$")


def _use_rows(text):
    """(use, status) rows of every use table in the appendix."""
    rows, inside = [], False
    for ln in text.split("\n"):
        if ln == "| Use | Status |":
            inside = True
            continue
        if inside and ln.startswith("| :---"):
            continue
        if inside and USE_ROW.match(ln):
            rows.append(USE_ROW.match(ln).groups())
            continue
        inside = False
    return rows


def test_the_appendix_carries_all_thirteen_districts_and_819_uses(base_tree):
    out = md(base_tree, 2)
    data = json.loads((base_tree / "article-02-data.json").read_text())
    for rec in data:
        assert f"### {rec['code']} {rec['name']}" in out
    rows = _use_rows(out)
    assert len(rows) == 819


def test_every_status_is_in_words_and_matches_the_data(base_tree):
    import use_table_changes as utc
    out = md(base_tree, 2)
    legend = utc.parse_legend((base_tree / "article-02.typ").read_text())
    data = json.loads((base_tree / "article-02-data.json").read_text())
    expected = [(u, utc.status_words(s, legend)) for rec in data
                for col in ("use_col1", "use_col2") for c in rec[col] for u, s in c["entries"]]
    assert _use_rows(out) == expected
    assert ("Retail & Service, General",
            "Residential Companion Permit (CEO) + Special Permit (Planning Board)") in _use_rows(out)
    assert any(s == "Not allowed" for _, s in _use_rows(out))


def test_d4s_split_category_prints_whole(base_tree):
    out = md(base_tree, 2)
    d4 = out[out.index("### D4 VILLAGE RESIDENTIAL"):out.index("### D5 VILLAGE BUSINESS")]
    assert "**TRANSPORTATION & UTILITIES**" in d4
    assert "ITIES**" not in d4.replace("UTILITIES**", "")
    assert "\xad" not in out


def test_the_three_districts_without_a_matrix_say_so(base_tree):
    out = md(base_tree, 2)
    for name in ("SD CONSERVATION", "SD CAMPUS", "SD MARINE"):
        sect = out[out.index(f"### {name}"):]
        sect = sect[:sect.find("\n### ", 1)] if "\n### " in sect[1:] else sect
        assert "No Permitted Buildings matrix." in sect


def test_the_appendix_has_the_legend_and_the_standards(base_tree):
    out = md(base_tree, 2)
    assert "Use Permit — issued by CEO" in out
    assert "**DESCRIPTION**" in out and "**PERMITTED BUILDINGS**" in out
    assert out.count("**USE STANDARDS FOR") == 13 or "USE STANDARDS" in out


def test_the_appendix_parses_as_markdown(base_tree):
    if not shutil.which("pandoc"):
        pytest.skip("pandoc not installed")
    r = subprocess.run(["pandoc", "-f", "markdown", "-t", "html"], input=md(base_tree, 2),
                       capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.count("<table") > 13 * 7


# --- the standalone build calls czc_md (moved from Task 3) -----------------------

def test_the_standalone_build_writes_the_honest_md(tmp_path, base_tree):
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-standalone.sh", "03", VER], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(base_tree), OUT_DIR=str(out)),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    m = next(out.glob("*.md")).read_text()
    assert "{=typst}" not in m and "this extract does not govern" in m


def test_a_refused_md_leaves_no_release_dir(tmp_path, base_tree):
    tree = Path(shutil.copytree(base_tree, tmp_path / "source"))
    (tree / "article-03-streets-roads-driveways.md").unlink()
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-standalone.sh", "03", VER], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(tree), OUT_DIR=str(out)),
                       capture_output=True, text=True)
    assert r.returncode != 0 and not out.exists()


def test_the_article_2_standalone_md_carries_the_appendix(tmp_path, base_tree):
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-standalone.sh", "02", VER], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(base_tree), OUT_DIR=str(out)),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    m = next(out.glob("*.md")).read_text()
    assert "## Appendix — District Standards" in m and "### D1 RURAL" in m.upper()
```

- [ ] **Step 2: Run them to verify they fail** — `md(base_tree, 2)` raises (no appendix registered).

- [ ] **Step 3: Write the appendix**

Add to `czc_md.py` `article2_appendix(src_dir)` and register it. Output, in this order:
1. `## Appendix — District Standards`, then the italic line `*Generated from the district data the PDF edition's district pages are printed from. Use statuses are given in words; the PDF shows them as symbols.*`
2. `**Use table legend**` and one bullet per legend row: `- {label without " Required"} — issued by {authority}` in the legend's order, then `- A use with no status is not allowed in that District.`
3. For each of the 13 records in file order: `### {code} {name}`, then:
   - each panel of `left` then `right`, in order: `**{title}**` then — kind `lv`: a pipe table `| Item | Standard |` / `| :--- | :--- |` / one row per pair; kind `list`: `- item` lines, a `{text, sub}` item as `- text` with `  - sub` lines beneath; kind `para`: the paragraph;
   - the matrix: `**{title}**` then `|  | {cols joined " | "} |`, a `:---` separator of len(cols)+1, one row per matrix row; or `*No Permitted Buildings matrix.*` when null;
   - each use category of `use_col1` then `use_col2` with at least one entry: `**{use_table_changes._category(rec, col, title)}**` then `| Use | Status |`, `| :--- | :--- |`, one row per entry `| {use} | {use_table_changes.status_words(status, legend)} |`;
   - `**{use_standards.title}**` and its items as a list (same list rendering).
   Separate blocks with blank lines. Escape a leading `#` in any paragraph or list text with a backslash; escape `|` in any table cell.
The legend comes from `use_table_changes.parse_legend` on `src_dir/article-02.typ` (ruling 7: one reader); data from `src_dir/article-02-data.json`.

- [ ] **Step 4: Call it from `build-standalone.sh`**

Replace the `.md` line so the deliverable is generated BEFORE `mkdir -p "$RELEASE_DIR"` (a refused `.md` must leave no release directory): before the `mkdir`, if `OUT_MD_SOURCE` is set, keep today's behaviour (copy it later); else run `python3 "$REPO_ROOT/build/czc_md.py" "$NUM" "$TMP/out.md" --src-dir "$SOURCE_DIR" --mode "$ADOPTION_MODE" --version "$VERSION"` and exit 1 with its message on failure. After the `mkdir`, copy `"${OUT_MD_SOURCE:-$TMP/out.md}"` to `"$RELEASE_DIR/$OUT_NAME.md"`. Update the header comment for `OUT_MD_SOURCE` (default: the honest markdown from czc_md.py). `test_standalone_seams.py` must pass unchanged.

- [ ] **Step 5: Run** `python3 -m pytest build/tests/test_czc_md.py build/tests/test_standalone_seams.py build/tests/test_redline_standalone.py -v` (all pass; `test_standalone_seams.py` unchanged — its Article 2 probe line sits in the prose, which the `.md` keeps). If the use-row count is not 819, STOP and report the count and which categories differ.

- [ ] **Step 6: Untouched-files diff (empty); full suite; commit**

```bash
git add build/czc_md.py build/build-standalone.sh build/tests/test_czc_md.py
git commit -m "$(cat <<'EOF'
build: Article 2's standalone .md carries its thirteen district pages

The deliverable most likely to be read as "Article 2" was its prefatory prose
alone: the district standards and use tables -- the part an amendment changes --
were absent (decision D2). czc_md now appends a generated appendix of all
thirteen districts from the same data and the same legend the PDF uses: each
district's standards panels, its Permitted Buildings matrix (or a line saying it
has none), its use tables with every status in words -- all 819 -- and its use
standards. The standalone build now writes its .md through czc_md, before the
release directory exists, so a refused .md leaves no release directory.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: The adopted edition's residue check reads the markdown

**Files:**
- Modify: `build/adopted_residue.py` (a residue-only mode)
- Modify: `build/build-adopted.sh` (scan the `.md` bytes)
- Modify: `build/build-full-czc.sh` (edition-neutral pointer wording only)
- Modify: `build/tests/test_build_adopted.py`

**Interfaces:**
- Produces: `adopted_residue.py --residue-only [FILE ...]` reads stdin and checks CHROME only (no damage check); exit 0/1 as before.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_build_adopted.py`:

```python
def _residue_mod():
    import importlib.util
    spec = importlib.util.spec_from_file_location("residue", REPO / "build" / "adopted_residue.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_residue_only_mode_ignores_the_damage_check():
    """A markdown file for the adopted edition is checked for chrome; the Code's
    own 'drafts the official map' check stays on the PDF text."""
    r = subprocess.run([sys.executable, str(REPO / "build" / "adopted_residue.py"), "--residue-only"],
                       input="# Article 7\nText.\n", capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run([sys.executable, str(REPO / "build" / "adopted_residue.py"), "--residue-only"],
                       input="See the Integrated Draft PDF.\n", capture_output=True, text=True)
    assert r.returncode == 1


def test_the_shipped_adopted_md_would_fail_and_a_new_build_does_not(tmp_path):
    """The positive control: the v1.0 adopted markdown carries 'Integrated Draft'
    pointers and Article 3's old footer, so the md scan would have caught it.
    A fresh integrated draft markdown from today's build carries neither."""
    mod = _residue_mod()
    shipped = (REPO / "releases" / "v1.0-adopted" / "Newcastle CZC (Adopted v1.0).md").read_text()
    assert mod.find_residue(shipped) != []
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-full-czc.sh", "v0.98-draft", "January 1, 2027"],
                       cwd=REPO, env=dict(os.environ, OUT_DIR=str(out)), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    md = next(out.glob("*.md")).read_text()
    assert "Integrated Draft PDF" not in md
    assert [c for c in mod.find_residue(md) if c != "INTEGRATED DRAFT"] == []
```

(Read the file's top for its imports; add `os`, `sys`, `subprocess` only if missing. The draft integrated md's own TITLE may legitimately say "Integrated Draft" in draft mode — the second assertion tolerates exactly that string and nothing else; the pointer notes must not use it.)

- [ ] **Step 2: Run them to verify they fail.**

- [ ] **Step 3: Implement**

- `adopted_residue.py`: `main` accepts a leading `--residue-only` flag; with it, report only `find_residue` over stdin + filenames (never `find_damage`). Docstring: the markdown is chrome-checked; the damage check stays on the PDF text, where the whole Code (including Article 8) is.
- `adopted_residue.py` today has NO flag handling — `main` reads stdin and treats every argument as a filename, so `--residue-only` would silently be taken as a file name. Parse it explicitly: a leading `--residue-only` is consumed as the flag; every other argument stays a filename.
- `build-adopted.sh`: the adopted `.md` is written by `build-full-czc.sh` into `$SCRATCH_OUT`; the identity gate is at lines 128-165, the residue gate at 167-174 (the `.md` passed only as a name), and the copy into the release directory at 176-179. Add the new scan between 174 and 176 — `python3 "$REPO_ROOT/build/adopted_residue.py" --residue-only < <the .md in $SCRATCH_OUT>` — so it runs on the scratch file BEFORE anything reaches the release directory. A failure exits 1 with the existing message style.
- `build-full-czc.sh`: in the two pointer notes (`:410`, `:418`), replace "See the Integrated Draft PDF" with "See the PDF edition of this Code". Change nothing else.

- [ ] **Step 4: Run** `python3 -m pytest build/tests/test_build_adopted.py build/tests/test_build_adoption.py -v` (all pass).

- [ ] **Step 5: Untouched-files diff (empty); full suite; commit**

```bash
git add build/adopted_residue.py build/build-adopted.sh build/build-full-czc.sh build/tests/test_build_adopted.py
git commit -m "$(cat <<'EOF'
build: the adopted edition's chrome check reads its markdown too

build-adopted.sh checked the adopted PDF's text and the artifacts' file names
for draft chrome, but passed the markdown only as a name -- so the shipped v1.0
adopted markdown carries "See the Integrated Draft PDF" twice and Article 3's
"Draft v0.2-draft" footer. The markdown's bytes are now chrome-checked too (the
"drafts the official map" damage check stays on the PDF text, where the whole
Code is), and the integrated markdown's pointer notes say "the PDF edition of
this Code", true in every mode.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Done when

- Article 3's source footer reads "Adopted: September 14, 2026" (its own commit); the three carried slips are fixed.
- Every standalone `.md` keeps its Article's text, converts Article 3's tables to markdown tables, names every native page by pointer note where it sits, says it is an extract that does not govern, carries no stale draft chrome, and is generated before the release directory is created.
- Article 2's standalone `.md` carries a generated appendix of all thirteen districts with all 819 use statuses in words.
- `md_completeness` is declared per Article and a contradiction is refused.
- The adopted edition's markdown is chrome-checked; the integrated `.md`'s pointer notes are edition-neutral.
- The untouched files are byte-identical to `main`; the full suite passes; CI is green on the PR.

## Not in this plan

- **The integrated `.md`'s Article 3 tables** stay raw Typst (the integrated `.md` is assembled by `build-full-czc.sh`; converting there is a separate decision).
- **The redline `.md`** (ruling 10).
- **P13**: the release driver, the section map in staging, and the draft-cover facts (D6) — before the next freeze.
