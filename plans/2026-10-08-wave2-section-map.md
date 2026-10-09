# Wave 2 — Section Renumbering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a section is inserted into or deleted from an Article, stop every later section's renumbering — its heading and every cross-reference to it — from reading as an amendment in the redline and in the packet's headline number, without ever hiding a real one.

**Architecture:** Two components from `specs/2026-10-07-release-deliverables-scope.md`, strictly sequential. **P6** derives a section map from two versions of the Code by aligning heading titles, and gates it; it is never committed and never touches the adoption map. **P7** applies that map on the OLD side only, inside `build/normalize_for_diff.py`, as a sixth narrow rule. Between them, a small pre-existing bug in the headline-number counter is fixed in its own task so P7 builds on a correct count.

**Tech Stack:** Python 3.14, pytest, git. No PDF output changes in this wave.

## Global Constraints

- **NEVER commit unless explicitly asked.** The operator has authorised this plan's commit steps; implementers commit locally, by name, on branch `wave2-section-map`. Nothing is pushed.
- **NEVER `git add -A` or `git add .`** — stage files by name, exactly as each commit step lists them.
- **Never modify anything in `docs/`.** Nothing into `releases/`.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` — **project standing rule 5**, which deliberately overrides any other attribution suggestion.
- Build tests: `python3 -m pytest build/tests -q` from the repository root. **199 tests** at the start of this wave, about 4 minutes. CI runs the same suite on the PR. **Report the count you actually see** — plan arithmetic has been stale before.
- **INVARIANT — three files are never touched by this wave:** `build/adoption-map.json`, `build/adoption_map.py`, `build/baseline_selfcheck.py`. Every task ends by proving it: `git diff --stat main -- build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py` must print nothing. This is the reason P6's map is *derived*: populating `adoption-map.json` for the next amendment makes `baseline_selfcheck.py` refuse it as "not rolled over" (reproduced: 7 articles, exit 1).
- **The module's doctrine binds every rule** (`build/normalize_for_diff.py:21-30`): every rule is narrow and separately tested in BOTH directions — it suppresses the cosmetic case AND a real change of the same shape survives. *A noisier redline is recoverable; a redline missing an amendment is not.* Over-suppression is the one unrecoverable failure.
- **Default preservation:** with no section map (`smap=None`), no `--section-map` and no `--report`, every existing call, output and test is byte-identical.
- **VACUITY — measured 2026-10-08:** all nine `source/article-0*.md` are **byte-identical to `v1.0`** (only five `.typ` files differ). So any assertion of the form "nothing changed / nothing mapped / zero lines" against the real tree passes before any code exists. **Every such assertion must sit beside a positive control in the same test** proving the code actually examined something.
- **Heading format, measured:** every `## ` line in Articles 1–8 matches `^## [0-9]+\. ` — digits, period, one space, uppercase title. Article 7 has **66** of them, numbered 1–66 without gaps; inserting one at §3 shifts §3–§66 = **64**. Article 9 has **no** headings. Sub-sections are `### x.` (single lowercase letter) and are **not** mapped in this wave.
- **Statutory citations must never be rewritten.** Measured: 15 `Section` occurrences on 13 lines, plus statutory `§` uses. The set includes two **federal** citations in Article 9 — `Public Law 75-412, 50 Stat. 888, Section 8` — which a guard limited to MRSA/M.R.S/Title/U.S.C would miss.

### Ten rulings this plan makes in writing

Each corrects or completes the scope document; reviewers should judge the code against these, not against the scope document's original wording.

1. **`selfcheck` semantics.** The scope document says the gate "applies the derived map to the old side and asserts the old tree compared against itself marks zero lines". That cannot hold for a non-empty map: applying a real renumbering to the old text rewrites references the unmodified copy still carries, so every real map would fail. The gate instead asserts **(a)** every map entry pairs an old heading and a new heading with *identical normalised titles* — which is exactly what catches an off-by-one shift — and **(b)** the map equals a fresh derivation against the same tree, entry for entry, so an added, dropped or hand-edited entry is refused. *(Amended in Task 2 fix round 1: the original (b), "deriving the old ref against itself maps nothing", could never fail — identical inputs always derive an empty map.)* `check` always verifies the tree: it has no tree-less mode, and the resolver's `--section-map` requires `--new-dir`.
2. **The containing Article is read from the text's own frontmatter** (`article-number: "N"`, present in every article file), not passed as a parameter. It cannot be wrong, and no caller's signature changes. `redline_resolve.py` therefore gains `--section-map` but not `--article`.
3. **The statutory guard is the measured set**, not the scope document's four tokens: `MRSA`, `M.R.S`, `Title`, `U.S.C`, `Public Law`, `Stat.`, `Chapter`, `Subchapter`, `CFR`, `C.F.R`, `Regulations`, within 40 characters before the reference (a 20-character window found the whole set; widening to 80 added none).
4. **An explicit `Article N Section M` / `Article N §M` bypasses the statute guard**; bare forms are guarded. Measured mixed lines carry both kinds — `23 MRSA §3026-A and Article 8 §27` — and the `Article N` prefix is decisive.
5. **Narrowness for bare references** *(amended in Task 4 fix round 1 — a third and fourth layer: a bare reference is rewritten only when NOTHING qualifies it; any `<word> <number>` directly before it, or any `of …` after it other than `of this Article`, leaves it raw. Skipping is always safe.)* **Originally two layers:** a number is rewritten only if it is a *key* in the containing Article's map **and** no statute token precedes it. The map alone is insufficient: Article 7 has 66 sections, so `§53.11` (a federal-regulations citation in Article 7) would collide with a renumbered §53.
6. **Deletion.** The scope document says a deleted section "must leave the surrounding numbers unmapped". That is wrong: sections after a deletion that keep their titles are a genuine renumbering and **are** mapped. Only the deleted section's own number is unmapped, so any reference to it stays visible as a change.
7. **"Rendered marks unchanged" is true only for headings.** `--source` never marks headings, so renumbered headings change no marks. But a shifted cross-reference in *prose* is marked without the map and suppressed with it — which is the intended effect. Tests assert the count, not the rendered marks.
8. **A retargeted reference is always shown** (decision D8). The map only ever makes two references equal when they point at title-identical content, so a reference that now points somewhere else still differs. This is a dedicated negative control.
9. **`changed_line_count`'s header filter is fixed** (found during planning, not in the scope document). It dropped every changed line whose content begins with `--` or `++`, so a deleted `---` horizontal rule was not counted in the number that goes to voters.
10. **No hand-entry mechanism this wave.** Below a 50% similarity floor `derive` fails closed — exit 2, no map written. How an operator supplies a hand entry is the release driver's decision (P13).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `build/section_map.py` | **New.** Derive a section map from two trees; `check` its provenance; `selfcheck` its correctness | Create (Tasks 1–2) |
| `build/tests/section_fixtures.py` | **New.** Builds trees where something *did* move, so the tests can fail | Create (Task 1) |
| `build/tests/test_section_map.py` | **New.** Derivation, provenance, the gates | Create (Task 1), extend (Task 2) |
| `build/normalize_for_diff.py` | The normaliser | Modify — fix the counter (Task 3); Rule 6 + `smap` (Task 4); `report()` covers every rule (Task 5) |
| `build/tests/test_normalize_for_diff.py` | Normaliser tests | Extend (Tasks 3, 4, 5) |
| `build/redline_resolve.py` | Old-side resolution | Modify — opt-in `--section-map` and `--report` (Task 5) |
| `build/tests/test_redline_resolve.py` | Resolution tests | Extend (Task 5) |

**Not touched, by design:** `build/adoption-map.json`, `build/adoption_map.py`, `build/baseline_selfcheck.py`, and `build/ADOPTION-SPEC.md` (its normaliser description is updated in P18).

---

## Task 1: Derive a section map

**Files:**
- Create: `build/section_map.py`
- Create: `build/tests/section_fixtures.py`
- Create: `build/tests/test_section_map.py`

**Interfaces:**
- Consumes: `redline_resolve.git_show(ref: str, path: str) -> str | None` (`build/redline_resolve.py:37-40`), imported **lazily** inside a function — `redline_resolve.py` will import this module in Task 5, and a top-level import would be circular.
- Produces:
  - `section_map.derive(old_ref: str, new_dir: Path = DEFAULT_NEW_DIR) -> dict` — the map document; raises `section_map.BelowFloor` below the similarity floor.
  - `section_map.derive_article(old_text: str, new_text: str) -> tuple[dict[int, int], int, list[str], list[str]]` — `(mapping, matched, old_unmatched, new_unmatched)`.
  - `section_map.load(path) -> dict[int, dict[int, int]]` — `{old article: {old section: new section}}`, the shape Task 4's `smap` takes.
  - `section_map.headings(text) -> list[tuple[int, str]]`, `section_map.article_number(text) -> int | None`, `section_map.tree_hash(new_dir) -> str`.
  - CLI: `python3 build/section_map.py derive <old-ref> [--new-dir DIR] --out PATH` — exit 0 on success, **2** below the floor with nothing written.
  - The map document: `{"for_old_ref": str, "for_new_tree": sha256-hex, "articles": {"7": {"3": 4, …}}, "matched": {"7": 66, …}, "unmapped_old": {…}, "unmapped_new": {…}}`.

- [ ] **Step 1: Write the fixture helpers**

Create `build/tests/section_fixtures.py`:

