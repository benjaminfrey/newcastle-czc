// Newcastle CZC Typst template (pandoc Typst output)
//
// Used by build scripts via:
//   pandoc input.md -o output.pdf --pdf-engine=typst --template=style/czc-template.typ
//
// Reads colors from style/czc-colors.yml. All visual values can be tuned without
// editing markdown sources.

// ---- Color palette ---------------------------------------------------------
// These values mirror style/czc-colors.yml — that file is the documented
// source of truth. Keep them in sync. (TODO: load YAML directly once the
// pandoc → typst resource-path/root issue is resolved.)

#let article_blue       = rgb("#2E96CC")
#let section_blue_dark  = rgb("#2079B0")
#let body_dark          = rgb("#333333")
#let footer_gray        = rgb("#666666")
#let header_gray        = rgb("#777777")
#let table_tint         = rgb("#E8E8E8")
#let rule_gray          = rgb("#B0B0B0")

// ---- Pandoc-provided metadata -----------------------------------------------

$if(title)$
#let doc_title = "$title$"
$else$
#let doc_title = "Newcastle Core Zoning Code"
$endif$

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

$if(tab-color)$
#let tab_color = rgb("$tab-color$")
$else$
#let tab_color = article_blue
$endif$

$if(footer-date)$
#let footer_date = "$footer-date$"
$else$
#let footer_date = "Draft"
$endif$

// ---- Page geometry ----------------------------------------------------------
// Note: columns are applied per-block via `columns(2)`, not as a page set rule,
// so the article opener can span the page in single-column mode.

#set page(
  paper: "us-letter",
  margin: (top: 0.75in, bottom: 0.85in, inside: 0.75in, outside: 1.0in),
  header: context {
    let topic = ""
    // Pull the most recent level-2 heading as the topic name for the header band
    let h = query(selector(heading.where(level: 2)).before(here()))
    if h.len() > 0 {
      topic = upper(h.last().body)
    }
    set text(size: 8pt, fill: header_gray, tracking: 0.5pt)
    let row = if calc.even(here().page()) {
      // Verso (left page): topic on outer (left), article tag on inner (right)
      grid(columns: (1fr, auto), align: (left, right),
        topic, ""
      )
    } else {
      // Recto (right page): topic on outer (right)
      grid(columns: (auto, 1fr), align: (left, right),
        "", topic
      )
    }
    block(below: 4pt, row)
    line(length: 100%, stroke: 0.5pt + rule_gray)
  },
  footer: context {
    set text(size: 8pt, fill: footer_gray)
    line(length: 100%, stroke: 0.5pt + rule_gray)
    v(4pt)
    let page_num = here().page()
    if calc.even(page_num) {
      // Verso: page left, date right (using grid for alignment)
      grid(columns: (auto, 1fr, auto), align: (left, center, right),
        text(fill: footer_gray)[#str(page_num)  |  #text(fill: article_blue, weight: "semibold")[Newcastle Core Zoning Code]],
        "",
        footer_date
      )
    } else {
      // Recto: date left, wordmark + page right
      grid(columns: (auto, 1fr, auto), align: (left, center, right),
        footer_date,
        "",
        [#text(fill: article_blue, weight: "semibold")[Newcastle Core Zoning Code]  |  #str(page_num)]
      )
    }
  }
)

// Body font: Helvetica Neue is the working default until we install static
// Source Sans 3 OTFs. (Typst doesn't accept variable-width font files,
// which is the form delivered by `brew install --cask font-source-sans-3`.)
#set text(font: ("Helvetica Neue", "Helvetica"),
          size: 9pt, fill: body_dark, lang: "en")

#set par(leading: 0.5em, justify: false, first-line-indent: 0pt)

// ---- Article tab (rotated vertical marker in outer margin) ------------------

#let article_tab(num, color: tab_color, text_color: white) = {
  if num == "" { return }
  place(
    right + horizon,
    dx: 0.45in,  // into the outer margin (page right edge + dx)
    dy: 0pt,
    rotate(-90deg, origin: center + horizon,
      box(
        fill: color,
        inset: (x: 8pt, y: 4pt),
        text(fill: text_color, weight: "semibold", size: 11pt, tracking: 1pt)[
          ARTICLE #num
        ]
      )
    )
  )
}

