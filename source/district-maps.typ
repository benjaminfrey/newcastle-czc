// =============================================================================
// Newcastle CZC — Article 1 DISTRICT MAP EXHIBITS (NATIVE TYPST renderer)
// =============================================================================
//
// Why this file exists:
//   The baseline CZC closes Article 1 with three full-page zoning exhibits —
//   EXHIBIT 1.1 District Map (whole town), 1.2 District Map Inset (Newcastle
//   Town Center) and 1.4 District Map Inset (Sheepscot Village). Each is a GIS
//   composite: hundreds of vector zoning polygons / road / boundary paths laid
//   over a sliced-JPEG aerial basemap, with a KEY legend, scale bar, compass
//   rose and the "Northern Geomantics" credit. That is not faithfully
//   redrawable in markup, so each exhibit's content region was rasterized at
//   300 DPI from the baseline (its native basemap resolution — no upscaling)
//   into source/exhibits/district-maps/*.png, with the baseline's own page
//   chrome (header / footer / side tab / EXHIBIT caption) cropped away. This
//   file re-seats those clean map rasters inside OUR Article-1 page chrome, the
//   same rasterize-and-reseat pattern used for the Article-2 district spreads
//   (article-02.typ) and the Article-3 Type plates (cross-section-plates.typ),
//   so a map reads as a torn-out page of the same code.
//
// Render the three exhibits standalone (1.1 lands on a recto via even offset):
//   typst compile source/district-maps.typ /tmp/maps.pdf \
//     --root . --font-path style/fonts --input page_offset=2
//
// Build integration passes the cumulative page-offset + footer date. PARITY
// INVARIANT identical to article-02.typ / cross-section-plates.typ: chrome keys
// off logical page = here().page() + page_offset; keep page_offset EVEN so each
// exhibit's parity (verso/recto) matches its eventual position in the document.
// At offset 2 the three pages land recto / verso / recto — the baseline's own
// 1.1 / 1.2 / 1.4 sequence.
// =============================================================================

#let page_offset = int(sys.inputs.at("page_offset", default: "2"))
#let footer_date = sys.inputs.at("footer_date", default: "Draft")

// ---- This file IS Article 1 (hardcoded, mirrors the plates' "ARTICLE 3") ----
#let article_number = "1"
#let article_name = "General Standards"

// ---- Palette (mirror of style/czc-colors.yml / czc-template.typ) ------------
#let article_blue    = rgb("#367AAC")
#let body_dark       = rgb("#231F20")
#let subsection_gray = rgb("#7C766F")
#let tab_gray        = rgb("#BFBFBF")

#let body_font = ("Barlow", "Helvetica Neue", "Helvetica")

// ---- Page geometry (identical to czc-template.typ / article-02.typ) ----------
#set page(
  paper: "us-letter",
  margin: (inside: 90pt, outside: 44pt, top: 64pt, bottom: 56pt),
  header-ascent: 26pt,
  footer-descent: 28pt,
)
#set text(font: body_font, stretch: 75%, weight: "light", size: 8.5pt, fill: body_dark, lang: "en")
#set par(leading: 0.57em, spacing: 0.78em, justify: false, first-line-indent: 0pt)

// ---- Running head (mirror of czc-template.typ: Article name on OUTER edge) ---
#set page(header: context {
  set text(size: 11pt, fill: subsection_gray, weight: "bold", stretch: 75%, tracking: 0.3pt)
  let pn = here().page() + page_offset
  let topic = upper(article_name)
  if calc.even(pn) {
    grid(columns: (auto, 1fr), align: (left, right), topic, [])
  } else {
    grid(columns: (1fr, auto), align: (left, right), [], topic)
  }
})

// ---- Footer (parity-aware, continuous page numbers — czc-template.typ) -------
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

// ---- Article tab (Article 1, mirror of czc-template.typ) --------------------
#let article_tab_box = rotate(-90deg, reflow: true,
  box(fill: tab_gray, width: 72pt, height: 30pt, inset: (x: 6pt, y: 0pt),
    align(center + horizon,
      text(fill: white, weight: "bold", stretch: 75%, size: 14pt, tracking: 0.5pt)[ARTICLE #article_number])))
#set page(background: context {
  let pn = here().page() + page_offset
  if calc.even(pn) { place(top + left, dy: 139.5pt, article_tab_box) }
  else { place(top + right, dy: 139.5pt, article_tab_box) }
})

// ---- One exhibit page -------------------------------------------------------
// Caption matches the baseline: BentonSansCond-Bold 11pt #7C766F (our Barlow
// 75%-bold gray stand-in), left-aligned at the text-block edge, sitting at the
// top of the body (~y65). The map raster fills the remaining body height,
// fit:"contain" so it never overflows to a second page (which would break the
// 3-page count and the document parity). Aspect ≈ 0.64 (w/h) so a height-fit
// map is ~410pt wide, centered in the 478pt text block.
#let map_page(num, title, img) = {
  block(above: 0pt, below: 10pt,
    text(fill: subsection_gray, weight: "bold", stretch: 75%, size: 11pt, tracking: 0.3pt)[
      EXHIBIT #num#h(0.85em)#upper(title)])
  block(above: 0pt, below: 0pt,
    box(width: 100%, height: 640pt,
      align(center + horizon, image(img, fit: "contain", width: 100%, height: 100%))))
}

// =============================================================================
// RENDER
// =============================================================================
// Baseline exhibit numbering skips 1.3 (no such exhibit exists in the baseline).
#let maps = (
  ("1.1", "District Map", "exhibits/district-maps/exhibit-1.1-district-map.png"),
  ("1.2", "District Map Inset - Newcastle Town Center", "exhibits/district-maps/exhibit-1.2-town-center.png"),
  ("1.4", "District Map Inset - Sheepscot Village", "exhibits/district-maps/exhibit-1.4-sheepscot-village.png"),
)

#for (i, m) in maps.enumerate() {
  if i > 0 { pagebreak() }
  map_page(m.at(0), m.at(1), m.at(2))
}
