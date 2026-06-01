// =============================================================================
// Newcastle CZC — Article 3 Street/Road Type PLATES (NATIVE TYPST renderer)
// =============================================================================
//
// Why this file exists:
//   Each numbered Street/Road Type (S1…S5, R1…R5) gets its own full-page
//   plate: a code badge + name banner (the Article 2 district-band chrome), a
//   column-spanning Streetmix-style cross-section graphic (built by
//   build/build-cross-sections.py -> source/exhibits/cross-sections/<CODE>.svg),
//   a CC BY-SA credit line, and a compact Design Standards strip drawn from each
//   Type's `standards` block in types.json. Each plate IS that Type's one-stop
//   page (description + standards + character), seated inside Article 3 §2 — they
//   replace the former §2.D–§2.M per-Type prose subsections, mirroring the
//   District pages of Article 2.
//
// Shares ALL visual tokens + page geometry + parity-aware chrome with
// source/article-02.typ so a plate reads as a torn-out page of the same code.
//
// Render the S1 slice standalone (lands on a verso page via even offset):
//   typst compile source/cross-section-plates.typ /tmp/plates/s1.pdf \
//     --root . --font-path style/fonts --input only=S1 --input page_offset=30
//
// Build integration passes the cumulative page-offset + footer date and the
// ordered subset to emit. PARITY INVARIANT identical to article-02.typ: chrome
// keys off logical page = here().page() + page_offset; keep page_offset EVEN so
// a plate's parity (verso/recto) matches its eventual position in the document.
// =============================================================================

#let page_offset = int(sys.inputs.at("page_offset", default: "30"))
#let footer_date = sys.inputs.at("footer_date", default: "Draft")
// Comma-separated subset to render, in order; empty => all Types in types.json.
#let only = sys.inputs.at("only", default: "")

// ---- Palette (mirror of style/czc-colors.yml / article-02.typ) --------------
#let article_blue    = rgb("#367AAC")
#let body_dark       = rgb("#231F20")
#let subsection_gray = rgb("#7C766F")
#let tab_gray        = rgb("#BFBFBF")
#let rule_dark       = rgb("#231F20")
#let hair            = 0.4pt + rule_dark
#let street_color    = rgb("#367AAC")   // Streets: article blue
#let road_color      = rgb("#6E7B3D")   // Roads: muted olive (rural)

#let body_font = ("Barlow", "Helvetica Neue", "Helvetica")

// ---- Page geometry (identical to article-02.typ / czc-template.typ) ---------
#set page(
  paper: "us-letter",
  margin: (inside: 90pt, outside: 44pt, top: 64pt, bottom: 56pt),
  header-ascent: 26pt,
  footer-descent: 28pt,
)
#set text(font: body_font, stretch: 75%, weight: "light", size: 8.5pt, fill: body_dark, lang: "en")
#set par(leading: 0.57em, spacing: 0.78em, justify: false, first-line-indent: 0pt)

// ---- Running head (mirror of article-02.typ; Article 3 wording) -------------
#let header_sep = box(stack(dir: ttb, spacing: 1.1pt,
  ..range(6).map(_ => box(width: 3pt, height: 0.7pt, fill: subsection_gray))))
#let HEAD_MARK = 125.5pt
#let HEAD_INNER = 145pt

#set page(header: context {
  let pn = here().page() + page_offset
  // Group label (Street Types / Road Types). A state updated in the plate body
  // lags by one page in page headers — Typst resolves the body update AFTER the
  // header queries it — which mislabels the first plate and the Street->Road
  // transition page. Instead read page-anchored <plate-group> markers and take
  // the last one on or before this physical page: lag-free, and still correct
  // when a single Type is rendered standalone (only=...).
  let marks = query(<plate-group>)
  let grp = "Street & Road Types"
  for m in marks { if m.location().page() <= here().page() { grp = m.value } }
  let outer = text(fill: subsection_gray, weight: "bold", size: 11pt, tracking: 1.35pt)[STREET & ROAD TYPES]
  let inner = text(fill: subsection_gray, weight: "bold", size: 10pt, tracking: 0.2pt, grp)
  if calc.even(pn) {
    grid(columns: (HEAD_MARK, HEAD_INNER - HEAD_MARK, 1fr),
      align: (left + horizon, left + horizon, left + horizon),
      outer, header_sep, inner)
  } else {
    grid(columns: (1fr, HEAD_INNER - HEAD_MARK, HEAD_MARK),
      align: (right + horizon, right + horizon, right + horizon),
      inner, header_sep, outer)
  }
})

