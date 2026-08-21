// =============================================================================
// Newcastle CZC — Article 3 STREET & ROAD TYPE MAP (NATIVE TYPST renderer)
// =============================================================================
//
// Why this file exists:
//   Article 3 §5.C establishes an Inventory of Existing Streets & Roads. The
//   binding content of that Inventory is each segment's assigned Street/Road
//   Type; the Type Map (Exhibit 3.2) is an ILLUSTRATIVE companion that draws the
//   Town's road network color-coded by assigned Type. It is GENERATED FROM the
//   Inventory data — it is not separately adopted, and where the Map and the
//   Inventory differ, the Inventory governs (§5.C.4).
//
//   This renderer reads a JSON of segments (geometry + Type + the recorded
//   reference fields) and draws each segment as a polyline in its Type's color,
//   with a legend, inside Article-3 page chrome — the same rasterize/draw-and-
//   reseat pattern as district-maps.typ and cross-section-plates.typ.
//
// STATUS: the bundled data (source/exhibits/street-types/inventory-sample.json)
//   is SAMPLE/SCAFFOLD data — a tiny invented network, one segment per Type — so
//   the engine can be demonstrated. To produce the real Exhibit 3.2, point
//   --input data=... at a JSON of Newcastle's road centerlines + Type
//   classifications (see that file's _meta for the schema). Because the geometry
//   is auto-scaled to the page, any consistent coordinate units work; for the
//   real map use projected town coordinates (e.g. Maine State Plane) and it fits
//   to page with north up. NOT wired into the production build until real data
//   exists (so sample data never lands in a deliverable).
//
// Render the sample standalone (lands on a recto via even offset):
//   typst compile source/street-type-map.typ /tmp/type-map.pdf \
//     --root . --font-path style/fonts --input page_offset=2
//
// PARITY INVARIANT identical to the other native units: chrome keys off logical
// page = here().page() + page_offset; keep page_offset EVEN.
// =============================================================================

#let page_offset = int(sys.inputs.at("page_offset", default: "2"))
#let footer_date = sys.inputs.at("footer_date", default: "Draft")
#let data_path   = sys.inputs.at("data", default: "exhibits/street-types/inventory-sample.json")

// ---- This file IS Article 3 (mirrors district-maps.typ's hardcoded Article 1)
#let article_number = "3"
#let article_name = "Thoroughfares"

// ---- Palette (mirror of style/czc-colors.yml / czc-template.typ) ------------
#let article_blue    = rgb("#367AAC")
#let body_dark       = rgb("#231F20")
#let subsection_gray = rgb("#7C766F")
#let tab_gray        = rgb("#BFBFBF")
#let hair            = 0.5pt + subsection_gray

#let body_font = ("Barlow", "Helvetica Neue", "Helvetica")

// ---- Per-Type colors: a blue ramp for the Street family, an olive ramp for the
// Road family (echoing the cross-section plates: Streets blue, Roads olive).
#let TYPE_COLORS = (
  S1: rgb("#103E66"), S2: rgb("#2E6FA0"), S3: rgb("#4E97C8"), S4: rgb("#74B2D6"), S5: rgb("#9AC8E4"),
  R1: rgb("#3D4A1F"), R2: rgb("#5E6E33"), R3: rgb("#84934A"), R4: rgb("#A99A4B"), R5: rgb("#C2B777"),
)
#let TYPE_NAMES = (
  S1: "Main Street", S2: "Village Street", S3: "Neighborhood Street", S4: "Lane", S5: "Alley",
  R1: "Connector Road", R2: "Rural Road", R3: "Rural Lane", R4: "Highway Commercial", R5: "Rural Highway",
)
#let TYPE_ORDER = ("S1", "S2", "S3", "S4", "S5", "R1", "R2", "R3", "R4", "R5")

