# Summary of Changes — v0.13-draft

**Release type:** **Tooling — ships the repeatable Street & Road Type pipeline that produces the §5.C Inventory (Exhibit 3.1) and the Street & Road Type Map (Exhibit 3.2). No change to the rendered CZC.** v0.12 established the regulatory structure (binding Type per segment + an illustrative map) and a render engine working on *sample* data. This release adds the **data engine** that turns authoritative public GIS layers into the real `inventory.json`, plus the Exhibit 3.1 table renderer. The integrated CZC and standalone Article 3 PDFs are **byte-unchanged from v0.12** — the exhibits are wired into Article 3 §5 only at adoption (see §6), so no draft classification lands in a deliverable.

**Compares against:** [v0.12-draft](../v0.12-draft/). Source `article-03` and all rendered deliverables are unchanged; this release is new tooling under `build/street-types/` + two Typst renderers + the archived source data.

## 1. What this adds

A scripted **GeoPandas pipeline** (`build/street-types/`) — re-runnable, deterministic, with adopted decisions preserved across runs:

| Stage | Script | Output |
|---|---|---|
| 01 | `01_fetch.py` | fetch E911 roads, MaineDOT roads, town boundary for the town → `data/street-types/raw/` + `provenance.json` |
| 02 | `02_prepare.py` | reproject (EPSG:26919), dissolve by name, split at **public-road** intersections → segments + termini |
| 03 | `03_join.py` | adjacent District (when digitized), MaineDOT functional class, ownership (derived online) |
| 04 | `04_classify.py` | provisional Type (Table 3.4 + functional class) + `overrides.json` merge |
| 05 | `05_export.py` | `work/inventory.json` + `work/review.csv` + `work/review.gpkg` |
| 00 | `00_digitize_districts.py` | colour-extract district polygons from a georeferenced District Map raster |

Plus `run.sh` (chains 01→05), `sources.yml` (pinned endpoints), `overrides.json` (durable human decisions), and a full `README.md`.

**Renderers:**
- `source/street-type-inventory.typ` *(new)* — Exhibit 3.1 Inventory **table** (binding Type column + reference columns), Article-3 chrome, multi-page.
- `source/street-type-map.typ` *(refined)* — handles unclassified (pending) segments in gray + an "Unclassified" legend entry; the disclaimer banner now reads from the data's `_meta.banner` (so a real render says "Draft classification…", not "Sample data").

Both render from one `inventory.json`, so the table and map never drift.

## 2. Built and validated on live Newcastle data

Run end-to-end against the live MEGIS/MaineDOT services:
- **Fetched:** E911 roads (326), MaineDOT public roads (192), town boundary (28 polygons).
- **Prepared:** 148 named roads → **215 segments** (42 public / 106 private), each with termini drawn from public-road intersections.
- **Joined:** ownership derived entirely online — **Private Road 105 / Town Way 80 / State Highway 28** (2 flagged); MaineDOT functional class attached.
- **Classified (partial):** **59** segments (46 R1 collectors + 13 R4 arterials) from functional class; **156 pending** the District overlay.
- **Rendered:** a real **Exhibit 3.2** (Newcastle's actual network, Route 1 as R4, collectors as R1, the rest gray-pending) and **Exhibit 3.1** (215-row table, 4 pages).

A network-size finding for the record: Newcastle has ~148 named ways (~61 public roads), more than the early "≤50" estimate; the pipeline scales fine.

## 3. What you (Ben) supply to finish the real map

- **Districts (Phase 0):** georeference the District Map raster in QGIS, run `00_digitize_districts.py`, clean up the polygons → `districts.gpkg`. This unblocks classification of the 156 pending (Local/private) segments.
- **Review + adopt:** work `review.csv`, record final Types / nonconformity / corrected widths in `overrides.json`, then promote `work/inventory.json` → `source/exhibits/street-types/inventory.json`.

## 4. Repeatability

Raw inputs are archived with provenance (committed); `work/` is regenerated; `overrides.json` carries adopted decisions across data refreshes; `run.sh --from N` resumes. Retarget another town by editing `sources.yml`.

## 5. Files added / changed

- **`build/street-types/`** *(new)* — `00_digitize_districts.py`, `01_fetch.py` … `05_export.py`, `lib.py`, `run.sh`, `sources.yml`, `overrides.json`, `requirements.txt`, `README.md`, `.gitignore`.
- **`source/street-type-inventory.typ`** *(new)* — Exhibit 3.1 table renderer.
- **`source/street-type-map.typ`** *(refined)* — unclassified handling + `_meta.banner` disclaimer.
- **`data/street-types/raw/`** *(new)* — archived Newcastle E911/MaineDOT/boundary GeoJSON + `provenance.json` (working/ is gitignored).

**Not touched:** every CZC source article, the build pipeline, and all rendered deliverables — identical to v0.12.

## 6. Wiring into Article 3 §5 (deferred to adoption — by design)

Wiring the exhibits into the production build is intentionally **not** done here, so a draft classification never ships in the CZC. The README §6 specifies the exact activation: add a `<!-- STREET-TYPE-EXHIBITS -->` marker in §5.C, extend `split-article-03.py` for the second marker, splice `street-type-inventory.typ` + `street-type-map.typ` in both build scripts (mirroring the Type-plate splice), promote `inventory.json`, and rebuild. A clean, isolated step once the classification is adopted.

## 7. Verification

- Geo stack installs + imports (geopandas 1.1.3 / GDAL 3.11.4 / rasterio 1.5.0).
- `run.sh` reproduces `work/inventory.json` deterministically from the archived raw data.
- `street-type-map.typ` and `street-type-inventory.typ` render the live `inventory.json` to a 1-page map + 4-page table with correct Article-3 chrome and parity.
- `00_digitize_districts.py` dry-run extracts district polygons by colour (first-cut; tolerance/cleanup expected).
- The integrated CZC + standalone Article 3 deliverables are unchanged from v0.12 (no build-input file was modified).
