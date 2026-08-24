#!/usr/bin/env python3
"""Stage 05 — export the canonical inventory + a human-review file.

Writes (under data/street-types/work/):
  - inventory.json  — the schema the Typst exhibits consume (geometry [x,y] in the
    working CRS + binding Type + reference fields). PROMOTE to
    source/exhibits/street-types/inventory.json only after the classification is
    reviewed + adopted (so a draft never lands in a deliverable).
  - review.csv      — flat table for QGIS / spreadsheet review (auto Type + evidence)
  - review.gpkg     — classified geometry for QGIS

Run:  cd build/street-types && .venv/bin/python 05_export.py
"""
import csv
import json

import geopandas as gpd

import lib


def coords_of(geom):
    if geom.geom_type == "LineString":
        return [[round(x, 2), round(y, 2)] for x, y in geom.coords]
    if geom.geom_type == "MultiLineString":
        longest = max(geom.geoms, key=lambda g: g.length)
        return [[round(x, 2), round(y, 2)] for x, y in longest.coords]
    return []


# Art 3 §7.C.7's driveway threshold is a count of DWELLINGS, and the only layer
# that can answer it is the E-911 ADDRESS POINTS (one record per addressed
# structure). NOT the road layer's L_ADD_FROM/L_ADD_TO ranges -- those are
# addressing CAPACITY windows: measured 2026-08-24, Barrol Point Road (a driveway
# serving one house) reads 2-24, identical to Academy Hill, a real Neighborhood
# Street. Ranges count nothing.
#
# REVIEW AID ONLY. This is decision support for the §5.C.3.g present-use review,
# never a determination -- §7.C.8 decides what is a Driveway, whatever is counted
# here. `unknown_type` matters as much as `residential`: 311 of Newcastle's 1227
# points carry no PLACE_TYPE at all, so `residential=0, unknown_type=2` means NOT
# REVIEWED, not NOT PRESENT, and must never be read as an empty segment.
RESIDENTIAL_PLACE_TYPES = {
    "Residential", "Single Family", "Multi Family", "Duplex", "Mobile Home", "Apartment",
}
ADDRESS_MATCH_M = 60.0   # nearest-segment tolerance; 219/1227 fall outside it


def address_counts(segs, crs):
    """{segment_id: {residential, unknown_type, total}}; empty if the layer is absent."""
    path = lib.RAW / "e911_addresses.geojson"
    if not path.exists():
        print("[export] no e911_addresses.geojson — address counts skipped")
        return {}
    try:
        ap = gpd.read_file(path).to_crs(crs)
        pt = ap["PLACE_TYPE"] if "PLACE_TYPE" in ap.columns else None
        ap["_res"] = pt.isin(RESIDENTIAL_PLACE_TYPES) if pt is not None else False
        ap["_unk"] = (pt.isna() | (pt == "")) if pt is not None else True
        j = gpd.sjoin_nearest(ap, segs[["id", "geometry"]], how="left",
                              max_distance=ADDRESS_MATCH_M, distance_col="_d")
        g = j.groupby("id").agg(res=("_res", "sum"), unk=("_unk", "sum"), tot=("_res", "size"))
        unmatched = int(len(ap) - j["id"].notna().sum())
        print(f"[export] address points: {len(ap)} ({unmatched} >{ADDRESS_MATCH_M:.0f} m from any segment)")
        return {i: {"residential": int(r.res), "unknown_type": int(r.unk), "total": int(r.tot)}
                for i, r in g.iterrows()}
    except Exception as exc:  # noqa: BLE001
        print(f"[export] address counts skipped: {exc}")
        return {}


