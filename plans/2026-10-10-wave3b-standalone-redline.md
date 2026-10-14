# Wave 3b — The Per-Article Redline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship, for any one Article, a redline in `.pdf` and `.md` whose reader can see every change — including the headings, tables and figures a text diff cannot mark word by word — with a generated "How to read this redline" page in front.

**Architecture:** A small shared module names headings and raw-Typst tables/figures in plain words. The change determination (`czc_diff.py`) gains a function that says WHICH headings and tables were added, removed or changed. The redline marker (`redline-text.py --source`, both PDF and plain modes) writes an italic bracketed note at the exact spot of each such change. The disclosure page (`structural_note.py`) is made truthful for the whole-Code redline and gains a per-Article scope generated from the change determination and the ownership map. A new `build-redline-standalone.sh` composes the Wave 1 seams into the one-Article redline.

**Tech Stack:** Python 3.14, bash, PyMuPDF (the disclosure page), pandoc → Typst (the redline PDF, via the existing builds), pytest.

**Spec:** `specs/2026-10-07-release-deliverables-scope.md` — §2 P8 and P14, §0 decision D1, §3 Wave 3. Ben Frey's rulings of 2026-10-10: dropped headings/tables/figures are made visible BOTH on the disclosure page AND by a marker in the text; Wave 3 continues as 3b (this plan) then 3c (standalone markdown + Article 2 appendix + the Article 3 footer fix).

## Global Constraints

