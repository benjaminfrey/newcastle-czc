# style/

Visual-identity assets for rendering Newcastle CZC drafts to PDF.

## Files

| File | Purpose |
|---|---|
| `style-analysis.md` | Reverse-engineered formatting of the baseline CZC — page geometry, typography, colors, heading hierarchy, table styles. Documented source of truth for visual decisions. |
| `czc-colors.yml` | Color palette (system colors, district colors, proposed Street/Road Type colors). Documented source of truth for color values — currently mirrored in the template by hand. |
| `czc-template.typ` | Pandoc-Typst template that defines page geometry, show rules for headings, the rotated Article tab, header/footer bands, and table styling. Pandoc fills in `$body$` from the markdown source. |
| `fonts/` | Embedded fonts (currently empty — body font is Helvetica Neue, system-installed). |

## How rendering works

```
markdown source (source/article-NN-*.md)
    │
    ▼
pandoc --pdf-engine=typst --template=style/czc-template.typ
    │
    ▼
PDF (releases/vX.Y-draft/*.pdf)
```

Pandoc converts markdown to Typst, substitutes variables into the template (`article-number`, `article-name`, `footer-date`, etc.), then invokes Typst to compile to PDF.

## Tuning the visual

To change a color: edit `czc-colors.yml` (documentation) **and** the corresponding `#let ... = rgb(...)` line in `czc-template.typ`. The template will load directly from YAML in a future revision; until then, keep them in sync.

To change page geometry, fonts, or heading styles: edit `czc-template.typ`. See the section comments for landmarks.

## Known TODOs

- Load colors directly from `czc-colors.yml` via Typst `yaml()` (currently blocked by pandoc/typst working-directory resolution; manual sync for now)
- Install static OTF version of Source Sans 3 (Adobe's static OTF release) to match the baseline body font more closely; current build uses Helvetica Neue as fallback
- Verify color hex values by pixel-sampling the baseline PDF
- Implement per-district article-tab coloring for Art. 2 district pages
- Implement per-Type article-tab coloring for new Art. 3 type pages
