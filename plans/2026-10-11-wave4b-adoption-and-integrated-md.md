# Wave 4b — The Integrated Markdown, the Cover Facts, and Adoption Through the Driver

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The integrated `.md` — the document the Town adopts — becomes as honest and readable as the extracts; the draft cover stops stating 2025 facts; `build-adoption.sh` freezes a Town Meeting packet through `build-release.sh` (so it ships what the change determination says, not a hard-coded Article 3); `pdf_recap` asserts instead of only printing; and `ADOPTION-SPEC.md` describes the machinery that exists.

**Architecture:** `build/integrated_md.py` assembles the integrated `.md` from each Article's frontmatter plus `czc_md.body_markdown`, with Article 2's generated district appendix — **mode-independent**, so the adopted edition's identity gate still compares bodies byte for byte. `adoption-map.json` gains the baseline's amended-through date, and `build-cover.py` generates the draft and meeting facts from it, masking the scanned date line whenever the baseline is newer than the scan. `release_plan.py` and `build-release.sh` gain meeting mode (old ref = the adopted baseline, the baseline-mode redline, meeting names). `build-adoption.sh` keeps its own gates and calls the driver.

**Tech Stack:** bash, Python 3.14, PyMuPDF, pytest.

**Spec:** `specs/2026-10-07-release-deliverables-scope.md` §2 P13 (the `build-adoption.sh` paragraph and `combined_md.py`), P18, §0 decisions D2, D5, D6. Ben Frey's rulings of 2026-10-11 (Wave 4 split 4a/4b/4c).

## Global Constraints

