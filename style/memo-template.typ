// Memo template — Newcastle CZC house style. Clean single-column letter memo.
//
// Used by build/build-memo.sh:
//   pandoc memo.md -o out.pdf --pdf-engine=typst --template=style/memo-template.typ \
//     --pdf-engine-opt=--font-path=style/fonts \
//     -V running-head="..." -V foot-note="..."
//
// Mirrors style/redline-template.typ conventions (proven pandoc→Typst pattern).
// Colours are the measured CZC palette (style/czc-colors.yml). Deliberately NOT
// the full czc-template: that one stamps per-Article openers, rotated tabs and
// running heads, which would misrender a plain memo.

#let body_dark       = rgb("#231F20")
#let article_blue    = rgb("#367AAC")
#let subsection_gray = rgb("#7C766F")
#let rule_faint      = rgb("#C9C6C2")

#set page(
  paper: "us-letter",
  margin: (x: 1in, top: 0.9in, bottom: 0.9in),
  header: context {
    if here().page() > 1 {
      set text(size: 8pt, fill: subsection_gray, weight: "medium")
      grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
        [$if(running-head)$$running-head$$endif$],
        [Newcastle Core Zoning Code])
      v(2pt)
      line(length: 100%, stroke: 0.4pt + rule_faint)
    }
  },
  footer: context {
    set text(size: 8.5pt, fill: subsection_gray)
    line(length: 100%, stroke: 0.4pt + rule_faint)
    v(3pt)
    grid(columns: (1fr, auto, 1fr), align: (left, center, right),
      [$if(foot-note)$#text(size: 8pt)[$foot-note$]$endif$],
      text(fill: article_blue, weight: "bold")[#counter(page).display("1")],
      [])
  },
)

#set text(font: ("Barlow", "Helvetica Neue", "Helvetica"), size: 10pt, fill: body_dark, lang: "en")
#set par(leading: 0.62em, spacing: 0.92em, justify: true)

// ---- Headings --------------------------------------------------------------
// Level 1 = the "MEMORANDUM" title line (rule beneath, like a letterhead).
#show heading.where(level: 1): it => block(below: 9pt, above: 0pt, width: 100%)[
  #set text(fill: article_blue, weight: "bold", size: 21pt)
  #upper(it.body)
  #v(3pt)
  #line(length: 100%, stroke: 1.2pt + article_blue)
]
// Level 2 = numbered sections.
#show heading.where(level: 2): it => block(above: 15pt, below: 6pt, breakable: false)[
  #set text(fill: article_blue, weight: "bold", size: 12.5pt)
  #upper(it.body)
]
#show heading.where(level: 3): it => block(above: 11pt, below: 4pt)[
  #set text(fill: subsection_gray, weight: "bold", size: 10.5pt)
  #upper(it.body)
]
#show heading.where(level: 4): it => block(above: 8pt, below: 3pt)[
  #set text(fill: subsection_gray, weight: "bold", size: 10pt)
  #it.body
]

// ---- Block quote: a tinted call-out bar (used for the "bottom line" notes) --
#show quote.where(block: true): it => block(
  width: 100%, inset: (x: 10pt, y: 7pt), above: 10pt, below: 10pt,
  fill: rgb("#EEF4F9"), stroke: (left: 2.5pt + article_blue),
)[#set text(size: 9.5pt); #it.body]

// ---- Tables: CZC hairlines; tinted, bold header row -------------------------
#set table(
  stroke: (x, y) => (
    top: if y == 0 { 0.8pt + body_dark } else { 0.4pt + rule_faint },
    bottom: 0.4pt + rule_faint,
  ),
  inset: (x: 5pt, y: 3.5pt),
  fill: (x, y) => if y == 0 { rgb("#EEF4F9") } else { none },
)
#show table: set text(size: 8.6pt)
#show table.cell.where(y: 0): set text(weight: "bold", fill: article_blue)
// Pandoc wraps tables in a #figure, which is non-breakable by default; allow
// long tables to flow across page breaks instead of being pushed/clipped.
#show figure: set block(breakable: true)

// Horizontal rule (markdown ---) -> subtle full-width divider. Pandoc emits a
// bare `#horizontalrule`, so it must be defined here (we replace pandoc's default
// template, which is where it normally lives).
#let horizontalrule = block(above: 11pt, below: 11pt,
  line(length: 100%, stroke: 0.4pt + rule_faint))

$body$
