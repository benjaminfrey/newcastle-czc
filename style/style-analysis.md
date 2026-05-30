# CZC Baseline Style Analysis (measured)

Forensic style analysis of [Newcastle Core Zoning Code.pdf](../docs/Newcastle Core Zoning Code.pdf). All values in this document are **measured** from the baseline PDF using `pdffonts`, `pymupdf` text-span extraction, and pixel sampling of rendered pages. Where ranges or "approximately" appear, they reflect actual variation observed in the source.

Companion: [`czc-colors.yml`](czc-colors.yml) (canonical color values) and [`czc-template.typ`](czc-template.typ) (rendering implementation).

---

## 1. Page geometry

Values below are the **precise** figures from the v0.4 forensic pass (averaged across 12 body pages, both parities, via `/tmp/forensic_layout.py`). They supersede the rough first-pass estimates and are the ones now encoded in `czc-template.typ`.

| Property | Measured value | In template |
|---|---|---|
| Page size | 612 × 792 pt (US Letter) | `paper: "us-letter"` |
| **Inside** (binding/gutter) margin — the WIDE side | **90 pt** | `inside: 90pt` |
| **Outside** (tab/fore-edge) margin — the NARROW side | **44 pt** | `outside: 44pt` |
| Top margin (first body line ~65 pt) | **64 pt** | `top: 64pt` |
| Bottom margin (body floor ~736 pt) | **56 pt** | `bottom: 56pt` |
| Column width (each of two) | **217 pt** | (derived: 478 − 44) ÷ 2 |
| Column gutter | **44 pt** | `columns(2, gutter: 44pt)` |
| Text block width | **478 pt** | inside 90 → 568 (recto) |

Column structure on an **odd/recto** page: `90 | colL 90→307 | gutter 44 | colR 351→568 | 44`. Verified in the v0.4 render: `colR_x0 = 351.0` exactly. Typst's named `inside`/`outside` margins flip automatically by page parity, reproducing the book-spread asymmetry.

The page is asymmetric: the side that hosts the rotated **Article tab** has a narrow 44 pt outer margin where the tab sits; the opposite (binding) side has a wide 90 pt margin. Verso (even-numbered) pages have the tab on the **left**; recto (odd-numbered) pages have the tab on the **right**.

> **Earlier rough estimates (superseded):** first-pass measurements read margins as ~45/~90 pt and the gutter as ~18 pt with ~225 pt columns. Those were imprecise — the real gutter is **44 pt** (the columns were rendering jammed together until this was corrected) and the wide/narrow margins are **90 / 44 pt**.

---

## 2. Embedded fonts

`pdffonts` reports the following font families embedded in the PDF:

| Family | Weights used | Where |
|---|---|---|
| **BentonSansCond** *(commercial; primary)* | Light, Book, Regular, Bold | All body text, all headings, footers, headers, district badges |
| **BentonSans** *(commercial; non-condensed)* | Regular | Only on district name banners (e.g., "RURAL", "TOWN CENTER") — a slightly wider display variant |
| BentonSansComp-Light-SC7 | Light, small caps | Sparse — appears on Article 5 design-component tables (likely small-caps captions like "FRONT", "SIDE", "REAR") |
| TrebuchetMS | Regular, Bold, Italic | Some figure/exhibit annotations only |
| ArialMT | Regular | Fallback / sparse |

**Benton Sans Condensed** (Font Bureau / Cyrus Highsmith) is a commercial font. The closest free metric/visual match used in this project is **Barlow Condensed** (Jeremy Tribby, SIL OFL, available on Google Fonts and via `brew install --cask font-barlow-condensed`). Where the baseline uses BentonSans (non-condensed), we substitute regular **Barlow**.

---

## 3. Typography — measured per element

Every entry below was sampled from a real text span in the baseline PDF via `pymupdf`. Font names are the embedded names; in this project they map to Barlow Condensed equivalents.

