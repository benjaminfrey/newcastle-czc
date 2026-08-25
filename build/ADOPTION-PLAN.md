# Adoption Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a two-stage adoption release to the CZC build system — freeze a draft into a Town Meeting edition at a whole version number with a correct redline against the previously adopted Code, then stamp it adopted after the vote.

**Architecture:** Two new wrapper scripts (`build-adoption.sh`, `build-adopted.sh`) reuse the existing `SRC_DIR`/`OUT_DIR` seams in `build-full-czc.sh` rather than forking it, exactly as `build-redline-full.sh` already does. Two new Python modules supply the knowledge the build currently lacks: a baseline→current article map, and a diff normaliser. Chrome gains a three-valued mode. Every state rule is a refusal, not a convention.

**Tech Stack:** bash, Python 3 (stdlib + PyMuPDF, already used by `build-cover.py`), pytest 9 (system Python), pandoc → Typst.

## Global Constraints

- **Spec:** `build/ADOPTION-SPEC.md` is authoritative. Where this plan and the spec disagree, the spec wins and the plan is wrong.
- **Never modify `docs/`.** It is the immutable baseline (original CZC, Comp Plan, RDEO). Read-only.
- **Commits: authorised for this branch only.** Ben was asked, 2026-08-24, how to run this given
  the standing rule *"NEVER commit unless explicitly asked"*, and chose: **"Feature branch, commit
  per task, you review before merge."** So on branch `adoption-release`, each task commits its own
  work. `main` is untouched until Ben reviews the branch and says merge. This authorisation is
  recorded in `.superpowers/sdd/ADOPTION-PLAN/progress.md`; a reviewer can verify it there rather
  than taking an agent's word for it. **Never push. Never `git add -A` or `git add .` — stage by
  name.** Task steps below that say "stage and report (do not commit)" are superseded by this line.
- **Never `git add -A` or `git add .`** — stage files by name.
- **Parity invariant:** chrome keys off `here().page() + page_offset`; logical page must equal physical page. Any change that breaks the constant footer offset is a defect.
- **A whole version number means adopted law; a decimal means a draft.** Enforced in Task 6.
- **Normalisation must never hide a substantive change.** Task 2's conservatism tests are the load-bearing safety property of this feature.
- Tests live in `build/tests/`, run with system `python3 -m pytest build/tests -q` from the repo root. This is a new directory; `build/` has no test convention today.
- Current release state: `v0.24-draft` is the latest tag; `v0.1-baseline` is the previously adopted Code (adopted Nov 3 2020, amended through Mar 24 2025).

---

## File Structure

| File | Responsibility |
|---|---|
| `build/adoption-map.json` | Data: baseline→current article file renames + article-number map |
| `build/adoption_map.py` | Reader for the above; resolves a current filename to its baseline path |
| `build/normalize_for_diff.py` | The three normalisation rules, each independently testable |
| `build/version_state.py` | Parses/validates version strings; the whole-number-means-adopted rule |
| `build/build-adoption.sh` | The freeze: Town Meeting edition + baseline redline + summary skeleton + standalone |
| `build/build-adopted.sh` | Post-vote: renders from the tagged meeting source, asserts content identity |
| `build/build-cover.py` | *(modify)* three-mode cover banner |
| `build/build-full-czc.sh` | *(modify)* three-mode footer; refuse whole-number draft chrome |
| `build/build-redline-full.sh` | *(modify)* `--baseline` mode: use the map + normaliser |
| `build/tests/` | pytest suite for the four Python modules |

---

### Task 1: The baseline→current article map

**Files:**
- Create: `build/adoption-map.json`
- Create: `build/adoption_map.py`
- Test: `build/tests/test_adoption_map.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `adoption_map.load(path=None) -> AdoptionMap`; `AdoptionMap.baseline_path_for(current_basename: str) -> str | None` (returns `None` when the article is new at this adoption); `AdoptionMap.renumber(text: str) -> str`; `AdoptionMap.article_numbers -> dict[int, int]`.

**Why:** `build-redline-full.sh` resolves the old side of each diff by looking up **the same filename** at the old tag. Eight of nine article files were renamed when Article 3 was inserted, so a baseline redline silently renders the whole Code as new (spec §1.1). The mapping currently exists only as a hardcoded `RENUM` dict in `extract/verso.py:18`, which the build cannot reach.

- [ ] **Step 1: Write the failing test**

```python
# build/tests/test_adoption_map.py
"""The baseline->current article correspondence.

Without this, build-redline-full.sh resolves the old side of each diff by
filename and finds nothing for 8 of 9 articles -- rendering the entire Code as
newly written in the document that goes to Town Meeting. See ADOPTION-SPEC.md §1.1.
"""
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402


def test_every_renamed_article_resolves_to_its_baseline_path():
    m = adoption_map.load()
    cases = {
        "article-01-general.md": "article-01-general.md",
        "article-04-site-standards.md": "article-03-site-standards.md",
        "article-05-building-standards.md": "article-04-building-standards.md",
        "article-06-design-standards.md": "article-05-design-standards.md",
        "article-07-use-standards.md": "article-06-use-standards.md",
        "article-08-administration.md": "article-07-administration.md",
        "article-09-definitions.md": "article-08-definitions.md",
        "article-02-prefatory.md": "article-02-districts.md",
    }
    for current, baseline in cases.items():
        assert m.baseline_path_for(current) == baseline, current


def test_article_3_is_new_and_says_so_rather_than_erroring():
    m = adoption_map.load()
    assert m.baseline_path_for("article-03-streets-roads-driveways.md") is None


def test_an_unknown_file_raises_rather_than_silently_reading_as_new():
    """The failure that motivated this module: an unmapped file must NOT
    quietly become an empty old-side and render as 100% new."""
    m = adoption_map.load()
    try:
        m.baseline_path_for("article-99-invented.md")
    except KeyError as exc:
        assert "article-99-invented.md" in str(exc)
    else:
        raise AssertionError("an unmapped article must raise, not return None")


