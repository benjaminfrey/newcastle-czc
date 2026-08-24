// Findings of Fact & Conclusions of Law — Newcastle Permit Review house style.
//
// Used by build/permit-review/render/build-findings.sh:
//   pandoc findings.md -o out.pdf --pdf-engine=typst \
//     --pdf-engine-opt=--font-path=style/fonts \
//     --template=style/findings-template.typ \
//     -V running-head="..." -V meeting-date="..." -V caption="..." \
//     [-V draft=true] [-V provenance=true]
//
// Clones style/memo-template.typ's proven pandoc -> Typst pattern (same
// measured palette, same Barlow fonts, same single pandoc body-splice point) but
// is shaped for a Planning Board Findings of Fact & Conclusions of Law draft
// rather than a memo: a two-column running head shown FROM PAGE 1, an
// "N of M" footer, an optional DRAFT watermark, and the Typst helpers below
// (#standard, #finding, #unresolved, #boardq, #motionblock, #conditions,
// #signaturegrid, #provenance) that reproduce the look of the real Newcastle
// decisions in docs/Findings of Fact and Conclusions of Law/*.pdf.
//
// FRAMING RULE (permit-review CONTRACT.md preamble, binding on this file too):
// this template renders THE WORKING DRAFT THE BOARD AMENDS, not a decision.
// #unresolved, #boardq and #motionblock exist so a blank stays visibly blank
// instead of being quietly filled in — honest blanks beat confident guesses.
//
// How markdown reaches these helpers: pandoc's Typst writer drops fenced-Div
// (`::: {.class}`) class names on the floor (verified empirically — a Div with
// class .standard round-trips to a bare `#block[...]`, the class is gone), so
// there is no way to key a `#show` rule off a div class the way an HTML build
// could. The load-bearing mechanism is instead the `raw_attribute` pandoc
// extension (already enabled by build/build-memo.sh's --from list and used
// the same way by style/redline-template.typ): render/findings_to_md.py emits
// fenced code blocks tagged `{=typst}`, which pass straight through to the
// compiler, and calls these helpers by name inside them. See
// render/findings_to_md.py's module docstring for the full explanation.

#let body_dark        = rgb("#231F20")
#let article_blue      = rgb("#367AAC")
#let subsection_gray  = rgb("#7C766F")
#let rule_faint        = rgb("#C9C6C2")
#let highlight_yellow  = rgb("#FCE29A")   // the highlighter color on the real
                                          // Board drafts (TBD fields, board
                                          // questions, blank vote counts)

// ---- pandoc metadata -> Typst booleans --------------------------------------
// This substitution happens once, when pandoc renders this template file, so
// draft-mode / provenance-mode are plain Typst booleans everywhere below,
// including inside calls made from the pandoc-generated body content. Only
// ever pass `-V draft=true` / `-V provenance=true` for "on" and OMIT the flag
// for "off" (never `-V draft=false` — pandoc's conditional treats any
// non-empty string, including the literal text "false", as present/true).
// This is exactly the convention render/build-findings.sh follows.
//
// NOTE ON THIS COMMENT BLOCK ITSELF: pandoc's template preprocessor scans the
// ENTIRE template file for its own delimiter character, textually, with no
// awareness of Typst comment syntax — so an unescaped delimiter anywhere in
// this file, including inside a comment, gets treated as template syntax and
// can corrupt the compiled output. That is why this file's comments spell
// pandoc's conditional out in words rather than writing its literal form;
// the four lines below are the only place that literal form actually
// appears, deliberately, and nowhere else in this file uses that character.
#let draft-mode      = $if(draft)$true$else$false$endif$
#let provenance-mode = $if(provenance)$true$else$false$endif$

#set page(
  paper: "us-letter",
  margin: (x: 1in, top: 1.05in, bottom: 0.9in),
  header: context {
    // Shown FROM PAGE 1 — unlike memo-template.typ (which suppresses the
    // header on page 1), every real Board draft carries this on its cover
    // page too, because the cover page IS page 1 of the document.
    set text(size: 8.5pt, fill: subsection_gray, weight: "medium")
    grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
      [$if(running-head)$$running-head$$else$Findings of Fact and Conclusions of Law$endif$],
      [$if(meeting-date)$$meeting-date$$endif$])
    v(1.5pt)
    grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
      [$if(caption)$#text(size: 8pt)[$caption$]$endif$],
      [])
    v(3pt)
    line(length: 100%, stroke: 0.4pt + rule_faint)
  },
  footer: context {
    set text(size: 8.5pt, fill: subsection_gray)
    line(length: 100%, stroke: 0.4pt + rule_faint)
    v(4pt)
    let total = counter(page).final().at(0)
    align(center)[
      #text(fill: article_blue, weight: "bold")[#counter(page).display("1")] of #total
    ]
  },
  background: context {
    if draft-mode {
      place(center + horizon,
        rotate(-33deg,
          text(size: 118pt, weight: "bold", fill: rgb(35, 31, 32, 22%))[DRAFT]
        )
      )
    }
  },
)

