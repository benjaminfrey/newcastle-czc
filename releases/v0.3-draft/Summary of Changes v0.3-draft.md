# Summary of Changes — v0.3-draft

**Release type:** Major visual-fidelity improvement. Rendered output is now substantially closer to the baseline CZC's look, based on a forensic style analysis of the baseline PDF (fonts, sizes, colors, geometry — all measured rather than estimated).

**Compares against:** [v0.2.1-draft](../v0.2.1-draft/) and the baseline [docs/Newcastle Core Zoning Code.pdf](../../docs/).

## Source of all changes: measured baseline values

Using `pdffonts` + `pymupdf` text-span extraction + pixel sampling of rendered baseline pages, the following were measured and applied throughout the template:

| Element | Baseline (measured) | v0.2.1 (estimated) | v0.3 (now matches) |
|---|---|---|---|
| Body font | Benton Sans Condensed Light | Helvetica Neue regular | **Barlow Condensed Light** (free metric/visual stand-in) |
| Body size | 8.5 pt | 9 pt | **8.5 pt** |
| Article blue | #367AAC | #2E96CC | **#367AAC** |
| Body text dark | #231F20 | #333333 | **#231F20** |
| Subsection gray | #7C766F | #2079B0 (was treated as a deep blue) | **#7C766F** |
| Tab background | #BFBFBF (gray, **uniform** across districts) | Article blue | **#BFBFBF** |
| Tab side | Verso (even pages): left; Recto (odd pages): right | Always right | **Alternates per page parity** |
| Subsection letter case | Lowercase (a., b., c.) | Uppercase (A., B., C.) | **Lowercase** in source + preserved in render |
| Section heading size | 14 pt Bold blue | 18 pt | **14 pt** |
| Subsection heading size | 11 pt Bold gray | 10 pt | **11 pt** |
| Article display | 33 pt | 36/48 pt | **33 pt** (Regular for "ARTICLE N", Bold for the name) |
| Section divider | 4×4 pt blue squares + thin #367AAC line | Estimated dimensions | **4×4 pt squares + 0.6 pt line** |

See [`style/style-analysis.md`](../../style/style-analysis.md) for the full forensic analysis with methodology.

## Files changed

- `style/style-analysis.md` — complete rewrite based on measured values (was estimates)
- `style/czc-colors.yml` — every district color measured; system colors updated
- `style/czc-template.typ` — body font, sizes, colors, tab geometry, subsection-marker case handling, footer layout per parity
- `style/fonts/` — added `BarlowCondensed-{Light,Regular,Medium,SemiBold,Bold}.otf` (SIL OFL; free)
- `build/build-article.sh` — adds `--pdf-engine-opt=--font-path=$REPO_ROOT/style/fonts` so Typst picks up Barlow Condensed
- `source/article-*.md` — perl-pass lowercased all `### A.` / `### B.` / `### C.` subsection markers to `### a.` / `### b.` / `### c.` to match the baseline convention

## Page count comparison

| | v0.1-baseline | v0.2-draft | v0.2.1-draft | v0.3-draft | Baseline body |
|---|---|---|---|---|---|
| Full integrated CZC | 95 | 107 | 113 | **79** | ~95–100 (excluding cover/blanks/TOC/exhibits) |
| Standalone Article 3 | n/a | 11 | 12 | **7** | n/a |

The dramatic drop (113 → 79) is the combined effect of:
- 8.5 pt body (was 9 pt)
- Condensed font (Barlow Cond Light glyphs are ~25% narrower than Helvetica Neue)
- Tighter leading
- All within the same content.

## What v0.3 fixed visually

1. **Font family** — narrow, humanist condensed sans that reads like Benton Sans
2. **Article blue** — the actual #367AAC, not the earlier #2E96CC
3. **Subsection markers** — lowercase letters as in baseline, not uppercase
4. **Article tab** — gray (not blue), correctly rotated, alternating side by page parity
5. **Section divider squares** — sized correctly (4×4 pt)
6. **Body text color** — warm #231F20 instead of generic #333333
7. **Header band** — uses subsection gray #7C766F like baseline
8. **Article opener** — no longer a separate empty page; integrates with body text in 2 columns

## What's still off (carry to v0.3.1 / v0.4)

1. **District-page banner styling** — the colored badge ("D1") + name banner ("RURAL") at top of each district page is currently rendered as standard level-2 headings. The actual baseline uses a full-width colored block with the district badge inset. A custom show rule + per-district colors lookup is needed. Carrying to v0.4.
2. **Use-table status glyphs** — `●` `❶` `❷` `✪` still render as `?` boxes in Barlow Condensed. Need a fallback font with those code points (e.g., DejaVu Sans for `●`, Noto Sans Symbols for the others).
3. **Header band topic name** — currently shows the most recent level-2 heading text. Baseline shows the *Section* name (which is what we want) but on Article 2 pages it shows "DISTRICT STANDARDS" / "Core Zoning Districts" — a fixed topic per Article. Acceptable for now.
4. **District-banner — none of the SD pages render a banner at all** because the SD pages aren't yet structured with the banner pattern in markdown. Defer to district-styling pass.
5. **Article opener Article-N "Light" weight** — baseline uses BentonSansCond-Book for the "ARTICLE 1" line and BentonSansCond-Bold for the name. Barlow Condensed doesn't have an exact "Book" face; I'm using Regular as a near-match. Visible distinction in baseline is subtle; acceptable.
6. **Exact margins per page parity** — current implementation uses Typst's named `inside`/`outside` margins. Baseline measurements suggest some additional asymmetry within the tab area (verso outside margin is ~50 pt with tab inside; recto outside is ~7 pt with tab in margin). Minor; not visible at typical reading zoom.
7. **`Article 4 Section 17 Building Groups` baseline typo** still preserved (see v0.2 Summary of Changes).
8. **Cross-section graphics** for Article 3 Types still not produced.

## Verification

- All 9 articles render without pandoc or Typst errors
- Per-article opener pages display the correct article display + section content sharing the page
- Subsection markers render as lowercase letters with uppercase names (e.g., "a. PURPOSE")
- Article tab renders as a gray block with white rotated "ARTICLE N" text, alternating left/right by parity
- Comparing v0.3 page 1 of Article 1 against baseline page 4: typography family resemblance is now strong; color palette matches; layout pattern matches

## Reproducing the analysis

The forensic-analysis scripts and methodology are recorded in [`style/style-analysis.md`](../../style/style-analysis.md) §12. Re-running them after any future template change will catch regressions.