def test_renumber_rewrites_cross_references():
    m = adoption_map.load()
    assert m.renumber("See Article 7 and Article 3.") == "See Article 8 and Article 4."
    assert m.renumber("Article 1 and Article 2 are unchanged.") == \
        "Article 1 and Article 2 are unchanged."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest build/tests/test_adoption_map.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'adoption_map'`

- [ ] **Step 3: Write the data file**

```json
{
  "_README": "Baseline->current article correspondence for an adoption release. The article files were renamed when Article 3 (Thoroughfares) was inserted, so a redline against the previously adopted Code cannot resolve the old side by filename. This map supplies that. Superseded ONLY when a future amendment renumbers articles again; after v1.0 is adopted it resets to identity. See build/ADOPTION-SPEC.md §3.1. The article_numbers map was previously hardcoded at extract/verso.py:18 and is duplicated nowhere else.",
  "baseline_version": "v0.1-baseline",
  "article_numbers": {"1": 1, "2": 2, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9},
  "files": {
    "article-01-general.md": "article-01-general.md",
    "article-02-prefatory.md": "article-02-districts.md",
    "article-03-streets-roads-driveways.md": null,
    "article-04-site-standards.md": "article-03-site-standards.md",
    "article-05-building-standards.md": "article-04-building-standards.md",
    "article-06-design-standards.md": "article-05-design-standards.md",
    "article-07-use-standards.md": "article-06-use-standards.md",
    "article-08-administration.md": "article-07-administration.md",
    "article-09-definitions.md": "article-08-definitions.md"
  },
  "new_at_this_adoption": ["article-03-streets-roads-driveways.md"]
}
```

- [ ] **Step 4: Write the reader**

```python
#!/usr/bin/env python3
"""Reads build/adoption-map.json -- the baseline->current article correspondence.

WHY THIS EXISTS. build-redline-full.sh resolves the OLD side of each article
diff by looking up the same filename at the old tag. That works between two
drafts. It does NOT work against the adopted baseline: 8 of 9 article files were
renamed when Article 3 was inserted, so 8 old-sides come back empty and the
whole Code renders as newly written -- in the document that goes to Town Meeting.
Measured 2026-08-24: exactly one file (article-01-general.md) resolved.

An UNMAPPED file raises. It must never fall through to "new", because that is
precisely the silent failure this module exists to prevent.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "adoption-map.json"


@dataclass(frozen=True)
class AdoptionMap:
    baseline_version: str
    article_numbers: dict[int, int]
    files: dict[str, str | None]

    def baseline_path_for(self, current_basename: str) -> str | None:
        """Baseline filename for a current article file, or None if it is new.

        Raises KeyError for a file the map does not know -- a new or renamed
        article must be added here deliberately, not discovered at render time.
        """
        if current_basename not in self.files:
            raise KeyError(
                f"{current_basename!r} is not in adoption-map.json. Add it "
                f"(with its baseline counterpart, or null if new at this "
                f"adoption) rather than letting it render as wholly new."
            )
        return self.files[current_basename]

    def renumber(self, text: str) -> str:
        """Rewrite 'Article N' cross-references from baseline to current numbering."""
        return re.sub(
            r"\bArticle (\d+)\b",
            lambda m: f"Article {self.article_numbers.get(int(m.group(1)), int(m.group(1)))}",
            text,
        )


def load(path: str | Path | None = None) -> AdoptionMap:
    doc = json.loads(Path(path or DEFAULT_PATH).read_text())
    return AdoptionMap(
        baseline_version=doc["baseline_version"],
        article_numbers={int(k): int(v) for k, v in doc["article_numbers"].items()},
        files=dict(doc["files"]),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest build/tests/test_adoption_map.py -q`
Expected: PASS, 4 tests

- [ ] **Step 6: Verify the map against the real repository**

Run:
```bash
python3 -c "
import sys; sys.path.insert(0,'build')
import adoption_map, subprocess, glob, os
m = adoption_map.load()
base = set(subprocess.run(['git','ls-tree','--name-only',m.baseline_version,'source/'],
    capture_output=True,text=True).stdout.split())
base = {os.path.basename(f) for f in base if 'article' in f and f.endswith('.md')}
cur  = {os.path.basename(f) for f in glob.glob('source/article-*.md')}
unmapped = cur - set(m.files)
missing  = {v for v in m.files.values() if v} - base
print('current files not in map :', unmapped or 'none')
print('map targets not in baseline:', missing or 'none')
assert not unmapped and not missing
print('MAP VERIFIED against', m.baseline_version)
"
```
Expected: both `none`, then `MAP VERIFIED against v0.1-baseline`

- [ ] **Step 7: Stage and report (do not commit)**

```bash
git add build/adoption-map.json build/adoption_map.py build/tests/test_adoption_map.py
```
Report the staged files and the verification output. A human commits.

---

### Task 2: The diff normaliser

**Files:**
- Create: `build/normalize_for_diff.py`
- Test: `build/tests/test_normalize_for_diff.py`

**Interfaces:**
- Consumes: `adoption_map.AdoptionMap` from Task 1.
- Produces: `normalize_for_diff.normalize(text: str, *, amap, is_baseline_side: bool) -> str`; `normalize_for_diff.report(old: str, new: str, *, amap) -> dict[str, int]` returning `{"heading_case": int, "renumber": int, "rewrap": int}`.

**Why:** 80% of the raw baseline diff is invisible formatting (spec §1.2) — 1,261 changed lines reduce to 243 after normalisation. Article 1 goes 30 → 0; Article 7 Use Standards 298 → 2.

**This is the most dangerous module in the feature.** A normaliser that is too aggressive silently removes a real amendment from the redline, and an omission from a redline is invisible to the reader. Every rule therefore ships with a test proving it suppresses the cosmetic case **and** a test proving a real change of the same shape still appears.

- [ ] **Step 1: Write the failing tests**

```python
# build/tests/test_normalize_for_diff.py
"""Normalisation rules for the baseline redline.

Each rule gets TWO tests: it suppresses the cosmetic difference, AND a real
change of the same shape still survives. The second test is the point. A
normaliser that quietly eats a real amendment produces a redline that is
confidently wrong, and nobody reading it can tell.
"""
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402
import normalize_for_diff as nz  # noqa: E402

AMAP = adoption_map.load()


def norm_old(t):
    return nz.normalize(t, amap=AMAP, is_baseline_side=True)


def norm_new(t):
    return nz.normalize(t, amap=AMAP, is_baseline_side=False)


# --- Rule 1: heading letter case -------------------------------------------

def test_heading_case_difference_is_suppressed():
    assert norm_old("### A. PURPOSE") == norm_new("### a. PURPOSE")


def test_but_a_changed_heading_WORD_still_differs():
    assert norm_old("### A. PURPOSE") != norm_new("### a. APPLICABILITY")


def test_case_normalisation_does_not_touch_body_text():
    """Only the heading's leading letter is lowered. Body prose keeps its case,
    including defined terms like Driveway and Thoroughfare."""
    body = "1. A Driveway serves no more than two Dwellings."
    assert norm_new(body) == body


# --- Rule 2: cross-reference renumbering ------------------------------------

def test_renumbering_is_suppressed_on_the_baseline_side_only():
    assert norm_old("See Article 7.") == norm_new("See Article 8.")


def test_but_a_reference_to_a_genuinely_different_article_still_differs():
    assert norm_old("See Article 7.") != norm_new("See Article 5.")


def test_the_new_side_is_never_renumbered():
    """Renumbering maps baseline->current. Applying it to the current side too
    would double-shift and silently corrupt every reference."""
    assert norm_new("See Article 7.") == "See Article 7."


# --- Rule 3: paragraph re-wrapping ------------------------------------------

def test_rewrapping_is_suppressed():
    wrapped = "1. The proposed subdivision will not\n   result in undue water pollution."
    flat = "1. The proposed subdivision will not result in undue water pollution."
    assert norm_old(wrapped) == norm_old(flat)


def test_but_a_deleted_sentence_still_differs():
    """THE test. If this ever passes trivially the feature is unsafe."""
    keep = "1. Water shall be adequate. Sewage shall be adequate."
    cut = "1. Water shall be adequate."
    assert norm_old(keep) != norm_new(cut)


def test_a_changed_number_still_differs():
    assert norm_old("a 40 ft right-of-way") != norm_new("a 33 ft right-of-way")


def test_shall_to_may_still_differs():
    assert norm_old("The Board shall require") != norm_new("The Board may require")


# --- The report --------------------------------------------------------------

def test_report_counts_each_rule_separately():
    old = "### A. PURPOSE\n1. See Article 7."
    new = "### a. PURPOSE\n1. See Article 8."
    r = nz.report(old, new, amap=AMAP)
    assert r["heading_case"] >= 1
    assert r["renumber"] >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest build/tests/test_normalize_for_diff.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'normalize_for_diff'`

- [ ] **Step 3: Write the module**

```python
#!/usr/bin/env python3
"""Normalisation applied to BOTH sides before a baseline redline diff.

WHY. Measured 2026-08-24 across the seven mappable article pairs: the raw diff
is 1,261 changed lines; after normalisation it is 243. Article 1 goes from 30 to
ZERO, Article 7 Use Standards from 298 to 2. The remaining 1,018 lines are
heading-case churn and paragraph re-wrapping -- neither of which reaches the
rendered page, because the Typst template styles headings itself.

