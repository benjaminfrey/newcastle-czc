# Wave 4a — The Release Driver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One command — `build/build-release.sh <version> [date] --old-ver=<ref>` — produces a draft release's whole deliverable set from the change determination, into a staging directory that becomes the release directory only after a gate proves every promised file exists and is well-formed.

**Architecture:** Four small Python tools and one shell driver. `release_plan.py` turns `czc_diff`'s verdicts, plus a person's written calls on the Articles a machine cannot decide, into `release-plan.json` — the list of artifacts this release must contain. `summary_skeleton.py` writes the Summary of Changes skeleton from that plan. `release_gate.py` refuses unless every planned file exists, is non-empty, every PDF's printed page numbers keep logical == physical, and nothing unplanned is present. `redline_md.py` assembles the integrated redline's markdown, which today is never produced. The driver derives and selfchecks the section map, now threaded through the redline staging and onto the disclosure page, runs the leaf builders into staging, runs the gate, and moves the result into place.

**Tech Stack:** bash, Python 3.14, PyMuPDF, pytest; the existing leaf builders.

**Spec:** `specs/2026-10-07-release-deliverables-scope.md` — §2 P13, §0 decisions D1, D5, D8, §6 (the owed items). Ben Frey's rulings of 2026-10-11: Wave 4 is split into 4a (this plan: the driver's core), 4b (the integrated `.md` through `czc_md`, the generated cover facts (D6), `build-adoption.sh` calling the driver, `pdf_recap` assertions, the spec + CLAUDE.md revisions (P18)) and 4c (the fifth status code, P15, after its four binding values are decided).

## Global Constraints

