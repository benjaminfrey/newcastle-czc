# Newcastle CZC — release history (pre-adoption drafts)

Moved from CLAUDE.md on 2026-10-12 (prompt audit). Kept as a record, not as instructions; the
rules these releases established live in CLAUDE.md.

- **Shipped `v0.24-draft`** (the last draft before v1.0); the adoption-release machinery merged
  as `7a22319` — see “Adoption release” in CLAUDE.md.
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
  **implemented 2026-06-19 and committed**:
  `build/build-redline-full.sh` + `redline-text.py --source` + `SRC_DIR`/`OUT_DIR` seams in
  `build-full-czc.sh` + a cover caveat in `build-cover.py`. Stages the marked source and runs the
  real build, so it carries the full integrated layout with prose marked inline; native figures
  render at current state, unmarked. Verified v0.20→v0.21: 117 pp / 1 blank, parity held. See the
  Build & release flow "Redline" bullet.)*
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

---

# Build history and status log, 2026 (moved from CLAUDE.md on 2026-10-13)

The Wave 0–4b record and the status notes as they stood at v1.1-draft. Kept as a record, not as
instructions; open items are listed in CLAUDE.md.

## Status log as of 2026-10-12

- **✅ Right to Farm Plan A — Wave 4c, the fifth use status (2026-10-14, branch `right-to-farm`;
  plan `plans/2026-10-14-right-to-farm-plan-a-status-code.md`, decisions R1–R5).** Article 2's
  legend gains ○ **No Permit Required** (data code `br`, authority —) and a two-sentence Note
  pointing at Article 7 Section 3. Both legend readers take it — the permit app's `legend.py`
  (optional row; the v1.0 four-code legend still parses) and `use_table_changes.py` (worded "No
  Permit Required"). `br` alongside another code in one cell is refused by Typst, the `.md` and
  the app (release spec D3). The app refuses any `br` cell until it can model one: DECISIONS-NEEDED
  **D-0035**. Article 2 standalone unchanged at 29 pages; column 3 grows ~21 pt per legend page.
  Commits `6d08332` (app), `898d4d3` (build reader), and the Article 2 commit. Ships only with Plan B.
- **✅ v1.1-draft CUT (2026-10-12)** — the first release through `build-release.sh`, against v1.0.
  Layout only: the binding-margin fix and the Article 2 first-page chrome fix. Written calls
  (Ben): Articles 1, 2, 3 layout-only. Ships the integrated Code + redline (no marks — no wording
  changed), Summary, `release-plan.json`, `ships.json`; 117 pp / 1 blank. Also fixed the
  manifest's Exhibit 3.1 label to the printed title, "Inventory of Existing Thoroughfares".

- **✅ MERGED to `main` — the release-deliverable machinery, Waves 0 and 1** (PR #1, merge
  commit `9291b20`, 31 commits). Build suite **111 → 196**. Wave 0 fixed the Article 2
  first-page chrome defect that is live in the adopted v1.0 edition (physical page 12 —
  it cannot be back-applied, because `build-adopted.sh` renders from the tag) and
  de-pinned three tests that tracked the live working tree. Wave 1 built the seams a
  per-Article redline needs: `czc_standalone_name`; `SRC_DIR`/`OUT_DIR`/
  `OUT_NAME_OVERRIDE` on `build-standalone.sh`; `STANDALONE_FRONT_NOTE` (uncounted, and
  it refuses an odd page count); whole-line HTML comments treated as **structure** in
  `redline-text.py --source`, with the integrated build now refusing a damaged split
  marker; **`--plain`**, the markdown redline (additions `**bold**` + a `⊕` sigil on
  whole-line insertions, deletions `~~struck~~`, a legend, and a visible
  figure-regenerated note); the **ownership map** in `article-manifest.json` +
  `manifest.py` (`data`/`articles`/`owner`, with a coverage test over every tracked file
  under `source/`); and **`redline-stage.sh`**, now the single definition of
  `redline_resolve.py`'s rc 0/3/4/refuse contract, with a guard that stops plain-marked
  source reaching the PDF stage.
  **Still to build:** **Wave 4c** — the fifth use-table status code (P15), **only after Ben or
  the Board supplies its four binding values** (the code, the legend symbol, the legend row's
  wording, the rewritten Note); log a DECISIONS-NEEDED entry per the D-0033 precedent.
- **✅ Wave 4b MERGED — integrated markdown, cover facts, adoption through the driver** (PR #8,
  merge `5bd45b8`; plan
  `plans/2026-10-11-wave4b-adoption-and-integrated-md.md`, ten rulings). Build suite **640 → 726**.
  (1) **`build/integrated_md.py`**: the integrated `.md` — what the Town adopts — keeps each
  Article's source frontmatter and runs every body through `czc_md.body_markdown` (tables as
  tables, page pointers, no build comments) with **Article 2's 13-district appendix**; **no
  mode-dependent text**, so meeting and adopted `.md` are byte-identical (the identity gate holds);
  built before the PDF render, so a refusal leaves neither file. (2) **Cover facts (D6)**:
  `adoption-map.json` gains **`baseline_amended_through`** ("September 14, 2026"); draft banner =
  "proposed amendments to the Core Zoning Code" / "as amended through <it>"; the scanned AMENDED
  THROUGH line is masked and reprinted in draft and meeting mode when the baseline is newer than
  the scan (pixel test: the whole date row vs the reprint alone; the v0.1 fixture map keeps the
  positive control). (3) **Meeting mode** in `build-release.sh`/`release_plan.py`/
  `summary_skeleton.py`. (4) **`build-adoption.sh` freezes through the driver** (see Adoption
  release); `pdf_recap` exits 1 on an unreadable or zero-page PDF. (5) **`ADOPTION-SPEC.md`
  matches the code**, with agreement tests (§3.3 packet kinds = `release_plan.ARTIFACT_KINDS`;
  §6.1 gates = script + literal refusal string in non-comment lines; negative controls).
  ⚠ **v1.0 cannot be re-adopted**: `build-adopted.sh` renders the v1.0 tag's source with today's
  builders and compares against the committed old-assembler Town Meeting `.md` (identity refuses),
  and the tag's Article 3 footer still reads "Draft v0.2-draft" (the `.md` residue scan refuses).
  No code works around it; v1.0's adopted edition already exists.
  ⚠ The adoption breakdown counts Article 3's footer change since v1.0 as 2 substantive lines
  while `czc_diff` calls Article 3 NEEDS-CALL (its layout units) — expect both at the next freeze.
