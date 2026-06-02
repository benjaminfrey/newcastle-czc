# Summary of Changes — v0.14-draft

**Release type: First release in which Article 3 §5 *shows* its exhibits.** v0.12
wrote the regulatory structure (a binding Street/Road Type per segment + an
illustrative companion map) and v0.13 shipped the GIS *engine* that turns
authoritative public data into the classification — but neither put a map or a
table into the Code. This release does: **Exhibit 3.1 (Inventory of Existing
Streets & Roads)** and **Exhibit 3.2 (Street & Road Type Map)** now render inside
Article 3 §5 of both deliverables, generated from real Newcastle data.

The classification is a **90–95 % DRAFT**, derived from an *approximate trace of the
official District Map* (the contractor's exact district shapefile is not yet in
hand). It is accurate enough to put a real map in front of readers for Town-Meeting
consideration; when the exact shapefile arrives, the **same pipeline** re-runs from
one step and produces a 100 % version. Every exhibit carries a DRAFT provenance
banner saying exactly this.

**Compares against:** [v0.12-draft](../v0.12-draft/) — the last release with a
rendered deliverable (v0.13 was tooling only).

## 1. What changed, in one picture

| | v0.12 | **v0.14** |
|---|---|---|
| §5 regulatory text | binding Type + Exhibit 3.1/3.2 *referenced* | **unchanged** |
| Exhibit 3.1 (Inventory table) | described, not rendered | **renders in §5** — 215 segments, colour-coded Type |
| Exhibit 3.2 (Type Map) | sample-data engine only | **renders in §5** — Newcastle's real network |
| Underlying data | none in the Code | **`inventory.json` promoted** — 214/215 segments typed |

**The regulatory prose did not change.** The v0.14-vs-v0.12 redline is intentionally
empty (0 passages): the only markdown delta is a non-printing HTML comment marking
where the exhibits splice in. Everything new in v0.14 is the *rendered exhibits* and
the *data* behind them — neither lives in the prose.

## 2. How the draft districts were produced (automated, repeatable)

The one thing v0.13 couldn't finish without the vendor file — the **district layer** —
is now derived automatically from the published District Map image, accurately
enough for a draft:

- **Georeference (`build/street-types/georef.py`, new).** Seeds with a bounding-box
  match between the colored-district extent and the authoritative town-boundary
  polygon, then optimizes a north-up affine transform to **maximize boundary overlap
  (IoU)** against that polygon — no manual control points. Final IoU **0.77** (the
  town polygon is the ground truth, so this is a real fit, not a self-graded one).
- **Full-coverage extraction (`00_digitize_districts.py --full-coverage`, new mode).**
  Within the town mask, assigns **every** pixel to its nearest District legend-swatch
  colour, sieves speckle, and polygonizes — a **gapless** district layer (the earlier
  threshold mode dropped the pale districts). Legend-swatch colours are sampled
  deterministically from the map's own key (`sample_key.py` → `key-colors.json`).
- **Result:** all **13 road-bearing districts** extracted (every district except
  SD-Marine, which carries no public ways).

## 3. The resulting classification (live Newcastle data)

Run end-to-end through `01_fetch → 02_prepare → 03_join → 04_classify → 05_export`:

- **215 segments** from 148 named ways, split at public-road intersections.
- **214 of 215 typed (99.5 %)** — 1 segment pending review.
- **By Type:** R2 Rural Road **127** · R1 Connector **46** · S3 Neighborhood **14** ·
  R4 Highway Commercial **13** · R5 Rural Highway **9** · S2 Village **5**. (S1, S4 and
  R3 have no current segments, so they don't appear in the map legend — by design.)
- **By ownership (derived online):** Private Road **105** · Town Way **80** ·
  State Highway **28** (2 flagged for review).
- **Spatially sane:** the village core around the river reads S2/S3, the Route 1
  corridor reads R4/R5, collectors read R1, and the rural majority reads R2 — exactly
  the pattern the District Map implies.

## 4. Wiring the exhibits into §5 (the build change)

Activating the exhibits in the production build, mirroring the Type-plate splice:

- A `<!-- STREET-TYPE-EXHIBITS -->` marker was added to §5.C (after the Inventory
  subsection, before the Classification Rubric).
- `split-article-03.py` gained an **optional second marker**: it now splits the body
  into `03a` (opener), `03b` (§2.d…§5.C) and `03c` (§5.D…§14). Backward-compatible —
  no marker ⇒ today's two-way split, **proven byte-identical** by a regression check.
- `build-full-czc.sh` + `build-article-3.sh` splice the render order
  **`[03a, plates, 03b, Exhibit 3.1, Exhibit 3.2, 03c]`**, threading the cumulative
  **even** page offset so verso/recto parity holds through §5 (the table is
  even-paged; the one-page map self-pads). The §5.D…§14 body **always** renders even
  if the data is absent — only the exhibits are conditional on `inventory.json`.

## 5. Deliverables

- `Newcastle CZC (Integrated Draft v0.14-draft).pdf` / `.md` — full Code; Exhibits
  3.1 + 3.2 in Article 3 §5 (body pp. 53 + 59); TOC re-derived (Article 3 → p. 37).
- `Article 3 Streets Roads & Driveways (Standalone v0.14-draft).pdf` — same exhibits
  in §5.
- `Redline — Full CZC v0.14-draft vs v0.12-draft.pdf` — **empty by design** (no prose
  change; the exhibits are rendered units, not text).
- `Redline — Full CZC v0.14-draft vs v0.1-baseline.pdf` — the cumulative Article 3
  rewrite (unchanged in substance from v0.12's baseline redline).

## 6. Files added / changed

- **New:** `build/street-types/georef.py`, `sample_key.py`, `key-colors.json`;
  `source/exhibits/street-types/inventory.json` (promoted draft, 215 segments);
  `data/street-types/districts.geojson` + `georef-transform.json` (reproducibility).
- **Changed:** `build/split-article-03.py` (second marker); `build/build-full-czc.sh`
  + `build/build-article-3.sh` (§5 splice + even-block parity);
  `source/article-03-streets-roads-driveways.md` (the §5 marker — non-printing);
  `build/street-types/00_digitize_districts.py` (full-coverage mode),
  `03_join.py` (nearest-district fallback), `05_export.py` (banner),
  `requirements.txt` (scipy / rasterio / matplotlib for georef + digitize).
- **Not touched:** all other CZC source articles and the baseline PDFs in `docs/`.

## 7. Verification

- **Placement:** both exhibits land in §5 between the Inventory subsection and the
  Classification Rubric — integrated (Exhibit 3.1 p. 53 → 3.2 p. 59 → §5.D p. 61) and
  standalone alike.
- **Parity:** every unit opens on an even offset; footer page numbers equal physical
  pages; both exhibits open recto.
- **Regression guard:** with the §5 marker absent, the split yields an empty `03c`
  and a `03b` carrying the full §5.D…§14 body — so the splice is dormant-safe and the
  pre-v0.14 build path is reproduced exactly.
- **Visual QA:** the map renders the recognizable Newcastle network with a coherent
  Type pattern + DRAFT banner; the Inventory table renders 215 alphabetized rows with
  colour-coded Type, ownership, district, and reference columns.

## 8. Notes & carry-forward

- **This is a DRAFT classification.** Two human steps remain before adoption, both
  required regardless of who drafts the map: (1) a minutes-long eyeball of the
  district layer against the official District Map, and (2) Planning-Board review +
  Town-Meeting adoption (all ordinance changes go to Town Meeting under Maine law).
- **The 100 % version is one step away.** When the contractor's exact `districts`
  shapefile arrives, drop it in, re-run the pipeline from the join stage, re-promote
  `inventory.json`, and rebuild — no code changes. The accuracy ceiling rises from
  ~90–95 % to 100 % with the same tooling.
- Adopted human decisions (final Types, corrected widths, nonconformity flags) live
  in `build/street-types/overrides.json` and survive every data refresh.
