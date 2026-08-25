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

// Adoption state, passed by build-full-czc.sh / build-standalone.sh. The DRAFT
// banner (from inventory.json's _meta.banner) asserts "not yet reviewed or
// adopted", which is false once adopted -- but the provenance note must survive
// in every mode: the district geometry is still an approximation
// (ADOPTION-SPEC.md §4.2). The MEETING banner carries its own not-yet-adopted
// marker because this exhibit runs five pages and gets separated from the cover.
#let adoption_mode = sys.inputs.at("adoption_mode", default: "draft")
#let PROVENANCE = "Types derived from a trace of the District Map; recorded right-of-way, traveled way and other field values are approximate."

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
// Present use "Driveway" (§5.C.3.g) is NOT an eleventh Type. It is a deliberately
// quiet neutral so a driveway reads as "not a road" instead of competing with the
// ten Type colours. Its Type moves to the "On conversion" column.
#let DRIVEWAY_COLOR = rgb("#A2988C")

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

#let banner = if adoption_mode == "adopted" {
  PROVENANCE
} else if adoption_mode == "meeting" {
  "NOT YET ADOPTED — for adoption at Town Meeting. " + PROVENANCE
} else {
  data.at("_meta", default: (:)).at("banner",
    default: "Sample data shown — not Newcastle's adopted network.")
}

// ---- Cell helpers -----------------------------------------------------------
#let dash = text(fill: subsection_gray)[—]
#let or_dash(v) = if v == none or v == "" { dash } else { [#v] }
#let type_cell(t) = {
  if t == none or not (t in TYPE_COLORS) { return dash }
  box(baseline: 1pt, rect(width: 7pt, height: 7pt, radius: 1pt, fill: TYPE_COLORS.at(t), stroke: none))
  h(3pt); text(weight: "bold")[#t]
}
#let is_driveway(s) = s.at("present_use", default: none) == "Driveway"
// What the segment IS today. A recorded driveway shows D; everything else shows
// its Type. §7.C.8 is what makes an access way a Driveway, not this column.
#let use_cell(s) = {
  if is_driveway(s) {
    box(baseline: 1pt, rect(width: 7pt, height: 7pt, radius: 1pt, fill: DRIVEWAY_COLOR, stroke: none))
    h(3pt); text(weight: "bold")[D]
  } else { type_cell(s.at("type", default: none)) }
}
// The Type that WOULD apply if the driveway is later expanded past the §7.C.7
// threshold — filled only for a recorded driveway, since for every other segment
// the Type column already states the standard that applies.
#let conversion_cell(s) = {
  if is_driveway(s) { type_cell(s.at("type", default: none)) } else { dash }
}
#let termini_str(s) = {
  let t = s.at("termini", default: ("", ""))
  [#t.at(0) #sym.arrow.r #t.at(1)]
}

// ---- Exhibit caption + reading note -----------------------------------------
#block(above: 0pt, below: 7pt,
  text(fill: subsection_gray, weight: "bold", stretch: 75%, size: 11pt, tracking: 0.3pt)[
    EXHIBIT 3.1#h(0.85em)INVENTORY OF EXISTING THOROUGHFARES])

#block(above: 0pt, below: 9pt, text(size: 8pt, fill: subsection_gray)[
  #text(weight: "bold", fill: body_dark)[Being listed here does not require anyone to do anything.]
  Adoption of this Article does not require any existing thoroughfare or driveway to be widened,
  rebuilt, or brought up to the standards of its Type (§1.B.5).
  #linebreak()
  The #text(weight: "bold")[Type] column states what a segment is today and the standard that
  applies when it is built, rebuilt, or improved (§5.C.2). Segments marked #text(weight: "bold")[D]
  serve today as #text(weight: "bold")[driveways]. For those, the standard that would apply
  #emph[if and when] the driveway is later expanded to serve more than two single-family dwellings,
  or more than one two-family dwelling, is shown under #text(weight: "bold")[On conversion]
  (§7.C.7–8, §7.F). #text(style: "italic")[A driveway stays a driveway until that happens — no
  Street or Road standard reaches it in the meantime, whatever Type is recorded for it.]
  #linebreak()
  The remaining columns are reference information (§5.C.3) the Town may update without amending
  this Code. Names and termini are drawn from the Town's E-911 road centerline data and reflect
  #text(style: "italic")[addressing, not regulatory status]. Recorded right-of-way, traveled way,
  and other field values are approximate.
  #text(weight: "bold")[#banner]])

// ---- The inventory table (breakable; header repeats per page) ---------------
#let hd(s) = text(fill: subsection_gray, weight: "bold", size: 6.5pt, tracking: 0.3pt)[#upper(s)]
#set text(size: 7pt)
#table(
  columns: (20pt, 1.6fr, 2.0fr, 0.75fr, 0.9fr, 1.1fr),
  stroke: (x, y) => (bottom: 0.4pt + subsection_gray),
  inset: (x: 4pt, y: 3pt),
  align: (x, y) => if x == 0 { right + horizon } else { left + horizon },
  table.header(
    hd("#"), hd("Thoroughfare"), hd("From → To"), hd("Type"), hd("On conversion"),
    hd("Ownership"),
  ),
  ..segs.enumerate().map(((i, s)) => (
    text(fill: subsection_gray)[#(i + 1)],
    [#s.name],
    text(fill: subsection_gray)[#termini_str(s)],
    use_cell(s),
    conversion_cell(s),
    or_dash(s.at("ownership", default: none)),
  )).flatten()
)
