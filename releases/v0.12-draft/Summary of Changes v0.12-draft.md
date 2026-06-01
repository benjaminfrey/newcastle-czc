# Summary of Changes — v0.12-draft

**Release type:** **Substantive — restructures how existing streets and roads are classified (Article 3 §5), decoupling the classification from the District Map.** Through v0.11, §5.C said the Inventory of Existing Streets and Roads was *"incorporated by reference into the District Map as Exhibit 3.1 and treated as a Special Requirement under Article 2 §4."* That conflated three things that don't belong together: a binding regulatory classification (each segment's Street/Road Type), mutable descriptive data (widths, MaineDOT class, nonconformity notes), and the District Map's lot-level "Special Requirements" machinery (shopfront streets, scenic views). This release separates the **binding classification** from the **recorded reference data**, gives each its proper amendment burden, removes the Special-Requirement mischaracterization, and adds an **illustrative Street & Road Type Map** as a generated companion to the Inventory. It also adds the **rendering engine** for that map (tooling).

**Compares against:** [v0.11-draft](../v0.11-draft/) (the Type-page visual redesign). This release changes **only Article 3 §5** in the rendered Code; the draft-to-draft redline isolates exactly those passages. Page counts are unchanged (integrated 115 pp, standalone 20 pp).

**Why this release exists.** Raised in review: putting the street Inventory "on the District Map" is the wrong home. The District Map is an *area* instrument (district polygons) with a couple of light overlays; a per-segment Type classification is *linear*, and most of the Inventory's content (approximate widths, MaineDOT class, ownership-as-recorded, nonconformity notes) can't legibly live on a map at all. Worse, because Newcastle amends all ordinances at Town Meeting, folding the *whole* Inventory into the adopted map would make correcting an approximate width — or updating a MaineDOT functional class when the state reclassifies — a Town-Meeting matter. The fix is to adopt only what is regulatory (the Type) and treat the rest as a maintained reference record.

---

## 1. What changed, in one picture

| | v0.11 | **v0.12** |
|---|---|---|
| **Inventory's legal nature** | "incorporated into the District Map as Exhibit 3.1; a Special Requirement under Art. 2 §4" | **the Inventory is its own instrument (Exhibit 3.1); the District-Map / Special-Requirement framing is removed** |
| **What's binding** | ambiguous — the whole 8-field Inventory, by implication | **only the assigned Street/Road Type** (with the segment's name/termini identifying it) |
| **Descriptive fields** (widths, MaineDOT class, ownership-as-recorded, nonconformity) | implicitly part of the adopted map | **recorded for reference — "approximate, does not establish or limit any standard … actual condition governs"; updatable by the Town without amending the Code** |
| **Changing a Type** | "Amendment of the District Map" (§5.E.1.a) | **amendment of the Type assignment in the Inventory under Art. 8 §21** — same Town-Meeting bar, correct instrument |
| **Map** | — | **Street & Road Type Map (Exhibit 3.2)** — an *illustrative* companion generated from the Inventory; the Inventory governs if they differ |
| **Map engine** | — | **new renderer + documented data schema** (tooling; sample data only — not in the built Code yet) |
| **Pages / parity** | 115 / 20 | **115 / 20 — unchanged** |
| **Rest of the Code** | — | **untouched** (Article 2 included) |

## 2. The design decisions behind it

Reached in discussion and locked:

