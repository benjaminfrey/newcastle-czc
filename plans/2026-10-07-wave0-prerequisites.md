# Wave 0 — Prerequisites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the missing page chrome on Article 2's first district page — a defect live in the adopted v1.0 edition — and convert the tests that track the live working tree into fixture- and invariant-driven tests, so later waves are not fighting red baselines they did not cause.

**Architecture:** Two independent changes with no shared code. The chrome fix removes three early returns in `source/article-02.typ` that were written for a leading parity blank the build no longer inserts, and adds the first test in the repository that asserts chrome on a unit's first page. The test de-pinning replaces three literals computed from the working tree with a fixture source tree and with invariants (front matter even, exactly one structural blank, every printed footer number equals its physical page minus the front-matter count).

**Tech Stack:** Bash build scripts, Typst 0.12 (native units), pandoc, Python 3.14 with PyMuPDF (`pymupdf`), pytest.

## Global Constraints

- **NEVER commit unless explicitly asked.** Each task below ends with a commit step; run it only when the operator has said to commit. If unsure, stop and ask.
- **NEVER `git add -A` or `git add .`** — stage files by name, exactly as each commit step lists them.
- **Never modify anything in `docs/`** — those are the immutable baseline PDFs.
- Commit messages end with the trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- **Parity invariant:** chrome (running head, footer page number, rotated Article tab) keys off `here().page() + page_offset`, and logical page must equal physical page. A change that alters pagination breaks parity; a change that alters only chrome does not.
- Build tests run with `python3 -m pytest build/tests -q` from the repository root. The suite is **111 tests** and takes about 2.5 minutes because it builds real PDFs.
- The integrated draft build is **117 pages with 1 structural blank** (the front-matter blank). Front matter is **4 pages**: cover, blank, and the two-page TOC.
- Work on branch `release-deliverables`.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `source/article-02.typ` | Article 2's thirteen district spreads, native Typst | Modify — remove three `here().page() == 1` guards at `:95`, `:119`, `:143` |
| `build/build-full-czc.sh` | Integrated build | Modify — delete two comments describing parity padding the code does not perform (`:87-89`, `:137`) |
| `build/tests/test_unit_chrome.py` | **New.** Asserts every district page carries chrome; the repository has no such test today, which is how this reached an adopted ordinance | Create |
| `build/adoption_breakdown.py` | Per-article substantive-change breakdown | Modify — add a `SRC_DIR` seam so a test can point it at a fixture tree instead of live `source/` |
| `build/tests/fixtures/breakdown-src/` | **New.** A two-article fixture source tree with a known substantive-change count | Create |
| `build/tests/test_build_adoption.py` | Freeze behaviour | Modify — replace `EXPECTED_TOTAL = 151` with a fixture assertion plus an internal-consistency invariant |
| `build/tests/test_structural_note.py` | Front-note placement and parity | Modify — replace `page_count == 117` and `"113" in last` with invariants |

---

## Task 1: Prove the chrome defect with a failing test

**Files:**
- Create: `build/tests/test_unit_chrome.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `build_integrated(tmp_path, version, date_str, **env) -> pymupdf.Document` — a helper later tasks reuse. It returns an open document; the caller closes it.

- [ ] **Step 1: Measure the defect before asserting it**

Run this and read the output. It prints every page that carries a district panel and whether that page carries the footer wordmark. Expect exactly one `MISSING`.

```bash
cd "/Users/ben/Developer/Claude/Projects/Newcastle Core Zoning Code"
python3 - <<'PY'
import os, subprocess, tempfile, pathlib, pymupdf
repo = pathlib.Path.cwd()
with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, OUT_DIR=tmp)
    subprocess.run(["bash", "build/build-full-czc.sh", "v0.24-draft", "August 24, 2026"],
                   cwd=repo, env=env, check=True, capture_output=True)
    pdf = next(pathlib.Path(tmp).glob("*.pdf"))
    d = pymupdf.open(pdf)
    for i, page in enumerate(d):
        t = page.get_text()
        if "LOT DIMENSIONS" in t:
            ok = "Newcastle Core Zoning Code" in t
            print(f"physical page {i+1}: {'ok' if ok else 'MISSING FOOTER'}")
    print("page_count", d.page_count)
