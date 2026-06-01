// Minimal pandoc→Typst template for the TEXT redline deliverable.
//
// Used by build/build-redline.sh:
//   pandoc redlined.md -o out.pdf --pdf-engine=typst \
//     --template=style/redline-template.typ \
//     --pdf-engine-opt=--font-path=style/fonts \
//     -V redline-title="..." -V redline-subtitle="..."
//
// Deliberately NOT the full czc-template: that one stamps per-Article openers,
// rotated tabs and running heads from per-Article metadata, which would
// misrender a single whole-document pass. This template is a clean, readable
// single-column change report. Deletions arrive as markdown strikeout
// (pandoc → #strike[...]); insertions arrive as raw Typst #text(fill: red)[...]
// emitted by build/redline-text.py.

#let body_dark       = rgb("#231F20")
#let article_blue    = rgb("#367AAC")
#let subsection_gray = rgb("#7C766F")
#let added_red       = rgb("#cc0000")

#set page(
  paper: "us-letter",
  margin: (x: 1in, y: 1in),
  numbering: "1",
  number-align: center,
)

#set text(
  font: ("Barlow", "Helvetica Neue", "Helvetica"),
  size: 10pt,
  fill: body_dark,
  lang: "en",
)
#set par(leading: 0.62em, spacing: 0.95em, justify: false)

// Headings — CZC blue/gray so document structure stays legible. Level-1 is the
// Article line (the full czc-template hides it; here we WANT it visible).
#show heading.where(level: 1): it => block(above: 20pt, below: 10pt)[
  #set text(fill: article_blue, weight: "bold", size: 17pt)
  #upper(it.body)
]
#show heading.where(level: 2): it => block(above: 14pt, below: 6pt)[
  #set text(fill: article_blue, weight: "bold", size: 13pt)
  #upper(it.body)
]
#show heading.where(level: 3): it => block(above: 12pt, below: 5pt)[
  #set text(fill: subsection_gray, weight: "bold", size: 11pt)
  #upper(it.body)
]
#show heading.where(level: 4): it => block(above: 9pt, below: 4pt)[
  #set text(fill: subsection_gray, weight: "bold", size: 10pt)
  #it.body
]

// Data tables: light horizontal hairlines, matching the CZC body look.
#set table(stroke: (x, y) => (top: 0.5pt + body_dark, bottom: 0.5pt + body_dark),
           inset: (x: 5pt, y: 3pt), fill: none)

// ---- Title + legend ---------------------------------------------------------
$if(redline-title)$
#align(center)[
  #block(spacing: 6pt, text(size: 19pt, weight: "bold", fill: article_blue)[$redline-title$])
$if(redline-subtitle)$
  #block(spacing: 4pt, text(size: 12pt, fill: subsection_gray)[$redline-subtitle$])
$endif$
]
#block(above: 12pt, below: 16pt, width: 100%, inset: 8pt,
       stroke: 0.5pt + subsection_gray, radius: 3pt)[
  #set text(size: 9pt)
  *How to read this redline.* #strike[Struck-through text] was removed;
  #text(fill: added_red)[red text] was added immediately after it. Only the
  TEXT of the Code is compared — natively rendered layout (district spreads,
  Type plates, district maps) and images are not shown here.
]
$endif$

$body$
