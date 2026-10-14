# Newcastle Core Zoning Code

Working repo for the Core Zoning Code (CZC) of Newcastle, Maine — a SmartCode-style, form-based
code — and its amendments. Our main addition is **Article 3, "Thoroughfares"**, which replaced the
repealed Road/Driveway/Entrance Ordinance and must match the CZC's look, feel and structure.
Output is camera-ready PDF (pandoc → Typst) plus markdown, released as tagged versions.

Repo: `/Users/ben/Developer/Claude/Projects/Newcastle Core Zoning Code` · remote
https://github.com/benjaminfrey/newcastle-czc.git · branch `main`. User: Ben Frey
<ben@homeportsupply.com>, Planning Board chair and the Town's only in-house GIS capacity. Every
ordinance change needs a Planning Board review and a **Town Meeting vote**, so what we ship is
read by residents and voters, not just by us.

The CZC **v1.0 was adopted on September 14, 2026**. New drafts are redlined against v1.0; the
current draft is **v1.1-draft** (layout only). Past work, wave by wave: `HISTORY.md`.

## Working rules

Ben has asked for each of these; most exist because a mistake here is public or hard to undo.

1. **Commit only when Ben asks.** Build, verify and document, then wait for the go-ahead — he
   reviews what goes into the Town's record.