// Present use "Driveway" (§5.C.3.g) is NOT an eleventh Type — it records what a
// segment IS TODAY. A quiet neutral so it reads as "not a road" rather than
// competing with the two Type ramps. The Type each of these would take on
// conversion (§7.F) stays in Exhibit 3.1's "On conversion" column.
#let DRIVEWAY_COLOR = rgb("#A2988C")
#let is_driveway(s) = s.at("present_use", default: none) == "Driveway"

// ---- Page geometry (identical to czc-template.typ / district-maps.typ) -------
#set page(
  paper: "us-letter",
  margin: (inside: 90pt, outside: 44pt, top: 64pt, bottom: 56pt),
  header-ascent: 26pt,
  footer-descent: 28pt,
)
#set text(font: body_font, stretch: 75%, weight: "light", size: 8.5pt, fill: body_dark, lang: "en")
#set par(leading: 0.57em, spacing: 0.78em, justify: false, first-line-indent: 0pt)

// ---- Running head (Article name on the OUTER edge — mirror of district-maps) -
#set page(header: context {
  set text(size: 11pt, fill: subsection_gray, weight: "bold", stretch: 75%, tracking: 0.3pt)
  let pn = here().page() + page_offset
  let topic = upper(article_name)
  if calc.even(pn) { grid(columns: (auto, 1fr), align: (left, right), topic, []) }
  else { grid(columns: (1fr, auto), align: (left, right), [], topic) }
})

