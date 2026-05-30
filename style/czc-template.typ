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

// ---- Page geometry ----------------------------------------------------------
// Margins: outside (tab side) narrow, inside (gutter) wide, mirroring the
// baseline's asymmetric spread. Typst flips inside/outside per page parity
// automatically when we use the named-margins form.

#set page(
  paper: "us-letter",
  margin: (
    inside: 0.95in,     // ~68pt gutter side
    outside: 0.62in,    // ~45pt tab side
    top: 0.55in,        // ~40pt
    bottom: 0.55in,     // ~40pt
  ),
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

#set par(leading: 0.42em, justify: false, first-line-indent: 0pt)

// ---- Header & footer bands --------------------------------------------------

#set page(
  header: context {
    set text(size: 8.5pt, fill: subsection_gray, weight: "bold", stretch: 75%, tracking: 0.3pt)
    let pn = here().page()
    // The header band shows the current Section name in upper small caps on
    // the OUTSIDE edge. For now, pull the most recent level-2 heading.
    let h = query(selector(heading.where(level: 2)).before(here()))
    let topic = if h.len() > 0 { upper(h.last().body) } else { [] }
    let row = if calc.even(pn) {
      // Verso (left page): topic on outer (left)
      grid(columns: (1fr, auto), align: (left, right), topic, [])
    } else {
      // Recto (right page): topic on outer (right)
      grid(columns: (auto, 1fr), align: (left, right), [], topic)
    }
    block(below: 4pt, row)
  },
  footer: context {
    set text(size: 10pt, weight: "bold", stretch: 75%, fill: body_dark)
    let pn = here().page()
    let wordmark = text(fill: article_blue)[Newcastle Core Zoning Code]
    let pagenum = text(fill: body_dark)[#str(pn)]
    let separator = text(fill: subsection_gray)[ | ]
    let date_part = text(fill: article_blue)[#footer_date]
    if calc.even(pn) {
      // Verso: page-num + separator + wordmark on LEFT, date on RIGHT
      grid(columns: (auto, 1fr, auto), align: (left, center, right),
        [#pagenum#separator#wordmark],
        [],
        date_part,
      )
    } else {
      // Recto: date on LEFT, wordmark + separator + page-num on RIGHT
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
  block(above: 0pt, below: 1.2em)[
    #set text(fill: article_blue, weight: "regular", stretch: 75%)
    #if number != "" {
      block(above: 0pt, below: 0pt,
        text(size: 33pt, weight: "regular")[ARTICLE #number]
      )
      v(-0.45em)
    }
    #block(above: 0pt, below: 0pt,
      text(size: 33pt, weight: "bold")[#upper(name)]
    )
  ]
}

// ---- Heading show rules -----------------------------------------------------

// Level 1 (markdown `#`): suppressed — article opener comes from metadata.
#show heading.where(level: 1): h => { }

// Level 2: numbered Section (e.g., "1. CORE ZONING CODE") — 14pt Bold blue.
// Followed by a thin blue divider with 4×4pt square endpoints.
#show heading.where(level: 2): h => {
  set block(above: 1.4em, below: 0.6em)
  set text(fill: article_blue, weight: "bold", stretch: 75%, size: 14pt, tracking: 0.3pt)
  upper(h.body)
  v(0.15em)
  // Divider: 4×4pt square + thin line + 4×4pt square
  let endpoint = 4pt
  grid(columns: (auto, 1fr, auto), align: horizon,
    rect(fill: article_blue, width: endpoint, height: endpoint),
    line(length: 100%, stroke: 0.6pt + article_blue),
    rect(fill: article_blue, width: endpoint, height: endpoint),
  )
  v(0.2em)
}

// Level 3: lowercase-letter Subsection (e.g., "a. PURPOSE") — 11pt Bold gray.
// IMPORTANT: baseline uses lowercase letter markers (a./b./c.), not uppercase.
// Source markdown already has lowercase letter + uppercase name (e.g., "a.
// PURPOSE"); we preserve case as authored — no upper() call here.
#show heading.where(level: 3): h => {
  set block(above: 0.9em, below: 0.3em)
  set text(fill: subsection_gray, weight: "bold", stretch: 75%, size: 11pt, tracking: 0.2pt)
  h.body
}

// Level 4: occasional inline header (used sparsely, kept small).
#show heading.where(level: 4): h => {
  set block(above: 0.6em, below: 0.2em)
  set text(fill: subsection_gray, weight: "bold", stretch: 75%, size: 9pt)
  upper(h.body)
}

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

#show table: it => {
  set text(size: 8.5pt, stretch: 75%)
  it
}

// ---- Body content (pandoc inserts here) -------------------------------------

// Article opener (full page width, single column, top of page).
#article_opener(article_number, article_name)

// Body content (two columns from here down).
#show: rest => columns(2, gutter: 0.18in, rest)

$body$