```python
"""Trees in which something DID move, for the section-map tests.

Every source/article-*.md is byte-identical to v1.0 (measured 2026-10-08), so a
test that derives v1.0 against the real tree can only ever see "nothing moved",
and passes whether or not the code works. These helpers build trees where a
section was inserted, deleted or retitled, so the assertions can fail.
"""
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_H2 = re.compile(r"^## (\d+)\. ", re.MULTILINE)


def copy_source(dest: Path, ref: str = "v1.0") -> Path:
    """Materialise the article files AS OF `ref` (amended in fix round 1 of
    Task 1: copying the LIVE source/ would break every count here the first
    time a real amendment is drafted). See the implemented file."""
    ...


def shift_headings(text: str, start: int, by: int) -> str:
    """Renumber every `## N.` heading with N >= start by `by`. Headings only."""
    return _H2.sub(
        lambda m: f"## {int(m.group(1)) + by}. " if int(m.group(1)) >= start else m.group(0),
        text)


def insert_section(text: str, at: int, title: str, body: str = "New text.") -> str:
    """Insert `## at. TITLE` before the existing `## at.`, shifting it and every
    later heading up by one."""
    shifted = shift_headings(text, at, 1)
    i = shifted.index(f"## {at + 1}. ")
    return shifted[:i] + f"## {at}. {title}\n\n{body}\n\n" + shifted[i:]


def delete_section(text: str, n: int) -> str:
    """Remove `## n.` and its body up to the next `## ` heading, shifting every
    later heading down by one."""
    start = text.index(f"## {n}. ")
    nxt = text.find("\n## ", start + 1)
    out = text[:start] + (text[nxt + 1:] if nxt != -1 else "")
    return shift_headings(out, n + 1, -1)


def retitle(text: str, n: int, new_title: str) -> str:
    return re.sub(rf"^## {n}\. .*$", f"## {n}. {new_title}", text, count=1, flags=re.MULTILINE)
```

- [ ] **Step 2: Write the failing tests**

Create `build/tests/test_section_map.py`:

```python
"""build/section_map.py -- the derived section-renumbering map.

The map is DERIVED, never authored: a hand-maintained renumbering map is exactly
the failure baseline_selfcheck.py exists to catch (308 phantom lines comparing
v1.0 to itself, exit 0). Every assertion here that something was NOT mapped sits
beside a positive control, because the real tree is identical to v1.0 and a
broken derivation would also map nothing.
"""
import json
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import section_map  # noqa: E402
import section_fixtures as fx  # noqa: E402

REPO = BUILD.parent
ART7 = "article-07-use-standards.md"


def _tree_with(tmp_path, article, transform):
    tree = fx.copy_source(tmp_path / "src")
    p = tree / article
    p.write_text(transform(p.read_text()))
    return tree


def test_against_v1_0_it_examines_every_heading_and_maps_nothing(tmp_path):
    """The real tree equals v1.0, so 'maps nothing' alone proves nothing.
    The positive control is `matched`: the derivation must have found every
    heading again -- 66 in Article 7, 14 in Article 3, 29 in Article 8."""
    doc = section_map.derive("v1.0", fx.copy_source(tmp_path / "src"))
    assert doc["articles"] == {}
    assert doc["matched"]["7"] == 66
    assert doc["matched"]["3"] == 14
    assert doc["matched"]["8"] == 29
    assert doc["matched"].get("9", 0) == 0     # Article 9 has no headings


def test_a_section_inserted_at_3_maps_exactly_64(tmp_path):
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    doc = section_map.derive("v1.0", tree)
    assert doc["articles"]["7"] == {str(o): o + 1 for o in range(3, 67)}
    assert len(doc["articles"]["7"]) == 64
    assert doc["matched"]["7"] == 66


def test_a_retitled_section_at_a_shifted_number_is_not_mapped(tmp_path):
    """Old §10 becomes new §11 AND is retitled: not a pure renumbering, so it
    stays visible as a change."""
    def change(t):
        return fx.retitle(fx.insert_section(t, 3, "AGRICULTURE"), 11, "SOMETHING ELSE")
    doc = section_map.derive("v1.0", _tree_with(tmp_path, ART7, change))
    assert "10" not in doc["articles"]["7"]
    assert len(doc["articles"]["7"]) == 63
    assert any(e.startswith("§10 ") for e in doc["unmapped_old"]["7"])


def test_a_deleted_section_maps_the_sections_after_it_but_not_itself(tmp_path):
    """Ruling 6: sections after a deletion keep their titles, so they ARE a
    renumbering. The deleted section's own number is never mapped."""
    doc = section_map.derive("v1.0", _tree_with(tmp_path, ART7, lambda t: fx.delete_section(t, 3)))
    assert doc["articles"]["7"] == {str(o): o - 1 for o in range(4, 67)}
    assert "3" not in doc["articles"]["7"]
    assert any(e.startswith("§3 ") for e in doc["unmapped_old"]["7"])


def test_a_changed_body_at_an_unchanged_number_is_not_mapped(tmp_path):
    def change(t):
        return t.replace("## 5. AMUSEMENT, OUTDOOR\n", "## 5. AMUSEMENT, OUTDOOR\n\nAmended text.\n", 1)
    tree = _tree_with(tmp_path, ART7, change)
    assert "Amended text." in (tree / ART7).read_text()     # the edit really landed
    doc = section_map.derive("v1.0", tree)
    assert doc["articles"] == {}
    assert doc["matched"]["7"] == 66                        # and every heading was examined


def test_a_duplicated_title_is_never_mapped():
    """Two headings with the same title cannot be told apart by title, so the
    alignment could pair the wrong one. Ambiguous titles stay unmapped."""
    old = "## 1. GENERAL\n## 2. GENERAL\n## 3. USE\n"
    new = "## 1. NEW\n## 2. GENERAL\n## 3. GENERAL\n## 4. USE\n"
    mapping, _, old_un, _ = section_map.derive_article(old, new)
    assert mapping == {3: 4}
    assert any("GENERAL" in e for e in old_un)


def test_below_the_similarity_floor_derive_refuses_and_writes_nothing(tmp_path):
    def change(t):
        return fx._H2.sub(lambda m: f"## {m.group(1)}. RENAMED ", t)
    tree = _tree_with(tmp_path, ART7, change)
    out = tmp_path / "map.json"
    r = subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                        "--new-dir", str(tree), "--out", str(out)],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 2, r.stderr
    assert "Article 7" in r.stderr
    assert not out.exists()


def test_the_map_records_its_provenance(tmp_path):
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = tmp_path / "map.json"
    r = subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                        "--new-dir", str(tree), "--out", str(out)],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text())
    assert doc["for_old_ref"] == "v1.0"
    assert doc["for_new_tree"] == section_map.tree_hash(tree)
    assert section_map.load(out) == {7: {o: o + 1 for o in range(3, 67)}}
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_section_map.py -v`
Expected: every test FAILS or ERRORS with `ModuleNotFoundError: No module named 'section_map'`.

- [ ] **Step 4: Write the module**

Create `build/section_map.py`:

```python
#!/usr/bin/env python3
"""Derive a SECTION renumbering map between two versions of the Code.

WHY THIS EXISTS. When a section is inserted into an Article -- Right to Farm
puts a new Section 3 into Article 7 -- every later section's number shifts, and
every heading and cross-reference to them changes by one. Those are not
amendments, but a raw diff counts each one, so the packet's headline number
would carry two phantom lines per shifted heading and reference.
normalize_for_diff.py suppresses them on the OLD side -- given a map saying
which old section became which new one. This module produces that map.

WHY IT IS DERIVED, NOT AUTHORED. A hand-maintained renumbering map is exactly
the failure baseline_selfcheck.py exists to catch: 308 phantom lines comparing
v1.0 to itself, exit 0. And this map cannot live in adoption-map.json anyway:
populating that file for the next amendment makes baseline_selfcheck refuse it
as "not rolled over". So the map is derived from the two trees, written to a
release's staging directory, and never committed. adoption-map.json,
adoption_map.py and baseline_selfcheck.py are NOT touched by this module.

WHAT COUNTS AS A RENUMBERING. Only a section whose `## N.` heading title is
identical (after normalising whitespace and case) in both versions, aligned in
order, with a different number. A retitled, added, deleted or ambiguous section
is NOT mapped -- it stays fully visible in the redline as a real change. That
conservatism is the point: a map that maps too much hides a real amendment, and
an omission from a redline is invisible to the reader.

SCOPE. `## N.` headings only (Articles 1-8; Article 9 has none). Lettered
`### x.` sub-sections are not mapped, so inserting a sub-section still shows
its shifted references as changes -- recoverable noise, never a hidden
amendment.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

BUILD = Path(__file__).resolve().parent
REPO = BUILD.parent
DEFAULT_NEW_DIR = REPO / "source"

# `## N. TITLE`. Measured 2026-10-08: every `## ` line in source/article-0*.md
# matches `^## [0-9]+\. ` -- digits, period, one space, uppercase title.
_H2 = re.compile(r"^## (\d+)\. (.+?)\s*$", re.MULTILINE)
_ARTICLE_NUMBER = re.compile(r'^article-number:\s*"(\d+)"', re.MULTILINE)

# Below this fraction of an Article's old headings found again in order, the
# alignment is too weak to trust as a pure renumbering, and derive() fails
# closed rather than guess. Inserting one section into Article 7 finds 66 of 66
# (1.0); a wholesale rewrite finds few. How an operator supplies a hand entry in
# that case is the release driver's decision, not this module's.
SIMILARITY_FLOOR = 0.5


class BelowFloor(Exception):
    """An Article's headings align too weakly to derive a map from."""