- **NEVER commit unless explicitly asked.** The operator authorises this plan's commit steps: implementers commit locally, by name, on branch `wave4-release-driver`. Nothing is pushed. **No `git stash`.**
- **NEVER `git add -A` or `git add .`** — stage files by name, exactly as each commit step lists them.
- **Never modify anything in `docs/`, `releases/` or `source/`.** Tests write only under `tmp_path`; no test builds into the real `releases/` dir.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` — **project standing rule 5**.
- Build tests: `python3 -m pytest build/tests -q` from the repository root. **522 tests** at the start of this wave, about 7 minutes; this wave adds end-to-end release builds (each about 40–60 s). CI runs the same suite on the PR (Linux, GNU coreutils, Typst 0.14.2). **Report the count you actually see.**
- **Untouched by this wave** (prove with `git diff --stat main -- <these>` printing nothing): `build/adoption-map.json`, `build/adoption_map.py`, `build/baseline_selfcheck.py`, `build/section_map.py`, `build/normalize_for_diff.py`, `build/redline_resolve.py`, `build/czc_diff.py`, `build/structural_note.py`, `build/use_table_changes.py`, `build/split-article-03.py`, `build/adoption-footer.sh`, `build/adoption-name.sh`, `build/build-full-czc.sh`, `build/build-standalone.sh`, `build/build-adoption.sh`, `build/build-adopted.sh`, `build/adopted_residue.py`, `build/version_state.py`, `build/permit-review/`.
- **Never pin the live working tree.** New-side trees come from `section_fixtures.copy_full_source(dest)` (the v1.0 tag). Test versions use `v0.98-draft`; the old ref is `v1.0`.
- **Measured facts** (2026-10-11, HEAD 809ebee; full detail in the Wave 4a facts sweep):
  - `czc_diff.py --old REF [--new-dir DIR] [--section-map P] --json PATH` exits **0 for every verdict, including NEEDS-CALL**, and 1 on a refusal; its JSON has top-level `old`, `new`, `articles` (keys "1".."9"), each `{prose, heading, table, data, suppressed, new, verdict, needs_call: [str], data_detail}`. Against `v1.0` today the working tree reads Articles 1, 2, 3 NEEDS-CALL (their layout units changed in the Wave 0/1 chrome fix), 4–9 UNCHANGED.
  - `section_map.py derive <old_ref> --new-dir DIR --out PATH` exits 0 (map written), 2 (below the similarity floor, nothing written), 1 (bad ref / nothing compared); `selfcheck PATH --old-ref REF --new-dir DIR` is the gate (0/1). The map's `articles` is `{"<old art>": {"<old §>": <new §>}}`.
  - `redline-stage.sh`'s `czc_redline_stage <src> <stage> <old> <baseline-flag> <plain-flag> [basename ...]` calls `redline_resolve.py "$base" "$old_ver" "$oldtmp" $baseline_flag` (line 101) and has **no way to pass `--section-map`**; `redline_resolve.py` already accepts `--section-map PATH --new-dir DIR` (and refuses one without the other). `structural_note.py --scope article:N` already accepts `--section-map`; **no script passes it.**
  - `build-redline-full.sh <new> [old] [date]` hard-codes `SRC="$REPO_ROOT/source"` (no `SRC_DIR`), writes `REDLINE_OUT` (a FILE path), and **produces no `.md`** — its child build's markdown is of the Typst-marked stage and is discarded with the tmpdir. `build-redline-standalone.sh <NN> <new> <old>` honours `SRC_DIR`, writes into `REDLINE_OUT` (a DIRECTORY), and produces both formats.
  - `use_table_changes.py <old_ref> <out.md> --new-dir DIR` exits 0 (written), **2 (nothing changed — normal)**, 1 (refused).
  - `build-full-czc.sh` honours `SRC_DIR` and `OUT_DIR`; ~14 s per integrated build. `build-standalone.sh` honours `SRC_DIR`, `OUT_DIR`. Names: `czc_integrated_name draft v0.98-draft` → `Newcastle CZC (Integrated Draft v0.98-draft)`; `czc_standalone_name draft 7 "Use Standards" v0.98-draft [redline]` → `Article 7 Use Standards (Standalone v0.98-draft)[ — Redline]`.
  - Printed footer numbers are read in the tests by `FOOTER_NUMBER = re.compile(r"Newcastle Core Zoning Code\s*\|\s*(\d+)|(\d+)\s*\|\s*Newcastle Core Zoning Code")` within the bottom 40 pt band (`test_structural_note.py`).
  - Each plain-marked Article file (`redline-text.py --source --plain`) is: frontmatter, then a paragraph starting `Redline key:`, then the body.

### Twelve rulings this plan makes in writing

1. **`--old-ver` is required**, never auto-detected (spec P13: `git describe` provably fails for an untagged draft).
2. **4a builds draft releases only.** The driver refuses `ADOPTION_MODE` other than `draft` and refuses a version `version_state.py --require draft` rejects. Meeting mode arrives in 4b through `build-adoption.sh`; adopted releases never ship standalones (D5).
3. **A person's call is a written record.** `--calls FILE` holds `{"calls": [{"article": N, "decision": "layout-only" | "substantive", "reason": "...", "by": "..."}]}`. Every NEEDS-CALL Article needs exactly one call; `reason` and `by` must be non-empty; `layout-only` is allowed only for a NEEDS-CALL Article; `substantive` may upgrade any verdict except SUBSTANTIVE (refused as redundant) — a call can make a release ship **more**, never less; unknown keys, duplicates and calls for Articles outside 1–9 are refused. The calls are copied into `release-plan.json`, which is committed with the release.
4. **Statuses.** SUBSTANTIVE (verdict, or a `substantive` call) ships a standalone and a standalone redline, each `.pdf` + `.md`; RENUMBER-ONLY is named in the Summary; NEEDS-CALL + `layout-only` becomes LAYOUT-ONLY and is named in the Summary with its reason; UNCHANGED.
5. **The Use Table Changes artifact is decided by running `use_table_changes.py` itself** during planning (0 → included, 2 → not, 1 → refuse) — one decider, so the plan and the artifact cannot disagree.
6. **The section map is derived fresh by the driver, selfchecked, used, and never shipped** (P6: never committed). The plan records only how many sections it renumbered.
7. **The section map reaches every redline consumer**: `czc_redline_stage` reads an optional `CZC_SECTION_MAP` environment variable and passes `--section-map … --new-dir <src>` to `redline_resolve.py`; `build-redline-full.sh` and `build-redline-standalone.sh` read `SECTION_MAP`, and the standalone passes it to `structural_note.py --section-map`.
8. **The integrated redline has a `.md`** (D1: the only redline that survives in git): one legend, then each Article's plain-marked text with headings `# Article N: Name`, its build comments and raw-Typst tables handled by `czc_md`'s own body walker (exposed as `czc_md.body_markdown`), never a second copy of that logic.
9. **The release directory appears only after the gate passes.** Everything is built into a sibling staging directory `<parent>/.staging-<version>.XXXXXX`; on any failure the staging directory is removed and the release directory is untouched. An existing release directory is refused unless it holds only `Summary of Changes <version>.md` (and its `.pdf`), which the driver keeps and never overwrites.
10. **The gate refuses; it does not report.** Every planned file exists and is non-empty; every PDF has at least one printed page number and `printed − physical` is the same on every numbered page (logical == physical, the parity invariant, which an uncounted front note or a missing page breaks); no file is present that the plan does not name (allowed extra: an existing `Summary of Changes <version>.pdf`).
11. **The leaf builders are looked up through test seams** `CZC_LEAF_FULL`, `CZC_LEAF_REDLINE_FULL`, `CZC_LEAF_STANDALONE`, `CZC_LEAF_REDLINE_STANDALONE` (default: the real scripts), so the negative control can stub one to exit 0 without writing — precedent: `ADOPTION_MAP`, a test seam only.
12. **The Summary skeleton is generated from the plan and never overwrites.** It names every non-UNCHANGED Article by status, says what the redline cannot show from the plan's own counts and units, and leaves the prose as marked placeholders. It contains none of the v0.1-baseline sentences `build-adoption.sh` hard-codes ("November 3, 2020", "March 24, 2025", "3-8 become 4-9").

