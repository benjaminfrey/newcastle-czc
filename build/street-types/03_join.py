#!/usr/bin/env python3
"""Stage 03 — join attributes onto each segment.

For every segment (from 02_prepare) this derives:
  - MaineDOT functional class + state-aid (matched from the MaineDOT Public Roads
    layer by best geometric overlap; private ways simply don't match),
  - Ownership Category (from MaineDOT jurisdiction where matched, else from the
    E911 jurisdiction carried on the segment; Public Easement is never auto-set),
  - adjacent District(s) (overlay with the digitized districts layer IF present;
    otherwise left null and filled once Phase 0 lands).

Output: data/street-types/work/joined.gpkg

Run:  cd build/street-types && .venv/bin/python 03_join.py
"""
import geopandas as gpd

import lib

BUF = 8.0  # metres: matching tolerance segment <-> MaineDOT centerline


def ownership_from(juris: str) -> str:
    """Map a jurisdiction string (MaineDOT or E911 vocab) to a CZC Ownership
    Category. Public Easement is never auto-assigned (no source signal)."""
    j = (juris or "").strip().lower()
    if "state hwy" in j or "state highway" in j:
        return "State Highway"
    if "private" in j:
        return "Private Road"
    if "town" in j or "state aid" in j:   # townway / tnwy summer / state aid
        return "Town Way"
    return ""                              # unknown -> flag in review


def main() -> None:
    cfg = lib.load_config()
    crs = cfg["working_crs"]
    segs = gpd.read_file(lib.WORK / "segments.gpkg").to_crs(crs)
    dot = gpd.read_file(lib.RAW / "maindot_roads.geojson").to_crs(crs)
    dsx = dot.sindex

    fedfunccls, jurisdictn, state_aid, surfc, lanes, speed = [], [], [], [], [], []
    for seg in segs.geometry:
        buf = seg.buffer(BUF)
        best, best_ov = None, 0.0
        for j in dsx.query(buf, predicate="intersects"):
            m = dot.iloc[j]
            ov = m.geometry.intersection(buf).length
            if ov > best_ov:
                best, best_ov = m, ov
        # require a real overlap (>=40% of the segment) to accept a MaineDOT match
        if best is not None and best_ov >= 0.40 * seg.length:
            fedfunccls.append(best.get("fedfunccls") or "")
            jurisdictn.append(best.get("jurisdictn") or "")
            sa = str(best.get("sh_sa_ir") or "")
            state_aid.append(bool(sa) and not sa.startswith("IR"))
            surfc.append(best.get("surfc_type") or "")
            lanes.append(best.get("num_lanes"))
            speed.append(best.get("speed_lim"))
        else:
            fedfunccls.append(""); jurisdictn.append(""); state_aid.append(False)
            surfc.append(""); lanes.append(None); speed.append(None)

    segs["fedfunccls"] = fedfunccls
    segs["maindot_juris"] = jurisdictn
    segs["state_aid"] = state_aid
    segs["surface"] = surfc
    segs["lanes"] = lanes
    segs["speed_lim"] = speed
    # Ownership: prefer MaineDOT jurisdiction, else the E911 jurisdiction.
    segs["ownership"] = [
        ownership_from(mj) or ownership_from(ej)
        for mj, ej in zip(segs["maindot_juris"], segs["e911_juris"])
    ]

    # Adjacent district(s): overlay with the digitized layer if it exists.
    dist_path = lib.WORK / "districts.gpkg"
    if dist_path.exists():
        dgdf = gpd.read_file(dist_path).to_crs(crs)
        code_field = "district" if "district" in dgdf.columns else dgdf.columns[0]
        adj = []
        disx = dgdf.sindex
        for seg in segs.geometry:
            hits = {}
            for j in disx.query(seg, predicate="intersects"):
                d = dgdf.iloc[j]
                hits[d[code_field]] = hits.get(d[code_field], 0.0) + seg.intersection(d.geometry).length
            adj.append("; ".join(sorted(hits, key=hits.get, reverse=True)) if hits else "")
        segs["districts"] = adj
        print(f"[join] district overlay applied from {dist_path.name}")
    else:
        segs["districts"] = ""
        print("[join] no districts.gpkg yet — 'districts' left blank (Phase 0 pending)")

    out = lib.WORK / "joined.gpkg"
    segs.to_file(out, driver="GPKG")
    matched = int((segs["fedfunccls"] != "").sum())
    print(f"[join] {len(segs)} segments  ·  {matched} matched to MaineDOT  ->  {out.relative_to(lib.REPO)}")
    print("  ownership:", segs["ownership"].value_counts().to_dict())
    print("  func class:", {k: v for k, v in segs["fedfunccls"].value_counts().to_dict().items() if k})


if __name__ == "__main__":
    main()
