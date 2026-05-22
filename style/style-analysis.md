# CZC Baseline Style Analysis

Reverse-engineered formatting of [Newcastle Core Zoning Code.pdf](../docs/Newcastle Core Zoning Code.pdf) and [Newcastle Roads Driveways and Entrances Ordinance.pdf](../docs/Newcastle Roads Driveways and Entrances Ordinance.pdf). The two documents share an identical visual system. All draft work must reproduce this look closely enough that a reader does not perceive new content as appended or separately styled.

The values below are working estimates derived from visual inspection. Items marked **(TODO: verify by pixel sampling)** should be refined by extracting exact pixels from the baseline PDF before the v0.1 release.

---

## 1. Page geometry

| Property | Value |
|---|---|
| Page size | US Letter, 8.5″ × 11″ portrait |
| Top margin | ≈ 0.75″ (with header band inside) |
| Bottom margin | ≈ 0.75″ (with footer band inside) |
| Inside (binding) margin | ≈ 0.75″ |
| Outside margin | ≈ 1.0″ (wider, to host the vertical Article tab) |
| Columns | Two columns, full body region |
| Column gutter | ≈ 0.25″ |
| Header band height | ≈ 0.4″ — contains topic name in muted small caps, right- or left-aligned to outside edge |
| Footer band height | ≈ 0.4″ — contains date and page identifier |

Front matter (cover, table of contents) and some district pages break from the two-column rule. The District Map exhibits (Art. 1 Exhibits 1.1–1.4) are full-page landscape-style images on portrait pages.

## 2. Typography

| Element | Font family (working) | Size | Weight | Style | Color |
|---|---|---|---|---|---|
| Body text | Source Sans 3 (humanist sans) | 9 pt | Regular | — | `#333333` |
| Body emphasis | Source Sans 3 | 9 pt | Semibold | — | `#333333` |
| Article display (cover & opener) | Source Sans 3 | 48–60 pt | Bold | UPPERCASE | Article blue `#2E96CC` |
| Section heading ("1. CORE ZONING CODE") | Source Sans 3 | 18 pt | Bold | UPPERCASE | Article blue `#2E96CC` |
| Subsection heading ("A. PURPOSE") | Source Sans 3 | 10 pt | Bold | UPPERCASE | Section blue dark `#2079B0` |
| Numbered item (1., 2.) | Source Sans 3 | 9 pt | Regular | — | `#333333` |
| Lettered sub-item (a., b.) | Source Sans 3 | 9 pt | Regular | — | `#333333` (indented) |
| Roman sub-sub (i., ii.) | Source Sans 3 | 9 pt | Regular | — | `#333333` (further indented) |
| Table caption ("TABLE 2.1 SIGHT DISTANCE") | Source Sans 3 | 8 pt | Semibold | UPPERCASE | `#333333` |
| Table header row | Source Sans 3 | 8 pt | Semibold | UPPERCASE | `#333333` on tinted background |
| Header band (topic name) | Source Sans 3 | 8 pt | Regular | UPPERCASE letter-spaced | `#777777` muted gray |
| Footer | Source Sans 3 | 8 pt | Regular | — | `#666666` muted gray; "Newcastle Core Zoning Code" in Article blue |
| Article tab (vertical) | Source Sans 3 | 11 pt | Semibold | UPPERCASE, rotated 90° CCW | White on Article color block |

**Font selection:** the baseline body font reads as a clean humanist sans. **Source Sans 3** (open-source, OFL) is the working default — visually very close to what appears in the CZC and freely embeddable. If a closer match is desired after pixel comparison, candidates include Open Sans, Noto Sans, or proprietary fonts (Calibri, Frutiger, Myriad Pro).

**Body line height (leading):** ≈ 12 pt for 9 pt body — generous for legibility in narrow columns.

**Body alignment:** body text is **left-aligned** (not justified), with hanging indents on numbered items.

## 3. Color palette

All hex values are working estimates **(TODO: verify by pixel sampling against the baseline PDF)**. The canonical encoding is in [czc-colors.yml](czc-colors.yml).

### Primary system colors

| Name | Hex | Usage |
|---|---|---|
| Article blue | `#2E96CC` | Article display headings, section headings, section divider lines, "Newcastle Core Zoning Code" wordmark |
| Section blue dark | `#2079B0` | Subsection headings, deep accents |
| Body dark | `#333333` | Body text |
| Footer gray | `#666666` | Footer text |
| Header gray | `#777777` | Header band text |
| Table tint | `#E8E8E8` | Table header row background (non-district tables) |
| Page background | `#FFFFFF` | All pages |