## Review Focus

1. **A NEEDS-CALL Article with no call must stop the release**, naming the Article and why it needs a call. Pinned in Task 3.
2. **A leaf that exits 0 without writing its file must not produce a release.** Pinned in Task 6 (the negative control).
3. **A refused release must leave no release directory and no staging directory.** Pinned in Task 6.
4. **Renumbered sections must not appear as "Heading changed" notes when the map is supplied, and must when it is not.** Pinned in Task 1.
5. **The integrated redline `.md` must carry one legend, every Article in order, and no raw Typst or build comments.** Pinned in Task 2.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `build/redline-stage.sh` | Old-side staging | `CZC_SECTION_MAP` (Task 1) |
| `build/build-redline-full.sh` | Integrated redline | `SRC_DIR`, `SECTION_MAP` (Task 1); `REDLINE_MD_OUT` (Task 2) |
| `build/build-redline-standalone.sh` | Standalone redline | `SECTION_MAP` (Task 1) |
| `build/czc_md.py` | Honest markdown | public `body_markdown` (Task 2) |
| `build/redline_md.py` | **New.** Integrated redline markdown | Task 2 |
| `build/release_plan.py` | **New.** Verdicts + calls → plan | Task 3 |
| `build/summary_skeleton.py` | **New.** Plan → Summary skeleton | Task 4 |
| `build/release_gate.py` | **New.** The refusing gate | Task 5 |
| `build/build-release.sh` | **New.** The driver | Task 6 |
| `build/tests/test_redline_section_map.py`, `test_redline_md.py`, `test_release_plan.py`, `test_summary_skeleton.py`, `test_release_gate.py`, `test_build_release.py` | **New** | Tasks 1–6 |

---

## Task 1: The section map reaches the redline

**Files:** Modify `build/redline-stage.sh`, `build/build-redline-full.sh`, `build/build-redline-standalone.sh`. Create `build/tests/test_redline_section_map.py`.

**Interfaces — Produces:** env `CZC_SECTION_MAP` read by `czc_redline_stage`; env `SECTION_MAP` and `SRC_DIR` read by `build-redline-full.sh`; env `SECTION_MAP` read by `build-redline-standalone.sh`.

- [ ] **Step 1: Write the failing tests** — `build/tests/test_redline_section_map.py`:

```python
"""The derived section map reaches the redline: staging, text and page."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
BUILD = TESTS.parent
REPO = BUILD.parent
sys.path.insert(0, str(TESTS))
import section_fixtures as fx  # noqa: E402

VER = "v0.98-draft"
ART7 = "article-07-use-standards.md"


@pytest.fixture(scope="module")
def inserted(tmp_path_factory):
    """A v1.0 tree with one section inserted near the top of Article 7, and its map."""
    root = tmp_path_factory.mktemp("ins")
    tree = fx.copy_full_source(root / "source")
    p = tree / ART7
    p.write_text(fx.insert_section(p.read_text(), 2, "PROBE SECTION"))
    smap = root / "map.json"
    r = subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                        "--new-dir", str(tree), "--out", str(smap)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return tree, smap


def _standalone_md(tmp_path, tree, **env):
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-redline-standalone.sh", "07", VER, "v1.0"], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(tree), REDLINE_OUT=str(out), **env),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return next(out.glob("*.md")).read_text()


def test_without_the_map_renumbering_reads_as_heading_changes(tmp_path, inserted):
    """The control: this is the noise the map exists to remove."""
    tree, _ = inserted
    assert _standalone_md(tmp_path, tree).count("Heading changed") >= 3


def test_with_the_map_only_the_inserted_section_is_noted(tmp_path, inserted):
    tree, smap = inserted
    md = _standalone_md(tmp_path, tree, SECTION_MAP=str(smap))
    assert md.count("Heading changed") == 0
    assert md.count("Heading added") == 1
    assert "PROBE SECTION" in md


def test_a_map_for_another_tree_is_refused(tmp_path, inserted):
    _, smap = inserted
    other = fx.copy_full_source(tmp_path / "source")          # no inserted section
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-redline-standalone.sh", "07", VER, "v1.0"], cwd=REPO,
                       env=dict(os.environ, SRC_DIR=str(other), REDLINE_OUT=str(out),
                                SECTION_MAP=str(smap)), capture_output=True, text=True)
    assert r.returncode != 0 and not out.exists()


def test_a_missing_map_file_is_refused_by_the_stage(tmp_path):
    tree = fx.copy_full_source(tmp_path / "source")
    r = subprocess.run(["bash", "-c",
                        f'source build/redline-stage.sh; '
                        f'czc_redline_stage "{tree}" "{tmp_path}/stage" v1.0 "" "" {ART7}'],
                       cwd=REPO, env=dict(os.environ, CZC_SECTION_MAP=str(tmp_path / "nope.json")),
                       capture_output=True, text=True)
    assert r.returncode != 0


def test_the_integrated_redline_honours_src_dir_and_the_map(tmp_path, inserted):
    tree, smap = inserted
    pdf = tmp_path / "rl.pdf"
    r = subprocess.run(["bash", "build/build-redline-full.sh", VER, "v1.0", "January 1, 2027"],
                       cwd=REPO, env=dict(os.environ, SRC_DIR=str(tree), REDLINE_OUT=str(pdf),
                                          SECTION_MAP=str(smap)), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert pdf.exists()
    import fitz
    text = "".join(p.get_text() for p in fitz.open(pdf))
    assert "PROBE SECTION" in text                 # SRC_DIR was honoured, not source/
```

- [ ] **Step 2: Run them; expected:** the control passes or fails as measured, the others FAIL (no seam yet). **If the control shows fewer than 3 "Heading changed" notes, STOP and report the count and the notes** — the premise of the map's value is then wrong and needs a ruling.
- [ ] **Step 3: Implement.**
  - `redline-stage.sh`: document `CZC_SECTION_MAP` in the header. In `czc_redline_stage`, if `${CZC_SECTION_MAP:-}` is non-empty and not a readable file, print `redline-stage: section map not found: …` and `return 1`; if set, append `--section-map "$CZC_SECTION_MAP" --new-dir "$src"` to the `redline_resolve.py` call. Nothing else changes when it is unset.
  - `build-redline-full.sh`: `SRC="${SRC_DIR:-$REPO_ROOT/source}"`; `SECTION_MAP` exported to the stage as `CZC_SECTION_MAP` (only when set). Header documents both.
  - `build-redline-standalone.sh`: the same `SECTION_MAP` → `CZC_SECTION_MAP` for both stage calls, and `--section-map "$SECTION_MAP"` added to the `structural_note.py` call when set.
- [ ] **Step 4: Run** `python3 -m pytest build/tests/test_redline_section_map.py build/tests/test_redline_stage.py build/tests/test_redline_standalone.py -v` — all pass.
- [ ] **Step 5: Untouched-files diff (empty); full suite; commit** `build/redline-stage.sh build/build-redline-full.sh build/build-redline-standalone.sh build/tests/test_redline_section_map.py` with message:

