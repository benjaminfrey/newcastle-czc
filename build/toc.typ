// build/toc.typ — Table of Contents for the integrated CZC draft.
//
// Reads the entries JSON produced by build/toc_entries.py (which scans the
// built BODY pdf, so the TOC can never drift from the rendered content):
//   typst compile build/toc.typ out.pdf --input data=/path/to/toc.json \
//       --font-path style/fonts
//
// Matches the baseline CZC TOC grammar, measured from docs/ page 2-3:
//   * Page geometry IDENTICAL to the body (inside 90 / outside 44, two 217pt
//     columns, 44pt gutter) so the spread reads as one document.
//   * "CONTENTS" running head, 11pt subsection-gray bold, OUTER edge.
//   * "TABLE OF CONTENTS" title, 25pt article-blue.
//   * Article label "ARTICLE N" on its own line + name line, both 14pt gray
//     bold; sub-entries 11.5pt article-blue with dot leaders and right-aligned
//     page numbers.
//   * Front matter is UNNUMBERED, so the footer carries only the blue wordmark
//     on the OUTER edge (no page number, no date) — exactly as the baseline TOC.

#let article_blue    = rgb("#367AAC")
#let subsection_gray = rgb("#7C766F")
#let body_dark       = rgb("#231F20")

#let data = json(sys.inputs.data)

#set text(font: ("Barlow", "Helvetica Neue", "Helvetica"), stretch: 75%, fill: body_dark)

#set page(
  paper: "us-letter",
  margin: (inside: 90pt, outside: 44pt, top: 64pt, bottom: 56pt),
  header-ascent: 26pt,
  footer-descent: 28pt,
  header: context {
    set text(size: 11pt, fill: subsection_gray, weight: "bold", stretch: 75%, tracking: 0.3pt)
    if calc.odd(here().page()) {
      // recto: outer edge = right
      grid(columns: (1fr, auto), align: (left, right), [], [CONTENTS])
    } else {
      // verso: outer edge = left
      grid(columns: (auto, 1fr), align: (left, right), [CONTENTS], [])
    }
  },
  footer: context {
    set text(size: 10pt, weight: "bold", stretch: 75%, fill: article_blue)
    let mark = [Newcastle Core Zoning Code]
    if calc.odd(here().page()) {
      grid(columns: (1fr, auto), align: (left, right), [], mark)
    } else {
      grid(columns: (auto, 1fr), align: (left, right), mark, [])
    }
  },
)

// Dot leader: a 1fr box of repeated dots that pushes the page number flush to
// the column's right edge. Inherits size/color from the insertion context.
#let leader = box(width: 1fr, inset: (x: 3pt), repeat(gap: 2pt)[.])

#let sub_entry(e) = block(spacing: 2.6pt, {
  set text(size: 11.5pt, fill: article_blue, weight: "regular")
  [#upper(e.name)#leader#str(e.page)]
})

#let article_block(a) = {
  v(7pt, weak: true)
  set text(size: 14pt, fill: subsection_gray, weight: "bold")
  block(spacing: 3pt)[ARTICLE #a.num]
  block(spacing: 5pt)[#upper(a.name)#leader#str(a.page)]
  for e in a.entries { sub_entry(e) }
}

// Title (article-blue, 25pt), then the two-column entry flow.
#block(spacing: 12pt, text(size: 25pt, fill: article_blue, weight: "regular")[TABLE OF CONTENTS])

#columns(2, gutter: 44pt)[
  #for a in data.articles { article_block(a) }
]