def main() -> None:
    cfg = lib.load_config()
    segs = gpd.read_file(lib.WORK / "classified.gpkg")

    # An override entry may carry "exclude": true to drop a source record that is
    # not a real thoroughfare segment — e.g. an orphan digitizing fragment in the
    # E-911 centerlines with no connection at either end. Excluding here (rather
    # than deleting from the promoted inventory by hand) makes the decision stick
    # across pipeline re-runs, like every other override.
    ov = {}
    if lib.OVERRIDES.exists():
        ov = json.loads(lib.OVERRIDES.read_text()).get("overrides", {})

    addr = address_counts(segs, cfg["working_crs"])

    out_segments, excluded = [], []
    for _, r in segs.iterrows():
        if ov.get(r["id"], {}).get("exclude"):
            excluded.append(r["id"])
            continue
        out_segments.append({
            "id": r["id"],
            "name": r["name"],
            "termini": [r.get("from_terminus", ""), r.get("to_terminus", "")],
            "type": (r.get("type", "") or None),
            "ownership": (r.get("ownership", "") or None),
            "row_ft": None,            # reference — fill during review/overrides
            "traveled_ft": None,       # reference — fill during review/overrides
            "districts": [d.strip() for d in (r.get("districts", "") or "").split(";") if d.strip()],
            "maindot": (r.get("fedfunccls", "") or None),
            "nonconformity": (r.get("nonconformity", "") or None),
            # Art 3 §5.C.3.g — REFERENCE only. "Driveway" records that the segment
            # functions today as a driveway, so Exhibit 3.1 can show Type D with the
            # recorded Type as the conversion Type. It never changes `type` (which
            # stays the Type that would apply on conversion) and it is not what makes
            # an access way a Driveway — §7.C.8 does that, whatever is recorded here.
            # Absent/None = not yet reviewed, which §7.C.8 also protects.
            "present_use": (ov.get(r["id"], {}).get("present_use") or None),
            "addresses": addr.get(r["id"], {"residential": 0, "unknown_type": 0, "total": 0}),
            "geometry": coords_of(r.geometry),
        })

    # Municipal outline for Exhibit 3.2, so a reader can place a road in the town
    # rather than in an unlabelled tangle of lines. REFERENCE ONLY -- it orients
    # the eye and establishes no standard, no jurisdiction and no boundary
    # determination. Dissolved from the state town-boundary layer, reprojected to
    # the working CRS and simplified to 15 m (sub-pixel at page scale).
    boundary_rings = []
    bpath = lib.RAW / "town_boundary.geojson"
    if bpath.exists():
        try:
            from shapely.ops import unary_union
            bnd = gpd.read_file(bpath)
            if "TOWN" in bnd.columns:
                bnd = bnd[bnd["TOWN"].str.strip().str.lower() == cfg["town"].strip().lower()]
            if len(bnd):
                merged = gpd.GeoSeries([unary_union(bnd.geometry.values)],
                                       crs=bnd.crs).to_crs(cfg["working_crs"]).iloc[0]
                simp = merged.simplify(15)
                polys = list(simp.geoms) if simp.geom_type == "MultiPolygon" else [simp]
                boundary_rings = [[[round(x, 2), round(y, 2)] for x, y in pl.exterior.coords]
                                  for pl in polys]
        except Exception as exc:  # noqa: BLE001
            # A missing or unreadable outline is cosmetic: the map still renders
            # every segment. Say so rather than failing the whole export.
            print(f"[export] town boundary skipped: {exc}")

    inv = {
        "_meta": {
            "note": ("Generated by build/street-types (05_export.py). WORKING/DRAFT "
                     "classification — promote to source/exhibits/street-types/inventory.json "
                     "only after Planning-Board review + adoption."),
            "banner": "DRAFT — Types auto-derived from an approximate trace of the District Map; not yet reviewed or adopted.",
            "crs": cfg["working_crs"],
            "town": cfg["town"],
            "town_boundary_note": ("Municipal outline, reference only: it orients the reader and "
                                   "establishes no standard or jurisdiction."),
            "town_boundary": boundary_rings,
            "addresses_note": ("Per-segment E-911 address-point counts, nearest segment within "
                               "60 m. REVIEW AID ONLY -- decision support for the §5.C.3.g "
                               "present-use review, never a determination. A low 'residential' "
                               "beside a nonzero 'unknown_type' means NOT REVIEWED, not NOT "
                               "PRESENT."),
        },
        "segments": out_segments,
    }
    invf = lib.WORK / "inventory.json"
    invf.write_text(json.dumps(inv, indent=1))

    cols = ["id", "name", "from_terminus", "to_terminus", "public", "ownership",
            "fedfunccls", "districts", "provisional_type", "type", "type_source",
            "nonconformity", "length_ft"]
    with open(lib.WORK / "review.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for _, r in segs.iterrows():
            w.writerow([r.get(c, "") for c in cols])

    segs.to_file(lib.WORK / "review.gpkg", driver="GPKG")
    print(f"[export] {len(out_segments)} segments  ->  {invf.relative_to(lib.REPO)}")
    if excluded:
        print(f"         excluded {len(excluded)} non-thoroughfare record(s): {', '.join(excluded)}")
    print(f"         + work/review.csv + work/review.gpkg")


if __name__ == "__main__":
    main()
