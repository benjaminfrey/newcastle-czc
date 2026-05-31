# Summary of Changes — v0.7-draft

**Release type:** **Graphics release.** Delivers the ten Street/Road Type **cross-section plates** carried forward since v0.6 — one full-page annotated cross-section per numbered Type (S-1…S-5, R-1…R-5) — and wires them into both the integrated and the standalone builds. The plates are **generated, not drawn**: a Python compositor assembles vendored Streetmix illustration sprites into one SVG per Type, and a native-Typst layout pages each into a plate that reuses Article 2's exact district-page chrome. **No regulatory standard is added or altered.** The only change to regulatory text is a single new item in Article 3 §2.c that tells the reader the plates exist, are illustrative, and that Section 3 controls where they differ.

**Compares against:** [v0.6-draft](../v0.6-draft/).

**Why this release exists.** v0.6's carry-forward list opened with: *"Cross-section graphics — 10 needed… held by direction, to be taken up as a dedicated effort."* This is that effort. A form-based code that calibrates right-of-way to context is far easier to read — for a Planning Board, an abutter, or a road contractor — when each Type's cross-section is drawn to typical width rather than only tabulated. The hard requirement was that the graphics be **part of the build**, regenerable from source, not hand-pasted images that drift from the standards. They now are: edit `types.json`, rerun the build, and every plate re-renders.

---

## 1. What changed, in one picture

| | v0.6 | **v0.7** |
|---|---|---|
| **Type cross-sections** | none (tabulated only) | **10 full-page plates**, one per numbered Type (S-1…S-5, R-1…R-5) |
| **How they're produced** | — | **generated from source** — `build-cross-sections.py` composites sprites → SVG; `cross-section-plates.typ` lays out the page |
| **Driveway (D)** | — | **no plate** (D is not a Street or Road Type) — stated in §2.c |
| **Integrated length** | 101 pp | **111 pp** (+10 plates) |
| **Standalone Article 3** | 10 pp | **20 pp** (10 prose + 10 plates) |
| **Plate location** | — | **end of Article 3**, after §14, before Article 4 — page-number-safe |
| **Regulatory text** | — | **+1 item** (Art. 3 §2.c.5, a pointer note) — *no standard changed* |
| **Illustration license** | — | **CC BY-SA 4.0** attribution on every plate + `NOTICE.md` provenance |

The ten plates and their typical right-of-way:

| Code | Name | Family | ROW (min–max / typ) | Notes |
|---|---|---|---|---|
| **S-1** | Main Street | Street | 66–80 / 73 ft | shopfront streetwall, parking both sides |
| **S-2** | Village Street | Street | 40–54 / 47 ft | sidewalks both sides, parking one side |
| **S-3** | Neighborhood Street | Street | 40–46 / 43 ft | sidewalk one side, planting strip |
| **S-4** | Lane | Street | 30–40 / 35 ft | low-speed, optional parking |
| **S-5** | Alley | Street | 16–20 / 18 ft | rear service, no sidewalk/parking |
| **R-1** | Connector Road | Road | 40–50 / 45 ft | shoulders not curbs |
| **R-2** | Rural Road | Road | 40–50 / 45 ft | narrowest paved, ditches |
| **R-3** | Rural Lane | Road | 33–50 / 40 ft | single shared travel surface, gravel OK |
| **R-4** | Highway Commercial | Road | per MaineDOT | **illustrative section** — cartway/ROW per MaineDOT |
| **R-5** | Rural Highway | Road | per MaineDOT | **illustrative section** — cartway/ROW per MaineDOT |

## 2. The plate — what one page shows

Each plate is a single page built to look like a torn-out leaf of the adopted code. Top to bottom:

- **Code badge + name banner** — the *identical* Article 2 district-band chrome (`type_band`), colored **article blue for Streets, muted olive for Roads**, with the badge at the fore-edge (left on verso, right on recto).
- **Context kicker** — e.g. *"STREET TYPE · D6 Town Center · designated D5 segments"* — naming the family and where the Type applies.
- **Cross-section graphic, spanning the full text column** — the right-of-way drawn to scale at the Type's typical width: travel lanes, on-street parking, planting strips, sidewalks, shoulders, verges, curbs, lane markings, plus framing context (buildings, street trees, parked/moving cars, pedestrians) and the rural ground surfaces (grass verge, gravel). Each segment carries a **width callout** (e.g. *11 ft / TRAVEL*) and the whole section a **right-of-way bracket** (*RIGHT-OF-WAY 66–80 ft (73 ft typ.)*).
- **CC BY-SA credit line** — see §5.
- **Design-standards strip** — the Type's row from **Table 3.1a (Streets) / 3.1b (Roads)**, two label/value pairs per row, values verbatim from Article 3.
- **Two reference columns** — *APPLIES IN* (the Districts the Type serves) and *KEY ATTRIBUTES* (its qualitative character) — complementing, not duplicating, the §2 prose that precedes the plate.

**R-4 and R-5 are explicitly illustrative.** US Route 1 is a State Highway; its cartway geometry and right-of-way are set by MaineDOT, not the Town. For those two plates the right-of-way bracket is replaced with *"ILLUSTRATIVE SECTION · CARTWAY & R.O.W. PER MAINEDOT"*, the credit line states the section is illustrative and the Town governs only the frontage zone / setbacks / sidewalks / access management (per §12), and the standards strip reads *"Per MaineDOT"* for the cartway dimensions while showing the Town-controlled rows (frontage, access management, vegetative screen) plainly.

## 3. How a plate is generated (the pipeline)

The design goal was a **self-contained renderer** — no headless browser, no Node, no Postgres, nothing from the Streetmix application stack. Two stages, both reproducible from source:

1. **`build/build-cross-sections.py`** — the compositor. Reads `source/exhibits/cross-sections/types.json` (the single source of truth for every Type's segments, widths, sprites, surfaces, standards, and notes) and lays the segments left-to-right at a fixed scale (39.37 px/ft). It samples sprite fill colors for ground surfaces, draws curbs/lane lines/centerlines, and emits **one self-contained SVG per Type** to `source/exhibits/cross-sections/<CODE>.svg`. Sprite ids are namespaced per-instance so multiple copies of a sprite (e.g. four parked cars) compose without id collisions. Headroom is trimmed dynamically to the tallest sprite, so rural sections render landscape rather than as a tall column of dead sky.
2. **`source/cross-section-plates.typ`** — the page layout, in native Typst. Reads the same `types.json`, places the `<CODE>.svg`, and draws the badge/banner/kicker/credit/standards-strip/notes chrome. It shares **all** visual tokens, page geometry, and parity-aware header/footer/tab logic with `source/article-02.typ`, so a plate is typographically indistinguishable from a district spread. An aspect-aware sizing step spans the section to the full column width when its natural height fits, and otherwise caps the height and centers it (this is what keeps the narrow S-5 Alley from towering up the page).

Because both stages read `types.json`, **a width or standard is edited in exactly one place** and propagates to the SVG, the on-graphic callouts, the standards strip, and the notes together.

## 4. Build integration & the parity arithmetic

Both deliverables place the 10-plate block **at the end of Article 3** — after §14, before Article 4. This is deliberate: pandoc paginates the Article 3 prose as one flow, so inserting plates *between* subsections would corrupt every footer after the insertion point (and pandoc's `columns()` forbids the `pagebreak()` that inline plates would need). Appending the block at the end shifts **nothing** inside Article 3; only Article 4 onward moves down by 10 pages, and the auto-derived TOC already follows.

- **Integrated build (`build/build-full-czc.sh`).** `cross-section-plates.typ` is spliced into the render order immediately after `article-03-*.md` and rendered by the existing native-Typst branch — the same path `article-02.typ` already uses, with the same `page_offset` / `footer_date` inputs. Article 3 prose renders at offset 32 (pp 33–42); the plate block renders at offset **42** (pp 43–52); Article 4 at offset **52** (opens recto, p 53).
- **Standalone build (`build/build-article-3.sh`).** The prose renders first (pp 1–10), then the plate block is appended at offset **10** (pp 11–20) and the two are `pdfunite`d.
- **The parity invariant holds by construction.** `cross-section-plates.typ` requires an **even** `page_offset` (its chrome keys off logical page = `here().page() + page_offset`; even offset keeps logical parity equal to physical parity, so the badge sits on the correct fore-edge). The plate block is always handed an even offset — Article 3 is padded to an even length first if needed — and 10 plates is itself even, so the offset stays even for Article 4. Verified: footers run continuously across the prose→plate→Article-4 seams; S-1 lands recto (badge right), S-5 Alley/odd plates recto, even plates verso; Article 4 still opens on a recto.

## 5. Illustration licensing — CC BY-SA 4.0 (`source/exhibits/cross-sections/sprites/NOTICE.md`)

The cross-section illustrations are composed from **Streetmix** illustration sprites, vendored **unmodified** into `sprites/`. Those illustrations are licensed **Creative Commons Attribution-ShareAlike 4.0** — distinct from the Streetmix *application code* (AGPLv3), which is **not** used, run, or redistributed here.

Because each rendered plate incorporates CC BY-SA art, the plates are **adaptations**, which obliges two things, both satisfied:

1. **Attribution** — every plate carries a visible credit line: *"Cross-section illustration adapted from Streetmix (streetmix.net), © the Streetmix project, licensed CC BY-SA 4.0."*
2. **ShareAlike** — the rendered cross-section images are made available under the same CC BY-SA 4.0 license. (This applies to the *images*; the zoning text of the Core Zoning Code is a separate work under its own terms.)

`NOTICE.md` records the source, license, the exact sprite subset vendored, and the fact that no sprite was altered (compositing, scaling, callouts, and chrome are original to this repository).

## 6. The one regulatory-text edit — Article 3 §2.c.5

A single new numbered item in §2.c (GENERAL), so the code itself acknowledges the figures:

> *"A full-page cross-section plate for each numbered Type (S-1 through S-5 and R-1 through R-5) appears at the end of this Article. Each plate illustrates the representative arrangement and typical widths of that Type's right-of-way components and summarizes its principal design standards. The plates are illustrative; where a plate and the standards of Section 3 differ, Section 3 controls. No plate is provided for the Driveway (D), which is not a Street or Road Type."*

This fixes the **legal precedence** (the binding standard is the Table, not the drawing), explains the **absence of a Driveway plate**, and gives the reader a **forward reference**. No width, range, table, or definition is touched.

## 7. Defect fixed along the way — running-head group label (`cross-section-plates.typ`)

Typst resolves a `state.update()` placed in the page *body* **after** a page header queries that state, so a section label driven by body-state lags one page. On the plates this mislabeled the first plate's running head ("Street & Road Types" — the default) and the Street→Road transition page (R-1 reading "Street Types"). Replaced the mutable state with a **page-anchored `<plate-group>` metadata marker**: each plate emits a marker, and the header `query`s all markers and picks the last one on or before the current physical page. This is lag-free and also correct when a **single** Type is rendered standalone (`--input only=R-1`), which the old state approach could not do. *(The analogous latent lag in `article-02.typ` at its Core→Special district boundary is noted for a separate fix; it does not affect this release.)*

## 8. What did NOT change

- **No regulatory standard added or altered.** Article 3's typology, ROW ranges, and Tables 3.1a–3.4 are unchanged; §2.c.5 is a pointer note, not a standard. Articles 1, 2, 4–9 are untouched apart from the footer version stamp and the +10-page downstream shift.
- **The body content is byte-stable** apart from the §2.c.5 sentence and the footer version string — same district spreads, same parity, same TOC grammar from v0.6 (with page targets shifted +10 after Article 3).
- **No Driveway graphic.** Ten plates only, by design.

## 9. Deliverables

- **`Newcastle CZC (Integrated Draft v0.7-draft).pdf`** — 111 pp (4 front matter + 107 body); plates at printed pp 43–52.
- **`Newcastle CZC (Integrated Draft v0.7-draft).md`** — concatenated markdown source; a pointer comment marks where the plates render (they have no markdown form).
- **`Article 3 Streets Roads & Driveways (Standalone v0.7-draft).pdf`** — 20 pp (10 prose + 10 plates).
- **`Article 3 Streets Roads & Driveways (Standalone v0.7-draft).md`** — Article 3 prose source.
- **`Summary of Changes v0.7-draft.md`** — this document.

No `diff-pdf` overlay is shipped: the substantive delta is +10 new pages and one new sentence, and the footer version stamp differs on every page (which an overlay would flag as noise on all 107 body pages). The new material is wholly new pages, best reviewed directly.

## 10. Files changed

- **`build/build-cross-sections.py`** *(new)* — Python SVG compositor; reads `types.json`, emits one self-contained `<CODE>.svg` per Type.
- **`source/cross-section-plates.typ`** *(new)* — native-Typst plate layout; reuses `article-02.typ` chrome; aspect-aware section sizing; page-anchored group marker.
- **`source/exhibits/cross-sections/types.json`** *(new)* — single source of truth for all 10 Types (segments, widths, sprites, surfaces, standards, notes).
- **`source/exhibits/cross-sections/*.svg`** *(new, generated)* — the 10 composed cross-sections (regenerable from `types.json`).
- **`source/exhibits/cross-sections/sprites/`** *(new, vendored)* — 28 unmodified Streetmix CC BY-SA sprites + `NOTICE.md` provenance/attribution.
- **`source/article-03-streets-roads-driveways.md`** — new §2.c.5 pointer note (only regulatory-text change).
- **`build/build-full-czc.sh`** — splices the plate block into the render order after Article 3; adds the combined-markdown pointer comment.
- **`build/build-article-3.sh`** — appends the plate block to the standalone at an even offset (pads the prose to even first if needed).
- **`releases/v0.7-draft/`** — Integrated (111 pp) `.md`/`.pdf`, Article 3 standalone (20 pp) `.md`/`.pdf`, and this Summary.

## 11. Verification

- **Integrated PDF: 111 pp** = 4 front matter + 107 body. Article 3 prose pp 33–42; **plates pp 43–52**; Article 4 opens recto at p 53. TOC auto-updated (Art. 4 → 53, … Art. 9 → 101).
- **All 10 plates render clean** — segment width callouts fit and never collide; double-yellow centerlines on two-way Types; no centerline on single-lane S-4/S-5/R-3; rural Types show grass verges/trees and (R-3) gravel; S-5 Alley is height-capped and centered (does not tower); R-4/R-5 show the MaineDOT illustrative override on both the ROW bracket and the credit line.
- **Running heads correct on every plate** — S-1…S-5 read "Street Types", R-1…R-5 read "Road Types" (the one-page lag is fixed); badge/tab/footer parity correct (verso = left fore-edge, recto = right).
- **Footers continuous & parity-correct** across the prose→plate and plate→Article-4 seams; footer reads **"Draft v0.7-draft"**.
- **Standalone Article 3: 20 pp** — prose pp 1–10, plates pp 11–20; S-1 plate opens recto at p 11.
- **Licensing present** — every plate carries the CC BY-SA credit; `NOTICE.md` records source/license/sprite subset.
- **Build reproducibility** — `build-cross-sections.py` regenerates all 10 SVGs from `types.json`; `build-full-czc.sh` and `build-article-3.sh` reproduce the committed PDFs.

## 12. What's still off (carry forward)

1. **Plates sit at the end of Article 3, not interleaved after each Type's §2 prose.** End-placement is the page-number-safe choice (see §4). True interleave would require splitting the Article 3 prose render at the §2/§3 boundary and a "continuation" mode in the template (no second article-opener) — a future refinement, not a defect. §2.c.5 forward-references the plates so the reader is not surprised.
2. **`article-02.typ` running-head lag** at the Core→Special district boundary (same Typst mechanism fixed here in §7) is unaddressed in this release; queued as a separate fix so it doesn't perturb Article 2's reviewed output.
3. **Comprehensive Plan citations** in §3.d remain to be re-verified against the adopted Comp Plan before public release (carried from v0.6).
4. **The ROW Justification Memo** remains an unadopted discussion draft *by design* (carried from v0.6).
