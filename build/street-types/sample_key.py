#!/usr/bin/env python3
"""Sample the District Map's KEY swatch colours -> key-colors.json.

The District Map uses its own colour scheme (the contractor's), which differs from
the Article-2 badge palette — so matching map fills against the badge colours
under-extracted several districts (D6, SD-Historic, SD-Conservation, SD-Fabrication).
This samples the actual rendered swatch colour for each district straight from the
map's KEY, giving 00_digitize_districts.py + georef.py the correct match targets.

The KEY geometry below (swatch column x, first-swatch row, row pitch) is measured
from source/exhibits/district-maps/exhibit-1.1-district-map.png; re-measure if the
map is ever replaced. This is a draft aid only — the adopted map will come from the
exact district shapefile (no raster sampling).

  cd build/street-types && .venv/bin/python sample_key.py
"""
import json

import numpy as np
import rasterio

import lib

# Districts in KEY order, top to bottom (Required Shopfront / Scenic View follow,
# and are not districts).
ORDER = ["D1", "D2", "D3", "D4", "D5", "D6", "SD-Campus", "SD-Marine",
         "SD-Highway Commercial", "SD-Rural Highway", "SD-Fabrication", "SD-Civic",
         "SD-Conservation", "SD-Historic"]
TOP0, PITCH = 1847, 46.0       # D1 swatch top row; ~46 px between swatches
CX0, CX1 = 1310, 1342          # swatch column (x)


def main() -> None:
    raster = lib.REPO / "source/exhibits/district-maps/exhibit-1.1-district-map.png"
    with rasterio.open(raster) as src:
        rgb = src.read()[:3].astype(int)
    key = {}
    for k, code in enumerate(ORDER):
        t = int(round(TOP0 + PITCH * k))
        box = rgb[:, t + 6:t + 22, CX0:CX1]
        key[code] = [int(np.median(box[i])) for i in range(3)]
    out = lib.HERE / "key-colors.json"
    out.write_text(json.dumps(key, indent=1) + "\n")
    print(f"sampled {len(key)} district swatch colours -> {out.relative_to(lib.REPO)}")
    for code, c in key.items():
        print(f"  {code:22} {tuple(c)}")


if __name__ == "__main__":
    main()