```
redline: the derived section map reaches the staging, the text and the page

When a section is inserted, every later heading renumbers and the redline
reported each as "Heading changed". The derived map existed but nothing passed
it on. czc_redline_stage now reads CZC_SECTION_MAP and hands it to the old-side
resolver; both redline builders take SECTION_MAP, and the standalone passes it
to its disclosure page. The integrated redline also honours SRC_DIR now, like
the standalone. A missing map, or a map for another tree, refuses.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task 2: The integrated redline's markdown

**Files:** Modify `build/czc_md.py`, `build/build-redline-full.sh`. Create `build/redline_md.py`, `build/tests/test_redline_md.py`.

**Interfaces:**
- Produces `czc_md.body_markdown(nn: int, text: str, *, src_dir: Path, doc: dict | None = None) -> str` — the Article's body (frontmatter removed) through the same walker `render` uses (tables converted, comments dropped, split markers → pointer notes), followed by a pointer note for each after-prose unit (never an appendix). Raises `MdError` exactly where `render` would. `render`'s output is unchanged (the existing `test_czc_md.py` passes untouched).
- Produces CLI `python3 build/redline_md.py <plain-stage-dir> <out.md> --title TITLE` — exit 0 written, 1 refused (nothing written).
- Produces env `REDLINE_MD_OUT=<path>` on `build-redline-full.sh`.

- [ ] **Step 1: Write the failing tests** — `build/tests/test_redline_md.py`:
  - `test_one_legend_every_article_in_order`: build a plain stage of a v1.0 tree with a one-word change in Article 7 (`bash -c 'source build/redline-stage.sh; czc_redline_stage <tree> <stage> v1.0 "" --plain'`), run `redline_md.py <stage> out.md --title "T — Redline"`; assert the file starts `# T — Redline`, `count("Redline key:") == 1`, the nine headings `# Article 1:` … `# Article 9:` appear in order, `"{=typst}" not in md`, `"<!--" not in md`, `"TABLE 3.2 SIGHT DISTANCE\n\n| Design Speed (MPH)"` in md, and the change shows as `**…**` / `~~…~~`.
  - `test_a_file_without_its_legend_is_refused` and `test_differing_legends_are_refused`: edit one staged file; exit 1, no output file.
  - `test_body_markdown_matches_render`: for Articles 3 and 7 on a v1.0 tree, `body_markdown(n, text, src_dir=tree)` is contained in `render(n, src_dir=tree, version=VER)`.
  - `test_the_integrated_redline_writes_its_md`: `build-redline-full.sh v0.98-draft v1.0 "January 1, 2027"` with `SRC_DIR`, `REDLINE_OUT=<tmp>/rl.pdf`, `REDLINE_MD_OUT=<tmp>/rl.md` on the edited tree → both exist; the `.md` passes the same assertions as the first test; with `REDLINE_MD_OUT` unset no `.md` is written anywhere (control: behaviour unchanged).
- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
  - `czc_md.py`: factor `body_markdown` out of `render`'s existing steps (the frontmatter split, `_walk_body`, and the after-prose pointers); `render` calls it; no change to `render`'s output.
  - `redline_md.py`: for each `article-0*.md` in the stage in sorted order — split frontmatter (read `article-number` and `article-name`); the rest must begin with a paragraph starting `Redline key:` (else refuse naming the file); all legends must be identical (else refuse); strip it; `body_markdown(n, rest, src_dir=stage)`. Output: `# {title}`, blank, the legend, blank, then per Article `# Article {n}: {name}`, blank, its body, blank. Write atomically (temp file + rename) only after every Article succeeded. Docstring: why (D1 — the markdown redline is the only redline that survives in git).
  - `build-redline-full.sh`: when `REDLINE_MD_OUT` is set, also stage `--plain` into a second temp dir (same old ref, baseline flag and `CZC_SECTION_MAP`) and run `redline_md.py` with title `"$RL_NAME — Redline"` into a temp file; place it at `REDLINE_MD_OUT` only after the PDF is placed.
- [ ] **Step 4: Run** `python3 -m pytest build/tests/test_redline_md.py build/tests/test_czc_md.py -v` — all pass.
- [ ] **Step 5: Untouched-files diff (empty); full suite; commit** `build/czc_md.py build/redline_md.py build/build-redline-full.sh build/tests/test_redline_md.py`:

