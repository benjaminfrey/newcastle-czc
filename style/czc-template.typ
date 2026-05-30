// Newcastle CZC Typst template (pandoc Typst output)
//
// Used by build scripts via:
//   pandoc input.md -o output.pdf --pdf-engine=typst --template=style/czc-template.typ \
//     --pdf-engine-opt=--font-path=<path-to-style/fonts>
//
// All visual values are MEASURED from the baseline PDF — see style/style-analysis.md.

// ---- Color palette (measured from baseline) --------------------------------
// Mirrors style/czc-colors.yml — keep in sync.

#let article_blue       = rgb("#367AAC")   // section headings, dividers, wordmark
#let body_dark          = rgb("#231F20")   // body text (near-black warm gray)
#let subsection_gray    = rgb("#7C766F")   // subsection markers, header band, district descriptors
#let tab_gray           = rgb("#BFBFBF")   // article-tab background (uniform across districts)
#let rule_dark          = rgb("#231F20")   // thin table rules

// ---- Pandoc-provided metadata -----------------------------------------------

$if(article-number)$
#let article_number = "$article-number$"
$else$
#let article_number = ""
$endif$

$if(article-name)$
#let article_name = "$article-name$"
$else$
#let article_name = ""
$endif$

$if(footer-date)$
#let footer_date = "$footer-date$"
$else$
#let footer_date = "Draft"
$endif$

// Page-number offset. The full-CZC build renders each Article to its own PDF
// then concatenates; without an offset every Article's footer would restart at
// "1". The build script passes the cumulative page count of all prior Articles
// here so footers read continuously across the combined document. Offsets are
// always EVEN (the build pads odd-length Articles with a blank page), which
// keeps Typst's automatic inside/outside margins aligned to the combined
// document's page parity. Default 0 for the standalone (single-render) build.
$if(page-offset)$
#let page_offset = $page-offset$
$else$
#let page_offset = 0
$endif$

// ---- Page geometry ----------------------------------------------------------
// MEASURED from baseline (612x792pt US Letter):
//   Inside (binding/gutter) margin = 90pt  — the WIDE margin.
//   Outside (tab/fore-edge) margin = 44pt  — the NARROW margin (holds the tab).
//   Body text starts ~65pt from top, ends ~736pt; footer below.
//   Two columns of 217pt each separated by a 44pt gutter:
//     odd page: 90 | colL 90->307 | gutter 44 | colR 351->568 | 44
// Typst flips inside/outside per page parity automatically (named-margin form).

#set page(
  paper: "us-letter",
  margin: (
    inside: 90pt,       // binding/gutter side (WIDE) — measured
    outside: 44pt,      // tab/fore-edge side (NARROW) — measured
    top: 64pt,          // first body line at ~65pt — measured
    bottom: 56pt,       // body floor ~736pt — measured
  ),
  header-ascent: 26pt,  // header band lands at y≈25–38 — measured
  footer-descent: 28pt, // footer band lands at y≈765–777 — measured
)

// Body text default — Barlow at stretch 75% selects the Condensed face when
// BarlowCondensed-*.otf are on the font-path. Free metric/visual stand-in
// for the baseline's commercial Benton Sans Condensed.
#set text(
  font: ("Barlow", "Helvetica Neue", "Helvetica"),
  stretch: 75%,
  weight: "light",
  size: 8.5pt,
  fill: body_dark,
  lang: "en",
)

// Baseline measured: line advance 11.0pt for 8.5pt body (≈1.29×); paragraph
// gaps ≈15.5pt. leading/spacing tuned to those targets.
#set par(leading: 0.57em, spacing: 0.78em, justify: false, first-line-indent: 0pt)

// ---- Header & footer bands --------------------------------------------------