| Element | Font | Size | Weight | Color | Notes |
|---|---|---|---|---|---|
| Body text | BentonSansCond-Light | **8.5 pt** | Light | **#231F20** | Near-black warm gray. Sample n=78 on a typical page. |
| Body text — alt (some spans) | BentonSansCond-Light | 8.5 pt | Light | **#000000** | Pure black appears on some spans, possibly from a different style. Treat as visually equivalent to #231F20. |
| Section heading marker + name ("1. CORE ZONING CODE") | BentonSansCond-Bold | **14 pt** | Bold | **#367AAC** | Uppercase. Article blue. |
| Subsection heading marker + name ("a. PURPOSE") | BentonSansCond-Bold | **11 pt** | Bold | **#7C766F** | **Lowercase letter marker** + uppercase name in the baseline. Muted gray-brown. *This is the single most visible deviation from common municipal-code conventions: the baseline's subsections use lowercase, not uppercase, letters.* **Note (v0.4.2):** the draft template now deliberately renders this marker **UPPERCASE** ("A. PURPOSE") — an intentional deviation from the baseline; see §15. The baseline measurement in this row is unchanged. |
| Article display "ARTICLE N" (on opener) | BentonSansCond-Book | **33 pt** | Book (a hair lighter than Bold) | **#367AAC** | Uppercase. |
| Article display "GENERAL STANDARDS" etc. | BentonSansCond-Bold | **33 pt** | Bold | **#367AAC** | Uppercase. Same line height as the "ARTICLE N" above it. |
| Article tab text ("ARTICLE N") | BentonSansCond-Bold | **14 pt** | Bold | **#FFFFFF** | White text, rotated 90° CCW, on a gray (#BFBFBF) background block. |
| Header band topic ("GENERAL STANDARDS") | BentonSansCond-Bold | **11 pt** | Bold | **#7C766F** | Uppercase. Same color as subsection markers. |
| Header band right-side topic (district pages: "Core Zoning Districts") | BentonSansCond-Bold | **10 pt** | Bold | #7C766F | Mixed case. |
| Footer wordmark ("Newcastle Core Zoning Code") | BentonSansCond-Bold | **10 pt** | Bold | **#367AAC** | Mixed case. |
| Footer page number | BentonSansCond-Bold | 10 pt | Bold | **#231F20** | |
| Footer date ("Amended: March 24, 2025") | BentonSansCond-Bold | 10 pt | Bold | #367AAC | |
| District badge ("D1") | BentonSansCond-Bold | **9 pt** *(verify; could be larger)* | Bold | varies | White on dark district colors, dark on light district colors |
| District name banner ("RURAL", "TOWN CENTER") | **BentonSans-Regular** *(not condensed)* | **19 pt** | Regular | #231F20 (dark text) or #FFFFFF (light text) | Color flips depending on district-color luminance |
| Description / Purpose / Lot Dimensions headers on district pages | BentonSansCond-Bold | **9 pt** | Bold | **#7C766F** | Uppercase. |
| Architectural Components column labels (Article 5: "FRONT", "SIDE", "REAR") | BentonSansComp-Light-SC7 | 7.8 pt | Light SC | #7C766F | Small caps. |

### Leading and spacing

Baseline measurements and the matching Typst settings now in `czc-template.typ`:

| Spacing | Baseline (measured) | Template setting | Rendered result |
|---|---|---|---|
| Body line advance | ~11.0 pt baseline-to-baseline (leading ≈ 1.29 × 8.5 pt) | `par(leading: 0.57em)` | ~10.8 pt (≈0.2 pt tight, acceptable) |
| Paragraph / item gap | ~15.5 pt baseline-to-baseline | `par(spacing: 0.78em)` | — |
| Subsection heading: space **below** | clear blank row before body resumes | `block(below: 9.5pt)` on level-3 | the user-requested "blank row below each sub-section header" |
| Section heading: space above/below | generous break, **no divider, no blank row below** (corrected v0.4.1 — the divider is an opener element, see §6) | `block(above: 13pt, below: 4pt)` on level-2 | section name sits directly above body text |
| **Article opener: "ARTICLE N" → name** baseline-to-baseline | **~39.7 pt** | two 33 pt blocks, each `below: 16pt` | **39.1 pt** (verified across all 9 articles) |