```
redline: the integrated redline has a markdown edition

The redline PDF is gitignored, so the markdown is the only redline that will
exist in the repository a year from now (decision D1) -- and the integrated
redline never produced one. redline_md assembles it from the plain-marked stage:
one legend, every Article under its own heading, its tables and page notes
handled by czc_md's own walker (now public as body_markdown, not copied).
build-redline-full.sh writes it when REDLINE_MD_OUT is set.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task 3: The release plan

**Files:** Create `build/release_plan.py`, `build/tests/test_release_plan.py`.

**Interfaces — Produces** CLI `python3 build/release_plan.py --old REF --new-dir DIR --version V --date D --out PLAN.json --ships SHIPS.json [--section-map P] [--calls FILE]` — exit 0 written, 1 refused (`release_plan: refusing -- …`, nothing written). And `release_plan.build(...) -> dict` for tests. The plan:

```json
{
  "schema": 1, "version": "v0.98-draft", "date": "January 1, 2027", "mode": "draft", "old": "v1.0",
  "section_map": {"renumbered": 0},
  "articles": {
    "7": {"name": "Use Standards", "verdict": "SUBSTANTIVE", "status": "SUBSTANTIVE", "new": false,
          "counts": {"prose": 1, "heading": 0, "table": 0, "data": 0, "suppressed": 0},
          "needs_call": [], "call": null}
  },
  "artifacts": [
    {"kind": "integrated", "article": null, "files": ["Newcastle CZC (Integrated Draft v0.98-draft).pdf", "Newcastle CZC (Integrated Draft v0.98-draft).md"]},
    {"kind": "integrated-redline", "article": null, "files": ["… — Redline.pdf", "… — Redline.md"]},
    {"kind": "standalone", "article": 7, "files": ["Article 7 Use Standards (Standalone v0.98-draft).pdf", "….md"]},
    {"kind": "standalone-redline", "article": 7, "files": ["Article 7 Use Standards (Standalone v0.98-draft) — Redline.pdf", "….md"]},
    {"kind": "use-table-changes", "article": 2, "files": ["Use Table Changes v0.98-draft.md", "Use Table Changes v0.98-draft.pdf"]},
    {"kind": "summary", "article": null, "files": ["Summary of Changes v0.98-draft.md"]},
    {"kind": "record", "article": null, "files": ["release-plan.json", "ships.json"]}
  ]
}
```
(`articles` lists all nine; `section_map` is `null` when no map was given.)

- [ ] **Step 1: Write the failing tests** — `build/tests/test_release_plan.py`, using `copy_full_source` trees (old ref `v1.0`):
  - unchanged tree → all nine UNCHANGED; artifacts are exactly integrated, integrated-redline, summary, record.
  - one Article 7 prose edit → Article 7 SUBSTANTIVE; artifacts add exactly Article 7's standalone and standalone-redline with the names `adoption-name.sh` gives (`czc_standalone_name`, called through bash — the test compares against that call, not a literal).
  - one `article-02-data.json` status edit → Article 2 SUBSTANTIVE and a `use-table-changes` artifact.
  - a comment appended to `article-02.typ` → Article 2 NEEDS-CALL; **without calls: refused, the message names Article 2 and quotes its needs_call line**; with a `layout-only` call → status LAYOUT-ONLY, no Article 2 standalone, the call copied into the plan.
  - calls refused: empty `reason`; empty `by`; `layout-only` for an UNCHANGED Article; `substantive` for a SUBSTANTIVE Article; duplicate Article; Article 10; an unknown key. Each exits 1 and writes neither file.
  - a `substantive` call on an UNCHANGED Article ships its standalone pair.
  - a refused `czc_diff` (e.g. bad `--old` ref) → refused, nothing written.
- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** per rulings 3–6: run `czc_diff.py` as a subprocess with `--json` into a temp file (refusal → refuse, relaying its message); validate calls; compute statuses; run `use_table_changes.py <old> <tmp.md> --new-dir DIR` (0 include, 2 not, 1 refuse); names via `bash -c 'source build/adoption-name.sh; czc_integrated_name draft "$1"'` and `czc_standalone_name draft N NAME V [redline]` (Article names from each prose file's frontmatter `article-name`); `section_map.renumbered` = number of entries across the map's `articles`. Write `ships.json` (czc_diff's JSON, verbatim) and the plan only after everything succeeded.
- [ ] **Step 4: Run** `python3 -m pytest build/tests/test_release_plan.py -v` — all pass.
- [ ] **Step 5: Untouched-files diff (empty); full suite; commit** `build/release_plan.py build/tests/test_release_plan.py`:

```
build: release_plan turns the change determination into a release plan

What a release must contain follows from czc_diff's verdicts, except where a
machine cannot decide (a changed layout unit): there a person's written call --
layout-only or substantive, with a reason and a name -- is required, and its
absence stops the release, naming the Article. A call can make a release ship
more, never less. The Use Table Changes artifact is planned by running
use_table_changes itself. The plan, with every call, is written as
release-plan.json beside czc_diff's ships.json.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task 4: The Summary skeleton

**Files:** Create `build/summary_skeleton.py`, `build/tests/test_summary_skeleton.py`.

**Interfaces:** Consumes the Task 3 plan. Produces CLI `python3 build/summary_skeleton.py <plan.json> <out.md>` — exit 0 written, 1 refused (out exists, or the plan is malformed).