def _git_show(ref: str, path: str) -> str | None:
    # Imported here rather than at module top: redline_resolve imports THIS
    # module to apply a map, so a top-level import would be circular.
    from redline_resolve import git_show
    return git_show(ref, path)


def normalise_title(title: str) -> str:
    return " ".join(title.split()).upper()


def headings(text: str) -> list[tuple[int, str]]:
    return [(int(m.group(1)), normalise_title(m.group(2))) for m in _H2.finditer(text)]


def article_number(text: str) -> int | None:
    m = _ARTICLE_NUMBER.search(text)
    return int(m.group(1)) if m else None


def derive_article(old_text: str, new_text: str):
    """Return (mapping, matched, old_unmatched, new_unmatched) for one Article.

    mapping       {old number: new number}, ONLY where the number changed for a
                  heading whose title is identical, unambiguous, and aligned in
                  order.
    matched       how many old headings were found again in order -- evidence
                  the derivation examined every heading, which a test of an
                  empty map needs (an empty map is also what a broken one gives).
    old_unmatched old headings left unmapped (retitled, deleted, reordered or
                  ambiguous): every reference to them stays visible as a change.
    new_unmatched new headings with no counterpart (added or retitled).
    """
    old_h, new_h = headings(old_text), headings(new_text)
    ambiguous = ({t for t, c in Counter(t for _, t in old_h).items() if c > 1}
                 | {t for t, c in Counter(t for _, t in new_h).items() if c > 1})
    sm = difflib.SequenceMatcher(None, [t for _, t in old_h], [t for _, t in new_h],
                                 autojunk=False)
    mapping: dict[int, int] = {}
    matched = 0
    old_unmatched: list[str] = []
    new_unmatched: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for (o_num, title), (n_num, _) in zip(old_h[i1:i2], new_h[j1:j2]):
                matched += 1
                if title in ambiguous:
                    old_unmatched.append(f"§{o_num} {title} (ambiguous title)")
                elif o_num != n_num:
                    mapping[o_num] = n_num
        else:
            old_unmatched += [f"§{n} {t}" for n, t in old_h[i1:i2]]
            new_unmatched += [f"§{n} {t}" for n, t in new_h[j1:j2]]
    return mapping, matched, old_unmatched, new_unmatched


