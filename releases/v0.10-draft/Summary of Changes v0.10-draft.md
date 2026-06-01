# Summary of Changes — v0.10-draft

**Release type:** **Additive / restorative — it adds content that was missing, and changes no regulatory text.** The baseline *Newcastle Core Zoning Code* closes Article 1 with three full-page zoning **District Map exhibits** — **EXHIBIT 1.1 District Map** (the whole town), **EXHIBIT 1.2 District Map Inset — Newcastle Town Center**, and **EXHIBIT 1.4 District Map Inset — Sheepscot Village**. Every generated draft from v0.1 through v0.9 carried Article 1's §3 DISTRICT MAP *prose* but **omitted the three map exhibits themselves**, because they are not text: each is a GIS composite — hundreds of vector zoning-district / road / boundary paths layered over a sliced-JPEG aerial basemap, with a KEY legend, scale bar, compass rose, and the original cartographer's credit — which pandoc/markdown cannot express. This release restores all three, rendered natively and reseated in our own Article-1 page chrome. **No Article, section, standard, table, definition, or cross-reference changes.**

This release also folds in **two presentation refinements** to the native-Typst renderers, both surfaced in review of the v0.10 draft. They change *how* existing content is drawn, never *what* it says: (1) the **doubled hairline** that appeared under roughly half the table headings is reduced to a **single rule**, and (2) each District's **Use Table page** is reset to **three equal columns with wider gutters**. Both are layout-only and confined to the native-Typst units (the Article-2 District spreads and the Article-3 Type plates); no regulatory text, dimension, table value, or cross-reference changes, and every markdown-rendered Article is byte-identical to v0.9. See §6.

**Compares against:** [v0.9-draft](../v0.9-draft/). Because this release **inserts** pages mid-document (the three maps + one parity-pad blank land after Article 1), every downstream page shifts by **+4**. A naïve positional `diff-pdf` therefore flags all 100+ downstream pages purely from the shift; the committed draft-to-draft redline is instead **alignment-corrected** so it isolates the real changes — the three new map pages and the two presentation refinements (§6) — see §7.

**Why this release exists.** The omission was first noticed in review: the generated CZC's Article 1 ended at the §3 DISTRICT MAP prose and jumped straight to Article 2, where the baseline shows three map pages. The maps are the visual key to the entire form-based code — every District (D1–D6) and Special District boundary the rest of the document regulates is *defined* by these exhibits — so their absence was a real content gap, not a cosmetic one. The fix uses the project's established **rasterize-and-reseat** pattern: the same approach already used to bring the Article-2 District spreads and the Article-3 Street/Road Type plates into the document as native pages.

---

## 1. What changed, in one picture

| | v0.9 | **v0.10** |
|---|---|---|
| **Article 1 District Map exhibits** | absent (prose only) | **EXHIBIT 1.1 / 1.2 / 1.4 restored as full pages** |
| **How the maps render** | — | **native Typst (`source/district-maps.typ`) reseating 300-DPI rasters of the baseline exhibits** |
| **Regulatory text (all Articles)** | — | **unchanged — byte-for-byte** |
| **Integrated length** | 111 pp | **115 pp** (+3 maps, +1 parity-pad blank) |
| **Maps land at (printed)** | — | **pp 3 / 4 / 5** — recto / verso / recto, the baseline's own 1.1 / 1.2 / 1.4 sequence |
| **Article 2 opener** | printed p 3 | **printed p 7** (+4) |
| **Article 3 opener / plates** | p 33 / pp 35–44 | **p 37 / pp 39–48** (+4) |
| **Articles 4–9** | pp 53 / 59 / 67 / 75 / 85 / 101 | **pp 57 / 63 / 71 / 79 / 89 / 105** (+4) |
| **Plate parity (10 plates = 10 pp)** | even offset, verso/recto-correct | **unchanged — even offset preserved, badges still verso/recto-correct** |
| **Table heading rules** (native-Typst units) | doubled hairline under ~half the headings | **single rule under every heading** |
| **District Use Table page** (recto) | columns 0.72 / 0.72 / 1 fr | **three equal columns + wider gutters** |
| **TOC "DISTRICT MAP" entry (Art. 1)** | present (points to §3 prose) | **unchanged** (matches the baseline, which never listed the exhibits individually) |
| **Standalone Article 3** | 20 pp | **20 pp** (the plate single-rule fix shows on its 10 Type plates; page count + text unchanged) |