Without this, the document meant to show voters what changed buries 243 real
changes under 1,018 invisible ones.

THE DANGER, and the rule that governs this file: a normaliser that is too
aggressive silently removes a real amendment from the redline, and an omission
from a redline is invisible to the reader. So:

  * Every rule is narrow and separately tested, in BOTH directions -- it
    suppresses the cosmetic case, AND a real change of the same shape survives.
  * Normalisation NEVER touches numerals, defined terms, shall/may/must, or any
    word not covered by a rule below.
  * If you are tempted to add a rule that "cleans up" anything semantic, don't.
    A noisier redline is recoverable; a redline missing an amendment is not.
"""
from __future__ import annotations

import re

# Rule 1. `### A. PURPOSE` -> `### a. PURPOSE`. ONLY the single leading letter
# of an ATX heading, and only when followed by a period. Body text is untouched.
_HEADING_LETTER = re.compile(r"^(#{1,6}\s+)([A-Za-z])(\.)", re.MULTILINE)

# Rule 3. Collapse runs of whitespace so markdown re-wrapping is invisible.
# Applied per-paragraph, so paragraph BREAKS still count as structure.
_WS_RUN = re.compile(r"[ \t]*\n[ \t]+")
_SPACES = re.compile(r"[ \t]{2,}")


def _heading_case(text: str) -> str:
    return _HEADING_LETTER.sub(lambda m: m.group(1) + m.group(2).lower() + m.group(3), text)


def _rewrap(text: str) -> str:
    # A single newline followed by indentation is a wrap; a blank line is not.
    return _SPACES.sub(" ", _WS_RUN.sub(" ", text))


def normalize(text: str, *, amap, is_baseline_side: bool) -> str:
    """Normalise one side of the diff.

    `is_baseline_side` matters: cross-reference renumbering maps baseline ->
    current, so it is applied to the OLD side only. Applying it to both would
    double-shift every reference and corrupt the comparison silently.
    """
    out = _heading_case(text)
    if is_baseline_side:
        out = amap.renumber(out)
    return _rewrap(out)


def report(old: str, new: str, *, amap) -> dict[str, int]:
    """How many differences each rule suppressed. Printed by the build so the
    normaliser's effect is visible rather than assumed."""
    counts = {"heading_case": 0, "renumber": 0, "rewrap": 0}
    counts["heading_case"] = sum(
        1 for _ in _HEADING_LETTER.finditer(old) if True
    ) - sum(1 for _ in _HEADING_LETTER.finditer(_heading_case(old)) if _.group(2).islower())
    counts["heading_case"] = max(counts["heading_case"], 0)
    counts["renumber"] = sum(
        1 for m in re.finditer(r"\bArticle (\d+)\b", old)
        if amap.article_numbers.get(int(m.group(1)), int(m.group(1))) != int(m.group(1))
    )
    counts["rewrap"] = len(_WS_RUN.findall(old)) + len(_WS_RUN.findall(new))
    return counts
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest build/tests/test_normalize_for_diff.py -q`
Expected: PASS, 11 tests

- [ ] **Step 5: Verify the measured reduction against the real repository**

Run:
```bash
python3 -c "
import sys, subprocess, difflib; sys.path.insert(0,'build')
import adoption_map, normalize_for_diff as nz
m = adoption_map.load()
tot_raw = tot_norm = 0
for cur, base in sorted(m.files.items()):
    if base is None: continue
    o = subprocess.run(['git','show',f'{m.baseline_version}:source/{base}'],
                       capture_output=True,text=True).stdout
    try: n = open(f'source/{cur}').read()
    except FileNotFoundError: continue
    raw = sum(1 for l in difflib.unified_diff(o.splitlines(), n.splitlines(), n=0)
              if l[:1] in '+-' and l[:3] not in ('+++','---'))
    on = nz.normalize(o, amap=m, is_baseline_side=True).splitlines()
    nn = nz.normalize(n, amap=m, is_baseline_side=False).splitlines()
    nm = sum(1 for l in difflib.unified_diff(on, nn, n=0)
             if l[:1] in '+-' and l[:3] not in ('+++','---'))
    tot_raw += raw; tot_norm += nm
    print(f'  {cur:38s} raw={raw:5d}  normalised={nm:5d}')