> **Article-opener overlap — root cause & fix.** The original template stacked the two 33 pt opener lines with too little vertical space, so "ARTICLE 3" and "STREETS, ROADS & DRIVEWAYS" collided. The subtlety: Typst sizes an **all-caps** line box to *cap-height* (~23 pt at 33 pt), **not** the full em. So the visually-relevant figure is the ~16 pt ink gap between the ARTICLE baseline and the name's cap-top — setting each opener block's `below: 16pt` yields the baseline's ~39 pt baseline-to-baseline. An earlier attempt that reasoned in em-boxes produced only ~24.6 pt and still looked cramped.

---

## 4. Color palette (pixel-sampled)

### Primary system colors

| Name | Hex | Sampled from |
|---|---|---|
| **Article blue** | **#367AAC** | "1. CORE ZONING CODE" (Art. 1 p. 4), wordmark, divider stroke |
| **Body dark** | **#231F20** | Body text spans |
| **Subsection gray** (warm) | **#7C766F** | Subsection markers, header band, district descriptors |
| **Tab gray** | **#BFBFBF** | Article tab background fill (e.g., D1 p. 12 drawing #0) |
| White (on colored backgrounds) | **#FFFFFF** | Tab text; banner text on dark district colors |
| Pure black | **#000000** | A subset of body spans (alternates with #231F20) |

### District badge & banner colors (pixel-sampled fills)

| District | Hex | Visual |
|---|---|---|
| D1 Rural | **#CDE3CC** | Pale mint green |
| D2 Neighborhood Residential | **#F3F2AE** | Pale yellow |
| D3 Neighborhood Business | **#B4A27A** | Tan / khaki |
| D4 Village Residential | **#EDE832** | Bright lemon yellow |
| D5 Village Business | **#BBACD4** | Lavender |
| D6 Town Center | **#502971** | Deep eggplant purple |
| SD-Historic | **#108C89** | Dark teal |
| SD-Conservation | **#3CAC48** | Medium green |
| SD-Highway Commercial | **#F2AB57** | Orange |
| SD-Rural Highway | **#716C53** | Warm olive-brown |
| SD-Campus | **#7ED0EE** | Light sky blue |
| SD-Marine | **#1C66B0** | Strong nautical blue |
| SD-Fabrication | **#A7A9AB** | Cool medium gray |
| SD-Civic | *(no district page; treated by enclosing District) * | — |

Each district page renders the banner as a single full-width colored rectangle at the top of the body area (about 42 pt tall, x = 99 → 522 pt on a verso page), with a separate badge block at left (also ~42 × 42 pt, holding the "D1"/"D6" code).

---

## 5. Article tab (margin element)

Measured on page 12 (D1, verso):

| Property | Value |
|---|---|
| Rectangle | x=0 → 30.2 pt, y=139.5 → 211.5 pt (so 30.2 × 72 pt) |
| Background fill | **#BFBFBF** (gray, uniform across districts and articles) |
| Text | "ARTICLE 2", rotated 90° CCW, 14 pt BentonSansCond-Bold #FFFFFF |
| Side (parity) | Verso (even pages): left; Recto (odd pages): right |

The tab is **the same gray on every page**, regardless of district or article. This contradicts an earlier assumption that tabs are district-color-coded; they are not.

---

## 6. Article-opener divider (under the opener title only — NOT under section headings)