The crucial invariant: the three maps plus one parity-pad blank are an **even** insertion (+4), so every Article after the maps keeps its exact page **parity**. Article 2 still opens on a recto; the ten Type plates still sit at an even `page_offset` (now 38, was 34) and their verso/recto badge placement is unchanged. The map sequence even reproduces the baseline's own page positions — **EXHIBIT 1.1 on a recto, 1.2 on the verso, 1.4 on a recto** (physical pp 7 / 8 / 9, exactly where the baseline prints them).

## 2. The three exhibits

The baseline carries exactly three District Map exhibits (the numbering skips 1.3 — there is no such exhibit). All three are restored:

| Exhibit | Title | Coverage | Printed page |
|---|---|---|---|
| **1.1** | District Map | Whole Town of Newcastle, with KEY legend, scale bar, compass rose | **3** (recto) |
| **1.2** | District Map Inset — Newcastle Town Center | Town Center detail, legend at foot | **4** (verso) |
| **1.4** | District Map Inset — Sheepscot Village | Sheepscot Village detail, legend at foot | **5** (recto) |

Each renders as a full page under Article 1, with the same chrome as every other Article-1 page: the **GENERAL STANDARDS** running head on the outer edge, the rotated **ARTICLE 1** tab in the outer margin, the continuous **Newcastle Core Zoning Code | <page>** footer with the draft date, and the baseline's own **EXHIBIT n.n  TITLE** caption (11 pt bold, subsection-gray) at the top of the body. The maps follow Article 1's prose (§§1–5) and precede Article 2, exactly as in the baseline.

## 3. How the maps were brought in — rasterize-and-reseat

The baseline maps are **not** single images that could be dropped into markdown. Inspected with PyMuPDF, each page is a composite of **hundreds of vector paths** (the zoning-district polygons, roads, and boundary lines — 194 / 405 / 287 paths on the three pages) drawn over a **sliced-JPEG aerial basemap** (≈30 horizontal strips) plus a small compass-rose PNG, credited to *Northern Geomantics, Bradford, NH*. That is not faithfully redrawable in any markup, so — exactly as for the Article-2 District spreads and the Article-3 Type plates — the maps are **rasterized and reseated**:

1. **Extract.** Each exhibit's content region was rendered at **300 DPI** — the basemap's native resolution, so there is **no upscaling and no detail loss** — and the baseline's own page chrome (its header, footer, side tab, and EXHIBIT caption) was cropped away, leaving only the clean map, legend, scale bar, compass, and the baked-in cartographer credit. The three crops live in **`source/exhibits/district-maps/`** (≈6 MB total).
2. **Reseat.** A new native-Typst renderer, **`source/district-maps.typ`**, places each clean raster inside our Article-1 chrome. Geometry, palette, header/footer, and the rotated article tab are copied verbatim from `style/czc-template.typ` (the markdown-article chrome) so a map reads as a torn-out page of the same code. Each map is fit-by-height inside a fixed box (aspect ≈ 0.64; the height-fit image is ~410 pt wide, centered in the 478 pt text block), which **guarantees each exhibit stays on a single page** — an overflow to a second page would break the 3-page count and the document parity.

The renderer threads the same cumulative **even page-offset** + footer date that every other unit receives, so its parity-aware chrome (verso/recto edge flipping) is correct in position, and its footers number continuously with the rest of the body.

## 4. Build integration & parity

`build/build-full-czc.sh` was extended to splice the maps in, mirroring the existing Type-plate splice:

- **Splice.** After the article render-unit list is assembled, `district-maps.typ` is inserted immediately **after `article-01-*.md`**. The render loop's existing `*.typ` branch handles it generically — same `--input page_offset` / `--input footer_date` it already passes to the Article-2 spreads and the Type plates. No new render logic.
- **Parity-pad.** Article 1's prose renders to 2 pages (even) and ends at offset 2; the maps unit renders to 3 pages (odd), so the build's standing odd-length pad appends **one trailing blank** (printed p 6), bringing the offset to 6 (even) before Article 2. This is the existing pad mechanism, not new code — the three maps simply make Article 1's contribution to the body an even +4.
- **Combined markdown.** A human-readable pointer note is injected after Article 1 in the concatenated `.md` (mirroring the Article-2 spread note), since the native-Typst maps have no markdown form.

