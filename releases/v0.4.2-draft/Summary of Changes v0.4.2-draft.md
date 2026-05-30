# Summary of Changes — v0.4.2-draft

**Release type:** Review-driven layout/typography pass on top of [v0.4.1-draft](../v0.4.1-draft/). Three targeted fixes flagged in review — subsection-marker case, Table 3.1 ordering, and detached table captions — with **no changes to the regulatory text**.

**Compares against:** [v0.4.1-draft](../v0.4.1-draft/) and the baseline [docs/Newcastle Core Zoning Code.pdf](../../docs/).

**Reported defects addressed:**
- ❌ → ✅ "Sub-section headers (Purpose, Applicability, General, etc.) should have their lettered-list letter **capitalized, not lowercase**. Also confirm this with the CZC." → **Confirmed** the baseline uses lowercase (129/0 across 110 pages); per an explicit decision the draft now renders the marker **UPPERCASE** as a deliberate deviation.
- ❌ → ✅ "Table 3.1 should come **after** Section 3. Type Standards Table, not before it." → Table 3.1 now bottom-floats **below** its section heading instead of migrating above it.
- ❌ → ✅ "The titles of Tables 3.2 and 3.3 are **detached from their tables** because the table wrapped to the next column. All table titles should be **locked to their tables**." → Tables 3.2, 3.3, and 3.4 captions are now welded to their grids and never strand at a column break.

---

## 1. Subsection marker case — confirmation & deliberate deviation

**Confirmation against the baseline (as requested).** A fresh measurement across all 110 baseline pages found subsection markers rendered in **lowercase** ("a. PURPOSE") in **129 of 129** cases — **0 uppercase**. So the baseline convention is unambiguously lowercase; common municipal-code practice (uppercase "A.") is *not* what the Newcastle CZC does.

**Decision.** With that confirmed, the marker is rendered **UPPERCASE** ("A. PURPOSE") anyway — a deliberate, informed deviation from the baseline, recorded as such so a future reader does not "correct" it back thinking it is a regression.

**Fix.** In `style/czc-template.typ`, the level-3 (subsection) heading show-rule changed from `#h.body` to `#upper(h.body)`. Because the subsection *name* is already all-caps in the source, `upper()` only flips the single marker letter. **The source markdown is untouched** (`### a. PURPOSE`), so the change is reversible with a one-line template edit.

**Measured result:** **277 uppercase / 0 lowercase** subsection markers in the integrated build; **44 / 0** in the standalone Article 3. Samples: "A. PURPOSE", "B. APPLICABILITY", "C. AUTHORITY & COMPLIANCE".

## 2. Table 3.1 ordering — bottom-float after its section heading

**Root cause.** v0.4.1 placed the full-width Type Standards matrix with `#place(top, scope: "parent", float: true, …)`. A **top** float migrates to the top of its anchor page — *above* any content that is earlier in the source on that page — so Table 3.1 rendered *above* its own "3. TYPE STANDARDS TABLE" heading, reading as if it preceded the section it belongs to.

**Fix.** In `source/article-03-streets-roads-driveways.md`, the float's placement edge changed from `top` to **`bottom`**. A bottom float sinks below the heading + intro text, so the table now follows Section 3.

```typst
#place(
  bottom,                       // was: top
  scope: "parent", float: true,
  block(width: 100%)[ … TABLE 3.1 … #table(…9 cols × 14 rows…) ]
)
```

**Why an edge change rather than a page break.** A strict "heading → table → next section" isolation would want a forced break, but `#pagebreak()` is **illegal inside Typst's `columns()` container** (the entire two-column body is one container; Typst errors *"pagebreaks are not allowed inside of containers"*). Float behavior is therefore steered by **edge**, not by forcing a page.

**Measured result:** the table still spans the full **478.5 pt** text block and appears exactly once (integrated p. 29). **Honest caveat:** with a bottom float, Section 4's body flows in the two columns *above* the table on the same page — the table is not visually fenced strictly between Sections 3 and 4. Strict fencing would cost ~half a page of whitespace and was not requested.

## 3. Table captions locked to their grids (Tables 3.2, 3.3, 3.4)