#set text(font: ("Barlow", "Helvetica Neue", "Helvetica"), size: 10pt, fill: body_dark, lang: "en")
#set par(leading: 0.6em, spacing: 0.9em, justify: true)

// ---- Headings ---------------------------------------------------------------
// Level 1 = top divisions: FINDINGS OF FACT / CONCLUSIONS OF LAW / DECISION
// OF THE PLANNING BOARD — big blue bold, matching the real decisions exactly.
#show heading.where(level: 1): it => block(above: 16pt, below: 8pt, breakable: false)[
  #set text(fill: article_blue, weight: "bold", size: 19pt)
  #upper(it.body)
]
// Level 2 = Code-derived headings (Article N, a District name, a standards
// group) — blue, smaller, no forced uppercase (Article titles carry their
// own casing, e.g. "Article 2 - District Standards").
#show heading.where(level: 2): it => block(above: 13pt, below: 5pt, breakable: false)[
  #set text(fill: article_blue, weight: "bold", size: 13pt)
  #it.body
]
// Level 3 = administrative subsection labels (Project Information, Required
// Review(s), a district code like "D1 - Rural") — black, bold, underlined,
// matching the real drafts' "Project Information" / "Site Information" style.
#show heading.where(level: 3): it => block(above: 11pt, below: 4pt, breakable: false)[
  #set text(fill: body_dark, weight: "bold", size: 11pt)
  #underline(offset: 2.5pt, stroke: 0.5pt + body_dark)[#it.body]
]
// Level 4 = fine sub-labels (APPLICABILITY, PUBLIC NOTICE, MAILED NOTICE).
#show heading.where(level: 4): it => block(above: 8pt, below: 3pt, breakable: false)[
  #set text(fill: subsection_gray, weight: "bold", size: 9.5pt)
  #upper(it.body)
]

// ---- Tables: plain hairlines, bold header row, no fill (the real drafts'
// "Required Review(s)" / "Additional Requirements" tables are unshaded). ----
#set table(
  stroke: (x, y) => (
    top: if y == 0 { 0.8pt + body_dark } else { 0pt },
    bottom: 0.4pt + rule_faint,
  ),
  inset: (x: 5pt, y: 4pt),
)
#show table: set text(size: 9.5pt)
#show table.cell.where(y: 0): set text(weight: "bold")
#show figure: set block(breakable: true)

// Horizontal rule (markdown ---) -> subtle full-width divider.
#let horizontalrule = block(above: 11pt, below: 11pt,
  line(length: 100%, stroke: 0.4pt + rule_faint))

// ==============================================================================
// Findings-specific helpers. Called from render/findings_to_md.py's raw-Typst
// output. These eight names are the contract between that script and this file.
// ==============================================================================

// #standard — the Code's own words, verbatim, in the Board's own house style.
//
// MEASURED from the real decisions (Shattuck 2025-12-18 p6 and Uberoi 2024-08-15,
// both in docs/): the criterion letter and the standard's opening run together on
// ONE line hanging at margin+9pt, and the standard's wrapped lines sit at
// margin+27pt. The finding beneath then shares that same +27pt edge. There is no
// quotation rule and no standalone heading line in the real documents — the
// hanging indent alone carries the structure.
#let standard(body) = block(
  width: 100%, above: 7pt, below: 2pt, breakable: true,
  inset: (left: 9pt),
)[
  #set text(fill: body_dark, size: 10pt)
  // #par(hanging-indent:) -- NOT `#set par(...)`, which silently does nothing
  // inside a block body (verified against typst 0.14).
  #par(hanging-indent: 18pt)[#body]
]

// #finding — the Board's finding in response to the standard immediately
// above it: indented, italic. Together #standard + #finding reproduce the
// "Per Section ... / The proposed building is located ..." pattern that makes
// up the bulk of every real decision.
#let finding(body) = block(
  width: 100%, above: 2pt, below: 9pt, breakable: true,
  inset: (left: 27pt),
)[
  #set text(fill: body_dark, size: 10pt, style: "italic")
  #body
]

// #unresolved — a yellow-highlighted blank: a TBD field, a missing number, an
// item the record does not yet answer.
//
// Indented to margin+27pt, the same edge the Board's finding sits on in the
// real decisions (measured: Shattuck 2025-12-18, Uberoi 2024-08-15) — because
// that is exactly what it stands in for when nothing has been drafted yet.
#let unresolved(body) = block(width: 100%, above: 2pt, below: 9pt,
  inset: (left: 27pt))[
  #box(fill: highlight_yellow, inset: (x: 3pt, y: 1pt), radius: 1pt)[#body]
]

