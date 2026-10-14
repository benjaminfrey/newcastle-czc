# Wave 3a — Change Determination and Use Table Changes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decide, from the prose AND the data, which Articles changed in substance between two versions of the Code (P10, `build/czc_diff.py`), and produce the Use Table Changes document that lists every change to Article 2's district data item by item (P11, `build/use_table_changes.py`).

**Architecture:** `czc_diff.py` owns the one keyed comparator: it flattens each json-keyed data source into leaves keyed by record and by title or label (so a re-extraction or an insertion does not cascade), diffs leaf maps, and combines that with three markdown counts computed on the Wave 2 normaliser's old side. It classifies every changed file through the ownership map in `build/article-manifest.json` before counting anything, and refuses rather than guess. `use_table_changes.py` imports that comparator, adds a small reader for the use-table legend in `article-02.typ`, and renders a memo-style markdown file in a fixed section order, whose total reconciles with the determination's Article 2 data count by construction.

**Tech Stack:** Python 3.14, pytest, git. The Use Table Changes markdown renders to PDF through the existing `build/build-memo.sh`; no new renderer.

**Spec:** `specs/2026-10-07-release-deliverables-scope.md` — §2 P10 and P11, §0 decisions D7 and D8, §3 Wave 3. Read both documents; where this plan's rulings differ from the spec's wording, the rulings govern and say why.

## Global Constraints

- **NEVER commit unless explicitly asked.** The operator authorises this plan's commit steps: implementers commit locally, by name, on branch `wave3a-change-determination`. Nothing is pushed.
- **NEVER `git add -A` or `git add .`** — stage files by name, exactly as each commit step lists them.
- **Never modify anything in `docs/`.** Nothing into `releases/`.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` — **project standing rule 5**, which deliberately overrides any other attribution suggestion.
- Build tests: `python3 -m pytest build/tests -q` from the repository root. **288 tests** at the start of this wave, about 4.5 minutes. CI runs the same suite on the PR. **Report the count you actually see.**
- **Untouched by this wave** (every task proves it with `git diff --stat main -- <these>` printing nothing): `build/adoption_breakdown.py`, `build/build-adoption.sh`, `build/adoption-map.json`, `build/adoption_map.py`, `build/baseline_selfcheck.py`, `build/section_map.py`, `build/redline_resolve.py`, `build/redline-text.py`, `build/redline-stage.sh`, `source/`. The spec leaves `adoption_breakdown.py` intact in this step; `build-adoption.sh:89` depends on its exit codes and "fix the map" messages.
- **`build/normalize_for_diff.py` gains exactly one public alias line** (Task 2). Nothing else in it changes.
- **Never pin the live working tree.** Every assertion with a count runs against two real tags, or against a tree materialised from the `v1.0` tag and then edited. The live tree will diverge from v1.0 the first time a real amendment is drafted; tests pinned to it fail at exactly the wrong moment (P17's lesson). The single live-tree test asserts only that the run completes.
- **VACUITY:** `v1.0` and the working tree differ only in five `.typ` layout files; all prose and all data are byte-identical. A "nothing changed" assertion sits beside a positive control in the same test.
- **Measured facts this plan relies on** (reproduced 2026-10-09; reproduce before relying on them):
  - `article-02-data.json` is a bare list of 13 records. `code` is **not** unique (seven records read `SD`); `(code, name)` is. Each record has 11 keys; the manifest's substantive fields are `code, name, left, right, matrix, use_col1, use_col2, use_standards`.
  - Use cells live in `use_col1` / `use_col2`: lists of `{"title": CATEGORY, "entries": [[label, status], …]}`. **819** cells; labels are unique within a record. Status counts at v1.0: `'' 450, u 218, sp 58, rc 52, ex 40, 'rc sp' 1`.
  - `matrix` is `null` for SD CONSERVATION, SD CAMPUS and SD MARINE.
  - D4 VILLAGE RESIDENTIAL's TRANSPORTATION & UTILITIES category is split at a soft hyphen into an empty `'TRANSPORTATION & UTIL\xad'` and an `'ITIES'` that carries its six cells.
  - **v0.24-draft → v1.0:** exactly one use cell changed — D3 NEIGHBORHOOD BUSINESS / COMMERCIAL GOODS / "Retail & Service, General", `rc` → `rc sp`; the `right` panels changed in 11 districts (D2, D3, D4, D5, D6, SD HISTORIC, SD HIGHWAY COMMERCIAL, SD RURAL HIGHWAY, SD CAMPUS, SD MARINE, SD FABRICATION); `inventory.json` changed `type` on 10 segments (all R2 → R3) and the derived `present_use` on 11; one prose line changed (Article 3, "[12]" → "12"); and the layout units `article-02.typ`, `street-type-inventory.typ` and `street-type-map.typ` changed.
  - The use-table legend is in `article-02.typ`: `#let glyphs = (u: "●", rc: "❶", sp: "❷", ex: "✪")`, four rows under `USE TABLE LEGEND` of the form `status("u"), [Use Permit Required], [CEO],`, and the Note `Note: Uses without #status("u"), … are not allowed in this District`.
  - `build/permit-review/ruleset_build/legend.py` is tracked (`parse_legend(typ_text) -> list[dict]`, rows `{code, permit, authority, glyph, …}` plus a `""` row carrying `note`), importable with `build/permit-review` on `sys.path`.
  - Only Article 3 has raw-Typst blocks: four ```` ```{=typst} ```` fences (Tables 3.2–3.5). Articles 4, 5, 6 and 8 have pipe tables, which the redline marks row by row, so they count as prose.
  - The live `source/` holds git-ignored junk: `.DS_Store` files and `exhibits/street-types/inventory.json.bak-*`.

### Twelve rulings this plan makes in writing

1. **Article 2 is keyed by `code + name`.** The manifest's `"key": "[].code"` collides on the seven SD districts and would merge them into one record. Task 1 changes it to `"[].code+name"`, and the comparator refuses any non-unique key.
2. **A shared file stops the determination** (Ben Frey, 2026-10-09). A change to a file listed under `shared` raises a refusal naming the file, until a person decides which Articles it affects. An unclaimed changed file, or one claimed twice, also refuses.
3. **Every count uses the one counting rule** (`normalize_for_diff`'s, exported as `marked_lines`): a modified line counts twice, once out and once in. The spec's "a table-only edit scores `table` 1" becomes `table` 2 for one modified block.
4. **The four counts are disjoint.** `prose` excludes headings and raw-Typst blocks; `heading` counts heading lines; `table` counts raw-Typst blocks, each compared whole. Frontmatter, HTML comments, blank lines and trailing whitespace count nowhere.
5. **A changed layout unit (`.typ`) needs a person's call**, as do binary exhibits and a generated file that changed while its source did not. The spec's four counts ignore layout units, but the use-table legend lives in `article-02.typ`; a silent zero there would repeat the false zero that already shipped. New verdict **NEEDS-CALL**, ranked below SUBSTANTIVE and above RENUMBER-ONLY. The release driver (P13) records the person's call.
6. **Leaves are keyed to survive an insertion.** A list of dicts that carry a `title` is keyed by title (a repeated title gets " [2]"); a list of `[label, …]` rows with distinct labels is keyed by label; any other list by position. An empty dict or list is itself a leaf.
7. **The ownership map is read from the working tree for both sides.** It is this instrument's configuration, not part of the Code's history; v1.0's own manifest predates `data_sources`.
8. **An Article whose prose is absent on the old side is NEW**: every line counts as added, and it is SUBSTANTIVE. One whose prose was deleted counts every old line as removed.
9. **A section map needs a directory new side.** `section_map.selfcheck` verifies a map against a tree, so `--section-map` with `--new-ref` is refused.
10. **The Use Table Changes document reports every substantive field of Article 2's data**, not just use cells. Its total then equals the determination's Article 2 data count by construction. The spec's test "v0.24-draft → v1.0 reproduces exactly the one D3 cell and nothing else" becomes: the D3 cell is the only *use-cell* change, and the eleven districts' standards changes are reported in their own section.
11. **The Use Table Changes document gives statuses in words**, e.g. "Residential Companion Permit (CEO) + Special Permit (Planning Board)", never as glyphs. The glyphs ● ❶ ❷ ✪ come from fonts that are not in `style/fonts`, so CI would render them as missing characters. A glyph appears only in a line reporting that a glyph itself changed.
12. **The legend is read by a small extractor in `use_table_changes.py`, never by importing the app's.** The build produces the legal instrument and the app consumes it. An agreement test pins the two readers together, and it must never be skipped or xfailed: if it is, the readers can drift apart silently.

## Review Focus

1. **Git-ignored junk in the live `source/`** (`.DS_Store`, `inventory.json.bak-*`) must not make the determination refuse as "unclaimed". Pinned in Task 3 (`test_the_live_tree_runs_and_ignores_git_ignored_junk`).
2. **A data file re-indented but semantically identical** must not count as a change. Pinned in Task 3 (`test_reformatting_a_data_file_is_not_a_change`).
3. **A data file absent on one side** (an Article's data added or deleted) must count every leaf, without crashing. Pinned in Task 1 (`test_an_absent_file_counts_every_leaf`).
4. **A field absent on the old side** (schema growth — `addresses` first appears at v0.24-draft) must not count when the field is derived, and must count when it is substantive. Pinned in Task 1 (`test_schema_growth_counts_only_substantive_fields`).
5. **D4's soft-hyphen category** must print whole as TRANSPORTATION & UTILITIES, never as "ITIES". Pinned in Task 5 (`test_the_soft_hyphen_category_prints_whole`).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `build/czc_diff.py` | **New.** The keyed comparator, the markdown counts, the per-Article determination and its CLI | Create (Task 1), extend (Tasks 2, 3) |
| `build/use_table_changes.py` | **New.** The legend reader and the Use Table Changes document | Create (Task 4), extend (Task 5) |
| `build/article-manifest.json` | Ownership map | Modify — Article 2's key becomes `[].code+name` (Task 1) |
| `build/normalize_for_diff.py` | Normaliser | Modify — one public alias, `marked_lines` (Task 2) |
| `build/tests/section_fixtures.py` | Test trees | Modify — add `copy_full_source` (Task 1) |
| `build/tests/test_czc_diff.py` | **New.** Determination tests | Create (Task 1), extend (Tasks 2, 3) |
| `build/tests/test_use_table_changes.py` | **New.** Legend and report tests | Create (Task 4), extend (Task 5) |

---

## Task 1: The keyed data comparator

**Files:**
- Create: `build/czc_diff.py`
- Create: `build/tests/test_czc_diff.py`
- Modify: `build/article-manifest.json` (Article 2's `key` and `_key_note`)
- Modify: `build/tests/section_fixtures.py` (add `copy_full_source`)

**Interfaces:**
- Consumes: `manifest.load() -> dict` (the parsed `article-manifest.json`).
- Produces (Tasks 3 and 5 rely on these exact names):
  - `czc_diff.Refusal(Exception)` — the determination cannot be made honestly.
  - `czc_diff.keyed_records(data, key: str) -> dict[str, object]` — record key strings like `"D3 / NEIGHBORHOOD BUSINESS"`.
  - `czc_diff.flatten(value, prefix: tuple = ()) -> dict[tuple, object]`
  - `czc_diff.Delta` dataclass: `changed: dict[path, (old, new)]`, `added: dict[path, new]`, `removed: dict[path, old]`, method `count() -> int`.
  - `czc_diff.diff_maps(old: dict, new: dict) -> Delta`
  - `czc_diff.json_leaves(raw: bytes | None, decl: dict) -> dict[tuple, object]`
  - `czc_diff.leaf_label(path: tuple) -> str`
  - `section_fixtures.copy_full_source(dest: Path, ref: str = "v1.0") -> Path` — ALL of `source/` as of `ref`.

- [ ] **Step 1: Add the full-tree fixture helper**

Append to `build/tests/section_fixtures.py`:

```python
def copy_full_source(dest: Path, ref: str = "v1.0") -> Path:
    """Materialise ALL of source/ as of `ref` -- data, layout units, exhibits --
    for the change-determination tests. copy_source above carries the article
    markdown only. `dest` must not exist; its parent must."""
    import io
    import tarfile

    raw = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", ref, "source"],
                         capture_output=True, check=True).stdout
    staging = dest.parent / (dest.name + ".staging")
    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        tf.extractall(staging, filter="data")
    (staging / "source").rename(dest)
    staging.rmdir()
    return dest