- [ ] **Step 1: Write the failing tests** over hand-made plan dicts (no build needed):
  - names each SUBSTANTIVE Article under "## Articles with their own extract and redline" with what changed in words ("its text", "its headings", "its tables", "its district or inventory data") from the non-zero counts;
  - names each RENUMBER-ONLY Article under "## Articles changed only by renumbering or cross-reference updates" (standing rule 4);
  - names each LAYOUT-ONLY Article with its reason and who decided, under "## Layout-only changes (a person's call)";
  - "## What the redline cannot show" lists: tables shown unmarked when any table count > 0; the data-generated pages of each Article with data > 0 or a layout call, **by their manifest labels** (e.g. "the thirteen district pages (district standards and use tables)"); "N section renumbering(s) suppressed as mechanical" when `section_map.renumbered > 0`; the Use Table Changes artifact when planned;
  - the opening line states the version, the date, and "Changes are stated against <old>"; when `<old>` equals `adoption-map.json`'s `baseline_version` it adds ", the Code as most recently adopted";
  - prose sections ("## What is new", "## What changed") are present with an HTML-comment placeholder asking for plain words and no file, path or script references;
  - **none of** "November 3, 2020", "March 24, 2025", "3-8 become 4-9", "entirely new" appear;
  - an all-UNCHANGED plan says so in one sentence;
  - an existing output file is refused and left byte-identical.
- [ ] **Step 2: Run to verify failure. Step 3: Implement** (labels from `manifest.load()`; baseline from `adoption_map.load()`; no hard-coded cycle facts). **Step 4: Run** the file — all pass.
- [ ] **Step 5: Untouched diff; full suite; commit** `build/summary_skeleton.py build/tests/test_summary_skeleton.py`:

```
build: the Summary of Changes skeleton is generated from the release plan

build-adoption.sh writes a skeleton keyed to the v0.1 baseline ("amended through
March 24, 2025", "old 3-8 become 4-9") -- false for every later cycle. The
skeleton now comes from the plan: every Article named by what happened to it
(standing rule 4 requires the renumber-only ones by name), every layout call
with its reason, and what the redline cannot show, from the plan's own counts
and the manifest's page labels. The prose stays hand-written, and an existing
Summary is never overwritten.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task 5: The gate

**Files:** Create `build/release_gate.py`, `build/tests/test_release_gate.py`.

**Interfaces:** Consumes the Task 3 plan. Produces CLI `python3 build/release_gate.py <plan.json> <dir>` — exit 0 (silent but one summary line), 1 refused with one stderr line per problem; and `release_gate.check(plan: dict, dir: Path) -> list[str]` (problems) and `release_gate.footer_numbers(pdf: Path) -> list[tuple[int, int]]` ((physical page, printed number), 1-based physical, bottom 40 pt band, the `FOOTER_NUMBER` pattern above).

- [ ] **Step 1: Write the failing tests** with synthetic PDFs made in the test with PyMuPDF (`fitz.open()`, `new_page`, `insert_text` near the bottom edge reading `Newcastle Core Zoning Code | N`), and empty `.md` / non-empty `.md` files:
  - a complete set → `check` returns `[]`, CLI exit 0;
  - a missing planned file → problem naming it;
  - a zero-byte planned file → problem;
  - a PDF numbered 1,2,4 → problem (offset changes);
  - a PDF with front pages unnumbered then 1,2,3 starting on physical page 3 → **no** problem (constant offset);
  - a PDF with no printed number at all → problem;
  - an unplanned file in the dir → problem naming it; an existing `Summary of Changes <v>.pdf` → allowed;
  - CLI exit 1 lists every problem, not just the first.
- [ ] **Step 2–4:** fail, implement, pass.
- [ ] **Step 5: Untouched diff; full suite; commit** `build/release_gate.py build/tests/test_release_gate.py`:

```
build: release_gate refuses an incomplete or mis-paginated release

A leaf builder's exit 0 does not prove its file was written. The gate checks
the staged release against its plan: every planned file present and non-empty,
nothing unplanned, and every PDF's printed page numbers keeping a constant
offset from its physical pages -- the parity invariant a missing page or a
counted front note breaks. It refuses; it does not report.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task 6: `build-release.sh`

**Files:** Create `build/build-release.sh`, `build/tests/test_build_release.py`.

**Interfaces:** Consumes Tasks 1–5. Produces `bash build/build-release.sh <version> [date] --old-ver=<ref> [--plan-only] [--out-dir DIR] [--calls FILE]`; env `SRC_DIR` (new tree, default `source/`); test seams `CZC_LEAF_*` (ruling 11). `--out-dir` is the release directory itself (default `releases/<version>`). Exit 0 released; 1 refused (release directory untouched, staging removed).

