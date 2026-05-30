# Summary of Changes — v0.5-draft

**Release type:** **Major structural release.** Replaces the hand-transcribed Article 2 district pages with **13 faithful 2-page district spreads re-derived directly from the baseline PDF** (`docs/Newcastle Core Zoning Code.pdf`) and rendered natively in Typst, then wires that renderer into the full-document build. This is the "district-pages overhaul" the Town directed: *each district is now its own 2-page spread, laid out to match the original, with all content read from the source rather than hand-typed.* No new regulatory standard is introduced in this release — the change is one of **fidelity and architecture**, restoring the district content the markdown transcription had distorted.

**Compares against:** [v0.4.5-draft](../v0.4.5-draft/).

**Why this release exists.** The district pages in every prior draft were generated from `source/article-02-districts.md`, a hand-keyed transcription that the Town flagged as **not accurate** — panel content, the use matrices, the status glyphs, and the per-district banners had all drifted from the adopted code. Rather than re-type 13 districts by hand again, this release **reads them out of the baseline PDF programmatically** (every panel heading, list, label/value pair, permitted-building matrix, use column, status glyph, and band color) into a single data file, and renders that data through a purpose-built Typst layout that reproduces the baseline's two-column verso (standards) + recto (use-matrix) spread. Hand-entry error is now impossible: change the code, re-run the extractor, re-build.

---

## 1. What changed, in one picture

| | v0.4.5 and earlier | **v0.5** |
|---|---|---|
| **District content** | hand-transcribed in `article-02-districts.md` (Town: "NOT accurate") | **extracted from the baseline PDF** into `article-02-data.json` (13 districts) |
| **District rendering** | pandoc → markdown tables (one compressed block per district) | **native Typst** 2-page spread per district (verso standards / recto use-matrix) |
| **Article 2 §1–§5 prose** | inside the same markdown file | split to `article-02-prefatory.md`, still pandoc-rendered (keeps nested 1./a./i. numbering + the baseline prose-page header) |
| **Status glyphs** (Use/Special/Expanded/Companion permit) | missing / placeholder (carried-forward defect) | **rendered**: ● ❶ ❷ ✪ |
| **District banners** | approximate colors | **band fill + text color read straight from the baseline** per district |
| **Integrated length** | 91 pp | **97 pp** (faithful 2-page spreads add ~6 pp net) |

## 2. The extraction pipeline (new `extract/`)

Nothing in the district spreads is hand-transcribed. Three scripts read the baseline:

- **`extract/verso.py`** — parses a district's **standards page**: bold `#7C766F` panel headings, then the body of each panel classified as paragraph / numbered-list (with nested a/b/c) / label-value pairs, plus the full-width **PERMITTED BUILDINGS** matrix. Cross-references to other Articles are **renumbered for the integrated draft on the way out** (old 3→4 Site, 4→5 Building, 5→6 Design, 6→7 Use, 7→8 Admin, 8→9 Definitions; new Article 3 = Streets).
- **`extract/recto.py`** — parses the **use-matrix page**: two columns of use categories, each use row's Wingdings **status glyph** mapped to `u`/`rc`/`sp`/`ex`, plus the USE TABLE LEGEND and the numbered USE STANDARDS list.
- **`extract/gen_districts.py`** — drives both over the 13 spread page-pairs (verso indices 11,13,15,17,19,21 = D1–D6; 23,25,27,29,31,33,35 = the 7 Special Districts), reads each band's **code/name/text-color/fill** from the PDF, and writes **`source/article-02-data.json`**.

The renderer **`source/article-02.typ`** is structure-agnostic: it lays out whatever ordered `left`/`right` panel arrays and optional `matrix` the data carries, so a future baseline correction flows through without touching layout code.

## 3. Hybrid Article-2 architecture

Article 2 now renders from **two** sources concatenated at its slot:

1. **`source/article-02-prefatory.md`** (§1 Districts, §2 Lots, §3 Setbacks, §4 Special Map Requirements, §5 Civic District) — stays in markdown/pandoc because the prose relies on nested ordered-list numbering (1./a./i.) and the baseline's *prose-page* header shows only "DISTRICT STANDARDS" (no group label). These were already integration-ready (frontage reworded to "Street or Road of a Type defined in Article 3"; cross-refs renumbered).
2. **`source/article-02.typ`** (the 13 district spreads) — native Typst, because a faithful 2-page spread with a fore-edge badge, a rotated article tab, two measured columns, and a variable-column permitted-buildings matrix **cannot be expressed in markdown**.

The old combined `article-02-districts.md` is **moved to `source/legacy/`** — preserved for reference, out of the build, referenced by nothing outside `releases/`.

## 4. Build-pipeline wiring (`build/build-full-czc.sh`)

- The article glob now collects **both** the markdown articles and the lone native-Typst file: `ls article-*.md article-02.typ | sort`. Lexical sort interleaves them correctly — `article-02-prefatory.md` (hyphen, 0x2D) sorts before `article-02.typ` (dot, 0x2E), both after `article-01` and before `article-03` — so the render order is prose-then-spreads with no special-casing.
- The render loop **dispatches by extension**: `*.typ` compiles directly with `typst` (threading the same cumulative even `page_offset` and `footer_date`); everything else goes through the existing pandoc `build-article.sh`.
- The **parity invariant is preserved**: margins/tab key off the *physical* page, chrome (header/footer) off the *logical* page = `here().page() + page_offset`, so `page_offset` must stay **even**. `article-02.typ` lands D1 on a verso via a leading `#pagebreak(to:"even")`; that one leading page is a true parity blank, and three context guards (`if here().page() == 1 { return [] }`) keep header, footer, and article-tab **off** it.
- The combined `.md` deliverable now cats only the markdown units and injects an HTML-comment pointer at Article 2's position noting that the 13 district spreads render natively from `article-02-data.json` (they have no markdown form).