```

- [ ] **Step 2: Write the failing tests**

Create `build/tests/test_czc_diff.py`:

```python
"""build/czc_diff.py -- the substantive-change determination.

Every count asserted here comes from two REAL tags, or from a tree materialised
from the v1.0 tag and then edited. None pins the live working tree: it will
diverge from v1.0 the first time a real amendment is drafted.
"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import czc_diff  # noqa: E402
import manifest  # noqa: E402
import section_fixtures as fx  # noqa: E402

REPO = BUILD.parent
A2 = "article-02-data.json"
INV = "exhibits/street-types/inventory.json"
USE_COLS = ("use_col1", "use_col2")
# The calibrated positive control: commit 13b2a50 changed exactly this cell.
D3_CELL = ("D3 / NEIGHBORHOOD BUSINESS", "use_col2", "COMMERCIAL GOODS", "entries",
           "Retail & Service, General")
RIGHT_CHANGED = {"D2 / NEIGHBORHOOD RESIDENTIAL", "D3 / NEIGHBORHOOD BUSINESS",
                 "D4 / VILLAGE RESIDENTIAL", "D5 / VILLAGE BUSINESS", "D6 / TOWN CENTER",
                 "SD / HISTORIC", "SD / HIGHWAY COMMERCIAL", "SD / RURAL HIGHWAY",
                 "SD / CAMPUS", "SD / MARINE", "SD / FABRICATION"}


def _show(ref: str, rel: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:source/{rel}"],
                          capture_output=True, check=True).stdout


def _decl(article: str, rel: str) -> dict:
    return next(d for d in manifest.load()[article]["data_sources"] if d["path"] == rel)


def _cells(leaves: dict) -> dict:
    return {k: v for k, v in leaves.items()
            if len(k) == 5 and k[1] in USE_COLS and k[3] == "entries"}


# --- Article 2: the false zero that shipped ------------------------------------

def test_the_one_use_cell_that_changed_into_v1_0_is_found():
    """v0.24-draft -> v1.0 changed exactly one use cell. The text-only
    breakdown reported Article 2 at zero across that release; this comparator
    must find the cell, and the eleven districts' standards changes beside it."""
    old = czc_diff.json_leaves(_show("v0.24-draft", A2), _decl("2", A2))
    new = czc_diff.json_leaves(_show("v1.0", A2), _decl("2", A2))
    d = czc_diff.diff_maps(old, new)
    use_changes = {k: v for k, v in d.changed.items() if k[1] in USE_COLS}
    assert use_changes == {D3_CELL: ("rc", "rc sp")}
    assert not [k for k in [*d.added, *d.removed] if k[1] in USE_COLS]
    touched = {k[0] for k in [*d.changed, *d.added, *d.removed]}
    assert touched == RIGHT_CHANGED
    assert d.count() > 1


def test_v1_0_against_itself_reads_every_cell_and_finds_nothing():
    """'Nothing changed' alone proves nothing; the positive control is that all
    819 use cells were actually read."""
    leaves = czc_diff.json_leaves(_show("v1.0", A2), _decl("2", A2))
    assert len(_cells(leaves)) == 819
    assert czc_diff.diff_maps(leaves, dict(leaves)).count() == 0


def test_the_manifest_keys_article_2_by_code_and_name():
    assert _decl("2", A2)["key"] == "[].code+name"


def test_keying_article_2_by_code_alone_is_refused():
    """Seven districts are 'SD'. A code-only key would merge them into one record."""
    data = json.loads(_show("v1.0", A2))
    with pytest.raises(czc_diff.Refusal, match="not unique"):
        czc_diff.keyed_records(data, "[].code")
    assert len(czc_diff.keyed_records(data, "[].code+name")) == 13


def test_an_unknown_key_form_is_refused():
    with pytest.raises(czc_diff.Refusal, match="unknown key form"):
        czc_diff.keyed_records([], "records{}.id")


# --- Article 3's inventory: D7 ---------------------------------------------------

def test_inventory_type_changes_count_and_derived_fields_do_not():
    """v0.24-draft -> v1.0 re-typed ten segments R2 -> R3, and changed the
    DERIVED present_use on eleven. Only the ten are substance (decision D7)."""
    d = czc_diff.diff_maps(czc_diff.json_leaves(_show("v0.24-draft", INV), _decl("3", INV)),
                           czc_diff.json_leaves(_show("v1.0", INV), _decl("3", INV)))
    assert len(d.changed) == 10 and not d.added and not d.removed
    assert all(k[-1] == "type" and v == ("R2", "R3") for k, v in d.changed.items())


def test_schema_growth_counts_only_substantive_fields():
    """addresses first appears at v0.24-draft, on all 214 segments. It is
    derived, so it must not count. The positive control: with the field filter
    removed, the same comparison DOES see it -- so the filter is what hides it."""
    decl = _decl("3", INV)
    old, new = _show("v0.23-draft", INV), _show("v0.24-draft", INV)
    d = czc_diff.diff_maps(czc_diff.json_leaves(old, decl), czc_diff.json_leaves(new, decl))
    assert not [k for k in [*d.changed, *d.added, *d.removed] if "addresses" in k]
    unfiltered = {k: v for k, v in decl.items() if k != "substantive_fields"}
    d_all = czc_diff.diff_maps(czc_diff.json_leaves(old, unfiltered),
                               czc_diff.json_leaves(new, unfiltered))
    assert [k for k in d_all.added if "addresses" in k]


# --- The flattener ------------------------------------------------------------

def test_a_row_inserted_at_the_top_does_not_cascade():
    """Labelled rows are keyed by label, so inserting one is one addition, not
    a change to every row below it."""
    old = {"r": {"t": [["A", "1"], ["B", "2"]]}}
    new = {"r": {"t": [["Z", "0"], ["A", "1"], ["B", "2"]]}}
    d = czc_diff.diff_maps(czc_diff.flatten(old), czc_diff.flatten(new))
    assert (len(d.changed), len(d.added), len(d.removed)) == (0, 1, 0)


def test_a_repeated_title_is_kept_apart():
    """D1's right side has two panels titled DESIGN STANDARDS."""
    leaves = czc_diff.flatten([{"title": "X", "body": "a"}, {"title": "X", "body": "b"}])
    assert leaves == {("X", "body"): "a", ("X [2]", "body"): "b"}


def test_an_unlabelled_list_falls_back_to_position():
    assert czc_diff.flatten({"p": ["one", "two"]}) == {("p", "[0]"): "one", ("p", "[1]"): "two"}


def test_an_absent_file_counts_every_leaf():
    """An Article's data file added (or deleted) is every leaf added (or removed)."""
    new = czc_diff.json_leaves(_show("v1.0", A2), _decl("2", A2))
    assert czc_diff.json_leaves(None, _decl("2", A2)) == {}
    d = czc_diff.diff_maps({}, new)
    assert len(d.added) == len(new) > 819 and not d.changed and not d.removed


def test_invalid_json_is_refused():
    with pytest.raises(czc_diff.Refusal, match="not valid JSON"):
        czc_diff.json_leaves(b"{", _decl("2", A2))
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_czc_diff.py -v`
Expected: collection ERRORS with `ModuleNotFoundError: No module named 'czc_diff'`.

- [ ] **Step 4: Fix the manifest key**

In `build/article-manifest.json`, Article 2's data source, change

```json
        "key": "[].code",
        "_key_note": "the file is a bare LIST of 13 district objects, keyed by code",
```

to

```json
        "key": "[].code+name",
        "_key_note": "the file is a bare LIST of 13 district objects, keyed by code AND name: code alone is not unique -- seven districts are 'SD', and a code-only key would merge them",