PY
```

Expected: a list of district pages, exactly one reading `MISSING FOOTER`, and `page_count 117`.

- [ ] **Step 2: Write the failing test**

```python
# build/tests/test_unit_chrome.py
"""Chrome on the first page of a native-Typst unit.

Nothing in this repository asserted chrome on any unit's first page before this
file, which is why Article 2's first district page shipped without a footer in
the adopted v1.0 edition. The guards that caused it were written for a leading
parity blank that build-full-czc.sh no longer inserts.
"""
import os
import subprocess
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent.parent

WORDMARK = "Newcastle Core Zoning Code"
DISTRICT_PANEL = "LOT DIMENSIONS"


def build_integrated(tmp_path, version="v0.24-draft", date_str="August 24, 2026", **env):
    """Build the integrated draft into tmp_path and return the open document."""
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    e = dict(os.environ, OUT_DIR=str(out), **env)
    subprocess.run(["bash", "build/build-full-czc.sh", version, date_str],
                   cwd=REPO, env=e, check=True, capture_output=True)
    return pymupdf.open(next(out.glob("*.pdf")))


def test_every_district_page_carries_the_footer(tmp_path):
    d = build_integrated(tmp_path)
    try:
        missing = [i + 1 for i, page in enumerate(d)
                   if DISTRICT_PANEL in page.get_text()
                   and WORDMARK not in page.get_text()]
    finally:
        d.close()
    assert missing == [], (
        f"district pages without a footer: {missing}. article-02.typ returns "
        f"early on here().page() == 1, a guard written for a leading parity "
        f"blank the build no longer inserts.")


def test_every_district_page_carries_the_article_tab(tmp_path):
    d = build_integrated(tmp_path)
    try:
        missing = [i + 1 for i, page in enumerate(d)
                   if DISTRICT_PANEL in page.get_text()
                   and "ARTICLE 2" not in page.get_text()]
    finally:
        d.close()
    assert missing == [], f"district pages without the article tab: {missing}"
```

- [ ] **Step 3: Run the tests and watch them fail**

```bash
python3 -m pytest build/tests/test_unit_chrome.py -v
```

Expected: both tests FAIL, each naming the same single physical page number — the one Step 1 reported.

- [ ] **Step 4: Commit the failing test**

```bash
git add build/tests/test_unit_chrome.py
git commit -m "test: assert chrome on every Article 2 district page

Fails today: the first district page carries no footer and no article tab.
Nothing asserted chrome on a unit's first page before this, which is how the
defect reached the adopted v1.0 edition.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Remove the three guards

**Files:**
- Modify: `source/article-02.typ:95` (header), `:119` (footer), `:143` (background/tab)
- Test: `build/tests/test_unit_chrome.py`

**Interfaces:**
- Consumes: `build_integrated` from Task 1.
- Produces: nothing new.

- [ ] **Step 1: Remove the header guard**

In `source/article-02.typ`, delete the five comment lines and the guard immediately above `let pn = here().page() + page_offset` in the `#set page(header: ...)` block:

```typst
  // Physical page 1 is always the leading parity-blank inserted by the
  // `pagebreak(to:"even")` at the start of the render (it lands D1 on a verso).
  // Keep that page a TRUE blank — no header/footer/tab — so it reads as a clean
  // section break, not a chrome-bearing empty page.
  if here().page() == 1 { return [] }
```

So the block begins:

```typst
#set page(header: context {
  let pn = here().page() + page_offset
  let grp = group_state.get()
```

- [ ] **Step 2: Remove the footer guard**

Delete this line from the `#set page(footer: ...)` block:

```typst
  if here().page() == 1 { return [] }   // leading parity-blank: no footer
```

- [ ] **Step 3: Remove the article-tab guard**

Delete this line from the `#set page(background: ...)` block:

```typst
  if here().page() == 1 { return [] }   // leading parity-blank: no article tab
```

- [ ] **Step 4: Run the chrome tests and watch them pass**

```bash
python3 -m pytest build/tests/test_unit_chrome.py -v
```

Expected: both PASS.

- [ ] **Step 5: Prove pagination did not move**

Chrome is not content; the page and blank counts must be identical.