print(f'TOTAL raw={tot_raw}  normalised={tot_norm}')
assert tot_norm < tot_raw, 'normalisation must reduce the diff'
assert tot_norm > 0, 'a zero normalised diff would mean the normaliser ate everything'
"
```
Expected: a substantial reduction, and a **nonzero** remainder. A normalised total of zero would mean the normaliser is eating real changes — that assertion is deliberate.

- [ ] **Step 6: Stage and report (do not commit)**

```bash
git add build/normalize_for_diff.py build/tests/test_normalize_for_diff.py
```
Report both totals. A human commits.

---

### Task 3: Baseline-aware redline

**Files:**
- Modify: `build/build-redline-full.sh:72-82` (the staging loop)
- Create: `build/redline_resolve.py`
- Test: `build/tests/test_redline_resolve.py`

**Interfaces:**
- Consumes: `adoption_map.load()`, `normalize_for_diff.normalize()`.
- Produces: CLI `python3 build/redline_resolve.py <current-basename> <old-ver> <out-old-path> [--baseline]`, exiting 0 on success, 3 when the article is new at this adoption (caller marks the whole body added), and nonzero on an unmapped file.

**Why:** The existing loop (`build-redline-full.sh:72-82`) resolves the old side by identical filename and, on failure, writes an empty file and prints a note — which is exactly how the whole Code would render as new against the baseline.

**AMENDED 2026-08-24 after Task 2 (spec §1.2b).** The resolver must ALSO honour
`adoption-map.json`'s `not_text_comparable` map. `article-02-prefatory.md` is 125 lines where its
baseline counterpart was 2,444 — Article 2's district standards moved into `article-02.typ`. A text
diff would mark ~2,319 lines DELETED, reading in a Town Meeting packet as though the Town deleted
all its district standards. For such an article the resolver must exit **4**, and the caller renders
it UNMARKED (old side == new side), exactly as every other native figure in this redline is handled.
Add a test asserting exit 4 for `article-02-prefatory.md` and that the rendered article carries no
marks.

- [ ] **Step 1: Write the failing test**

```python
# build/tests/test_redline_resolve.py
"""The old-side resolver for a baseline redline.

The bug this prevents: build-redline-full.sh's loop writes an EMPTY old-side
when `git show <old>:source/<same-name>` fails, so a renamed article renders as
100% new with only a console note. Against v0.1-baseline that is 8 of 9 files.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
RESOLVE = REPO / "build" / "redline_resolve.py"


def run(*args):
    return subprocess.run([sys.executable, str(RESOLVE), *args],
                          capture_output=True, text=True, cwd=REPO)


def test_a_renamed_article_resolves_to_real_baseline_content(tmp_path):
    out = tmp_path / "old.md"
    r = run("article-08-administration.md", "v0.1-baseline", str(out), "--baseline")
    assert r.returncode == 0, r.stderr
    text = out.read_text()
    assert len(text) > 1000, "should contain the baseline Administration article"
    assert "ADMINISTRATION" in text.upper()


def test_article_3_reports_new_rather_than_empty_silence(tmp_path):
    out = tmp_path / "old.md"
    r = run("article-03-streets-roads-driveways.md", "v0.1-baseline", str(out), "--baseline")
    assert r.returncode == 3, "new-at-adoption must be its own exit code"
    assert "new at this adoption" in (r.stdout + r.stderr).lower()


def test_an_unmapped_article_fails_loudly(tmp_path):
    out = tmp_path / "old.md"
    r = run("article-99-invented.md", "v0.1-baseline", str(out), "--baseline")
    assert r.returncode not in (0, 3), "an unmapped file must not succeed"
    assert "adoption-map.json" in (r.stdout + r.stderr)


def test_without_baseline_flag_it_uses_the_same_filename(tmp_path):
    """Draft-to-draft redlines keep today's behaviour untouched."""
    out = tmp_path / "old.md"
    r = run("article-08-administration.md", "v0.23-draft", str(out))
    assert r.returncode == 0, r.stderr
    assert len(out.read_text()) > 1000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest build/tests/test_redline_resolve.py -q`
Expected: FAIL — the script does not exist

- [ ] **Step 3: Write the resolver**

```python
#!/usr/bin/env python3
"""Resolve the OLD side of one article's redline diff, and normalise both sides.

Exit codes:
  0  wrote the old-side file
  3  the article is NEW at this adoption -- caller writes an empty old side
     DELIBERATELY (whole body marked added), which is correct here and only here
  1  the article is not in adoption-map.json -- refuse rather than render as new

Draft-to-draft redlines (no --baseline) keep the historical behaviour exactly:
same filename at the old tag, no map, no normalisation.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402
import normalize_for_diff as nz  # noqa: E402

REPO = BUILD.parent


def git_show(ref: str, path: str) -> str | None:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("basename")
    ap.add_argument("old_ver")
    ap.add_argument("out_path")
    ap.add_argument("--baseline", action="store_true",
                    help="resolve through adoption-map.json and normalise both sides")
    a = ap.parse_args()

    if not a.baseline:
        text = git_show(a.old_ver, f"source/{a.basename}")
        if text is None:
            return 3
        Path(a.out_path).write_text(text)
        return 0

    amap = adoption_map.load()
    try:
        base = amap.baseline_path_for(a.basename)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if base is None:
        print(f"{a.basename}: new at this adoption — whole body will be marked added")
        return 3

    text = git_show(a.old_ver, f"source/{base}")
    if text is None:
        print(f"{a.basename}: adoption-map.json points at {base!r}, which does not "
              f"exist at {a.old_ver}. Fix the map.", file=sys.stderr)
        return 1

    Path(a.out_path).write_text(nz.normalize(text, amap=amap, is_baseline_side=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest build/tests/test_redline_resolve.py -q`
Expected: PASS, 4 tests

- [ ] **Step 5: Wire it into the redline script**

In `build/build-redline-full.sh`, replace the staging loop body (currently lines 72–82) with:

```bash
BASELINE_FLAG=""
if [ "${ADOPTION_BASELINE:-0}" = "1" ]; then BASELINE_FLAG="--baseline"; fi

shopt -s nullglob
n=0
for nf in "$STAGE"/article-*.md; do
  base="$(basename "$nf")"
  set +e
  python3 "$REPO_ROOT/build/redline_resolve.py" "$base" "$OLD_V" "$OLDTMP" $BASELINE_FLAG
  rc=$?
  set -e
  case "$rc" in
    0) ;;
    3) : > "$OLDTMP"
       echo "  ($base is new since $OLD_V — whole body marked as added)" ;;
    *) echo "redline: could not resolve the old side for $base (exit $rc)." >&2
       exit 1 ;;
  esac
  # In baseline mode the NEW side is normalised too, so the two sides are
  # compared on equal terms. is_baseline_side=False -- the current side is
  # never renumbered.
  if [ -n "$BASELINE_FLAG" ]; then
    python3 - "$nf" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, "build")
import adoption_map, normalize_for_diff as nz
p = Path(sys.argv[1])
p.write_text(nz.normalize(p.read_text(), amap=adoption_map.load(), is_baseline_side=False))
PYEOF
  fi
  python3 "$REDLINE_PY" "$OLDTMP" "$nf" "$nf" --source
  n=$((n + 1))
done
```

- [ ] **Step 6: Verify a draft-to-draft redline is unchanged**

Run: `REDLINE_OUT=/tmp/rl-check bash build/build-redline-full.sh v0.24-draft v0.23-draft "August 24, 2026"`
Expected: completes; page count 117 as in the shipped v0.24 redline. This proves the wiring did not disturb existing behaviour.

- [ ] **Step 7: Stage and report (do not commit)**

```bash
git add build/redline_resolve.py build/tests/test_redline_resolve.py build/build-redline-full.sh
```

---

### Task 4: Three-mode cover chrome

**Files:**
- Modify: `build/build-cover.py:52` (signature), `:65-90` (the banner block)
- Test: `build/tests/test_cover_modes.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `build_cover(baseline_pdf, out_pdf, version, date_str, caveat=None, mode="draft", event_date=None)` where `mode` is `"draft" | "meeting" | "adopted"`. `event_date` is the Town Meeting date in `meeting` mode and the adoption date in `adopted` mode.

**Why:** Spec §4. The cover currently hardcodes `INTEGRATED DRAFT — NOT ADOPTED` and `For review only — not a certified copy.`

- [ ] **Step 1: Write the failing test**

```python
# build/tests/test_cover_modes.py
"""The cover's three states.

The adopted cover must not carry draft language, and the meeting cover must
still say NOT YET ADOPTED -- the vote has not happened when it is produced.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "build"))
BASELINE = REPO / "docs" / "Newcastle Core Zoning Code.pdf"

import pymupdf  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("build_cover", REPO / "build" / "build-cover.py")
build_cover_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_cover_mod)


def cover_text(tmp_path, **kw):
    out = tmp_path / "cover.pdf"
    build_cover_mod.build_cover(str(BASELINE), str(out), kw.pop("version"),
                                kw.pop("date_str"), **kw)
    return pymupdf.open(out)[0].get_text()


def test_draft_mode_is_unchanged(tmp_path):
    t = cover_text(tmp_path, version="v0.24-draft", date_str="August 24, 2026")
    assert "INTEGRATED DRAFT" in t
    assert "NOT ADOPTED" in t


def test_meeting_mode_says_not_yet_adopted(tmp_path):
    t = cover_text(tmp_path, version="v1.0", date_str="August 24, 2026",
                   mode="meeting", event_date="March 15, 2027")
    assert "TOWN MEETING EDITION" in t
    assert "NOT YET ADOPTED" in t
    assert "March 15, 2027" in t


def test_adopted_mode_carries_no_draft_language(tmp_path):
    t = cover_text(tmp_path, version="v1.0", date_str="March 15, 2027",
                   mode="adopted", event_date="March 15, 2027")
    upper = t.upper()
    for banned in ("INTEGRATED DRAFT", "NOT ADOPTED", "NOT YET ADOPTED",
                   "FOR REVIEW ONLY", "TOWN MEETING EDITION"):
        assert banned not in upper, banned
    assert "March 15, 2027" in t


def test_adopted_mode_still_masks_the_clerk_attestation(tmp_path):
    """The masked signature block is a legal certification of the ORIGINAL
    adopted code. It must stay masked in every mode -- an adopted amendment is
    not the same document the clerk attested."""
    t = cover_text(tmp_path, version="v1.0", date_str="March 15, 2027",
                   mode="adopted", event_date="March 15, 2027")
    assert "Attested" not in t
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest build/tests/test_cover_modes.py -q`
Expected: FAIL — `build_cover() got an unexpected keyword argument 'mode'`

- [ ] **Step 3: Implement the modes**

In `build/build-cover.py`, change the signature and replace the banner block:

```python
def build_cover(baseline_pdf, out_pdf, version, date_str, caveat=None,
                mode="draft", event_date=None):
    """mode: 'draft' | 'meeting' | 'adopted'.  See build/ADOPTION-SPEC.md §4.

    The clerk attestation is masked in EVERY mode (see module docstring): it
    certifies the originally adopted code, not an amendment to it.
    """
