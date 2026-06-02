// =============================================================================
// Newcastle CZC — Article 3 INVENTORY OF EXISTING STREETS & ROADS (Exhibit 3.1)
// =============================================================================
//
// The binding instrument of §5.C: a table assigning each segment its Street/Road
// Type (the regulatory classification, §5.C.2) alongside the recorded reference
// fields (ownership, widths, district, MaineDOT class, nonconformity — §5.C.3,
// "not a standard"). Reads the SAME inventory.json the Type Map (Exhibit 3.2)
// renders from, so the two never drift.
//
//   typst compile source/street-type-inventory.typ /tmp/ex31.pdf \
//     --root . --font-path style/fonts \
//     --input data=/data/street-types/work/inventory.json --input page_offset=2
//
// PARITY: chrome keys off here().page() + page_offset; keep page_offset EVEN.
// =============================================================================

#let page_offset = int(sys.inputs.at("page_offset", default: "2"))
#let footer_date = sys.inputs.at("footer_date", default: "Draft")
#let data_path   = sys.inputs.at("data", default: "exhibits/street-types/inventory-sample.json")

#let article_number = "3"
#let article_name = "Thoroughfares"

#let article_blue    = rgb("#367AAC")
#let body_dark       = rgb("#231F20")
#let subsection_gray = rgb("#7C766F")
#let tab_gray        = rgb("#BFBFBF")
#let hair            = 0.5pt + subsection_gray
#let body_font = ("Barlow", "Helvetica Neue", "Helvetica")

#let TYPE_COLORS = (
  S1: rgb("#103E66"), S2: rgb("#2E6FA0"), S3: rgb("#4E97C8"), S4: rgb("#74B2D6"), S5: rgb("#9AC8E4"),
  R1: rgb("#3D4A1F"), R2: rgb("#5E6E33"), R3: rgb("#84934A"), R4: rgb("#A99A4B"), R5: rgb("#C2B777"),
)

// ---- Page geometry + chrome (identical to street-type-map.typ) --------------
#set page(
  paper: "us-letter",
  margin: (inside: 90pt, outside: 44pt, top: 64pt, bottom: 56pt),
  header-ascent: 26pt, footer-descent: 28pt,
)
#set text(font: body_font, stretch: 75%, weight: "light", size: 8.5pt, fill: body_dark, lang: "en")
#set par(leading: 0.57em, spacing: 0.78em, justify: false, first-line-indent: 0pt)

#set page(header: context {
  set text(size: 11pt, fill: subsection_gray, weight: "bold", stretch: 75%, tracking: 0.3pt)
  let pn = here().page() + page_offset
  let topic = upper(article_name)
  if calc.even(pn) { grid(columns: (auto, 1fr), align: (left, right), topic, []) }
  else { grid(columns: (1fr, auto), align: (left, right), [], topic) }
})
#set page(footer: context {
  set text(size: 10pt, weight: "bold", stretch: 75%, fill: body_dark)
  let pn = here().page() + page_offset
  let wm = text(fill: article_blue)[Newcastle Core Zoning Code]
  let num = text(fill: body_dark)[#str(pn)]
  let sep = text(fill: body_dark)[ | ]
  let dt = text(fill: article_blue)[#footer_date]
  if calc.even(pn) {
    grid(columns: (auto, 1fr, auto), align: (left, center, right), [#num#sep#wm], [], dt)
  } else {
    grid(columns: (auto, 1fr, auto), align: (left, center, right), dt, [], [#wm#sep#num])
  }
})
#let article_tab_box = rotate(-90deg, reflow: true,
  box(fill: tab_gray, width: 72pt, height: 30pt, inset: (x: 6pt, y: 0pt),
    align(center + horizon,
      text(fill: white, weight: "bold", stretch: 75%, size: 14pt, tracking: 0.5pt)[ARTICLE #article_number])))
#set page(background: context {
  let pn = here().page() + page_offset
  if calc.even(pn) { place(top + left, dy: 139.5pt, article_tab_box) }
  else { place(top + right, dy: 139.5pt, article_tab_box) }
})

// =============================================================================
// DATA
// =============================================================================
#let data = json(data_path)
#let segs = data.segments.sorted(key: s => (s.name, s.at("termini", default: ("", "")).at(0)))

#let banner = data.at("_meta", default: (:)).at("banner",
  default: "Sample data shown — not Newcastle's adopted network.")

// ---- Cell helpers -----------------------------------------------------------
#let dash = text(fill: subsection_gray)[—]
#let or_dash(v) = if v == none or v == "" { dash } else { [#v] }
#let type_cell(t) = {
  if t == none or not (t in TYPE_COLORS) { return dash }
  box(baseline: 1pt, rect(width: 7pt, height: 7pt, radius: 1pt, fill: TYPE_COLORS.at(t), stroke: none))
  h(3pt); text(weight: "bold")[#t]
}
#let termini_str(s) = {
  let t = s.at("termini", default: ("", ""))
  [#t.at(0) #sym.arrow.r #t.at(1)]
}
#let dist_str(s) = {
  let d = s.at("districts", default: ())
  if d.len() == 0 { dash } else { d.join(", ") }
}

// ---- Exhibit caption + reading note -----------------------------------------
#block(above: 0pt, below: 7pt,
  text(fill: subsection_gray, weight: "bold", stretch: 75%, size: 11pt, tracking: 0.3pt)[
    EXHIBIT 3.1#h(0.85em)INVENTORY OF EXISTING THOROUGHFARES])

#block(above: 0pt, below: 9pt, text(size: 8pt, fill: subsection_gray, style: "italic")[
  The #text(weight: "bold")[Type] column is the binding classification of each segment (§5.C.2). The remaining
  columns record reference information (§5.C.3) the Town may update without amending this Code.
  #text(weight: "bold")[#banner]])

// ---- The inventory table (breakable; header repeats per page) ---------------
#let hd(s) = text(fill: subsection_gray, weight: "bold", size: 6.5pt, tracking: 0.3pt)[#upper(s)]
#set text(size: 7pt)
#table(
  columns: (1.5fr, 1.9fr, 0.75fr, 1.15fr, 0.7fr),
  stroke: (x, y) => (bottom: 0.4pt + subsection_gray),
  inset: (x: 4pt, y: 3pt),
  align: (left + horizon),
  table.header(
    hd("Thoroughfare"), hd("From → To"), hd("Type"), hd("Ownership"), hd("District"),
  ),
  ..segs.map(s => (
    [#s.name],
    text(fill: subsection_gray)[#termini_str(s)],
    type_cell(s.at("type", default: none)),
    or_dash(s.at("ownership", default: none)),
    dist_str(s),
  )).flatten()
)
