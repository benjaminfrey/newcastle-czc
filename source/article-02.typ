// =============================================================================
// Newcastle CZC — Article 2 District Standards (NATIVE TYPST renderer)
// =============================================================================
//
// Why this file exists:
//   The district pages of the baseline CZC are NOT a linear two-column flow.
//   Each district is a fixed 2-page SPREAD — a verso "standards" page (badge +
//   banner, two designated columns of standards, a full-width PERMITTED
//   BUILDINGS matrix) and a recto "use-matrix" page (three columns of use
//   categories with per-use status glyphs, a legend, and use standards).
//   Pandoc/markdown cannot express that layout, so Article 2 is rendered
//   natively in Typst from structured per-district data.
//
// All visual values are MEASURED from docs/Newcastle Core Zoning Code.pdf
//   (pp. 12-13 = D1 spread). See style/style-analysis.md.
//
// Render standalone (D1 slice as baseline pp. 12-13; blank lead = p. 11):
//   typst compile source/article-02.typ /tmp/a2/a2.pdf \
//     --font-path style/fonts --input page_offset=10
//
// Build integration passes the real cumulative page-offset + footer date:
//   --input page_offset=<N> --input footer_date="Draft v0.4.x-draft"
//
// PARITY INVARIANT (critical): Typst keys its inside/outside MARGINS off the
//   PHYSICAL page index (physical page 1 = recto, left margin = inside = 90pt).
//   The chrome here (badge/banner/header/footer/tab) keys off the LOGICAL page
//   number = here().page() + page_offset. For the two to agree, page_offset
//   MUST BE EVEN. The render loop then lands the FIRST district on a physical-
//   even (verso) page via `pagebreak(to:"even")`, so a district's standards
//   page is a left/verso page (badge at the LEFT fore-edge) exactly as in the
//   baseline. An odd offset shifts the band into the inside margin (the badge
//   ends up at x=90pt instead of x=44pt) — do not use one.
// =============================================================================

// ---- Inputs (with standalone defaults) --------------------------------------
// Default offset 10 (EVEN): with the leading `pagebreak(to:"even")` the blank
// pad becomes p. 11 and D1's standards page lands on verso p. 12 (recto p. 13).
#let page_offset = int(sys.inputs.at("page_offset", default: "10"))
#let footer_date = sys.inputs.at("footer_date", default: "Draft")

// ---- Color palette (mirror of style/czc-colors.yml) -------------------------
#let article_blue    = rgb("#367AAC")
#let body_dark       = rgb("#231F20")
#let subsection_gray = rgb("#7C766F")
#let tab_gray        = rgb("#BFBFBF")
#let rule_dark       = rgb("#231F20")
#let hair            = 0.4pt + rule_dark

// ---- Fonts ------------------------------------------------------------------
#let body_font  = ("Barlow", "Helvetica Neue", "Helvetica")
// Symbol fallback for the four use-status glyphs (Barlow lacks them).
#let glyph_font = ("Apple Symbols", "Arial Unicode MS")

// ---- Page geometry (identical to style/czc-template.typ) --------------------
#set page(
  paper: "us-letter",
  margin: (inside: 90pt, outside: 44pt, top: 64pt, bottom: 56pt),
  header-ascent: 26pt,
  footer-descent: 28pt,
)

#set text(
  font: body_font, stretch: 75%, weight: "light",
  size: 8.5pt, fill: body_dark, lang: "en",
)
#set par(leading: 0.57em, spacing: 0.78em, justify: false, first-line-indent: 0pt)

#set enum(indent: 0.6em, body-indent: 0.6em, spacing: 0.5em, tight: false)

// ---- Running head (district-page two-part label) ----------------------------
// Baseline: "DISTRICT STANDARDS" (bold) hugs the OUTER (fore-edge) end; the
// group label ("Core Zoning Districts" / "Special Zoning Districts") sits at a
// FIXED inner tab stop with a small 6-bar mark between. We carry the current
// group in a state so the header can read it.
#let group_state = state("district-group", "Core Zoning Districts")