- **NEVER commit unless explicitly asked.** The operator authorises this plan's commit steps: implementers commit locally, by name, on branch `wave4b-adoption-and-integrated-md`. Nothing is pushed. **No `git stash`.**
- **NEVER `git add -A` or `git add .`** — stage files by name.
- **Never modify anything in `docs/`, `releases/` or `source/`.** Tests write only under `tmp_path`; nothing builds into the real `releases/`.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` (project standing rule 5).
- Build tests: `python3 -m pytest build/tests -q` — **640** at the start, ~12 min; CI on Linux with Typst 0.14.2. Report the count you see.
- **⛔ Nothing may claim adoption before the vote.** `version_state.py` is the only thing standing between an env var and a document that claims adoption; never bypass it.
- **The adopted body must stay mode-independent**: `build-adopted.sh` compares the committed meeting `.md` with a fresh adopted `.md` after stripping only frontmatter blocks of exactly the keys `article-number`, `article-name`, `footer-date`. Nothing mode-dependent may appear outside those blocks.
- **Untouched by this wave:** `build/section_map.py`, `build/normalize_for_diff.py`, `build/redline_resolve.py`, `build/czc_diff.py`, `build/structural_note.py`, `build/use_table_changes.py`, `build/split-article-03.py`, `build/adoption-footer.sh`, `build/adoption-name.sh`, `build/build-adopted.sh`, `build/adopted_residue.py`, `build/version_state.py`, `build/baseline_selfcheck.py`, `build/permit-review/`.
- **Never pin the live working tree.** Trees come from `section_fixtures.copy_full_source(dest)` (the v1.0 tag). Draft test version `v0.98-draft`; adoption test version `v9.0` (meeting date "May 1, 2027").
- **Measured facts** (2026-10-11, HEAD c5d6a0b — full detail in the Wave 4b facts sweep):
  - `build-full-czc.sh:358-423` assembles the `.md` by concatenating each pandoc-rendered Article's source (frontmatter intact), swapping Article 3's split markers for long HTML comments and appending HTML-comment pointers after Articles 1 and 2. A built draft `.md` carries 4 raw `{=typst}` blocks, 5 HTML comments, 9 frontmatter blocks and **no district pages**. The assembly is mode-independent today.
  - `czc_md.body_markdown(nn, text, *, src_dir, doc)` (Wave 4a) strips frontmatter, converts the raw-Typst tables, replaces split markers with pointer notes, drops comments, appends after-prose pointers — never the appendix. `czc_md.APPENDICES[2](src_dir)` returns Article 2's 13-district appendix.
  - `build-cover.py:134-153` BANNERS: draft line 2 `"{version}  ·  includes proposed Article 3: Thoroughfares"`, line 3 `"Generated {date_str} from the adopted Core Zoning Code (amended through March 24, 2025).\nFor review only — not a certified copy."`. Adopted mode masks the scanned `AMENDED THROUGH: MARCH 24, 2025` line (`AMENDED_RECT = Rect(386, 721.0, 566, 733.8)`) and reprints `AMENDED THROUGH: <EVENT DATE>`; `test_cover_modes.py` pins it with a pixel test over `STALE_STRIP = Rect(388, 721, 408, 734)` (adopted → 0 ink with a short date; draft and meeting are the positive controls).
  - **No machine-readable record of v1.0's adoption date exists.** `adoption-map.json` has `baseline_version: "v1.0"` and a `_README` saying it rolled over on September 14, 2026; `releases/v1.0/frozen-from.json` has only the *meeting* date.
  - `build-adoption.sh <version> <meeting-date> [--dry-run] [--freeze-date=]`: gates (version_state adoption, `baseline_selfcheck`, breakdown print, `--dry-run` exit, dirty-`source/` refusal), then builds the meeting edition, the baseline redline (`ADOPTION_BASELINE=1`), a **hard-coded** standalone Article 3, `frozen-from.json`, a **stale** Summary heredoc ("amended through March 24, 2025", "old 3-8 become 4-9", "Article 3 is entirely new") or — if the Summary already exists — its PDF, and `pdf_recap`. It never builds the Use Table Changes memo. `test_build_adoption.py::test_freeze_expects_the_standalone_name_the_builder_actually_writes` extracts the hard-coded standalone line verbatim.
  - `build-release.sh` refuses `ADOPTION_MODE` ≠ draft but **does not refuse or unset an inherited `ADOPTION_BASELINE` or `ADOPTION_EVENT_DATE`**; `release_plan.py:223` hard-codes `"mode": "draft"` and names with `draft`.
  - `pdf_recap.py` prints `(pages, blanks)` per PDF and always returns 0; callers: `build-adoption.sh:255`, `build-adopted.sh:194`, `build-release.sh:288` (`|| true`).
  - `ADOPTION-SPEC.md` is stale at :3 ("Not yet implemented"), §3.1, §3.2, §3.3, §4.3, §6.2, §6.3, §6.5 and §7 (:380-382) — see Task 5.

### Ten rulings this plan makes in writing

1. **The integrated `.md` keeps each Article's frontmatter block exactly as the source has it** (the three keys the identity gate strips) and replaces its body with `czc_md.body_markdown`, plus, for Article 2, the generated district appendix in place of the pointer (D2's reasoning applies with more force to the document that governs). **No title, provenance or mode line** — the mode lives in the file name and the PDF cover, never in the body.
2. **The baseline's amended-through date is recorded data**: `adoption-map.json` gains `"baseline_amended_through": "September 14, 2026"` (the day v1.0 was adopted); `adoption_map.AdoptionMap.baseline_amended_through` exposes it; the v0.1-baseline fixture map (`build/tests/fixtures/adoption-map-v0.1-baseline.json`) gains `"March 24, 2025"`. The rollover instructions in CLAUDE.md say to set it at every adoption.
3. **Draft cover facts are generated**: line 2 becomes `"{version}  ·  proposed amendments to the Core Zoning Code"`; line 3 becomes `"Generated {date} from the Core Zoning Code as amended through {baseline_amended_through}.\nFor review only — not a certified copy."`. Meeting mode is unchanged in wording.
4. **The scanned AMENDED THROUGH line is masked and reprinted with the baseline's date in draft and meeting mode whenever that date is not the scan's own (March 24, 2025)**; adopted mode keeps reprinting the adoption date. With the v0.1 fixture map, draft and meeting stay unmasked — that remains the pixel test's positive control.
5. **The driver gains meeting mode**, entered only by `ADOPTION_MODE=meeting` with `ADOPTION_EVENT_DATE` set: the version must be an adoption version; `--old-ver` must equal `adoption_map.baseline_version`; the integrated redline is built with `ADOPTION_BASELINE=1`; names come from `meeting` mode; the plan records `"mode": "meeting"` and `"event_date"`; the Summary skeleton opens "For adoption at Town Meeting, {date}". **In draft mode the driver refuses an inherited `ADOPTION_BASELINE` or `ADOPTION_EVENT_DATE`.** Adopted mode is still refused (D5).
6. **`build-adoption.sh` freezes through the driver**: it keeps its own argv and gates (version state, `baseline_selfcheck`, breakdown, `--dry-run`, the dirty-`source/` refusal), gains `--calls FILE` (passed through), calls `ADOPTION_MODE=meeting ADOPTION_EVENT_DATE=<meeting date> build-release.sh <v> <freeze date> --old-ver=<baseline>`, then writes `frozen-from.json` into the placed packet. Its stale Summary heredoc and its hard-coded Article 3 standalone are deleted. The packet therefore carries a standalone + standalone redline for every SUBSTANTIVE Article and the Use Table Changes memo when district data moved (standing rule 4).
7. **Rendering the hand-written Summary is its own step**: `build-adoption.sh <v> <meeting-date> --render-summary` renders `Summary of Changes <v>.pdf` from an existing hand-written `.md` in the frozen packet and does nothing else (refuses if the packet or the `.md` is missing, or the `.md` is still the generated skeleton — detected by the skeleton's placeholder comment). This replaces "re-run with the same `--freeze-date`", which the driver's existing-directory refusal now forbids.
8. **`pdf_recap` asserts**: exit 1 on a PDF that cannot be opened or has zero pages, after printing every line; callers stop swallowing its status (`build-release.sh`'s `|| true` goes). Blank-page counts stay a report — `release_gate.py` already owns pagination.
9. **The spec is revised to match the code**, and two agreement tests keep it there: the packet list in `ADOPTION-SPEC.md` §3.3 names exactly the artifact kinds `release_plan.py` can plan; every gate §6.1 names is reachable by name from `build-adoption.sh`, `build-release.sh` or `build-adopted.sh`. Each has a negative control.
10. **v1.0 cannot be re-adopted** (already true since Wave 3c; this wave's `.md` change makes it doubly so). Said in `ADOPTION-SPEC.md` §7 and CLAUDE.md; no code works around it.

## Review Focus

1. **The meeting and adopted integrated `.md` bodies must be byte-identical after the identity gate's strip.** Pinned in Task 1.
2. **Nothing in meeting mode may claim adoption, and nothing in draft mode may leak baseline-mode redlining.** Pinned in Tasks 3 and 4.
3. **A frozen packet must carry what the determination says** — no hard-coded Article. Pinned in Task 4.
4. **The cover's stale line must be gone in every mode once the baseline is newer than the scan, and still present with the v0.1 map** (the positive control). Pinned in Task 2.
5. **The spec's packet list and the planner's artifact kinds must not drift apart silently.** Pinned in Task 5.

---

## Task 1: The integrated markdown

**Files:** Create `build/integrated_md.py`, `build/tests/test_integrated_md.py`. Modify `build/build-full-czc.sh` (the `.md` assembly only, :351-423).

**Interfaces — Produces:** `integrated_md.render(src_dir: Path, *, doc=None) -> str`; CLI `python3 build/integrated_md.py <src-dir> <out.md>` (exit 0 written / 1 refused, nothing written). `build-full-czc.sh` writes `$COMBINED_MD` through it.

- [ ] **Step 1: Failing tests** over a `copy_full_source` tree:
  - the `.md` has exactly nine frontmatter blocks, each byte-identical to its source file's frontmatter, in Article order 1–9;
  - no `{=typst}`, no `<!--`; Article 3's `TABLE 3.2 SIGHT DISTANCE` is a pipe table; the Type-pages and Exhibit pointer notes sit where the markers were;
  - Article 2's appendix is present once (`## Appendix — District Standards`, 13 district headings, 819 use rows — reuse `test_czc_md.py`'s row counter) between Article 2 and Article 3;
  - Article 1 ends with the District Maps pointer note;
  - **identity**: build the integrated Code twice from the same tree — `ADOPTION_MODE=meeting ADOPTION_EVENT_DATE="May 1, 2027" build-full-czc.sh v9.0 …` and `ADOPTION_MODE=adopted ADOPTION_EVENT_DATE="May 1, 2027" … v9.0` into temp dirs — and assert the two `.md` files are **byte-identical** (no mode-dependent text anywhere, frontmatter included);
  - the draft `.md` passes `adopted_residue.find_residue` with only `INTEGRATED DRAFT` tolerated (the existing `test_build_adopted.py` expectation) — in fact assert it is empty;
  - a damaged split marker refuses (exit 1, no `.md` written, and `build-full-czc.sh` exits non-zero).