Because +4 is even, the offset threading downstream is unchanged in parity: maps at offset 2 → Article 2 prefatory at offset 6 → District spreads at offset 8 → … → **Type plates at offset 38 (even, was 34)** → … The plates' verso/recto correctness, which depends only on the offset being even, is preserved.

## 5. The TOC — why no change was needed

The baseline's own CONTENTS lists a single **DISTRICT MAP** entry under Article 1 (pointing to the §3 prose section), **not** the three exhibits individually. Our auto-derived TOC (`build/toc_entries.py`, which scans the rendered body for 14 pt blue section headings) already emits exactly that entry from the `## 3. DISTRICT MAP` heading in `article-01-general.md`. The EXHIBIT captions render at 11 pt subsection-gray — not a scanned signal — so they neither add spurious TOC lines nor need new TOC logic. **The TOC matches the baseline's treatment with no code change.**

## 6. Presentation refinements (two rendering fixes)

Two layout issues in the native-Typst renderers — both surfaced in review of the v0.10 draft — are fixed this release. Each changes only *how* existing content is drawn; **no regulatory text, dimension, table value, or cross-reference is altered**, and both are confined to the native-Typst units (the 13 Article-2 District spreads and the 10 Article-3 Type plates). The pandoc-rendered markdown Articles are byte-identical to v0.9.