// Header inter-label separator: NOT a pipe. The baseline draws a small stack of
// 6 short gray bars here (a recurring CZC motif), MEASURED at ~3pt wide × ~9pt
// tall in #7c766f (vector, no text span). Reproduce it as stacked filled boxes.
#let header_sep = box(
  stack(dir: ttb, spacing: 1.1pt,
    ..range(6).map(_ => box(width: 3pt, height: 0.7pt, fill: subsection_gray))))

// MEASURED fixed tab stops, distance from the fore-edge: the 6-bar mark's near
// edge sits 125.5pt in; the inner (group) label's near edge sits 145pt in. These
// are CONSTANT across every district (verso inner x0=189, recto inner x1=423).
#let HEAD_MARK = 125.5pt
#let HEAD_INNER = 145pt

#set page(header: context {
  // Physical page 1 is always the leading parity-blank inserted by the
  // `pagebreak(to:"even")` at the start of the render (it lands D1 on a verso).
  // Keep that page a TRUE blank — no header/footer/tab — so it reads as a clean
  // section break, not a chrome-bearing empty page.
  if here().page() == 1 { return [] }
  let pn = here().page() + page_offset
  let grp = group_state.get()
  // MEASURED: outer label 11pt bold #7C766F; inner label 10pt bold #7C766F
  // (same gray, NOT a lighter tint); both BentonSansCond-Bold => stretch 75%.
  // tracking 1.35pt widens the (narrower) Barlow condensed face to the baseline's
  // BentonSansCond width (~104pt: x 45→149) so the gap to the mark matches too.
  let outer = text(fill: subsection_gray, weight: "bold", size: 11pt, tracking: 1.35pt)[DISTRICT STANDARDS]
  let inner = text(fill: subsection_gray, weight: "bold", size: 10pt, tracking: 0.2pt, grp)
  if calc.even(pn) {
    // verso: fore-edge = LEFT. outer flush left | mark @125.5 | inner @145.
    grid(columns: (HEAD_MARK, HEAD_INNER - HEAD_MARK, 1fr),
      align: (left + horizon, left + horizon, left + horizon),
      outer, header_sep, inner)
  } else {
    // recto: fore-edge = RIGHT (mirror). inner | mark | outer flush right.
    grid(columns: (1fr, HEAD_INNER - HEAD_MARK, HEAD_MARK),
      align: (right + horizon, right + horizon, right + horizon),
      inner, header_sep, outer)
  }
})