### District badge/banner colors (Article 2 D1–D6 + SD pages)

| District | Hex (working) | Visual character |
|---|---|---|
| D1 Rural | `#B5C58F` | Olive / sage green |
| D2 Neighborhood Residential | `#F5E58A` | Pale yellow |
| D3 Neighborhood Business | `#C9A87C` | Tan / light brown |
| D4 Village Residential | `#F5D540` | Brighter saturated yellow |
| D5 Village Business | `#C0A4D2` | Light lavender purple |
| D6 Town Center | `#5C2D74` | Deep / dark purple |
| SD-Historic | `#6FB5B5` | Teal |
| SD-Conservation | `#4B8B3A` | Forest green |
| SD-Highway Commercial | `#F08A30` | Orange |
| SD-Rural Highway | `#7A6536` | Olive-brown |
| SD-Campus | `#69C2D6` | Light sky blue |
| SD-Marine | `#244D8F` | Deep nautical blue |
| SD-Fabrication | `#939393` | Medium gray |
| SD-Civic | `#803535` | Brick red / maroon |

The district color appears in three places per district page: (a) the colored code badge ("D1") top-left, (b) the colored name banner ("RURAL") spanning the rest of the row, and (c) the rotated Article tab in the outer margin.

### Proposed Type colors (new — for Article 3)

To extend the system to the new Street/Road Types without clashing with district colors, use a constrained dual-family palette: warmer tones for the **Street** family (S-1…S-4), cooler tones for the **Road** family (R-1…R-4), neutral for **Driveway**.

| Type | Hex (proposed) | Visual character |
|---|---|---|
| S-1 Main Street | `#A33C3C` | Deep red — strongest urban marker |
| S-2 Village Street | `#C67343` | Burnt orange |
| S-3 Neighborhood Street | `#D9A05B` | Warm tan |
| S-4 Lane / Alley | `#9C8466` | Muted brown |
| R-1 Connector Road | `#4F8AAB` | Slate blue |
| R-2 Rural Road | `#3F6D5C` | Forest teal |
| R-3 Highway Commercial | `#7E5C8C` | Muted plum |
| R-4 Rural Highway | `#5A6E48` | Olive |
| D Driveway | `#888888` | Neutral gray |

These are **proposed only** and should be reviewed by the user before locking in. The constraint: every Type color must be distinguishable from every District color when adjacent on the District Map.

## 4. Heading hierarchy and section structure

Newcastle's CZC uses a six-level hierarchy:

```
ARTICLE 1                              ← Article opener (big blue display)
1. CORE ZONING CODE                    ← Numbered Section heading
   A. PURPOSE                          ← Lettered Subsection heading
      1. To implement the Comp Plan.   ← Numbered Item (body)
         a. ...                        ← Lettered sub-item
            i. ...                     ← Roman sub-sub-item
```

Numbering style:
- Items use a period after the marker: `1.` `2.` `A.` `a.` `i.`
- Item text is left-aligned with a hanging indent so subsequent lines align with the first character of the item text, not the marker
- No bullet glyphs — all items are numbered/lettered

## 5. Section divider

Under each numbered Section heading ("1. CORE ZONING CODE"), there is a thin horizontal rule in Article blue, spanning the column, with small filled-square endpoints (▪) at left and right ends of the rule:

```
1. CORE ZONING CODE
▪━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▪
```

The rule sits a few points below the heading text. The endpoints are subtle but unmistakable when rendered.

## 6. Article tab (vertical margin element)

Each page within an Article displays a vertical "ARTICLE N" label in the outer margin.

- Position: outer margin (right margin on right pages, left margin on left pages), aligned vertically center or slightly above center
- Orientation: rotated 90° counter-clockwise (reads bottom-to-top)
- Background: a solid block in the Article color (Article blue for Articles 1–9; district color on Article 2 district pages; type color on new Article 3 type pages)
- Text: white, UPPERCASE, semibold, e.g., "ARTICLE 1"
- Block dimensions: ~0.25" wide × ~1.5" tall

On Article 2 (District Standards) pages, the tab is **color-coded by district**, not by Article — D1 pages have a green tab, D6 pages have a purple tab, etc. The Article number ("ARTICLE 2") appears on the tab regardless of district color. Apply the same convention to new Article 3 type pages.

## 7. Header band

The header band runs across the top of the page, below the top margin:

- Left page (verso): outer-aligned (left), small-caps muted gray topic name (e.g., "GENERAL"), with the Article tab tagged opposite
- Right page (recto): outer-aligned (right), small-caps muted gray topic name (e.g., "DISTRICT STANDARDS"), with the Article tab tagged opposite
- Topic name is typically the Section name from the current page (e.g., "DRIVEWAYS" if the page is in Art. 3 §2 Driveways)
- District pages substitute the topic with "Core Zoning Districts" or "Special Zoning Districts" with a small ▪ between
- A thin horizontal rule (1 pt, muted gray) sits at the bottom of the header band

## 8. Footer band

The footer band runs across the bottom of the page, above the bottom margin:

- Left position: date string ("Adopted: November 3, 2020" for the original CZC, "Amended: March 24, 2025" for the amended version) in muted gray
- Right position: "Newcastle Core Zoning Code | [page number]" — wordmark in Article blue, separator "|" in gray, page number in muted gray
- On left pages (verso) the layout is mirrored: page number left, date right
- A thin horizontal rule (1 pt, muted gray) sits at the top of the footer band

## 9. Tables

Several table conventions are in use:

**Standard data tables** (e.g., Table 2.1 Sight Distance, Table 5.5 Tower Dimensions):
- Caption above table, e.g., "TABLE 2.1 SIGHT DISTANCE" — semibold uppercase, body-text-size
- Header row: tinted gray (`#E8E8E8`) background, semibold uppercase body
- Body rows: white background, body text
- Borders: subtle horizontal rules only, no vertical borders
- Right-aligned numerics, left-aligned text columns

**District tables (D1–D6 and SD pages)**:
- The district badge + name banner is itself a table-like header row in the district color
- Below, two-column tabular content (Lot Dimensions | Permitted Buildings, etc.)
- "Use Table" section uses a multi-column grid of use categories with status glyphs (● ❶ ❷ ✪)

**Status glyphs** in district use tables:
- ● Use Permit Required (CEO)
- ❶ Residential Companion Permit Required (CEO)
- ❷ Special Permit Required (Planning Board)
- ✪ Expanded Use Permit Required (Planning Board)
- Blank = not allowed in this district

## 10. Cross-reference conventions

- Article references: "Article 4 Building Standards" — Article + number + name
- Section references: "Article 4 Section 17 Building Groups" — full path with "Section"
- Internal short references within an Article: "see section 8" (lowercase "section")
- Table references: "Table 4.3 Building Groups Permitted By District" — Table + number + name
- Exhibit references: "Exhibit 1.1 District Map" — Exhibit + number + name
- External law references: "Title 23, Section 704" or "30-A MRSA Chapter 187"
- Defined terms appear with leading capital ("Public Road," "Frontage Zone") but are not italicized or otherwise typographically distinguished

## 11. Notable conventions to preserve in new content

1. **Every Section starts with Purpose, then Applicability, then General/Standards** — without exception
2. **No bulleted lists** — everything is numbered or lettered hierarchically
3. **No bold/italic emphasis in body text** — emphasis carries through heading hierarchy alone
4. **No footnotes or endnotes** — references are inline
5. **No marginal annotations** — the outer margin is reserved for the Article tab
6. **Tables include captions with TABLE N.N format**, even single-table sections
7. **Cross-references include the named section, not just the number** (e.g., "Article 4 Building Standards," not "Article 4")
8. **Definitions are alphabetized**, one bold term per entry, body text definition below

## 12. Open questions for the template implementation

- Exact body font selection (Source Sans 3 working; may refine after pixel-sampling)
- Whether to embed fonts in PDFs (recommended for portability and archival)
- Whether the District Map exhibits will be regenerated as vector (SVG) or remain raster — affects template page break logic
- Whether the rotated Article tab should be implemented via Typst `rotate()` or via a precomputed image
- Whether numbered list nesting in Typst can produce the exact CZC indent pattern, or if a custom show rule is needed

These will be resolved during template iteration.

## 13. Validation method

After the template is implemented, validate visual fidelity by:

1. Transcribing CZC Article 1 (pages 4–9, "General Standards") into markdown at the source numbering
2. Rendering it through the build pipeline
3. Placing a rendered page side-by-side with the corresponding baseline PDF page
4. Comparing: page geometry, fonts, colors, heading hierarchy, section divider, Article tab, header/footer bands, table styling
5. Iterating on the template until the comparison passes the "not jarring" bar set in the plan

Pixel-perfect identity is not required. The deliverable test is: does a typical reviewer perceive this as the same document or as a separate document?