- **✅ Wave 4a MERGED — the release driver** (PR #7, merge `c5d6a0b`; plan
  `plans/2026-10-11-wave4a-release-driver.md`, twelve rulings). Build suite **522 → 640**.
  `build-release.sh` (see Build & release flow) composes: `release_plan.py` (czc_diff verdicts +
  written calls → `release-plan.json`; `ships.json` = czc_diff's JSON with `new` set to the version,
  never a local path; Use Table Changes decided by running `use_table_changes.py`; duplicate JSON
  keys in the calls file refused), `summary_skeleton.py` (every non-UNCHANGED Article by status in
  plain words; what the redline cannot show, from the plan's counts and the manifest's page labels;
  none of the v0.1-era sentences), `release_gate.py` (the refusing gate; memo PDFs — kind
  `use-table-changes` — only need to open with text, chosen by artifact kind, never file name), and
  `redline_md.py` (the integrated redline's **markdown edition**, which never existed before; uses
  `czc_md.body_markdown`). The **section map now reaches the redline**: `czc_redline_stage` reads
  `CZC_SECTION_MAP`; `build-redline-full.sh` (now also honours `SRC_DIR`) and
  `build-redline-standalone.sh` read `SECTION_MAP` (measured: one inserted section in Article 7 —
  130 "Heading changed" notes without the map, 0 with it). Leaf builders are reachable through test
  seams `CZC_LEAF_*` (test use only). First run of the Haiku tier for mechanical checks.