```

Then, in place of the current fixed three `insert_textbox` calls:

```python
    BANNERS = {
        "draft": (
            "INTEGRATED DRAFT — NOT ADOPTED",
            f"{version}  ·  includes proposed Article 3: Thoroughfares",
            f"Generated {date_str} from the adopted Core Zoning Code "
            f"(amended through March 24, 2025).\nFor review only — not a certified copy.",
        ),
        "meeting": (
            "TOWN MEETING EDITION — NOT YET ADOPTED",
            f"{version}  ·  for adoption at Town Meeting, {event_date}",
            f"Frozen {date_str}. The text put before the voters.\n"
            f"Not a certified copy.",
        ),
        "adopted": (
            None,
            f"{version}  ·  Adopted {event_date}",
            f"Adopted {event_date}, amending the Core Zoning Code "
            f"adopted November 3, 2020.",
        ),
    }
    if mode not in BANNERS:
        raise ValueError(f"unknown cover mode {mode!r}")
    if mode in ("meeting", "adopted") and not event_date:
        raise ValueError(f"mode {mode!r} requires event_date")

    headline, line2, line3 = BANNERS[mode]

    if headline is not None:
        page.draw_rect(bar, color=None, fill=ARTICLE_BLUE)
        page.insert_textbox(
            fitz.Rect(bar.x0, bar.y0 + 14, bar.x1, bar.y0 + 52), headline,
            fontfile=BARLOW_BOLD, fontname="barlow-bold", fontsize=20, color=WHITE,
            align=fitz.TEXT_ALIGN_CENTER,
        )
        page.insert_textbox(
            fitz.Rect(bar.x0 + 8, bar.y0 + 56, bar.x1 - 8, bar.y0 + 86), line2,
            fontfile=BARLOW_MED, fontname="barlow-med", fontsize=12, color=WHITE,
            align=fitz.TEXT_ALIGN_CENTER,
        )
    else:
        # Adopted: no blue bar. The version/date line sits in the white space, in
        # article blue on white, so the page reads as a code rather than a notice.
        page.insert_textbox(
            fitz.Rect(bar.x0, bar.y0 + 30, bar.x1, bar.y0 + 62), line2,
            fontfile=BARLOW_MED, fontname="barlow-med", fontsize=13,
            color=ARTICLE_BLUE, align=fitz.TEXT_ALIGN_CENTER,
        )

    page.insert_textbox(
        fitz.Rect(96, bar.y1 + 10, w - 96, bar.y1 + 48), line3,
        fontfile=BARLOW_REG, fontname="barlow-reg", fontsize=9.5, color=GRAY,
        align=fitz.TEXT_ALIGN_CENTER,
    )
```

Then extend the CLI at the bottom of the file to accept `--mode` and `--event-date`, keeping the existing positional arguments so `build-full-czc.sh:274` continues to work unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest build/tests/test_cover_modes.py -q`
Expected: PASS, 4 tests

- [ ] **Step 5: Verify the existing draft build is unaffected**

Run: `OUT_DIR=/tmp/czc-cover-check bash build/build-full-czc.sh v0.24-draft "August 24, 2026"`
Expected: 117 pp, cover still reads `INTEGRATED DRAFT — NOT ADOPTED`.

- [ ] **Step 6: Stage and report (do not commit)**

```bash
git add build/build-cover.py build/tests/test_cover_modes.py
```

---

### Task 5: Footer and exhibit-banner modes

**Files:**
- Modify: `build/build-full-czc.sh:210,223,229` (the `footer-date` overrides)
- Modify: `source/street-type-inventory.typ`, `source/street-type-map.typ` (banner selection)
- Test: `build/tests/test_footer_modes.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `build-full-czc.sh` honours `ADOPTION_MODE` ∈ `draft|meeting|adopted` and `ADOPTION_EVENT_DATE`, defaulting to `draft` so every existing invocation is unchanged.

**Why:** Spec §4. The footer currently hardcodes `Draft $VERSION` in three places. The exhibit banner currently comes from `inventory.json`'s `_meta.banner` and says "not yet reviewed or adopted", which is false once adopted — but the provenance note must stay, because the district geometry is still a ~0.77-IoU approximation (spec §4.2).

**The Meeting edition's exhibits keep their own not-yet-adopted marker** rather than relying on the cover: Exhibit 3.1 runs five pages and 3.2 is a full-page map, and those are exactly the pages someone photocopies detached from the cover that carries the status.

- [ ] **Step 1: Write the failing test**

```python
# build/tests/test_footer_modes.py
"""Footer text per adoption state, and the exhibit banner rules."""
import os
import subprocess
import sys
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent.parent


def build(tmp_path, version, date_str, **env):
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    e = dict(os.environ, OUT_DIR=str(out), **env)
    subprocess.run(["bash", "build/build-full-czc.sh", version, date_str],
                   cwd=REPO, env=e, check=True, capture_output=True)
    pdf = next(out.glob("*.pdf"))
    d = pymupdf.open(pdf)
    return "\n".join(p.get_text() for p in d)


def test_draft_footer_is_unchanged(tmp_path):
    t = build(tmp_path, "v0.24-draft", "August 24, 2026")
    assert "Draft v0.24-draft" in t


def test_adopted_footer_carries_the_adoption_date(tmp_path):
    t = build(tmp_path, "v1.0", "March 15, 2027",
              ADOPTION_MODE="adopted", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "Adopted: March 15, 2027" in t
    assert "Draft v" not in t


def test_adopted_exhibits_keep_provenance_but_drop_draft_language(tmp_path):
    t = build(tmp_path, "v1.0", "March 15, 2027",
              ADOPTION_MODE="adopted", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "approximate" in t.lower(), "the provenance note must survive"
    assert "not yet reviewed or adopted" not in t.lower()


def test_meeting_exhibits_carry_their_own_not_yet_adopted_marker(tmp_path):
    """Exhibit 3.1 is five pages and 3.2 a full-page map; both get photocopied
    away from the cover that carries the status."""
    t = build(tmp_path, "v1.0", "August 24, 2026",
              ADOPTION_MODE="meeting", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "not yet adopted" in t.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest build/tests/test_footer_modes.py -q`
Expected: FAIL — adopted footer assertion fails; the build still prints `Draft v1.0`

- [ ] **Step 3: Implement the footer mode**

Near the top of `build/build-full-czc.sh`, after `VERSION`/`DATE_STR` are read:

```bash
# Adoption state. Defaults to 'draft', so every existing invocation is unchanged.
# See build/ADOPTION-SPEC.md §4.
ADOPTION_MODE="${ADOPTION_MODE:-draft}"
ADOPTION_EVENT_DATE="${ADOPTION_EVENT_DATE:-}"
case "$ADOPTION_MODE" in
  draft)    FOOTER_TEXT="Draft $VERSION" ;;
  meeting)  FOOTER_TEXT="Town Meeting Edition $VERSION" ;;
  adopted)  FOOTER_TEXT="Adopted: $ADOPTION_EVENT_DATE" ;;
  *) echo "unknown ADOPTION_MODE '$ADOPTION_MODE'" >&2; exit 1 ;;
esac
if [ "$ADOPTION_MODE" != "draft" ] && [ -z "$ADOPTION_EVENT_DATE" ]; then
  echo "ADOPTION_MODE=$ADOPTION_MODE requires ADOPTION_EVENT_DATE" >&2; exit 1
