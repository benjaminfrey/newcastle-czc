#!/usr/bin/env python3
"""Stage 04 — classify each segment with a provisional Street/Road Type.

Applies the automatable parts of the §5.D rubric:
  - test 4 (MaineDOT functional class): Arterial -> R4/R5 (by district), Collector -> R1;
  - test 1 (adjacent District -> default Type via Table 3.4) for Local / private /
    unmatched roads.
Then merges overrides.json (Planning-Board decisions), which always win.

District-dependent results stay 'pending' until the digitized districts layer is
present (03_join fills the 'districts' column); collectors + arterials classify
immediately from MaineDOT data.

Output: data/street-types/work/classified.gpkg

Run:  cd build/street-types && .venv/bin/python 04_classify.py
"""
import json

import geopandas as gpd

import lib

# Table 3.4 — primary default Type per District (the rubric's test-1 target).
DEFAULT_TYPE = {
    "D1": "R2", "D2": "S3", "D3": "S3", "D4": "S3", "D5": "S2", "D6": "S1",
    "SD-Historic": "S3", "SD-Conservation": "R2", "SD-Highway Commercial": "R4",
    "SD-Rural Highway": "R5", "SD-Campus": "S3", "SD-Marine": "S3",
    "SD-Fabrication": "S3", "SD-Civic": None,    # follows the adjacent district
}
RURAL_ARTERIAL_DISTRICTS = {"SD-Rural Highway", "D1", "SD-Conservation"}


def primary_district(districts: str) -> str:
    return (districts or "").split(";")[0].strip()


def auto_type(funcclass: str, district: str):
    """Return (provisional_type, source) from the automatable rubric tests."""
    fc = (funcclass or "").lower()
    if "arterial" in fc:
        return ("R5" if district in RURAL_ARTERIAL_DISTRICTS else "R4"), "funcclass"
    if "collector" in fc:
        return "R1", "funcclass"
    if district:                                  # Local / private -> District default
        return DEFAULT_TYPE.get(district), "district"
    return None, ""                               # pending until districts exist


def main() -> None:
    segs = gpd.read_file(lib.WORK / "joined.gpkg")
    ov = {}
    if lib.OVERRIDES.exists():
        ov = json.loads(lib.OVERRIDES.read_text()).get("overrides", {})

    prov, ptype, psrc, nonconf, owner = [], [], [], [], []
    for _, r in segs.iterrows():
        o = ov.get(r["id"], {})
        d = primary_district(r.get("districts", ""))
        t, src = auto_type(r.get("fedfunccls", ""), d)
        prov.append(t or "")
        final = o["type"] if "type" in o else t
        ptype.append(final or "")
        psrc.append("override" if "type" in o else src)
        nonconf.append(o.get("nonconformity", ""))
        owner.append(o.get("ownership", r.get("ownership", "")))
    segs["provisional_type"] = prov
    segs["type"] = ptype
    segs["type_source"] = psrc
    segs["nonconformity"] = nonconf
    segs["ownership"] = owner

    out = lib.WORK / "classified.gpkg"
    segs.to_file(out, driver="GPKG")
    nclass = int((segs["type"] != "").sum())
    npend = int((segs["type"] == "").sum())
    print(f"[classify] {nclass} classified · {npend} pending (need districts)  ->  {out.relative_to(lib.REPO)}")
    print("  by source:", segs["type_source"].value_counts().to_dict())
    print("  by type:", {k: v for k, v in segs["type"].value_counts().to_dict().items() if k})


if __name__ == "__main__":
    main()