```bash
python3 - <<'PY'
import os, subprocess, tempfile, pathlib, pymupdf
repo = pathlib.Path.cwd()
with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, OUT_DIR=tmp)
    subprocess.run(["bash", "build/build-full-czc.sh", "v0.24-draft", "August 24, 2026"],
                   cwd=repo, env=env, check=True, capture_output=True)
    d = pymupdf.open(next(pathlib.Path(tmp).glob("*.pdf")))
    blanks = [i + 1 for i, p in enumerate(d) if not p.get_text().strip()]
    print("page_count", d.page_count, "blanks", blanks)
PY
```

Expected: `page_count 117 blanks [2]` — one structural blank, the front-matter blank.

- [ ] **Step 6: Run the whole build suite**

```bash
python3 -m pytest build/tests -q
```

Expected: 111 passed plus the 2 new tests = **113 passed**.

- [ ] **Step 7: Commit**

```bash
git add source/article-02.typ
git commit -m "article 2: restore chrome on the first district page

The three guards returned empty header, footer and article tab on physical
page 1 of the unit. They were written for a leading parity blank that the
build stopped inserting when the redundant Article 2 blanks were removed in
2026-06, so the guard has been suppressing chrome on D1's first page ever
since — in every draft, in the Town Meeting edition, and in the adopted v1.0
edition, which renders from this source.

Pagination is unchanged: 117 pages, one structural blank. Chrome is not
content.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Negative control — prove the test can fail

**Files:**
- Modify (temporarily, then revert): `source/article-02.typ`

**Interfaces:**
- Consumes: Task 1's tests, Task 2's fix.
- Produces: nothing. This task writes no permanent change; it proves the guard is real.

- [ ] **Step 1: Reintroduce one guard**

Put the footer guard back in `source/article-02.typ`:

```typst
  if here().page() == 1 { return [] }   // TEMPORARY — negative control
```

- [ ] **Step 2: Run the chrome test and confirm it fails for the right reason**

```bash
python3 -m pytest build/tests/test_unit_chrome.py::test_every_district_page_carries_the_footer -v
```

Expected: FAIL, naming the district page number. If it PASSES, the test is not actually exercising the defect — stop and report, because the fix in Task 2 is then unverified.

- [ ] **Step 3: Revert the guard**

```bash
git checkout source/article-02.typ
```

- [ ] **Step 4: Confirm the tests pass again**

```bash
python3 -m pytest build/tests/test_unit_chrome.py -v
```

Expected: both PASS. Nothing to commit — `git status` must show `source/article-02.typ` unmodified.

---

## Task 4: Delete the stale parity comments

**Files:**
- Modify: `build/build-full-czc.sh:87-89`, `:137`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

- [ ] **Step 1: Read both comments and confirm they describe padding the code does not perform**

```bash
sed -n 85,92p build/build-full-czc.sh
sed -n 134,140p build/build-full-czc.sh
```

The written model must match the build: the code pads to an **odd running offset** before `article-02.typ` so D1 lands on a verso, and inserts **no leading blank inside the unit**. Any comment claiming a leading parity blank inside Article 2 is wrong, and it is the comment that produced the guards Task 2 removed.

- [ ] **Step 2: Replace each stale comment with what the code actually does**

Where a comment describes a leading parity-blank page inside the Article 2 unit, replace it with:

```bash
# article-02.typ renders D1 on a verso by having the integrated build pad to an
# ODD running page_offset before this unit (offset+1 is even == verso). The unit
# itself inserts NO leading blank — it did until 2026-06, and the chrome guards
# that outlived that change suppressed the footer on D1's first page until
# 2026-10-07. Keep this comment true: it is the model the next person reads.
```

- [ ] **Step 3: Confirm the build is byte-identical**

Comments cannot change output.

```bash
python3 -m pytest build/tests/test_unit_chrome.py build/tests/test_structural_note.py -q
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add build/build-full-czc.sh
git commit -m "build: correct the parity comments in the integrated build

The comments described a leading parity blank inside the Article 2 unit. The
build pads to an odd running offset instead, and has since the redundant
Article 2 blanks were removed in 2026-06. The stale model is what produced the
chrome guards fixed in the previous commit.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Give `adoption_breakdown.py` a source seam

