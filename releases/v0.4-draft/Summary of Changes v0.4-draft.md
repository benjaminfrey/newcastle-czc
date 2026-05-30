# Summary of Changes — v0.4-draft

**Release type:** Layout/typography correction pass. A second, deeper forensic measurement of the baseline — focused on **margins, column widths, the space between columns, headers, footers, and tables** — fixed the specific defects flagged in review and corrected geometry that v0.3 had only estimated.

**Compares against:** [v0.3-draft](../v0.3-draft/) and the baseline [docs/Newcastle Core Zoning Code.pdf](../../docs/).

**Reported defects addressed:**
- ❌ → ✅ "Article 3" and "Streets, Roads & Driveways" **overlapping** on the opener.
- ❌ → ✅ "There should be a **blank row below each sub-section header**."
- ❌ → ✅ Thorough forensic analysis of **margins, column widths, space between columns, headers and footers, and all tables** ("which need serious help").

---

## 1. Forensic measurements (baseline) and corrections applied

All values measured from the baseline PDF with `pymupdf` span/drawing extraction. Scripts: `forensic_layout.py`, `forensic_tables.py`, `forensic_table_geom.py`, `forensic_pagenum.py`.

| Element | Baseline (measured) | v0.3 (was) | v0.4 (now) |
|---|---|---|---|
| Inside (binding) margin — WIDE | 90 pt | 68 pt | **90 pt** |
| Outside (tab) margin — NARROW | 44 pt | 45 pt | **44 pt** |
| Top margin | ~64 pt (first line ~65) | — | **64 pt** |
| Bottom margin | ~56 pt (floor ~736) | — | **56 pt** |
| **Column gutter (space between columns)** | **44 pt** | **13 pt (jammed)** | **44 pt** |
| Column width (each) | 217 pt | ~227 pt | **217 pt** (colR_x0 = 351.0, exact) |
| Running header text | Article topic name, 11 pt #7C766F | last section name, 10 pt | **Article topic name, 11 pt #7C766F** |
| Footer separator `|` color | dark #231F20 | gray | **dark #231F20** |
| Article-opener line spacing | ~39.7 pt baseline-to-baseline | overlapping | **~39 pt (no overlap)** |
| Subsection space-below | clear blank row | ~2.5 pt (cramped) | **9.5 pt blank row** |
| Tables | horizontal hairlines only | Typst default 1 pt full grid | **hairlines only, no verticals, no shading** |
| Footer page numbers (integrated) | continuous | restarted at 1 per Article | **continuous 1→91** |

## 2. The two named defects — root cause & fix

### Article-opener overlap
The two 33 pt opener lines ("ARTICLE 3" / "STREETS, ROADS & DRIVEWAYS") collided because the vertical space between them was too small. The subtlety: **Typst sizes an all-caps line box to cap-height (~23 pt at 33 pt), not the full em.** Reasoning in em-boxes undershot; the fix sets each opener block's `below: 16pt`, which reproduces the baseline's ~16 pt ink gap and ~39 pt baseline-to-baseline. Verified across all 9 Article openers.

### Blank row below each subsection header
Level-3 (subsection, e.g., "a. PURPOSE") now uses `block(above: 14pt, below: 9.5pt)`, producing the requested clear blank row before body text resumes (was ~2.5 pt).

## 3. Tables — "serious help"

Pandoc emits a bare `#table`, which inherited Typst's **default heavy 1 pt full-box grid** — the biggest table deviation. The template now globally overrides table styling to the baseline look:

```typst
#set table(
  stroke: (x, y) => (top: 0.5pt + rule_dark, bottom: 0.5pt + rule_dark), // horizontal hairlines
  inset: (x: 5pt, y: 3pt),     // ~15 pt rows
  fill: none,                  // no header/zebra shading
)
#set table.hline(stroke: 0.5pt + rule_dark)
#set table.vline(stroke: none)                       // no vertical borders
#show table.cell.where(y: 0): set text(weight: "medium")  // header row slightly heavier
#show table: set text(size: 8.5pt, stretch: 75%)
```