- **✅ Wave 3c MERGED — honest standalone markdown** (PR #6, merge `809ebee`;
  plan `plans/2026-10-11-wave3c-standalone-markdown.md`, ten rulings + one amendment). Build suite
  **470 → 522**. (1) **Article 3's source `footer-date`** now reads "Adopted: September 14, 2026"
  (its own commit, `07e82db`; it had read "Draft v0.2-draft" and sat in the adopted v1.0 `.md`).
  (2) **`build/typst_tables.py`** converts Article 3's raw-Typst Tables 3.2–3.5 to markdown pipe
  tables — strictly: anything outside the measured shape (a late header, Typst code in a caption or
  cell, `# $ \ ~ @ <`, spans, short rows) returns None and the caller writes a note naming the
  table. (3) **`build/czc_md.py <NN> <out.md> --src-dir --mode --version`** builds every standalone
  `.md`: frontmatter minus `footer-date`; a mode-aware provenance line ("a working draft (v…)" /
  "the Town Meeting edition (v1.0), not yet adopted" / "adopted (v1.0)"), **refusing a version that
  contradicts the mode** (same `version_state` rule as the PDF chrome); "The integrated Code is the
  document the Town adopts; this extract does not govern."; a note where each native page sits
  (by manifest `label`); whole-line HTML comments dropped; an unclosed `<!--` refused.
  **`md_completeness`** is declared per Article in `article-manifest.json` (1, 3 `prose-only`;
  2 `prose-plus-appendix`; 4–9 `complete`) and a declaration that contradicts the units is refused.
  (4) **Article 2's `.md` carries a generated appendix** of all 13 district pages from the same
  data + legend reader as the PDF — panels, Permitted Buildings matrix (or "No Permitted Buildings
  matrix."), use tables with all **819** statuses in words, use standards. (5) `build-standalone.sh`
  calls `czc_md` **before** creating the release dir (a refusal leaves none); the redline path
  (`OUT_MD_SOURCE`) skips it. (6) **`build-adopted.sh` step 4b** scans the adopted `.md` bytes with
  `adopted_residue.py --residue-only` (chrome only; the "drafts the official map" damage check stays
  on the PDF text), with an end-to-end negative control; the integrated `.md`'s pointer notes now
  say "See the PDF edition of this Code".
  ⚠ **`build-adopted.sh` pairs the TAG's source with the WORKING TREE's generators.** Any change to
  text a generator writes (e.g. `build-full-czc.sh`'s pointer notes) between a freeze and the vote
  breaks the identity gate. Consequence today: **re-running `build-adopted.sh v1.0` now refuses**
  (identity, and step 4b — the v1.0 tag's Article 3 still reads "Draft v0.2-draft"). That is honest:
  the shipped v1.0 `.md` really carries that chrome. **Do not revert the pointer wording to make v1.0
  rebuild**; the next adoption builds from fixed source. Freeze → vote: change no generator.
  ⚠ The `.md` chrome scan is **case-insensitive** and covers HTML comments the PDF never prints, so
  ordinary prose like "draft vote" or "not adopted" in `source/` would refuse an adoption (nothing
  matches today). Check before adding such wording.
- **✅ Wave 3b MERGED — the per-Article redline** (PR #5, merge `82d097b`;
  plan `plans/2026-10-10-wave3b-standalone-redline.md`, ten rulings + amendments). Build suite
  **389 → 470**. **Ben ruled 2026-10-10: dropped headings/tables/figures are made visible BOTH on
  the page AND in the text.** (1) `redline-text.py --source` (PDF and `--plain`) now writes an
  italic bracketed note at the spot of every structural change — `*[Heading removed: “…”]*`,
  `*[Heading added]*`, `*[Heading changed — it read: “…”]*`, `*[Table or figure removed/changed/
  new …: “TABLE 3.2 …”]*`, `*[Article title changed …]*`; notes are body paragraphs (never red,
  struck or a heading; never a split-marker token); the legend and tally say so. Previously a
  removed table or heading left one blank line. (2) `build/structure_text.py` names headings and
  tables and holds the ONE classifier for each (`classify_blocks`: exact-content matches first,
  then by caption, untitled never paired; `classify_headings`: section-qualified keys, retitles by
  similarity) — used by both the text and `czc_diff.structural_changes`, so page and text agree by
  construction (measured on every real tag pair v0.3→v1.0). (3) `structural_note.py` is
  **truthful** for the whole Code (no "Article 3 is new" / "NO marks" / March 2025 under the v1.0
  map; names every data-generated page as unmarked, from new manifest unit `label`s) and has
  `--scope article:N --old REF [--baseline] [--section-map] --md --pad-to-even`: kinds of change
  (never line counts), each heading/table by name, flows across pages ("…and N more" past 4, full
  list in the `.md`), markdown wording for the `.md`. (4) **`build/build-redline-standalone.sh
  <NN> <new-ver> <old-ver>`** → `<…> — Redline.pdf` + `.md` (page in front as even, uncounted front
  matter; parity, D1 verso and plate seating tested; `REDLINE_OUT=<dir>` dry run; refuses a bad
  ref/Article cleanly, writing nothing). `build-standalone.sh` gains `OUT_MD_SOURCE`; shared
  `build/article-meta.sh`. ⚠ **Owed by P13:** thread the section map through staging AND pass it to
  the page (`--section-map`), else renumbering shows as many "Heading changed" notes.
- **✅ Wave 3a MERGED — the change determination + Use Table Changes** (PR #4, merge
  `1f931b1`; CI also fixed `build-memo.sh`'s macOS-only `mktemp`; plan `plans/2026-10-09-wave3a-change-determination.md`,
  twelve rulings + amendments; Ben split Wave 3 into 3a/3b on 2026-10-09). Build suite
  **288 → 389**.
  **`build/czc_diff.py --old REF [--new-ref REF | --new-dir DIR] [--section-map P] [--json P]`**
  decides, per Article, whether it changed in substance — prose AND data. Four disjoint counts:
  `prose`, `heading` (incl. frontmatter `article-name`/`article-number` — the printed title;
  `footer-date` is chrome), `table` (raw-Typst blocks, which the redline shows unmarked) and
  `data` (json-keyed sources flattened to leaves keyed by record + title/label, D7 field filter).
  Verdicts: **SUBSTANTIVE · NEEDS-CALL · RENUMBER-ONLY · UNCHANGED**. **NEEDS-CALL** (a ruling
  beyond the spec) = a changed layout unit (`.typ`), binary exhibit, or a generated figure whose
  source had no real data change — a machine cannot tell a legend edit from a layout edit.
  It **refuses** (exit 1, names the file) on an unclaimed / doubly claimed / **shared** changed
  file (**Ben, 2026-10-09: a shared-file change stops the determination until a person says
  which Articles it affects**), a non-unique key, duplicate JSON keys, a misspelt substantive
  field, a leaf path collision, broken JSON, a bad ref. Article 2's manifest key is now
  **`[].code+name`** (code alone collides: seven districts are `SD`). Measured: v0.24-draft →
  v1.0 = Article 2 data **87** (incl. the D3 Retail & Service, General `rc`→`rc sp` cell the
  text-only breakdown missed), Article 3 prose 2 / data 10 (R2→R3), three layout units NEEDS-CALL;
  v1.0 vs itself all UNCHANGED. `adoption_breakdown.py` left intact (spec: re-express later).
  **`build/use_table_changes.py <old-ref> <out.md> [--new-ref|--new-dir] [--json]`** writes the
  Use Table Changes memo (render with `build-memo.sh`): legend first (fail-closed reader of
  `article-02.typ`, pinned to the permit-review app's reader by an agreement test), changed uses
  in words ("Not allowed" for blank), added/removed uses and districts (a wholly added/removed
  district lists every item), Permitted Buildings by row/column (named from both versions),
  district standards in plain words, and a total that **equals czc_diff's Article 2 data count**.
  Exit 2 = nothing to report, nothing written; outputs are cleared first so no stale file survives.
  (Articles 1, 2, 3 read NEEDS-CALL against v1.0; v1.1-draft recorded layout-only calls.)
- **✅ Wave 2 MERGED — section renumbering** (PR #3, merge `91a81c9`; plan
  `plans/2026-10-08-wave2-section-map.md`, which records ten rulings and their amendments).
  Build suite **199 → 288**. When a section is inserted into an Article, later headings and
  cross-references shift; **`build/section_map.py`** *derives* a map of the pure renumberings
  (title-identical headings, in order) between an old ref and a tree — never authored, never
  committed, never in `adoption-map.json`. It refuses below a 50% similarity floor, on a bad
  ref, or when nothing was compared; `check` verifies the map's ref **and tree**; `selfcheck`
  (the gate) requires every entry to pair title-identical headings **and** the map to equal a
  fresh derivation. **Rule 6** in `normalize_for_diff.py` rewrites those numbers on the OLD
  side only, and leaves raw anything it cannot prove internal: statute tokens, any
  `<word> <number>` or `<name>,` before, any `of …` after (except "of this Article"), any
  paragraph naming another Article/Ordinance/statute, and any range whose span changed.
  Measured: a section inserted into Article 7 drops that Article's count **132 → 4** (the
  inserted lines). `redline_resolve.py` gains opt-in `--section-map` (requires `--new-dir`;
  runs `selfcheck`, refuses with nothing written) and `--report` (every rule counted).
  Also fixed: `changed_line_count` dropped changed lines beginning `--`/`++`.
  `adoption-map.json`, `adoption_map.py`, `baseline_selfcheck.py` untouched.
  ⚠ **Owed by P13/P18:** thread `--section-map`/`--new-dir` through `redline-stage.sh` and
  the release driver; the redline's HOW-TO-READ note must say section renumbering was
  suppressed and list the map. **Latent, accepted:** some foreign-reference forms not in
  v1.0 could still be rewritten ("International Building Code Section 3", "Article Eight",
  "Section 3 - Section 5"); full list in the Wave 2 SDD ledger.
- **▶ For counsel / the next draft (found during Wave 2):** the adopted Article 9
  **Variance** definition cites "Section 10 of Chapter 40A of the **Maine General Laws**" —
  that is the **Massachusetts** Zoning Act; Maine's variance statute is 30-A M.R.S. §4353
  (pairs with the Variance tracking memo). Adopted Article 7 has the typo **"Atricle 4
  Section 17 Building Groups"**.
- **▶ PARTLY DECIDED — what a change to a `shared` file implies.** Interim ruling (Ben,
  2026-10-09): `czc_diff` **refuses**, naming the file, until a person decides which Articles it
  affects. The permanent rule (candidate: flag every Article) is still open; `shared` is empty.

- **CZC v1.0 was ADOPTED at the Special Town Meeting, September 14, 2026.** Adopted edition built from the
  tag (`releases/v1.0-adopted/`, md + gitignored pdf); baseline rolled over to v1.0. Future drafts are
  redlined against v1.0. Permit-review app: new binding ruleset `rulesets/adopted-v1.0` built from the tag
  by `ruleset_build/build_edition.py` (current); the 2020 ruleset kept as `superseded`; per-Code article
  schemes (`adopted` = 2020, `adopted-v1.0` = identity) instead of resetting the 2020 map; D-0033 resolved
  by Ben (**both permits required** for D3 Retail & Service, General); D-0034 logged (v1.0 standard s reads
  "phosphorous"). App suite 1099 passed / 0 errors; selftest 12/12; citations 157/157. Build tests 111.

- **✅ FIXED (branch `fix-binding-margins`) — binding margins were mirrored on 82 of 113 body pages.**
  Typst resolves `inside`/`outside` from a unit's **own physical page**, but chrome keys off the
  logical page (`here().page() + page_offset`), so every unit starting on an odd offset was bound
  backwards; the rotated Article tab also lacked `+ page_offset`. **Rule: chrome and margins both
  follow the LOGICAL page** — each of the six `#set page(` calls (template + five native units) now
  sets `binding: if calc.odd(page_offset) { right } else { left }`, and the tab uses
  `here().page() + page_offset`. Result matches the 2020 Code (odd pages bound on the left).
  Measured: integrated **117 pp / 1 blank unchanged**, 0 pages reflowed, every numbered page bound
  correctly. Guard: `build/tests/test_binding_side.py` (integrated + Article 2 + Article 3
  standalones; fails 80/26/12 problems with the binding lines removed). This changes the Code's
  layout units, so v1.1-draft recorded layout-only calls for Articles 1, 2 and 3.
  ⚠ The adopted v1.0 edition carries the OLD geometry and cannot be re-rendered
  (`build-adopted.sh` renders from the tag); the next amendment supersedes it with the fix.
- **▶ OPEN — the adopted v1.0 edition is missing chrome on physical page 12.** The first district
  page carries no running head, no footer page number and no rotated Article tab: three
  `if here().page() == 1 { return [] }` guards in `source/article-02.typ` outlived the leading
  parity blank they were written for. **Fixed on `main`** (`6d5c299`, Wave 0) and guarded by
  `build/tests/test_unit_chrome.py` + `build/tests/test_structural_note.py`. It **cannot** be
  back-applied — `build-adopted.sh` renders from the tag, which is correct. No machine deadline:
  the next amendment supersedes the v1.0 edition and carries the
  fix at zero cost. Only an external trigger forces it earlier (printed copies of the adopted
  edition distributed, a page-number citation hitting the unnumbered page, or the clerk noticing on
  the attested copy). What is missing is a page number, a running head and the Article tab —
  typography, not text; no standard, definition or sentence is affected.
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
- **Still open:** finalize the district layer from the contractor's exact shapefile and re-run
  the classification (see "100% map" below); any change it makes goes through Planning-Board
  review and a Town-Meeting vote like any amendment.

- **NEW pipeline capability:** an override entry may carry **`"exclude": true`** to drop a source
  record that is not a real thoroughfare (orphan E-911 fragment) — implemented in `05_export.py`,
  so the decision survives re-runs like every other override.
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
- **Release history (v0.14 – v0.24, pre-adoption):** see `HISTORY.md`. The rules those releases
  established live in the sections above.

## ✅ DONE: per-Article standalone build system + safe-set disk reclaim (2026-06-21)

**The ask (2026-06-06, built 2026-06-21):** work on **any** CZC Article the way Article 3 works —
standalone draft + md, while the integrated CZC + redline pick up the changes. **Implemented in
`main`:**
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
  The policy is committed (`.gitignore`: `releases/**/*.pdf`); the v0.21 reference + baseline
  PDFs remain tracked + on disk.

**Deferred (documented options):** the `git filter-repo` history purge; a shared render-lib
unifying `build-standalone.sh` + `build-full-czc.sh`. (The per-Article standalone redline was
built in Wave 3b.)

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
  - The app is committed under `build/permit-review/` (214 files); `BUILD-STATE.md` is the
    resume document.
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
