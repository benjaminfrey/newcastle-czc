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
- `build/` — build scripts (see below) + `street-types/` GIS pipeline.
- `releases/vX.Y-draft/` — shipped deliverables + redlines + Summary per version.
- `docs/` — **baseline PDFs, do not modify.**
- `memos/` — supporting justification/discussion memos.
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
- **Standalone Article 3:** `bash build/build-article-3.sh vX.Y-draft "Month D, YYYY"`
  → `releases/.../Article 3 Thoroughfares (Standalone vX.Y-draft).{pdf,md}`
- **Redlines:** `bash build/build-redline.sh <new-ver> <old-ver>` — TEXT diff of the
  integrated markdown (layout/image-only edits don't appear, by construction).
  Standard pair: vs the last *content* release **and** vs `v0.1-baseline`.
- **Summary:** hand-write `releases/vX.Y-draft/Summary of Changes vX.Y-draft.md`.

**Parity invariant (critical, don't break):** native-Typst units are spliced
between pandoc passes; chrome (verso/recto binding margins, rotated Article tab,
running head, footer page numbers) keys off `here().page() + page_offset`, so each
unit must render at an offset that makes **logical == physical**.
- **Integrated CZC (bound book):** each unit renders at a **cumulative EVEN**
  `page_offset`; odd-length units are padded with a trailing blank so every Article/
  exhibit opens on a recto. Front matter (cover+TOC) is always even.
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
**To get the 100% map later:** drop in the contractor's exact district shapefile,
re-run from the join stage, re-promote `work/inventory.json` → `source/exhibits/...`,
rebuild. No code changes.

---

## Current state (as of 2026-06-02)

- **Shipped `v0.15-draft`** — the **Thoroughfares** terminology release. Collective
  "Street/Road" term → **Thoroughfare**; Article 3 retitled **"Thoroughfares"**;
  `Street/Road Type` defined term → `Thoroughfare Type`. Street & Road kept for the
  two families, the Type names, the driveway/entrance connection phrases, and the
  Comp Plan citation. Regulation-neutral. Also removed the 2 recto-opening blanks
  from the standalone (now 27 pp, flows continuously). Tags exist through v0.15-draft.
- **"Thoroughfare" is the umbrella** (already defined in Article 9, includes Driveway);
  **Street** (S1–S5) + **Road** (R1–R5) are the two families.
- v0.14 (commit `4444972`) = first release where Article 3 §5 **renders** Exhibit 3.1
  (Inventory) + Exhibit 3.2 (Type Map) from a real but **DRAFT** classification
  (~90–95%, auto-traced from the District Map; banner says so). 215 segments, 214 typed.
- **Two human steps remain before any vote:** (1) eyeball the draft district layer
  vs the official District Map; (2) Planning-Board review → Town-Meeting adoption.
- **Deferred cosmetic cleanup:** internal names still use the old term — file names
  `street-type-{map,inventory}.typ`, dir `build/street-types/`, the `STREET-TYPE-EXHIBITS`
  marker, build vars, JSON keys, `.typ` code comments. Optional; not user-facing.

## ▶ NEXT: v0.16 — reconcile Main Street (form vs. function/jurisdiction) — APPROVED A+B

Ben caught that Newcastle's **Main Street** (a state-owned **Major Collector** through
the village) is typed **R1 (Connector Road — rural)**, and the flagship **S1 "Main
Street" Type has zero segments**. Three compounding causes: (1) the approximate
district trace put the 12 "Main Street" segments in **D1 = Rural** (Table 3.4 →
R2/R3/R1) — almost certainly a trace error; downtown belongs in D5/D6/SD-Historic;
(2) §5.D rubric ¶d presumes "Collector → R1," overriding the form default; (3) it's a
State Highway (an *ownership* fact, not a form fact). §4.D already says Type ⊥
Ownership and that "a Main Street (S1) may be … a State Highway."

**Approved approach = A + B (do as v0.16, ship with redlines + Summary on go-ahead):**
- **A — Form wins (data):** type Main Street **S1**, keep Ownership **State Highway**,
  coordinate via §12. Correct the district (Main St → D5/D6) and/or pin the 12 "Main
  Street" segments to S1 in `build/street-types/overrides.json`; `run.sh --from 3`;
  re-promote `inventory.json`. Add a sentence that S1-on-a-state-highway is the
  coordinated target, not unilaterally enforceable. Optional **C:** a "§12-coordinated"
  flag in the inventory note column.
- **B — Rubric (text):** amend §5.D ¶d so the MaineDOT functional-class presumption
  (arterial→R4/R5, collector→R1) applies only in **rural/auto-oriented** districts; in
  **village/urban** districts (D5, D6, SD-Historic…) the Adjacent-District (form) test
  governs and the highway is coordinated via §12. Durable — prevents recurrence when
  the exact shapefile is run.

Districts (Table 3.4): D1 Rural · D2 Nbhd Residential · D3 Nbhd Business · D4 Village
Residential · D5 Village Business (S2; S1 on designated) · D6 Town Center (S1).
