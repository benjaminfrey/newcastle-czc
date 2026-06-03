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


# --- §5.D classification rule (Table 3.4 + the v0.16 form-first amendment) ----------
# Default Type per District (Table 3.4, primary target).
DEFAULT_TYPE = {
    "D1": "R2", "D2": "S3", "D3": "S3", "D4": "S3", "D5": "S2", "D6": "S1",
    "SD-Historic": "S3", "SD-Conservation": "R2", "SD-Highway Commercial": "R4",
    "SD-Rural Highway": "R5", "SD-Campus": "S3", "SD-Marine": "S3",
    "SD-Fabrication": "S3", "SD-Civic": None,        # SD-Civic follows the adjacent district
}
# Districts whose default Type is a Road type — here MaineDOT functional class governs
# (§5.D ¶d). In every other (form) District the Adjacent-District test governs.
ROAD_DEFAULT_DISTRICTS = {"D1", "SD-Conservation", "SD-Highway Commercial", "SD-Rural Highway"}
RURAL_ARTERIAL_DISTRICTS = {"SD-Rural Highway", "D1", "SD-Conservation"}
# Urbanity rank among the FORM (Street-default) Districts: where a segment meaningfully
# touches more than one, the more urban one governs. Higher = more urban.
FORM_RANK = {"D6": 6, "D5": 5, "SD-Historic": 4, "D3": 4, "D4": 3,
             "D2": 2, "SD-Campus": 2, "SD-Marine": 2, "SD-Fabrication": 2}
# A District must cover at least this fraction of a segment to govern it via the form
# test — so a road merely clipping the edge of a village polygon stays rural.
MIN_DISTRICT_FRAC = 0.25


def governing_district(fracs: dict):
    """Pick the District that governs a segment's Type from its per-District overlap
    fractions. A FORM District covering >= MIN_DISTRICT_FRAC wins (most urban among
    them); otherwise the predominant (largest-overlap) District governs."""
    if not fracs:
        return None
    meaningful = {d: f for d, f in fracs.items() if f >= MIN_DISTRICT_FRAC}
    form = [d for d in meaningful if d in FORM_RANK]
    if form:
        return max(form, key=lambda d: FORM_RANK[d])
    pool = meaningful or fracs
    return max(pool, key=pool.get)


def classify_type(funcclass: str, district_fracs: dict, override=None):
    """Automatable part of the §5.D rubric. Returns (type, source).

    - Arterials are the regional highways and stay R4/R5 in every District.
    - In a road-default District, MaineDOT functional class governs (Collector -> R1,
      else the District default).
    - In a form District the Adjacent-District test governs regardless of functional
      class (a collector through the village takes the village Type; e.g. a Main Street
      that is a State Highway is S1) — realized through the Section 12 coordination.
    - overrides.json always wins.
    """
    if override:
        return override, "override"
    fc = (funcclass or "").lower()
    if not district_fracs:                            # outside every District (rare)
        if "arterial" in fc:
            return "R4", "funcclass"
        if "collector" in fc:
            return "R1", "funcclass"
        return None, "pending"
    predominant = max(district_fracs, key=district_fracs.get)
    if "arterial" in fc:
        return ("R5" if predominant in RURAL_ARTERIAL_DISTRICTS else "R4"), "arterial"
    gov = governing_district(district_fracs)
    if gov in ROAD_DEFAULT_DISTRICTS:
        if "collector" in fc:
            return "R1", "collector"
        return DEFAULT_TYPE.get(gov), "district"
    return DEFAULT_TYPE.get(gov), "district-form"


def parse_fracs(s: str) -> dict:
    """Parse a 'code:frac;code:frac' district_fracs string into {code: float}."""
    out = {}
    for part in (s or "").split(";"):
        part = part.strip()
        if ":" in part:
            code, f = part.rsplit(":", 1)
            try:
                out[code.strip()] = float(f)
            except ValueError:
                pass
    return out


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
