# Street & Road Type pipeline

A repeatable pipeline that turns authoritative public GIS layers into one
`inventory.json`, from which **Exhibit 3.1** (the Inventory table) and **Exhibit
3.2** (the Street & Road Type Map) both render. It implements Article 3 §5.C: the
binding content is each segment's assigned **Type**; everything else is recorded
for reference (§5.C.3).

Re-runnable when roads change, the District Map is amended, or MaineDOT
reclassifies — adopted human decisions are preserved in `overrides.json`.

---

## 1. One-time setup (geo venv)

The routine CZC build needs only PyMuPDF; this pipeline adds a geospatial stack,
kept in a local venv:

```sh
python3 -m venv build/street-types/.venv
build/street-types/.venv/bin/pip install -r build/street-types/requirements.txt
```

(`pyogrio`/`rasterio` ship GDAL in their wheels — no system GDAL needed.)

## 2. Run the pipeline

```sh
bash build/street-types/run.sh            # stages 01 -> 05
bash build/street-types/run.sh --from 3   # resume at the join stage
```

| Stage | Script | Does |
|---|---|---|
| 01 | `01_fetch.py` | fetch E911 roads, MaineDOT roads, town boundary → `data/street-types/raw/` (+ `provenance.json`) |
| 02 | `02_prepare.py` | reproject, dissolve by name, split at **public-road** intersections → `work/segments.gpkg` |
| 03 | `03_join.py` | adjacent District (if digitized), MaineDOT functional class, ownership → `work/joined.gpkg` |
| 04 | `04_classify.py` | provisional Type (Table 3.4 + functional class) + `overrides.json` → `work/classified.gpkg` |
| 05 | `05_export.py` | `work/inventory.json` + `work/review.csv` + `work/review.gpkg` |

Sources + the working CRS (EPSG:26919, UTM 19N) are pinned in `sources.yml`.

## 3. Phase 0 — digitize the districts (the one manual input)

Auto-classification of Local/private roads needs the zoning Districts as polygons.

1. **Georeference** `source/exhibits/district-maps/exhibit-1.1-district-map.png`
   in QGIS (control points from road intersections / town-boundary corners that
   you can match to the fetched E911 roads + boundary), export a GeoTIFF in
   EPSG:26919.
2. **Extract** polygons by colour:
   ```sh
   cd build/street-types
   .venv/bin/python 00_digitize_districts.py --raster /path/to/district-map-georef.tif --tol 35
   ```
   → `data/street-types/work/districts.gpkg`. (Dry-run on the PNG with
   `--dry-run` validates the mechanism in pixel space.)
3. **Clean up** in QGIS — district fills are blended over the aerial, so expect to
   tune `--tol`, merge slivers, and confirm the ~13 polygons. Hand-tracing is the
   fallback. The district codes must read `D1`…`D6` / `SD-Historic` etc. (matching
   `04_classify.py`'s Table 3.4 keys).

Once `districts.gpkg` exists, re-run `run.sh --from 3` and the district-based
classification activates (the ~156 currently-"pending" segments classify).

## 4. Review + adopt (the non-automatable step)

1. Open `work/review.csv` (or `review.gpkg` in QGIS). Each row shows the auto Type
   + its evidence (district, functional class, ownership) + flags.
2. Apply the §5.D rubric by hand where needed (built character, ROW/cartway,
   tie-breakers) and record decisions in **`overrides.json`** — final Type, manual
   nonconformity notes, corrected `row_ft`/`traveled_ft`, ownership fixes. Example:
   ```json
   { "overrides": { "main-street-1": { "type": "S1", "nonconformity": "ROW 38 ft, narrower than Type" } } }
   ```
   Re-run `run.sh --from 4` to merge. `overrides.json` is version-controlled and
   survives every future data refresh.
3. When the Planning Board adopts the classification, **promote** the working
   inventory to the canonical path:
   ```sh
   cp data/street-types/work/inventory.json source/exhibits/street-types/inventory.json
   ```

## 5. Render the exhibits

```sh
# Exhibit 3.2 — Type Map
typst compile source/street-type-map.typ /tmp/ex32.pdf --root . --font-path style/fonts \
  --input data=/data/street-types/work/inventory.json --input page_offset=2
# Exhibit 3.1 — Inventory table
typst compile source/street-type-inventory.typ /tmp/ex31.pdf --root . --font-path style/fonts \
  --input data=/data/street-types/work/inventory.json --input page_offset=2
```

Both auto-scale the projected geometry to the page; unclassified segments draw
gray and the disclaimer banner comes from the data's `_meta.banner`.

## 6. Wiring the exhibits into Article 3 §5 (at adoption — not yet done)

Deliberately deferred so a draft classification never lands in a shipped CZC. To
activate once `source/exhibits/street-types/inventory.json` is adopted:

1. Add a marker in `source/article-03-streets-roads-driveways.md` §5.C (after the
   Inventory paragraph), e.g. `<!-- STREET-TYPE-EXHIBITS -->`.
2. Extend `build/split-article-03.py` to also split Article 3 at that second
   marker (yielding a `03c` part), mirroring the existing `<!-- TYPE-PAGES -->`
   split.
3. In `build/build-full-czc.sh` and `build/build-article-3.sh`, splice
   `street-type-inventory.typ` + `street-type-map.typ` at the marker position
   (render order `[03a, plates, 03b, inventory.typ, map.typ, 03c]`), threading the
   cumulative even `page_offset` + `footer_date` and padding for parity — exactly
   as the Type plates and District maps are spliced today.
4. Rebuild; the two exhibits land in §5 of both the integrated CZC and the
   standalone Article 3, and page-count parity re-derives.

## 7. Repeatability

- `data/street-types/raw/` (committed, with `provenance.json`) freezes the source
  pull; `work/` (gitignored) is regenerated.
- `overrides.json` carries adopted decisions across re-runs.
- To retarget another town: change `town` + the WHERE clauses in `sources.yml`.