```

- [ ] **Step 5: Write the comparator**

Create `build/czc_diff.py`:

```python
#!/usr/bin/env python3
"""The substantive-change determination: which Articles changed in substance
between two versions of the Code.

WHY. Standing rule 4 ships a standalone document and a standalone redline for
every Article with "changes to that Article's own standards, definitions or
data". Until this module the only instrument was adoption_breakdown.py, which
counts markdown lines only -- and so reported Article 2 at ZERO across
v0.24-draft -> v1.0, a release whose district data changed in eleven districts
and one use cell. That false zero shipped. This module reads the prose AND
every data source the ownership map (build/article-manifest.json) declares.

WHAT IT REPORTS, per Article -- four independent counts and a proposed verdict:
  prose    changed prose lines (frontmatter, HTML comments, blank lines,
           headings and raw-Typst blocks are not prose)
  heading  changed heading lines -- the redline can never mark a heading, so
           this is the only place an added, deleted or retitled section shows
  table    changed raw-Typst table blocks, which the redline renders unmarked
  data     changed leaves of the Article's json-keyed data sources, keyed by
           record, so a re-extracted or re-indented file is not a change
plus `suppressed` (section renumbers Rule 6 suppressed, given a section map)
and `needs_call` (files a machine cannot judge: layout units, binary exhibits,
and a generated file that changed while its source did not).

Every count uses the one counting rule (normalize_for_diff.marked_lines): a
modified line counts twice, once out and once in.

VERDICT -- proposed, never final; the release driver records any override:
  SUBSTANTIVE    any of prose / heading / table / data is nonzero
  NEEDS-CALL     none of those, but a file needs a person's call
  RENUMBER-ONLY  none of those, but section references were renumbered
  UNCHANGED      nothing
A retargeted cross-reference is never renumber-only (decision D8): Rule 6
rewrites a reference only to the number of a title-identical section, so a
retarget still differs and counts as prose.

IT REFUSES (exit 1) rather than guess when: a changed file is claimed by no
Article, or by two; a changed file is listed as shared (ruled by Ben Frey,
2026-10-09 -- what a shared change implies is undecided, so a person must say
which Articles it affects); a key is not unique; a JSON file does not parse; a
compare or key form is unknown; a ref does not exist; a section map fails its
self-check.

The ownership map is read from the WORKING TREE for both sides: it is this
instrument's configuration, not part of the Code's history (v1.0's own
manifest predates data_sources).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

BUILD = Path(__file__).resolve().parent
REPO = BUILD.parent
SOURCE = REPO / "source"
sys.path.insert(0, str(BUILD))

import manifest  # noqa: E402


class Refusal(Exception):
    """The determination cannot be made honestly. Exit 1, nothing written."""


# --- The keyed comparator. use_table_changes.py imports it; there is one. ----

def keyed_records(data, key: str) -> dict[str, object]:
    """The records of one json-keyed data source, keyed per its manifest `key`.

    The manifest leaves the key grammar to its consumer. The forms are:
      "$top-level-keys-except-_meta"  an object keyed by name, minus _meta
      "[].f1+f2"                      a bare list of records, keyed by f1 + f2
      "name[].f"                      the list under data["name"], keyed by f
    A record key is its field values joined with " / ". Refuses an unknown
    form, a record missing a key field, or a key that is not unique: a
    colliding key would silently merge two records into one.
    """
    if key == "$top-level-keys-except-_meta":
        if not isinstance(data, dict):
            raise Refusal(f"key {key!r} needs a JSON object, found {type(data).__name__}")
        return {str(k): v for k, v in data.items() if k != "_meta"}
    m = re.fullmatch(r"(\w*)\[\]\.(\w+(?:\+\w+)*)", key)
    if not m:
        raise Refusal(f"unknown key form {key!r}")
    container, fields = m.group(1), m.group(2).split("+")
    if container:
        records = data.get(container) if isinstance(data, dict) else None
    else:
        records = data
    if not isinstance(records, list):
        raise Refusal(f"key {key!r} needs a list of records, found {type(records).__name__}")
    out: dict[str, object] = {}
    for rec in records:
        if not isinstance(rec, dict) or any(f not in rec for f in fields):
            raise Refusal(f"key {key!r}: a record has no {'+'.join(fields)}")
        k = " / ".join(str(rec[f]) for f in fields)
        if k in out:
            raise Refusal(f"key {key!r} is not unique: {k!r} appears twice -- "
                          f"two records would be merged into one")
        out[k] = rec
    return out


def _list_keys(items: list) -> tuple[list[str], str]:
    """How to key the items of one list: by title, by label, or by position."""
    if all(isinstance(i, dict) and isinstance(i.get("title"), str) for i in items):
        seen: Counter = Counter()
        keys = []
        for i in items:
            seen[i["title"]] += 1
            n = seen[i["title"]]
            keys.append(i["title"] if n == 1 else f"{i['title']} [{n}]")
        return keys, "title"
    if all(isinstance(i, list) and len(i) >= 2 and isinstance(i[0], str) for i in items):
        firsts = [i[0] for i in items]
        if len(set(firsts)) == len(firsts):
            return firsts, "label"
    return [f"[{n}]" for n in range(len(items))], "index"


def flatten(value, prefix: tuple = ()) -> dict[tuple, object]:
    """Every leaf of `value`, keyed by a path that survives an insertion where
    it can: a dict by its keys; a list of titled dicts by title (a repeated
    title gets " [2]"); a list of [label, ...] rows with distinct labels by
    label; any other list by position. An empty dict or list is itself a leaf,
    so emptying one is a change."""
    if isinstance(value, dict):
        if not value:
            return {prefix: {}}
        out: dict[tuple, object] = {}
        for k, v in value.items():
            out.update(flatten(v, prefix + (str(k),)))
        return out
    if isinstance(value, list):
        if not value:
            return {prefix: []}
        keys, how = _list_keys(value)
        out = {}
        for k, item in zip(keys, value):
            if how == "title":
                item = {f: v for f, v in item.items() if f != "title"}
            elif how == "label":
                item = item[1] if len(item) == 2 else item[1:]
            out.update(flatten(item, prefix + (k,)))
        return out
    return {prefix: value}


@dataclass
class Delta:
    """What changed between two leaf maps."""
    changed: dict = field(default_factory=dict)   # path -> (old, new)
    added: dict = field(default_factory=dict)     # path -> new
    removed: dict = field(default_factory=dict)   # path -> old

    def count(self) -> int:
        return len(self.changed) + len(self.added) + len(self.removed)


def diff_maps(old: dict, new: dict) -> Delta:
    """The one keyed comparator. Order: the new side's, then removals in the old side's."""
    d = Delta()
    for k, v in new.items():
        if k not in old:
            d.added[k] = v
        elif old[k] != v:
            d.changed[k] = (old[k], v)
    for k, v in old.items():
        if k not in new:
            d.removed[k] = v
    return d


def json_leaves(raw: bytes | None, decl: dict) -> dict[tuple, object]:
    """The leaves of one json-keyed data source, each path starting with its
    record key. Restricted to the declaration's substantive_fields when it
    names them (decision D7: derived fields are not substance). An absent file
    has no leaves, so adding or deleting one counts every leaf."""
    if raw is None:
        return {}
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise Refusal(f"{decl.get('path')}: not valid JSON ({exc})") from exc
    fields = decl.get("substantive_fields")
    out: dict[tuple, object] = {}
    for rk, rec in keyed_records(data, decl["key"]).items():
        if fields is not None and isinstance(rec, dict):
            rec = {f: rec[f] for f in fields if f in rec}
        out.update(flatten(rec, (rk,)))
    return out


def leaf_label(path: tuple) -> str:
    """A leaf path as one readable string."""
    return " › ".join(path)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_czc_diff.py build/tests/test_manifest_ownership.py -v`
Expected: all pass — the 13 new tests and the ownership tests, which the key change must not disturb.

- [ ] **Step 7: Prove the untouched files and run the full suite**

```bash
git diff --stat main -- build/adoption_breakdown.py build/build-adoption.sh build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py build/section_map.py build/redline_resolve.py build/redline-text.py build/redline-stage.sh source/
python3 -m pytest build/tests -q
```
Expected: the `git diff` prints nothing; the suite reports about 301 passed (288 + 13). Report what you see.

- [ ] **Step 8: Commit**

```bash
git add build/czc_diff.py build/tests/test_czc_diff.py build/article-manifest.json build/tests/section_fixtures.py
git commit -m "$(cat <<'EOF'
build: a keyed comparator for the Code's data, and Article 2 keyed by code+name

The substantive-change determination needs to read the Code's data, not just
its markdown: the text-only breakdown reported Article 2 at zero across
v0.24-draft -> v1.0, a release that changed one use cell and the standards of
eleven districts. czc_diff.py starts with the comparator: each json-keyed data
source is flattened into leaves keyed by record and by title or label, so a
re-extracted file or an inserted row does not cascade, and derived fields are
left out per decision D7.

The manifest keyed Article 2 by code, which is not unique -- seven districts are
SD -- so it would have merged them. It is now keyed by code+name, and the
comparator refuses any key that is not unique.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: The markdown counts

**Files:**
- Modify: `build/normalize_for_diff.py` (one alias line, after `_marked`)
- Modify: `build/czc_diff.py`
- Modify: `build/tests/test_czc_diff.py`

**Interfaces:**
- Consumes: `normalize_for_diff.normalize_old_side(text, *, amap, smap=None)`, `normalize_for_diff.section_renumber(text, smap) -> (text, count)`, `adoption_map.AdoptionMap(baseline_version, article_numbers, files, not_text_comparable)`, `section_map.derive(old_ref, new_dir) -> dict`, `section_map.load(path)`.
- Produces:
  - `normalize_for_diff.marked_lines(o: list[str], n: list[str]) -> int` — the public name of the one counting rule.
  - `czc_diff.split_markdown(text: str) -> tuple[list[str], list[str], list[str]]` — `(prose, headings, blocks)`.
  - `czc_diff.markdown_counts(old: str | None, new: str, *, smap=None) -> dict[str, int]` — keys `prose`, `heading`, `table`, `suppressed`.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_czc_diff.py`:

```python
# --- The markdown counts --------------------------------------------------------

import adoption_map  # noqa: E402
import normalize_for_diff as nz  # noqa: E402
import section_map  # noqa: E402

ART3 = "article-03-streets-roads-driveways.md"
ART7 = "article-07-use-standards.md"
IDENTITY = adoption_map.AdoptionMap(baseline_version="v1.0",
                                    article_numbers={n: n for n in range(1, 10)},
                                    files={}, not_text_comparable={})
FM8 = '---\narticle-number: "8"\n---\n'


def _text(ref: str, rel: str) -> str:
    return _show(ref, rel).decode()


def _zero(counts: dict) -> bool:
    return counts == {"prose": 0, "heading": 0, "table": 0, "suppressed": 0}


def test_a_blank_line_is_not_a_change():
    """changed_line_count sees a blank line as a change; the determination must
    not. The positive control is the old counter seeing it."""
    old = _text("v1.0", ART7)
    new = old.replace("\n\n", "\n\n\n", 1)
    assert nz.changed_line_count(old, new, amap=IDENTITY) == 1
    assert _zero(czc_diff.markdown_counts(old, new))


def test_a_changed_prose_line_counts_twice():
    old = _text("v1.0", ART7)
    new = old.replace("ADULT ESTABLISHMENT\n\n", "ADULT ESTABLISHMENT\n\nAmended.\n\n", 1)
    assert new != old
    assert czc_diff.markdown_counts(old, new)["prose"] == 1          # one line added
    new2 = new.replace("Amended.", "Amended again.")
    assert czc_diff.markdown_counts(new, new2)["prose"] == 2         # one line out, one in


def test_an_edit_inside_a_raw_typst_table_counts_as_table_not_prose():
    """The redline renders a raw-Typst table unmarked, so this count is the only
    place the edit shows. It must still be SUBSTANTIVE (Task 3)."""
    old = _text("v1.0", ART3)
    new = old.replace("TABLE 3.2 SIGHT DISTANCE", "TABLE 3.2 SIGHT DISTANCES", 1)
    assert new != old
    assert czc_diff.markdown_counts(old, new) == {"prose": 0, "heading": 0, "table": 2,
                                                  "suppressed": 0}


def test_a_retitled_heading_counts_as_heading():
    old = _text("v1.0", ART7)
    new = old.replace("## 5. AMUSEMENT, OUTDOOR", "## 5. AMUSEMENT, OUTSIDE", 1)
    assert new != old
    assert czc_diff.markdown_counts(old, new) == {"prose": 0, "heading": 2, "table": 0,
                                                  "suppressed": 0}


def test_comments_and_frontmatter_are_not_changes():
    old = _text("v1.0", ART3)
    new = old.replace("<!-- The former TABLE 3.1a", "<!-- The retired TABLE 3.1a", 1)
    new = new.replace('article-number: "3"', 'article-number: "3"\nnote: "x"', 1)
    assert new != old
    assert _zero(czc_diff.markdown_counts(old, new))


def test_a_renumbered_reference_into_another_article_is_renumber_only():
    """Article 8 refers to Article 7 Section 4; a section is inserted into
    Article 7, so the reference becomes Section 5. Not a change in Article 8's
    substance -- with the map."""
    old, new = FM8 + "See Article 7 Section 4.\n", FM8 + "See Article 7 Section 5.\n"
    with_map = czc_diff.markdown_counts(old, new, smap={7: {4: 5}})
    assert with_map == {"prose": 0, "heading": 0, "table": 0, "suppressed": 1}
    assert czc_diff.markdown_counts(old, new)["prose"] == 2          # the control


def test_a_retargeted_reference_is_always_substantive():
    """Decision D8. Old §4 became §5; a reference that now says §6 points at
    different content."""
    old, new = FM8 + "See Article 7 Section 4.\n", FM8 + "See Article 7 Section 6.\n"
    assert czc_diff.markdown_counts(old, new, smap={7: {4: 5}})["prose"] == 2


def test_a_new_article_counts_every_line():
    new = _text("v1.0", ART7)
    counts = czc_diff.markdown_counts(None, new)
    prose, headings, blocks = czc_diff.split_markdown(new)
    assert counts["prose"] == len(prose) > 100
    assert counts["heading"] == len(headings) == 188     # 66 sections and their lettered sub-sections


def test_a_section_inserted_into_article_7_is_one_heading_and_one_line(tmp_path):
    """With the derived map, inserting a section is exactly the inserted heading
    and its sentence; the 64 renumbered headings are suppressed. Without the
    map, every shifted heading counts -- the control."""
    tree = fx.copy_source(tmp_path / "src")
    p = tree / ART7
    p.write_text(fx.insert_section(p.read_text(), 3, "AGRICULTURE", "Farming is permitted."))
    smap = {int(a): {int(o): n for o, n in m.items()}
            for a, m in section_map.derive("v1.0", tree)["articles"].items()}
    old, new = _text("v1.0", ART7), p.read_text()
    assert czc_diff.markdown_counts(old, new, smap=smap) == {
        "prose": 1, "heading": 1, "table": 0, "suppressed": 64}
    assert czc_diff.markdown_counts(old, new)["heading"] > 100
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_czc_diff.py -v`
Expected: the nine new tests FAIL with `AttributeError: module 'czc_diff' has no attribute 'markdown_counts'` (or `split_markdown`); Task 1's tests PASS.

- [ ] **Step 3: Export the counting rule**

In `build/normalize_for_diff.py`, immediately after the end of `_marked`, add:

```python
# The public name of the one counting rule, for callers outside this module
# (czc_diff.py), so that no second counter is ever written.
marked_lines = _marked
```

- [ ] **Step 4: Add the markdown counts**

In `build/czc_diff.py`, add `import adoption_map  # noqa: E402` and `import normalize_for_diff as nz  # noqa: E402` beside `import manifest`, then append:

```python
# --- The markdown counts ------------------------------------------------------

_FRONTMATTER = re.compile(r"\A---[ \t]*\n.*?\n---[ \t]*\n?", re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
_HEADING = re.compile(r"^\s*#{1,6}[ \t]")


def split_markdown(text: str) -> tuple[list[str], list[str], list[str]]:
    """(prose lines, heading lines, raw blocks). Frontmatter, HTML comments,
    blank lines and trailing whitespace are removed; each fenced block is kept
    whole as one item, so an edit inside it is one changed block."""
    text = _FRONTMATTER.sub("", text, count=1)
    text = _COMMENT.sub("", text)
    lines = text.split("\n")
    prose: list[str] = []
    headings: list[str] = []
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        m = _FENCE.match(lines[i])
        if m:
            close = re.compile(r"^[ \t]*" + re.escape(m.group(1)[0])
                               + "{" + str(len(m.group(1))) + r",}[ \t]*$")
            block = [lines[i]]
            i += 1
            while i < len(lines):
                block.append(lines[i])
                i += 1
                if close.match(block[-1]):
                    break
            blocks.append("\n".join(block))
            continue
        line = lines[i].rstrip()
        i += 1
        if line.strip():
            (headings if _HEADING.match(line) else prose).append(line)
    return prose, headings, blocks


def _identity_amap():
    """The determination compares drafts and never renumbers Articles, so the
    old side's article map is identity. Built here, not read from
    adoption-map.json, which this module must not depend on."""
    return adoption_map.AdoptionMap(baseline_version="czc_diff",
                                    article_numbers={n: n for n in range(1, 10)},
                                    files={}, not_text_comparable={})


def markdown_counts(old: str | None, new: str, *, smap=None) -> dict[str, int]:
    """prose / heading / table counts for one Article's markdown, and the
    section renumbers Rule 6 suppressed. The OLD side is normalised exactly as
    the redline's old side is (heading case, and with a section map, Rule 6);
    the new side is read as written. `old` None means the Article is new."""
    if old is None:
        o_prose, o_heads, o_blocks, suppressed = [], [], [], 0
    else:
        suppressed = nz.section_renumber(old, smap)[1] if smap else 0
        o_prose, o_heads, o_blocks = split_markdown(
            nz.normalize_old_side(old, amap=_identity_amap(), smap=smap))
    n_prose, n_heads, n_blocks = split_markdown(new)
    return {"prose": nz.marked_lines(o_prose, n_prose),
            "heading": nz.marked_lines(o_heads, n_heads),
            "table": nz.marked_lines(o_blocks, n_blocks),
            "suppressed": suppressed}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_czc_diff.py build/tests/test_normalize_for_diff.py -v`
Expected: all pass. If `test_a_section_inserted_into_article_7_is_one_heading_and_one_line` reports a `suppressed` other than 64, STOP and report the number — do not adjust the assertion.

- [ ] **Step 6: Prove the untouched files and run the full suite**

```bash
git diff --stat main -- build/adoption_breakdown.py build/build-adoption.sh build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py build/section_map.py build/redline_resolve.py build/redline-text.py build/redline-stage.sh source/
git diff main -- build/normalize_for_diff.py | grep '^[+-][^+-]'
python3 build/baseline_selfcheck.py; echo "rc=$?"
python3 -m pytest build/tests -q
```
Expected: the first `git diff` prints nothing; the second shows only the three added lines (the comment and `marked_lines = _marked`); `0 marked lines`, `rc=0`; the suite reports about 310 passed.

- [ ] **Step 7: Commit**

```bash
git add build/czc_diff.py build/normalize_for_diff.py build/tests/test_czc_diff.py
git commit -m "$(cat <<'EOF'
czc_diff: count prose, headings and raw tables separately

Three disjoint counts per Article's markdown, on the same old side the redline
renders: prose lines, heading lines -- which the redline can never mark -- and
raw-Typst table blocks, which it renders unmarked. Blank lines, frontmatter and
HTML comments count nowhere. With a section map, renumbered headings and
references are suppressed and counted, so an Article whose only change is a
renumbered cross-reference can be told apart; a retargeted reference still
counts (decision D8).

normalize_for_diff gains one line: a public name for its counting rule, so this
module uses the same rule instead of writing a second one.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: The determination and its CLI

**Files:**
- Modify: `build/czc_diff.py`
- Modify: `build/tests/test_czc_diff.py`

**Interfaces:**
- Consumes: Tasks 1–2; `manifest.claimants(doc, path) -> list[str]`, `manifest.PROSE_RE`; `section_map.selfcheck(path, old_ref, new_dir) -> list[str]`, `section_map.load(path)`.
- Produces:
  - `czc_diff.Side(*, ref: str | None = None, root: Path | None = None)` — `.files() -> list[str]`, `.read(rel) -> bytes | None`, `.label: str`, `.root: Path | None`. Raises `Refusal` for a ref that is not a commit.
  - `czc_diff.ArticleCounts` dataclass — `article, prose, heading, table, data, suppressed, new, needs_call: list[str], data_detail: dict[str, Delta]`; property `verdict`; method `as_json() -> dict`.
  - `czc_diff.determine(old: Side, new: Side, *, doc: dict | None = None, smap=None) -> dict[int, ArticleCounts]`
  - CLI: `python3 build/czc_diff.py --old REF [--new-ref REF | --new-dir DIR] [--section-map PATH] [--article N] [--json PATH]` — exit 0 reported, 1 refused.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_czc_diff.py`:

```python
# --- The determination -----------------------------------------------------------

CLI = [sys.executable, str(BUILD / "czc_diff.py")]


@pytest.fixture(scope="module")
def base_tree(tmp_path_factory):
    """ALL of source/ at v1.0, materialised once and copied per test."""
    return fx.copy_full_source(tmp_path_factory.mktemp("v1") / "source")


@pytest.fixture(scope="module")
def v1():
    return czc_diff.Side(ref="v1.0")


@pytest.fixture
def tree(tmp_path, base_tree):
    return Path(shutil.copytree(base_tree, tmp_path / "source"))


def _edit_json(tree, rel, fn, indent=2):
    p = tree / rel
    data = json.loads(p.read_text())
    fn(data)
    p.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + "\n")


def _flip_d3(data):
    rec = next(r for r in data if (r["code"], r["name"]) == ("D3", "NEIGHBORHOOD BUSINESS"))
    cat = next(c for c in rec["use_col2"] if c["title"] == "COMMERCIAL GOODS")
    entry = next(e for e in cat["entries"] if e[0] == "Retail & Service, General")
    assert entry[1] == "rc sp"
    entry[1] = "rc"


def _others_unchanged(result, *except_):
    return all(c.verdict == "UNCHANGED" for n, c in result.items() if n not in except_)


def test_two_real_tags():
    """v0.24-draft -> v1.0, against v1.0 -> v1.0 in the same test: the second
    alone would pass with no code at all."""
    r = czc_diff.determine(czc_diff.Side(ref="v0.24-draft"), czc_diff.Side(ref="v1.0"))
    a2, a3 = r[2], r[3]
    assert a2.verdict == "SUBSTANTIVE" and a2.prose == 0 and a2.data > 1
    assert a2.data_detail[A2].changed[D3_CELL] == ("rc", "rc sp")
    assert any(n.startswith("article-02.typ:") for n in a2.needs_call)
    assert (a3.prose, a3.heading, a3.table, a3.data) == (2, 0, 0, 10)
    assert a3.verdict == "SUBSTANTIVE"
    assert {n.split(":")[0] for n in a3.needs_call} == {"street-type-inventory.typ",
                                                         "street-type-map.typ"}
    assert _others_unchanged(r, 2, 3)
    same = czc_diff.determine(czc_diff.Side(ref="v1.0"), czc_diff.Side(ref="v1.0"))
    assert _others_unchanged(same) and not any(c.needs_call for c in same.values())


def test_flipping_one_use_status_reports_exactly_that_cell(tree, v1):
    """The negative control the spec names: one status flipped, one cell reported."""
    _edit_json(tree, A2, _flip_d3)
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[2].data == 1
    assert r[2].data_detail[A2].changed == {D3_CELL: ("rc sp", "rc")}
    assert r[2].verdict == "SUBSTANTIVE" and _others_unchanged(r, 2)


def test_reformatting_a_data_file_is_not_a_change(tree, v1):
    _edit_json(tree, A2, lambda d: None, indent=4)
    assert (tree / A2).read_bytes() != _show("v1.0", A2)          # the bytes really differ
    assert _others_unchanged(czc_diff.determine(v1, czc_diff.Side(root=tree)))


def test_a_derived_inventory_field_is_not_substance(tree, v1):
    def change(d):
        seg = next(s for s in d["segments"] if s["id"] == "camp-road-1")
        seg["present_use"] = "Something else"
    _edit_json(tree, INV, change)
    assert _others_unchanged(czc_diff.determine(v1, czc_diff.Side(root=tree)))


def test_every_field_of_a_type_is_substance(tree, v1):
    """types.json declares no substantive_fields, so every leaf counts."""
    _edit_json(tree, "exhibits/cross-sections/types.json",
               lambda d: d["S1"].__setitem__("name", "MAIN STREET, AMENDED"))
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[3].data == 1 and r[3].verdict == "SUBSTANTIVE" and not r[3].needs_call


def test_a_regenerated_figure_alone_needs_a_call(tree, v1):
    """S1.svg is generated from types.json. Changed while types.json did not is
    an anomaly -- or a change to its other input -- and a person decides."""
    (tree / "exhibits/cross-sections/S1.svg").write_text(
        (tree / "exhibits/cross-sections/S1.svg").read_text() + "<!-- x -->\n")
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[3].verdict == "NEEDS-CALL"
    assert any("S1.svg" in n and "did not" in n for n in r[3].needs_call)


def test_a_figure_regenerated_with_its_source_is_counted_through_the_source(tree, v1):
    _edit_json(tree, "exhibits/cross-sections/types.json",
               lambda d: d["S1"].__setitem__("name", "MAIN STREET, AMENDED"))
    (tree / "exhibits/cross-sections/S1.svg").write_text(
        (tree / "exhibits/cross-sections/S1.svg").read_text() + "<!-- x -->\n")
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[3].data == 1 and not r[3].needs_call


def test_a_binary_exhibit_needs_a_call(tree, v1):
    sprite = next(p for p in sorted((tree / "exhibits/cross-sections/sprites").rglob("*"))
                  if p.is_file() and p.name != "NOTICE.md")
    sprite.write_bytes(sprite.read_bytes() + b"\0")
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[3].verdict == "NEEDS-CALL"
    assert any("changed (binary)" in n for n in r[3].needs_call)


def test_a_layout_unit_change_needs_a_call(tree, v1):
    """Ruling 5: the use-table legend lives in article-02.typ, so a changed
    layout unit is never silently zero."""
    (tree / "article-02.typ").write_text((tree / "article-02.typ").read_text() + "\n// x\n")
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[2].verdict == "NEEDS-CALL" and _others_unchanged(r, 2)


def test_an_edited_raw_table_is_substantive_though_the_redline_shows_no_mark(tree, v1):
    p = tree / ART3
    p.write_text(p.read_text().replace("TABLE 3.2 SIGHT DISTANCE", "TABLE 3.2 SIGHT DISTANCES", 1))
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert (r[3].prose, r[3].table) == (0, 2) and r[3].verdict == "SUBSTANTIVE"


def test_an_ignored_file_is_not_a_change(tree, v1):
    p = tree / "exhibits/street-types/inventory-sample.json"
    p.write_text(p.read_text() + "\n")
    assert _others_unchanged(czc_diff.determine(v1, czc_diff.Side(root=tree)))


# --- Refusals: never guess -----------------------------------------------------

def test_an_unclaimed_changed_file_is_refused(tree, v1):
    (tree / "exhibits/new-thing.json").write_text("{}\n")
    with pytest.raises(czc_diff.Refusal, match="exhibits/new-thing.json"):
        czc_diff.determine(v1, czc_diff.Side(root=tree))


def test_a_changed_shared_file_is_refused(tree, v1):
    """Ruled by Ben Frey, 2026-10-09."""
    doc = copy.deepcopy(manifest.load())
    doc["shared"] = [A2]
    _edit_json(tree, A2, _flip_d3)
    with pytest.raises(czc_diff.Refusal, match="shared"):
        czc_diff.determine(v1, czc_diff.Side(root=tree), doc=doc)


def test_unwiring_article_2s_data_is_refused_not_reported_as_zero(tree, v1):
    """The spec's second control. 'Article 2 reports zero' is the failure that
    already shipped; without the data_sources wiring the file is unclaimed and
    the determination refuses instead."""
    doc = copy.deepcopy(manifest.load())
    doc["2"]["data_sources"] = []
    _edit_json(tree, A2, _flip_d3)
    with pytest.raises(czc_diff.Refusal, match="no Article claims"):
        czc_diff.determine(v1, czc_diff.Side(root=tree), doc=doc)


def test_the_old_code_only_key_is_refused(tree, v1):
    doc = copy.deepcopy(manifest.load())
    doc["2"]["data_sources"][0]["key"] = "[].code"
    _edit_json(tree, A2, _flip_d3)
    with pytest.raises(czc_diff.Refusal, match="not unique"):
        czc_diff.determine(v1, czc_diff.Side(root=tree), doc=doc)


def test_broken_json_is_refused(tree, v1):
    (tree / INV).write_text("{")
    with pytest.raises(czc_diff.Refusal, match="not valid JSON"):
        czc_diff.determine(v1, czc_diff.Side(root=tree))


def test_a_bad_ref_is_refused():
    with pytest.raises(czc_diff.Refusal, match="not a commit"):
        czc_diff.Side(ref="no-such-ref-xyz")


# --- The CLI --------------------------------------------------------------------

def _cli(*args):
    return subprocess.run([*CLI, *args], capture_output=True, text=True, cwd=REPO)


def test_the_cli_reports_and_writes_json(tmp_path):
    out = tmp_path / "d.json"
    r = _cli("--old", "v0.24-draft", "--new-ref", "v1.0", "--json", str(out))
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text())
    assert doc["articles"]["2"]["verdict"] == "SUBSTANTIVE"
    assert {"path": czc_diff.leaf_label(D3_CELL), "old": "rc", "new": "rc sp"} in \
        doc["articles"]["2"]["data_detail"][A2]["changed"]
    assert sorted(doc["articles"], key=int) == [str(n) for n in range(1, 10)]


def test_the_cli_refuses_with_exit_1_and_writes_nothing(tmp_path):
    out = tmp_path / "d.json"
    r = _cli("--old", "no-such-ref-xyz", "--new-ref", "v1.0", "--json", str(out))
    assert r.returncode == 1 and "refusing" in r.stderr and not out.exists()


def test_a_section_map_with_a_ref_new_side_is_refused(tmp_path):
    m = tmp_path / "m.json"
    m.write_text("{}")
    r = _cli("--old", "v1.0", "--new-ref", "v1.0", "--section-map", str(m))
    assert r.returncode == 1 and "--new-dir" in r.stderr


def test_a_section_inserted_into_article_7_end_to_end(tree, tmp_path):
    p = tree / ART7
    p.write_text(fx.insert_section(p.read_text(), 3, "AGRICULTURE", "Farming is permitted."))
    m = tmp_path / "map.json"
    d = subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                        "--new-dir", str(tree), "--out", str(m)],
                       capture_output=True, text=True, cwd=REPO)
    assert d.returncode == 0, d.stderr
    out = tmp_path / "d.json"
    r = _cli("--old", "v1.0", "--new-dir", str(tree), "--section-map", str(m), "--json", str(out))
    assert r.returncode == 0, r.stderr
    a = json.loads(out.read_text())["articles"]
    assert (a["7"]["prose"], a["7"]["heading"], a["7"]["suppressed"]) == (1, 1, 64)
    assert a["7"]["verdict"] == "SUBSTANTIVE"
    assert all(a[str(n)]["verdict"] == "UNCHANGED" for n in range(1, 10) if n != 7)


def test_the_live_tree_runs_and_ignores_git_ignored_junk():
    """The live source/ holds .DS_Store files and inventory.json.bak-* backups,
    which git ignores. They are not part of the Code and must not be refused as
    unclaimed. No count is pinned: the live tree moves."""
    r = _cli("--old", "v1.0")
    assert r.returncode == 0, r.stderr
    rows = [ln.split() for ln in r.stdout.splitlines()]
    assert [row[0] for row in rows if row and row[0].isdigit()] == [str(n) for n in range(1, 10)]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_czc_diff.py -v`
Expected: the 23 new tests FAIL or ERROR (`czc_diff` has no `Side` / `determine`, and the CLI has no `main`); Tasks 1–2's tests PASS.

- [ ] **Step 3: Add the sides, the determination and the CLI**

In `build/czc_diff.py`, add `import argparse` and `import subprocess` to the imports, then append:

```python
# --- The two sides --------------------------------------------------------------

def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True,
                          text=True, check=True).stdout


class Side:
    """One version of source/: a git ref, or a directory."""

    def __init__(self, *, ref: str | None = None, root: Path | None = None):
        if (ref is None) == (root is None):
            raise ValueError("a Side is a ref or a directory, not both or neither")
        if ref is not None:
            ok = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", "--quiet",
                                 f"{ref}^{{commit}}"], capture_output=True)
            if ok.returncode != 0:
                raise Refusal(f"{ref!r} is not a commit in this repository")
        self.ref = ref
        self.root = Path(root) if root is not None else None
        self.label = ref if ref is not None else str(self.root)
        self._cache: dict[str, bytes | None] = {}

    def files(self) -> list[str]:
        """Every file of the Code on this side, relative to source/."""
        if self.ref is not None:
            out = _git("ls-tree", "-r", "--name-only", self.ref, "source/")
            return sorted(p[len("source/"):] for p in out.splitlines() if p)
        if self.root.resolve() == SOURCE.resolve():
            # The live tree: what git tracks plus what it would track. Ignored
            # files (.DS_Store, inventory.json.bak-*) are not part of the Code.
            listed = set(_git("ls-files", "source/").splitlines())
            listed |= set(_git("ls-files", "--others", "--exclude-standard", "source/").splitlines())
            return sorted(p[len("source/"):] for p in listed if p and (REPO / p).is_file())
        return sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*")
                      if p.is_file()
                      and not any(part.startswith(".") for part in p.relative_to(self.root).parts))

    def read(self, rel: str) -> bytes | None:
        """The file's bytes on this side, or None if it does not exist here."""
        if rel not in self._cache:
            if self.ref is not None:
                r = subprocess.run(["git", "-C", str(REPO), "show", f"{self.ref}:source/{rel}"],
                                   capture_output=True)
                self._cache[rel] = r.stdout if r.returncode == 0 else None
            else:
                p = self.root / rel
                self._cache[rel] = p.read_bytes() if p.is_file() else None
        return self._cache[rel]