- **Split binding from descriptive.** The **Type** is the regulatory classification (adopted, Town-Meeting-amended). The descriptive fields are recorded reference data — explicitly *not* standards — so a stale or approximate value can never be read as a binding dimension, and clerical corrections don't require amending the Code. (Newcastle confirmed it is comfortable updating reference data at annual/special Town Meetings; the disclaimer is about regulatory *weight*, not update frequency.)
- **Binding at adoption.** The Type classification binds when adopted (it sets the standards that apply to each segment).
- **List governs; map illustrates.** With ~50 segments and a single in-house GIS maintainer, the **Inventory table is the legally-operative instrument**; the **Type Map is a generated illustration** (so it can't drift, needs no separate adoption, and a misdrawn boundary creates no legal ambiguity). This is the form-based "thoroughfare table + regulating-plan map" pattern, with the table as source of truth.
- **Town-Meeting amendment.** Per Newcastle's form of government, every ordinance change is a Town-Meeting matter; Article 8 §21 already processes *text or map* amendments that way, so a Type reclassification routes through §21.
- **Not a §4 Special Requirement.** Article 2 §4 (shopfront streets, scenic views) is a lot-level standard triggered by a map flag; the Type classification is a record, not a lot standard. That label is removed.

## 3. The reworked §5.C (Article 3)

§5.C now reads, in substance:

1. The Town maintains an Inventory (Exhibit 3.1) that, for every segment, **assigns a Street/Road Type** and **records descriptive information**.
2. **Classification (binding).** For each segment — identified by name and termini — the Type assignment is the regulatory classification, adopted as part of the Code; the applicable standards are those of the assigned Type (§2) plus the rules of general application (§3); a Type may be changed only under §5.E.
3. **Recorded information (reference).** Ownership Category (per §4), approximate ROW width, approximate traveled-way width, adjacent District(s), MaineDOT functional class, and nonconformity notes — *approximate, not a standard, updatable by the Town; actual condition / controlling standard governs on conflict.*
4. **Street & Road Type Map (Exhibit 3.2)** illustrates the assigned Type, generated from the Inventory; the Inventory governs on conflict.
5. Initial Inventory adopted with this Article; Type changes via §5.E; reference data updatable without a Code amendment.

And **§5.E.1.a** is repointed from *"Amendment of the District Map under Article 8 §21"* to *"Amendment of the segment's Type assignment in the Inventory (Section 5.C) under Article 8 §21 (Zoning Amendment)."*

## 4. The Street & Road Type Map engine (tooling — not yet in the Code)

`source/street-type-map.typ` renders Exhibit 3.2: it reads a JSON of segments and draws each as a polyline color-coded by assigned Type (a blue ramp for the Street family, an olive ramp for the Road family), inside Article-3 page chrome, with a Type legend, a north arrow, and an "Inventory governs / illustrative" note. It is the linear/vector sibling of `district-maps.typ`.

`source/exhibits/street-types/inventory-sample.json` is a **documented schema + sample network** (one invented segment per Type) so the engine can be demonstrated — see this release's rendered sample. **It is not Newcastle data, and the engine is not wired into the production build**, so no sample map lands in any deliverable.

**To make the real Exhibit 3.2,** populate the schema with Newcastle's road centerlines (ideally projected, e.g. Maine State Plane / EPSG:26919) and each segment's Type (the §5.D rubric applied), then point the renderer at that file. At that point it gets wired into the build as a real exhibit, and the populated Inventory table (Exhibit 3.1) is produced for adoption. Both the geometry and the classification are Town inputs — they're not in this repo.

## 5. Deliverables

- **`Newcastle CZC (Integrated Draft v0.12-draft).pdf`** — 115 pp, 7.71 MiB; identical to v0.11 except Article 3 §5.
- **`Newcastle CZC (Integrated Draft v0.12-draft).md`** — concatenated markdown.
- **`Article 3 Streets Roads & Driveways (Standalone v0.12-draft).pdf`** — 20 pp, 503 KiB.
- **`Article 3 Streets Roads & Driveways (Standalone v0.12-draft).md`** — Article 3 source (carries the §5 rework).
- **`Redline — Full CZC v0.12-draft vs v0.11-draft.pdf`** *(56 KiB)* — isolates the §5.C rewrite + the §5.E.1.a repointing; nothing else.
- **`Redline — Full CZC v0.12-draft vs v0.1-baseline.pdf`** *(1.23 MiB)* — cumulative vs baseline.
- **`Summary of Changes v0.12-draft.md`** — this document.

## 6. Files changed

- **`source/article-03-streets-roads-driveways.md`** — §5.C rewritten (binding/reference split, Exhibit 3.1/3.2, District-Map/§4 framing removed); §5.E.1.a repointed to the Inventory under Art. 8 §21. No other section changed; no Type standard, table, or rubric altered.
- **`source/street-type-map.typ`** *(new — tooling)* — the Street & Road Type Map (Exhibit 3.2) renderer.
- **`source/exhibits/street-types/inventory-sample.json`** *(new — tooling/sample)* — schema + sample network; not real data, not built into the Code.

**Not touched:** Article 2 (no more street-classification entanglement), all other Articles, the Type pages/plates and their data (`cross-section-plates.typ`, `types.json`), and every build script (the Type-Map engine is rendered standalone for now).

## 7. Verification

- **Scope is exactly §5.** The v0.11→v0.12 redline shows only the §5.C rewrite and the §5.E.1.a repointing, under the "5. CLASSIFICATION OF EXISTING STREETS & ROADS" breadcrumb. No other passage drifted.
- **Parity holds.** Integrated 115 pp and standalone 20 pp, unchanged from v0.11; the expanded §5.C absorbed within Article 3 without adding a page.
- **Markdown parses** cleanly (pandoc), and §5.C renders as a well-formed numbered list with the binding/reference paragraphs.
- **Map engine renders.** The sample network renders as Exhibit 3.2 — Article-3 chrome, ten Type-colored segments, two-column legend, north arrow, "sample data / Inventory governs" note — on one page.

## 8. Notes & carry-forward

- **The real map + populated Inventory need Town data** — road centerlines (your GIS) and the per-segment Type classification (the §5.D rubric applied, ultimately Town-Meeting-adopted). Until then the engine ships as tooling and Exhibit 3.2 is not in the built Code.
- **Town-attorney review.** The "recorded for reference, not a standard, updatable without amendment" treatment touches what is legally "adopted"; counsel should bless the §5.C wording and the §5.E.1.a amendment mechanics.
- **Map legibility at scale.** The per-Type blue/olive ramps are distinct enough for a legend; with ~50 real segments, adjacent shades (e.g. S2/S3) or dense areas may warrant tuned colors or per-segment labels — a quick renderer tweak when real data is in.
- **Carry-forward from v0.11** (the Type-page redesign, full-width framed cross-sections, the newly-authored PURPOSE statements pending drafter review) is unaffected.