def tree_hash(new_dir: Path) -> str:
    """Identify the tree a map was derived against, so it is not applied to another."""
    h = hashlib.sha256()
    for p in sorted(Path(new_dir).glob("article-0*.md")):
        h.update(p.name.encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def derive(old_ref: str, new_dir: Path = DEFAULT_NEW_DIR) -> dict:
    new_dir = Path(new_dir)
    doc: dict = {"for_old_ref": old_ref, "for_new_tree": tree_hash(new_dir),
                 "articles": {}, "matched": {}, "unmapped_old": {}, "unmapped_new": {}}
    weak: list[str] = []
    for new_path in sorted(new_dir.glob("article-0*.md")):
        old_text = _git_show(old_ref, f"source/{new_path.name}")
        if old_text is None:
            continue                      # new at this version: nothing renumbered from it
        art = article_number(old_text)    # keyed on the OLD number, which references use
        if art is None:
            continue
        mapping, matched, old_un, new_un = derive_article(old_text, new_path.read_text())
        key = str(art)
        doc["matched"][key] = matched
        if old_un:
            doc["unmapped_old"][key] = old_un
        if new_un:
            doc["unmapped_new"][key] = new_un
        total = len(headings(old_text))
        if total and matched / total < SIMILARITY_FLOOR:
            weak.append(f"Article {art}: {matched} of {total} headings found again in order")
            continue
        if mapping:
            doc["articles"][key] = {str(o): n for o, n in sorted(mapping.items())}
    if weak:
        raise BelowFloor("; ".join(weak))
    return doc


def load(path) -> dict[int, dict[int, int]]:
    doc = json.loads(Path(path).read_text())
    return {int(a): {int(o): int(n) for o, n in m.items()} for a, m in doc["articles"].items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("derive", help="derive a map from <old-ref> to a tree")
    d.add_argument("old_ref")
    d.add_argument("--new-dir", default=str(DEFAULT_NEW_DIR))
    d.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "derive":
        try:
            doc = derive(a.old_ref, Path(a.new_dir))
        except BelowFloor as exc:
            print(f"section_map: refusing to derive -- {exc}. Below the "
                  f"{SIMILARITY_FLOOR:.0%} similarity floor the alignment cannot be "
                  f"trusted as a pure renumbering; no map was written.", file=sys.stderr)
            return 2
        Path(a.out).write_text(json.dumps(doc, indent=2) + "\n")
        n = sum(len(m) for m in doc["articles"].values())
        print(f"section_map: {n} renumbered section(s) across "
              f"{len(doc['articles'])} Article(s) vs {a.old_ref}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_section_map.py -v`
Expected: 8 passed.

- [ ] **Step 6: Prove the invariant and run the full suite**

```bash
cd "/Users/ben/Developer/Claude/Projects/Newcastle Core Zoning Code"
git diff --stat main -- build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py
python3 -m pytest build/tests -q
```
Expected: the `git diff` prints **nothing**; the suite reports 207 passed (199 + 8). Report the number you see.

- [ ] **Step 7: Commit**

```bash
git add build/section_map.py build/tests/section_fixtures.py build/tests/test_section_map.py
git commit -m "$(cat <<'EOF'
build: derive a section-renumbering map between two versions of the Code

When a section is inserted, every later section's heading and every reference
to it shift by one. A raw diff counts each as a change, inflating the packet's
headline number with renumbering nobody amended.

The map is derived by aligning heading titles, never authored: a hand-kept
renumbering map is the failure baseline_selfcheck.py exists to catch, and
populating adoption-map.json for the next amendment would make that check
refuse it. Only an identical, unambiguous, in-order title at a new number is
mapped; anything retitled, added, deleted or ambiguous stays visible. Below a
50% similarity floor it fails closed.

adoption-map.json, adoption_map.py and baseline_selfcheck.py are untouched.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: The provenance check and the self-check gate

**Files:**
- Modify: `build/section_map.py`
- Modify: `build/tests/test_section_map.py`

**Interfaces:**
- Consumes: Task 1's `derive`, `derive_article`, `headings`, `article_number`, `tree_hash`, `_git_show`.
- Produces:
  - `section_map.check(path, old_ref, new_dir=None) -> list[str]` — problems; empty means acceptable. Refuses a map whose `for_old_ref` differs from `old_ref`, and — when `new_dir` is given — whose `for_new_tree` differs from that tree's hash. Task 5's `redline_resolve.py` calls it.
  - `section_map.selfcheck(path, old_ref, new_dir=DEFAULT_NEW_DIR) -> list[str]` — the gate (ruling 1).
  - CLI: `check <PATH> --old-ref R [--new-dir DIR]` and `selfcheck <PATH> --old-ref R [--new-dir DIR]`, each exit 0 clean or **1** with every problem on stderr. The release driver (P13) runs `selfcheck` as a precondition.

**Why the gate is not the one the scope document describes:** see ruling 1. "Apply the map to the old side and compare against itself" fails every real map. What actually catches a wrong map is that its entries pair headings whose titles differ — an off-by-one shift pairs old §3 with new §5, two different sections.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_section_map.py`:

```python
# --- check: is this map for this comparison? ----------------------------------

def _derived(tmp_path, tree):
    out = tmp_path / "map.json"
    r = subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                        "--new-dir", str(tree), "--out", str(out)],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    return out


def _cli(*args):
    return subprocess.run([sys.executable, str(BUILD / "section_map.py"), *args],
                          capture_output=True, text=True, cwd=REPO)


def test_check_accepts_the_comparison_a_map_was_derived_for(tmp_path):
    """The positive control for the two refusals below."""
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = _derived(tmp_path, tree)
    r = _cli("check", str(out), "--old-ref", "v1.0", "--new-dir", str(tree))
    assert r.returncode == 0, r.stderr


def test_check_refuses_a_map_for_a_different_old_ref(tmp_path):
    """Nothing today validates the old ref against a map; this closes it."""
    out = _derived(tmp_path, _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "X")))
    r = _cli("check", str(out), "--old-ref", "v0.24-draft")
    assert r.returncode == 1
    assert "v1.0" in r.stderr and "v0.24-draft" in r.stderr


def test_check_refuses_a_map_applied_to_a_different_tree(tmp_path):
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = _derived(tmp_path, tree)
    (tree / ART7).write_text((tree / ART7).read_text() + "\nLater edit.\n")
    r = _cli("check", str(out), "--old-ref", "v1.0", "--new-dir", str(tree))
    assert r.returncode == 1
    assert "different tree" in r.stderr


# --- selfcheck: is this map right? ---------------------------------------------

def test_selfcheck_passes_a_correct_non_empty_map(tmp_path):
    """The positive control, and deliberately NOT the empty map against the real
    tree: that passes whether or not the gate works. This map has 64 entries,
    every one of which the gate must examine and accept."""
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = _derived(tmp_path, tree)
    assert len(json.loads(out.read_text())["articles"]["7"]) == 64
    r = _cli("selfcheck", str(out), "--old-ref", "v1.0", "--new-dir", str(tree))
    assert r.returncode == 0, r.stderr


def test_selfcheck_refuses_an_off_by_one_map(tmp_path):
    """The control the gate exists for: shift every target by one and every
    entry now pairs two different sections. It must be able to fail, or it
    is decoration."""
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = _derived(tmp_path, tree)
    doc = json.loads(out.read_text())
    doc["articles"]["7"] = {o: n + 1 for o, n in doc["articles"]["7"].items()}
    out.write_text(json.dumps(doc))
    r = _cli("selfcheck", str(out), "--old-ref", "v1.0", "--new-dir", str(tree))
    assert r.returncode == 1
    assert "Article 7" in r.stderr


def test_selfcheck_refuses_a_single_wrong_entry(tmp_path):
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = _derived(tmp_path, tree)
    doc = json.loads(out.read_text())
    doc["articles"]["7"]["10"] = 40          # old §10 is not new §40
    out.write_text(json.dumps(doc))
    r = _cli("selfcheck", str(out), "--old-ref", "v1.0", "--new-dir", str(tree))
    assert r.returncode == 1
    assert "§10 -> §40" in r.stderr


def test_section_map_does_not_reach_into_the_adoption_map():
    """The invariant behind deriving the map. It reads the Code only through
    git_show; a later edit importing the adoption map or its self-check would
    make the next amendment's map collide with the rollover guard.

    Checked on the parsed module, not its text: the docstrings deliberately
    NAME those files to say they are not touched, so a text search fails on
    the documentation of their absence."""
    import ast
    tree = ast.parse((BUILD / "section_map.py").read_text())
    imported = {a.name.split(".")[0] for n in ast.walk(tree)
                if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.module}
    assert not imported & {"adoption_map", "baseline_selfcheck"}, imported
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
                  and n.body and isinstance(n.body[0], ast.Expr)
                  and isinstance(n.body[0].value, ast.Constant)}
    literals = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and id(n) not in docstrings]
    assert not [s for s in literals if "adoption-map" in s or "adoption_map" in s
                or "baseline_selfcheck" in s]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_section_map.py -v`
Expected: the six new check/selfcheck tests FAIL — the `check` and `selfcheck` subcommands do not exist yet (argparse exits 2 with "invalid choice"). The eight Task 1 tests and `test_section_map_does_not_reach_into_the_adoption_map` PASS.

- [ ] **Step 3: Add `check` and `selfcheck`**

In `build/section_map.py`, add above `main`:

```python
def check(path, old_ref: str, new_dir=None) -> list[str]:
    """Is this map for THIS comparison? Problems as operator-readable lines."""
    doc = json.loads(Path(path).read_text())
    problems: list[str] = []
    if doc.get("for_old_ref") != old_ref:
        problems.append(f"the map was derived for {doc.get('for_old_ref')!r}, "
                        f"not {old_ref!r}")
    if new_dir is not None and doc.get("for_new_tree") != tree_hash(Path(new_dir)):
        problems.append(f"the map was derived against a different tree than {new_dir}")
    return problems


def selfcheck(path, old_ref: str, new_dir=DEFAULT_NEW_DIR) -> list[str]:
    """Is this map RIGHT? The gate the release driver runs before using a map.

    (a) Every entry pairs an old heading and a new heading whose normalised
        titles are identical. An off-by-one shift pairs old §3 with new §5 --
        two different sections -- which is what this catches.
    (b) Deriving the old ref against ITSELF maps nothing.

    Not "apply the map to the old side and compare it against itself": a real
    renumbering rewrites references the unmodified copy still carries, so that
    test fails every correct map (see plans/2026-10-08-wave2-section-map.md,
    ruling 1).
    """
    new_dir = Path(new_dir)
    doc = json.loads(Path(path).read_text())
    problems = check(path, old_ref, new_dir)

    index: dict[int, tuple[str, str]] = {}
    for new_path in sorted(new_dir.glob("article-0*.md")):
        old_text = _git_show(old_ref, f"source/{new_path.name}")
        if old_text is None:
            continue
        art = article_number(old_text)
        if art is not None:
            index[art] = (old_text, new_path.read_text())

    for key, entries in sorted(doc["articles"].items()):
        art = int(key)
        if art not in index:
            problems.append(f"Article {art}: in the map but not found at {old_ref}")
            continue
        old_titles = dict(headings(index[art][0]))
        new_titles = dict(headings(index[art][1]))
        for o, n in entries.items():
            o, n = int(o), int(n)
            ot, nt = old_titles.get(o), new_titles.get(n)
            if ot is None or nt is None or ot != nt:
                problems.append(f"Article {art}: §{o} -> §{n} pairs {ot!r} with {nt!r}")

    for art, (old_text, _) in sorted(index.items()):
        mapping, *_ = derive_article(old_text, old_text)
        if mapping:
            problems.append(f"Article {art}: deriving {old_ref} against itself "
                            f"mapped {len(mapping)} section(s)")
    return problems
```

In `main`, register the two subcommands after the `derive` parser:

```python
    c = sub.add_parser("check", help="is this map for this comparison?")
    c.add_argument("path")
    c.add_argument("--old-ref", required=True)
    c.add_argument("--new-dir", default=None)
    s = sub.add_parser("selfcheck", help="is this map right? (the release gate)")
    s.add_argument("path")
    s.add_argument("--old-ref", required=True)
    s.add_argument("--new-dir", default=str(DEFAULT_NEW_DIR))
```

and replace the final `return 2` with:

```python
    if a.cmd == "check":
        found = check(a.path, a.old_ref, Path(a.new_dir) if a.new_dir else None)
    else:
        found = selfcheck(a.path, a.old_ref, Path(a.new_dir))
    for p in found:
        print(f"  - {p}", file=sys.stderr)
    return 1 if found else 0
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_section_map.py -v`
Expected: 15 passed.

- [ ] **Step 5: Prove the invariant and run the full suite**

```bash
git diff --stat main -- build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py
python3 -m pytest build/tests -q
```
Expected: the `git diff` prints nothing; the suite reports 214 passed (207 + 7). Report what you see.

- [ ] **Step 6: Commit**

```bash
git add build/section_map.py build/tests/test_section_map.py
git commit -m "$(cat <<'EOF'
build: gate a section map on provenance and on correctness

check refuses a map derived for a different old ref or a different tree --
nothing today validates the ref a redline compares against. selfcheck is the
gate the release driver will run: every entry must pair two headings with
identical titles, which is what an off-by-one shift breaks, and deriving the
old ref against itself must map nothing.

Not the gate the scope document described ("apply the map to the old side and
compare it against itself"): a real renumbering rewrites references the
unmodified copy still carries, so that test fails every correct map.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Count every changed line, including ones that begin with `--`

**Files:**
- Modify: `build/normalize_for_diff.py:201-226` (`changed_line_count`)
- Modify: `build/tests/test_normalize_for_diff.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `normalize_for_diff._marked(old_lines: list[str], new_lines: list[str]) -> int` — the one counting rule, used by `changed_line_count` and by the tests. Task 4 extends `changed_line_count` on top of it.

**The bug, found while planning this wave.** `changed_line_count` counts `+`/`-` lines of a unified diff and drops its file headers by *prefix*: `line[:3] not in ("+++", "---")`. That also drops every **real** changed line whose content begins with `--` or `++`. A deleted `---` horizontal rule appears as `----` and is silently not counted — in the number that goes to voters. The two header lines are always exactly the first two lines of a non-empty unified diff, so skip those two by position instead.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_normalize_for_diff.py`:

```python
# --- The counter counts every changed line ------------------------------------
# changed_line_count dropped diff headers by PREFIX ("---"/"+++"), which also
# dropped real changed lines beginning with -- or ++. Found 2026-10-08.

def test_a_deleted_horizontal_rule_is_counted():
    """`---` deleted appears in the diff as `----`, which the old prefix filter
    discarded as if it were the file header."""
    assert nz.changed_line_count("a\n---\nb\n", "a\nb\n", amap=AMAP) == 1


def test_an_added_line_beginning_with_plus_plus_is_counted():
    assert nz.changed_line_count("a\n", "a\n++x\n", amap=AMAP) == 1


def test_identical_text_still_counts_zero():
    """The fix must not count the headers when there is no diff at all -- an
    empty diff has no header lines to skip."""
    assert nz.changed_line_count("a\nb\n", "a\nb\n", amap=AMAP) == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_normalize_for_diff.py -k "horizontal_rule or plus_plus or still_counts_zero" -v`
Expected: the first two FAIL (`0 == 1`); `test_identical_text_still_counts_zero` PASSES — it is the control that the fix does not break the empty case.

- [ ] **Step 3: Fix the counter**

In `build/normalize_for_diff.py`, add above `changed_line_count`:

```python
def _marked(o: list[str], n: list[str]) -> int:
    """How many lines differ between two line lists: the ONE counting rule.

    A non-empty unified diff always begins with exactly two file-header lines
    (`--- ` and `+++ `); every later line starting with `+` or `-` is a changed
    line. The previous filter dropped headers by PREFIX instead, which also
    dropped real changed lines beginning with -- or ++ -- a deleted `---`
    horizontal rule appears as `----`. Found 2026-10-08.
    """
    import difflib

    lines = list(difflib.unified_diff(o, n, n=0))
    return sum(1 for line in lines[2:] if line[:1] in "+-")
```

and replace the body of `changed_line_count` after its docstring with:

```python
    o = normalize_old_side(old, amap=amap).splitlines()
    n = new.splitlines()
    return _marked(o, n)
```

- [ ] **Step 4: Point the existing tests at the one rule**

Two existing tests carry their own copy of the old prefix filter. Leaving them would keep a second, divergent definition of "a changed line".

In `test_changed_line_count_follows_the_render_path`, replace the `expected = sum(…)` computation with:

```python
    expected = nz._marked(nz.normalize_old_side(old, amap=AMAP).splitlines(),
                          new.splitlines())
```

and remove its now-unused `import difflib`.

In `test_breakdown_and_render_paths_agree_on_the_real_corpus`, replace the `comparison = sum(…)` computation with:

```python
        comparison = nz._marked(
            nz.normalize(old.stdout, amap=AMAP, is_baseline_side=True).splitlines(),
            nz.normalize(new, amap=AMAP, is_baseline_side=False).splitlines())
```

and remove its now-unused `import difflib`.

- [ ] **Step 5: Run the module's tests**

Run: `python3 -m pytest build/tests/test_normalize_for_diff.py -v`
Expected: all pass, including the three new ones and the real-corpus agreement test.

- [ ] **Step 6: Prove the invariant and run the full suite**

```bash
git diff --stat main -- build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py
python3 build/baseline_selfcheck.py; echo "rc=$?"
python3 -m pytest build/tests -q
```
Expected: the `git diff` prints nothing; `baseline_selfcheck.py` prints `0 marked lines` and `rc=0` (it calls `changed_line_count` at its line 87, so this proves the fix did not disturb the rollover guard); the suite reports 217 passed (214 + 3).

- [ ] **Step 7: Commit**

```bash
git add build/normalize_for_diff.py build/tests/test_normalize_for_diff.py
git commit -m "$(cat <<'EOF'
normalize: count changed lines that begin with -- or ++

changed_line_count dropped the unified diff's file headers by prefix, which
also dropped real changed lines whose content begins with -- or ++: a deleted
`---` horizontal rule appears as `----` and was not counted, in the number the
packet reports to voters. The two headers are always the first two lines of a
non-empty diff, so they are now skipped by position.

The two tests that carried their own copy of the old filter now use the one
counting rule, so there is a single definition of a changed line.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Rule 6 — section renumbering on the old side

**Files:**
- Modify: `build/normalize_for_diff.py`
- Modify: `build/tests/test_normalize_for_diff.py`

**Interfaces:**
- Consumes: Task 3's `_marked`; an `smap` of shape `{old article: {old section: new section}}`, as `section_map.load` returns.
- Produces:
  - `normalize(text, *, amap, is_baseline_side, smap=None)`, `normalize_old_side(text, *, amap, smap=None)`, `changed_line_count(old, new, *, amap, smap=None)` — **keyword-only, defaulting to `None`**, so every existing call and test is unchanged.
  - `normalize_for_diff.normalize_sections_only(text, *, smap) -> str` — Rule 6 alone, render-safe. Task 5's draft-to-draft path uses it.
  - `normalize_for_diff._section_renumber(text, smap) -> tuple[str, int]` — the text and how many numbers changed. Task 5's `report()` uses the count.

**Why it lives in BOTH `normalize()` and `normalize_old_side()`:** `test_breakdown_and_render_paths_agree_on_the_real_corpus` pins their agreement. A rule in only one of them breaks it.

**Why it runs FIRST, before `amap.renumber`:** the map is keyed on the *baseline* article number, and the containing Article is read from the frontmatter that `_renumber_frontmatter` rewrites. Run after them, `Article 7 Section 3` would have its article rewritten out from under the lookup.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_normalize_for_diff.py`:

```python
# --- Rule 6: section renumbering ---------------------------------------------
# A section inserted into an Article shifts every later heading and every
# reference to it. Suppressed on the OLD side only, from a DERIVED map
# (build/section_map.py), keyed on the baseline article number read from the
# text's own frontmatter. Every grammar is tested in both directions.

FM = '---\narticle-number: "7"\n---\n'
SMAP = {7: {3: 4, 4: 5, 6: 7, 7: 8, 14: 15}}

# Rule 6 is tested against an IDENTITY article map. The module-level AMAP is the
# pinned v0.1 fixture, which renumbers Article 7 -> 8: under it every test below
# would have its own frontmatter rewritten (and every count would carry one
# extra changed line), failing for a reason that has nothing to do with Rule 6.
# Only the ordering test uses AMAP, deliberately.
IDENTITY = adoption_map.AdoptionMap(baseline_version="v1.0",
                                    article_numbers={n: n for n in range(1, 10)},
                                    files={}, not_text_comparable={})


def old7(body):
    return nz.normalize_old_side(FM + body, amap=IDENTITY, smap=SMAP)


def test_a_renumbered_heading_is_suppressed():
    assert old7("## 3. ADULT ESTABLISHMENT\n") == FM + "## 4. ADULT ESTABLISHMENT\n"


def test_but_a_heading_the_map_does_not_cover_is_untouched():
    assert old7("## 2. EXPANDED USE STANDARDS\n") == FM + "## 2. EXPANDED USE STANDARDS\n"


def test_a_bare_section_reference_is_suppressed():
    assert old7("See Section 3.\n") == FM + "See Section 4.\n"


def test_but_a_bare_reference_to_an_unmapped_section_still_differs():
    assert old7("See Section 5.\n") == FM + "See Section 5.\n"


def test_only_the_leading_number_of_a_dotted_reference_moves():
    assert old7("See Section 3.C.4.\n") == FM + "See Section 4.C.4.\n"


def test_but_a_changed_sub_section_letter_still_differs():
    """Only the section number is normalised; a real change to the letter that
    follows it is untouched and survives the comparison."""
    assert old7("See Section 3.C.4.\n") != FM + "See Section 4.D.4.\n"


def test_each_element_of_a_list_is_mapped_independently():
    assert old7("Sections 6, 7.F, and 14\n") == FM + "Sections 7, 8.F, and 15\n"


def test_a_list_with_and_and_through_is_mapped():
    assert old7("Sections 3 and 6\n") == FM + "Sections 4 and 7\n"
    assert old7("Sections 3.F.2 through 3.F.4\n") == FM + "Sections 4.F.2 through 4.F.4\n"


def test_a_bare_section_sign_is_suppressed():
    assert old7("under §3.\n") == FM + "under §4.\n"


def test_an_explicit_article_reference_resolves_against_THAT_article():
    """`Article 3 Section 2` inside Article 7 means Article 3's section 2,
    not Article 7's."""
    smap = {3: {2: 3}, 7: {2: 9}}
    out = nz.normalize_old_side(FM + "See Article 3 Section 2.\n", amap=IDENTITY, smap=smap)
    assert "Section 3." in out and "Section 9" not in out


def test_an_explicit_article_section_sign_resolves_against_that_article():
    smap = {8: {12: 13}}
    assert nz.normalize_old_side(FM + "under Article 8 §12.F.\n", amap=IDENTITY,
                                 smap=smap).endswith("under Article 8 §13.F.\n")


def test_a_bare_reference_resolves_against_its_OWN_article_not_another():
    """A bare `Section N` is unambiguous only within its Article. Article 3's
    text is not shifted by Article 7's map."""
    fm3 = '---\narticle-number: "3"\n---\n'
    assert nz.normalize_old_side(fm3 + "See Section 3.\n", amap=IDENTITY,
                                 smap={7: {3: 4}}) == fm3 + "See Section 3.\n"


def test_section_of_another_article_is_left_alone():
    assert old7("See Section 3 of Article 4.\n") == FM + "See Section 3 of Article 4.\n"
    assert old7("See Section 3.C.4 of Article 4.\n") == FM + "See Section 3.C.4 of Article 4.\n"


def test_section_of_this_article_resolves_against_the_containing_one():
    assert old7("See Section 3 of this Article.\n") == FM + "See Section 4 of this Article.\n"


def test_without_frontmatter_bare_references_are_not_guessed():
    """No frontmatter, no containing Article: bare forms stay as they are.
    Explicit `Article N Section M` still resolves."""
    assert nz.normalize_old_side("See Section 3.\n", amap=IDENTITY, smap=SMAP) == "See Section 3.\n"


def test_the_section_rule_runs_before_article_renumbering():
    """Keyed on BASELINE numbers. The fixture map shifts Article 7 -> 8; if
    article renumbering ran first, the section lookup would use Article 8's
    sub-map and miss. The ONE Rule 6 test that uses the fixture AMAP, on purpose."""
    out = nz.normalize_old_side(FM + "See Article 7 Section 3.\n", amap=AMAP, smap={7: {3: 4}})
    assert out.endswith("See Article 8 Section 4.\n")


def test_the_new_side_is_never_section_renumbered():
    out = nz.normalize(FM + "See Section 3.\n", amap=IDENTITY, is_baseline_side=False, smap=SMAP)
    assert "Section 3." in out


def test_without_a_map_nothing_changes():
    text = FM + "## 3. ADULT\nSee Section 3 and Sections 6, 7.F, and 14.\n"
    assert nz.normalize_old_side(text, amap=AMAP) == nz.normalize_old_side(text, amap=AMAP, smap=None)
    assert nz.normalize_sections_only(text, smap=None) == text


# --- Statutory citations are never rewritten -----------------------------------

STATUTORY = [
    ("article-01-general.md", ["30-A MRSA Section 4358", "30-A MRSA Section 4404",
                               "38 MRSA Sections 435449"]),
    ("article-03-streets-roads-driveways.md", ["30-A MRSA §4404", "23 MRSA §3022",
                                              "23 MRSA §3021", "23 MRSA §3026-A",
                                              "23 MRSA §704"]),
    ("article-07-use-standards.md", ["Subchapter C, §53.11"]),
    ("article-08-administration.md", ["Chapter187, Section 4401", "Title 23, Section 704",
                                      "Title 38, Section 480-B", "38 M.R.S.A. Section 420-D",
                                      "MRSA Title 38 Section 480-B", "Title 12, Section 8869",
                                      "Title 38, Section 435", "MRSA Title 30 Section 2691",
                                      "Title 30-A Section 4452"]),
    ("article-09-definitions.md", ["50 Stat. 888, Section 8", "23 MRSA §3021",
                                   "23 MRSA §3022"]),
]


def _real(name):
    import subprocess
    r = subprocess.run(["git", "-C", str(BUILD.parent), "show", f"v1.0:source/{name}"],
                       capture_output=True, text=True)
    assert r.returncode == 0, name
    return r.stdout


def _shift_everything():
    """A map that would rewrite EVERY section number in every Article."""
    return {a: {k: k + 1 for k in range(1, 10000)} for a in range(1, 10)}


def test_no_statutory_citation_is_ever_rewritten():
    """Every statutory citation in the Code survives a map that would rewrite
    every number it can reach. Measured set, 2026-10-08 -- including the two
    federal citations in Article 9 that a guard limited to MRSA/M.R.S/Title/
    U.S.C would have renumbered, and `§53.11` in Article 7, which collides with
    a real section number."""
    smap = _shift_everything()
    for name, citations in STATUTORY:
        text = _real(name)
        out = nz.normalize_sections_only(text, smap=smap)
        for cite in citations:
            assert cite in text, f"{name}: fixture citation not in the source: {cite!r}"
            assert cite in out, f"{name}: statutory citation rewritten: {cite!r}"


def test_and_the_same_map_DID_rewrite_internal_references():
    """The positive control. If the rule did nothing at all, every statutory
    citation would survive trivially. Article 3 carries internal references the
    same map must move."""
    text = _real("article-03-streets-roads-driveways.md")
    out = nz.normalize_sections_only(text, smap=_shift_everything())
    assert "Article 8 §20" in text and "Article 8 §21" in out
    assert "(Sections 6, 7.F, and 14)" in text and "(Sections 7, 8.F, and 15)" in out


def test_a_mixed_line_rewrites_its_internal_reference_and_not_its_statute():
    """`23 MRSA §3026-A and Article 8 §27` -- the explicit Article prefix is
    decisive, so the statute guard does not suppress the internal reference."""
    fm3 = '---\narticle-number: "3"\n---\n'
    out = nz.normalize_sections_only(fm3 + "under 23 MRSA §3026-A and Article 8 §27.\n",
                                     smap={3: {3026: 3027}, 8: {27: 28}})
    assert "23 MRSA §3026-A" in out
    assert "Article 8 §28" in out


# --- The negative controls that matter most ------------------------------------

def test_a_real_amendment_beside_a_renumbered_heading_still_counts():
    """THE control for this rule. A renumbered heading is suppressed; a real
    change on the very next line -- shall to may -- must still be counted."""
    old = FM + "## 3. ADULT ESTABLISHMENT\nThe applicant shall comply.\n"
    new = FM + "## 4. ADULT ESTABLISHMENT\nThe applicant may comply.\n"
    assert nz.changed_line_count(old, new, amap=IDENTITY, smap={7: {3: 4}}) == 2


def test_a_retargeted_reference_still_counts():
    """Decision D8. §3 FARMING is inserted, so ADULT moves 3 -> 4. A reference
    that still says `Section 3` now points at FARMING -- different content. The
    map turns the old side's reference into `Section 4`, so it differs."""
    old = FM + "## 3. ADULT\n## 4. AMUSE\nSee Section 3.\n"
    new = FM + "## 3. FARMING\n## 4. ADULT\n## 5. AMUSE\nSee Section 3.\n"
    count = nz.changed_line_count(old, new, amap=IDENTITY, smap={7: {3: 4, 4: 5}})
    assert count == 3          # the inserted heading, and the reference line both ways


def test_the_count_drops_to_the_real_figure_for_an_insertion():
    """Only the inserted section is a real change. Without the map, every
    shifted heading and reference counts too."""
    old = FM + ("## 1. GENERAL\nSee Section 2 and Section 3.\n"
                "## 2. ADULT\nText A. See Section 3.\n"
                "## 3. AMUSE\nText B.\n")
    new = FM + ("## 1. GENERAL\nSee Section 3 and Section 4.\n"
                "## 2. FARMING\nNew text.\n"
                "## 3. ADULT\nText A. See Section 4.\n"
                "## 4. AMUSE\nText B.\n")
    smap = {7: {2: 3, 3: 4}}
    assert nz.changed_line_count(old, new, amap=IDENTITY, smap=smap) == 2  # `## 2. FARMING`, `New text.`
    assert nz.changed_line_count(old, new, amap=IDENTITY) > 2               # the control


def test_the_two_paths_still_agree_with_a_map():
    """normalize() and changed_line_count() must apply the rule identically, or
    the operator's number and the packet's marks part company."""
    old = FM + "## 2. ADULT\nSee Section 2.\n## 3. AMUSE\n"
    new = FM + "## 2. FARMING\n## 3. ADULT\nSee Section 3.\n## 4. AMUSE\n"
    smap = {7: {2: 3, 3: 4}}
    comparison = nz._marked(
        nz.normalize(old, amap=IDENTITY, is_baseline_side=True, smap=smap).splitlines(),
        nz.normalize(new, amap=IDENTITY, is_baseline_side=False, smap=smap).splitlines())
    assert comparison == 1     # the inserted heading; and the paths must agree on it
    assert comparison == nz.changed_line_count(old, new, amap=IDENTITY, smap=smap)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_normalize_for_diff.py -k "section or statut or retarget or insertion or two_paths or real_amendment_beside or without_frontmatter or without_a_map" -v`
Expected: they FAIL with `TypeError: … got an unexpected keyword argument 'smap'` or `AttributeError: … has no attribute 'normalize_sections_only'`.

- [ ] **Step 3: Add the rule**

In `build/normalize_for_diff.py`, after Rule 5's `_FRONTMATTER_ARTICLE_NUMBER` definition, add:

```python
# Rule 6. Section renumbering. When a section is inserted into an Article,
# every later `## N.` heading and every reference to it shifts by one. The map
# comes from build/section_map.py, which DERIVES it by aligning heading titles
# -- only an identical, unambiguous, in-order title at a new number is mapped.
#
# Narrowness, in two layers, for a BARE reference (`Section N`, `§N`,
# `Sections A, B, and C`):
#   1. The number is rewritten only if it is a KEY in the containing Article's
#      map. The containing Article is read from the text's own frontmatter.
#   2. It is never rewritten when a statute token occurs within 40 characters
#      before it. The map alone is not enough: Article 7 has 66 sections, so
#      `Subchapter C, §53.11` -- a federal-regulations citation in Article 7 --
#      would collide with a renumbered §53. The token set is the MEASURED one
#      (2026-10-08): it includes `Public Law` and `Stat.`, because Article 9
#      cites `Public Law 75-412, 50 Stat. 888, Section 8`, which a guard limited
#      to MRSA/M.R.S/Title/U.S.C would have renumbered.
# An EXPLICIT `Article N Section M` / `Article N §M` resolves against Article N's
# map and is not statute-guarded: the `Article N` prefix is decisive, and the
# corpus has lines carrying both kinds (`23 MRSA §3026-A and Article 8 §27`).
_SECTION_REF = re.compile(
    r"(?P<explicit>\bArticle (?P<art>\d+) (?:Section |§))(?P<n1>\d+)"
    r"|(?P<plural>\bSections )(?P<list>\d+[A-Za-z0-9.]*"
    r"(?:(?:,\s*(?:and\s+)?|\s+and\s+|\s+through\s+)\d+[A-Za-z0-9.]*)*)"
    r"|(?P<bare>\bSection |§)(?P<n2>\d+)"
)
_LIST_NUMBER = re.compile(r"(?<![A-Za-z0-9.])(\d+)")
_H2_NUMBER = re.compile(r"^(## )(\d+)(\. )", re.MULTILINE)
_OF_ARTICLE = re.compile(r"[A-Za-z0-9.]*\s+of\s+Article\s+\d")   # `Section N[.X.n] of Article M`
_STATUTE_CONTEXT = re.compile(
    r"MRSA|M\.R\.S|Title|U\.S\.C|Public Law|Stat\.|Chapter|Subchapter|C\.F\.R|CFR|Regulations")
STATUTE_LOOKBEHIND = 40
```

Then, after `_renumber_frontmatter`, add:

```python
def _section_renumber(text: str, smap) -> tuple[str, int]:
    """Rule 6, returning the text and how many numbers it actually changed."""
    if not smap:
        return text, 0
    fm = _FRONTMATTER_ARTICLE_NUMBER.search(text)
    containing = int(fm.group(2)) if fm else None
    changed = 0

    def lookup(article, n: int) -> int:
        nonlocal changed
        new = smap.get(article, {}).get(n, n) if article is not None else n
        if new != n:
            changed += 1
        return new

    out = _H2_NUMBER.sub(
        lambda h: f"{h.group(1)}{lookup(containing, int(h.group(2)))}{h.group(3)}", text)

    def statute_before(pos: int) -> bool:
        return bool(_STATUTE_CONTEXT.search(out[max(0, pos - STATUTE_LOOKBEHIND):pos]))

    def repl(r: re.Match) -> str:
        if r.group("explicit"):
            return r.group("explicit") + str(lookup(int(r.group("art")), int(r.group("n1"))))
        if containing is None or statute_before(r.start()):
            return r.group(0)
        if r.group("plural"):
            return r.group("plural") + _LIST_NUMBER.sub(
                lambda k: str(lookup(containing, int(k.group(1)))), r.group("list"))
        if _OF_ARTICLE.match(out, r.end()):
            return r.group(0)          # `Section N of Article M`: a reference INTO another Article
        return r.group("bare") + str(lookup(containing, int(r.group("n2"))))

    return _SECTION_REF.sub(repl, out), changed


def _renumber_sections(text: str, smap) -> str:
    return _section_renumber(text, smap)[0]


def normalize_sections_only(text: str, *, smap) -> str:
    """Render-SAFE: Rule 6 alone, for a draft-to-draft redline.

    A draft-to-draft redline normalises nothing else (redline_resolve.py keeps
    that path raw), but a section inserted between two drafts shifts headings
    and references just as one inserted at an adoption does. Rule 6 rewrites
    only digits in fixed positions, so it never touches line structure.
    """
    return _renumber_sections(text, smap)
```

Change `normalize`'s signature to `def normalize(text: str, *, amap, is_baseline_side: bool, smap=None) -> str:` and its baseline branch to:

```python
    out = _heading_case(text)
    if is_baseline_side:
        out = _renumber_sections(out, smap)   # FIRST: keyed on baseline article numbers
        out = amap.renumber(out)
        out = _renumber_tables(out, amap)
        out = _renumber_frontmatter(out, amap)
    return _rewrap(out)
```

Change `normalize_old_side`'s signature to `def normalize_old_side(text: str, *, amap, smap=None) -> str:` and its body to:

```python
    out = _heading_case(text)
    out = _renumber_sections(out, smap)       # FIRST: keyed on baseline article numbers
    out = amap.renumber(out)
    out = _renumber_tables(out, amap)
    out = _renumber_frontmatter(out, amap)
    return out
```

Add one sentence to each of those two docstrings saying that Rule 6 applies when an `smap` is given and runs first because the map is keyed on baseline article numbers.

Change `changed_line_count`'s signature to `def changed_line_count(old: str, new: str, *, amap, smap=None) -> int:` and its first line of body to:

```python
    o = normalize_old_side(old, amap=amap, smap=smap).splitlines()
```

Finally, extend the module docstring: after the paragraph that ends "Articles 1, 5, 6, and 7 report ZERO substantive changes.", add a paragraph naming Rule 6, its derived map, and the two layers of narrowness, in the same plain register as the paragraphs around it.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_normalize_for_diff.py -v`
Expected: every test passes, the new ones and every pre-existing one.

- [ ] **Step 5: Prove the guards held**

```bash
git diff --stat main -- build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py
python3 build/baseline_selfcheck.py; echo "rc=$?"
python3 -m pytest build/tests -q
```
Expected: the `git diff` prints nothing; `baseline_selfcheck.py` prints `0 marked lines` and `rc=0` — the scope document's second control: with the shipped map and **no** section map, the rollover guard is undisturbed; the suite reports about 244 passed (217 + 27). Report what you see.

- [ ] **Step 6: Commit**

```bash
git add build/normalize_for_diff.py build/tests/test_normalize_for_diff.py
git commit -m "$(cat <<'EOF'
normalize: suppress section renumbering on the old side (Rule 6)

A section inserted into an Article shifts every later heading and every
reference to it. With a derived section map, those are now rewritten on the
OLD side only, so they stop counting as amendments -- and a real amendment
beside a renumbered heading, or a reference retargeted at different content,
still counts.

Two layers of narrowness for bare references: the number must be a key in the
containing Article's map, and no statute token may precede it. The token set is
the measured one, including `Public Law` and `Stat.` for Article 9's federal
citations, which a guard limited to state-statute tokens would have renumbered.
An explicit `Article N Section M` resolves against Article N and bypasses the
guard, because the corpus has lines carrying both kinds.

Opt-in: with no map every existing call is unchanged, and baseline_selfcheck
still reports 0 marked lines.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Wire it into the resolver, and make `report()` honest

**Files:**
- Modify: `build/normalize_for_diff.py:229-250` (`report`)
- Modify: `build/redline_resolve.py`
- Modify: `build/tests/test_normalize_for_diff.py`
- Modify: `build/tests/test_redline_resolve.py`

**Interfaces:**
- Consumes: Task 2's `section_map.check` and `section_map.load`; Task 4's `normalize_old_side(…, smap=)`, `normalize_sections_only` and `_section_renumber`.
- Produces:
  - `report(old, new=None, *, amap, smap=None) -> dict[str, int]` — keys `heading_case`, `renumber`, `tables`, `frontmatter`, `sections`, plus `rewrap` **only** when `new` is given (it compares both sides).
  - `redline_resolve.py <basename> <old-ver> <out> [--baseline] [--section-map PATH --new-dir DIR] [--report]` — opt-in; `--section-map` without `--new-dir` is refused (exit 1, nothing written). **Wiring `--section-map` into `build/redline-stage.sh` and the release driver is P13's work, not this task's.**

**Why `report()` changes.** `build/ADOPTION-SPEC.md:155` says the module "reports what each rule suppressed, by count". It reported three of five: table-number and frontmatter suppressions were never counted, and it was called by one test and no production code. A suppressed mark is honest only if a reader can be shown the count.

**Why the draft path needs the map too.** A Right-to-Farm redline compares `v1.1-draft` against `v1.0` **without** `--baseline` — the draft path, which normalises nothing. A section inserted there shifts headings exactly as one inserted at an adoption does. So `--section-map` applies on both paths: on the draft path it applies Rule 6 **alone**, keeping that path otherwise raw.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_normalize_for_diff.py`:

```python
# --- The report counts every rule ----------------------------------------------
# ADOPTION-SPEC.md:155 says the module reports what EACH rule suppressed. It
# counted three of five. Each test below triggers exactly ONE rule and asserts
# that rule's count and the others' zeros -- so a key that miscounts fails.

def _only(r, key):
    return {k: v for k, v in r.items() if v} == {key: r[key]}


def test_report_counts_table_renumbering():
    r = nz.report("See TABLE 6.1 Design Standards.\n", amap=AMAP)
    assert r["tables"] == 1 and _only(r, "tables")


def test_report_counts_frontmatter_renumbering():
    r = nz.report('---\narticle-number: "6"\n---\n', amap=AMAP)
    assert r["frontmatter"] == 1 and _only(r, "frontmatter")


def test_report_counts_section_renumbering():
    r = nz.report(FM + "See Section 3.\n", amap=AMAP, smap={7: {3: 4}})
    assert r["sections"] == 1


def test_report_omits_rewrap_without_a_new_side():
    """rewrap compares BOTH sides; the resolver has only the old one."""
    assert "rewrap" not in nz.report("x\n", amap=AMAP)
    assert "rewrap" in nz.report("x\n", "x\n", amap=AMAP)
```

`FM` is the frontmatter constant Task 4 defined in this file.

Append to `build/tests/test_redline_resolve.py`:

```python
# --- --section-map and --report -------------------------------------------------

import json  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import section_fixtures as fx  # noqa: E402


def _map_for_an_insertion(tmp_path):
    """A real derived map: Article 7 with a section inserted at §3."""
    tree = fx.copy_source(tmp_path / "src")
    art7 = tree / "article-07-use-standards.md"
    art7.write_text(fx.insert_section(art7.read_text(), 3, "AGRICULTURE"))
    out = tmp_path / "map.json"
    r = subprocess.run([sys.executable, str(REPO / "build" / "section_map.py"), "derive",
                        "v1.0", "--new-dir", str(tree), "--out", str(out)],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    return out, tree


def test_the_draft_path_is_byte_identical_to_git_without_a_map(tmp_path):
    """The existing draft-path test only checks the length is over 1,000. This
    checks the content, so a change to the raw path cannot pass unnoticed."""
    out = tmp_path / "old.md"
    r = run("article-07-use-standards.md", "v1.0", str(out))
    assert r.returncode == 0, r.stderr
    expected = subprocess.run(["git", "-C", str(REPO), "show",
                               "v1.0:source/article-07-use-standards.md"],
                              capture_output=True, text=True).stdout
    assert out.read_text() == expected


def test_the_draft_path_applies_ONLY_rule_6_with_a_map(tmp_path):
    smap_path, tree = _map_for_an_insertion(tmp_path)
    out = tmp_path / "old.md"
    r = run("article-07-use-standards.md", "v1.0", str(out), "--section-map", str(smap_path),
            "--new-dir", str(tree))
    assert r.returncode == 0, r.stderr
    raw = subprocess.run(["git", "-C", str(REPO), "show",
                          "v1.0:source/article-07-use-standards.md"],
                         capture_output=True, text=True).stdout
    sys.path.insert(0, str(REPO / "build"))
    import normalize_for_diff as nz
    import section_map
    assert out.read_text() == nz.normalize_sections_only(raw, smap=section_map.load(smap_path))
    assert "## 4. ADULT ESTABLISHMENT" in out.read_text()     # and it really moved


def test_a_map_for_a_different_old_ref_is_refused_and_nothing_written(tmp_path):
    smap_path, tree = _map_for_an_insertion(tmp_path)
    out = tmp_path / "old.md"
    r = run("article-07-use-standards.md", "v0.24-draft", str(out), "--section-map", str(smap_path),
            "--new-dir", str(tree))
    assert r.returncode == 1
    assert "section map refused" in r.stderr
    assert not out.exists()


def test_a_map_without_its_tree_is_refused_and_nothing_written(tmp_path):
    """A map is valid only for the tree it was derived against. Without
    --new-dir the resolver cannot check that, so it refuses rather than apply
    a possibly stale map -- which could hide a retargeted reference (D8)."""
    smap_path, _ = _map_for_an_insertion(tmp_path)
    out = tmp_path / "old.md"
    r = run("article-07-use-standards.md", "v1.0", str(out), "--section-map", str(smap_path))
    assert r.returncode == 1
    assert "--new-dir" in r.stderr
    assert not out.exists()


def test_report_is_opt_in(tmp_path):
    out = tmp_path / "old.md"
    r = run("article-08-administration.md", "v0.1-baseline", str(out), "--baseline")
    assert r.returncode == 0, r.stderr
    assert "suppressed" not in r.stderr


def test_report_names_every_rule_on_the_baseline_path(tmp_path):
    out = tmp_path / "old.md"
    r = run("article-08-administration.md", "v0.1-baseline", str(out), "--baseline", "--report")
    assert r.returncode == 0, r.stderr
    line = next(l for l in r.stderr.splitlines() if "suppressed" in l)
    for key in ("heading_case=", "renumber=", "tables=", "frontmatter=", "sections="):
        assert key in line, key
```

Read the top of `build/tests/test_redline_resolve.py` first: confirm `run`, `REPO`, `sys`, `Path` and `subprocess` are already defined or imported there, and that the module pins the pre-rollover `ADOPTION_MAP` the way `test_normalize_for_diff.py` does — the `--baseline` tests against `v0.1-baseline` depend on it. Add only the imports that are missing, and say what you added.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest build/tests/test_normalize_for_diff.py build/tests/test_redline_resolve.py -k "report or section_map or draft_path or different_old_ref" -v`
Expected: the `report` tests FAIL on the missing `tables`/`frontmatter`/`sections` keys or on `rewrap` always being present; the resolver tests FAIL with argparse rejecting `--section-map` / `--report`. `test_the_draft_path_is_byte_identical_to_git_without_a_map` and `test_report_is_opt_in` may PASS already — they are the default-preservation controls. Say which passed.

- [ ] **Step 3: Make `report()` count every rule**

Replace `report` in `build/normalize_for_diff.py` with:

```python
def report(old: str, new: str | None = None, *, amap, smap=None) -> dict[str, int]:
    """How many differences each rule suppressed, counted from the OLD side.

    Every rule normalize_old_side() applies is counted: heading case, Article
    references, table numbers, frontmatter, and -- when a section map is given
    -- section numbers. `rewrap` compares BOTH sides, so it appears only when
    `new` is given; the resolver has only the old side, and normalize_old_side
    does not rewrap anyway.

    ADOPTION-SPEC.md:155 promises these counts. Until 2026-10-08 the table and
    frontmatter rules were never counted. A suppressed mark is honest only if a
    reader can be shown how many there were.

    NOTE: the heading_case count is the number of baseline headings whose
    leading letter is uppercase -- exactly the ones the rule rewrites. (A count
    of matches before and after normalising `old` against itself was always
    zero, since case never changes how many headings match.)
    """
    def shifted(n: int) -> bool:
        return amap.article_numbers.get(n, n) != n

    counts = {
        "heading_case": sum(1 for m in _HEADING_LETTER.finditer(old) if m.group(2).isupper()),
        "renumber": sum(1 for m in re.finditer(r"\bArticle (\d+)\b", old)
                        if shifted(int(m.group(1)))),
        "tables": sum(1 for m in _TABLE_NUM.finditer(old) if shifted(int(m.group(2)))),
        "frontmatter": sum(1 for m in _FRONTMATTER_ARTICLE_NUMBER.finditer(old)
                           if shifted(int(m.group(2)))),
        "sections": _section_renumber(old, smap)[1],
    }
    if new is not None:
        counts["rewrap"] = len(_WS_RUN.findall(old)) + len(_WS_RUN.findall(new))
    return counts
```

Confirm the existing `test_report_counts_each_rule_separately` still passes — it calls `report(old, new, amap=AMAP)` and asserts only `heading_case` and `renumber`.

- [ ] **Step 4: Add the resolver flags**

In `build/redline_resolve.py`, add `import section_map  # noqa: E402` beside the existing `import normalize_for_diff as nz`.

After the `--baseline` argument, add:

```python
    ap.add_argument("--section-map", default=None,
                    help="a map from build/section_map.py derive: renumbered sections "
                         "are suppressed on the old side (both paths)")
    ap.add_argument("--new-dir", default=None,
                    help="the tree the map was derived against; required with --section-map")
    ap.add_argument("--report", action="store_true",
                    help="print what each normalisation rule suppressed, to stderr")
```

Immediately after `a = ap.parse_args()`, add:

```python
    smap = None
    if a.section_map:
        if not a.new_dir:
            print(f"{a.basename}: --section-map requires --new-dir: a map is only "
                  f"valid for the tree it was derived against", file=sys.stderr)
            return 1
        problems = section_map.check(a.section_map, a.old_ver, a.new_dir)
        if problems:
            for p in problems:
                print(f"{a.basename}: section map refused -- {p}", file=sys.stderr)
            return 1
        smap = section_map.load(a.section_map)
```

Replace the non-baseline branch with:

```python
    if not a.baseline:
        # Historical behaviour, untouched: same filename at the old tag. With a
        # section map, Rule 6 alone -- the draft path normalises nothing else.
        text = git_show(a.old_ver, f"source/{a.basename}")
        if text is None:
            return 3
        if smap:
            if a.report:
                print(f"{a.basename}: suppressed sections={nz._section_renumber(text, smap)[1]}",
                      file=sys.stderr)
            text = nz.normalize_sections_only(text, smap=smap)
        Path(a.out_path).write_text(text)
        return 0
```

Replace the final write at the end of `main` with:

```python
    if a.report:
        r = nz.report(text, amap=amap, smap=smap)
        print(f"{a.basename}: suppressed " + " ".join(f"{k}={v}" for k, v in r.items()),
              file=sys.stderr)
    # normalize_old_side, NOT normalize: this text is what gets RENDERED (the
    # old side of redline-text.py --source), and normalize()'s rewrap rule
    # flattens indented sub-clauses into run-on prose when it reaches a
    # renderer. See normalize_for_diff.py's module docstring.
    Path(a.out_path).write_text(nz.normalize_old_side(text, amap=amap, smap=smap))
    return 0
```

Update the module docstring's last paragraph: draft-to-draft redlines keep the historical behaviour **unless a section map is given**, in which case Rule 6 alone is applied.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest build/tests/test_normalize_for_diff.py build/tests/test_redline_resolve.py -v`
Expected: all pass, including every pre-existing test — in particular `test_without_baseline_flag_it_uses_the_same_filename`, the draft-path guarantee the scope document says must not break.

- [ ] **Step 6: Prove the invariant and run the full suite**

```bash
git diff --stat main -- build/adoption-map.json build/adoption_map.py build/baseline_selfcheck.py
python3 build/baseline_selfcheck.py; echo "rc=$?"
python3 -m pytest build/tests -q
```
Expected: the `git diff` prints nothing; `0 marked lines`, `rc=0`; the suite reports about 253 passed (244 + 9). Report what you see.

- [ ] **Step 7: Commit**

```bash
git add build/normalize_for_diff.py build/redline_resolve.py build/tests/test_normalize_for_diff.py build/tests/test_redline_resolve.py
git commit -m "$(cat <<'EOF'
redline: opt-in --section-map and --report on the resolver; count every rule

--section-map applies a derived map on BOTH paths. A Right-to-Farm redline runs
on the draft path, which normalises nothing, and a section inserted there
shifts headings exactly as one inserted at an adoption does -- so on that path
Rule 6 is applied alone, keeping it otherwise raw. A map derived for a
different old ref is refused before anything is written.

report() now counts every rule the old side applies. ADOPTION-SPEC.md:155
promised per-rule counts; table and frontmatter suppressions were never
counted, and nothing outside a test called it. --report prints them.

Both flags are opt-in: with neither, the resolver's output and stderr are
unchanged. Threading --section-map through redline-stage.sh and the release
driver is P13's work.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Done when

- `build/section_map.py derive` produces a map of exactly the pure renumberings, failing closed below the similarity floor; `check` refuses a map for another ref or tree; `selfcheck` refuses a map whose entries pair differently-titled headings.
- `normalize_for_diff.py` applies Rule 6 on the old side only, with no statutory citation ever rewritten and a real amendment or retargeted reference always still counted.
- `changed_line_count` counts every changed line, including ones beginning with `--` or `++`.
- `report()` counts every rule; `redline_resolve.py` takes opt-in `--section-map` and `--report`.
- `build/adoption-map.json`, `build/adoption_map.py`, `build/baseline_selfcheck.py` are byte-identical to `main`, and `baseline_selfcheck.py` still reports 0 marked lines.
- The full suite passes; CI is green on the PR.

## Not in this plan

- **Threading `--section-map` through `build/redline-stage.sh` and `build-release.sh`** — P13, which also decides how an operator supplies a hand entry when `derive` fails closed.
- **Lettered `### x.` sub-section renumbering** — out of scope; such shifts stay visible.
- **`build/ADOPTION-SPEC.md`'s normaliser description** — P18.
- **The font dependency** (Barlow italics and the use-table symbols coming from the operator's machine) — a separate decision, recorded in `CLAUDE.md`.
