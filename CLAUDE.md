# Newcastle Core Zoning Code — project memory

Working repo for integrating Newcastle, Maine's **repealed** Road/Driveway/Entrance
Ordinance (RDEO) into the Core Zoning Code (CZC) as a **form-based Article 3,
"Thoroughfares"** (titled "Streets, Roads & Driveways" through v0.14). The CZC is a SmartCode-style form-based code; our
Article 3 must match its look, feel, and structure. Output is camera-ready PDF (via
pandoc → Typst) plus markdown, released as tagged draft versions.

Repo: `/Users/ben/Developer/Claude/Projects/Newcastle Core Zoning Code`
Remote: https://github.com/benjaminfrey/newcastle-czc.git · branch `main`
User: Ben Frey <ben@homeportsupply.com>. Newcastle is a small town; Ben is the only
in-house GIS capacity. All ordinance changes require a **Town Meeting** vote (Maine).

---

## ⛔ STANDING RULES — never violate (the user has insisted on each of these)

1. **NEVER commit unless explicitly asked.** "It is VERY IMPORTANT to only commit
   when explicitly asked." Build, verify, document, then *wait* for the go-ahead.
2. **NEVER `git add -A` or `git add .`** — always stage files **by name**.
3. **Never touch `docs/*.pdf`** — those are the immutable baseline (original CZC,
   Comp Plan, RDEO). Read-only reference.
4. Every release ships **BOTH** the integrated full CZC **AND** the standalone
   Article 3, and **BOTH** `.pdf` **AND** `.md` for each.