2. **Stage files by name, never `git add -A` / `git add .`.** The tree holds untracked material
   that must not be swept in (local settings, Ben's docs, scratch).
3. **`docs/*.pdf` are the immutable baseline** (original CZC, Comp Plan, RDEO). Read only.
4. **Release deliverables.** Every release ships the integrated Code (the document the Town
   adopts). Each Article with substantive changes — its own standards, definitions or data — also
   ships as a standalone and a standalone redline, in both `.pdf` and `.md`. Articles touched only
   by renumbering or cross-reference updates are named in the Summary of Changes instead.
   Adoption releases ship the frozen packet, plus a Use Table Changes memo when district tables
   moved. Standalones are extracts and do not govern.
5. **Commit messages end with a `Co-Authored-By:` trailer** naming the Claude model that wrote the
   change, e.g. `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
6. **On release, push `main` and the annotated tag (`vX.Y-draft`) as separate commands.** Never
   force-push without Ben's explicit OK; re-cutting a pushed version means a new number unless he
   says otherwise.
7. **Match the baseline CZC's formatting and typography** — measured in `style/style-analysis.md`.
8. **Nothing may claim adoption before the vote.** See the version-state gotcha below.
9. **Never guess a legal value** (a statute, a use status, a standard). Write it down as an open
   decision for Ben, the Board or counsel instead.

## Repo map

- `source/` — the editable Code: Articles 1–9 as `article-0N-*.md`. Native-Typst units are
  spliced into the pandoc flow at build time: `article-02.typ` (district pages),
  `district-maps.typ` (Article 1), and Article 3's `cross-section-plates.typ` (the 10 Type
  plates), `street-type-inventory.typ` (Exhibit 3.1) and `street-type-map.typ` (Exhibit 3.2).
  Data: `exhibits/cross-sections/types.json`, `exhibits/street-types/inventory.json`.
- `style/` — Typst template (`czc-template.typ`), memo template, fonts, colors, style analysis.
- `build/` — build and release scripts, `article-manifest.json` (which units and data belong to
  which Article), tests in `build/tests/`, the GIS pipeline in `build/street-types/`, the
  permit-review app in `build/permit-review/`.
- `releases/<version>/` — shipped deliverables. Release PDFs are gitignored (rebuild from tags).
- `memos/` — justification and analysis memos, rendered with `build/build-memo.sh`.
- `plans/` — implementation plans; `build/ADOPTION-SPEC.md` — the adoption design (authoritative).
- `docs/` — the baseline (see rule 3).

## The Type system (Article 3)

"Thoroughfare" is the umbrella term; each segment in town gets one binding **Thoroughfare Type**
in the §5 Inventory. Street (S, urban) and Road (R, rural) families: `S1` Main Street · `S2`
Village Street · `S3` Neighborhood Street · `S4` Lane · `S5` Alley · `R1` Connector Road · `R2`
Rural Road · `R3` Rural Lane · `R4` Highway Commercial · `R5` Rural Highway. Legends show only
Types actually present. Districts (Table 3.4): D1 Rural · D2 Neighborhood Residential · D3
Neighborhood Business · D4 Village Residential · D5 Village Business · D6 Town Center.

## Commands

- **Tests:** `python3 -m pytest build/tests -q` — 729 tests, ~15–20 min (they build real PDFs,
  redlines and releases). CI runs them on every PR and push to `main`, pinned to Python 3.14,
  PyMuPDF 1.27.2.2 and Typst 0.14.2, with full git history because the redline tests read tags.
- **Releases, redlines, standalones, the Summary of Changes, Town Meeting freezes and the adopted
  edition:** use the **`czc-release` skill** — it holds the full procedure. The everyday entry
  points are `build/build-release.sh` (a whole draft release; run `--plan-only` first),
  `build/build-standalone.sh <NN> <ver>` (a focused proof of one Article) and
  `build/build-full-czc.sh <ver> "<date>"` (the integrated Code alone).
- **Memos:** `bash build/build-memo.sh <md> <pdf> "<running head>" "<footer>"`.
- **GIS classification:** `build/street-types/run.sh [--from N]` (own venv; see its README).

## Gotchas that have bitten before

- **Python.** The build calls bare `python3` and needs only PyMuPDF and pytest. When Homebrew moves
  `python3` to a new minor version, builds fail with `No module named 'pymupdf'`. Fix:
  `python3.X -m pip install --only-binary=:all: --break-system-packages "pymupdf==1.27.2.2"
  "pytest==9.0.3"`. The permit-review app has its own `.venv` and is unaffected.
- **Page sides and parity.** Chrome (running head, footer number, Article tab) and binding margins
  both follow the *logical* page, `here().page() + page_offset`; every `#set page(` call sets
  `binding: if calc.odd(page_offset) { right } else { left }`. Each native unit must render at an
  offset that makes logical == physical, and Article 2's D1 must land on a verso. Odd pages bind
  on the left, as in the 2020 Code. Guards: `test_binding_side.py`, `test_unit_chrome.py`.
- **The version number is the state.** Decimal (`v1.1-draft`) = draft; whole (`v2.0`) = adoption.
  `build/version_state.py` enforces it in both directions; it is the only thing between an env
  var and a document that falsely claims adoption, so never bypass it.
- **Between a freeze and the vote, change no generator.** `build-adopted.sh` renders the tag's
  source with the working tree's builders and requires the body to match the frozen Town Meeting
  edition byte for byte. (This is why v1.0 itself can no longer be re-adopted — leave that alone.)
- **The residue gate matches chrome strings, never the word "draft".** The Code's own text says
  the Planning Board "drafts the official map", and the gate asserts that sentence is present. The
  `.md` scan is case-insensitive and covers HTML comments, so new prose like "draft vote" or "not
  adopted" in `source/` would make an adoption refuse.
- **Normalise only the OLD side of a baseline redline.** Normalising the new side flattens the
  Code's hierarchy in the typeset PDF.
- **The cover's AMENDED THROUGH line is scanned art** with no text layer; only the pixel test
  (`test_cover_modes.py`) can see it. Don't move `AMENDED_RECT` without re-measuring.
- **After an adoption, roll the baseline over** in `build/adoption-map.json` (all fields, including
  `baseline_amended_through`). `baseline_selfcheck.py` guards it: a half-done rollover can report
  hundreds of phantom changes and still exit 0.
- **Changes to layout units need a written call.** `czc_diff` marks an Article NEEDS-CALL when a
  `.typ` unit or binary exhibit changed; the release stops until a person records whether it is
  layout-only or substantive (the skill has the format). A change to a `shared` file stops the
  determination until a person says which Articles it affects.

## Open items

- **Right to Farm amendment** (Articles 1, 2, 4, 5, 7, 9) — design spec with decisions D1–D7 at
  `specs/2026-10-07-right-to-farm-design.md` on branch `right-to-farm`, approved 2026-10-14;
  decisions R1–R29 in `plans/2026-10-14-right-to-farm-decisions.md`; Plan A (status code) and
  Plan B (ordinance + v1.2-draft) in `plans/`. Drafts will be v1.2-draft.
- **Wave 4c done on `right-to-farm`** — the fifth status `br` / ○ "No Permit Required" is in the
  legend and both readers (Plan A, decisions R1–R5). No cell uses it until Plan B; it ships only
  with Right to Farm (its Note cites Article 7 Section 3). The app refuses `br` cells (D-0035).
- **For counsel:** Article 9's Variance definition cites the Massachusetts Zoning Act (Maine's is
  30-A M.R.S. §4353); typos "Atricle" (Article 7), "extentions", "designnee" — fixing "designnee"
  also means updating the residue gate's expected sentence in the same commit.
- **Planning Board:** R2 vs R3 scope (memo in `memos/`, recommends a 600 ft test on private
  dead-end ways; Eden Lane vs Camp Rd inconsistency).
- **Ben to confirm:** Ownership Categories for `kavanagh-road-1` and `woods-island-road-1`
  (marker entries in `build/street-types/overrides.json`).
- **The contractor's district shapefile** — drop it in, re-run the pipeline from the join stage,
  re-promote `inventory.json`, rebuild; any change goes to the Board and Town Meeting.
- **Another planner's Fall-2026 redline** (`docs/CZC Redline 2026.06.docx`, untracked) — four
  analysis memos in `memos/`; open: merging their Article X into our Article 3, their "reviewing
  authority" rename vs our "Permitting Authority", the stale "Road" definition.
- **Permit-review app** (`build/permit-review/`) — paused; W5 blocked on decision D-0025 (may
  application content go to a third-party API?). Read `build/permit-review/BUILD-STATE.md` first.
- **The adopted v1.0 edition** lacks chrome on physical page 12 and has the old margins; it cannot
  be re-rendered and the next amendment supersedes it.