- [ ] **Step 2–4:** fail; implement (`integrated_md.py` reads each `article-0N-*.md` through `manifest`/`czc_md` helpers — no copy of the frontmatter or walker logic; `build-full-czc.sh` replaces the whole python/printf block with one call and keeps its log line); pass.
- [ ] **Step 5:** untouched diff empty; full suite; commit `build/integrated_md.py build/build-full-czc.sh build/tests/test_integrated_md.py`:

```
build: the integrated markdown is the honest document the Town adopts

The integrated .md -- what the Town adopts -- carried Article 3's tables as raw
Typst, build comments where pages belong, and none of Article 2's thirteen
district pages, so it read worse than the extracts that say it governs.
integrated_md keeps each Article's frontmatter and runs every body through
czc_md's walker, with Article 2's generated district appendix in place. It has
no mode-dependent text, so the adopted edition's identity gate still compares
meeting and adopted bodies byte for byte.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task 2: The cover facts come from the baseline

**Files:** Modify `build/adoption-map.json`, `build/adoption_map.py`, `build/tests/fixtures/adoption-map-v0.1-baseline.json`, `build/build-cover.py`, `build/tests/test_cover_modes.py`.

**Interfaces — Produces:** `adoption_map.AdoptionMap.baseline_amended_through: str`; `build-cover.py` reads it (through `adoption_map.load()`, which honours the `ADOPTION_MAP` env seam).

- [ ] **Step 1: Failing tests** in `test_cover_modes.py`:
  - draft cover text contains "proposed amendments to the Core Zoning Code" and "as amended through September 14, 2026", and contains none of "includes proposed Article 3", "March 24, 2025";
  - **pixel**: with the real map, draft **and** meeting have 0 ink in `STALE_STRIP` (masked; reprinted date "SEPTEMBER 14, 2026" — note its left end: re-measure where the reprinted text starts; if a long date's own ink reaches into `STALE_STRIP`, use a strip that only the stale glyphs occupy and **record the measurement** in the test docstring), and the reprinted text reads `AMENDED THROUGH: SEPTEMBER 14, 2026`;
  - **positive control**: with `ADOPTION_MAP=<the v0.1 fixture>`, draft and meeting are unmasked (ink > 0 in the strip) and the draft text says "as amended through March 24, 2025";
  - adopted mode unchanged (existing tests pass);
  - a map without `baseline_amended_through` → `build-cover.py` refuses (exit 1, message names the field) — never guesses a date;
  - `baseline_selfcheck.py` still passes with the new field (run it).
- [ ] **Step 2–4:** fail; implement (`adoption_map.py`: optional-in-schema but required by `build-cover.py`; `build-cover.py`: BANNERS draft lines per ruling 3; the mask in draft/meeting per ruling 4 using the existing `AMENDED_*` geometry); pass.
- [ ] **Step 5:** untouched diff empty; full suite; commit the five files:

```
cover: the draft cover states the baseline it was generated from