5. Commit messages end with the trailer:
   `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
6. On release: **isolate `git push origin main`** as its own command, then push the
   tag as a **separate** command. (Annotated tags, `vX.Y-draft`.)
7. Match the baseline CZC formatting/typography; we have measured it forensically
   (see `style/style-analysis.md`).

---

## Repo map

- `source/` — the editable Code. Articles 1–9 as `article-0N-*.md`. Article 2
  (districts) and the Article-3 exhibits are **native-Typst** (`*.typ`), spliced
  into the pandoc flow at build time.
  - `article-03-streets-roads-driveways.md` — our new Article 3.
  - `cross-section-plates.typ` — the 10 Type "plate" pages (one per Type).
  - `street-type-inventory.typ` — **Exhibit 3.1** (inventory table).
  - `street-type-map.typ` — **Exhibit 3.2** (Type map).
  - `exhibits/cross-sections/types.json` — the 10 Types' spec (standards, etc.).
  - `exhibits/street-types/inventory.json` — the promoted classification data.
- `style/` — Typst template (`czc-template.typ`), fonts, colors, style analysis.
- `build/` — build scripts (see below) + `street-types/` GIS pipeline
  + the adoption-release scripts (see “Adoption release”).
  `build-standalone.sh <article-NN> <ver>` builds any Article standalone, driven by
  `build/article-manifest.json` (+ `manifest.py` reader); `build-article-3.sh` is a shim to it.
- `releases/vX.Y-draft/` — shipped deliverables + redlines + Summary per version.
- `docs/` — **baseline PDFs, do not modify.**
- `memos/` — supporting justification/discussion memos. Rendered to PDF in CZC
  house style by `build/build-memo.sh` + `style/memo-template.typ` (memo builder
  added during the Fall-2026 redline review; usage: `build-memo.sh <md> <pdf>
  "running head" "footer"`; long tables flow across pages via breakable figures).
- `extract/`, `review-d1/` — scratch/analysis.

## The Type system

"Thoroughfare" is the umbrella term (the §5 binding classification is a **Thoroughfare
Type**); Street and Road are the two families.

10 Types, prefix = family: **S = Street** (urban), **R = Road** (rural).
`S1` Main Street · `S2` Village Street · `S3` Neighborhood Street · `S4` Lane ·
`S5` Alley · `R1` Connector Road · `R2` Rural Road · `R3` Rural Lane ·
`R4` Highway Commercial · `R5` Rural Highway. Each segment in town gets one binding
Type (the §5 Inventory). Map/table legends show only Types actually present.

## Build & release flow

- **Integrated CZC:** `bash build/build-full-czc.sh vX.Y-draft "Month D, YYYY"`
  → `releases/vX.Y-draft/Newcastle CZC (Integrated Draft vX.Y-draft).{pdf,md}`
- **Standalone (any Article):** `bash build/build-standalone.sh <article-NN> vX.Y-draft`
  → `releases/.../Article N <Name> (Standalone vX.Y-draft).{pdf,md}` — any Article 1–9 as its own
  draft (no cover/TOC; pages 1..N). Native units splice per `build/article-manifest.json`
  (Art 1 maps · Art 2 spreads w/ pad-to-odd D1-verso · Art 3 plates+exhibits); Articles 4–9 are
  pure-prose single-pass. Reuses `build-article.sh` + `split-article-03.py`. **`build-article-3.sh`
  is now a shim** → `build-standalone.sh 3` (so `build-article-3.sh vX.Y-draft` still works).
- **Working on Article N:** edit `source/article-0N-*.md` (+ its native unit/data for Art 1/2/3);
  `build-standalone.sh N <ver>` for a focused proof; then `build-full-czc.sh <ver> <date>` for the
  integrated draft and `build-redline-full.sh <ver>` for the redline (both already Article-agnostic).
  Inline images need NO tooling — `![](exhibits/foo.png)` renders in any Article via pandoc; only
  full-page native exhibits need a manifest entry.
- **Redline (formatted, full-layout — canonical):** `bash build/build-redline-full.sh <new-ver> [old-ver] [date]`
  → `releases/.../Newcastle CZC (Integrated Draft <new-ver>) — Redline.pdf` — the integrated draft
  in its **full publication layout** (chrome + all native figures) with **prose** changes marked
  inline (additions red, deletions struck) vs the **prior version**. Stages the working-tree
  `source/` (marks each `article-*.md` via `redline-text.py --source` vs the old tag) and runs
  `build-full-czc.sh` against it (`SRC_DIR`/`OUT_DIR` seams; the build threads parity for the
  longer doc automatically). **v1 limit:** figures/tables/maps + inline raw-Typst tables render at
  **current state, unmarked** (a text diff can't mark a regenerated figure) — narrate those in the
  Summary; the cover carries a redline caveat. `REDLINE_OUT=<path>` = a dry-run that won't touch a
  release. Implemented 2026-06-19 (verified v0.20→v0.21: 117 pp / 1 blank, parity held).
- **Redline (plain text — legacy):** `bash build/build-redline.sh <new-ver> <old-ver>`
  (`redline-text.py --full`) — single-column TEXT-only report, no chrome/figures; superseded by
  the formatted redline above, kept for quick wording-only reads.
- **Summary (md + PDF):** hand-write `releases/vX.Y-draft/Summary of Changes vX.Y-draft.md`
  in **plain, human-readable** language — list changes by §/Table/Type/road name; **no file,
  path, or script references**. Render to PDF with `bash build/build-memo.sh "<…Summary….md>"
  "<…Summary….pdf>" "Summary of Changes — <ver>" "Newcastle Core Zoning Code · <date>"`.
- **Re-cutting a shipped draft** (amending an already-pushed version, e.g. the v0.17
  column trim) needs a **force-push** (history rewrite); the harness gates that pending
  Ben's explicit OK. Default to a new version number unless Ben says "stay in vX.Y".

### Adoption release (the Town-Meeting path) — merged 2026-08-25

Full design in **`build/ADOPTION-SPEC.md`** (authoritative); the 8-task build log and the
adjudicated fix-later items are in `.superpowers/sdd/ADOPTION-PLAN/progress.md` (gitignored,
local only). **Nothing here changes the ordinary draft flow** — with no adoption env vars set,
`build-full-czc.sh` is byte-identical to before.

- **The version number IS the state.** Decimal (`v0.24-draft`) = draft. **Whole (`v1.0`) = an
  adoption version.** `build/version_state.py` enforces it **in both directions**: draft chrome
  refuses a whole number, and meeting/adopted chrome refuses a decimal. Never bypass this — it is
  the only thing standing between an env var and a document that claims adoption.
- **⛔ Nothing may claim adoption before the vote.** The frozen packet says **NOT YET ADOPTED**.
  The clerk attestation is masked in *every* mode.
- **Freeze (before the meeting):** `bash build/build-adoption.sh v1.0 "<meeting date>"
  [--freeze-date=<date>] [--dry-run]` → `releases/v1.0/`: the **Town Meeting edition**
  (`Newcastle CZC (Town Meeting Edition v1.0).pdf`), a redline + Summary skeleton vs the
  **previously adopted** Code, and **`frozen-from.json`**. Refuses a dirty `source/`. Then commit
  `releases/v1.0/` and tag `v1.0` at that commit.
  *Re-running to render the Summary PDF? Pass the same `--freeze-date=` or the cover restamps.*
- **Adopt (after the vote):** `bash build/build-adopted.sh v1.0 "<adoption date>"` →
  `releases/v1.0-adopted/Newcastle CZC (Adopted v1.0).{pdf,md}`. It renders **from the tag, never
  the working tree**, so the adopted document structurally cannot contain anything the voters did
  not see. Three gates: **provenance** (the tag's `source/` **tree** must still match
  `frozen-from.json` — the *tree*, not the commit, so a legitimate re-tag of identical source still
  passes, but moving the tag onto different source refuses), **identity** (adopted body byte-equal
  to the meeting edition, frontmatter stripped — frontmatter is chrome and differs by design), and
  **residue** (no draft chrome in page text *or* filename). Gates run **before** anything is
  written, so a refusal leaves no shipped-looking release dir.
  ⚠ **The residue gate matches chrome strings, never the bare word "draft"** — the Code's own
  adopted text reads *"The Planning Board, or its designnee, **drafts** the official map of the
  Town of Newcastle."* A blanket search fails on the Town's own words, and the natural 11pm fix is
  to delete the gate. It also asserts that sentence is still **present**: a substitution that
  damaged the Code's text would be far worse than a leftover banner.
- **The baseline redline is not a plain diff.** `ADOPTION_BASELINE=1` compares against the
  **adopted** Code, where ~80% of raw diff lines are formatting noise. `build/normalize_for_diff.py`
  suppresses rewrap, heading case, **article renumbering** (`build/adoption-map.json`: adopted 3→
  draft 4 … 8→9) and **table renumbering**; `build/redline_resolve.py` maps each file (exit 1
  unmapped/refuse · 3 new · 4 not text-comparable). **Article 2 is not text-comparable across the
  baseline** (native-Typst, rebuilt from data) — it renders **unmarked**. v0.24 → adopted baseline
  = **151** substantive changed lines.
  ⚠ **Normalise the OLD side only.** The NEW side gets *typeset*: normalising it flattens the
  Code's hierarchy (measured: Article 8 went 211 indented sub-clause lines → 4). `normalize()` is
  comparison-only; **`normalize_old_side()`** is the render-safe one.
  ⚠ **A suppressed mark is honest only if the reader is told once.** `build/structural_note.py`
  puts a **"HOW TO READ THIS REDLINE"** page on the verso facing the cover in baseline mode —
  it says in plain words that Article 2 rendering unmarked is *not* a statement that it was
  untouched, and prints the article map. It **replaces** the front-matter blank, so parity holds.
- **Chrome is three-mode** (`draft` | `meeting` | `adopted`) via `ADOPTION_MODE` +
  `ADOPTION_EVENT_DATE`, shared by the integrated and standalone builds through
  `build/adoption-footer.sh` and `build/adoption-name.sh` (one `czc_integrated_name` — the
  filename is chrome too; a page-text-only residue check cannot see it).
- **The adopted cover restates its own amended-through date** (spec §7, decided 2026-08-25). The
  baseline cover art reads "AMENDED THROUGH: MARCH 24, 2025"; in **adopted mode only**, that one
  line is masked and reprinted as **"AMENDED THROUGH: <adoption date>"**. Draft and Town Meeting
  editions keep the baseline date — before the vote nothing has been amended. EFFECTIVE and ADOPTED
  stay untouched in every mode: the Code was adopted November 3, 2020 and this edition *amends* it.
  ⚠ **That line is scanned art with no text layer**, so a text-only assertion cannot see the stale
  line and passes with the mask deleted. The real gate is a **pixel** test (`test_cover_modes.py`)
  using a short adoption date so the stale line's left end stays uncovered, with meeting mode as the
  positive control. Geometry measured at 600 dpi; don't nudge `AMENDED_RECT` without re-measuring.

**Tests:** `python3 -m pytest build/tests -q` — **102**, ~2.5 min (they build real PDFs).

**Parity invariant (critical, don't break):** native-Typst units are spliced
between pandoc passes; chrome (verso/recto binding margins, rotated Article tab,
running head, footer page numbers) keys off `here().page() + page_offset`, so each
unit must render at an offset that makes **logical == physical**.
- **Integrated CZC:** threads the **true running** `page_offset` (continuous flow, no
  recto-opening pads — v0.19). Only `article-02.typ` needs parity alignment: D1 (its first
  page) must land on a verso, so the build pads to an **ODD** running offset before it
  (offset+1 = even/verso for D1) and `article-02.typ` no longer self-forces
  `pagebreak(to:"even")`. (Those two together previously produced **2 redundant blanks** —
  removed 2026-06.) Front matter stays even (cover + blank + TOC). **Just 1 structural blank
  remains (the front-matter blank).** After assembly, `build/toc_links.py` adds clickable
  GoTo links from each TOC row to its page.
- **Standalone Article 3 (excerpt):** threads the **true running page count** — no
  recto-opening blanks — so it flows continuously (`build-article-3.sh`, v0.15).
- Article 3 is split by `build/split-article-03.py` at two markers:
  `<!-- TYPE-PAGES -->` (§2, before the plates) and `<!-- STREET-TYPE-EXHIBITS -->`
  (§5.C, before the Classification Rubric — marker token unchanged by the rename)
  → `03a / 03b / 03c`. Render order: `[03a, plates, 03b, Exhibit 3.1, Exhibit 3.2, 03c]`.
  Backward-compatible and **dormant-safe** (marker absent ⇒ no change; body always
  renders, exhibits only when `inventory.json` exists).

## GIS pipeline (`build/street-types/`)

Repeatable GeoPandas pipeline that produces the §5 classification. Venv at
`build/street-types/.venv` (gitignored). `bash run.sh [--from N]` chains
`01_fetch → 02_prepare → 03_join → 04_classify → 05_export`; `00_digitize_districts.py`
+ `georef.py` + `sample_key.py` build the district layer from the District Map image.
Durable human decisions live in `overrides.json`. Full docs: `build/street-types/README.md`.
The **§5.D classification rule** is centralized in `lib.classify_type` (form-first;
arterials always R4/R5; road-default Districts use MaineDOT functional class; the more
urban *form* District wins when it covers ≥25% of a segment). `03_join` emits per-District
overlap fractions (`district_fracs`); `04_classify` applies the rule (v0.18).
**To get the 100% map later:** drop in the contractor's exact district shapefile,
re-run from the join stage, re-promote `work/inventory.json` → `source/exhibits/...`,
rebuild. No code changes.

---

## Current state (as of 2026-08-25)

- **Shipped `v0.24-draft`**; the **adoption-release machinery is merged to `main`** (20 commits,
  `7a22319`) — see “Adoption release” above. The next release is the one that gets **frozen at
  `v1.0`** for the special Town Meeting. Editing continues exactly as before until then.
- **Shipped `v0.22-draft`** (re-cut several times; tag moved forward each time — main is never
  rewritten, only the tag is force-pushed) — **two resident comments + a full §5 inventory audit.**
  (1) **Driveway "road stubs":** §1.B.5 no-upgrade-on-adoption clause; §5.A.3 + §5.C.6 certainty
  (the Inventory-assigned Type is fixed at adoption → **no CEO/PB Type determination and no
  Town-Meeting amendment at development time**); §7.C.7 trigger (a driveway *expanded or altered to
  serve* >2 SFD / >1 TFD is no longer a Driveway); **new §7.F phased obligation** — 3–4 dwellings =
  safety-critical core only (Basic tier, no sidewalk/planting/full ROW), 5+/Subdivision/Town Way =
  full Type, plus a stream/Shoreland safety floor; E-911 provenance on the Exhibit 3.1 caption.
  (2) **Street trees:** new **§3.G** (Streets S1–S5) — strengthened planting + preservation of
  **Significant Street Trees** (CRZ protection, required in-kind replacement, arborist review) for
  Town/applicant ROW work; utilities *coordinate + restore* (no override of State/MPUC rights);
  general maintenance ≠ removing a healthy mature tree; §6.D.4 canopy direction. New Art-9 defs:
  **Critical Root Zone** (1 ft radius per inch DBH — also cures an undefined use in Art 4 §3.H),
  **Significant Street Tree** (≥6 in caliper; qualifies when its **CRZ *or* canopy dripline reaches
  into the ROW**, so a tree on adjacent land counts), **Certified Arborist**.
  (3) **§5 inventory audit — 42 Type corrections across 18 roads** (the cause was the approximate
  District trace, NOT the classifier): Main St all **S1**; Mills Rd all **S3**; Pond Rd all **R1**;
  Timber Ln, Stonebridge Cir, Bay View, Gastaldo Farm, Ledge Hill, Bailey, Cole Cabin, Cottril,
  East View, Middle Way → **R2**; Teague, High St → **S4**; Camp, Desperado, Fern Birch, Hawthorn →
  **R3**; two State-Highway "River Road" junction pieces → **S1** (they are Main St / Route 1B) +
  the Town Way connector → S3. Also **removed an 11 ft orphan `station-road-3`** fragment
  (**215 → 214 segments**). All recorded in `overrides.json` (**48 entries**).
  **S4 and R3 now appear for the first time** → both legends carry them (S5 Alley still absent).
  Editorial pass: `is`→`shall` on the upgrade duty, `may`→required off-segment tree replacement,
  "comes to serve"→"is expanded or altered to serve", §5.C.6 recast. Integrated **117 pp / 1 blank**.
- **NEW pipeline capability:** an override entry may carry **`"exclude": true`** to drop a source
  record that is not a real thoroughfare (orphan E-911 fragment) — implemented in `05_export.py`,
  so the decision survives re-runs like every other override.
- **▶ OPEN — R2 vs R3 scope (Board decision).** R3 is currently only the 4 private lanes off
  Route 1. A town-wide test was **deferred to the Planning Board**; memo written + committed:
  `memos/Thoroughfares — Rural Road (R2) vs Rural Lane (R3) — Board Decision Memo.{md,pdf}`
  (recommends a **600 ft test on private dead-end ways = 31 segments**; notes R3 is the *lighter*
  standard — 12 ft gravel / 33 ft ROW vs R2's 18 ft two-lane / 40 ft — so it *reduces* the §7.F
  obligation; caveats that length is a weak proxy for R3's actual <400 vpd volume test).
  Inconsistency to resolve: Eden Lane (277 ft) is R2 while Camp Rd (303 ft) is R3.
- **▶ OPEN — 2 missing Ownership Categories:** `kavanagh-road-1` + `woods-island-road-1` matched no
  MaineDOT/E-911 jurisdiction record. **Ben to confirm against the Town's road records**; marker
  entries sit in `overrides.json` (note-only, no values set — they render as "—").
- **Shipped `v0.21-draft`** — Article 3 batch + output cleanup. (1) §5 inventory: 4 Type
  corrections (Academy Hill all S3; Stonebridge Circle end → R2; Route 1 Lewis Hill/Lynch →
  Woods Island → R5) via `overrides.json` + promoted `inventory.json`; (2) **Exhibit 3.1 rows
  numbered 1–215** (`street-type-inventory.typ`); (3) **S1 Main Street recalibrated** — sidewalk
  6 ft, planting 2–6 ft (typ 3), ROW recomputed 50–62 ft (typ 56), SVG regenerated, + a
  State-route/Route 1B caption (DOT controls the traveled way; S1 keeps its full standards, no
  `maindot` flag); (4) **§6 New Thoroughfares tiered engineering/oversight** — new §6.e +
  **Table 3.5** (Basic = S4/S5/R3 · Engineered = S2/S3/R1/R2 · State = S1/R4/R5) + safety floor
  (stream/Shoreland crossings, Town-Way candidates, reviewing-authority bump-up); §6 subsections
  renumbered e→h (§14 cross-ref 6.G→6.H); (5) RDEO **hammerhead/EMS turnaround** clause (>150 ft)
  in §6.f; (6) **Article 9 definitions merged alphabetically** (the 25 Article-3 terms; Alley/
  Driveway superseded; end-section removed); (7) **blank-page fix** — removed 2 redundant
  Article-2 blanks (integrated now **116 pp / 1 blank**). **Output structure changed:** one
  **full-document redline** vs prior version (dropped the vs-baseline + the changed-passages
  digest); **Summary now md + PDF**, rewritten plain (no file/path refs). "cartway" left as-is
  (already defined). Tags through v0.21-draft. *(Formatted full-layout redline — now
  **IMPLEMENTED 2026-06-19** (working tree, pending Ben's commit/adoption decision):
  `build/build-redline-full.sh` + `redline-text.py --source` + `SRC_DIR`/`OUT_DIR` seams in
  `build-full-czc.sh` + a cover caveat in `build-cover.py`. Stages the marked source and runs the
  real build, so it carries the full integrated layout with prose marked inline; native figures
  render at current state, unmarked. Verified v0.20→v0.21: 117 pp / 1 blank, parity held. See the
  Build & release flow "Redline" bullet.)*
- **Reviewed another planner's Fall-2026 redline of the CZC** (`docs/CZC Redline
  2026.06.docx` — a Google-Docs **color/strike legislative redline**, NOT Word
  track-changes: green/underline = add, red/strike = delete, yellow = moved;
  ~690 adds / 380 dels across Articles 1,2,3,X,6,7,8 — built on the **original
  adopted CZC numbering**, so it does NOT include our Article 3 Thoroughfares).
  Wrote **4 analysis memos in `memos/`** (all built to PDF): (1) **Thoroughfares
  reconciliation** — our form-based Article 3 vs their engineering-style
  "Article X"; verdict **merge, not choose** (ours is the better fit + a near-
  superset; harvest their culvert-embedment/hammerhead/road-spacing specifics;
  borrow their ROW-as-easement def; **fix our stale "Road" definition**; ⛔ both
  can't reach Town Meeting — conflicting Thoroughfare/Road/Driveway/ROW defs);
  (2) **Reconciled definitions + Article X harvest list**; (3) a **2-page
  summary**; (4) **Article 7 Administration** analysis (~496 changes = a wholesale
  development-review rewrite: "Permitting Authority"→"reviewing authority" + CEO
  sole permit-issuer; Select Board; Permit→Review; project-size tiers; CEO↔PB
  authority shifts; LD-2003 / §4404 alignment). **Open coordination items:** the
  Thoroughfares merge; their "reviewing authority" rename vs **our Art. 3 §13
  "Permitting Authority"**; confirm their deleted overlay reviews (Shoreland/
  Floodplain/etc.) are preserved; the safe self-contained **"Road" def fix** is a
  good near-term v0.x edit. The redline `.docx` sits in `docs/` (Ben placed it
  there; **left untracked** — relocate out of the baseline folder before tracking).
- **Shipped `v0.20-draft`** — legal-drafting/editorial: **defined "Character"** and removed
  it from the binding standards. New Article 9 definition anchors Character to measurable
  physical/form attributes and **excludes ownership/occupancy/socioeconomic factors** (a
  fair-housing safeguard). Replaced the **8 operative uses** with concrete terms (§5.D
  "Built character test" → **"Built-form test"**; §5.E/§6.C/§6.D/§14.E "built character /
  future character" → **"built form"**; two Art. 8 criteria "character" → **"nature"**).
  **Kept** the word in non-binding **purpose** statements (now anchored), the form-based
  **"form and character"** pairing, and the policy term **"rural character."** **Left
  verbatim for town counsel + filed two tracking memos in `memos/`:** the **Variance**
  standards (Art. 8 §19.d — mirror 30-A M.R.S. §4353; the new def could narrow the
  statutory term → savings-clause suggested) and the **Human Service Facility** standards
  (Art. 7 §34.b — FHA / Maine Human Rights Act exposure: a need/overconcentration/character
  gate on a protected-class use). Text-only; **parity held** (integrated 118 pp/3 blank,
  standalone 27 pp/0 blank). Tags through v0.20-draft.
- **Shipped `v0.19-draft`** — integrated-PDF output only (no content change; integrated
  `.md` byte-identical to v0.18). Removed the inter-article recto-opening blank pages —
  the build now threads the **true** running `page_offset` instead of padding each
  Article to a recto (**10→3 blanks, 125→118 pp**; the 3 remaining are structural —
  Article 2's 2-page district spreads need a verso start + the front-matter TOC blank).
  Added a **clickable TOC** (`build/toc_links.py` adds a GoTo link per row → its page;
  188 links). Standalone unchanged. Tags through v0.19-draft.
- **Shipped `v0.18-draft`** — classification-engine improvement. The §5.D form-first
  rubric is now implemented in code (`lib.classify_type`; was prose-only since v0.16),
  plus a most-urban-District-wins-in-the-village tweak (25% overlap gate; arterials
  always R4/R5). Re-typed **9 village segments R→S** (Mills Rd→S3, River Rd→S2,
  Stonebridge→S3, Teague→S2, Austin→S3, High St→S3); now **215/215 typed (0 pending)**.
  `03_join` emits `district_fracs`; `04_classify` consumes them via `lib`. No prose
  change (engine/data only).
- **Shipped `v0.17-draft`** — editorial: the repealed RDEO is now named only in the
  §1.A repeal/supersede clause; the 3 incidental mentions (§3.E grade rationale, §14.D
  substantial-reconstruction definition) reworded to keep substance without the
  citation. Also trimmed the always-empty ROW/Nonconformity columns from Exhibit 3.1
  (JSON fields kept). No standard/definition change.
- **Shipped `v0.16-draft`** — **Main Street reconciliation.** Typed the downtown core
  **S1** (Mills Rd → Damariscotta bridge) + **S2** (Mills → River Rd), Ownership kept
  **State Highway** (`overrides.json`: main-street-9→S2, -10/-11/-12→S1); **S1 went
  0 → 3 segments**. Amended §5.D ¶d so MaineDOT functional class drives Type only in
  road-default Districts; in the village the form test governs (Main-St-is-S1 example,
  §12 coordination). Western approach to Route 1 left R-typed.
- **Shipped `v0.15-draft`** — the **Thoroughfares** terminology release. Collective
  "Street/Road" → **Thoroughfare**; Article 3 retitled **"Thoroughfares"**;
  `Street/Road Type` → `Thoroughfare Type`. Street & Road kept for the families, Type
  names, driveway/entrance connection phrases, Comp Plan citation. Regulation-neutral.
  Standalone lost its 2 recto-opening blanks (27 pp, continuous).
- **"Thoroughfare" is the umbrella** (already defined in Article 9, includes Driveway);
  **Street** (S1–S5) + **Road** (R1–R5) are the two families.
- v0.14 (commit `4444972`) = first release where Article 3 §5 **renders** Exhibit 3.1
  (Inventory) + Exhibit 3.2 (Type Map) from a real but **DRAFT** classification
  (~90–95%, auto-traced from the District Map; banner says so). 215 segments, 214 typed.
- **Before any vote:** (1) finalize the district layer via the contractor's exact
  shapefile + re-run (the hand-eyeball of the distorted draft trace proved low-value —
  see NEXT); (2) Planning-Board review → Town-Meeting adoption.

## ✅ DONE: per-Article standalone build system + safe-set disk reclaim (2026-06-21)

**The ask (2026-06-06, built 2026-06-21):** work on **any** CZC Article the way Article 3 works —
standalone draft + md, while the integrated CZC + redline pick up the changes. **Implemented in
the working tree (pending Ben's commit):**
- **`build/build-standalone.sh <article-NN> <version> [date]`** — unified standalone builder for
  any Article 1–9, driven by **`build/article-manifest.json`** (+ tiny `build/manifest.py` reader).
  Pure-prose fast path (Art 4–9); after-prose splice (Art 1 maps; Art 2 spreads with the
  pad-to-odd D1-verso guard); at-marker splice (Art 3 plates + §5 exhibits). Reuses
  `build-article.sh` + `split-article-03.py`. **`build-article-3.sh` is now a 3-line shim** →
  `build-standalone.sh 3`. **`build-full-czc.sh` left untouched** (a shared-render-lib unification
  is a future option). Verified: Art 7 (9 pp), Art 1 (maps), Art 2 (29 pp, D1 on a verso),
  Art 3 (27 pp — matches the shipped v0.21 standalone); integrated build still **116 pp / 1 blank**.
- **Disk reclaim — safe set done:** deleted `build/street-types/.venv` (−458 M, rebuilds from
  `requirements.txt` via `run.sh`); pruned old release PDFs (80 → 5 on disk, keeping `v0.21-draft`
  + `v0.1-baseline`), which removed the obsolete v0.8/v0.9 raster redlines. **~1.1 GB → ~446 M**
  working tree. `.git` stays ~356 M — the `git filter-repo` history purge that would shrink it was
  **declined for now** (revisit if local space gets tight; needs a force-push + reclone).
- **PDF policy:** **stop committing generated PDFs** — `.gitignore` now ignores `releases/**/*.pdf`
  (regenerable from tags); markdown/Summaries + the `docs/` baseline + `memos/` PDFs stay tracked.
  The 75 pruned PDF deletions + the policy are **pending Ben's commit** (standing rule #1); the
  v0.21 reference + baseline PDFs remain tracked + on disk.

**Deferred (documented options):** per-Article *standalone* redline (the integrated
`build-redline-full.sh` already isolates one Article's changes; a `build-redline-standalone.sh`
would reuse `redline-text.py --source` on one file); the `git filter-repo` history purge; a shared
render-lib unifying `build-standalone.sh` + `build-full-czc.sh`.

- **▶ PAUSED (resumable) — Permit-review app, `build/permit-review/`.** The 2026-06-09 question
  ("should we build a permit-review + Findings-of-Fact drafter?") was **answered yes** and the app
  was designed and largely built 2026-08-20/21. **Read `build/permit-review/BUILD-STATE.md` first**
  — it is the resume document (status, verify commands, open decisions, known issues, and the
  orchestration lessons). Short version:
  - **W1–W4 complete; W5 is next and is BLOCKED on decision D-0025.** ~31k lines Python,
    **592 tests**, `run.py --selftest` 10/10, `--verify-citations` 157/157. Everything runs
    **offline** — no network, no LLM, no PII, so far.
  - **D-0025 is Ben's call and gates W5:** may application content (names, addresses, deed refs,
    and page images of scans that *cannot* be name-redacted) go to a third-party API? Note it may
    already be public record under **Maine FOAA** — confirm with counsel, don't assume.
  - **Architecture:** FastAPI on 127.0.0.1, SQLite/WAL + numbered migrations, append-only
    hash-chained `events` table, rules-as-data with per-case ruleset pinning (`rulesets.binding`
    means real cases run against the **adopted** Code only; the draft CZC is for dogfooding),
    pandoc→Typst output to `data/exports/`.
  - **The design reframe that governs everything:** the app produces the **working draft the Board
    marks up**, never a decision. It never concludes, never signs. Honest blanks beat confident
    guesses — a long confident draft on a contradictory application is a *failure*.
  - **`DECISIONS-NEEDED.md` (27 entries) is the "never guess a legal value" ledger.** Only D-0025
    blocks anything; the rest are deliberately collected, incl. the missing appeal-rights paragraph
    (D-0026) and the "preparer of record" issue (D-0027 — Ben is Chair, author and operator).
  - ⚠ **Nothing in `build/permit-review/` is committed** — it is one untracked directory and HEAD
    is still `e956296`. No recovery point exists if it is lost.
- **100% map (the real fix):** the draft district trace is a ~0.77-IoU georeferenced
  approximation — spatially distorted, so a hand polygon-review is low-value (we did the
  v0.18 engine tweak instead, which sharpened the *village* classification on the
  existing trace). The accurate layer comes from the contractor's exact district
  shapefile: drop it in → `run.sh` from the join stage → re-promote `inventory.json` →
  rebuild. The §5.D rule is now in the engine (`lib.classify_type`), so correct Types
  fall out automatically; `overrides.json` (incl. the Main St S1/S2 pins) carries forward.
- **Deferred cosmetic cleanup** (optional, not user-facing): internal names still use
  the old term — `street-type-{map,inventory}.typ`, dir `build/street-types/`, the
  `STREET-TYPE-EXHIBITS` marker, build vars, JSON keys, `.typ` code comments.
- **Adoption:** Planning-Board review → Town-Meeting vote (Maine).

Districts (Table 3.4): D1 Rural · D2 Nbhd Residential · D3 Nbhd Business · D4 Village
Residential · D5 Village Business (S2; S1 on designated) · D6 Town Center (S1).