// ---- Footer (parity-aware, continuous page numbers) -------------------------
#set page(footer: context {
  set text(size: 10pt, weight: "bold", stretch: 75%, fill: body_dark)
  let pn = here().page() + page_offset
  let wordmark = text(fill: article_blue)[Newcastle Core Zoning Code]
  let pagenum = text(fill: body_dark)[#str(pn)]
  let separator = text(fill: body_dark)[ | ]
  let date_part = text(fill: article_blue)[#footer_date]
  if calc.even(pn) {
    grid(columns: (auto, 1fr, auto), align: (left, center, right),
      [#pagenum#separator#wordmark], [], date_part)
  } else {
    grid(columns: (auto, 1fr, auto), align: (left, center, right),
      date_part, [], [#wordmark#separator#pagenum])
  }
})

// ---- Article tab (ARTICLE 3) ------------------------------------------------
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
// DATA + projection
// =============================================================================
#let data = json(data_path)
#let segs = data.segments

// Collect all geometry points to find the bounding box.
#let xs = ()
#let ys = ()
#for s in segs { for p in s.geometry { xs.push(p.at(0)); ys.push(p.at(1)) } }
#let minx = calc.min(..xs)
#let maxx = calc.max(..xs)
#let miny = calc.min(..ys)
#let maxy = calc.max(..ys)
#let spanx = calc.max(maxx - minx, 0.0001)
#let spany = calc.max(maxy - miny, 0.0001)

// Map panel geometry. The drawing is fit-to-panel (preserving aspect) and
// centered; north is up (data y increases northward, screen y increases down,
// so we flip with maxy - y).
#let MAPW = 478pt
#let MAPH = 466pt
#let PAD = 18pt
#let scale = calc.min((MAPW - 2 * PAD) / spanx, (MAPH - 2 * PAD) / spany)
#let usedw = spanx * scale
#let usedh = spany * scale
#let offx = (MAPW - usedw) / 2
#let offy = (MAPH - usedh) / 2
#let project(p) = (offx + (p.at(0) - minx) * scale, offy + (maxy - p.at(1)) * scale)

// ---- The map panel ----------------------------------------------------------
#let map_panel = box(width: MAPW, height: MAPH, radius: 2pt,
  fill: rgb("#F7F9FB"), stroke: hair, clip: true, {
  // each segment as one Type-colored polyline
  for s in segs {
    // A segment may be unclassified (type null/pending) — draw it gray.
    let t = if s.type == none { "" } else { s.type }
    let col = if is_driveway(s) { DRIVEWAY_COLOR }
              else { TYPE_COLORS.at(t, default: subsection_gray) }
    let pts = s.geometry.map(project)
    place(top + left, curve(stroke: 2.6pt + col,
      curve.move(pts.at(0)),
      ..pts.slice(1).map(p => curve.line(p)),
    ))
  }
  // north arrow (top-right)
  place(top + right, dx: -10pt, dy: 8pt,
    text(fill: subsection_gray, weight: "bold", size: 9pt)[N #box(baseline: 1pt, text(size: 11pt)[\u{2191}])])
})

// ---- Legend -----------------------------------------------------------------
// Only the Types actually present, in canonical order, two columns.
// A segment recorded as a driveway is drawn as D, so it must not also make its
// conversion Type appear "present" in the legend — the legend describes what the
// map actually shows.
#let present = TYPE_ORDER.filter(t => segs.any(s => s.type == t and not is_driveway(s)))
#let has_unclassified = segs.any(s => (s.type == none or not (s.type in TYPE_ORDER))
                                      and not is_driveway(s))
#let n_driveways = segs.filter(is_driveway).len()
#let legend_cell(code) = box(inset: (y: 2.5pt))[
  #box(baseline: -1.5pt, rect(width: 18pt, height: 3.5pt, radius: 1pt,
    fill: TYPE_COLORS.at(code), stroke: none))
  #h(6pt)#text(size: 8.5pt, fill: body_dark)[#text(weight: "bold")[#code] #h(2pt) #TYPE_NAMES.at(code)]
]
#let legend = block(above: 12pt, below: 0pt, {
  text(fill: subsection_gray, weight: "bold", size: 9pt, tracking: 0.3pt)[TYPE LEGEND]
  v(2pt, weak: true)
  line(length: 100%, stroke: hair)
  v(4pt, weak: true)
  grid(columns: (1fr, 1fr), column-gutter: 24pt, row-gutter: 0pt,
    ..present.map(legend_cell))
  if n_driveways > 0 {
    box(inset: (y: 2.5pt))[
      #box(baseline: -1.5pt, rect(width: 18pt, height: 3.5pt, radius: 1pt,
        fill: DRIVEWAY_COLOR, stroke: none))
      #h(6pt)#text(size: 8.5pt, fill: body_dark)[#text(weight: "bold")[D] #h(2pt)
        Driveway today — no Street or Road standard applies (§7.C.8)]]
  }
  if has_unclassified {
    box(inset: (y: 2.5pt))[
      #box(baseline: -1.5pt, rect(width: 18pt, height: 3.5pt, radius: 1pt,
        fill: subsection_gray, stroke: none))
      #h(6pt)#text(size: 8.5pt, fill: body_dark)[Unclassified — pending District classification]]
  }
})

// =============================================================================
// RENDER (single page exhibit)
// =============================================================================
// EXHIBIT caption — same style as the Article-1 District Map exhibits.
#block(above: 0pt, below: 9pt,
  text(fill: subsection_gray, weight: "bold", stretch: 75%, size: 11pt, tracking: 0.3pt)[
    EXHIBIT 3.2#h(0.85em)THOROUGHFARE TYPE MAP])

#map_panel

#legend

#let banner = data.at("_meta", default: (:)).at("banner",
  default: "Sample data shown — not Newcastle's adopted network.")
#block(above: 11pt, text(fill: subsection_gray, size: 7.5pt, style: "italic")[
  Illustrative companion to the Inventory of Existing Thoroughfares (Exhibit 3.1, §5.C),
  generated from the Inventory and provided for convenience. The Type assignment shown is the
  governing classification (§5.C.2) and requires no work on any existing thoroughfare or driveway
  (§1.B.5). Segments drawn as #text(weight: "bold")[D] serve today as driveways and no Street or
  Road standard applies to them (§7.C.8); the Type each would take on conversion is listed in
  Exhibit 3.1. Where this Map and the Inventory differ, the Inventory governs.
  #text(weight: "bold")[#banner]])
