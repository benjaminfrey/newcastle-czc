#!/usr/bin/env python3
"""Georeference the District Map raster WITHOUT manual control points.

The only ground truth needed is the authoritative town-boundary polygon (already
fetched by 01_fetch). The coloured-district fills cover the town, so this seeds a
north-up affine from the coloured-extent <-> town-boundary bbox match, then
optimizes (sx, sy, tx, ty) to maximize IoU between the rasterized town polygon and
the coloured-district mask. Writes a georeferenced GeoTIFF + the transform JSON,
for 00_digitize_districts.py.

  cd build/street-types
  .venv/bin/python georef.py \
     --raster ../../source/exhibits/district-maps/exhibit-1.1-district-map.png

Accuracy is DRAFT-grade (one tie source). Verify the result (A3) and, for the
adopted map, re-run with the exact district shapefile instead.
"""
import argparse
import json

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize, sieve
from rasterio.transform import Affine
from scipy.optimize import minimize
from shapely.ops import unary_union

import lib


def palette_rgb():
    # Use the Article-2 BADGE palette for the alignment mask (NOT the KEY colours):
    # the KEY's pale D1 (~white) floods near-white pixels and the mask stops being
    # a town-shape proxy, collapsing the optimization. The badge greens/tans mark
    # the developed + rural land well enough to outline the town.
    ds = json.loads((lib.REPO / "source/article-02-data.json").read_text())
    return [tuple(int(d["color"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for d in ds]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raster", required=True)
    ap.add_argument("--out", default="/tmp/districtmap-georef.tif")
    ap.add_argument("--tol", type=float, default=50.0)
    ap.add_argument("--min-px", type=int, default=300)
    a = ap.parse_args()

    with rasterio.open(a.raster) as src:
        bands = src.read()[:3]
    rgb = bands.astype("int32")
    H, W = rgb.shape[1], rgb.shape[2]

    mask = np.zeros((H, W), bool)
    for (r, g, b) in palette_rgb():
        mask |= np.sqrt((rgb[0] - r) ** 2 + (rgb[1] - g) ** 2 + (rgb[2] - b) ** 2) <= a.tol
    mask = sieve(mask.astype("uint8"), size=a.min_px).astype(bool)

    crs = lib.load_config()["working_crs"]
    town = unary_union(gpd.read_file(lib.RAW / "town_boundary.geojson").to_crs(crs).geometry.values)
    minx, miny, maxx, maxy = town.bounds

    ys, xs = np.where(mask)
    c0, c1 = np.percentile(xs, [0.5, 99.5])
    r0, r1 = np.percentile(ys, [0.5, 99.5])
    sx0, sy0 = (maxx - minx) / (c1 - c0), (maxy - miny) / (r1 - r0)
    seed = np.array([sx0, sy0, minx - c0 * sx0, maxy + r0 * sy0])

    def iou(p):
        sx, sy, tx, ty = p
        if sx <= 0 or sy <= 0:
            return 0.0
        A = Affine(sx, 0, tx, 0, -sy, ty)
        tm = rasterize([(town, 1)], out_shape=(H, W), transform=A, dtype="uint8").astype(bool)
        inter = np.logical_and(tm, mask).sum()
        union = np.logical_or(tm, mask).sum()
        return inter / union if union else 0.0

    seed_iou = iou(seed)
    res = minimize(lambda p: -iou(p), seed, method="Nelder-Mead",
                   options=dict(xatol=1e-3, fatol=1e-4, maxiter=400))
    sx, sy, tx, ty = res.x
    A = Affine(sx, 0, tx, 0, -sy, ty)
    print(f"seed IoU {seed_iou:.3f}  ->  optimized IoU {-res.fun:.3f}")
    print(f"transform  sx={sx:.3f} sy={sy:.3f}  tx={tx:.1f} ty={ty:.1f}")

    prof = dict(driver="GTiff", height=H, width=W, count=3, dtype="uint8", crs=crs, transform=A)
    with rasterio.open(a.out, "w", **prof) as dst:
        dst.write(bands)
    lib.WORK.mkdir(parents=True, exist_ok=True)
    tj = lib.WORK / "georef-transform.json"
    tj.write_text(json.dumps({"raster": a.raster, "crs": crs,
                              "affine": [A.a, A.b, A.c, A.d, A.e, A.f],
                              "seed_iou": round(seed_iou, 4), "iou": round(-res.fun, 4)}, indent=2))
    print("wrote", a.out, "+", tj.relative_to(lib.REPO))


if __name__ == "__main__":
    main()