- **NEVER commit unless explicitly asked.** The operator authorises this plan's commit steps: implementers commit locally, by name, on branch `wave3b-standalone-redline`. Nothing is pushed.
- **NEVER `git add -A` or `git add .`** — stage files by name, exactly as each commit step lists them. **No `git stash`.**
- **Never modify anything in `docs/`, `source/` or `releases/`.** Tests write only under `tmp_path`.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` — **project standing rule 5**, which deliberately overrides any other attribution suggestion.
- Build tests: `python3 -m pytest build/tests -q` from the repository root. **389 tests** at the start of this wave. CI runs the same suite on the PR (Linux: GNU coreutils, no macOS fonts). **Report the count you actually see.**
- **Untouched by this wave** (prove with `git diff --stat main -- <these>` printing nothing): `build/adoption-map.json`, `build/adoption_map.py`, `build/baseline_selfcheck.py`, `build/section_map.py`, `build/normalize_for_diff.py`, `build/redline_resolve.py`, `build/redline-stage.sh`, `build/adoption-footer.sh`, `build/adoption-name.sh`, `build/use_table_changes.py`, `build/build-full-czc.sh`, `build/split-article-03.py`, `build/permit-review/`, `source/`.
- **Never pin the live working tree.** Every assertion with a count runs against a tree materialised from the `v1.0` tag (`section_fixtures.copy_full_source`) and then edited, or against two real tags. Test versions use `v0.98-draft` (a whole-number or `v9.9-test` version is refused by `version_state.py`).
- **The marked prose file is three things at once** (measured): the pandoc → Typst input; `split-article-03.py`'s input, which finds split markers by SUBSTRING (`TYPE-PAGES`, `STREET-TYPE-EXHIBITS` anywhere in a line); and, for the integrated build, a document whose TOC is read back from the built PDF by text size and colour. So every marker the redline writes is an ordinary body paragraph — never a `#` heading, never coloured, and never containing either split-marker token.
- **Measured behaviour this wave changes** (`redline-text.py --source`, both PDF and `--plain`): a REMOVED heading, a REMOVED raw-Typst block and a REMOVED whole-line comment each leave ONE EMPTY LINE — no trace, tally 0/0; a RETITLED heading shows only the new title, unmarked; an ADDED heading is the heading verbatim, unmarked; an ADDED or CHANGED raw-Typst block is verbatim in the PDF path with no note, and preceded by `<!-- unmarked: new or regenerated figure -->` + `*[figure new or regenerated — shown unmarked]*` in `--plain`. Only Article 3 has raw-Typst blocks at v1.0: four ```` ```{=typst} ```` fences (Tables 3.4, 3.5, 3.2, 3.3).
- **`structural_note.py` is false today** under the shipped identity map (baseline v1.0): it unconditionally prints "Article 3, Thoroughfares, is new", a heading "The articles after Article 2 were renumbered", "Article 2 is reproduced UNMARKED … NO marks", "the Article 3 inventory and Type map", the literal "Three real changes", and a default old-side label "…amended through March 24, 2025" (the Code was amended September 14, 2026). It is one page (odd); `build-standalone.sh` refuses an odd front note.
- **`build-standalone.sh:214` writes the `.md` deliverable as `cp "$PROSE"`** — for a redline stage that is the Typst-marked prose, not markdown; and a `--plain` stage is refused as `SRC_DIR` by `adoption-footer.sh`'s sentinel guard. So the standalone redline needs two stages, and `build-standalone.sh` needs one small, default-preserving seam for the `.md` source.

### Ten rulings this plan makes in writing

1. **Structural notes are italic, bracketed body paragraphs**, in both modes: `*[Heading removed: “…”]*`. Not red (red means added Code text), not struck (strike means deleted Code text), never a heading. This matches the existing plain-mode figure note.
2. **The six notes, verbatim** (`{x}` is a plain-words label): `*[Heading removed: “{x}”]*` · `*[Heading added]*` (after the new heading) · `*[Heading changed — it read: “{x}”]*` (after the new heading) · `*[Table or figure removed: “{x}”]*` · `*[New table or figure, shown in full: “{x}”]*` (before the block) · `*[Table or figure changed — shown in its current form, not marked: “{x}”]*` (before the block).
3. **Labels:** a heading's label is its text without `#`s or a trailing `{#id}`; a raw-Typst block's label is the first `TABLE n.n …` / `FIGURE n …` / `EXHIBIT n …` caption in its non-comment lines, else "an untitled table or figure". Labels are whitespace-collapsed, ≤ 100 characters, and have the split-marker tokens' hyphens replaced by spaces.
4. *(Amended in Task 1 fix round 1: decided once by `structure_text.classify_blocks` — exact-content matches first, so a reordered table is no change; then remaining blocks paired by caption in order. Task 2 uses the classifier, not caption sets.)* **Originally: added vs changed vs removed for a block decided by caption across the whole Article:** an inserted block whose caption also exists on the old side is "changed"; else "new". A deleted block whose caption also exists on the new side gets no note (its changed note is at the new block); else "removed". The page uses the same caption rule (Task 1's `structural_changes`), so the page and the text agree.
5. **Whole-line HTML comments stay silent.** They carry build structure (split markers), not Code text.
6. **The plain-mode note comment stays** (`UNMARKED_FIGURE_NOTE`, before a new/changed block), because `is_unmarkable_structure` and existing tests key on it; the visible line becomes the new/changed note of ruling 2.
7. **The tally reports structural notes separately**: `redline: N line(s) removed, M line(s) added, K structural change(s) noted`. `_markable` (what counts as a marked line) does not change.
8. **The disclosure page names KINDS of change, not line counts.** `czc_diff` counts a modified line twice; "12 lines changed" would mislead a resident. The page says which of the Article's wording, headings, tables or figures, or underlying data changed, then lists each heading/table/figure by name.
9. **The page is also written as markdown** and placed in the `.md` redline after the legend: the markdown is the redline that survives in the repository (D1).
10. **The standalone redline does not apply a section map in this wave.** Threading `--section-map` through staging is P13's; without it the page never claims suppressed renumbering for a standalone.

## Review Focus

1. **A deleted table or heading must leave a visible note in BOTH the PDF and the `.md`** — pinned in Task 2 (`test_a_deleted_table_leaves_a_note_in_both_modes`, `test_a_deleted_heading_leaves_a_note_in_both_modes`).
2. **A note must never break the split or seat a plate wrongly** — a note text carrying a split-marker token would split Article 3 at the wrong place and exit 0. Pinned in Task 1 (`test_labels_never_carry_a_split_marker_token`) and Task 4 (plate position test).
3. **The parity predicate must be able to fail** — an inserted uncounted page must be detected. Pinned in Task 4 (`test_the_parity_check_sees_an_uncounted_page`).
4. **The whole-Code note must not lie under the shipped identity map** — "is new", "UNMARKED", a renumbering heading with no renumbering. Pinned in Task 3 (`test_the_identity_map_note_claims_nothing_false`).
5. **A dry run must not touch `releases/`** — pinned in Task 4 (`test_a_dry_run_leaves_releases_untouched`).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `build/structure_text.py` | **New.** Plain-words labels for headings and raw-Typst blocks | Create (Task 1) |
| `build/czc_diff.py` | Change determination | Add `structural_changes` (Task 1) |
| `build/redline-text.py` | Redline marker | In-text structural notes, legend, tally (Task 2) |
| `build/structural_note.py` | Disclosure page | Truthful whole-Code note; per-Article scope; markdown; even padding (Task 3) |
| `build/article-manifest.json` | Ownership map | Each native unit gains a `label` (Task 3) |
| `build/build-redline-full.sh` | Whole-Code redline | Old-side label no longer hard-codes 2025 (Task 3) |
| `build/build-standalone.sh` | Standalone build | One seam, `OUT_MD_SOURCE` (Task 4) |
| `build/build-redline-standalone.sh` | **New.** The per-Article redline | Create (Task 4) |
| `build/tests/test_structure_text.py` | **New** | Task 1 |
| `build/tests/test_redline_markers.py` | **New** | Task 2 (and rewrites of pinned tests in `test_redline_plain.py`, `test_redline_structure.py`) |
| `build/tests/test_structural_note.py` | Note tests | Extend (Task 3) |
| `build/tests/test_redline_standalone.py` | **New** | Task 4 |

---

## Task 1: Name the parts a redline cannot mark word by word

**Files:**
- Create: `build/structure_text.py`
- Modify: `build/czc_diff.py` (add `structural_changes`; nothing else changes)
- Create: `build/tests/test_structure_text.py`

**Interfaces:**
- Produces:
  - `structure_text.heading_label(line: str) -> str`
  - `structure_text.block_caption(block: str) -> str`
  - `structure_text.UNTITLED = "an untitled table or figure"`
  - `czc_diff.structural_changes(old: str | None, new: str, *, smap=None) -> dict[str, list]` with keys `headings_added`, `headings_removed` (lists of labels), `headings_changed` (list of `(old_label, new_label)`), `tables_added`, `tables_removed`, `tables_changed` (lists of captions).

- [ ] **Step 1: Write the failing tests**

Create `build/tests/test_structure_text.py`:

```python
"""Plain-words names for headings and raw-Typst blocks, and which of them
changed. The redline's in-text notes and the disclosure page both use these, so
the two say the same thing."""
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import czc_diff  # noqa: E402
import structure_text as st  # noqa: E402

REPO = BUILD.parent
ART3 = "article-03-streets-roads-driveways.md"
ART7 = "article-07-use-standards.md"


def _text(ref, rel):
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:source/{rel}"],
                          capture_output=True, text=True, check=True).stdout


def _blocks(text):
    return czc_diff.split_markdown(text)[2]


def test_the_four_article_3_tables_are_named_by_their_captions():
    caps = [st.block_caption(b) for b in _blocks(_text("v1.0", ART3))]
    assert len(caps) == 4
    assert [c.split()[1] for c in caps] == ["3.4", "3.5", "3.2", "3.3"]
    assert all(c.startswith("TABLE ") for c in caps)
    assert "TABLE 3.2 SIGHT DISTANCE" in caps


def test_a_block_with_no_caption_is_untitled():
    assert st.block_caption("```{=typst}\n// only a comment\n#line()\n```") == st.UNTITLED


def test_heading_labels():
    assert st.heading_label("## 5. AMUSEMENT, OUTDOOR") == "5. AMUSEMENT, OUTDOOR"
    assert st.heading_label("### a. DEFINITION {#def}") == "a. DEFINITION"


def test_labels_never_carry_a_split_marker_token():
    """split-article-03.py finds its markers by substring: a note carrying the
    token would split Article 3 at the wrong place and still exit 0."""
    for raw in ("## TYPE-PAGES note", "```{=typst}\nTABLE 9.1 STREET-TYPE-EXHIBITS\n```"):
        label = st.heading_label(raw) if raw.startswith("#") else st.block_caption(raw)
        assert "TYPE-PAGES" not in label and "STREET-TYPE-EXHIBITS" not in label


def test_v1_0_against_itself_changes_nothing_and_sees_every_heading():
    text = _text("v1.0", ART7)
    assert all(v == [] for v in czc_diff.structural_changes(text, text).values())
    assert len(czc_diff.split_markdown(text)[1]) > 100          # the control: headings were read


def test_a_retitled_heading_is_a_change_not_an_add_and_a_remove():
    old = _text("v1.0", ART7)
    new = old.replace("## 5. AMUSEMENT, OUTDOOR", "## 5. AMUSEMENT, OUTSIDE", 1)
    sc = czc_diff.structural_changes(old, new)
    assert sc["headings_changed"] == [("5. AMUSEMENT, OUTDOOR", "5. AMUSEMENT, OUTSIDE")]
    assert sc["headings_added"] == sc["headings_removed"] == []


def test_tables_added_removed_and_changed_are_named():
    old = _text("v1.0", ART3)
    blocks = _blocks(old)
    sight = next(b for b in blocks if "TABLE 3.2" in b)
    eng = next(b for b in blocks if "TABLE 3.5" in b)
    new = old.replace(sight, sight.replace("TABLE 3.2 SIGHT DISTANCE", "TABLE 3.2 SIGHT DISTANCE ", 1)
                      .replace("\n#", "\n// edited\n#", 1), 1)       # same caption, different content
    new = new.replace(eng, "", 1)                                   # removed
    new += "\n```{=typst}\n#block[\n  TABLE 3.9 NEW THING\n]\n```\n"  # added
    sc = czc_diff.structural_changes(old, new)
    assert sc["tables_changed"] == ["TABLE 3.2 SIGHT DISTANCE"]
    assert sc["tables_removed"] == [st.block_caption(eng)]
    assert sc["tables_added"] == ["TABLE 3.9 NEW THING"]


def test_a_new_article_lists_every_heading_as_added():
    new = _text("v1.0", ART7)
    sc = czc_diff.structural_changes(None, new)
    assert len(sc["headings_added"]) == len(czc_diff.split_markdown(new)[1])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_structure_text.py -v`
Expected: collection ERROR, `ModuleNotFoundError: No module named 'structure_text'`.

- [ ] **Step 3: Write `structure_text.py`**

```python
#!/usr/bin/env python3
"""Plain-words names for the parts of an Article a redline cannot mark word by
word: its headings and its raw-Typst tables and figures.

The redline's in-text notes (redline-text.py) and the disclosure page
(structural_note.py, via czc_diff.structural_changes) both name these parts, so
they share one namer and cannot disagree.

A label is an ordinary string placed in a body paragraph of the marked prose,
which is also split-article-03.py's input -- and that splitter finds its markers
by SUBSTRING. So a label never carries a split-marker token.
"""
from __future__ import annotations

import re

UNTITLED = "an untitled table or figure"
_FENCE_LINE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
_CAPTION = re.compile(r"\b((?:TABLE|FIGURE|EXHIBIT)\s+\d+(?:\.\d+)?[A-Za-z]?\b[^\n\[\]]*)")
_HEADING = re.compile(r"^\s*#{1,6}[ \t]+(.*?)\s*(?:\{[^}]*\})?\s*$")
_RESERVED = ("TYPE-PAGES", "STREET-TYPE-EXHIBITS")


def _clean(text: str) -> str:
    text = " ".join(text.split()).strip(" \"“”")
    for token in _RESERVED:
        text = text.replace(token, token.replace("-", " "))
    return text[:100]


def heading_label(line: str) -> str:
    """A heading's text, without its #s or a trailing {#id}."""
    m = _HEADING.match(line)
    return _clean(m.group(1) if m else line)


def block_caption(block: str) -> str:
    """The first TABLE / FIGURE / EXHIBIT caption in a raw block's non-comment
    lines, or UNTITLED."""
    for line in block.split("\n"):
        if _FENCE_LINE.match(line) or line.strip().startswith("//"):
            continue
        m = _CAPTION.search(line)
        if m:
            return _clean(m.group(1))
    return UNTITLED
```

- [ ] **Step 4: Add `structural_changes` to `czc_diff.py`**

Add `import difflib` to czc_diff's imports and `import structure_text  # noqa: E402` beside `import manifest`, then add after `markdown_counts`:

```python
def structural_changes(old: str | None, new: str, *, smap=None) -> dict[str, list]:
    """WHICH headings and raw-Typst tables/figures were added, removed or
    changed -- the names behind markdown_counts' heading and table counts. The
    old side is normalised exactly as in markdown_counts. A table or figure is
    matched by its caption across the whole Article: the same caption with
    different content is "changed". The redline's in-text notes use the same
    caption rule, so the page and the text agree."""
    if old is None:
        o_heads, o_blocks = [], []
    else:
        _, o_heads, o_blocks = split_markdown(
            nz.normalize_old_side(old, amap=_identity_amap(), smap=smap))
    _, n_heads, n_blocks = split_markdown(new)
    out: dict[str, list] = {k: [] for k in ("headings_added", "headings_removed",
                                            "headings_changed", "tables_added",
                                            "tables_removed", "tables_changed")}
    sm = difflib.SequenceMatcher(None, o_heads, n_heads, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        old_part, new_part = o_heads[i1:i2], n_heads[j1:j2]
        if tag == "replace" and len(old_part) == len(new_part):
            out["headings_changed"] += [(structure_text.heading_label(a),
                                         structure_text.heading_label(b))
                                        for a, b in zip(old_part, new_part)]
        else:
            out["headings_removed"] += [structure_text.heading_label(h) for h in old_part]
            out["headings_added"] += [structure_text.heading_label(h) for h in new_part]
    o_caps = [structure_text.block_caption(b) for b in o_blocks]
    n_caps = [structure_text.block_caption(b) for b in n_blocks]
    sm = difflib.SequenceMatcher(None, o_caps, n_caps, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out["tables_changed"] += [n_caps[j] for i, j in zip(range(i1, i2), range(j1, j2))
                                      if o_blocks[i] != n_blocks[j]]
        else:
            out["tables_removed"] += o_caps[i1:i2]
            out["tables_added"] += n_caps[j1:j2]
    return out
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_structure_text.py build/tests/test_czc_diff.py -v`
Expected: all pass (the existing czc_diff tests unchanged). If `test_tables_added_removed_and_changed_are_named` reports a different caption for Table 3.5's block, STOP and report the four captions `block_caption` returns for v1.0 Article 3.

- [ ] **Step 6: Prove the untouched files; run the full suite**

```bash
git diff --stat main -- build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py build/section_map.py build/normalize_for_diff.py build/redline_resolve.py build/redline-stage.sh build/adoption-footer.sh build/adoption-name.sh build/use_table_changes.py build/build-full-czc.sh build/split-article-03.py build/permit-review/ source/
python3 -m pytest build/tests -q
```
Expected: the `git diff` prints nothing; the suite reports about 397 passed.

- [ ] **Step 7: Commit**

```bash
git add build/structure_text.py build/czc_diff.py build/tests/test_structure_text.py
git commit -m "$(cat <<'EOF'
build: name the headings and tables a redline cannot mark word by word

A redline marks prose; headings and raw-Typst tables and figures it shows as
they now stand. structure_text gives each one a plain-words name -- a heading by
its text, a table or figure by its caption -- and czc_diff.structural_changes
says which were added, removed or changed. The redline's in-text notes and the
disclosure page will both use these, so the two cannot disagree. A name never
carries a split-marker token, because Article 3's splitter finds its markers by
substring.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: A note in the text wherever a heading, table or figure changed

**Files:**
- Modify: `build/redline-text.py`
- Create: `build/tests/test_redline_markers.py`
- Modify: `build/tests/test_redline_plain.py`, `build/tests/test_redline_structure.py` — ONLY the assertions that pin today's silence (listed in Step 4), each rewritten to the new behaviour with a one-line comment saying why

**Interfaces:**
- Consumes: Task 1's `structure_text.heading_label`, `structure_text.block_caption`.
- Produces: `redline-text.py --source [--plain]` output carrying ruling 2's notes; tally line `redline: N line(s) removed, M line(s) added, K structural change(s) noted`.

- [ ] **Step 1: Write the failing tests**

Create `build/tests/test_redline_markers.py`:

```python
"""redline-text.py --source: a note in the text wherever a heading, table or
figure was added, removed or changed. Before this, a removed table or heading
left one empty line -- no trace, and a tally of 0/0."""
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
REPO = BUILD.parent
RT = BUILD / "redline-text.py"
ART3 = "article-03-streets-roads-driveways.md"
ART7 = "article-07-use-standards.md"


def _text(ref, rel):
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:source/{rel}"],
                          capture_output=True, text=True, check=True).stdout