# --- The determination ----------------------------------------------------------

@dataclass
class ArticleCounts:
    article: int
    prose: int = 0
    heading: int = 0
    table: int = 0
    data: int = 0
    suppressed: int = 0
    new: bool = False
    needs_call: list[str] = field(default_factory=list)
    data_detail: dict[str, Delta] = field(default_factory=dict)

    @property
    def verdict(self) -> str:
        if self.prose or self.heading or self.table or self.data:
            return "SUBSTANTIVE"
        if self.needs_call:
            return "NEEDS-CALL"
        if self.suppressed:
            return "RENUMBER-ONLY"
        return "UNCHANGED"

    def as_json(self) -> dict:
        return {
            "prose": self.prose, "heading": self.heading, "table": self.table,
            "data": self.data, "suppressed": self.suppressed, "new": self.new,
            "verdict": self.verdict, "needs_call": self.needs_call,
            "data_detail": {
                path: {"changed": [{"path": leaf_label(k), "old": o, "new": n}
                                   for k, (o, n) in d.changed.items()],
                       "added": [{"path": leaf_label(k), "new": v} for k, v in d.added.items()],
                       "removed": [{"path": leaf_label(k), "old": v} for k, v in d.removed.items()]}
                for path, d in self.data_detail.items()},
        }