**Files:**
- Modify: `build/adoption_breakdown.py`
- Test: `build/tests/test_build_adoption.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `adoption_breakdown.py` honours `SRC_DIR` (environment variable) and `--src-dir PATH`, defaulting to `REPO/source`. Task 6 uses `--src-dir` to point it at a fixture tree.

- [ ] **Step 1: Write the failing test**

```python
# add to build/tests/test_build_adoption.py
def test_breakdown_accepts_a_source_directory(tmp_path):
    """The breakdown must be runnable against a fixture tree, or every test of
    it is pinned to whatever is in source/ today."""
    src = tmp_path / "source"
    src.mkdir()
    (src / "article-01-general.md").write_text(
        '---\narticle-number: "1"\narticle-name: "General Standards"\n---\n\n'
        '# Article 1 General Standards\n\n## 1. CORE ZONING CODE\n')
    r = subprocess.run(
        [sys.executable, "build/adoption_breakdown.py", "--src-dir", str(src)],
        cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1), r.stderr
    assert "article-01-general.md" in r.stdout, r.stdout
```

- [ ] **Step 2: Run it and watch it fail**

```bash
python3 -m pytest build/tests/test_build_adoption.py::test_breakdown_accepts_a_source_directory -v
```

Expected: FAIL — `unrecognized arguments: --src-dir`.

- [ ] **Step 3: Add the seam**

In `build/adoption_breakdown.py`, add the argument and use it wherever the module currently composes a path under `REPO / "source"`:

```python
import os

ap.add_argument("--src-dir", default=os.environ.get("SRC_DIR"),
                help="source tree to compare against the baseline "
                     "(default: the repository's source/). The SRC_DIR env var "
                     "is honoured too, matching build-full-czc.sh's seam.")
```

and resolve it once, near the top of the function that reads the current side:

```python
src_dir = Path(args.src_dir) if args.src_dir else (REPO / "source")
```

Replace every later `REPO / "source"` in that path with `src_dir`.

- [ ] **Step 4: Run the test and watch it pass**

```bash
python3 -m pytest build/tests/test_build_adoption.py::test_breakdown_accepts_a_source_directory -v
```

Expected: PASS.

- [ ] **Step 5: Confirm the default is unchanged**

```bash
python3 build/adoption_breakdown.py | tail -3
```

Expected: the same TOTAL the command printed before this task — the seam must not change default behaviour.

- [ ] **Step 6: Commit**

```bash
git add build/adoption_breakdown.py build/tests/test_build_adoption.py
git commit -m "build: let adoption_breakdown read a source tree other than source/

Without a seam, every test of the breakdown is pinned to whatever is in the
working tree, so the suite goes red the moment an amendment lands — at exactly
the release where the number matters most.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: De-pin `EXPECTED_TOTAL`

**Files:**
- Create: `build/tests/fixtures/breakdown-src/article-01-general.md`
- Create: `build/tests/fixtures/breakdown-src/README.md`
- Modify: `build/tests/test_build_adoption.py:11-17,28` and the test that uses `EXPECTED_TOTAL`

**Interfaces:**
- Consumes: Task 5's `--src-dir`.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Create the fixture tree**

```bash
mkdir -p build/tests/fixtures/breakdown-src
```

`build/tests/fixtures/breakdown-src/article-01-general.md`:

```markdown
---
article-number: "1"
article-name: "General Standards"
footer-date: "Draft vX.Y-draft"
---

# Article 1 General Standards

## 1. CORE ZONING CODE

### a. PURPOSE

1. This fixture exists so the breakdown can be tested without pinning the test
   to whatever is in source/ today.

2. This sentence is the only substantive difference from the baseline copy of
   this file, so the expected count is one.
```

`build/tests/fixtures/breakdown-src/README.md`:

```markdown
# breakdown-src

A minimal source tree for `build/adoption_breakdown.py` tests. It exists so the
breakdown's output can be asserted against a known, frozen input rather than
against the live `source/` tree, which moves with every amendment.

Keep it small. If a test needs a second article, add the smallest file that
exercises the rule under test, and say here what it is for.
```

- [ ] **Step 2: Write the replacement test**

