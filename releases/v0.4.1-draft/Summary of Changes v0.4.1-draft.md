# Summary of Changes — v0.4.1-draft

**Release type:** Review-driven correction pass on top of [v0.4-draft](../v0.4-draft/). Two targeted layout fixes flagged in review — the section-divider placement and the cramped Type Standards table — with no content changes to the regulatory text.

**Compares against:** [v0.4-draft](../v0.4-draft/) and the baseline [docs/Newcastle Core Zoning Code.pdf](../../docs/).

**Reported defects addressed:**
- ❌ → ✅ "There should **NOT** be a blank row under the section headers / above the blue line with square dots on each end." → **Match baseline:** the square-endpoint divider now sits tight under the **Article-opener title only** and is **removed from under section headings entirely**.
- ❌ → ✅ "Table 3.1 should probably be an entire page… **spanning both columns**, so that it is easier to read; it is too crunched as it is." → Table 3.1 now renders as a **full-width float spanning both columns**.

---

## 1. Section divider — root cause & fix

**Root cause.** v0.4 drew the 4×4 pt-square blue divider under *every* numbered section heading (level-2), with a gap above it. Re-measuring the baseline shows the divider is an **Article-opener element**: it appears **once per Article**, tight under the opener title ("ARTICLE N" / NAME), and **never** under mid-article section headings (the baseline's "3. DISTRICT MAP" and similar have no rule below them). The earlier measurement that "found" a divider near a section heading had actually measured the *opener* divider on the Article 1 opener page, which happens to sit just above the first section "1. CORE ZONING CODE".

**Fix.** In `style/czc-template.typ`:
- The `#show heading.where(level: 2)` rule no longer draws a divider — just the 14 pt blue section name, with `below: 4pt` (no rule, no blank row; body/subsection follows directly).
- The divider (4×4 pt squares + 0.6 pt blue rule, full text-block width) moved into `article_opener()`, placed tight under the bold name block.

**Measured result (vs. baseline targets):**

| Gap | Baseline | v0.4.1 (now) |
|---|---|---|
| Opener name-baseline → divider | ~10.6 pt | **10.4 pt** |
| Divider → first section heading | ~14.4 pt | **11.8 pt** (remainder absorbed at the single-column-opener → two-column-body boundary; reads correctly) |
| Divider under mid-article section headings | none | **none** |

Verified on **all 9 Article openers** in the integrated build (pages 1, 3, 27, 37, 43, 51, 59, 69, 85) — every opener carries the divider; no section heading does.

## 2. Table 3.1 — full-width float

**Root cause.** The Street & Road Type Standards matrix is **9 columns** (Standard + 8 Types) × 14 rows. Rendered as an ordinary in-column table it was confined to a single 217 pt column and was unreadably cramped.

**Fix.** In `source/article-03-streets-roads-driveways.md`, Table 3.1 is now authored directly in Typst inside a ` ```{=typst} ` raw block and placed with:

```typst
#place(top, scope: "parent", float: true, block(width: 100%)[ … #table(…) ])
```

`scope: "parent"` floats the block out of the two-column flow so it spans the **full text-block width**; body text flows in two columns above and below it. A local `#show table: set text(size: 8pt)` and `inset: (x: 3pt)` keep dense cells (e.g., "per MaineDOT") on one line. The global hairline table styling (horizontal rules only, no verticals, no shading) still applies.

**Measured result:** the table's widest horizontal hairline is **478.5 pt** (the full text block) vs. ~217 pt for an in-column table; it appears **exactly once** (integrated p. 29, standalone p. 3). Tables 3.2 and 3.3 are unchanged (they fit a single column).

> The other tables were already reported as "looking much better" in v0.4 and are untouched.

## 3. Files changed

- `style/czc-template.typ` — divider removed from the level-2 heading rule (`below: 6pt` → `below: 4pt`, no grid); divider added to `article_opener()` (name block `below: 15pt`, divider block `below: 16pt`).
- `source/article-03-streets-roads-driveways.md` — Table 3.1 (caption + 9-column pipe table) replaced by a full-width Typst float (`place(scope: "parent", float: true)`). No regulatory text changed; the data values are identical.
- `style/style-analysis.md` — §6 retitled/rewritten (divider is an opener element, not a section-heading element); the spacing table corrected; new §14 documenting the v0.4.1 fixes and the 91 → 90 page-count change.

## 4. Page count comparison

| | v0.4-draft | v0.4.1-draft |
|---|---|---|
| Full integrated CZC | 91 (3 blank pads) | **90** (4 blank pads at p. 36, 58, 68, 84) |
| Standalone Article 3 | 9 | **9** |

The 91 → 90 change is **not** a regression. The divider relocation and the Table 3.1 float shift each Article's content flow, which changes *which* Articles render to an odd page length and therefore which receive an even-keeping blank pad. Footers remain **continuous 1→90** and every Article still opens on a **recto** page; the binding (inside/outside) margin parity is preserved.

## 5. Verification

- Section headings (level-2) render with **no divider and no blank row** below them; the body/subsection follows directly.
- The square-endpoint divider renders **once per Article**, tight under the opener title, full text-block width, on all 9 openers.
- Table 3.1 spans **both columns** (478.5 pt rule), appears exactly once (integrated p. 29), and its cells are legible at 8 pt; body text flows in two columns above and below.
- Footer page numbers are **continuous 1→90** across the integrated document; the 4 blank pad pages (36, 58, 68, 84) are truly empty and unnumbered.
- Every Article opener lands on a **recto** (odd) page; tab and running header sit on the correct outer edge per parity.

## 6. What's still off (carry forward from v0.4)

1. **Front matter (cover + TOC).** Still absent, so Articles open on recto (vs. the baseline's verso, an artifact of its 3 front-matter pages). Adding a cover + TOC is the proper fix and will restore verso openers; deferred as separate scope.
2. **District-page banner styling** — colored badge ("D1") + name banner ("RURAL") still render as standard headings, not the baseline's full-width colored block.
3. **Use-table status glyphs** `●` `❶` `❷` `✪` — `●` renders; the enclosed numerals/star still need a symbol fallback font.
4. **Cross-section graphics** for the eight Street/Road Types not yet produced.
