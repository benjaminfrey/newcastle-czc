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