#set page(
  header: context {
    if article_name == "" { return [] }
    // MEASURED: 11pt Bold, subsection gray (#7C766F), on the OUTER edge.
    set text(size: 11pt, fill: subsection_gray, weight: "bold", stretch: 75%, tracking: 0.3pt)
    let pn = here().page() + page_offset
    // Running head = the Article's topic name (baseline shows the Article name,
    // not the running Section), placed on the OUTER edge per page parity.
    let topic = upper(article_name)
    if calc.even(pn) {
      // Verso (even/left page): topic on the OUTER (left) edge
      grid(columns: (auto, 1fr), align: (left, right), topic, [])
    } else {
      // Recto (odd/right page): topic on the OUTER (right) edge
      grid(columns: (1fr, auto), align: (left, right), [], topic)
    }
  },
  footer: context {
    set text(size: 10pt, weight: "bold", stretch: 75%, fill: body_dark)
    let pn = here().page() + page_offset
    let wordmark = text(fill: article_blue)[Newcastle Core Zoning Code]
    let pagenum = text(fill: body_dark)[#str(pn)]
    let separator = text(fill: body_dark)[ | ]   // measured: dark, grouped w/ page no.
    let date_part = text(fill: article_blue)[#footer_date]
    if calc.even(pn) {
      // Verso: page-num + separator + wordmark on OUTER (left); date inner (right)
      grid(columns: (auto, 1fr, auto), align: (left, center, right),
        [#pagenum#separator#wordmark],
        [],
        date_part,
      )
    } else {
      // Recto: date inner (left); wordmark + separator + page-num OUTER (right)
      grid(columns: (auto, 1fr, auto), align: (left, center, right),
        date_part,
        [],
        [#wordmark#separator#pagenum],
      )
    }
  },
)

// ---- Article tab (rotated vertical marker in outer margin) ------------------
//
// In the baseline the tab is a 30pt × 72pt gray rectangle with "ARTICLE N"
// in white BentonSansCond-Bold 14pt rotated 90° CCW, positioned in the
// outer margin near the top of the body area (y ≈ 139–211 pt).

// Make a tab that's 72pt wide × 30pt tall BEFORE rotation, then rotate the
// whole box -90° (CCW) so it becomes 30pt wide × 72pt tall on the page.
// rotate(reflow: true) tells Typst to use the post-rotation bounding box for
// layout, which is what we want.

#let article_tab_box = if article_number == "" { none } else {
  rotate(
    -90deg,
    reflow: true,
    box(
      fill: tab_gray,
      width: 72pt,
      height: 30pt,
      inset: (x: 6pt, y: 0pt),
      align(center + horizon,
        text(
          fill: white,
          weight: "bold",
          stretch: 75%,
          size: 14pt,
          tracking: 0.5pt,
        )[ARTICLE #article_number]
      )
    )
  )
}

#set page(background: context {
  if article_tab_box == none { return [] }
  let pn = here().page()
  let y_offset = 139.5pt  // matches baseline tab top edge
  if calc.even(pn) {
    place(top + left, dx: 0pt, dy: y_offset, article_tab_box)
  } else {
    place(top + right, dx: 0pt, dy: y_offset, article_tab_box)
  }
})

// ---- Article opener (top of first page of each Article) --------------------
//
// Baseline pattern: title block at top of page, then section body in two
// columns continues directly below — NOT a separate full-height title page.

#let article_opener(number, name) = {
  if number == "" and name == "" { return }
  set text(fill: article_blue, stretch: 75%)
  // MEASURED: both lines 33pt blue at x = text-block left; "ARTICLE N" in a
  // Book/Regular weight, the name in Bold; baselines are ~39pt apart with a
  // ~16pt ink gap between the ARTICLE baseline and the name's cap-top. Typst
  // sizes an all-caps line box to cap-height (~23pt at 33pt), so a 16pt
  // `below` yields the ~39pt baseline-to-baseline spacing of the baseline.
  if number != "" {
    block(above: 0pt, below: 16pt,
      text(size: 33pt, weight: "regular")[ARTICLE #number])
  }
  block(above: 0pt, below: 16pt,
    text(size: 33pt, weight: "bold")[#upper(name)])
}

// ---- Heading show rules -----------------------------------------------------

// Level 1 (markdown `#`): suppressed — article opener comes from metadata.
#show heading.where(level: 1): h => { }

// Level 2: numbered Section (e.g., "1. CORE ZONING CODE") — 14pt Bold blue.
// Followed by a thin blue divider with 4×4pt square endpoints.
#show heading.where(level: 2): h => block(above: 13pt, below: 6pt)[
  #set text(fill: article_blue, weight: "bold", stretch: 75%, size: 14pt, tracking: 0.3pt)
  #upper(h.body)
  #v(2pt)
  // Divider: 4×4pt square + 0.6pt line + 4×4pt square (measured)
  #grid(columns: (auto, 1fr, auto), align: horizon,
    rect(fill: article_blue, width: 4pt, height: 4pt),
    line(length: 100%, stroke: 0.6pt + article_blue),
    rect(fill: article_blue, width: 4pt, height: 4pt),
  )
]

// Level 3: lowercase-letter Subsection (e.g., "a. PURPOSE") — 11pt Bold gray.
// IMPORTANT: baseline uses lowercase letter markers (a./b./c.), not uppercase.
// Source markdown already has lowercase letter + uppercase name (e.g., "a.
// PURPOSE"); we preserve case as authored — no upper() call here.
#show heading.where(level: 3): h => block(above: 14pt, below: 9.5pt)[
  #set text(fill: subsection_gray, weight: "bold", stretch: 75%, size: 11pt, tracking: 0.2pt)
  #h.body
]

// Level 4: occasional inline header (used sparsely, kept small).
#show heading.where(level: 4): h => block(above: 9pt, below: 4pt)[
  #set text(fill: subsection_gray, weight: "bold", stretch: 75%, size: 9pt)
  #upper(h.body)
]