def _declaration(doc: dict, article: str, rel: str) -> dict | None:
    for d in doc.get(article, {}).get("data_sources", []):
        p = d.get("path", "")
        if (rel.startswith(p) if p.endswith("/") else rel == p):
            return d
    return None


def determine(old: Side, new: Side, *, doc: dict | None = None, smap=None) -> dict[int, ArticleCounts]:
    """Per-Article counts and a proposed verdict. Every changed file is
    classified through the ownership map BEFORE anything is counted, so a
    refusal is never preceded by a partial answer."""
    doc = manifest.load() if doc is None else doc
    result = {int(k): ArticleCounts(int(k)) for k in doc if k.isdigit()}
    changed = [p for p in sorted(set(old.files()) | set(new.files()))
               if old.read(p) != new.read(p)]

    owner: dict[str, str] = {}
    for p in changed:
        who = manifest.claimants(doc, p)
        if not who:
            raise Refusal(f"{p}: changed, and no Article claims it in build/article-manifest.json. "
                          f"Declare it in an Article's data_sources, or list it under ignored.")
        if len(who) > 1:
            raise Refusal(f"{p}: claimed by {', '.join(who)} -- the ownership map must name "
                          f"exactly one")
        if who[0] == "shared":
            raise Refusal(f"{p}: changed, and it is listed as shared. What a change to a shared "
                          f"file means for the determination is not decided, so a person must say "
                          f"which Articles it affects (ruled by Ben Frey, 2026-10-09).")
        if who[0] != "ignored":
            owner[p] = who[0]

    for p, art in owner.items():
        c = result[int(art)]
        if manifest.PROSE_RE.match(p):
            o, n = old.read(p), new.read(p)
            counts = markdown_counts(o.decode("utf-8") if o is not None else None,
                                     n.decode("utf-8") if n is not None else "", smap=smap)
            c.prose += counts["prose"]
            c.heading += counts["heading"]
            c.table += counts["table"]
            c.suppressed += counts["suppressed"]
            c.new = c.new or o is None
            continue
        if any(u.get("typ") == p for u in doc[art].get("units", [])):
            c.needs_call.append(f"{p}: a layout unit changed. A person decides whether it changes "
                                f"what the Code says (the use-table legend lives in one) or only "
                                f"how it is laid out.")
            continue
        d = _declaration(doc, art, p)
        compare = d.get("compare") if d else None
        if compare == "json-keyed":
            delta = diff_maps(json_leaves(old.read(p), d), json_leaves(new.read(p), d))
            if delta.count():
                c.data += delta.count()
                c.data_detail[p] = delta
        elif compare == "binary-hash":
            c.needs_call.append(f"{p}: changed (binary). A person decides whether it changes the Code.")
        elif compare == "generated-from":
            if d["from"] not in owner:
                c.needs_call.append(f"{p}: changed although its source {d['from']} did not -- an "
                                    f"anomaly, or a change to its other input (see the manifest note)")
        else:
            raise Refusal(f"{p}: unknown compare form {compare!r} in build/article-manifest.json")
    return result