// ---- Footer (parity-aware, continuous page numbers) -------------------------
#set page(footer: context {
  set text(size: 10pt, weight: "bold", stretch: 75%, fill: body_dark)
  let pn = here().page() + page_offset
  let wordmark = text(fill: article_blue)[Newcastle Core Zoning Code]
  let pagenum = text(fill: body_dark)[#str(pn)]
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

// ---- Article tab (Article 3) ------------------------------------------------
#let article_tab_box = rotate(-90deg, reflow: true,
  box(fill: tab_gray, width: 72pt, height: 30pt, inset: (x: 6pt, y: 0pt),
    align(center + horizon,
      text(fill: white, weight: "bold", stretch: 75%, size: 14pt, tracking: 0.5pt)[ARTICLE 3])))
#set page(background: context {
  let pn = here().page() + page_offset
  if calc.even(pn) { place(top + left, dy: 139.5pt, article_tab_box) }
  else { place(top + right, dy: 139.5pt, article_tab_box) }
})

// ---- Badge + banner band (reused from article-02.typ) -----------------------
#let band_h = 41.5pt
#let badge_w = 46pt
#let gap_w = 8pt
#let type_band(code, name, fill_c) = context {
  let pn = here().page() + page_offset
  let band_text(s) = text(fill: white, font: body_font, weight: "regular", stretch: 100%, size: 19pt)[#s]
  let badge = box(fill: fill_c, width: badge_w, height: band_h, inset: 0pt,
    align(center + horizon, band_text(code)))
  let verso = calc.even(pn)
  let nm = box(fill: fill_c, height: band_h, width: 100%,
    inset: (left: if verso { 15pt } else { 0pt }, right: if verso { 0pt } else { 15pt }),
    align((if verso { left } else { right }) + horizon, band_text(upper(name))))
  if verso { grid(columns: (badge_w, gap_w, 1fr), rows: band_h, badge, [], nm) }
  else { grid(columns: (1fr, gap_w, badge_w), rows: band_h, nm, [], badge) }
}

// ---- Panel heading (gray bold uppercase + under-rule) -----------------------
#let panel(title, above: 17pt) = block(above: above, below: 3.5pt, breakable: false, {
  text(fill: subsection_gray, weight: "bold", size: 9pt, tracking: 0.3pt)[#upper(title)]
  v(2.5pt, weak: true)
  line(length: 100%, stroke: hair)
})

