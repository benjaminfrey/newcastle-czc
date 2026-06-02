#!/usr/bin/env python3
"""Stage 00 — digitize district polygons from a georeferenced District Map raster.

Classifies the raster's pixels against the known District fill colours (taken from
source/article-02-data.json) and polygonizes each colour into a district polygon.

FIRST georeference the District Map exhibit in QGIS (control points from road
intersections / the town boundary) and export a GeoTIFF in the working CRS; pass
it with --raster. Then 03_join / 04_classify pick up data/street-types/work/
districts.gpkg automatically.

  cd build/street-types
  # dry run on the held PNG to validate colour extraction (pixel space, no CRS):
  .venv/bin/python 00_digitize_districts.py \
      --raster ../../source/exhibits/district-maps/exhibit-1.1-district-map.png --dry-run
  # real run on a georeferenced GeoTIFF:
  .venv/bin/python 00_digitize_districts.py --raster /path/to/district-map-georef.tif

Colour extraction is a FIRST CUT — district fills printed over the aerial basemap
are blended, so expect to widen --tol and clean the result in QGIS (hand-tracing
is the fallback). The point is a repeatable starting layer, not a finished one.
"""
import argparse
import json
import sys

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize, shapes, sieve
from shapely.geometry import shape
from shapely.ops import unary_union

import lib


def district_palette() -> dict:
    """Map a district code (D1..D6, SD-Historic, ...) to its (r,g,b) fill.

    Prefers the District Map's own KEY-sampled colours (key-colors.json, from
    sample_key.py) over the Article-2 badge palette — the map uses a different
    colour scheme, so the badge colours under-extracted several districts."""
    kc = lib.HERE / "key-colors.json"
    if kc.exists():
        return {k: tuple(v) for k, v in json.loads(kc.read_text()).items()}
    ds = json.loads((lib.REPO / "source" / "article-02-data.json").read_text())
    pal = {}
    for d in ds:
        code, name = d.get("code", ""), d.get("name", "")
        key = code if (code[:1] == "D" and code[1:].isdigit()) else f"SD-{name.title()}"
        h = d["color"].lstrip("#")
        pal[key] = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return pal


def polygonize(mask_u8, transform, code, feats):
    polys = [shape(g) for g, v in shapes(mask_u8, mask=mask_u8.astype(bool), transform=transform) if v == 1]
    if polys:
        feats.append({"district": code, "geometry": unary_union(polys)})
    return len(polys)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raster", required=True)
    ap.add_argument("--tol", type=float, default=30.0, help="RGB match tolerance (threshold mode)")
    ap.add_argument("--min-px", type=int, default=400, help="drop blobs smaller than this (px)")
    ap.add_argument("--full-coverage", action="store_true",
                    help="assign every in-town pixel to its nearest district colour (gapless)")
    ap.add_argument("--dry-run", action="store_true", help="pixel-space output (ungeoreferenced raster)")
    a = ap.parse_args()

    pal = district_palette()
    with rasterio.open(a.raster) as src:
        rgb = src.read()[:3].astype("int32")        # int32: avoid overflow when squaring
        transform, crs = src.transform, src.crs
    H, W = rgb.shape[1], rgb.shape[2]
    feats = []

    if a.full_coverage:
        if a.dry_run or crs is None:
            sys.exit("--full-coverage needs a georeferenced raster (run georef.py first)")
        # restrict to the real town footprint, then label each pixel by nearest colour
        town = unary_union(gpd.read_file(lib.RAW / "town_boundary.geojson").to_crs(crs).geometry.values)
        town_mask = rasterize([(town, 1)], out_shape=(H, W), transform=transform, dtype="uint8").astype(bool)
        codes = list(pal.keys())
        flat = rgb.reshape(3, -1).T                  # (H*W, 3)
        best = np.full(flat.shape[0], np.inf)
        lbl = np.zeros(flat.shape[0], dtype="int16")
        for i, code in enumerate(codes):
            d = ((flat - np.array(pal[code])) ** 2).sum(1)
            upd = d < best
            best[upd] = d[upd]; lbl[upd] = i
        lbl = lbl.reshape(H, W)
        for i, code in enumerate(codes):
            m = ((lbl == i) & town_mask).astype("uint8")
            if m.sum() == 0:
                continue
            m = sieve(m, size=a.min_px)
            n = polygonize(m, transform, code, feats)
            if n:
                print(f"  {code:18} {int(((lbl == i) & town_mask).sum()):>8} px  ->  {n} polygon(s)")
    else:
        for code, (r, g, b) in pal.items():
            dist = np.sqrt((rgb[0] - r) ** 2 + (rgb[1] - g) ** 2 + (rgb[2] - b) ** 2)
            raw = (dist <= a.tol).astype("uint8")
            if raw.sum() == 0:
                print(f"  {code:18} no pixels matched"); continue
            n = polygonize(sieve(raw, size=a.min_px), transform, code, feats)
            print(f"  {code:18} {int(raw.sum()):>7} px  ->  {n} polygon(s)" if n
                  else f"  {code:18} {int(raw.sum()):>7} px matched, all sieved out")

    gdf = gpd.GeoDataFrame(feats, geometry="geometry", crs=(None if a.dry_run else crs))
    lib.WORK.mkdir(parents=True, exist_ok=True)
    # Dry runs write a separate file so a pixel-space result never feeds 03/04.
    out = lib.WORK / ("districts-dryrun.gpkg" if a.dry_run else "districts.gpkg")
    gdf.to_file(out, driver="GPKG")
    tag = ("  (DRY RUN — pixel space, NOT geographic)" if a.dry_run
           else "  (full-coverage)" if a.full_coverage else "")
    print(f"[digitize] {len(gdf)} districts  ->  {out.relative_to(lib.REPO)}{tag}")


if __name__ == "__main__":
    main()