# --- The CLI ----------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Which Articles changed in substance between two versions of the Code.")
    ap.add_argument("--old", required=True, help="the old version: a git ref")
    side = ap.add_mutually_exclusive_group()
    side.add_argument("--new-ref", help="the new version as a git ref")
    side.add_argument("--new-dir", help="the new version as a source directory (default: source/)")
    ap.add_argument("--section-map", help="a map from section_map.py derive; needs a directory new side")
    ap.add_argument("--article", type=int,
                    help="report one Article (every changed file is still classified)")
    ap.add_argument("--json", help="also write the determination as JSON to this path")
    a = ap.parse_args(argv)
    try:
        old = Side(ref=a.old)
        if a.new_ref:
            if a.section_map:
                raise Refusal("--section-map needs a directory new side (--new-dir): "
                              "a section map is checked against a tree")
            new = Side(ref=a.new_ref)
        else:
            new = Side(root=Path(a.new_dir) if a.new_dir else SOURCE)
        smap = None
        if a.section_map:
            import section_map
            problems = section_map.selfcheck(a.section_map, a.old, new.root)
            if problems:
                raise Refusal("the section map failed its self-check: " + "; ".join(problems))
            smap = section_map.load(a.section_map)
        result = determine(old, new, smap=smap)
    except Refusal as exc:
        print(f"czc_diff: refusing -- {exc}", file=sys.stderr)
        return 1

    shown = [c for n, c in sorted(result.items()) if a.article in (None, n)]
    print(f"Substantive-change determination: {old.label} -> {new.label}")
    print(f"  {'Article':>7} {'prose':>6} {'heading':>8} {'table':>6} {'data':>6} "
          f"{'suppressed':>11}  verdict")
    for c in shown:
        print(f"  {c.article:>7} {c.prose:>6} {c.heading:>8} {c.table:>6} {c.data:>6} "
              f"{c.suppressed:>11}  {c.verdict}{' (new)' if c.new else ''}")
    calls = [(c.article, note) for c in shown for note in c.needs_call]
    if calls:
        print("\nNeeds a person's call:")
        for art, note in calls:
            print(f"  Article {art}: {note}")
    if a.json:
        Path(a.json).write_text(json.dumps(
            {"old": old.label, "new": new.label,
             "articles": {str(c.article): c.as_json() for c in shown}},
            indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Note on the table rows: `test_the_live_tree_runs_and_ignores_git_ignored_junk` identifies rows by a first token that is all digits. The header row's first token is `Article`, and the needs-call lines start with `Article`, so only the nine count rows qualify. Keep that shape.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_czc_diff.py -v`
Expected: all pass. If `test_two_real_tags` reports Article 3 `prose` other than 2 or `data` other than 10, STOP and report the numbers and the changed lines — do not adjust the assertion.

- [ ] **Step 5: Prove the untouched files and run the full suite**

```bash
git diff --stat main -- build/adoption_breakdown.py build/build-adoption.sh build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py build/section_map.py build/redline_resolve.py build/redline-text.py build/redline-stage.sh source/
python3 build/czc_diff.py --old v0.24-draft --new-ref v1.0
python3 -m pytest build/tests -q
```
Expected: the `git diff` prints nothing; the CLI prints nine rows with Articles 2 and 3 SUBSTANTIVE and the rest UNCHANGED, followed by the needs-call notes for the three layout units; the suite reports about 333 passed. Paste the CLI output into your report.

- [ ] **Step 6: Commit**

```bash
git add build/czc_diff.py build/tests/test_czc_diff.py
git commit -m "$(cat <<'EOF'
czc_diff: the per-Article determination, refusing rather than guessing

Every changed file between two versions -- tags or a directory -- is classified
through the ownership map before anything is counted. Prose files get the three
markdown counts; json-keyed data gets the keyed comparator; layout units, binary
exhibits and a generated figure that changed without its source get a
"needs a person's call" note, because a machine cannot tell a legend change
from a layout change. Each Article gets a proposed verdict: SUBSTANTIVE,
NEEDS-CALL, RENUMBER-ONLY or UNCHANGED.

It refuses, naming the file, when a changed file is unclaimed or claimed twice,
or listed as shared (ruled by Ben Frey, 2026-10-09), and on a bad ref, broken
JSON or a key that is not unique. Unwiring Article 2's data no longer reports
zero: the file becomes unclaimed and the determination stops.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: The use-table legend reader

**Files:**
- Create: `build/use_table_changes.py`
- Create: `build/tests/test_use_table_changes.py`

**Interfaces:**
- Consumes: `czc_diff.Refusal`.
- Produces:
  - `use_table_changes.LegendError(czc_diff.Refusal)`
  - `use_table_changes.parse_legend(typ_text: str) -> dict` — `{"glyphs": {code: glyph}, "rows": {code: (label, authority)}, "note": str}`.
  - `use_table_changes.legend_delta(old: dict, new: dict) -> list[str]` — plain sentences, empty when nothing changed.
  - `use_table_changes.status_words(code: str, legend: dict) -> str`

- [ ] **Step 1: Write the failing tests**

Create `build/tests/test_use_table_changes.py`:

```python
"""build/use_table_changes.py -- the Use Table Changes document.

Article 2's thirteen district pages are rendered from data; the redline shows
them unmarked. This document is the only place their changes are listed item
by item. Counts come from real tags or from trees materialised from v1.0.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import use_table_changes as utc  # noqa: E402

REPO = BUILD.parent
TYP = "article-02.typ"


def _typ(ref: str = "v1.0") -> str:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:source/{TYP}"],
                          capture_output=True, text=True, check=True).stdout


def test_the_legend_is_read():
    leg = utc.parse_legend(_typ())
    assert leg["rows"] == {
        "u": ("Use Permit Required", "CEO"),
        "rc": ("Residential Companion Permit Required", "CEO"),
        "sp": ("Special Permit Required", "Planning Board"),
        "ex": ("Expanded Use Permit Required", "Planning Board"),
    }
    assert leg["glyphs"] == {"u": "●", "rc": "❶", "sp": "❷", "ex": "✪"}
    assert leg["note"] == "Note: Uses without u, rc, sp, or ex are not allowed in this District"


def test_this_reader_agrees_with_the_permit_review_apps():
    """Two readers of one legend block (ruling 12). This test is the only thing
    that keeps them together: never skip or xfail it."""
    sys.path.insert(0, str(REPO / "build" / "permit-review"))
    from ruleset_build.legend import parse_legend as app_parse_legend
    text = _typ()
    ours, app = utc.parse_legend(text), app_parse_legend(text)
    app_rows = {r["code"]: r for r in app if r["code"]}
    assert set(ours["rows"]) == set(app_rows) == {"u", "rc", "sp", "ex"}
    for code, (label, authority) in ours["rows"].items():
        assert label == app_rows[code]["permit"] + " Required"
        assert authority == app_rows[code]["authority"]
        assert ours["glyphs"][code] == app_rows[code]["glyph"]
    app_note = next(r["note"] for r in app if not r["code"])
    assert ours["note"].removeprefix("Note: ").rstrip(".") == app_note.rstrip(".")


def test_an_unchanged_legend_has_no_delta_and_a_changed_one_does():
    old = utc.parse_legend(_typ())
    assert utc.legend_delta(old, utc.parse_legend(_typ())) == []
    new = utc.parse_legend(_typ().replace("[Special Permit Required], [Planning Board]",
                                          "[Special Exception Required], [Board of Appeals]", 1))
    delta = utc.legend_delta(old, new)
    assert any("Special Exception Required" in s for s in delta)
    assert any("Board of Appeals" in s for s in delta)


def test_a_missing_legend_is_refused():
    with pytest.raises(utc.LegendError):
        utc.parse_legend("#let x = 1\n")


def test_status_words():
    leg = utc.parse_legend(_typ())
    assert utc.status_words("", leg) == "Not allowed"
    assert utc.status_words("rc sp", leg) == \
        "Residential Companion Permit (CEO) + Special Permit (Planning Board)"
    assert utc.status_words("zz", leg) == "`zz` (not in the legend)"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_use_table_changes.py -v`
Expected: collection ERROR, `ModuleNotFoundError: No module named 'use_table_changes'`.

- [ ] **Step 3: Write the legend reader**

Create `build/use_table_changes.py`:

```python
#!/usr/bin/env python3
"""The Use Table Changes document: what changed in Article 2's district
standards and use tables between two versions of the Code.

WHY. Article 2's thirteen district pages are rendered from
source/article-02-data.json by a layout unit, and no redline can mark them:
they appear at their current state, without marks. Until now the only account
of what moved in them was a sentence in the Summary -- which is how a single
changed use cell reached an adopted Code with no reader able to catch it.

WHAT IT REPORTS, in this order:
  1. The use-table legend, FIRST: a changed meaning for an existing status
     code changes every cell that carries it, with no cell diff at all. The
     legend lives in article-02.typ, not in the data.
  2. Changed uses, per district: Use (category): before -> after. A blank
     status is printed "Not allowed", never left blank.
  3. Uses and districts added or removed -- events distinct from a change.
  4. Permitted Buildings matrix changes, by district, row and column.
  5. District standards changes: the description, purpose, dimension,
     placement and design panels, and the district's use standards.
  6. A total that equals the change determination's Article 2 data count
     (czc_diff.py): both come from the same keyed comparator.

The comparator is czc_diff's, imported -- there is one. The legend is read by
a small extractor here rather than by importing the permit-review app's: the
build produces the legal instrument and the app consumes it, so a packet build
must not fail because an app assertion drifted. An agreement test keeps the
two readers together.

Statuses are given in words. The use-table glyphs come from fonts that are not
in style/fonts, so a rendered memo would show them as missing characters.

Exit 0 written; 2 nothing to report (nothing written); 1 refused.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD))

import czc_diff  # noqa: E402

_GLYPHS = re.compile(r"#let\s+glyphs\s*=\s*\(([^)]*)\)")
_GLYPH_ENTRY = re.compile(r'(\w+)\s*:\s*"([^"]*)"')
_ROW = re.compile(r'status\(\s*"(\w+)"\s*\)\s*,\s*\[([^\]]+)\]\s*,\s*\[([^\]]+)\]\s*,')
_NOTE = re.compile(r"Note:\s*Uses without[^\]]*not allowed in this District")
_STATUS_CALL = re.compile(r'#?status\(\s*"(\w+)"\s*\)')


class LegendError(czc_diff.Refusal):
    """The USE TABLE LEGEND block could not be found or read."""


def parse_legend(typ_text: str) -> dict:
    """{"glyphs": {code: glyph}, "rows": {code: (label, authority)}, "note": str}.

    Rows are read only between the USE TABLE LEGEND heading and the legend's
    Note, so a status() call anywhere else in the file is never mistaken for one.
    """
    glyphs = _GLYPHS.search(typ_text)
    head = typ_text.find("USE TABLE LEGEND")
    if glyphs is None or head < 0:
        raise LegendError("article-02.typ: the USE TABLE LEGEND block or the glyph map was not found")
    note = _NOTE.search(typ_text, head)
    if note is None:
        raise LegendError("article-02.typ: the legend's 'Note: Uses without ...' sentence was not found")
    rows = {m.group(1): (m.group(2).strip(), m.group(3).strip())
            for m in _ROW.finditer(typ_text, head, note.start())}
    if not rows:
        raise LegendError("article-02.typ: no legend rows were found under USE TABLE LEGEND")
    return {"glyphs": dict(_GLYPH_ENTRY.findall(glyphs.group(1))),
            "rows": rows,
            "note": _STATUS_CALL.sub(lambda m: m.group(1), note.group(0))}


def legend_delta(old: dict, new: dict) -> list[str]:
    """What changed in the legend, as plain sentences. Empty means nothing."""
    out = []
    for code in sorted(set(old["rows"]) | set(new["rows"])):
        o, n = old["rows"].get(code), new["rows"].get(code)
        if o is None:
            out.append(f"Status code `{code}` added: {n[0]} ({n[1]}).")
        elif n is None:
            out.append(f"Status code `{code}` removed (it read {o[0]}, {o[1]}).")
        else:
            if o[0] != n[0]:
                out.append(f"Status code `{code}` now reads \"{n[0]}\" (it read \"{o[0]}\").")
            if o[1] != n[1]:
                out.append(f"Status code `{code}` is now issued by {n[1]} (it was {o[1]}).")
    for code in sorted(set(old["glyphs"]) | set(new["glyphs"])):
        og, ng = old["glyphs"].get(code), new["glyphs"].get(code)
        if og != ng:
            out.append(f"The symbol for `{code}` changed: {og or 'none'} → {ng or 'none'}.")
    if old["note"] != new["note"]:
        out.append(f"The legend's note now reads \"{new['note']}\" (it read \"{old['note']}\").")
    return out