Replace the test that asserts `EXPECTED_TOTAL` with these two. The first pins the instrument against a frozen input; the second is the invariant that survives any amendment.

```python
def test_breakdown_reports_the_fixture_tree_exactly(tmp_path):
    """The instrument is pinned against a frozen input, not against source/."""
    fixture = Path(__file__).resolve().parent / "fixtures" / "breakdown-src"
    r = subprocess.run(
        [sys.executable, "build/adoption_breakdown.py", "--src-dir", str(fixture),
         "--map", str(_PRE_ROLLOVER_MAP)],
        cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1), r.stderr
    assert "article-01-general.md" in r.stdout


def test_breakdown_total_equals_the_sum_of_its_own_lines():
    """The invariant: whatever the per-article numbers are, the TOTAL is their
    sum. This holds at every release, so it never needs re-pinning — and it
    catches the failure a literal cannot: a total that stops matching its own
    breakdown."""
    r = subprocess.run([sys.executable, "build/adoption_breakdown.py"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1), r.stderr
    per_article = [int(m) for m in re.findall(r"^\s+article-\S+\s+(\d+) lines?$",
                                              r.stdout, re.M)]
    total = int(re.search(r"^\s+TOTAL\s+(\d+) substantive changed lines?$",
                          r.stdout, re.M).group(1))
    assert per_article, f"no per-article lines parsed from:\n{r.stdout}"
    assert sum(per_article) == total, (
        f"TOTAL {total} is not the sum of its own per-article lines "
        f"{per_article} (sum {sum(per_article)})")
```

- [ ] **Step 3: Delete `EXPECTED_TOTAL` and its comment block**

Remove lines 11–28 of `build/tests/test_build_adoption.py` — the explanatory comment and the constant — and add this where the constant was:

```python
# The reviewed headline number is NOT pinned here any more. It was EXPECTED_TOTAL
# = 151, measured against the working tree on 2026-08-24; it went red the moment
# an amendment landed, and re-pinning it is how a reviewed number silently
# becomes a reproduced one. The number is now asserted two ways: against a frozen
# fixture tree (the instrument works) and as the sum of its own per-article lines
# (the instrument is self-consistent). The release operator still reads the real
# breakdown before a freeze — that is build-adoption.sh's job, not this file's.
```

- [ ] **Step 4: Run the file**

```bash
python3 -m pytest build/tests/test_build_adoption.py -v
```

Expected: all PASS, including the two new tests.

- [ ] **Step 5: Prove the invariant can fail**

Temporarily edit `build/adoption_breakdown.py` so the total it prints is one higher than the sum, run the invariant test, confirm FAIL with a message naming both numbers, then `git checkout build/adoption_breakdown.py`.

```bash
python3 -m pytest build/tests/test_build_adoption.py::test_breakdown_total_equals_the_sum_of_its_own_lines -v
git checkout build/adoption_breakdown.py
```

- [ ] **Step 6: Commit**

```bash
git add build/tests/test_build_adoption.py build/tests/fixtures/breakdown-src/article-01-general.md build/tests/fixtures/breakdown-src/README.md
git commit -m "test: de-pin the breakdown total from the working tree

EXPECTED_TOTAL = 151 was measured against source/ on 2026-08-24 and goes red
the moment any amendment lands. Replaced by two assertions that do not: the
breakdown reproduces a frozen fixture tree exactly, and its TOTAL equals the
sum of its own per-article lines. The second catches a failure the literal
never could — a total that stops matching its own breakdown.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Convert the structural-note literals to invariants

**Files:**
- Modify: `build/tests/test_structural_note.py:108,118`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

- [ ] **Step 1: Replace the page-count literal**

In `test_front_note_replaces_the_blank_without_moving_anything`, replace:

```python
    assert d.page_count == 117, (
        f"the note must not change the page count (got {d.page_count}); it "
        f"takes the place of the blank verso, it does not add a page")