The draft cover still said "includes proposed Article 3" and "amended through
March 24, 2025" -- true before the September 14, 2026 adoption, false since.
The baseline's amended-through date is now recorded in adoption-map.json beside
its version, and the draft and meeting covers state it, masking the scanned
date line when the baseline is newer than the scan (decision D6). With the
v0.1 map the scan is left alone, which keeps the pixel test's positive control.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task 3: The driver in meeting mode

**Files:** Modify `build/build-release.sh`, `build/release_plan.py`, `build/summary_skeleton.py`, `build/tests/test_build_release.py`, `build/tests/test_release_plan.py`, `build/tests/test_summary_skeleton.py`.

**Interfaces:** `release_plan.py` gains `--mode draft|meeting` (default draft) and `--event-date D` (required for meeting); the plan carries `"mode"` and `"event_date"`; names use the mode. `build-release.sh` reads `ADOPTION_MODE` / `ADOPTION_EVENT_DATE` per ruling 5.

- [ ] **Step 1: Failing tests:**
  - release_plan: meeting mode with `v9.0`, `--old v1.0`, `--event-date "May 1, 2027"` → names `Newcastle CZC (Town Meeting Edition v9.0)` and `… (Standalone Town Meeting Edition v9.0)` (compare against `adoption-name.sh` calls, as Task 3 of 4a did); a decimal version in meeting mode refused; meeting without `--event-date` refused; `--old` ≠ the adoption map's baseline refused in meeting mode.
  - summary_skeleton: a meeting plan opens "**For adoption at Town Meeting, May 1, 2027.**" and states changes against "the Code as most recently adopted (v1.0)"; nothing in it says "adopted" about the new version.
  - build-release.sh (stub leaves): draft run with `ADOPTION_BASELINE=1` inherited → refused; with `ADOPTION_EVENT_DATE` inherited → refused; meeting run → the integrated-redline leaf receives `ADOPTION_BASELINE=1`, `ADOPTION_MODE=meeting` and the event date (a stub that records its env), every leaf receives `ADOPTION_MODE=meeting`; meeting with `--old-ver` ≠ baseline → refused; `ADOPTION_MODE=adopted` → refused.
  - **One real meeting release** (`v9.0`, v1.0 tree with an Article 7 edit, `--old-ver=v1.0`, Articles 1–3 not NEEDS-CALL on a v1.0 tree): exit 0; the gate passes; no file name or `.md` body contains "Adopted v9.0" or "ADOPTED" chrome; the meeting edition PDF cover text says "TOWN MEETING EDITION — NOT YET ADOPTED".