Result: horizontal hairlines at each row boundary, **no vertical rules, no shading** — matching the baseline (verified on p. 13 district tables and p. 31 Article 3 tables).

## 4. Continuous page numbering across the per-Article build

The integrated CZC is assembled by rendering each Article to its own PDF (to honor per-Article metadata — number, name, tab, opener) and concatenating with `pdfunite`. Each standalone render numbers from 1, so the combined document previously had multiple "page 1"s — unusable for a legal document cited by page.

`build/build-full-czc.sh` now threads a cumulative **page offset** into each render (`-V page-offset=N`); the template footer displays `here().page() + page_offset` and uses the same adjusted value for header/footer/tab edge parity. To keep Typst's automatic `inside`/`outside` (binding) margins aligned with the **combined** document's parity, every offset must be **even** — so the build pads any odd-length Article with a trailing blank page. Side effect (intentional, conventional book layout): each Article opens on a **recto** (odd) page. The final Article is never padded (no trailing blank at document end).

## 5. Files changed

- `style/czc-template.typ` — page geometry (margins 90/44/64/56); `columns(2, gutter: 44pt)`; running header now shows the Article topic name; footer separator color; article-opener spacing fix; level-3 subsection `below: 9.5pt`; full table-styling override; new `page-offset` metadata used for footer number + parity.
- `build/build-full-czc.sh` — sequential render threading an even cumulative `page-offset`; blank-page padding of odd-length Articles (none for the last Article).
- `build/build-article-3.sh` — added the missing `--pdf-engine-opt=--font-path=…/style/fonts` flag (standalone was rendering without Barlow Condensed).
- `style/style-analysis.md` — §1 (geometry), §9 (tables), and the leading/spacing subsection rewritten with measured values; new §13 documenting the v0.4 pass and the continuous-numbering mechanism.

## 6. Page count comparison

| | v0.3-draft | v0.4-draft |
|---|---|---|
| Full integrated CZC | 79 | **91** (incl. 3 blank recto-pads at p. 36, 58, 84) |
| Standalone Article 3 | 7 | **9** |

The increase is correct, not a regression: v0.3's columns were jammed (13 pt gutter) and its margins too small (68 pt), over-packing each page. v0.4 restores the baseline's true text-block width and the generous heading/subsection spacing the baseline actually uses, plus the 3 inter-Article blank pads.

## 7. What's still off (carry forward)

1. **Front matter (cover + TOC).** The integrated draft has none, so its Articles open on **recto** pages, mirroring the baseline's **verso** openers (the baseline's verso openers are an artifact of its 3 front-matter pages). Adding a cover + TOC is the proper fix and will restore verso openers; deferred as separate scope.
2. **District-page banner styling** — colored badge ("D1") + name banner ("RURAL") still render as standard headings, not the baseline's full-width colored block. (Carried from v0.3.)
3. **Use-table status glyphs** `●` `❶` `❷` `✪` — `●` now renders; the enclosed numerals/star still need a symbol fallback font. (Carried from v0.3.)
4. **Cross-section graphics** for the eight Street/Road Types not yet produced.
5. **One dense Article 3 table** bleeds a few points into the outer margin; column-width tuning for wide tables is a candidate for the next pass.

## 8. Verification

- Footer numbers are **continuous 1→91** across the integrated document (0 mismatches vs. physical page; verified `forensic_pagenum.py`-style across the Article 2→3 boundary that previously restarted at "1").
- Article tab and running header sit on the correct **outer** edge per page parity at every Article opener (recto→right, verso→left) and mid-document; tab is 30 × 72 pt at y ≈ 140, matching baseline.
- Article openers show "ARTICLE N" and the name **clearly separated** (no overlap) on all 9 Articles.
- Subsections show a clear blank row below the header.
- Tables render as **horizontal hairlines only**, no vertical borders, no shading (p. 13, p. 31).
- Blank pad pages (36, 58, 84) are truly empty; no trailing blank at document end.

## 9. Reproducing the analysis

Forensic scripts and methodology are recorded in [`style/style-analysis.md`](../../style/style-analysis.md) §12–§13. Re-running them after any template change catches regressions.