def mark(tmp_path, old, new, *flags):
    o, n, out = tmp_path / "old.md", tmp_path / "new.md", tmp_path / "out.md"
    o.write_text(old)
    n.write_text(new)
    r = subprocess.run([sys.executable, str(RT), str(o), str(n), str(out), "--source", *flags],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    return out.read_text(), r.stderr


BOTH = pytest.mark.parametrize("flags", [(), ("--plain",)], ids=["pdf", "plain"])


def _sight(text):
    start = text.index("```{=typst}", text.index("b. To a point 4 ft above ground"))
    end = text.index("```\n", start + 10) + 4
    return text[start:end]


@BOTH
def test_a_deleted_table_leaves_a_note_in_both_modes(tmp_path, flags):
    old = _text("v1.0", ART3)
    new = old.replace(_sight(old), "", 1)
    out, err = mark(tmp_path, old, new, *flags)
    assert "*[Table or figure removed: “TABLE 3.2 SIGHT DISTANCE”]*" in out
    assert "1 structural change(s) noted" in err


@BOTH
def test_a_deleted_heading_leaves_a_note_in_both_modes(tmp_path, flags):
    old = _text("v1.0", ART7)
    new = old.replace("## 5. AMUSEMENT, OUTDOOR\n", "", 1)
    out, _ = mark(tmp_path, old, new, *flags)
    assert "*[Heading removed: “5. AMUSEMENT, OUTDOOR”]*" in out


@BOTH
def test_an_added_heading_stays_a_heading_and_gets_a_note(tmp_path, flags):
    old = _text("v1.0", ART7)
    new = old.replace("## 3. ADULT ESTABLISHMENT", "## 3. AGRICULTURE\n\nFarming.\n\n## 4. ADULT ESTABLISHMENT", 1)
    out, _ = mark(tmp_path, old, new, *flags)
    assert "\n## 3. AGRICULTURE\n\n*[Heading added]*\n" in out


@BOTH
def test_a_retitled_heading_says_what_it_read(tmp_path, flags):
    old = _text("v1.0", ART7)
    new = old.replace("## 5. AMUSEMENT, OUTDOOR", "## 5. AMUSEMENT, OUTSIDE", 1)
    out, _ = mark(tmp_path, old, new, *flags)
    assert "## 5. AMUSEMENT, OUTSIDE\n\n*[Heading changed — it read: “5. AMUSEMENT, OUTDOOR”]*" in out


@BOTH
def test_a_changed_table_is_noted_before_it_in_both_modes(tmp_path, flags):
    """The PDF path used to show a changed Table 3.2 exactly like an unchanged one."""
    old = _text("v1.0", ART3)
    sight = _sight(old)
    new = old.replace(sight, sight.replace("\n#", "\n// edited\n#", 1), 1)
    out, _ = mark(tmp_path, old, new, *flags)
    note = "*[Table or figure changed — shown in its current form, not marked: “TABLE 3.2 SIGHT DISTANCE”]*"
    assert note in out
    assert out.index(note) < out.index("TABLE 3.2 SIGHT DISTANCE", out.index(note) + len(note))


@BOTH
def test_a_new_table_is_noted(tmp_path, flags):
    old = _text("v1.0", ART3)
    new = old + "\n```{=typst}\n#block[\n  TABLE 3.9 NEW THING\n]\n```\n"
    out, _ = mark(tmp_path, old, new, *flags)
    assert "*[New table or figure, shown in full: “TABLE 3.9 NEW THING”]*" in out


@BOTH
def test_an_unchanged_article_carries_no_note(tmp_path, flags):
    old = _text("v1.0", ART3)
    out, err = mark(tmp_path, old, old, *flags)
    assert "*[" not in out                           # no structural note at all
    assert "0 structural change(s) noted" in err


def test_a_removed_split_marker_comment_stays_silent(tmp_path):
    """Ruling 5: whole-line comments are build structure, not Code text."""
    old = _text("v1.0", ART3)
    line = next(ln for ln in old.splitlines() if "The former TABLE 3.1a" in ln)
    out, err = mark(tmp_path, old, old.replace(line + "\n", "", 1))
    assert "*[" not in out
    assert "0 structural change(s) noted" in err


def test_the_legend_no_longer_says_a_removal_leaves_no_trace(tmp_path):
    old = _text("v1.0", ART7)
    out, _ = mark(tmp_path, old, old, "--plain")
    assert "leaves no trace" not in out
    assert "a note in italics and square brackets" in out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_redline_markers.py -v`
Expected: most FAIL (no notes are written; the tally has no "structural change(s)"); `test_a_removed_split_marker_comment_stays_silent` may fail only on the tally wording. Say which passed.

- [ ] **Step 3: Write the notes**

In `build/redline-text.py`:

1. Add `import os` to the imports, then after them:
```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import structure_text  # noqa: E402  (plain-words names; shared with the disclosure page)
```
2. Beside `UNMARKED_FIGURE_NOTE`, add ruling 2's six templates and a counter:
```python
# Structural notes (Wave 3b, ruling 1): italic, bracketed BODY paragraphs, never
# red (red means added Code text), never struck (strike means deleted Code text),
# never a heading (the integrated TOC is read back from the PDF). The same text in
# both modes. Labels come from structure_text and never carry a split-marker token.
NOTE_HEADING_REMOVED = '*[Heading removed: “{}”]*'
NOTE_HEADING_ADDED = '*[Heading added]*'
NOTE_HEADING_CHANGED = '*[Heading changed — it read: “{}”]*'
NOTE_BLOCK_REMOVED = '*[Table or figure removed: “{}”]*'
NOTE_BLOCK_ADDED = '*[New table or figure, shown in full: “{}”]*'
NOTE_BLOCK_CHANGED = ('*[Table or figure changed — shown in its current form, '
                      'not marked: “{}”]*')
_STRUCT = {'n': 0}


def _note(template: str, label: str = '') -> str:
    _STRUCT['n'] += 1
    return template.format(label.replace('*', r'\*'))
```
3. Replace `LEGEND_SOURCE_LIMITS` with:
```python
LEGEND_SOURCE_LIMITS = ('Only prose and the rows of simple tables are marked word by word. Headings, '
                        'figures and complex tables (those laid out as figures rather than as plain '
                        'rows) are shown in their current form; where one was added, removed or '
                        'changed, a note in italics and square brackets says so at that spot. '
                        'See the Summary of Changes for detail.')
```
   and update the comment above it to say a removal now leaves a note.
4. Replace `emit_deleted_src` and `emit_inserted_src` with versions taking a context (`ctx`: the block TOKENS that `structure_text.classify_blocks` — the one classifier the disclosure page also uses — found removed, added and changed):
```python
_NO_CTX = {'removed': set(), 'added': set(), 'changed': set()}


def emit_deleted_src(ln: str, reg: dict, ctx: dict | None = None) -> str:
    ctx = ctx or _NO_CTX
    if is_block_token(ln):
        # A changed block's note sits at its new version; a moved one needs none.
        if ln not in ctx['removed']:
            return ''
        return _note(NOTE_BLOCK_REMOVED, structure_text.block_caption(reg[ln]))
    if is_heading(ln):
        return _note(NOTE_HEADING_REMOVED, structure_text.heading_label(ln))
    if is_unmarkable_structure(ln):
        return ''            # build structure (a split marker), not Code text: silent (ruling 5)
    return strike_pipe(ln) if is_pipe_row(ln) else strike_line(ln)


def emit_inserted_src(ln: str, reg: dict, ctx: dict | None = None) -> str:
    ctx = ctx or _NO_CTX
    if is_block_token(ln):
        if ln in ctx['changed']:
            template = NOTE_BLOCK_CHANGED
        elif ln in ctx['added']:
            template = NOTE_BLOCK_ADDED
        else:
            return reg[ln]   # an unchanged block that only moved: no note
        note = _note(template, structure_text.block_caption(reg[ln]))
        lead = (UNMARKED_FIGURE_NOTE + '\n\n') if PLAIN else ''
        return lead + note + '\n\n' + reg[ln]
    if is_heading(ln):
        return ln + '\n\n' + _note(NOTE_HEADING_ADDED)   # the heading stays a heading (TOC, structure)
    if is_unmarkable_structure(ln):
        return ln            # NEW split marker VERBATIM: it is structure the splitter reads
    return red_pipe(ln) if is_pipe_row(ln) else red_line(ln)
```
5. In `redline_source`: reset `_STRUCT['n'] = 0` at the start; build the context from the one classifier: `old_toks = [t for t in a if is_block_token(t)]`, `new_toks = [t for t in b if is_block_token(t)]`, `cls = structure_text.classify_blocks([reg_a[t] for t in old_toks], [reg_b[t] for t in new_toks])`, `ctx = {'removed': {old_toks[i] for i in cls['removed']}, 'added': {new_toks[j] for j in cls['added']}, 'changed': {new_toks[j] for _, j in cls['changed']}}`; pass `ctx` to every `emit_deleted_src` / `emit_inserted_src` call; and in the `replace` branch, BEFORE the existing 1:1 check, handle a single heading replaced by a single heading:
```python
            if (len(ol) == 1 and len(nl) == 1
                    and is_heading(ol[0]) and is_heading(nl[0])):
                out.append(nl[0] + '\n\n' + _note(NOTE_HEADING_CHANGED,
                                                 structure_text.heading_label(ol[0])))
                continue
```
   Return `(marked, n_del, n_ins)` exactly as before (the count lives in `_STRUCT`).
6. In `main`, after the `--source` branch, append the structural count to the tally ONLY for `--source`: `extra = (f', {_STRUCT["n"]} structural change(s) noted' if '--source' in flags else extra)` — keep `--full` and the digest's tally lines unchanged.

`UNMARKED_FIGURE_VISIBLE` is no longer emitted; leave the constant only if another call site still uses it (search), else delete it.

- [ ] **Step 4: Rewrite the assertions that pinned the old silence**

These existing assertions describe the behaviour this task replaces. Rewrite each to the new behaviour, with a one-line comment `# Wave 3b: a structural change now leaves a note (Ben, 2026-10-10)`. Change nothing else in those files.
- `test_redline_plain.py`: the `LEGEND_SOURCE_LIMITS` assertions (they quote "Only prose and the rows of simple tables are marked" and "leaves no trace") → assert the new legend sentence instead; the assertion that other modes must not carry "leaves no trace" → that no mode carries it; the assertions that a removed section / old figure leave no trace → assert the removed-heading / removed-table note is present and the old heading text appears only inside the note; the added heading verbatim (`"\n## 3. ADDED SECTION\n"`) → still verbatim, now followed by `*[Heading added]*`; the changed-block test expecting `UNMARKED_FIGURE_VISIBLE` → expect `UNMARKED_FIGURE_NOTE` then the changed note.
- `test_redline_structure.py`: tally assertions `0 line(s) removed, 0 line(s) added` remain true as substrings for marker-only (comment) changes — keep them; if any exact-equality match on the whole tally line breaks, match the new line. `~~<!--` / `\<!--` absence stays.
Report every assertion you changed, before → after.

- [ ] **Step 5: Run the tests**

Run: `python3 -m pytest build/tests/test_redline_markers.py build/tests/test_redline_plain.py build/tests/test_redline_structure.py build/tests/test_redline_stage.py -v`
Expected: all pass.

- [ ] **Step 6: Prove the untouched files; run the full suite**

Run Task 1's `git diff --stat main -- …` (prints nothing) and `python3 -m pytest build/tests -q` (all pass; report the count and every test whose page count changed because a real-tag redline now carries notes).

- [ ] **Step 7: Commit**

```bash
git add build/redline-text.py build/tests/test_redline_markers.py build/tests/test_redline_plain.py build/tests/test_redline_structure.py
git commit -m "$(cat <<'EOF'
redline: a note in the text wherever a heading, table or figure changed

A redline marks prose word by word; until now a removed table, a removed heading
or a retitled one left no trace at all -- one empty line and a tally of 0/0 --
and a changed table looked identical to an unchanged one in the PDF. Now each
leaves an italic, bracketed note at that spot, in both the PDF and the markdown
redline: heading added, removed or changed (with what it read); table or figure
new, removed or changed (by caption). The notes are body paragraphs, never red
or struck or a heading, and never carry a split-marker token. The legend and the
tally say so. Ruled by Ben Frey, 2026-10-10.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: A truthful disclosure page, for the whole Code or one Article

**Files:**
- Modify: `build/structural_note.py`
- Modify: `build/article-manifest.json` (each `units[]` entry gains `"label"`)
- Modify: `build/build-redline-full.sh` (the hard-coded 2025 old-side label)
- Modify: `build/tests/test_structural_note.py`

**Interfaces:**
- Consumes: Task 1's `czc_diff.structural_changes`; `czc_diff.Side`, `czc_diff.determine`, `czc_diff.Refusal`; `adoption_map.load`; `manifest.load`, `manifest.PROSE_RE`.
- Produces: `structural_note.py OUT_PDF [--map PATH] [--old-label L] [--scope code|article:N] [--old REF] [--new-dir DIR] [--md OUT_MD] [--pad-to-even]`.
  - `--scope code` (the default): the whole-Code note, now truthful; one page; `--pad-to-even` adds a blank.
  - `--scope article:N` (needs `--old`): the per-Article note; up to 4 pages of content, then `--pad-to-even` pads to even; refuses beyond 4.
  - `--md OUT_MD`: also writes the same note as markdown.

- [ ] **Step 1: Label the native units**

In `build/article-manifest.json`, give each unit a `"label"` — the plain words a resident would use:
- `district-maps.typ` → `"the District Maps"`
- `article-02.typ` → `"the thirteen district pages (district standards and use tables)"`
- `cross-section-plates.typ` → `"the ten Thoroughfare Type pages"`
- `street-type-inventory.typ` → `"Exhibit 3.1, the Thoroughfare Inventory"`
- `street-type-map.typ` → `"Exhibit 3.2, the Thoroughfare Type Map"`

- [ ] **Step 2: Write the failing tests**

Append to `build/tests/test_structural_note.py` (read its top first; reuse its `note_text` helper if it fits, else add `_text(pdf)` that joins page texts with pymupdf):

```python
# --- Wave 3b: truthful for the whole Code; scoped to one Article ----------------

import shutil as _shutil
import subprocess as _sp
import sys as _sys

_sys.path.insert(0, str(Path(__file__).resolve().parent))
import section_fixtures as _fx  # noqa: E402

_NOTE = Path(__file__).resolve().parent.parent / "structural_note.py"
_SHIPPED_MAP = Path(__file__).resolve().parent.parent / "adoption-map.json"
_PRE_ROLLOVER = Path(__file__).resolve().parent / "fixtures" / "adoption-map-v0.1-baseline.json"


def _note(tmp_path, *args, name="n.pdf"):
    out = tmp_path / name
    r = _sp.run([_sys.executable, str(_NOTE), str(out), *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    import pymupdf
    d = pymupdf.open(out)
    try:
        return "\n".join(p.get_text() for p in d), len(d)
    finally:
        d.close()


def test_the_identity_map_note_claims_nothing_false(tmp_path):
    """The NEGATIVE CONTROL the spec names: under the shipped identity map
    (baseline v1.0, nothing new, nothing non-comparable, nothing renumbered)
    the note must not say any Article is new, unmarked or renumbered. Before
    this wave it said all three, unconditionally."""
    text, _ = _note(tmp_path, "--map", str(_SHIPPED_MAP))
    assert "is new" not in text
    assert "UNMARKED" not in text
    assert "were renumbered" not in text
    assert "Three real changes" not in text
    assert "March 24, 2025" not in text
    assert "HOW TO READ THIS REDLINE" in text                     # the control: it rendered


def test_the_pre_rollover_map_still_discloses_all_three(tmp_path):
    text, pages = _note(tmp_path, "--map", str(_PRE_ROLLOVER))
    assert "Article 3" in text and "is new" in text
    assert "UNMARKED" in text
    assert "3 becomes 4" in text
    assert pages == 1


def test_pad_to_even(tmp_path):
    _, pages = _note(tmp_path, "--map", str(_PRE_ROLLOVER), "--pad-to-even")
    assert pages == 2


@pytest.fixture
def tree(tmp_path):
    return _fx.copy_full_source(tmp_path / "source")


def test_an_article_note_names_what_changed(tmp_path, tree):
    p = tree / "article-07-use-standards.md"
    p.write_text(p.read_text().replace("## 5. AMUSEMENT, OUTDOOR", "## 5. AMUSEMENT, OUTSIDE", 1))
    md = tmp_path / "n.md"
    text, pages = _note(tmp_path, "--scope", "article:7", "--old", "v1.0",
                        "--new-dir", str(tree), "--md", str(md), "--pad-to-even")
    assert pages % 2 == 0
    assert "Article 7" in text and "Use Standards" in text
    assert "its headings" in text
    assert "“5. AMUSEMENT, OUTDOOR”" in text and "“5. AMUSEMENT, OUTSIDE”" in text
    assert md.read_text().startswith("## How to read this redline")
    assert "5. AMUSEMENT, OUTSIDE" in md.read_text()


def test_an_unchanged_article_says_so(tmp_path, tree):
    text, _ = _note(tmp_path, "--scope", "article:7", "--old", "v1.0", "--new-dir", str(tree))
    assert "No change was found in this Article." in text


def test_the_article_2_note_names_the_district_pages_and_the_use_table_document(tmp_path, tree):
    text, pages = _note(tmp_path, "--scope", "article:2", "--old", "v1.0",
                        "--new-dir", str(tree), "--pad-to-even")
    assert "the thirteen district pages" in text
    assert "Use Table Changes" in text
    assert pages % 2 == 0


def test_a_table_only_change_is_named_on_the_page(tmp_path, tree):
    p = tree / "article-03-streets-roads-driveways.md"
    t = p.read_text()
    start = t.index("```{=typst}", t.index("b. To a point 4 ft above ground"))
    p.write_text(t[:start] + t[start:].replace("\n#", "\n// edited\n#", 1))
    text, _ = _note(tmp_path, "--scope", "article:3", "--old", "v1.0", "--new-dir", str(tree))
    assert "its tables or figures" in text
    assert "TABLE 3.2 SIGHT DISTANCE" in text


def test_an_article_scope_needs_an_old_ref(tmp_path):
    r = _sp.run([_sys.executable, str(_NOTE), str(tmp_path / "n.pdf"), "--scope", "article:7"],
                capture_output=True, text=True)
    assert r.returncode != 0 and "--old" in r.stderr
```

Make sure the module imports `pytest` and `Path` (it may already); add only what is missing.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_structural_note.py -v`
Expected: the new tests FAIL (unknown arguments; the identity-map note still says "is new"); the existing tests PASS.

- [ ] **Step 4: Make the whole-Code note truthful**

Rewrite `note_blocks(amap, old_label)` so every block that names an Article, a count or a "new" status is generated:
- "What this document compares" — as now, then: "Where a heading, table or figure was added, removed or changed, a note in italics and square brackets says so at that spot."
- For each `basename` with `amap.files[basename] is None` (new at this adoption), in Article order: heading `f"Article {n}, {name}, is new"` (`n` from the basename via `manifest.PROSE_RE`, `name` from that file's frontmatter `article-name` in the working tree's `source/`), body as now.
- Only if some Article moved (`article_shift_sentence`'s `moved` is non-empty): heading `f"The articles after Article {pivot} were renumbered"` and `article_shift_sentence(amap)`. Factor the `moved`/`pivot` computation into a helper so the heading and the sentence use the same values.
- For each entry of `amap.not_text_comparable`, in Article order: heading `f"Article {n} is reproduced UNMARKED"`, body as now with "Article 2" replaced by `f"Article {n}"`.
- "Figures, tables and maps show their current state" — the same body without "including the Article 3 inventory and Type map", plus: "Where one was added, removed or changed, the text says so in a note."
- Intro sentence: "Some changes cannot be marked word by word in a redline. They are stated here, once, before any marked text." (no count).
- Default `old_label`: `f"the previously adopted Code ({amap.baseline_version})"` — never a hard-coded date.
- **The code-scope note must stay exactly ONE page**: in the integrated redline it replaces the front-matter blank, so its page count is parity-critical. If the added sentences overflow the page under the pre-rollover map (which has the most blocks), tighten the existing body wording — never widen the box or shrink the type — and report what you shortened.

- [ ] **Step 5: Add the per-Article scope, the markdown, and even padding**

Add to `structural_note.py`:

```python
def _frontmatter_value(text: str, key: str) -> str:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    for line in (m.group(1).split("\n") if m else []):
        if line.startswith(key + ":"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def article_blocks(n: int, *, old_ref: str, new_dir: Path,
                   old_label: str | None = None) -> tuple[str, list[tuple[str, str]]]:
    """(subtitle, blocks) for Article n. Every sentence that names an Article, a
    kind of change, a heading or a table is generated from the change
    determination and the ownership map (ruling 8: kinds, never line counts)."""
    import czc_diff
    import manifest

    doc = manifest.load()
    entry = doc.get(str(n), {})
    prose = entry.get("prose") or next(
        (p.name for p in sorted(Path(new_dir).glob(f"article-0{n}-*.md"))), None)
    if prose is None:
        raise SystemExit(f"structural note: no prose for Article {n} in {new_dir}")
    new_text = (Path(new_dir) / prose).read_text(encoding="utf-8")
    name = _frontmatter_value(new_text, "article-name") or f"Article {n}"
    old = czc_diff.Side(ref=old_ref)
    c = czc_diff.determine(old, czc_diff.Side(root=Path(new_dir)))[n]
    raw = old.read(prose)
    sc = czc_diff.structural_changes(raw.decode("utf-8") if raw is not None else None, new_text)

    blocks = [(
        "What this document compares",
        f"This is Article {n}, {name}, as proposed, compared against {old_label or old_ref}. "
        f"Text added is shown in red; text deleted is struck through. Where a heading, table "
        f"or figure was added, removed or changed, a note in italics and square brackets says "
        f"so at that spot.")]

    kinds = [k for k, v in (("its wording", c.prose), ("its headings", c.heading),
                            ("its tables or figures", c.table),
                            ("the data its pages are printed from", c.data)) if v]
    if c.verdict == "SUBSTANTIVE":
        said = kinds[0] if len(kinds) == 1 else ", ".join(kinds[:-1]) + " and " + kinds[-1]
        what = f"This Article changed in substance: {said}."
    elif c.verdict == "NEEDS-CALL":
        what = ("No change to its wording, headings, tables or data was found, but some of its "
                "files changed in a way that needs a person's judgement (listed below).")
    elif c.verdict == "RENUMBER-ONLY":
        what = "Only references to renumbered sections changed; that renumbering is not marked."
    else:
        what = "No change was found in this Article."
    blocks.append(("What changed in this Article", what))

    items = ([f"Heading added: “{h}”" for h in sc["headings_added"]]
             + [f"Heading removed: “{h}”" for h in sc["headings_removed"]]
             + [f"Heading changed from “{a}” to “{b}”" for a, b in sc["headings_changed"]]
             + [f"Table or figure added: “{t}”" for t in sc["tables_added"]]
             + [f"Table or figure removed: “{t}”" for t in sc["tables_removed"]]
             + [f"Table or figure changed: “{t}”" for t in sc["tables_changed"]])
    blocks.append(("Headings, tables and figures",
                   "\n".join(f"• {i}" for i in items) if items
                   else "None of this Article's headings, tables or figures was added, removed "
                        "or changed."))

    labels = [u["label"] for u in entry.get("units", []) if u.get("label")]
    if labels:
        body = ("These are generated from data, so a text comparison cannot mark them; they "
                "appear as they now stand: " + "; ".join(labels) + ".")
        if n == 2:
            body += (" Every change to the district pages is listed item by item in the Use "
                     "Table Changes document.")
        blocks.append(("Shown in their current form, without marks", body))
    if c.needs_call:
        blocks.append(("Needs a person's judgement",
                       "\n".join(f"• {note}" for note in c.needs_call)))
    return f"Article {n} — {name}", blocks
```

Then refactor `build_note` into a renderer that flows blocks across pages:
- `render(out_pdf, title_sub, blocks, *, intro, max_pages, pad_to_even)`: the title bar ("HOW TO READ THIS REDLINE") and, when `title_sub` is given, a second line under it; then each block (heading + body) placed with `insert_textbox`. PyMuPDF writes nothing when text does not fit and returns a negative value: when a block does not fit in the remaining space, start a new page and place it there; if it does not fit on an EMPTY page, raise `SystemExit` naming the block. Refuse beyond `max_pages` (1 for `--scope code`, 4 for an Article) with a message saying which scope overflowed. With `pad_to_even`, append a blank page when the count is odd.
- `--md OUT_MD`: write `## How to read this redline` + (for an Article) `**{title_sub}**`, then for each block `### {heading}` + body (the `•` bullets become `- ` list items), separated by blank lines.
- `main`: add `--scope` (default `code`), `--old`, `--new-dir` (default `source/`), `--md`, `--pad-to-even`. `--scope article:N` without `--old` → exit 2 with a message naming `--old`. A `czc_diff.Refusal` → exit 1 with the refusal's message.

- [ ] **Step 6: Stop the whole-Code redline hard-coding 2025**

In `build/build-redline-full.sh`, the old-side label passed to the structural note and used in the cover caveat names "the Core Zoning Code adopted November 3, 2020 and amended through March 24, 2025". Replace that literal with a label derived the same way as the note's default: in baseline mode, `"the previously adopted Code (<baseline_version>)"` read from `adoption-map.json` via `python3 -c "import sys; sys.path.insert(0,'build'); import adoption_map; print(adoption_map.load().baseline_version)"`; otherwise `"$OLD_V"` as today. Change nothing else in that script.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_structural_note.py build/tests/test_manifest_ownership.py -v`
Expected: all pass — the existing structural-note tests too (they use the pre-rollover map).

- [ ] **Step 8: Prove the untouched files; run the full suite**

Task 1's `git diff --stat main -- …` (prints nothing); `python3 -m pytest build/tests -q` (all pass; report the count).

- [ ] **Step 9: Commit**

```bash
git add build/structural_note.py build/article-manifest.json build/build-redline-full.sh build/tests/test_structural_note.py
git commit -m "$(cat <<'EOF'
structural_note: truthful for the whole Code, and scoped to one Article

The "How to read this redline" page said, under the shipped v1.0 baseline, that
Article 3 was new, that Article 2 carried no marks and that articles had been
renumbered -- none true any longer -- and named an amended-through date of March
2025. Every such sentence is now generated from the adoption map, and the
default comparison label from its baseline.

A per-Article scope writes the page a standalone redline needs: what is compared,
which kinds of thing changed (wording, headings, tables, data -- never raw line
counts), each heading and table by name, which pages are generated and shown
unmarked (from the ownership map's new unit labels), and anything needing a
person's judgement. It flows across pages, pads to an even count, and is also
written as markdown for the redline that survives in the repository.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: The standalone redline

**Files:**
- Create: `build/build-redline-standalone.sh`
- Modify: `build/build-standalone.sh` (one seam: `OUT_MD_SOURCE`)
- Create: `build/tests/test_redline_standalone.py`

**Interfaces:**
- Consumes: `czc_redline_stage <src-dir> <stage-dir> <old-ver> <baseline-flag> <plain-flag> [basename ...]` (`build/redline-stage.sh` — read it for the exact flag values `build-redline-full.sh` passes for "baseline" and "plain", and use those); `czc_standalone_name <mode> <num> <name> <ver> [redline]` (`build/adoption-name.sh` — read it for the redline argument's exact form); `build-standalone.sh` seams `SRC_DIR`, `OUT_DIR`, `OUT_NAME_OVERRIDE`, `STANDALONE_FRONT_NOTE`; Task 3's `structural_note.py --scope article:N --old --new-dir --md --pad-to-even`.
- Produces: `build-redline-standalone.sh <article-NN> <new-ver> <old-ver> [date]`, honouring `SRC_DIR` (default `source/`), `ADOPTION_BASELINE=1` (compare against the adopted baseline, as the whole-Code redline does), `ADOPTION_MODE`/`ADOPTION_EVENT_DATE` (through `build-standalone.sh`, unchanged), and `REDLINE_OUT=<directory>` (a dry run: both files go there and `releases/` is not touched). Writes `<czc_standalone_name … redline>.pdf` and `.md`.

- [ ] **Step 1: Add the `.md` seam to `build-standalone.sh`**

At the header's list of seams add `#   OUT_MD_SOURCE      file copied as the .md deliverable (default: the prose source)`; where `FRONT_NOTE` is validated, also refuse a set-but-missing `OUT_MD_SOURCE` (`standalone: OUT_MD_SOURCE not found: …`, exit 1 — before `mkdir`); and change line 214 to `cp "${OUT_MD_SOURCE:-$PROSE}" "$RELEASE_DIR/$OUT_NAME.md"`.

- [ ] **Step 2: Write the failing tests**

Create `build/tests/test_redline_standalone.py`:

```python
"""build-redline-standalone.sh: the one-Article redline, in .pdf and .md, with a
generated "How to read this redline" page in front."""
import os
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import section_fixtures as fx  # noqa: E402
from test_standalone_seams import footer_numbers  # noqa: E402

REPO = TESTS.parent.parent
SCRIPT = REPO / "build" / "build-redline-standalone.sh"
VER = "v0.98-draft"
ART3 = "article-03-streets-roads-driveways.md"
ART7 = "article-07-use-standards.md"
RED = 0xCC0000


@pytest.fixture(scope="module")
def base_tree(tmp_path_factory):
    return fx.copy_full_source(tmp_path_factory.mktemp("v1") / "source")


@pytest.fixture
def tree(tmp_path, base_tree):
    import shutil
    return Path(shutil.copytree(base_tree, tmp_path / "source"))


def redline(tmp_path, tree, nn, old="v1.0", **env):
    out = tmp_path / "out"
    e = dict(os.environ, SRC_DIR=str(tree), REDLINE_OUT=str(out), **env)
    r = subprocess.run(["bash", str(SCRIPT), nn, VER, old], capture_output=True, text=True,
                       cwd=REPO, env=e)
    assert r.returncode == 0, r.stderr
    pdf = next(out.glob("*.pdf"))
    return pdf, pdf.with_suffix(".md")


def note_pages(pdf):
    """Leading pages with no footer number: the uncounted disclosure note."""
    pairs = footer_numbers(pdf)
    return pairs[0][0] - 1


def parity_violations(pdf):
    pairs = footer_numbers(pdf)
    k = note_pages(pdf)
    return [(phys, printed) for phys, printed in pairs
            if phys - printed != k or phys % 2 != printed % 2]


def red_spans(pdf, from_page):
    d = pymupdf.open(pdf)
    try:
        return [s["text"] for p in list(d)[from_page:]
                for b in p.get_text("dict")["blocks"] for line in b.get("lines", [])
                for s in line["spans"] if s["color"] == RED and s["text"].strip()]
    finally:
        d.close()


def text_of(pdf):
    d = pymupdf.open(pdf)
    try:
        return "\n".join(p.get_text() for p in d)
    finally:
        d.close()


def test_article_7_redline_is_marked_and_keeps_parity(tmp_path, tree):
    p = tree / ART7
    t = p.read_text()
    t = t.replace("## 5. AMUSEMENT, OUTDOOR", "## 5. AMUSEMENT, OUTSIDE", 1)
    t = t.replace("## 3. ADULT ESTABLISHMENT\n", "## 3. ADULT ESTABLISHMENT\n\nA new sentence.\n", 1)
    p.write_text(t)
    pdf, md = redline(tmp_path, tree, "07")
    k = note_pages(pdf)
    assert k >= 2 and k % 2 == 0
    assert footer_numbers(pdf)[0][1] == 1
    assert parity_violations(pdf) == []
    assert red_spans(pdf, k), "the added sentence must be marked red"
    body = text_of(pdf)
    assert "HOW TO READ THIS REDLINE" in body
    assert "Heading changed" in body
    m = md.read_text()
    assert "{=typst}" not in m and "rgb(" not in m
    assert "## How to read this redline" in m and "**" in m
    assert "*[Heading changed — it read: “5. AMUSEMENT, OUTDOOR”]*" in m


def test_the_parity_check_sees_an_uncounted_page(tmp_path, tree):
    """The second control: the predicate must be able to fail."""
    p = tree / ART7
    p.write_text(p.read_text().replace("## 3. ADULT ESTABLISHMENT\n",
                                       "## 3. ADULT ESTABLISHMENT\n\nA new sentence.\n", 1))
    pdf, _ = redline(tmp_path, tree, "07")
    d = pymupdf.open(pdf)
    d.new_page(pno=note_pages(pdf) + 1, width=612, height=792)
    broken = tmp_path / "broken.pdf"
    d.save(broken)
    d.close()
    assert parity_violations(broken) != []


def test_article_2_keeps_d1_on_a_verso(tmp_path, tree):
    p = tree / "article-02-prefatory.md"
    t = p.read_text()
    p.write_text(t.replace("\n\n", "\n\nAn added sentence in the prefatory text.\n\n", 2))
    pdf, _ = redline(tmp_path, tree, "02")
    d = pymupdf.open(pdf)
    try:
        first = next(i for i, pg in enumerate(d) if "LOT DIMENSIONS" in pg.get_text())
    finally:
        d.close()
    assert (first + 1) % 2 == 0, f"D1 is on physical page {first + 1}, a recto"
    assert parity_violations(pdf) == []


def test_a_table_only_change_has_no_red_mark_and_says_so(tmp_path, tree):
    """The spec's NEGATIVE CONTROL: a reader who sees no marks concludes nothing
    changed. The page and the text must both say a table changed."""
    p = tree / ART3
    t = p.read_text()
    start = t.index("```{=typst}", t.index("b. To a point 4 ft above ground"))
    p.write_text(t[:start] + t[start:].replace("\n#", "\n// edited\n#", 1))
    pdf, md = redline(tmp_path, tree, "03")
    assert red_spans(pdf, note_pages(pdf)) == []
    body = text_of(pdf)
    assert "Table or figure changed" in body                       # on the page and in the text
    assert body.count("TABLE 3.2 SIGHT DISTANCE") >= 3              # page + note + the table itself
    assert "*[Table or figure changed — shown in its current form, not marked: “TABLE 3.2 SIGHT DISTANCE”]*" in md.read_text()


def test_an_edited_type_pages_line_still_seats_the_plates_in_place(tmp_path, tree):
    """P3's interaction: the marker line's comment text changes, the token stays.
    The first Type plate must sit where it sits in an unmarked build, plus the note."""
    p = tree / ART3
    t = p.read_text()
    line = next(ln for ln in t.splitlines() if "TYPE-PAGES" in ln)
    p.write_text(t.replace(line, line.replace("<!--", "<!-- (edited)"), 1))
    pdf, _ = redline(tmp_path, tree, "03")
    plain = tmp_path / "plain"
    r = subprocess.run(["bash", "build/build-standalone.sh", "03", VER], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(tree), OUT_DIR=str(plain)),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    def first_plate(path):
        d = pymupdf.open(path)
        try:
            return next(i for i, pg in enumerate(d) if "MAIN STREET" in pg.get_text()
                        and "S1" in pg.get_text())
        finally:
            d.close()
    assert first_plate(pdf) == first_plate(next(plain.glob("*.pdf"))) + note_pages(pdf)


def test_a_dry_run_leaves_releases_untouched(tmp_path, tree):
    before = subprocess.run(["git", "status", "--porcelain", "--", "releases/"], cwd=REPO,
                            capture_output=True, text=True).stdout
    redline(tmp_path, tree, "09")
    after = subprocess.run(["git", "status", "--porcelain", "--", "releases/"], cwd=REPO,
                           capture_output=True, text=True).stdout
    assert before == after
    assert not (REPO / "releases" / VER).exists()


def test_the_output_names_are_the_standalone_redline_names(tmp_path, tree):
    pdf, md = redline(tmp_path, tree, "07")
    assert pdf.name.endswith(" — Redline.pdf") and md.name.endswith(" — Redline.md")
    assert "Article 7" in pdf.name
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_redline_standalone.py -v`
Expected: every test FAILS (the script does not exist).

- [ ] **Step 4: Write `build-redline-standalone.sh`**

Create it, executable, with a header comment in the style of `build-redline-full.sh`, and this behaviour, in this order:
1. `set -euo pipefail`; parse `<article-NN> <new-ver> <old-ver> [date]` (usage message and exit 1 if missing); `NUM=$((10#$1))`, `NN=$(printf %02d "$NUM")`; `SRC="${SRC_DIR:-$REPO_ROOT/source}"`; `BASELINE` from `ADOPTION_BASELINE` (the same value `build-redline-full.sh` derives).
2. Resolve the prose basename exactly as `build-standalone.sh` does (`manifest.py prose`, else `article-$NN-*.md` in `$SRC`); refuse if absent.
3. `TMP=$(mktemp -d)`, `trap 'rm -rf "$TMP"' EXIT`; source `build/redline-stage.sh` and `build/adoption-name.sh`.
4. Stage twice, ONE basename each: `czc_redline_stage "$SRC" "$TMP/stage" "$OLD_V" "$BASELINE" "" "$PRO"` (the PDF path) and `czc_redline_stage "$SRC" "$TMP/plain" "$OLD_V" "$BASELINE" <the plain flag value> "$PRO"` (the markdown). A non-zero return from either aborts with the stage's message.
5. The disclosure note: `python3 build/structural_note.py "$TMP/note.pdf" --scope "article:$NUM" --old "$OLD_V" --new-dir "$SRC" --md "$TMP/note.md" --pad-to-even`.
6. The `.md` deliverable: the plain-marked prose with the note's markdown inserted after its frontmatter and legend paragraph — a short `python3` heredoc that reads `$TMP/plain/$PRO`, splits off the leading `---…---` frontmatter, takes the first paragraph after it (the legend) and writes frontmatter + legend + blank line + note markdown + blank line + the rest to `$TMP/redline.md`.
7. Name: read `article-number` / `article-name` from `$SRC/$PRO`'s frontmatter; `NAME="$(czc_standalone_name "${ADOPTION_MODE:-draft}" "$ANUM" "$ANAME" "$NEW_V" <redline form>)"`.
8. Build: `SRC_DIR="$TMP/stage" OUT_DIR="$TMP/out" OUT_NAME_OVERRIDE="$NAME" STANDALONE_FRONT_NOTE="$TMP/note.pdf" OUT_MD_SOURCE="$TMP/redline.md" bash build/build-standalone.sh "$NN" "$NEW_V" "$DATE_STR"`.
9. Place: `DEST="${REDLINE_OUT:-$REPO_ROOT/releases/$NEW_V}"`; `mkdir -p "$DEST"`; move `$NAME.pdf` and `$NAME.md` there; print both paths.
Every refusal happens before step 9, so a refused run leaves no output directory.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_redline_standalone.py build/tests/test_standalone_seams.py -v`
Expected: all pass. If `test_article_2_keeps_d1_on_a_verso` fails, STOP and report the physical page of D1 and the note's page count — do not move the pad.

- [ ] **Step 6: Run it once by hand, as a person would**

```bash
REDLINE_OUT=/private/tmp/claude-501/w3b-try bash build/build-redline-standalone.sh 7 v0.98-draft v1.0
```
(Against the live tree this is an unchanged Article 7: expect a redline with no marks and a note saying "No change was found in this Article.") Put the note's first 20 lines of text (pymupdf) and the first 30 lines of the `.md` in your report.

- [ ] **Step 7: Prove the untouched files; run the full suite**

Task 1's `git diff --stat main -- …` (prints nothing); `python3 -m pytest build/tests -q` (all pass; report the count).

- [ ] **Step 8: Commit**

```bash
git add build/build-redline-standalone.sh build/build-standalone.sh build/tests/test_redline_standalone.py
git commit -m "$(cat <<'EOF'
build: the standalone redline, one Article in .pdf and .md

Standing rule 4 ships a standalone redline for every Article that changed in
substance; it did not exist. build-redline-standalone.sh stages that one
Article's prose twice -- marked for the PDF, plain for the markdown -- writes its
"How to read this redline" page, and builds through build-standalone.sh with the
page as uncounted, even-length front matter, so every footer still prints its
physical page's parity. The markdown carries the same page after its legend.
REDLINE_OUT is a dry run that never touches releases/. build-standalone.sh gains
one default-preserving seam, OUT_MD_SOURCE, because its .md was a copy of the
staged prose -- Typst, not markdown -- for a redline.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Done when

- A removed, added, retitled or changed heading, and a removed, new or changed table or figure, each leave the ruling-2 note at that spot in the PDF redline and the markdown redline; whole-line comments stay silent; the legend and tally say so.
- Under the shipped identity map the whole-Code note says nothing false; under the pre-rollover map it still makes all three disclosures; it no longer names March 2025.
- `structural_note.py --scope article:N` writes a generated, even-length page (and markdown) naming the kinds of change and each heading and table by name.
- `build-redline-standalone.sh` writes `<…> — Redline.pdf` and `.md` for any Article, with parity held, D1 on a verso for Article 2, the plates in place for Article 3, and a dry run that never touches `releases/`.
- The files listed as untouched are byte-identical to `main`; the full suite passes; CI is green on the PR.

## Not in this plan

- **Wave 3c**: honest standalone markdown (`czc_md.py`, P12) — the Article 2 data appendix, frontmatter chrome, `md_completeness` — and the Article 3 footer fix (`footer-date: "Draft v0.2-draft"`), as its own commit.
- **Threading a section map through redline staging**, and recording a person's call on a NEEDS-CALL Article — P13.
- **The plain-mode bold-on-bold artifact** (`⊕ ****Planting.** …` when an added line starts with bold) — logged; it renders as a bold paragraph, which is what an addition should look like.