// ---- List styling -----------------------------------------------------------
// CZC convention: outer level "1." then "a." then "i." for nested items.
// Pandoc's per-block #set enum(numbering: "a.") inside #block[...] handles the
// nested numbering; we provide indent, body-indent, and spacing defaults.

#set enum(
  indent: 0.6em,
  body-indent: 0.6em,
  spacing: 0.55em,
  tight: false,
)

// Suppress bulleted lists — CZC uses only numbered/lettered hierarchies.
#show list: it => { it }

// ---- Table styling ----------------------------------------------------------
// MEASURED: CZC data tables use HORIZONTAL HAIRLINES ONLY (≈0.25pt, #231F20)
// at each row boundary, with NO vertical borders and NO header shading; rows
// are ~15pt tall. Pandoc emits a bare `#table` which inherits Typst's default
// heavy 1pt full-box grid, so we override the defaults globally here.

#set table(
  // Top+bottom on every cell => horizontal rule at each row boundary; the
  // absence of left/right keys means NO vertical borders.
  stroke: (x, y) => (top: 0.5pt + rule_dark, bottom: 0.5pt + rule_dark),
  inset: (x: 5pt, y: 3pt),     // ~15pt rows at 8.5pt text
  fill: none,                  // no header/zebra shading (baseline has none)
)
// Pandoc inserts a bare `table.hline()` after the header — keep it a hairline,
// and suppress any stray vertical rules.
#set table.hline(stroke: 0.5pt + rule_dark)
#set table.vline(stroke: none)

// Header row: slightly heavier than the light body, no fill (per baseline).
#show table.cell.where(y: 0): set text(weight: "medium")

// Table body text: 8.5pt condensed, matching the surrounding body.
#show table: set text(size: 8.5pt, stretch: 75%)

// ---- Body content (pandoc inserts here) -------------------------------------

// Article opener (full page width, single column, top of page).
#article_opener(article_number, article_name)

// Body content (two columns from here down).
// MEASURED gutter = 44pt (0.61in): two 217pt columns + 44pt gutter span the
// 478pt text block. (Was 0.18in — columns were jammed together.)
#show: rest => columns(2, gutter: 44pt, rest)

$body$