**a. Doubled rule under table headings → single rule.** In the native-Typst units, each panel heading (e.g. **DESCRIPTION**, **LOT DIMENSIONS**, **DESIGN STANDARDS**, **PERMITTED BUILDING GROUPS**, a plate's **Design Standards**) draws a hairline beneath itself — and the data table immediately under it *also* stroked a **top** hairline, so roughly half the tables showed **two parallel rules ≈3.5 pt apart** while the other half (whose first row carried no top border) showed the intended single rule. The three offending tables — the District `lvtable` (label/value) and the `permitted_buildings` matrix in `source/article-02.typ`, and the plate `standards_strip` in `source/cross-section-plates.typ` — now stroke their **bottom border only**, so the panel's own rule is the single line under every heading. A stroke is paint, not layout: no row moved, no page count changed, and parity is untouched.

**b. District Use Table page → three equal columns.** Each District's recto (the Use Table page) previously laid its three columns at unequal widths (`0.72fr / 0.72fr / 1fr`), crowding the two use-category columns against a wider legend/standards column. The recto grid is reset to **three equal columns (`1fr` each)** with the inter-column gutter widened from ~14 pt to ~22 pt — balanced, evenly separated columns: use categories in columns 1–2, the Use Table Legend + Use Standards in column 3, with the faint vertical dividers retained. **Every one of the 13 Districts still fits its recto on a single page**, so the 2-page-per-District invariant — and therefore document parity — is preserved. (One cosmetic consequence at the narrower column 3: the longest legend label, "Residential Companion Permit Required," now wraps to two lines; it remains centered against its badge and fully legible.)

Both fixes touch only native-Typst source, so in the rendered PDF they appear on the 13 Article-2 District spreads and the 10 Article-3 Type plates. The standalone Article 3 picks up fix (a) on its ten plates (text and 20-page count unchanged); Article 2 is integrated-only.

## 7. Relationship to the baseline & redlines

This release moves the generated CZC **closer** to the baseline: it adds the three map pages the baseline has and we lacked. No baseline-derived regulatory text is touched.

- **`Redline — Full CZC v0.10-draft vs v0.9-draft.pdf`** *(committed; alignment-corrected)* — the meaningful diff. `diff-pdf` compares **positionally** (page against same-numbered page), so a raw overlay of v0.10 (115 pp) against v0.9 (111 pp) would mis-align everything after the insertion and flag 100+ pages from the +4 shift alone — and at **102.7 MiB** the raw overlay also exceeds GitHub's 100 MiB hard limit. To produce a *content-meaningful* overlay, the v0.9 PDF was first **padded with four blank pages at the insertion point** (after Article 1's prose, where v0.10 places the maps + parity blank), bringing it to 115 pp and re-aligning every downstream page with its v0.10 counterpart. The corrected overlay shows the **real changes**: (i) **pp 7–9 are the three new maps**, rendered in highlight as added content (they were blank in the aligned v0.9); (ii) the **13 District spreads and 10 Type plates carry the two presentation refinements of §6** — most visibly the District Use Table pages reset to three equal columns, plus the single-rule table-heading fix; and (iii) every page shows the footer page-number renumbering +4 (a true, if trivial, consequence of inserting four pages). The pandoc-rendered markdown body is otherwise identical black text. At **67.7 MiB** it commits within the limit (drawing the same >50 MiB advisory warning v0.9's committed redline drew); the alignment correction keeps it well under the raw 102.7 MiB by marking most pages as only-footer-differs rather than wholly-shifted.
- **`Redline — Full CZC v0.10-draft vs Baseline.pdf`** *(generated locally, NOT committed)* — included on disk for completeness with the standing caveat carried since v0.5: once the draft added a cover, an auto-TOC, native District spreads, and Type pages, a physical overlay against the baseline aligns on no page and reads as noise. At **110.5 MiB** it also exceeds GitHub's 100 MiB hard limit, so — exactly as every prior vs-Baseline redline since v0.5 — it is produced by the build but **excluded from the commit**.

## 8. Deliverables

- **`Newcastle CZC (Integrated Draft v0.10-draft).pdf`** — 115 pp (4 front matter + 111 body); Article 1 prose at printed pp 1–2, **District Maps at pp 3–5**, parity-pad blank at p 6, Article 2 at p 7, Article 3 at p 37 (plates pp 39–48), Articles 4–9 at pp 57 / 63 / 71 / 79 / 89 / 105.
- **`Newcastle CZC (Integrated Draft v0.10-draft).md`** — concatenated markdown; a pointer comment after Article 1 marks where the three maps render.
- **`Article 3 Streets Roads & Driveways (Standalone v0.10-draft).pdf`** — 20 pp; text and page count unchanged from v0.9, but its **ten Type plates carry the single-rule table-heading fix** of §6.a (the maps are Article 1, so they do not appear here).
- **`Article 3 Streets Roads & Driveways (Standalone v0.10-draft).md`** — Article 3 source (unchanged).
- **`Redline — Full CZC v0.10-draft vs v0.9-draft.pdf`** *(committed)* — alignment-corrected draft-to-draft overlay (v0.9 padded with four blanks at the insertion point) isolating the three new map pages **and the two presentation refinements**; 67.7 MiB. See §7.
- **`Redline — Full CZC v0.10-draft vs Baseline.pdf`** *(not committed)* — full overlay vs. the original (page-misaligned and 110.5 MiB > GitHub's 100 MiB limit); generated locally only. See §7.
- **`Summary of Changes v0.10-draft.md`** — this document.

## 9. Files changed

- **`source/district-maps.typ`** *(new)* — native-Typst renderer for the three Article-1 District Map exhibits; reseats the extracted rasters in Article-1 chrome (GENERAL STANDARDS head, ARTICLE 1 tab, continuous footer, baseline EXHIBIT caption), fit-by-height to guarantee one page each. Threads the cumulative even `page_offset` + `footer_date` like every other native unit.
- **`source/exhibits/district-maps/`** *(new — 3 files)* — `exhibit-1.1-district-map.png`, `exhibit-1.2-town-center.png`, `exhibit-1.4-sheepscot-village.png`: 300-DPI crops of the baseline exhibits' content regions, baseline chrome removed, the original Northern Geomantics credit retained in-image.
- **`build/build-full-czc.sh`** — splice `district-maps.typ` into the render-unit list after `article-01-*.md` (mirroring the Type-plate splice); inject a combined-markdown pointer note after Article 1. No change to the render loop, the pad logic, the offset threading, or the TOC step.
- **`source/article-02.typ`** *(presentation only — §6)* — (a) the District `lvtable` and `permitted_buildings` matrix now stroke their **bottom** border only, removing the doubled heading rule; (b) the recto Use-Table grid changed from `columns: (0.72fr, 0.72fr, 1fr)` to **`(1fr, 1fr, 1fr)`** with the inter-column inset widened 7 pt → 11 pt per side. No district data, value, or text changed.
- **`source/cross-section-plates.typ`** *(presentation only — §6.a)* — the plate `standards_strip` (the 3-column Type-standard / Build-To table) now strokes its **bottom** border only, removing the doubled rule under the plate's **Design Standards** heading. No Type dimension, Build-To value, or footnote changed.

**Not touched:** every regulatory source file (`article-01` … `article-09`, `types.json`, `article-02-data.json`), all build scripts other than `build-full-czc.sh`, `toc_entries.py`, and the style template (`czc-template.typ`). The two native-Typst renderers above changed only stroke direction and column geometry — paint and layout, never content; all district/Type **data** is byte-unchanged from v0.9.

## 10. Verification

- **Integrated PDF: 115 pp.** Body 107 → 111 (+3 maps, +1 parity-pad blank); 4 front-matter pages prepended. Confirmed by page-count read.
- **Maps render correctly in context.** EXHIBIT 1.1 / 1.2 / 1.4 at physical pp 7 / 8 / 9 (printed 3 / 4 / 5), each on exactly one page, no clipping and no second-page overflow; full maps, legends, scale bars, compass, and the baked-in GIS credit all present. Chrome flips edges correctly by parity — header + tab on the right for the recto exhibits (1.1, 1.4), on the left for the verso exhibit (1.2); footers read **3 / 4 / 5** with the draft date.
- **Parity preserved downstream.** Article 2 opener still on a recto (printed p 7); the ten Type plates render at even offset 38 with badges verso/recto-correct — spot-checked the S1 Main Street plate at printed p 39 (recto), badge on the outer/right edge, intact. Every Article-opener page shifted exactly +4 vs v0.9.
- **TOC unchanged and correct.** Article 1 still lists its 5 section entries including **DISTRICT MAP**; no spurious exhibit entries; downstream article page numbers re-derived to the new positions.
- **Parity-pad blank.** Physical p 10 (printed p 6) is a genuine blank (0 text characters), sitting between the maps and Article 2.
- **No regulatory drift.** All Article markdown, `types.json`, and `article-02-data.json` are byte-unchanged from v0.9. The two changed renderers (`article-02.typ`, `cross-section-plates.typ`) altered only stroke direction and column geometry — confirmed by diff that no district datum, Type dimension, Build-To value, or label string changed.
- **Fix (a) — single rule, verified at 300 DPI.** D1's verso lv-tables (DESCRIPTION, LOT DIMENSIONS, DESIGN STANDARDS) and the S1 plate's **Design Standards** table each show exactly one rule under the heading (the panel line; the table's first row no longer adds a top hairline). No row shifted; the integrated PDF is still 115 pp and the standalone Article 3 still 20 pp.
- **Fix (b) — three equal columns, verified across all 13 Districts.** Each District recto renders three equal-width columns with widened gutters; spot-checked D2 (integrated printed p 13) and a contact sheet of all 13 rectos. Every recto still fits **one page**, so each District remains exactly 2 pages and document parity is unchanged.
- **Redline sanity.** The committed alignment-corrected redline (67.7 MiB) shows the three maps as added content on pp 7–9 and marks the Use-Table column change on the District rectos — confirmed by spot-rendering redline pp 7 and 17.
- **Build reproducibility.** `build-full-czc.sh v0.10-draft "May 31, 2026"` reproduces the integrated PDF/markdown; `build-article-3.sh` reproduces the standalone; `build-redline.sh` reproduces the vs-baseline redline, and the committed vs-v0.9 redline is the alignment-corrected overlay (v0.9 padded with four blanks at the insertion point, then `diff-pdf` vs v0.10).

## 11. Notes & carry-forward

- **GIS credit retained.** The original cartographer's attribution (*Northern Geomantics, Bradford, NH*) is baked into the baseline rasters and is preserved in-image; no separate typeset credit was added (the maps reproduce the baseline exhibits faithfully).
- **Source provenance.** The maps are rasterized from `docs/Newcastle Core Zoning Code.pdf`, the project's read-only baseline. If the Town issues updated official District Maps, re-running the extraction against the new source and rebuilding regenerates the exhibit pages — the rest of the pipeline is unaffected.
- **Resolution.** 300 DPI matches the basemap's native resolution; the crops are exact (no upscaling). They print crisply at full page size.
- **Carry-forward items** from v0.9 are unchanged (Comp-Plan citation re-verification in §3.D, the unadopted ROW memo, the `article-02.typ` running-head lag, the existing-street inventory, Article 2 per-District §3.F pointers, the deferred transit-stop sidewalk trigger, and the dropped Option E parking incentive). None is affected by this release.