- [ ] **Step 2–4:** fail; implement; pass.
- [ ] **Step 5:** untouched diff empty; full suite; commit the six files:

```
build: build-release.sh freezes a Town Meeting packet as well as a draft

The driver now runs in meeting mode when ADOPTION_MODE=meeting and an event
date are set: an adoption version, compared against the adopted baseline, the
redline in baseline mode, the Town Meeting names, and a Summary skeleton that
says the text is for adoption, not adopted. A draft run now refuses an
inherited ADOPTION_BASELINE or ADOPTION_EVENT_DATE, which would otherwise have
reached the redline builder. Adopted mode stays refused (decision D5).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task 4: `build-adoption.sh` freezes through the driver; `pdf_recap` asserts

**Files:** Modify `build/build-adoption.sh`, `build/pdf_recap.py`, `build/build-release.sh` (drop `|| true` on pdf_recap only), `build/tests/test_build_adoption.py`. Create `build/tests/test_pdf_recap.py`.

- [ ] **Step 1: Failing tests:**
  - test_build_adoption: replace `test_freeze_expects_the_standalone_name_the_builder_actually_writes` (it pins the deleted hard-coded line) with a test that `build-adoption.sh` contains no Article number in a build command and calls `build-release.sh` exactly once; `--calls` is passed through (a stubbed driver via a `CZC_LEAF_RELEASE` test seam records its argv); after a stubbed successful driver run, `frozen-from.json` exists in the packet with the existing keys; a dirty `source/` is still refused **before** the driver runs; `--dry-run` still exits before any build; the stale strings "March 24, 2025", "3-8 become 4-9", "entirely new" no longer appear in `build-adoption.sh`.
  - `--render-summary`: with a packet dir holding a hand-written Summary `.md` → renders the `.pdf` only (stub `build-memo.sh` via a seam or a real 1-page memo); with the generated skeleton still in place → refused; with no packet → refused.
  - test_pdf_recap: a good PDF → exit 0 and its line printed; an unopenable file and a zero-page PDF → exit 1 after printing every line.
- [ ] **Step 2–4:** fail; implement per rulings 6–8 (seam `CZC_LEAF_RELEASE` defaults to `build/build-release.sh`, test use only); pass.
- [ ] **Step 5:** untouched diff empty; full suite; commit the five files:

```
build: build-adoption.sh freezes the Town Meeting packet through build-release.sh