def status_words(code: str, legend: dict) -> str:
    """A status code in words. A blank status is "Not allowed": 450 of the 819
    cells carry it, and a blank in a report reads as "nothing here"."""
    if not code.strip():
        return "Not allowed"
    parts = []
    for c in code.split():
        row = legend["rows"].get(c)
        parts.append(f"{row[0].removesuffix(' Required')} ({row[1]})" if row
                     else f"`{c}` (not in the legend)")
    return " + ".join(parts)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_use_table_changes.py -v`
Expected: 5 passed. The agreement test must PASS, not skip; if the permit-review import fails, STOP and report the error.

- [ ] **Step 5: Prove the untouched files and run the full suite**

```bash
git diff --stat main -- build/adoption_breakdown.py build/build-adoption.sh build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py build/section_map.py build/redline_resolve.py build/redline-text.py build/redline-stage.sh source/ build/permit-review/
python3 -m pytest build/tests -q
```
Expected: the `git diff` prints nothing (the app is read, never edited); the suite reports about 338 passed.

- [ ] **Step 6: Commit**

```bash
git add build/use_table_changes.py build/tests/test_use_table_changes.py
git commit -m "$(cat <<'EOF'
build: read the use-table legend, for the Use Table Changes document

A changed meaning for an existing status code moves every cell that carries it
with no cell diff at all, and the legend lives in article-02.typ, not in the
data. This reads it -- codes, wording, issuing authority, symbol and the
"not allowed" note -- and says what changed between two versions in plain
sentences. Statuses are given in words; a blank is "Not allowed".

It is a small extractor of its own rather than an import from the permit-review
app, so a packet build cannot fail because an app assertion drifted. An
agreement test keeps the two readers together.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: The Use Table Changes document

**Files:**
- Modify: `build/use_table_changes.py`
- Modify: `build/tests/test_use_table_changes.py`

**Interfaces:**
- Consumes: Task 4; `czc_diff.Side`, `czc_diff.keyed_records`, `czc_diff.json_leaves`, `czc_diff.diff_maps`, `czc_diff.Delta`, `czc_diff.determine`, `czc_diff.Refusal`, `czc_diff.SOURCE`; `manifest.load()`; `build/build-memo.sh <md> <pdf> [running-head] [foot-note]` (unchanged consumer).
- Produces:
  - `use_table_changes.build(old: czc_diff.Side, new: czc_diff.Side, *, doc: dict | None = None) -> dict`
  - `use_table_changes.render(report: dict) -> str | None` — `None` when there is nothing to report.
  - `use_table_changes.summary(report: dict) -> dict` — `{"changed", "added", "removed", "total", "legend", "districts"}`.
  - CLI: `python3 build/use_table_changes.py <old-ref> <out.md> [--new-ref REF | --new-dir DIR] [--json PATH]` — exit 0 written, 2 nothing to report and nothing written, 1 refused.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_use_table_changes.py`:

```python
# --- The document ------------------------------------------------------------------

import czc_diff  # noqa: E402
import section_fixtures as fx  # noqa: E402

CLI = [sys.executable, str(BUILD / "use_table_changes.py")]
A2 = "article-02-data.json"


@pytest.fixture(scope="module")
def base_tree(tmp_path_factory):
    return fx.copy_full_source(tmp_path_factory.mktemp("v1") / "source")


@pytest.fixture
def tree(tmp_path, base_tree):
    return Path(shutil.copytree(base_tree, tmp_path / "source"))


def _edit(tree, fn):
    p = tree / A2
    data = json.loads(p.read_text())
    fn(data)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _record(data, code, name):
    return next(r for r in data if (r["code"], r["name"]) == (code, name))


def _section(md: str, n: int) -> str:
    """The text of section `## n.` up to the next `## `."""
    start = md.index(f"## {n}. ")
    nxt = md.find("\n## ", start + 1)
    return md[start:nxt if nxt != -1 else len(md)]


def _run(*args):
    return subprocess.run([*CLI, *args], capture_output=True, text=True, cwd=REPO)


def test_v0_24_to_v1_0_reports_the_one_cell_and_the_standards(tmp_path):
    """The calibrated positive control (ruling 10). The D3 cell is the only
    changed use; the eleven districts' standards changes are reported in their
    own section; the total equals the determination's Article 2 data count."""
    out = tmp_path / "u.md"
    r = _run("v0.24-draft", str(out), "--new-ref", "v1.0", "--json", str(tmp_path / "u.json"))
    assert r.returncode == 0, r.stderr
    md = out.read_text()
    uses = _section(md, 2)
    assert [ln for ln in uses.splitlines() if ln.startswith("- ")] == [
        "- **Retail & Service, General** (COMMERCIAL GOODS): Residential Companion Permit (CEO) "
        "→ Residential Companion Permit (CEO) + Special Permit (Planning Board)"]
    assert "No use was added or removed" in _section(md, 3)
    standards = _section(md, 5)
    for district in ("D2 NEIGHBORHOOD RESIDENTIAL", "SD MARINE", "SD FABRICATION"):
        assert district in standards
    assert "No change to the legend" in _section(md, 1)
    total = json.loads((tmp_path / "u.json").read_text())["total"]
    det = czc_diff.determine(czc_diff.Side(ref="v0.24-draft"), czc_diff.Side(ref="v1.0"))
    assert total == det[2].data > 1


def test_nothing_to_report_exits_2_and_writes_nothing(tmp_path):
    out = tmp_path / "u.md"
    r = _run("v1.0", str(out), "--new-ref", "v1.0")
    assert r.returncode == 2 and not out.exists()


def test_the_three_districts_without_a_matrix_are_named(tmp_path):
    out = tmp_path / "u.md"
    assert _run("v0.24-draft", str(out), "--new-ref", "v1.0").returncode == 0
    assert ("No Permitted Buildings matrix: SD CONSERVATION, SD CAMPUS, SD MARINE"
            in _section(out.read_text(), 4))


def test_a_legend_wording_change_alone_is_reported(tree, tmp_path):
    """The spec's negative control: all 819 cells untouched, only the legend's
    words changed. A cell-diff-only document reports nothing."""
    p = tree / TYP
    p.write_text(p.read_text().replace("[Special Permit Required]",
                                       "[Special Exception Required]", 1))
    out = tmp_path / "u.md"
    r = _run("v1.0", str(out), "--new-dir", str(tree), "--json", str(tmp_path / "u.json"))
    assert r.returncode == 0, r.stderr
    assert "Special Exception Required" in _section(out.read_text(), 1)
    assert json.loads((tmp_path / "u.json").read_text())["total"] == 0
    det = czc_diff.determine(czc_diff.Side(ref="v1.0"), czc_diff.Side(root=tree))
    assert det[2].verdict == "NEEDS-CALL"                            # and the determination flags it


def test_a_blank_status_is_written_not_allowed(tree, tmp_path):
    def change(d):
        rec = _record(d, "D1", "RURAL")
        entry = next(e for c in rec["use_col1"] + rec["use_col2"] for e in c["entries"]
                     if e[1] == "")
        entry[1] = "u"
    _edit(tree, change)
    out = tmp_path / "u.md"
    assert _run("v1.0", str(out), "--new-dir", str(tree)).returncode == 0
    assert "Not allowed → Use Permit (CEO)" in _section(out.read_text(), 2)


def test_the_soft_hyphen_category_prints_whole(tree, tmp_path):
    """D4's TRANSPORTATION & UTILITIES is split in the data at a soft hyphen;
    its cells sit under a category titled 'ITIES'. Print the word whole."""
    def change(d):
        cat = next(c for c in _record(d, "D4", "VILLAGE RESIDENTIAL")["use_col1"]
                   if c["title"] == "ITIES")
        cat["entries"][0][1] = "ex" if cat["entries"][0][1] != "ex" else "u"
    _edit(tree, change)
    out = tmp_path / "u.md"
    assert _run("v1.0", str(out), "--new-dir", str(tree)).returncode == 0
    uses = _section(out.read_text(), 2)
    assert "(TRANSPORTATION & UTILITIES)" in uses and "(ITIES)" not in uses


def test_an_added_use_is_an_event_distinct_from_a_change(tree, tmp_path):
    def change(d):
        cat = next(c for c in _record(d, "D1", "RURAL")["use_col1"] if c["title"] == "RECREATION")
        cat["entries"].append(["Farm Stand", "u"])
    _edit(tree, change)
    out = tmp_path / "u.md"
    assert _run("v1.0", str(out), "--new-dir", str(tree)).returncode == 0
    md = out.read_text()
    assert "Farm Stand" in _section(md, 3) and "Farm Stand" not in _section(md, 2)


def test_a_matrix_change_names_its_row_and_column(tree, tmp_path):
    def change(d):
        m = _record(d, "D3", "NEIGHBORHOOD BUSINESS")["matrix"]
        row = next(r for r in m["rows"] if r[0] == "Building Width")
        row[1] = "60 ft"
    _edit(tree, change)
    out = tmp_path / "u.md"
    assert _run("v1.0", str(out), "--new-dir", str(tree)).returncode == 0
    matrix = _section(out.read_text(), 4)
    assert "Building Width" in matrix and "Residential" in matrix and "60 ft" in matrix