// ---- Footer (parity-aware, continuous page numbers) -------------------------
#set page(footer: context {
  if here().page() == 1 { return [] }   // leading parity-blank: no footer
  set text(size: 10pt, weight: "bold", stretch: 75%, fill: body_dark)
  let pn = here().page() + page_offset
  let wordmark = text(fill: article_blue)[Newcastle Core Zoning Code]
  let pagenum = text(fill: body_dark)[#str(pn)]
  // MEASURED footer separator: a real pipe in dark, with wide spacing ('   |    ').
  let sep = text(fill: body_dark)[#h(7pt)|#h(7pt)]
  let date_part = text(fill: article_blue)[#footer_date]
  if calc.even(pn) {
    grid(columns: (auto, 1fr, auto), align: (left, center, right),
      [#pagenum#sep#wordmark], [], date_part)
  } else {
    grid(columns: (auto, 1fr, auto), align: (left, center, right),
      date_part, [], [#wordmark#sep#pagenum])
  }
})

// ---- Article tab (gray rotated marker in the outer margin) ------------------
#let article_tab_box = rotate(-90deg, reflow: true,
  box(fill: tab_gray, width: 72pt, height: 30pt, inset: (x: 6pt, y: 0pt),
    align(center + horizon,
      text(fill: white, weight: "bold", stretch: 75%, size: 14pt, tracking: 0.5pt)[ARTICLE 2])))

#set page(background: context {
  if here().page() == 1 { return [] }   // leading parity-blank: no article tab
  let pn = here().page() + page_offset
  if calc.even(pn) { place(top + left, dy: 139.5pt, article_tab_box) }
  else { place(top + right, dy: 139.5pt, article_tab_box) }
})

// =============================================================================
// District spread components
// =============================================================================

// ---- Badge + banner band (full text-block width) ----------------------------
// MEASURED (D1 verso): band top y≈67pt, height≈41.5pt; badge ≈46pt square at
// the OUTER edge; ≈8pt white gap; banner fills to the inner margin. Badge text
// ("D1") and banner text ("RURAL") are both ≈19pt, vertically centered; badge
// bold+centered, banner left-inset ≈15pt (right-inset on recto).
#let band_h = 41.5pt
#let badge_w = 46pt
#let gap_w = 8pt

#let district_band(d) = context {
  let pn = here().page() + page_offset
  let fill_c = rgb(d.color)
  let text_c = rgb(d.band_text)
  // MEASURED: badge "D1" and banner "RURAL" are both BentonSans-Regular (NON-
  // condensed) 19pt — stretch 100% selects the non-condensed Barlow faces now
  // bundled in style/fonts (the body default stretch 75% picks the condensed).
  let band_text(s) = text(fill: text_c, font: body_font, weight: "regular",
    stretch: 100%, size: 19pt)[#s]
  let badge = box(fill: fill_c, width: badge_w, height: band_h, inset: 0pt,
    align(center + horizon, band_text(d.code)))
  let verso = calc.even(pn)
  let name = box(fill: fill_c, height: band_h, width: 100%,
    inset: (left: if verso { 15pt } else { 0pt }, right: if verso { 0pt } else { 15pt }),
    align((if verso { left } else { right }) + horizon, band_text(upper(d.name))))
  if verso {
    grid(columns: (badge_w, gap_w, 1fr), rows: band_h, badge, [], name)
  } else {
    grid(columns: (1fr, gap_w, badge_w), rows: band_h, name, [], badge)
  }
}

// ---- Panel heading (gray bold uppercase + under-rule) -----------------------
// `above` opens the inter-section gap before each heading; MEASURED baseline
// table→heading gaps run ~24-29pt (mine were ~20 with above:11). `below` is the
// rule→table gap; kept tight so heading→first-row ≈ baseline 14.5pt.
#let panel(title, above: 17pt) = block(above: above, below: 3.5pt, breakable: false, {
  text(fill: subsection_gray, weight: "bold", size: 9pt, tracking: 0.3pt)[#upper(title)]
  v(2.5pt, weak: true)
  line(length: 100%, stroke: hair)
})

// ---- Label / value mini-table (row hairlines) -------------------------------
// inset y 3.75pt => ~13.5pt row pitch (MEASURED baseline lvtable pitch).
// Stroke is BOTTOM-only: the heading's panel() already draws the line() that
// serves as the rule under the heading (i.e. the table's top edge). Adding a
// cell `top` here would stack a SECOND hairline ~3.5pt below it — the "double
// rule" the baseline never shows. Bottom on every cell still yields the
// inter-row hairlines and the table's closing bottom rule.
#let lvtable(rows) = table(
  columns: (1.15fr, 1fr),
  stroke: (x, y) => (bottom: hair),
  inset: (x: 0pt, y: 3.75pt),
  align: (left + horizon, left + horizon),
  ..rows.map(r => (r.at(0), r.at(1))).flatten()
)

