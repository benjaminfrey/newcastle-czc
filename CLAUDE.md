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
- **Re-cutting a shipped draft** (amending an already-pushed version, e.g. the v0.17
  column trim) needs a **force-push** (history rewrite); the harness gates that pending
  Ben's explicit OK. Default to a new version number unless Ben says "stay in vX.Y".

**Parity invariant (critical, don't break):** native-Typst units are spliced
between pandoc passes; chrome (verso/recto binding margins, rotated Article tab,
running head, footer page numbers) keys off `here().page() + page_offset`, so each
unit must render at an offset that makes **logical == physical**.
- **Integrated CZC:** threads the **true running** `page_offset` (continuous flow, no
  recto-opening pads — v0.19); an even-guard pads only before `article-02.typ`, whose
  2-page district spreads need a verso start. Front matter stays even (cover + blank +
  TOC). 3 structural blanks remain (Article 2 ×2 + the front-matter blank). After
  assembly, `build/toc_links.py` adds clickable GoTo links from each TOC row to its page.
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

## Current state (as of 2026-06-09)

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

## ▶ NEXT: re-scope to all Articles + local-disk plan — AWAITING BEN'S DECISIONS (the morning topic)

**The ask (2026-06-06):** expand the project so we can work on **any** CZC Article the
same way we've done Article 3 — drafts, markdown, redlines, and the full integrated CZC
with the new changes. Ben's stated concern is **local hard-drive space** (NOT git/remote
storage), and he **plans to add images/graphics to many Articles**. He asked whether to
have **per-Article PDF generators** or **one unified script** — said **"either way is
fine."** This was a **report-only** turn; **no code/commits** made. He said *"not right
now… we'll pick this back up in the morning."* So: **nothing is decided yet — re-present
the decisions below and wait.**

- **Local-disk findings (all on Ben's drive): ~1.1 GB total.** Three movers:
  `build/street-types/.venv` **458 M** (gitignored, fully reproducible from
  `requirements.txt`); `.git` **331 M** (bloated by committed PDFs — every draft adds
  ~7.5 M ×, permanently, to the *local* `.git`); `releases/` **264 M** (PDFs regenerate
  exactly from tags; v0.8/v0.9 carry ~140 M of obsolete raster redlines). Rest ~60 M
  (docs 25 M baseline, source/exhibits 7.6 M / 41 images, etc.). **Graphics will
  accelerate `.git` + `releases/` growth** (each draft's PDFs land in both).
- **My recommendation (reclaim, ranked):** (1) delete `.venv`, make `run.sh`
  self-heal/recreate it (−458 M, zero risk); (2) keep only recent PDFs in `releases/`
  (latest + `v0.1-baseline`), prune the rest since regenerable from tags (≈ −240 M);
  (3) **stop committing generated PDFs** — gitignore `releases/**/*.pdf`, keep the
  text (md + Summary; redline inputs) — caps `.git` growth; (4) **optional one-time
  `git filter-repo`** to purge historic PDFs from history (≈ −300 M now; **history
  rewrite + force-push → needs Ben's explicit OK**); (5) delete v0.8/v0.9 legacy raster
  redlines (−140 M). Safe set (1+2+3) ≈ 1.1 GB → ~350 M; add (4) ≈ ~100 M and flat
  thereafter.
- **Architecture recommendation (per-Article vs one script):** go with **one unified
  `build-standalone.sh <article-NN> <version>`** driven by a tiny **per-Article exhibit
  manifest** (which split markers + which `.typ` exhibits + splice points) — mirrors
  what `build-full-czc.sh` already centralizes, DRY, no per-script drift. Key point for
  Ben: **inline graphics need NO tooling** — `![](exhibits/foo.png)` already renders in
  any Article via pandoc today; only **full-page native-Typst exhibits** (like Art. 3's
  plates / Type map) need the splice machinery. (Per-Article scripts also fine per Ben,
  just more duplication.) `build-article-3.sh` becomes Art. 3's manifest / can fold in.
- **Re-scope is mostly already done:** `build-full-czc.sh` + `build-redline.sh` are
  already Article-agnostic (they render all of `source/article-0N-*.md`). Only the
  **standalone builder** needs generalizing. So the work = (a) safe disk reclaim,
  (b) unified standalone builder + manifest, (c) document the "working on Article N"
  flow in this file.
- **OPEN DECISIONS to put to Ben (do not act until he answers):** (i) run the safe
  reclaim set now? (deletes only regenerable files — `.venv` + old release PDFs);
  (ii) stop committing PDFs going forward (recommended) or keep committing?;
  (iii) the `git filter-repo` history purge — now / later / skip?; (iv) confirm unified
  standalone builder (my rec) vs per-Article scripts.

- **Permit-application + automated-review system (Ben's 2026-06-09 question — UNRESOLVED):**
  should the project expand to include a **resident permit-intake portal** + an engine that
  reviews applications against the Code and **drafts Findings of Fact / Conclusions of Law**
  for the CEO or Planning Board — or be a **separate project**? My provisional lean:
  **separate repo/stack** (it's a stateful, multi-user, hosted, PII-handling web app — near-
  zero code reuse with this batch document toolchain), **bridged by a shared machine-readable
  model of the CZC's substantive standards** (the real reusable core; would also sharpen the
  code). Caveat: CZC is still a *draft*, so production adjudication is premature — but
  *prototyping* could dogfood/sharpen the code pre-adoption (Art. 3 driveway permit = natural
  first slice). I asked Ben ~8 scoping questions (automation depth / human-in-loop; permit
  types first; public vs internal + hosting; existing town software; legal weight of AI-drafted
  findings + Maine process; the CZC-as-data bridge + parcel GIS; build-vs-buy + funding; who
  maintains it). **Awaiting his answers** — he pivoted to the "character" task before answering.
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