The freeze built a hard-coded standalone Article 3 and wrote a Summary skeleton
keyed to the 2025 baseline, and never built the Use Table Changes memo.
build-adoption.sh keeps its own gates -- version state, the baseline
self-check, the dirty-source refusal, frozen-from.json -- and now calls the
release driver in meeting mode, so the packet carries an extract and redline
for every Article that changed in substance and the memo whenever district
tables moved. Rendering the hand-written Summary is its own step
(--render-summary). pdf_recap now fails on a PDF it cannot read.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task 5: `ADOPTION-SPEC.md` matches the code

**Files:** Modify `build/ADOPTION-SPEC.md`. Create `build/tests/test_spec_agreement.py`.

- [ ] **Step 1: Failing tests** (`test_spec_agreement.py`):
  - the §3.3 packet list (a fenced or bulleted list the spec marks with `<!-- PACKET-KINDS -->` … `<!-- /PACKET-KINDS -->`) names exactly the artifact kinds `release_plan.py` can emit (read from a constant `release_plan.ARTIFACT_KINDS` — add it in this task if absent, used by `release_plan.py` itself);
  - **negative control**: a spec text with one extra kind fails the comparison function (test the function, not by editing the real spec);
  - every gate name listed in §6.1 between `<!-- GATES -->` markers appears by name in `build-adoption.sh`, `build-release.sh` or `build-adopted.sh`; negative control with a made-up gate name.
- [ ] **Step 2–4:** fail; revise the spec — :3 status (implemented, adopted v1.0 on September 14, 2026); §3.1 (section map derived, never in `adoption-map.json`, and why; `baseline_amended_through`); §3.2 (old side only; the real rule list incl. section renumbering; conservatism); §3.3 (packet = the driver's plan in meeting mode + `frozen-from.json`; per-Article standalones and redlines in both formats; Use Table Changes; `release-plan.json`, `ships.json`); §4.3 (structural note per Article and code scope); §6.1 (add `baseline_selfcheck`, the dirty-tree refusal, the section-map selfcheck, the release gate); §6.2 (correct the premise: nine frontmatter blocks; the body is mode-independent by construction since Task 1); §6.3 (residue also over `.md` bytes); §6.5 (the release gate refuses pagination; `pdf_recap` asserts readability); §7 (close the standalone-in-adopted item by D5; the footer-date fixed; v1.0 cannot be re-adopted, ruling 10). Plain, short; keep the spec's voice. Pass.
- [ ] **Step 5:** full suite; commit `build/ADOPTION-SPEC.md build/release_plan.py build/tests/test_spec_agreement.py` (release_plan.py only if `ARTIFACT_KINDS` was added):

```
docs: ADOPTION-SPEC.md describes the machinery that adopted v1.0

The spec still said "Not yet implemented" for machinery that shipped an adopted
ordinance, normalised both sides with three rules, and listed a four-item
packet. It now matches the code -- the derived section map, the old-side rule
list, the packet the driver plans, the gates that exist and refuse -- and two
agreement tests, each with a negative control, keep its packet list and gate
list from drifting behind the code again.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Done when

- The integrated `.md` has no raw Typst or build comments, carries Article 2's districts, and is byte-identical between meeting and adopted builds.
- The draft and meeting covers state the baseline's amended-through date; the pixel test's positive control still fires with the v0.1 map.
- `build-adoption.sh` freezes through the driver in meeting mode with its gates intact; the packet follows the determination; `--render-summary` renders the hand-written Summary.
- `pdf_recap` fails on an unreadable PDF; the spec matches the code with agreement tests.
- The untouched files are byte-identical to `main`; the full suite passes; CI is green.

## Not in this plan

- Wave 4c (the fifth status code), after its binding values are decided.
- Re-adopting v1.0 (impossible by design; ruling 10).
- Pinning the renderer in `frozen-from.json` (deferred by Ben, 2026-10-07).