// ---- Article opener (called from body, not via H1 show rule) ---------------

#let article_opener(number, name) = {
  if number == "" and name == "" { return }
  block(above: 0.5em, below: 1.5em)[
    #set text(fill: article_blue, weight: "bold")
    #if number != "" {
      text(size: 36pt, tracking: 1pt)[ARTICLE #number]
      v(-0.2em)
    }
    #text(size: 48pt, tracking: 0.5pt)[#upper(name)]
    #v(0.3em)
    #line(length: 100%, stroke: 1pt + article_blue)
  ]
}

// ---- Heading show rules -----------------------------------------------------

// Level 1 in markdown: ignored when article-name is provided via metadata.
// (Suppresses the duplicate "Article N Name" heading that lives in source files
// for human readability but should not be rendered as content.)
#show heading.where(level: 1): h => { }

// Level 2: Numbered Section (e.g., "1. CORE ZONING CODE")
#show heading.where(level: 2): h => {
  set block(above: 1.5em, below: 0.5em)
  set text(fill: article_blue, weight: "bold", size: 18pt, tracking: 0.5pt)
  upper(h.body)
  v(-0.3em)
  // Divider line with small square endpoints
  context {
    let endpoint_size = 3pt
    grid(columns: (auto, 1fr, auto), align: horizon,
      rect(fill: article_blue, width: endpoint_size, height: endpoint_size),
      line(length: 100%, stroke: 0.8pt + article_blue),
      rect(fill: article_blue, width: endpoint_size, height: endpoint_size)
    )
  }
}

// Level 3: Lettered Subsection (e.g., "A. PURPOSE")
#show heading.where(level: 3): h => {
  set block(above: 1em, below: 0.3em)
  set text(fill: section_blue_dark, weight: "bold", size: 10pt, tracking: 0.3pt)
  upper(h.body)
}

// Level 4: Inline header for additional structure
#show heading.where(level: 4): h => {
  set block(above: 0.7em, below: 0.2em)
  set text(fill: section_blue_dark, weight: "bold", size: 9pt)
  upper(h.body)
}

// ---- List styling -----------------------------------------------------------
//
// CZC convention: 1. / A. / 1. / a. / i. hierarchy. Section headings own the
// "A." and uppercase-letter level (handled in heading show rules above), so
// for list bodies pandoc emits a top-level enum at the "1." level and nested
// enums at the "a." and "i." levels via #set enum(numbering: ...) inside
// #block[...]. Our defaults below:
//   - keep "1." numbering at the outer level
//   - let pandoc's per-block override take care of nested numbering style
//   - apply real visual indent at every level so nested items don't read
//     as continuations of their parent

#set enum(
  indent: 1.2em,
  body-indent: 0.5em,
  spacing: 0.55em,
  tight: false
)

// Suppress bulleted lists — CZC uses only numbered/lettered hierarchies.
#show list: it => { it }

// Suppress bulleted lists — CZC uses only numbered/lettered hierarchies.
#show list: it => { it }

// ---- Table styling ----------------------------------------------------------

#show table: it => {
  set text(size: 8.5pt)
  it
}

#let czc_table(caption: none, ..args) = {
  if caption != none {
    block(above: 0.8em, below: 0.3em,
      text(weight: "semibold", size: 8.5pt, tracking: 0.5pt)[#upper(caption)]
    )
  }
  table(
    stroke: 0.4pt + rule_gray,
    fill: (col, row) => if row == 0 { table_tint } else { white },
    ..args
  )
}

// ---- Body content (pandoc inserts here) -------------------------------------

// Render the rotated Article tab in the outer margin on every page.
// place() with `scope: "parent"` would be ideal, but we use page-set-rule
// background instead so it applies per-page automatically.

#set page(background: article_tab(article_number, color: tab_color))

// Article opener (full page width, single column)
#article_opener(article_number, article_name)

// Body content (two columns)
#columns(2, gutter: 0.25in)[
$body$
]