fi
```

Then replace the three hardcoded strings at lines 210, 223 and 229 with `$FOOTER_TEXT`, and pass `--mode`/`--event-date` through to `build-cover.py` at line 274.

- [ ] **Step 4: Implement the exhibit banner selection**

Both `source/street-type-inventory.typ` and `source/street-type-map.typ` read `banner` from the data. Add an input that overrides it:

```typst
// Adoption state, passed by build-full-czc.sh. The DRAFT banner asserts "not yet
// reviewed or adopted", which is false once adopted -- but the provenance note
// must survive in every mode: the district geometry is still an approximation
// (ADOPTION-SPEC.md §4.2). The MEETING banner carries its own not-yet-adopted
// marker because these pages get separated from the cover.
#let adoption_mode = sys.inputs.at("adoption_mode", default: "draft")
#let PROVENANCE = "Types derived from a trace of the District Map; recorded right-of-way, traveled way and other field values are approximate."
#let banner = if adoption_mode == "adopted" {
  PROVENANCE
} else if adoption_mode == "meeting" {
  "NOT YET ADOPTED — for adoption at Town Meeting. " + PROVENANCE
} else {
  data.at("_meta", default: (:)).at("banner", default: "")
}
```

Pass `--input adoption_mode=$ADOPTION_MODE` alongside the existing `--input footer_date=` in `build-full-czc.sh` and `build-standalone.sh`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest build/tests/test_footer_modes.py -q`
Expected: PASS, 4 tests

- [ ] **Step 6: Stage and report (do not commit)**

```bash
git add build/build-full-czc.sh source/street-type-inventory.typ source/street-type-map.typ build/tests/test_footer_modes.py
```

---

### Task 6: Version-state rules

**Files:**
- Create: `build/version_state.py`
- Modify: `build/build-full-czc.sh` (refusal), `build/build-standalone.sh` (refusal)
- Test: `build/tests/test_version_state.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `version_state.parse(v: str) -> Version` with fields `major:int, minor:int, is_draft:bool`; `version_state.is_adoption_version(v) -> bool`; CLI `python3 build/version_state.py --require adoption|draft <version>` exiting 0/1.

**Why:** Spec §2.1 and §6.1. "A whole number means adopted law" is worth nothing as a convention and everything as a refusal.

- [ ] **Step 1: Write the failing test**

```python
# build/tests/test_version_state.py
"""Whole numbers are adopted law; decimals are drafts. Enforced, not assumed."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "build"))

import version_state as vs  # noqa: E402


def test_parses_a_draft():
    v = vs.parse("v0.24-draft")
    assert (v.major, v.minor, v.is_draft) == (0, 24, True)


def test_parses_an_adoption_version():
    v = vs.parse("v1.0")
    assert (v.major, v.minor, v.is_draft) == (1, 0, False)


def test_adoption_version_must_be_whole():
    assert vs.is_adoption_version("v1.0") is True
    assert vs.is_adoption_version("v2.0") is True
    assert vs.is_adoption_version("v1.1") is False
    assert vs.is_adoption_version("v0.24-draft") is False
    assert vs.is_adoption_version("v1.0-draft") is False


def test_baseline_tag_is_not_an_adoption_version():
    """v0.1-baseline is a transcription of the previously adopted code, not an
    adoption produced by this tool."""
    assert vs.is_adoption_version("v0.1-baseline") is False


def test_cli_refuses_a_decimal_for_adoption():
    r = subprocess.run([sys.executable, "build/version_state.py",
                        "--require", "adoption", "v1.1-draft"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0
    assert "whole" in (r.stdout + r.stderr).lower()


def test_cli_refuses_a_whole_number_for_a_draft():
    r = subprocess.run([sys.executable, "build/version_state.py",
                        "--require", "draft", "v1.0"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest build/tests/test_version_state.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'version_state'`

- [ ] **Step 3: Write the module**

```python
#!/usr/bin/env python3
"""Version-string rules for the CZC release lifecycle.

  vX.Y-draft   a draft            (decimal, -draft suffix)
  vN.0         adopted law        (whole number, no suffix)

"A whole number means adopted law" is only worth something if it cannot be
faked, so this is a refusal rather than a convention (ADOPTION-SPEC.md §6.1).
v0.1-baseline is deliberately NOT an adoption version: it is a transcription of
the previously adopted Code, not an adoption this tool produced.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass

_RE = re.compile(r"^v(\d+)\.(\d+)(?:-(draft|baseline))?$")


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    is_draft: bool
    suffix: str | None


def parse(v: str) -> Version:
    m = _RE.match(v.strip())
    if not m:
        raise ValueError(f"{v!r} is not a recognised version (expected vX.Y[-draft])")
    return Version(int(m.group(1)), int(m.group(2)),
                   m.group(3) == "draft", m.group(3))