## 5. Carried-forward defects resolved this release

Two items the v0.4.5 carry-forward list flagged are now **fixed** as a side effect of the overhaul:

- **Use-table status glyphs** — previously "`❶ ❷ ✪` need a fallback font" / placeholder. Now rendered from real data via `glyph_font = ("Apple Symbols", "Arial Unicode MS")`: ● (Use Permit) ❶ (Special Permit) ❷ (Expanded Use) ✪ (Residential Companion). Counts in the integrated PDF: ● ×302, ❶ ×79, ❷ ×84, ✪ ×66.
- **District-page banner styling** — band fill color and band text color are now read **per district from the baseline** (e.g., D6 Town Center's dark band with light text, the Special Districts' shared "SD" treatment) rather than approximated.

## 6. What did NOT change

- **No new or altered regulatory standard.** Article 3 (Streets, Roads & Driveways) — including the v0.4.5 ROW ranges, Comp Plan citations, Tables 3.1a/3.1b/3.2/3.3/3.4 — is **untouched**. Articles 1 and 4–9 are untouched. This release changes how Article 2's districts are *sourced and rendered*, not what they require.
- **Cross-reference renumbering** (old→new 3→4 … 8→9) is the same mapping used everywhere else; it is now applied to the district text **automatically** in the extractor (confirmed: D6's verso reads "Article 6", was "Article 5" in the baseline).
- **Standalone Article 3** holds at **9 pp**, byte-for-byte the v0.4.5 content (only the footer version string differs).

## 7. Redline decision

A page-by-page visual overlay against v0.4.5 is **not** included this release, by design. The district pages are entirely re-rendered and the document grew 91 → 97 pp, so every page from Article 2 onward shifts — a full-document overlay would be ~all-pages-changed noise (the v0.4.5 cross-version overlays ran 100–200 MB for far smaller changes and were deleted). In its place, this release ships a **focused fidelity comparison**:

- **`District Spread Fidelity — Baseline vs v0.5-draft.pdf`** (6 pp) — D1 Rural, D6 Town Center, and SD-Historic, each verso + recto, **baseline on the left / v0.5 draft on the right**, so a reviewer can confirm the spreads read as the same document. This is the plan's "visual integration check"; the structural narrative above is the "Summary of Changes fills the gaps the visual diff misses."

## 8. Files changed

- **`build/build-full-czc.sh`** — glob + extension-dispatch render loop + combined-`.md` pointer note (+57/−9).
- **`source/article-02.typ`** *(new)* — native district-spread renderer; structure-agnostic panels + variable-column matrix; leading parity-blank with chrome suppressed.
- **`source/article-02-prefatory.md`** *(new)* — Article 2 §1–§5 prose, integration-ready.
- **`source/article-02-data.json`** *(new)* — 13 districts, extracted from the baseline.
- **`extract/`** *(new)* — `verso.py`, `recto.py`, `gen_districts.py`, plus mapping/probe helpers; the reproducible derivation pipeline.
- **`source/article-02-districts.md` → `source/legacy/`** — moved out of the build; preserved.
- **`style/fonts/Barlow-{Regular,Medium,SemiBold,Bold}.ttf`** — committed so `--font-path` resolves the body family on a clean clone.
- **`releases/v0.5-draft/`** — Integrated Draft (97 pp) `.md`/`.pdf`, Article 3 standalone (9 pp) `.md`/`.pdf`, the fidelity comparison `.pdf`, and this Summary.

## 9. Verification

- **Integrated PDF: 97 pp.** Blank parity pads at physical pages **5, 32, 42, 64, 74, 90** (page 5 is the clean section-break blank before D1 — header/footer/tab all suppressed, confirmed empty).
- **Footers continuous and parity-correct.** Printed number == physical page on every non-blank page (spot-verified at pp. 6, 16, 21, 33, 34, 41, 51, 76, 92, 97); even/verso pages carry the number at the left fore-edge (x≈44), odd/recto at the right (x≈560); footer reads **"Draft v0.5-draft"**.
- **Status glyphs render** (● ❶ ❷ ✪) with the counts in §5.
- **Cross-ref renumber confirmed** in district text ("Article 6" ×8, "Article 5" ×7) and **zero legacy RDEO references** ("Driveway, Road…") survive in the district spreads.
- **Visual fidelity** confirmed on the prose opener, the D1 spread (verso badge at left fore-edge, recto use-matrix), and D6 (light-on-dark band, 4-column permitted-buildings matrix) against the baseline via the fidelity comparison.

## 10. What's still off (carry forward)

1. **Stale table numbers from the Article renumbering (DEFERRED).** Art. 4 tables still read "3.x" (colliding with the new Article 3), Art. 5 "4.x", Art. 6 "5.x", Art. 8 "7.x". The new Article 3's own tables (3.1a/3.1b/3.2/3.3/3.4) and Article 2's matrices are correct.
2. **Cross-section graphics — 10 needed.** One annotated cross-section per Street/Road Type still unproduced.
3. **Front matter (cover + TOC)** still absent, so Articles open on recto rather than the baseline's verso.
4. **R-2 maximum grade (12%) vs. RDEO's 10%** — unresolved engineering reconciliation, carried unchanged.
5. **Memo finalization** — the Right-of-Way justification memo keeps a blank FROM line and remains an unadopted discussion draft.