**Root cause.** When a Markdown pipe table wrapped from the bottom of one column to the top of the next, its "TABLE 3.x …" caption could strand at the bottom of the previous column, detached from the grid.

**Fix.** Tables 3.2 (Sight Distance), 3.3 (Construction Specifications), and 3.4 (Default Type by District) were re-authored from Markdown pipe tables into raw Typst inside ` ```{=typst} ` blocks, each wrapping the caption + grid in:

```typst
#block(breakable: false)[ TABLE 3.x …  #table(…) ]
```

`breakable: false` forbids the block from splitting across a column/page boundary, so the caption and its grid always travel together. These tables are short (≤14 rows) and fit comfortably within a single column, so locking them costs no readability. The global hairline table styling (horizontal rules only, no verticals, no shading) still applies; bold sub-header rows in Table 3.3 ("Construction", "Hot Bituminous Pavement") use `*…*` span emphasis, and the ″ / ½ glyphs render correctly.

**Measured result:** each caption sits immediately above its grid on the same page/column (standalone pp. 4, 6, 7). Table 3.1 (the full-width float) was already a single Typst block and is unaffected.

## 4. Files changed

- `style/czc-template.typ` — level-3 subsection heading rule: `#h.body` → `#upper(h.body)` (force-uppercase marker); explanatory comment recording the deliberate deviation.
- `source/article-03-streets-roads-driveways.md` — Table 3.1 float edge `top` → `bottom`; Tables 3.2 / 3.3 / 3.4 converted from Markdown pipe tables to raw-Typst `#block(breakable: false)[caption + table]`. **No regulatory text or data values changed.**
- `style/style-analysis.md` — §3 and §8 annotated to flag the deliberate uppercase rendering (baseline measurements left intact); new **§15** documenting all three v0.4.2 fixes and the newly-identified deferred table-numbering defect.

## 5. Page count comparison

| | v0.4.1-draft | v0.4.2-draft |
|---|---|---|
| Full integrated CZC | 90 (4 blank pads: 36, 58, 68, 84) | **90** (same 4 blank pads) |
| Standalone Article 3 | 9 | **9** |

The case change and table edits do not alter pagination. Footers remain **continuous 1→90**; every Article still opens on a recto page; the 4 blank pad pages remain truly empty and unnumbered.

## 6. Verification

- Subsection markers render **UPPERCASE** everywhere: 277/0 (integrated), 44/0 (standalone). Source markdown remains authored lowercase (`### a. PURPOSE`).
- Table 3.1 spans both columns (478.5 pt rule), appears exactly once (integrated p. 29), and now sits **below** its "3. TYPE STANDARDS TABLE" heading rather than above it.
- Tables 3.2, 3.3, 3.4 captions are locked to their grids — caption immediately above the grid, same column/page (standalone pp. 4, 6, 7).
- Footer page numbers continuous **1→90**; the 4 blank pads (36, 58, 68, 84) are empty and unnumbered.
- Footer date reads the build's version ("Draft v0.4.2-draft") on both deliverables.

## 7. What's still off (carry forward)

1. **Stale table numbers from the Article renumbering (NEWLY IDENTIFIED — deferred to its own pass).** When Articles 3–8 were renumbered to 4–9 (v0.2), their table captions and in-text "see Table X.Y" references kept the *old* article prefix. Currently: Art. 4 (Site Standards) tables read "3.x" (and collide with the new Article 3); Art. 5 reads "4.x"; Art. 6 reads "5.x"; Art. 8 reads "7.x". Fixing requires renumbering ~35 captions plus every in-text cross-reference and a verification sweep. The new Article 3's own tables (3.1–3.4) are correct. *(Deferred by explicit decision; see `style/style-analysis.md` §15.)*
2. **Front matter (cover + TOC).** Still absent, so Articles open on recto (vs. the baseline's verso). Adding a cover + TOC is the proper fix and will restore verso openers; deferred as separate scope.
3. **District-page banner styling** — colored badge ("D1") + name banner ("RURAL") still render as standard headings, not the baseline's full-width colored block.
4. **Use-table status glyphs** `●` `❶` `❷` `✪` — `●` renders; the enclosed numerals/star still need a symbol fallback font.
5. **Cross-section graphics** for the eight Street/Road Types not yet produced.