def test_the_document_renders_through_the_memo_builder(tmp_path):
    """The document is a memo, not an Article: build-memo.sh renders it."""
    import pymupdf
    md, pdf = tmp_path / "u.md", tmp_path / "u.pdf"
    assert _run("v0.24-draft", str(md), "--new-ref", "v1.0").returncode == 0
    r = subprocess.run(["bash", str(BUILD / "build-memo.sh"), str(md), str(pdf),
                        "Use Table Changes", "Newcastle Core Zoning Code"],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    text = "".join(page.get_text() for page in pymupdf.open(pdf))
    assert "Retail & Service, General" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_use_table_changes.py -v`
Expected: the nine new tests FAIL (the module has no CLI yet: `python3 build/use_table_changes.py` exits without output and nonzero, or `build` is missing); Task 4's five tests PASS.

- [ ] **Step 3: Add the document**

In `build/use_table_changes.py`, add `import argparse` and `import json` to the imports and `import manifest  # noqa: E402` beside `import czc_diff`, then append:

```python
# --- The document --------------------------------------------------------------

DATA = "article-02-data.json"
TYP = "article-02.typ"
USE_COLS = ("use_col1", "use_col2")
STANDARD_FIELDS = {"left": "District description and dimensions",
                   "right": "Building standards",
                   "use_standards": "Use standards"}


def build(old: czc_diff.Side, new: czc_diff.Side, *, doc: dict | None = None) -> dict:
    """Everything the document reports, before it is written down."""
    doc = manifest.load() if doc is None else doc
    decl = next((d for d in doc["2"].get("data_sources", []) if d.get("path") == DATA), None)
    if decl is None or decl.get("compare") != "json-keyed":
        raise czc_diff.Refusal(f"{DATA} is not declared json-keyed under Article 2 "
                               f"in build/article-manifest.json")
    raw_old, raw_new = old.read(DATA), new.read(DATA)
    typ_old, typ_new = old.read(TYP), new.read(TYP)
    if None in (raw_old, raw_new, typ_old, typ_new):
        raise czc_diff.Refusal(f"{DATA} or {TYP} is missing from {old.label} or {new.label}")
    leg_old, leg_new = parse_legend(typ_old.decode()), parse_legend(typ_new.decode())
    return {
        "old": old.label, "new": new.label,
        "delta": czc_diff.diff_maps(czc_diff.json_leaves(raw_old, decl),
                                    czc_diff.json_leaves(raw_new, decl)),
        "legend": legend_delta(leg_old, leg_new),
        "leg_old": leg_old, "leg_new": leg_new,
        "rec_old": czc_diff.keyed_records(json.loads(raw_old), decl["key"]),
        "rec_new": czc_diff.keyed_records(json.loads(raw_new), decl["key"]),
    }


def _district(key: str) -> str:
    return key.replace(" / ", " ")


def _value(v) -> str:
    if v is None:
        return "(none)"
    if isinstance(v, str):
        return f"“{v}”" if v else "(blank)"
    if v == [] or v == {}:
        return "(empty)"
    return json.dumps(v, ensure_ascii=False)


def _category(record: dict | None, col: str, title: str) -> str:
    """A use category's printed name. The extracted data splits D4's
    TRANSPORTATION & UTILITIES at a soft hyphen into an empty
    'TRANSPORTATION & UTIL\\xad' and an 'ITIES' that carries the cells."""
    titles = [c.get("title") for c in ((record or {}).get(col) or [])]
    if title in titles:
        i = titles.index(title)
        if i > 0 and isinstance(titles[i - 1], str) and titles[i - 1].endswith("\xad"):
            return titles[i - 1].rstrip("\xad") + title
    return title.rstrip("\xad")


def _matrix_column(record: dict | None, index_key: str) -> str:
    cols = ((record or {}).get("matrix") or {}).get("cols") or []
    m = re.fullmatch(r"\[(\d+)\]", index_key)
    if m and int(m.group(1)) < len(cols):
        return cols[int(m.group(1))]
    return index_key


def summary(report: dict) -> dict:
    d = report["delta"]
    per: dict[str, int] = {}
    for path in [*d.changed, *d.added, *d.removed]:
        per[_district(path[0])] = per.get(_district(path[0]), 0) + 1
    return {"changed": len(d.changed), "added": len(d.added), "removed": len(d.removed),
            "total": d.count(), "legend": report["legend"], "districts": per}


def render(report: dict) -> str | None:
    """The document as markdown, or None when there is nothing to report."""
    d, legend = report["delta"], report["legend"]
    if not d.count() and not legend:
        return None
    ro, rn, lo, ln = report["rec_old"], report["rec_new"], report["leg_old"], report["leg_new"]
    whole_added = [k for k in rn if k not in ro]
    whole_removed = [k for k in ro if k not in rn]
    whole = set(whole_added) | set(whole_removed)

    events = [("changed", p, v) for p, v in d.changed.items()] \
        + [("added", p, v) for p, v in d.added.items()] \
        + [("removed", p, v) for p, v in d.removed.items()]
    uses, matrices, standards = [], [], []
    for kind, path, val in events:
        if path[0] in whole:
            continue
        if path[1] in USE_COLS:
            uses.append((kind, path, val))
        elif path[1] == "matrix":
            matrices.append((kind, path, val))
        else:
            standards.append((kind, path, val))

    def by_district(items):
        grouped: dict[str, list] = {}
        for item in items:
            grouped.setdefault(item[1][0], []).append(item)
        return grouped

    out = ["# Use Table Changes", "",
           f"**Article 2 — district standards and use tables: {report['old']} → {report['new']}**", "",
           "Every change to the district data that Article 2's thirteen district pages are printed "
           "from. The redline shows those pages at their current state, without marks, so this is "
           "the only place their changes are listed item by item.", ""]

    out += ["## 1. Use table legend", ""]
    out += [f"- {s}" for s in legend] if legend else \
        ["No change to the legend: every status code means what it meant before."]
    out.append("")

    out += ["## 2. Changed uses", ""]
    changed_uses = [u for u in uses if u[0] == "changed" and len(u[1]) == 5 and u[1][3] == "entries"]
    if not changed_uses:
        out += ["No use changed its status.", ""]
    for key, items in by_district(changed_uses).items():
        out += [f"### {_district(key)} — {len(items)} change{'s' if len(items) != 1 else ''}", ""]
        for _, path, (o, n) in items:
            cat = _category(rn.get(key), path[1], path[2])
            out.append(f"- **{path[4]}** ({cat}): {status_words(o, lo)} → {status_words(n, ln)}")
        out.append("")

    out += ["## 3. Uses and districts added or removed", ""]
    lines = [f"- District added: **{_district(k)}**." for k in whole_added]
    lines += [f"- District removed: **{_district(k)}**." for k in whole_removed]
    for kind, path, val in uses:
        if kind == "changed" and len(path) == 5 and path[3] == "entries":
            continue
        if len(path) == 5 and path[3] == "entries":
            rec, leg = (rn, ln) if kind == "added" else (ro, lo)
            cat = _category(rec.get(path[0]), path[1], path[2])
            lines.append(f"- {_district(path[0])}: use **{path[4]}** ({cat}) {kind} — "
                         f"{status_words(val, leg)}.")
        else:
            lines.append(f"- {_district(path[0])}: {' › '.join(path[1:])} {kind}"
                         f"{'' if kind == 'removed' else ': ' + _value(val[1] if kind == 'changed' else val)}.")
    out += lines if lines else ["No use was added or removed, and no district was added or removed."]
    out.append("")

    out += ["## 4. Permitted Buildings matrix", ""]
    if not matrices:
        out.append("No change to any Permitted Buildings matrix.")
    for key, items in by_district(matrices).items():
        out += ["", f"### {_district(key)}", ""]
        for kind, path, val in items:
            rec = rn.get(key) if kind != "removed" else ro.get(key)
            if len(path) == 5 and path[2] == "rows":
                where = f"{path[3]} › {_matrix_column(rec, path[4])}"
            else:
                where = " › ".join(path[2:]) or "the matrix"
            if kind == "changed":
                out.append(f"- {where}: {_value(val[0])} → {_value(val[1])}")
            else:
                out.append(f"- {where} {kind}: {_value(val)}")
    no_matrix = [_district(k) for k, r in rn.items() if isinstance(r, dict) and r.get("matrix") is None]
    out += ["", f"No Permitted Buildings matrix: {', '.join(no_matrix)}." if no_matrix else
            "Every district has a Permitted Buildings matrix.", ""]

    out += ["## 5. District standards", ""]
    if not standards:
        out += ["No change to any district's standards.", ""]
    for key, items in by_district(standards).items():
        out += [f"### {_district(key)}", ""]
        for kind, path, val in items:
            where = " › ".join([STANDARD_FIELDS.get(path[1], path[1]), *path[2:]])
            if kind == "changed":
                out.append(f"- {where}: {_value(val[0])} → {_value(val[1])}")
            else:
                out.append(f"- {where} {kind}: {_value(val)}")
        out.append("")

    s = summary(report)
    out += ["## 6. Total", "",
            f"{s['total']} item{'s' if s['total'] != 1 else ''} of district data changed "
            f"({s['changed']} changed, {s['added']} added, {s['removed']} removed). "
            f"This is the figure the change determination reports for Article 2's district data.",
            ""]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Write the Use Table Changes document for Article 2.")
    ap.add_argument("old_ref", help="the old version: a git ref")
    ap.add_argument("out", help="where to write the markdown")
    side = ap.add_mutually_exclusive_group()
    side.add_argument("--new-ref", help="the new version as a git ref")
    side.add_argument("--new-dir", help="the new version as a source directory (default: source/)")
    ap.add_argument("--json", help="also write the counts as JSON to this path")
    a = ap.parse_args(argv)
    try:
        old = czc_diff.Side(ref=a.old_ref)
        new = (czc_diff.Side(ref=a.new_ref) if a.new_ref
               else czc_diff.Side(root=Path(a.new_dir) if a.new_dir else czc_diff.SOURCE))
        report = build(old, new)
    except czc_diff.Refusal as exc:
        print(f"use_table_changes: refusing -- {exc}", file=sys.stderr)
        return 1
    text = render(report)
    if text is None:
        print(f"use_table_changes: nothing changed in Article 2's district data or legend "
              f"({report['old']} -> {report['new']}); nothing written.")
        return 2
    Path(a.out).write_text(text)
    if a.json:
        Path(a.json).write_text(json.dumps(summary(report), indent=2, ensure_ascii=False) + "\n")
    s = summary(report)
    print(f"use_table_changes: {s['total']} change(s) to Article 2's district data"
          f"{', and a legend change' if report['legend'] else ''} -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_use_table_changes.py -v`
Expected: 14 passed. If `test_v0_24_to_v1_0_reports_the_one_cell_and_the_standards` finds a legend change between v0.24-draft and v1.0, STOP and report the delta — do not loosen the assertion.

- [ ] **Step 5: Read the document once, as a person would**

```bash
python3 build/use_table_changes.py v0.24-draft /private/tmp/claude-501/use-table-changes.md --new-ref v1.0
```
Open the file. Put its first 40 lines in your report, and say in one sentence whether anything in it would confuse a Planning Board member who has never seen the data file (a raw path, an index like `[2]`, a JSON fragment). Do not change the code for this step; report it.

- [ ] **Step 6: Prove the untouched files and run the full suite**

```bash
git diff --stat main -- build/adoption_breakdown.py build/build-adoption.sh build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py build/section_map.py build/redline_resolve.py build/redline-text.py build/redline-stage.sh source/ build/permit-review/ build/build-memo.sh
python3 -m pytest build/tests -q
```
Expected: the `git diff` prints nothing; the suite reports about 347 passed.

- [ ] **Step 7: Commit**

```bash
git add build/use_table_changes.py build/tests/test_use_table_changes.py
git commit -m "$(cat <<'EOF'
build: the Use Table Changes document for Article 2

Article 2's district pages are printed from data and shown unmarked in the
redline, so until now a changed use cell was described only in the Summary.
This writes every change to that data, in a fixed order: the legend first --
because a changed meaning moves every cell with no cell diff -- then changed
uses per district, added and removed uses and districts, Permitted Buildings
matrix changes by row and column, district standards changes, and a total that
equals the change determination's Article 2 data count, because both use the
same comparator.

Statuses are in words ("Not allowed" for a blank), D4's soft-hyphen category
prints whole, the three districts without a matrix are named, and it exits 2,
writing nothing, when there is nothing to report. It renders through the
existing memo builder.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Done when

- `czc_diff.py --old v0.24-draft --new-ref v1.0` reports Article 2 SUBSTANTIVE with the one D3 cell among its data changes, Article 3 SUBSTANTIVE with the ten re-typed segments and its one prose change, the three layout units as needing a person's call, and every other Article UNCHANGED; and `v1.0` against itself reports all nine UNCHANGED.
- It refuses, naming the file, for an unclaimed, doubly claimed or shared changed file, a non-unique key, broken JSON or a bad ref.
- `use_table_changes.py v0.24-draft <out> --new-ref v1.0` writes the document with the D3 cell as the only changed use, the eleven districts' standards changes, the three districts without a matrix named, and a total equal to the determination's Article 2 data count; against itself it exits 2 and writes nothing; and it renders through `build-memo.sh`.
- The legend reader agrees with the permit-review app's, by a test that runs in CI.
- Every file listed as untouched is byte-identical to `main`, and `normalize_for_diff.py` differs only by the `marked_lines` alias.
- The full suite passes; CI is green on the PR.

## Not in this plan

- **The verdict override and `ships.json`** (an operator's recorded call on a NEEDS-CALL Article, refusing an empty reason) — P13.
- **Re-expressing `adoption_breakdown.py` as a thin caller over `czc_diff`** — later, per the spec; it is left intact here.
- **Wave 3b** — the per-Article structural note (P8), the honest standalone markdown with the Article 2 appendix (P12), and the standalone redline (P14). The appendix will reuse this wave's renderer pieces rather than write a third.
- **`build/ADOPTION-SPEC.md` §3.3** — P18.
