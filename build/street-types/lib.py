"""Shared helpers for the Street & Road Type pipeline (build/street-types/).

Conventions:
  - Run the stage scripts from this directory so ``import lib`` resolves
    (``run.sh`` does ``cd`` here).
  - Raw fetched layers + provenance.json live under data/street-types/raw/
    (committed for reproducibility); intermediates under data/street-types/work/
    (gitignored).
"""
from __future__ import annotations

import datetime
import json
import pathlib

import requests
import yaml

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent                      # repo root
DATA = REPO / "data" / "street-types"
RAW = DATA / "raw"
WORK = DATA / "work"
# Canonical output the Typst exhibits consume:
INVENTORY = REPO / "source" / "exhibits" / "street-types" / "inventory.json"
OVERRIDES = HERE / "overrides.json"


def load_config() -> dict:
    with open(HERE / "sources.yml") as f:
        return yaml.safe_load(f)


def arcgis_query(url: str, where: str = "1=1", out_sr: int = 4326,
                 page: int = 1000, timeout: int = 90) -> dict:
    """Page through an ArcGIS REST FeatureServer/MapServer layer ``/query`` and
    return a GeoJSON FeatureCollection dict. Works for both ArcGIS Online hosted
    layers and ArcGIS Server MapServer layers (both support f=geojson + paging)."""
    feats: list = []
    offset = 0
    while True:
        params = {
            "where": where,
            "outFields": "*",
            "f": "geojson",
            "outSR": out_sr,
            "returnGeometry": "true",
            "resultOffset": offset,
            "resultRecordCount": page,
        }
        r = requests.get(url.rstrip("/") + "/query", params=params, timeout=timeout)
        r.raise_for_status()
        d = r.json()
        if isinstance(d, dict) and "error" in d:
            raise RuntimeError(f"ArcGIS error from {url}: {d['error']}")
        batch = d.get("features", [])
        feats.extend(batch)
        if len(batch) < page:        # short page => done
            break
        offset += page
        if offset > 200_000:         # runaway guard
            raise RuntimeError(f"paging guard tripped at {url}")
    return {"type": "FeatureCollection", "features": feats}


def record_provenance(name: str, url: str, where: str, n: int, crs: str) -> None:
    """Append/update a provenance record so a fetch is reproducible + dated."""
    RAW.mkdir(parents=True, exist_ok=True)
    pf = RAW / "provenance.json"
    prov = json.loads(pf.read_text()) if pf.exists() else {}
    prov[name] = {
        "url": url,
        "where": where,
        "features": n,
        "crs": crs,
        "fetched": datetime.date.today().isoformat(),
    }
    pf.write_text(json.dumps(prov, indent=2) + "\n")