// #boardq — a highlighted, italic, first-person question addressed to the
// Board. Never a conclusion — a question the Board must answer on the record.
//
// Sits at margin+27pt, the finding's own edge in the real decisions: it occupies
// the place a finding will occupy once the Board answers it.
#let boardq(body) = block(width: 100%, above: 2pt, below: 9pt,
  inset: (left: 27pt))[
  #box(fill: highlight_yellow, inset: (x: 3pt, y: 1pt), radius: 1pt)[
    #text(style: "italic")[#body]
  ]
]

// A blank fill-in-the-line cell, shared by #motionblock and #signaturegrid:
// prints the value if one was supplied, otherwise an empty underlined slot.
#let blank-slot(value) = box(width: 100%, inset: (bottom: 1pt),
  stroke: (bottom: 0.6pt + subsection_gray))[
  #if value == none or value == "" { h(1fr) } else { value }
]

// #motionblock — the vote record. Every field defaults to none, which renders
// as a genuinely blank underlined slot — the app NEVER fills these in itself.
#let motionblock(
  motion: none, moved-by: none, second: none, discussion: none,
  yea: none, nay: none, abstain: none, result: none,
) = block(
  width: 100%, above: 10pt, below: 10pt, breakable: false,
  stroke: 0.6pt + rule_faint, inset: 10pt, radius: 2pt,
)[
  #set text(size: 9.5pt, fill: body_dark)
  #set par(justify: false)
  #grid(columns: (auto, 1fr), row-gutter: 8pt, column-gutter: 8pt,
    text(weight: "bold")[Motion:],     blank-slot(motion),
    text(weight: "bold")[Moved by:],   blank-slot(moved-by),
    text(weight: "bold")[Second:],     blank-slot(second),
    text(weight: "bold")[Discussion:], blank-slot(discussion),
    text(weight: "bold")[Yea:],        blank-slot(yea),
    text(weight: "bold")[Nay:],        blank-slot(nay),
    text(weight: "bold")[Abstain:],    blank-slot(abstain),
    text(weight: "bold")[Result:],     blank-slot(result),
  )
]

// #conditions — a numbered list of conditions of approval. An empty list
// still prints one genuinely blank numbered slot (matching the real drafts'
// "Additional conditions included by the Planning Board: 1. ...") rather than
// silently omitting the section.
#let conditions(items) = block(width: 100%, above: 8pt, below: 8pt)[
  #set text(size: 10pt, fill: body_dark)
  #if items.len() == 0 [
    #enum(numbering: "1.")[#unresolved[_(conditions to be added by the Board)_]]
  ] else [
    #enum(numbering: "1.", ..items)
  ]
]

// #signaturegrid — a two-column grid of signature lines. `members` is an
// array of either plain strings (a name) or dictionaries with `name` and,
// optionally, `title` (e.g. "Chair"). Signature and date are both blank.
//
// The certification line above the grid is copied VERBATIM from every
// sample in docs/Findings of Fact and Conclusions of Law/*.pdf, draft and
// adopted alike (`pdftotext -layout`, checked against Uberoi/Profenno/Z38
// DRAFTs and the Shattuck ADOPTED FINAL, 2026-08-23) -- INCLUDING the
// "Conditions of Law" wording where "Conclusions" is plainly meant
// (permit-review DECISIONS-NEEDED.md D-0028: the Town's settled house
// wording, error or not; correcting it is the Board's call, not this
// template's).
#let signaturegrid(members) = block(width: 100%, above: 16pt, breakable: false)[
  #set text(size: 10pt, fill: body_dark)
  #set par(justify: false)
  We, the undersigned, certify the above Findings of Fact and Conditions of Law.
  #v(14pt)
  #grid(columns: (1fr, 1fr), row-gutter: 22pt, column-gutter: 26pt,
    ..members.map(m => {
      let name  = if type(m) == dictionary { m.at("name", default: "") } else { m }
      let title = if type(m) == dictionary { m.at("title", default: none) } else { none }
      block[
        #line(length: 100%, stroke: 0.6pt + body_dark)
        #v(2pt)
        #grid(columns: (1fr, auto), column-gutter: 6pt,
          [#name#if title != none and title != "" [, #title]],
          [#text(fill: subsection_gray, size: 8.5pt)[Date] #box(width: 0.85in, inset: (bottom: 1pt), stroke: (bottom: 0.6pt + subsection_gray))[]],
        )
      ]
    })
  )
]

// #provenance — a small gray superscript citation marker, shown only when the
// draft is rendered with -V provenance=true (a debugging / audit aid; the
// Board-facing draft omits it by default). `key` is any short citation string
// (typically the output of app/citation.py:render(..., style="short")).
#let provenance(key) = if provenance-mode {
  h(2pt) + super(text(size: 6.5pt, fill: subsection_gray)[[#key]])
} else { none }

$body$
