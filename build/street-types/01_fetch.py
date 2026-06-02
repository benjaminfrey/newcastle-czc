#!/usr/bin/env python3
"""Stage 01 — fetch raw source layers for the configured town and archive them.

Reads build/street-types/sources.yml; for each source, runs a paged ArcGIS REST
query (f=geojson, EPSG:4326) filtered to the town, writes
data/street-types/raw/<name>.geojson, and records provenance (URL, WHERE, count,
date) in data/street-types/raw/provenance.json.

Run:  cd build/street-types && .venv/bin/python 01_fetch.py
"""
import json

import lib


def main() -> None:
    cfg = lib.load_config()
    lib.RAW.mkdir(parents=True, exist_ok=True)
    print(f"Town: {cfg['town']}  ·  working CRS: {cfg['working_crs']}")
    for name, src in cfg["sources"].items():
        print(f"[fetch] {name}\n        {src['url']}\n        WHERE {src['where']}")
        fc = lib.arcgis_query(src["url"], src["where"])
        n = len(fc["features"])
        out = lib.RAW / f"{name}.geojson"
        out.write_text(json.dumps(fc))
        lib.record_provenance(name, src["url"], src["where"], n, "EPSG:4326")
        size_kb = out.stat().st_size / 1024
        print(f"        -> {n} features  ·  {size_kb:.0f} KiB  ·  {out.relative_to(lib.REPO)}")
    print("Done. Provenance:", (lib.RAW / "provenance.json").relative_to(lib.REPO))


if __name__ == "__main__":
    main()