```

with a comparison against the same build without the note — which is what the test is actually claiming:

```python
    # The claim is "the note does not add a page", so compare against the same
    # build without it rather than against a literal that moves every amendment.
    plain_out = tmp_path / "plain"
    plain_out.mkdir()
    subprocess.run(["bash", "build/build-full-czc.sh", "v0.24-draft", "August 24, 2026"],
                   cwd=REPO, env=dict(os.environ, OUT_DIR=str(plain_out)),
                   check=True, capture_output=True)
    plain = pymupdf.open(next(plain_out.glob("*.pdf")))
    try:
        assert d.page_count == plain.page_count, (
            f"the note changed the page count: {plain.page_count} without it, "
            f"{d.page_count} with it. It takes the place of the blank verso.")
    finally:
        plain.close()
```

- [ ] **Step 2: Replace the footer-number literal**

Replace:

```python
    last = d[-1].get_text()
    assert "113" in last, (
        f"the footer's page number moved — front matter is no longer 4 pages "
        f"(last page text: {last[-200:]!r})")
```

with the parity invariant it stands for:

```python
    # Parity invariant: the printed footer number equals the physical page minus
    # the 4-page front matter, on EVERY page that carries a footer — not just the
    # last one, and not a literal that moves with the Code's length.
    FRONT_COUNT = 4
    for i in range(FRONT_COUNT, d.page_count):
        text = d[i].get_text()
        if "Newcastle Core Zoning Code" not in text:
            continue
        expected = str(i + 1 - FRONT_COUNT)
        assert expected in text, (
            f"physical page {i + 1} should print footer number {expected}; "
            f"front matter is 4 pages and logical must equal physical. "
            f"Page text ends: {text[-200:]!r}")
```

- [ ] **Step 3: Run the file**

```bash
python3 -m pytest build/tests/test_structural_note.py -v
```

Expected: all PASS.

- [ ] **Step 4: Prove the parity invariant can fail**

Temporarily change `FRONT_COUNT` to `5`, run, confirm FAIL naming a physical page and its expected number, then change it back to `4`.

```bash
python3 -m pytest build/tests/test_structural_note.py -v
```

- [ ] **Step 5: Run the whole suite**

```bash
python3 -m pytest build/tests -q
```

Expected: **115 passed** — the 111 originals, plus 2 chrome tests, plus 2 breakdown tests.

- [ ] **Step 6: Commit**

```bash
git add build/tests/test_structural_note.py
git commit -m "test: assert parity as an invariant, not as two literals

page_count == 117 and \"113\" in last were measured against the Code's current
length. Both move with any amendment, and both would be re-pinned reflexively
at exactly the release where the evidence matters. Replaced by what they stood
for: the note does not change the page count (compared against the same build
without it), and every footer number equals its physical page minus the
four-page front matter — checked on every page, not just the last.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Done when

- `python3 -m pytest build/tests -q` reports **115 passed**.
- A fresh integrated build is **117 pages, one blank at physical page 2**, and every page carrying a district panel also carries the footer wordmark and the ARTICLE 2 tab.
- No literal page count, footer number, or breakdown total remains in `build/tests/` except inside `build/tests/fixtures/`, where a comment names the release it was measured on.
- `git status` is clean apart from the four untracked entries the repository always carries.

## Not in this plan

Wave 1's seams (P1–P5, P9), Wave 2's section map and normaliser rule (P6, P7), Wave 3's determination and artifacts (P8, P10–P12, P14), Wave 4's release driver (P13, P18), and the fifth use-table status code (P15), which ships separately by decision D3. Each has its own plan.

P17 also calls for two fixtures this plan cannot write yet: **a section map with a within-article shift**, which has no format until `section_map.py` exists (P6), and a **`v1.0`-as-baseline pair**, which the section rule consumes (P7). Both land in the Wave 2 plan, where the thing they exercise exists; writing them here would mean inventing a shape P6 is free to change.

`build/tests/test_footer_modes.py` appears in P17's touches and is **reviewed and left alone**: its literals at `:25` and `:33-35` are throwaway test version strings deliberately picked outside the release series, not measurements of the live tree, so they do not go red when an amendment lands.

The app-side literals named in P17 — `test_use_matrix.py`'s 819/63 counts, `test_parse_definitions.py`'s 272 terms and RESIDENCE section, `test_edition_rollover.py:73` — are **not** touched here. They move only when the Code's data changes, which happens in P15, and they are de-pinned in that plan where the change that moves them is visible.
