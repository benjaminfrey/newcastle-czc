#!/usr/bin/env python3
"""Stage 04 — classify each segment with a provisional Street/Road Type.

Applies the automatable parts of the §5.D rubric via lib.classify_type:
  - arterials stay R4/R5 in every District (the regional highways);
  - in road-default Districts, MaineDOT functional class governs (Collector -> R1,
    else the District default);
  - in form Districts the Adjacent-District (Table 3.4) test governs regardless of
    functional class, using the per-District overlap fractions (district_fracs from
    03_join) so the more urban District wins where a segment meaningfully touches
    several (the v0.16 form-first / urban-wins amendment).
Then merges overrides.json (Planning-Board decisions), which always win.

District-dependent results stay 'pending' until the digitized districts layer is
present (03_join fills 'districts' + 'district_fracs').

Output: data/street-types/work/classified.gpkg

Run:  cd build/street-types && .venv/bin/python 04_classify.py
"""
import json

import geopandas as gpd

import lib

# The §5.D classification rule lives in lib.classify_type so the pipeline and the
# one-off inventory re-classification share one implementation (Table 3.4 + the v0.16
# form-first amendment, keyed off the per-District overlap fractions from 03_join).


def main() -> None:
    segs = gpd.read_file(lib.WORK / "joined.gpkg")
    ov = {}
    if lib.OVERRIDES.exists():
        ov = json.loads(lib.OVERRIDES.read_text()).get("overrides", {})

    prov, ptype, psrc, nonconf, owner = [], [], [], [], []
    for _, r in segs.iterrows():
        o = ov.get(r["id"], {})
        fr = lib.parse_fracs(r.get("district_fracs", ""))
        prov_t, _ = lib.classify_type(r.get("fedfunccls", ""), fr, None)
        final_t, src = lib.classify_type(r.get("fedfunccls", ""), fr, o.get("type"))
        prov.append(prov_t or "")
        ptype.append(final_t or "")
        psrc.append(src)
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
