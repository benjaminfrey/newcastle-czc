# Summary of Changes — v0.2.1-draft

**Release type:** Patch release on v0.2-draft. Fixes a rendering defect in nested numbered lists; no content changes.

**Compares against:** [v0.2-draft](../v0.2-draft/).

## Issue fixed

In v0.2-draft (and earlier releases), nested numbered list items at the `a./b./c.` and `i./ii./iii.` levels rendered as inline continuations of their parent item rather than as their own indented sub-items on new lines.

Example of the broken rendering (v0.2-draft):

> 1. The Street/Road Types are organized in two families: a. The Street family (S-1 through S-4) contains Types whose character emphasizes pedestrian comfort, defined frontages, and lower design speeds. b. The Road family (R-1 through R-4) contains Types...

Example of the corrected rendering (v0.2.1-draft):

> 1. The Street/Road Types are organized in two families:
>     a. The Street family (S-1 through S-4) contains Types whose character emphasizes pedestrian comfort, defined frontages, and lower design speeds.
>     b. The Road family (R-1 through R-4) contains Types whose character emphasizes vehicular movement, working landscapes, and higher design speeds.

## Root cause

The Typst template's `#set enum(...)` rule used `indent: 0pt, body-indent: 0.6em, spacing: 0.4em`. With `indent: 0pt`, nested enum blocks emitted by pandoc (wrapped in `#block[#set enum(numbering: "a.")...]`) inherited zero left-indent, so a nested `a.` item visually aligned with its parent item's body — reading as the same paragraph.

Markdown sources were already structurally correct (4-space-indented nested ordered lists). Pandoc's `markdown+fancy_lists+startnum` input filter was already enabled and produced correct nested Typst output. The defect was purely in template enum styling.

## Fix

[style/czc-template.typ](../../style/czc-template.typ) `#set enum(...)` updated to:

- `indent: 1.2em` (was `0pt`) — gives each nested enum a real left offset
- `body-indent: 0.5em` (was `0.6em`) — small adjustment for clarity at narrower indent
- `spacing: 0.55em` (was `0.4em`) — slightly looser vertical rhythm so multi-line nested items don't collide visually
- `tight: false` — explicit; ensures item-to-item gaps are honored

Pandoc's per-block `#set enum(numbering: ...)` overrides for nested levels continue to work correctly under the new defaults — the change only affects the visual indent and spacing, not the numbering style.

## Page-count impact

| Build | v0.2-draft | v0.2.1-draft | Δ |
|---|---|---|---|
| Full integrated CZC | 107 | 113 | +6 |
| Standalone Article 3 | 11 | 12 | +1 |

The increase reflects nested items now occupying their own lines (previously squashed inline).

## Files changed

- `style/czc-template.typ` — enum styling only
- New release artifacts in `releases/v0.2.1-draft/`

No changes to any `source/article-*.md` files.

## Known issues NOT fixed in this patch

- **Use-table status glyphs** (`●`, `❶`, `❷`, `✪`) — rendering as `?` placeholder boxes in Article 2 district pages because Helvetica Neue (current fallback body font) does not include these characters. Fix requires either installing a font with these glyphs (e.g., static Source Sans 3 or DejaVu Sans) or using image substitutes. Tracked in `style/style-analysis.md` TODOs.
- **Baseline cross-reference typos** — see `releases/v0.2-draft/Summary of Changes v0.2-draft.md` for the inventory. Deferred to v0.3.
- **Cross-section graphics for Article 3 Types** — still pending.