**Corrected v0.4.1.** Earlier passes mislabeled this as a *section-heading* divider and attached it to every level-2 ("1. NAME") heading. Re-measurement shows the square-endpoint divider appears **once per Article**, tight under the opener title ("ARTICLE N" / NAME), and **never** under mid-article section headings (verified: the baseline's "3. DISTRICT MAP" and other mid-Article section headings have no rule below them). The y = ~149.4 pt rule originally measured "on page 4" is the *Article 1 opener* divider — it sits just above the first section "1. CORE ZONING CODE", which is what created the confusion. It is an opener element (see §7), so the template now draws it in `article_opener()` and the level-2 heading rule draws nothing.

Measured on page 4 (the Article 1 opener):

| Property | Value |
|---|---|
| Horizontal rule | x = 49.5 → 517.5 pt (full body width), y = ~149.4 pt |
| Stroke color | #367AAC (Article blue) |
| Stroke width | ~0.5–0.75 pt (thin) |
| Endpoint squares | 4 × 4 pt filled #367AAC at each end of the rule, vertically centered on the rule's y-position |
| Name-baseline → divider | ~10.6 pt |
| Divider → first section heading | ~14.4 pt |

---

## 7. Article opener layout

Important: the article opener is **NOT a separate full-height title page**. Title + first section share the same page:

1. Top: header band (`GENERAL STANDARDS` topic, gray small caps, with thin gray rule)
2. Then "ARTICLE 1" at ~33 pt #367AAC Book
3. Then "GENERAL STANDARDS" at ~33 pt #367AAC Bold
4. Then a thin blue divider with 4×4 endpoint squares
5. Then "1. CORE ZONING CODE" section heading in column 1, body content flowing in both columns

So the article display heading occupies roughly the top third of the page; the body starts directly below. The opener does *not* leave the rest of the page blank.

---

## 8. Heading numbering hierarchy (with marker case)

Confirmed by sampling text spans on page 5:

```
ARTICLE 1                                  ← Article opener (33 pt blue, Book + Bold)
1. CORE ZONING CODE                        ← Numbered Section (14 pt blue Bold, UPPERCASE name)
   a. PURPOSE                              ← Subsection (11 pt gray Bold, LOWERCASE letter marker, UPPERCASE name)
      1. To implement the Comp Plan.       ← Numbered Item (8.5 pt body, sentence case)
         a. Allowance of the waiver…       ← Sub-item (8.5 pt body, lowercase letter)
            i. (no examples found yet)     ← Sub-sub-item (presumed Roman lowercase)
```

The convention "lowercase a./b./c. for subsections" is a baseline reality. Source markdown is authored with lowercase markers (`### a. PURPOSE`), preserving the baseline's authored form.

> **v0.4.2 rendering deviation.** As of v0.4.2 the template **force-uppercases** the level-3 marker at render time (`#upper(h.body)`), so the rendered output reads "A. PURPOSE" even though the source stays `### a. PURPOSE`. This is a deliberate, informed deviation from the baseline (see §15) — the source markdown is unchanged, so reverting is a one-line template edit.

---

## 9. Tables

Measured across representative table pages (p. 13 district tables, p. 44 site standards, p. 48 building grid, p. 82 administration) via `/tmp/forensic_table_geom.py`:

| Property | Measured | Template setting |
|---|---|---|
| Cell borders | **horizontal hairlines only** at each row boundary; ~0.25–0.5 pt | `stroke: (x,y) => (top: 0.5pt + rule_dark, bottom: 0.5pt + rule_dark)` |
| Vertical borders | **none** | absence of `left`/`right` keys + `table.vline(stroke: none)` |
| Rule color | **#231F20** (near-black) | `rule_dark` |
| Row height | ~15 pt at 8.5 pt text | `inset: (x: 5pt, y: 3pt)` |
| Header/zebra shading | **none** | `fill: none` |
| Header row weight | slightly heavier than Light body | `table.cell.where(y: 0): set text(weight: "medium")` |
| Body text | 8.5 pt condensed, matching surrounding body | `show table: set text(size: 8.5pt, stretch: 75%)` |

**Table-styling rewrite (v0.4).** Pandoc emits a bare `#table` with no stroke spec, so it inherited Typst's default **heavy 1 pt full-box grid** — the single biggest table-rendering deviation. The global `#set table(...)` / `#set table.hline(...)` / `#set table.vline(stroke: none)` overrides above convert every table to the baseline's horizontal-hairline-only look with no vertical rules and no shading. Verified on the v0.4 render (p. 13, p. 31).

District use-tables use the same hairline style with status glyphs (§10) in a narrow right column.

---

## 10. Specific Unicode glyphs needed in body

The use tables use four custom glyphs:
- `●` Use Permit Required (CEO)
- `❶` Residential Companion Permit Required (CEO)
- `❷` Special Permit Required (Planning Board)
- `✪` Expanded Use Permit Required (Planning Board)

These render correctly in BentonSansCond (the baseline). They do **not** render in Helvetica Neue or in Barlow Condensed by default; a fallback font like DejaVu Sans, Noto Sans Symbols 2, or Symbola will be needed for these specific code points.

---

## 11. Implementation deltas (v0.2.1-draft → target)

What our current rendering gets wrong and how to fix:

| Deviation | Current | Target | Action |
|---|---|---|---|
| Body font | Helvetica Neue | Barlow Condensed Light, 8.5 pt | Install Barlow Condensed; set body to "Barlow Condensed Light" 8.5 pt |
| Article blue hex | #2E96CC | #367AAC | Update template + colors.yml |
| Body dark hex | #333333 | #231F20 | Update template + colors.yml |
| Subsection gray | #2079B0 (was using "section_blue_dark") | #7C766F | Update; rename palette key |
| Tab color | Article blue | #BFBFBF (gray) | Update tab function |
| Tab side | Always right | Left on verso, right on recto | Make tab side parity-aware |
| Subsection markers | Uppercase A./B. | Lowercase a./b. | Sed across all source files |
| Article opener layout | Full page, only opener | Title + first section share page | Restructure article_opener function |
| Section heading size | 18 pt | 14 pt | Update show rule |
| Subsection heading size | 10 pt | 11 pt | Update show rule |
| Body size | 9 pt | 8.5 pt | Update text default |
| District colors | Estimated | Measured (per Section 4 above) | Update colors.yml |
| Status glyphs | Render as `?` | Need a fallback font with these glyphs | Add fallback font to template |

This is the work list for v0.3-draft. **All items above were applied in v0.3; v0.4 then re-measured and corrected the geometry — see §13.**

---

## 12. Methodology

Measurements were obtained with the following tools (all reproducible):

```sh
# Embedded font inventory
pdffonts docs/Newcastle\ Core\ Zoning\ Code.pdf

# Per-span typography
python3 -c "import fitz; doc=fitz.open('docs/...'); …"
# See /tmp/analyze_pdf.py and /tmp/analyze_pdf_2.py

# Pixel sampling of rendered pages
# See /tmp/sample_colors.py and /tmp/sample_tab.py
```

All sampled PNGs were rendered at 144 DPI from the baseline PDF via `pdftoppm` or `pymupdf.get_pixmap(dpi=144)`. Color values reported are the modal pixel in a 5×5 region around the target point. Drawing fills were read from PyMuPDF's `page.get_drawings()` API.

---

## 13. v0.4 forensic pass — corrections applied

This pass re-measured everything the v0.3 render still got wrong and corrected it. The reusable measurement scripts are `/tmp/forensic_layout.py` (margins/columns/header/footer), `/tmp/forensic_tables.py` + `/tmp/forensic_table_geom.py` (table geometry), and `/tmp/forensic_pagenum.py` (footer continuity & opener parity).

| Fix | Before (v0.3) | After (v0.4, measured) |
|---|---|---|
| Inside / outside margins | 68 / 45 pt | **90 / 44 pt** |
| Column gutter | 13 pt (columns jammed) | **44 pt** (colR_x0 = 351.0, exact) |
| Running header | last level-2 section name | **Article topic name, 11 pt #7C766F**, outer edge per parity |
| Footer separator color | gray | **dark (#231F20)**, grouped with page number |
| Article-opener overlap | "ARTICLE N" / name collided | **39.1 pt baseline-to-baseline** (each block `below: 16pt`) |
| Subsection spacing below | ~2.5 pt (cramped) | **9.5 pt** — a clear blank row |
| Tables | Typst default 1 pt full-box grid | **horizontal hairlines only, no verticals, no shading** |
| Footer page numbers (integrated build) | restarted at 1 every Article | **continuous 1→91** across the document |

### Continuous page numbering across a per-Article build

The full-CZC deliverable is assembled by rendering each Article to its own PDF (so per-Article metadata — number, name, tab, opener — is honored) and concatenating with `pdfunite`. Each standalone render naturally numbers from 1, so without intervention the combined document had multiple "page 1"s — unusable for a legal document cited by page.

The build (`build/build-full-czc.sh`) threads a cumulative **page offset** into each render via `-V page-offset=N`; the template displays `here().page() + page_offset` in the footer (and uses the same adjusted value for header/footer/tab edge parity). To keep Typst's automatic `inside`/`outside` (binding) margins aligned to the **combined** document's parity, every offset must be **even** — so the build pads any odd-length Article with a trailing blank page. Side effect (intentional, conventional): each Article opens on a **recto** (odd) page.

> **Known deviation from baseline parity.** The baseline opens each Article on a **verso** page because it carries three front-matter pages (cover + 2-page TOC) that the integrated draft does not yet include. The draft therefore mirrors the baseline's tab/binding side on opener pages. Adding real front matter (cover + TOC) is the proper future fix and will restore verso openers; it is deferred as separate scope.

---

## 14. v0.4.1 corrections — divider placement & wide-table layout

Two review-driven fixes on top of v0.4.

**Divider relocated to the Article opener (see §6).** v0.4 still drew the square-endpoint blue divider under *every* level-2 section heading, with a blank row above it — neither matches the baseline. The divider is now drawn once per Article inside `article_opener()`, tight under the opener title, and the level-2 heading rule draws nothing (no rule, no blank row; `below: 4pt`). Measured opener gaps reproduced: name-baseline → divider ≈ **10.4 pt** (target 10.6), divider → first section ≈ **11.8 pt** (target 14.4; the remainder is absorbed at the single-column-opener → two-column-body boundary and reads correctly). Verified on all 9 Article openers in the integrated build (pages 1, 3, 27, 37, 43, 51, 59, 69, 85 — every one carries the divider; no section heading does).

**Table 3.1 promoted to a full-width float.** The 9-column Street/Road Type Standards matrix is unreadable inside a single 217 pt column. It is now authored directly in Typst in the source (a ```` ```{=typst} ```` raw block) and placed with `#place(top, scope: "parent", float: true, block(width: 100%)[…])`, which spans both body columns; body text flows in two columns above/below it. A local `#show table: set text(size: 8pt)` and `inset: (x: 3pt)` keep the "per MaineDOT" cells on one line. Verified: the table's widest horizontal hairline measures **478.5 pt** (full text block) vs. ~217 pt for an in-column table, and it appears exactly once (integrated p. 29). The global hairline table styling (§9) still applies to it.

> **Page-count note.** The integrated document is now **90 pages** (v0.4 was 91). This is not a regression: the divider relocation and the Table 3.1 float shift each Article's content flow, which changes *which* Articles render to an odd page length and therefore which receive an even-keeping blank pad. v0.4.1 has 4 blank pads (verso pages 36, 58, 68, 84); footers remain **continuous 1→90** and every Article still opens on a recto page.

---

## 15. v0.4.2 corrections — subsection-marker case, table ordering & caption-locking

Three review-driven fixes on top of v0.4.1. None change regulatory text; all three are layout/typography.

### Subsection marker forced UPPERCASE (deliberate deviation)

The baseline renders subsection markers in **lowercase** ("a. PURPOSE") — re-confirmed in this pass: **129 lowercase / 0 uppercase** markers across all 110 baseline pages. Per an explicit styling decision the draft now renders them **UPPERCASE** ("A. PURPOSE"). The level-3 heading show-rule in `czc-template.typ` changed from `#h.body` to `#upper(h.body)`; the subsection name is already all-caps in the source, so `upper()` only flips the single marker letter. The source markdown is untouched (`### a. PURPOSE`), so this is reversible with a one-line edit. See the notes in §3 and §8.

> This is the one place the draft *intentionally* diverges from a measured baseline value. It is recorded here so a future reader does not "correct" it back to lowercase thinking it is a regression. Verified in the v0.4.2 render: **277 uppercase / 0 lowercase** markers in the integrated build, **44 / 0** in the standalone Article 3 (samples: "A. PURPOSE", "B. APPLICABILITY", "C. AUTHORITY").

### Table 3.1 ordering — bottom-float after its section heading

v0.4.1 placed the full-width Table 3.1 with `#place(top, scope: "parent", float: true, …)`. A **top** float migrates to the top of its anchor page — *above* any source-earlier content on that page — so the table read as if it preceded its own "3. TYPE STANDARDS TABLE" heading. Changing the placement edge to **`bottom`** sinks the float below the heading + intro, so the table now follows Section 3 as intended. The float still spans the full **478.5 pt** text block (verified) and still appears exactly once (integrated p. 29).

> **Why an edge change and not a page break.** A clean "Section 3 heading → table → Section 4" isolation would want a page/column break, but `#pagebreak()` is **illegal inside the `columns()` container** Typst error: *"pagebreaks are not allowed inside of containers"*, which the whole two-column body is). So float placement is steered by **edge** (`top`/`bottom`), not by forcing a page. Honest caveat: with a bottom float, Section 4's body still flows in the two columns *above* the table on the same page; the table is not visually fenced between the two sections. Strict fencing would cost ~half a page of whitespace and was not requested.

### Caption-locking for Tables 3.2, 3.3, 3.4

When a table wrapped to the next column, its "TABLE 3.x …" caption could strand at the bottom of the previous column, detached from its grid. Fix: each of these three tables was re-authored from a Markdown pipe table into a raw Typst `#block(breakable: false)[ caption + #table(…) ]`. `breakable: false` forbids the block from splitting across a column/page boundary, so the caption and grid always travel together. These tables are short (≤14 rows) and fit comfortably within one column, so locking them costs no readability. The global hairline table styling (§9) still applies; bold sub-header rows in Table 3.3 use `*…*` span emphasis. Verified: captions sit immediately above their grids on the same page/column (standalone pp. 4, 6, 7).

### Known defect identified this pass — DEFERRED: stale table numbers from renumbering

While locking captions, a pre-existing **table-numbering collision** surfaced, introduced back when Articles 3–8 were renumbered to 4–9 (v0.2) but their *table captions and in-text "see Table X.Y" references were not*. The old article-number prefix is stale in every renumbered Article:

| Article (new no.) | Was | Table captions currently read | Should read |
|---|---|---|---|
| Art. 4 Site Standards | 3 | "TABLE 3.1 SCREENING FORMULA", "TABLE 3.1 SITE LUMENS" (also collide with the new Art. 3 tables) | 4.1, 4.2, … |
| Art. 5 Building Standards | 4 | "TABLE 4.1" – "TABLE 4.7" | 5.1 – 5.7 |
| Art. 6 Design Standards | 5 | "TABLE 5.1" – "TABLE 5.21" | 6.1 – 6.21 |
| Art. 8 Administration | 7 | "TABLE 7.1" | 8.1 |

Fixing this requires renumbering ~35 captions **plus** every in-text cross-reference that cites them, and a verification sweep. It is **out of scope for v0.4.2** (deferred to its own pass by explicit decision) and recorded here and in the v0.4.2 Summary of Changes as a known issue. The new Article 3's own tables (3.1–3.4) are correct.

> **Page-count note.** Integrated remains **90 pages**; standalone Article 3 remains **9 pages**. The case change and the table edits do not alter pagination materially; the 4 blank pads (verso pages 36, 58, 68, 84) and continuous 1→90 footers are unchanged from v0.4.1.

## 16. v0.4.3 — two new Street/Road Types & the Table 3.1 split (content + layout)

Unlike §§13–15 (pure layout passes), v0.4.3 is primarily a **regulatory-content** change: the typology grew from **8 Types to 10**. Full rationale and the calibration values live in `releases/v0.4.3-draft/Summary of Changes v0.4.3-draft.md`; recorded here are only the parts that touch rendering, the template, and pagination.

### Typology change (what the renderer now has to lay out)

- **S-4 "Lane / Alley" was split into two Types:** **S-4 Lane** (a narrow *fronting* slow-movement street — buildings front on it; it "punches in" to mid-block land) and **S-5 Alley** (the *service* rear-lane, buildings do not front on it). The old combined Type's standards moved to S-5; S-4 is new.
- **New R-3 "Rural Lane"** (rural yield roadway, ADT ≤ 400, two-way single-lane where ≤ 15 ft with passing pull-outs ≤ 300 ft; conforms historic two-rod / 33 ft ways) inserted between R-2 Rural Road and the highway Types.
- **Highway Types shifted down one number** to make room: old R-3 Highway Commercial → **R-4**, old R-4 Rural Highway → **R-5**. Every in-text code reference and the §2 description letters (now **d–n**) were renumbered to match.
- **Held findings from earlier research applied in the same pass:** S-1 Main Street ROW widened to **66–80 ft**; the "cartway" row relabelled **"Traveled way (moving lanes)"** with a separate **"On-street parking lane (each side)"** row, so moving-lane width and parking width are no longer conflated.

### Table 3.1 → split into 3.1a + 3.1b (the layout-relevant fix)

Ten Types will not fit one readable full-width matrix, so the single Table 3.1 was split by family:

- **TABLE 3.1a STREET TYPE STANDARDS** — 6 columns (Standard + S-1…S-5).
- **TABLE 3.1b ROAD TYPE STANDARDS** — 6 columns (Standard + R-1…R-5).

Both are raw-Typst **full-width bottom floats** (`#place(bottom, scope: "parent", float: true, block(width: 100%)[…])`, the §14/§15 pattern), `columns: (1.7fr, 1fr, 1fr, 1fr, 1fr, 1fr)`, body text dropped to **8 pt** with `inset: (x: 3pt, y: 3pt)` so six columns fit the 478.5 pt block. Literal `@` in lane specs (e.g. `2@10–11`) is escaped `\@` in the Markdown so Pandoc does not treat it as a Typst code sigil. **Verified in the v0.4.3 render:** 3.1a on integrated **p. 29**, 3.1b on **p. 30**, all columns present (incl. the new R-3 Rural Lane), no `\@` escape leak, `@` glyph renders.

> **Why split rather than rotate or shrink one wide table.** A 10-data-column matrix at a legible size overruns the full-width block; landscape/rotated tables break the two-column reading flow and the running header/tab geometry. Splitting by family keeps each table at the same 8 pt as the body and keeps **Tables 3.2/3.3/3.4 numbers unchanged**, so none of the "per Table 3.2" / "per Table 3.3" cross-references had to move.

### Cross-file ripple

The renumber/split touched three source files: `article-03-streets-roads-driveways.md` (typology, descriptions, all five split-table-and-§ references), `article-09-definitions.md` (new **Lane (S-4)**, **Alley (S-5)**, **Rural Lane (R-3)**, **On-Street Parking Lane** entries; **Rural Road (R-2)** softened; highway defs renumbered; **Thoroughfare** now "ten … Types (S-1 through S-5 and R-1 through R-5)"), and `article-04-site-standards.md` (parking-access reference now "Lane or Alley (Types S-4 or S-5)"). `article-02` and the other renumbered Articles needed **no** change (they reference Special-District *names*, not Type codes).

> **Page-count note.** Integrated is now **91 pages** (was 90); standalone Article 3 holds at **9 pages**. The +1 is **Article 9 (Definitions)** growing 6 → 7 pages from the four new/expanded entries — *not* Article 3, whose two new Types and split table still fit its existing 9-page (+1 pad) block. The 4 blank pads are unchanged at verso pages **36, 58, 68, 84**; footers remain continuous **1 → 91**; Articles 1–8 paginate identically to v0.4.2.

> **Deferred items carried forward (unchanged from §15 except where noted).** Stale renumbered-Article table numbers (Art. 4 reads "3.x", etc.) — still deferred; the new Art. 3 tables 3.1a/3.1b/3.2/3.3/3.4 are correct. Front matter (cover + TOC). District-page banner styling. Status-glyph fallback font (`❶ ❷ ✪`). **Cross-section graphics now number 10, not 8** (one per Type) — still unproduced, and slightly more relevant now that two Types are new. R-2 12 % grade vs. RDEO's 10 % still flagged for a future reconciliation.