def is_adoption_version(v: str) -> bool:
    try:
        p = parse(v)
    except ValueError:
        return False
    return p.minor == 0 and p.suffix is None and p.major >= 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require", choices=("adoption", "draft"), required=True)
    ap.add_argument("version")
    a = ap.parse_args()
    if a.require == "adoption":
        if not is_adoption_version(a.version):
            print(f"{a.version!r} is not an adoption version. An adoption must "
                  f"carry a WHOLE number (v1.0, v2.0) with no suffix — a whole "
                  f"number means adopted law.", file=sys.stderr)
            return 1
    else:
        if is_adoption_version(a.version):
            print(f"{a.version!r} is a whole number, which is reserved for adopted "
                  f"law. Use a decimal draft version (v1.1-draft).", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest build/tests/test_version_state.py -q`
Expected: PASS, 6 tests

- [ ] **Step 5: Wire the refusal into the draft builders**

In `build/build-full-czc.sh`, immediately after `ADOPTION_MODE` is resolved:

```bash
if [ "$ADOPTION_MODE" = "draft" ]; then
  python3 "$REPO_ROOT/build/version_state.py" --require draft "$VERSION" || exit 1
fi
```

Add the same guard to `build/build-standalone.sh` after its version argument is read.

- [ ] **Step 6: Verify the guard fires and does not fire**

Run:
```bash
OUT_DIR=/tmp/vs-check bash build/build-full-czc.sh v1.0 "March 15, 2027" ; echo "exit=$?"
OUT_DIR=/tmp/vs-check2 bash build/build-full-czc.sh v0.24-draft "August 24, 2026" >/dev/null; echo "exit=$?"
```
Expected: first refuses (nonzero, message about whole numbers); second succeeds (0).

- [ ] **Step 7: Stage and report (do not commit)**

```bash
git add build/version_state.py build/tests/test_version_state.py build/build-full-czc.sh build/build-standalone.sh
```

---

### Task 7: `build-adoption.sh` — the freeze

**Files:**
- Create: `build/build-adoption.sh`
- Test: `build/tests/test_build_adoption.py`

**Interfaces:**
- Consumes: `version_state.py --require adoption`; `ADOPTION_MODE=meeting` in `build-full-czc.sh`; `ADOPTION_BASELINE=1` in `build-redline-full.sh`; `adoption_map.load().baseline_version`.
- Produces: `releases/<version>/` containing the Meeting-edition integrated PDF+md, the baseline redline PDF, the standalone Article 3 PDF+md, and a Summary skeleton md.

**Why:** Spec §3.3.

- [ ] **Step 1: Write the failing test**

```python
# build/tests/test_build_adoption.py
"""The freeze produces a complete Town Meeting packet, and refuses a bad version."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


def test_refuses_a_decimal_version(tmp_path):
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.1-draft", "March 15, 2027"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0
    assert "whole" in (r.stdout + r.stderr).lower()


def test_requires_a_meeting_date():
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0


def test_prints_the_substantive_change_breakdown():
    """The 243 lines going to the voters must be reviewable BEFORE the packet
    exists, not discovered at the meeting (ADOPTION-SPEC.md §7)."""
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0", "March 15, 2027",
                        "--dry-run"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "substantive change" in out.lower()
    assert "article-09-definitions.md" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest build/tests/test_build_adoption.py -q`
Expected: FAIL — script does not exist

- [ ] **Step 3: Write the script**

```bash
#!/usr/bin/env bash
# Freeze a draft into a TOWN MEETING EDITION. See build/ADOPTION-SPEC.md.
#
# Produces, into releases/<version>/:
#   1. the Town Meeting edition (integrated PDF + md)
#   2. the redline vs the PREVIOUSLY ADOPTED Code (mapped + normalised)
#   3. the standalone Article 3
#   4. a Summary of Changes skeleton, to be written by hand in plain language
#
# It does NOT stamp an adoption date. The vote has not happened.
#
# Usage:  build-adoption.sh <version> <meeting-date> [--dry-run]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
MEETING_DATE="${2:-}"
DRY_RUN=0
[ "${3:-}" = "--dry-run" ] && DRY_RUN=1

if [ -z "$VERSION" ] || [ -z "$MEETING_DATE" ]; then
  echo "usage: build-adoption.sh <version> <meeting-date> [--dry-run]" >&2
  exit 1
fi

python3 "$REPO_ROOT/build/version_state.py" --require adoption "$VERSION" || exit 1

BASELINE="$(python3 -c "
import sys; sys.path.insert(0,'$REPO_ROOT/build')
import adoption_map; print(adoption_map.load().baseline_version)")"

echo "Freezing $VERSION for Town Meeting, $MEETING_DATE"
echo "Previously adopted version: $BASELINE"
echo

# --- The substantive-change breakdown, printed BEFORE anything is built. -----
# These are the changes the voters will adopt. They accumulated across 24 drafts
# and have never been reviewed as a set.
echo "Substantive changes vs $BASELINE (formatting and renumbering suppressed):"
python3 - <<PYEOF
import sys, subprocess, difflib
sys.path.insert(0, "$REPO_ROOT/build")
import adoption_map, normalize_for_diff as nz
m = adoption_map.load()
total = 0
for cur, base in sorted(m.files.items()):
    if base is None:
        print(f"  {cur:40s}   NEW at this adoption")
        continue
    o = subprocess.run(["git", "-C", "$REPO_ROOT", "show", f"{m.baseline_version}:source/{base}"],
                       capture_output=True, text=True).stdout
    try:
        n = open(f"$REPO_ROOT/source/{cur}").read()
    except FileNotFoundError:
        continue
    on = nz.normalize(o, amap=m, is_baseline_side=True).splitlines()
    nn = nz.normalize(n, amap=m, is_baseline_side=False).splitlines()
    c = sum(1 for l in difflib.unified_diff(on, nn, n=0)
            if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    total += c
    print(f"  {cur:40s} {c:5d} lines")
print(f"  {'TOTAL':40s} {total:5d} substantive changed lines")
PYEOF
echo

if [ "$DRY_RUN" = "1" ]; then
  echo "(dry run — nothing built)"
  exit 0
fi

OUT="$REPO_ROOT/releases/$VERSION"
mkdir -p "$OUT"

# 1. Town Meeting edition
ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-full-czc.sh" "$VERSION" "$MEETING_DATE"

# 2. Redline vs the previously adopted Code
ADOPTION_BASELINE=1 ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-redline-full.sh" "$VERSION" "$BASELINE" "$MEETING_DATE"

# 3. Standalone Article 3
ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="$MEETING_DATE" \
  bash "$REPO_ROOT/build/build-standalone.sh" 3 "$VERSION" "$MEETING_DATE"

# 4. Summary skeleton — written by hand, in plain language, no file/path refs.
SUMMARY="$OUT/Summary of Changes $VERSION.md"
if [ ! -f "$SUMMARY" ]; then
  cat > "$SUMMARY" <<EOF
# Summary of Changes — $VERSION

**For adoption at Town Meeting, $MEETING_DATE.** Changes are stated against the
Core Zoning Code adopted November 3, 2020 and amended through March 24, 2025.

<!-- Write this by hand, in plain language: by section, by road name, by Type.
     No file, path or script references. Describe the figure and table changes
     in prose — a redline marks wording only, so the Inventory and the Type Map
     changes will not appear as marked text. -->

## What is new

## What changed

## What did not change

No standard, dimension or requirement was made stricter anywhere in this
release except as described above.
EOF
  echo "Wrote Summary skeleton: $SUMMARY"
fi

echo
echo "Town Meeting edition $VERSION built into releases/$VERSION/"
echo "NEXT: write the Summary by hand, then tag $VERSION when the packet is final."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest build/tests/test_build_adoption.py -q`
Expected: PASS, 3 tests

- [ ] **Step 5: Run the dry run for real and read the output**

Run: `bash build/build-adoption.sh v1.0 "March 15, 2027" --dry-run`
Expected: a per-article breakdown totalling roughly 243 substantive lines, with `article-03-streets-roads-driveways.md` shown as NEW. Read it — this is the set of changes the voters would be adopting.

- [ ] **Step 6: Stage and report (do not commit)**

```bash
git add build/build-adoption.sh build/tests/test_build_adoption.py
```

---

### Task 8: `build-adopted.sh` — after the vote

**Files:**
- Create: `build/build-adopted.sh`
- Test: `build/tests/test_build_adopted.py`

**Interfaces:**
- Consumes: `version_state.py --require adoption`; `ADOPTION_MODE=adopted`; the tag created at the end of Task 7.
- Produces: `releases/<version>-adopted/` containing the adopted integrated PDF + md.

**Why:** Spec §3.4 and §6.2–6.3. Two properties matter more than anything else in this task:

1. **It renders from the tagged Meeting-edition source, not the working tree.** The adopted document then structurally cannot contain anything the voters did not see.
2. **The draft-residue gate targets the chrome strings, not the bare word "draft".** The Code's own adopted text reads *"The Planning Board, or its designnee, drafts the official map of the Town of Newcastle."* A blanket search would fail on the Town's own words, and the natural fix under time pressure — deleting the gate — is worse than never having had it.

- [ ] **Step 1: Write the failing test**

```python
# build/tests/test_build_adopted.py
"""The adopted edition: same content as the voters saw, different chrome only."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "build"))


def test_refuses_a_decimal_version():
    r = subprocess.run(["bash", "build/build-adopted.sh", "v1.1-draft", "March 15, 2027"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0


def test_refuses_when_the_meeting_edition_tag_does_not_exist():
    r = subprocess.run(["bash", "build/build-adopted.sh", "v9.0", "March 15, 2027"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0
    assert "tag" in (r.stdout + r.stderr).lower()


def test_residue_gate_targets_chrome_not_the_word_draft():
    """The Code's own text says 'the Planning Board ... drafts the official map'.
    A gate that fails on that would be deleted the first time it fired."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "residue", REPO / "build" / "adopted_residue.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    ok_text = "The Planning Board, or its designnee, drafts the official map."
    assert mod.find_residue(ok_text) == []

    bad = "INTEGRATED DRAFT — NOT ADOPTED"
    assert mod.find_residue(bad) != []

    bad2 = "Draft v1.0"
    assert mod.find_residue(bad2) != []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest build/tests/test_build_adopted.py -q`
Expected: FAIL — neither script exists

- [ ] **Step 3: Write the residue checker**

```python
#!/usr/bin/env python3
"""Draft-chrome residue check for an adopted document.

THE GATE TARGETS CHROME PHRASES, NOT THE WORD "DRAFT". The Code's own adopted
text reads "The Planning Board, or its designnee, drafts the official map of the
Town of Newcastle." A blanket search for "draft" fails on the Town's own words,
and the natural fix under time pressure is to delete the gate -- which is worse
than never having had it.

It also asserts the substantive occurrences are STILL PRESENT: a substitution
that damaged the Code's own text would be a far worse failure than a leftover
banner.
"""
from __future__ import annotations

import sys

CHROME = (
    "INTEGRATED DRAFT",
    "TOWN MEETING EDITION",
    "NOT YET ADOPTED",
    "NOT ADOPTED",
    "For review only",
    "Draft v",
)

# Substantive uses of the word that MUST survive untouched.
MUST_SURVIVE = ("drafts the official map",)


def find_residue(text: str) -> list[str]:
    upper = text.upper()
    return [c for c in CHROME if c.upper() in upper]


def find_damage(text: str) -> list[str]:
    return [s for s in MUST_SURVIVE if s.lower() not in text.lower()]


def main() -> int:
    text = sys.stdin.read()
    residue = find_residue(text)
    damage = find_damage(text)
    for r in residue:
        print(f"DRAFT CHROME SURVIVED in the adopted document: {r!r}", file=sys.stderr)
    for d in damage:
        print(f"SUBSTANTIVE TEXT DAMAGED — missing: {d!r}", file=sys.stderr)
    return 1 if (residue or damage) else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Write the adoption script**

```bash
#!/usr/bin/env bash
# Stamp a Town Meeting edition as ADOPTED, after the vote. See ADOPTION-SPEC.md §3.4.
#
# It renders from the TAGGED meeting-edition source, never the working tree, so
# the adopted document structurally cannot contain anything the voters did not
# see. It then asserts the body is byte-identical to what was voted on.
#
# Usage:  build-adopted.sh <version> <adoption-date>
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
ADOPTION_DATE="${2:-}"

if [ -z "$VERSION" ] || [ -z "$ADOPTION_DATE" ]; then
  echo "usage: build-adopted.sh <version> <adoption-date>" >&2
  exit 1
fi

python3 "$REPO_ROOT/build/version_state.py" --require adoption "$VERSION" || exit 1

if ! git -C "$REPO_ROOT" rev-parse -q --verify "refs/tags/$VERSION" >/dev/null; then
  echo "No tag '$VERSION'. The Town Meeting edition must be tagged before it can" >&2
  echo "be adopted — the adopted document is rendered from that tag, not from the" >&2
  echo "working tree, so that it cannot contain anything the voters did not see." >&2
  exit 1
fi

# 1. Check out the tagged source into a staging tree. The working tree is not consulted.
STAGE="$(mktemp -d)"; OUTDIR="$REPO_ROOT/releases/${VERSION}-adopted"
trap 'rm -rf "$STAGE"' EXIT
git -C "$REPO_ROOT" archive "$VERSION" source | tar -x -C "$STAGE"
mkdir -p "$OUTDIR"

# 2. Render with adopted chrome from the tagged source.
SRC_DIR="$STAGE/source" OUT_DIR="$OUTDIR" \
ADOPTION_MODE=adopted ADOPTION_EVENT_DATE="$ADOPTION_DATE" \
  bash "$REPO_ROOT/build/build-full-czc.sh" "$VERSION" "$ADOPTION_DATE"

ADOPTED_MD="$(ls "$OUTDIR"/*.md | head -1)"
ADOPTED_PDF="$(ls "$OUTDIR"/*.pdf | head -1)"
MEETING_MD="$REPO_ROOT/releases/$VERSION/$(basename "$ADOPTED_MD")"

# 3. Content-identity gate. Frontmatter is stripped: it carries footer-date,
#    which is chrome and differs by state BY DESIGN. Comparing the raw file
#    would fail every run for the one reason that does not matter.
python3 - "$MEETING_MD" "$ADOPTED_MD" <<'PYEOF'
import re, sys, hashlib
def body(p):
    t = open(p, encoding="utf-8").read()
    t = re.sub(r"(?ms)^---\n.*?^---\n", "", t)     # YAML frontmatter blocks
    return hashlib.sha256(t.encode()).hexdigest()
a, b = body(sys.argv[1]), body(sys.argv[2])
if a != b:
    print("ADOPTED BODY DIFFERS FROM THE TOWN MEETING EDITION.", file=sys.stderr)
    print(f"  meeting={a}\n  adopted={b}", file=sys.stderr)
    print("The adopted document must contain exactly what was voted on.", file=sys.stderr)
    raise SystemExit(1)
print(f"Content identity verified (body sha256 {a[:16]}…)")
PYEOF

# 4. Draft-residue gate, on the rendered PDF's extracted text.
python3 -c "
import pymupdf, sys
d = pymupdf.open(sys.argv[1])
sys.stdout.write(''.join(p.get_text() for p in d))
" "$ADOPTED_PDF" | python3 "$REPO_ROOT/build/adopted_residue.py"

echo
echo "ADOPTED edition built: $OUTDIR"
echo "Version $VERSION · adopted $ADOPTION_DATE"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest build/tests/test_build_adopted.py -q`
Expected: PASS, 3 tests

- [ ] **Step 6: Run the whole suite**

Run: `python3 -m pytest build/tests -q`
Expected: PASS, all tests across the six test files (roughly 32 tests).

- [ ] **Step 7: Verify the draft path is completely unaffected**

Run:
```bash
OUT_DIR=/tmp/final-check bash build/build-full-czc.sh v0.24-draft "August 24, 2026"
python3 -c "
import pymupdf
d = pymupdf.open('/tmp/final-check/Newcastle CZC (Integrated Draft v0.24-draft).pdf')
blank = [i+1 for i,p in enumerate(d) if not p.get_text().strip()]
print('pages:', d.page_count, 'blanks:', blank)
assert d.page_count == 117 and blank == [2]
print('DRAFT PATH UNCHANGED')"
```
Expected: `117 pages, blanks [2]`, `DRAFT PATH UNCHANGED`.

- [ ] **Step 8: Stage and report (do not commit)**

```bash
git add build/build-adopted.sh build/adopted_residue.py build/tests/test_build_adopted.py
```

Report: the full test count, the draft-path page count, and the dry-run change breakdown from Task 7.

---

## Self-review notes

**Spec coverage.** §1.1 → Tasks 1, 3. §1.2 → Task 2. §1.3 → Tasks 4, 5, 7, 8. §2 lifecycle → Tasks 7, 8. §2.1 version rules → Task 6. §3.1 → Task 1. §3.2 → Task 2. §3.3 → Task 7. §3.4 → Task 8. §3.5 baseline identity → Task 1 data. §4 chrome → Tasks 4, 5. §4.1 footer → Task 5. §4.2 exhibit banners → Task 5. §4.3 structural note → **see gap below**. §6.1 → Task 6. §6.2 → Task 8. §6.3 → Task 8. §6.4 → Tasks 2, 3, 7. §6.5 parity → Tasks 5, 8 verification steps.

**One gap, deliberately deferred.** Spec §4.3 requires the redline to open with a prose structural-changes note (Article 3 is new; every Article after 2 shifts up by one; cross-references renumbered and not individually marked). No task implements it, because it is a page of prose in the redline's front matter and the right place for it depends on how the redline cover renders — which is not settled until Task 4 lands. **Add it as Task 9 after Task 4 is reviewed**, or write it by hand into the Summary for the first adoption. It must not be forgotten: suppressing 126 renumbering marks is honest only if the reader is told once, plainly, that it happened.

**Open items from spec §7 that this plan does not close:** the stale `footer-date: "Draft v0.2-draft"` in Article 3's frontmatter (harmless — always overridden — but should be corrected); the inherited `designnee`/`extentions` typos, which are the Board's call and must not be silently fixed; and whether the adopted edition ships a standalone Article 3 at all.