// ---- Full-width PERMITTED BUILDINGS matrix ----------------------------------
// MEASURED: every cell (column headers, row labels, values) is Light body weight
// — NOT bold/medium. inset y 4.25pt => ~14.5pt row pitch (looser than lvtable).
// BOTTOM-only stroke (see lvtable): the panel() line() is the rule under the
// heading, so a cell `top` would double it.
#let permitted_buildings(m) = table(
  columns: (1.6fr,) + (1fr,) * m.cols.len(),
  stroke: (x, y) => (bottom: hair),
  inset: (x: 4pt, y: 4.25pt),
  align: left + horizon,
  table.header([], ..m.cols.map(c => [#c])),
  ..m.rows.map(r => ([#r.at(0)], ..r.slice(1))).flatten()
)

// ---- Use-status glyph -------------------------------------------------------
#let glyphs = (u: "●", rc: "❶", sp: "❷", ex: "✪")
// A cell may carry MORE THAN ONE status. The adopted Code marks "Retail &
// Service, General" in D3 Neighborhood Business with both the Residential
// Companion symbol and the Special Permit symbol, i.e. CEO and Planning Board.
// Codes are space-separated ("rc sp"); a single code behaves exactly as before.
#let status(code) = {
  if code == none or code == "" { return [] }
  text(font: glyph_font, fill: body_dark, size: 8pt,
       code.split(" ").map(c => glyphs.at(c)).join(h(2pt)))
}

// ---- One use category (heading + under-rule + use rows, no row rules) --------
#let usecat(c) = block(breakable: false, above: 9pt, below: 0pt, {
  text(fill: subsection_gray, weight: "bold", size: 8.2pt, tracking: 0.3pt)[#upper(c.title)]
  v(2pt, weak: true)
  line(length: 100%, stroke: hair)
  v(2.5pt, weak: true)
  table(
    columns: (1fr, auto), stroke: none, inset: (x: 0pt, y: 1.7pt),
    align: (left + horizon, right + horizon),
    ..c.entries.map(e => (e.at(0), status(e.at(1)))).flatten()
  )
})

// ---- A full use column (stack of categories) --------------------------------
// The left vertical divider is drawn by the enclosing grid (so all columns
// share a single full-matrix-height rule), not per-column.
#let usecolumn(cats) = { for c in cats { usecat(c) } }

// ---- Panel renderers (kind-dispatched) --------------------------------------
// A list body is an array whose elements are either a plain string (flat item)
// or a dict {text, sub:(...)} (an item carrying a nested a/b/c sub-list).
#let render_list(items) = enum(..items.map(it => {
  if type(it) == dictionary {
    [#it.text#if it.sub.len() > 0 { enum(numbering: "a.", ..it.sub.map(s => [#s])) }]
  } else {
    [#it]
  }
}))

// One verso panel: heading + body, dispatched on kind. `first` suppresses the
// inter-panel gap above a column's first heading (the band already set the gap).
#let render_panel(p, first: false) = {
  panel(p.title, above: if first { 0pt } else { 17pt })
  if p.kind == "lv" { lvtable(p.body) }
  else if p.kind == "list" { render_list(p.body) }
  else { [#p.body] }   // "para"
}

// =============================================================================
// District spread (2 pages): verso standards + recto use matrix
// =============================================================================
#let district(d) = {
  group_state.update(d.group)

  // ----- Page 1 (verso): standards -----
  district_band(d)
  v(13pt)

  // Verso body runs at stretch 80% (vs the global 75%): Barlow at 75% is a touch
  // narrower than the baseline's BentonSansCond, so paragraphs wrapped one line
  // short and the column crept upward. 80% matches the baseline wrap (e.g. the
  // D1 DESCRIPTION breaks to 7 lines, as in the original). Scoped to this block
  // so the tuned chrome (header/footer/band) and the tight recto use columns
  // keep their 75% width.
  {
    set text(stretch: 80%)
    // Panels come pre-ordered per column straight from the baseline, so the
    // renderer is structure-agnostic (Conservation has 1 right panel; Campus and
    // Marine have a single "Building Placement"; D6 a 4-column matrix; etc.).
    grid(columns: (1fr, 1fr), column-gutter: 44pt,
      { for (i, p) in d.left.enumerate() { render_panel(p, first: i == 0) } },
      { for (i, p) in d.right.enumerate() { render_panel(p, first: i == 0) } },
    )

    // Full-width PERMITTED BUILDINGS matrix (absent in Conservation/Campus/Marine).
    if d.matrix != none {
      panel(d.matrix.title)
      permitted_buildings(d.matrix)
    }
  }

  pagebreak()

  // ----- Page 2 (recto): use matrix -----
  district_band(d)
  v(9pt)

  // Three EQUAL columns (1fr each) for a balanced spread. The two inter-column
  // dividers are drawn at the GRID level so each spans the full matrix height
  // (the tallest column), rather than per-column boxes that would each stop at
  // their own content's end. Insets supply 11pt+11pt of breathing room on either
  // side of each hairline (≈ a 22pt gutter) — wider separation between col1↔col2
  // and col2↔col3 than the old layout.
  grid(columns: (1fr, 1fr, 1fr),
    stroke: (x, y) => if x > 0 { (left: hair) },
    inset: (x, y) => (left: if x > 0 { 11pt } else { 0pt },
                      right: if x < 2 { 11pt } else { 0pt }),
    usecolumn(d.use_col1),
    usecolumn(d.use_col2),
    // col 3: legend + use standards (divider/inset now supplied by the grid)
    {
      text(fill: subsection_gray, weight: "bold", size: 9pt, tracking: 0.3pt)[USE TABLE LEGEND]
      v(2pt, weak: true)
      line(length: 100%, stroke: hair)
      v(2.5pt, weak: true)
      table(columns: (auto, 1fr, auto), stroke: none,
        inset: (x: 0pt, y: 2.6pt), column-gutter: (5pt, 0pt),
        align: (center + horizon, left + horizon, right + horizon),
        status("u"), [Use Permit Required], [CEO],
        status("rc"), [Residential Companion Permit Required], [CEO],
        status("sp"), [Special Permit Required], [Planning Board],
        status("ex"), [Expanded Use Permit Required], [Planning Board],
      )
      v(2pt)
      text(size: 8pt)[Note: Uses without #status("u"), #status("rc"), #status("sp"), or #status("ex") are not allowed in this District]

      if d.use_standards.title != none {
        panel(d.use_standards.title)
        if d.use_standards.items.len() > 0 { render_list(d.use_standards.items) }
      }
    },
  )
  // NB: no trailing parity break. Invariant: each district is exactly 2 pages,
  // so once the first district lands on a global-even (verso) page, every
  // subsequent district does too. The render loop inserts a single page break
  // BETWEEN districts; alignment of the FIRST district is handled once, before
  // the loop (a no-op for the standalone slice, which already starts even).
}

// =============================================================================
// DISTRICT DATA  —  generated by extract/gen_districts.py straight from the
// baseline PDF (all 13 spreads: D1-D6 + 7 Special Districts). String colors are
// converted to rgb() at render time. Regenerate after any extractor change:
//     python3 extract/gen_districts.py
// =============================================================================
#let districts = json("article-02-data.json")

// =============================================================================
// RENDER
// =============================================================================
// The FIRST district's standards page must land on a verso (even DISPLAYED page)
// so its badge sits at the LEFT fore-edge (see PARITY INVARIANT above). D1 is this
// unit's first page; the integrated build pads to an ODD running page-offset before
// this unit, so D1 renders at an even displayed page (offset+1) with NO leading
// blank. (A previous `#pagebreak(to:"even")` here, combined with the build's even
// pad, produced two redundant blank pages — removed.) Each district is exactly two
// pages, so every subsequent district inherits parity.
#for (i, d) in districts.enumerate() {
  if i > 0 { pagebreak() }
  district(d)
}