// ---- Standards strip: one row per standard, Type standard + Build to ---------
// Three columns: the item, the Type standard (the authorized range/option, set
// gray as reference) and the Build-To Standard (the value to construct, dark +
// bold). Art. 3 §3.C. Build to the right-hand column; on fixed/reference rows
// (design speed, sight distance, "Per MaineDOT", …) the two columns coincide.
// Each standards row in types.json is a [label, type-standard, build-to] triple.
#let standards_strip(rows) = {
  let sz = 7.5pt
  let head(s) = text(fill: subsection_gray, weight: "bold", size: 6pt, tracking: 0.4pt)[#upper(s)]
  let cells = (head(""), head("Type standard"), head("Build to"))
  for r in rows {
    cells.push(text(fill: subsection_gray, weight: "regular", size: sz)[#r.at(0)])
    cells.push(text(fill: subsection_gray, weight: "regular", size: sz)[#r.at(1)])
    cells.push(text(fill: body_dark, weight: "bold", size: sz)[#r.at(2)])
  }
  table(
    columns: (auto, 1fr, 1fr),
    // BOTTOM-only stroke: the panel("Design Standards") line() above is the rule
    // under the heading (this table's top edge). A cell `top` would stack a
    // second hairline ~3.5pt below it (the "double rule" bug). Bottom on every
    // cell keeps the header/row separators and the closing bottom rule.
    stroke: (x, y) => (bottom: hair),
    inset: (x: 6pt, y: 2pt),
    align: left + horizon,
    ..cells,
  )
}

// ---- One plate (single page) ------------------------------------------------
#let plate(t) = {
  let fam = t.family
  // Page-anchored group marker for the running head (read in the header via
  // query(<plate-group>)); avoids the one-page state lag of page headers.
  [#metadata(if fam == "ROAD" { "Road Types" } else { "Street Types" })<plate-group>]
  let fill_c = if fam == "ROAD" { road_color } else { street_color }

  type_band(t.code, t.name, fill_c)
  v(6pt)

  // Context kicker line.
  block(above: 0pt, below: 8pt,
    text(fill: subsection_gray, size: 9pt, weight: "regular", tracking: 0.2pt)[
      #upper(fam) TYPE · #t.context])

  // Regulatory description — the authoritative page text rolled on from the
  // former §2 prose subsection. Reads as body prose; the TARGET DISTRICTS and
  // CHARACTER columns below carry the scannable specifics without restating it.
  block(above: 0pt, below: 9pt, text(fill: body_dark, size: 8.5pt)[#t.description])

  // Optional Type-specific cross-reference (shopfront / state-aid), set off with
  // a colored left bar in the Type's family color.
  if "note" in t {
    block(above: 0pt, below: 11pt, width: 100%,
      inset: (left: 9pt, top: 1pt, bottom: 1pt),
      stroke: (left: 2pt + fill_c),
      text(fill: body_dark, size: 8pt, style: "italic")[#t.note])
  }

  // Cross-section graphic. Span the full text-block width when the section's
  // natural aspect keeps it within a sane height; otherwise (narrow Types like
  // the Alley) cap the height and center so the section never towers up the page.
  let xs_path = "exhibits/cross-sections/" + t.code + ".svg"
  layout(size => {
    let nat = measure(image(xs_path))
    let full_h = size.width * (nat.height / nat.width)
    let maxh = 180pt
    if full_h <= maxh {
      align(center, image(xs_path, width: 100%))
    } else {
      align(center, image(xs_path, height: maxh))
    }
  })

  // Credit + context caption.
  v(3pt)
  let credit = if t.at("illustrative", default: false) [
    Illustrative section only. Cartway geometry and right-of-way for this Type are set by
    the Maine DOT (see §12); the Town governs the frontage zone, setbacks, sidewalks, and
    access management. Cross-section illustration adapted from Streetmix (streetmix.net),
    © the Streetmix project, licensed CC BY-SA 4.0.
  ] else [
    Representative section at a typical right-of-way; widths are typical values within
    the ranges in the Design Standards below. Cross-section illustration adapted
    from Streetmix (streetmix.net), © the Streetmix project, licensed CC BY-SA 4.0.
  ]
  block(above: 0pt, below: 14pt, text(fill: subsection_gray, size: 7pt, style: "italic", credit))

  // Standards strip — these per-Type pages are the standards home (the former
  // Table 3.1a/3.1b comparison matrix has been retired in favor of these pages).
  panel("Design Standards")
  standards_strip(t.standards)

  // Build-To legend + Type-specific footnote. Set in the same gray 7pt italic as
  // the credit caption so it reads as an annotation on the standards strip rather
  // than as another standards row. States the §3.C reading convention (build to
  // the right-hand column) plus the §3.F / §6.D component rules; t.footnote (if
  // present) carries the Type-specific note.
  block(above: 5pt, below: 13pt, text(fill: subsection_gray, size: 7pt, style: "italic")[
    Build to the right-hand column (Art. 3 §3.C): the fuller value for pedestrian and
    landscape components (reducible only on the written demonstration of §3.C.4), the
    lower value for the traffic-calming dimensions (a safety floor). Components marked
    "where …" are required by context under §3.F; the Board may require fuller components
    within the assigned Type under §6.D.#if "footnote" in t [ \ #t.footnote]
  ])

  // Reference notes — complement the §2 prose (which sits just before the
  // plate); do not duplicate it. Two columns: where the Type applies + its
  // qualitative character attributes.
  let notecol(title, items) = {
    panel(title, above: 15pt)
    set list(marker: text(fill: article_blue)[•], indent: 0pt, body-indent: 0.5em, spacing: 0.5em, tight: true)
    pad(top: 4pt, list(..items.map(it => [#it])))
  }
  grid(columns: (0.85fr, 1.15fr), column-gutter: 44pt,
    notecol("Target Districts", t.at("applies_in", default: ())),
    notecol("Character", t.at("attributes", default: ())),
  )
}

// =============================================================================
// RENDER
// =============================================================================
#let data = json("exhibits/cross-sections/types.json")
#let order = if only.trim() != "" {
  only.split(",").map(s => s.trim())
} else {
  data.keys().filter(k => not k.starts-with("_"))
}

#for (i, code) in order.enumerate() {
  if i > 0 { pagebreak() }
  plate(data.at(code))
}
