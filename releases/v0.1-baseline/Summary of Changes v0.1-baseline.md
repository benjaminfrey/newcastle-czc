# Summary of Changes — v0.1-baseline

**Release type:** Baseline transcription. No substantive content changes from the original Newcastle Core Zoning Code (adopted Nov 3, 2020, amended through Mar 24, 2025).

**Purpose:** Establish a markdown source-of-truth that mirrors the baseline CZC. All subsequent drafts (v0.2-draft, v0.3-draft, …) diff against this v0.1-baseline rather than against the PDF, giving cleaner redlines and clearer change tracking.

## Contents of this release

| File | Purpose |
|---|---|
| `Newcastle CZC (Integrated Draft v0.1-baseline).pdf` | Full CZC rendered from markdown sources. 8 Articles in original numbering, 95 pages. |
| `Newcastle CZC (Integrated Draft v0.1-baseline).md` | Concatenated markdown sources (intermediate output; not re-rendered as one input). |
| `Summary of Changes v0.1-baseline.md` | This file. |

## What was transcribed

All 8 Articles of the baseline CZC were transcribed into individual markdown files in `source/`:

- `article-01-general.md` — Article 1 General Standards
- `article-02-districts.md` — Article 2 District Standards (D1–D6 + 7 Special Districts)
- `article-03-site-standards.md` — Article 3 Site Standards
- `article-04-building-standards.md` — Article 4 Building Standards (incl. 4 Building Groups)
- `article-05-design-standards.md` — Article 5 Design Standards (Massing + Architectural Components)
- `article-06-use-standards.md` — Article 6 Use Standards (66 use definitions)
- `article-07-administration.md` — Article 7 Administration (29 sections)
- `article-08-definitions.md` — Article 8 Definitions (~150 alphabetical entries)

## What is NOT in this release (deliberate omissions from the transcription)

The following baseline elements are not reproduced in v0.1-baseline. They will be addressed in later releases or remain referenced from the baseline PDF.

- **Cover page** — original CZC pp. 1–3 (cover, blank, attestation)
- **Table of Contents** — original CZC pp. 1–3 (will be regenerated mechanically before public review)
- **District Map exhibits** — `Exhibit 1.1 District Map`, `Exhibit 1.2 District Map Inset – Newcastle Town Center`, `Exhibit 1.4 District Map Inset – Sheepscot Village`. These are GIS-derived images that will be referenced as image files when added to `source/exhibits/`.
- **Page-level layout artifacts** — original blank pages between articles; not reproduced.

## Known transcription limitations to address in v0.2+

- **Body font** — Currently rendering with Helvetica Neue. Baseline appears to use a humanist sans (likely Source Sans 3 or similar). Typst does not accept variable-font files; static OTF Source Sans 3 install needed for closer match.
- **District badge + name banner** — Baseline Article 2 district pages have a distinctive colored badge ("D1") + name banner ("RURAL"). Current template renders these as standard level-2 section headings with the blue divider. Needs a custom Typst show rule.
- **Article tab coloring** — Baseline uses district color for the tab on district pages. Current template uses Article blue everywhere. Future work: per-page tab color override.
- **Color palette verification** — Color values in `style/czc-colors.yml` are visual estimates. Pixel sampling from the baseline PDF would produce more exact values.
- **Yaml frontmatter visible** — In the per-article PDF render, the frontmatter block is suppressed correctly. In the concatenated markdown output, frontmatter is preserved (read by humans, not re-rendered).

## Verification performed

- All 8 articles render without pandoc or Typst errors
- Per-article opener pages display correctly ("ARTICLE N / NAME")
- Two-column body, blue section dividers with endpoint squares, rotated margin tab, header/footer all render
- Total page count (95) consistent with baseline body content (baseline 110 pages including cover/blanks/TOC/exhibits)

## Notes on the v0.1-baseline-vs-baseline-PDF redline

A page-level visual diff (`diff-pdf`) was attempted against the baseline PDF but produced a ~120 MB output where nearly every page registered as "different" — driven by font choice and page-layout details, not by content. This output was removed as it added noise without value. **Content-level redlines will be meaningful starting at v0.2-draft**, when the markdown source begins to diverge from the baseline. Until then, the baseline PDF in `docs/` remains the canonical reference for the original text.