- [ ] **Step 1: Write the failing tests** — `build/tests/test_build_release.py`, each building into `tmp_path` from a `copy_full_source` tree, version `v0.98-draft`, `--old-ver=v1.0`, date "January 1, 2027":
  - (a) unchanged tree → exit 0; the directory holds exactly: integrated pdf+md, integrated redline pdf+md, the Summary md, `release-plan.json`, `ships.json`; the Summary says nothing shipped as an extract.
  - (b) one Article 7 prose edit → exactly (a)'s files plus Article 7's standalone pdf+md and standalone redline pdf+md.
  - (c) one `article-02-data.json` status edit → (a)'s files plus Article 2's four files plus `Use Table Changes v0.98-draft.md` and `.pdf`; the Article 2 standalone redline `.md` names "the thirteen district pages".
  - (d) an Article 2 layout-unit edit with a calls file whose reason is empty → exit 1, release dir absent; with a proper `layout-only` call → exit 0 and the Summary quotes the reason.
  - (e) `--plan-only` → exit 0, the plan JSON on stdout, release dir absent.
  - **Negative control:** (b) with `CZC_LEAF_STANDALONE` pointing at a stub script that exits 0 and writes nothing → exit 1, stderr names the missing Article 7 standalone, release dir absent, no `.staging-*` dir left beside it.
  - an existing release dir holding only `Summary of Changes v0.98-draft.md` → exit 0, that Summary byte-identical afterwards; holding anything else → exit 1, untouched.
  - missing `--old-ver` → exit 1; version `v1.0` → exit 1 (not a draft version); `ADOPTION_MODE=meeting` → exit 1.
- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** the driver: parse arguments; refusals first (rulings 1, 2, 9); create the staging dir beside the release dir (`mktemp -d "<parent>/.staging-<ver>.XXXXXX"`) with an EXIT trap that removes it; `section_map.py derive` into a temp file (exit 2, below the floor: proceed with no map and say so; exit 1: refuse) then `selfcheck` (non-zero: refuse); `release_plan.py` into staging (`--plan-only`: print the plan, exit 0); integrated build (`OUT_DIR=staging`); integrated redline (`REDLINE_OUT=staging/<name> — Redline.pdf`, `REDLINE_MD_OUT=…md`, `SECTION_MAP`, `SRC_DIR`); for each `standalone` artifact the standalone build, for each `standalone-redline` the standalone redline (`REDLINE_OUT=staging`, `SECTION_MAP`); the use-table memo (`use_table_changes.py` + `build-memo.sh` with running head `Use Table Changes — <ver>`) when planned; the Summary skeleton into staging — or, when the release dir already holds a hand-written `Summary of Changes <ver>.md` (and `.pdf`), a byte-for-byte copy of it into staging instead, so the gate sees the planned file and the move writes back identical bytes; `release_gate.py plan staging` (non-zero: refuse); move into place (rename staging to the release dir, or move each file into a Summary-only release dir); finally `pdf_recap.py` over the PDFs (report only) and `Release <ver>: N file(s) -> <dir>`. All leaf calls through the `CZC_LEAF_*` variables. Header comment documents the sequence, the seams, and that adoption runs through `build-adoption.sh` (4b).
- [ ] **Step 4: Run** `python3 -m pytest build/tests/test_build_release.py -v` — all pass.
- [ ] **Step 5: Untouched diff; full suite; commit** `build/build-release.sh build/tests/test_build_release.py`:

```
build: build-release.sh, one command for a draft release and its gate

The deliverables were produced by hand-run commands, and nothing knew what a
release must contain. build-release.sh derives and selfchecks the section map,
plans the release from the change determination and a person's written calls,
builds every planned artifact into a staging directory -- the integrated Code,
its redline in both formats, each substantively changed Article's extract and
redline, the Use Table Changes memo when district data moved, and a Summary
skeleton -- and moves it into place only after the gate passes. A refusal at any
step leaves no release directory. Draft releases only; adoption follows in 4b.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Done when

- `build-release.sh` builds a draft release end to end from one command, refuses without `--old-ver`, refuses a NEEDS-CALL Article without a written call, and leaves no release directory on any refusal — the negative control proves the gate catches a leaf that wrote nothing.
- The section map reaches staging, text and page; the integrated redline has a `.md`.
- The untouched files are byte-identical to `main`; the full suite passes; CI is green on the PR.

## Not in this plan (4b / 4c)

- 4b: the integrated `.md` through `czc_md` (tables, district appendix, pointer notes); generated cover facts (D6); `build-adoption.sh` calling the driver in meeting mode (with its own gates kept); `pdf_recap` counts as assertions; `ADOPTION-SPEC.md` + `CLAUDE.md` revisions (P18), including "Build & release flow" becoming `build-release.sh`.
- 4c: the fifth status code (P15), after its four values are decided.
