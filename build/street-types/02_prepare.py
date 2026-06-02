#!/usr/bin/env python3
"""Stage 02 — prepare segments.

Reads the raw E911 roads (primary spine), reprojects to the working CRS, dissolves
to one geometry per named road, then splits each named road at its PRINCIPAL
intersections — the points where it meets another named road (and, when a district
layer is present, at district boundaries). Each resulting piece is an ordinance
"segment between two principal intersections" (§5.B.2), tagged with a stable id,
name, and termini (the cross-road names at each end).

Output: data/street-types/work/segments.gpkg

Run:  cd build/street-types && .venv/bin/python 02_prepare.py
"""
import re
import unicodedata

import geopandas as gpd
import shapely
from shapely.geometry import MultiPoint, Point
from shapely.ops import split, unary_union

import lib

SNAP = 1.0   # metres: endpoint/terminus matching tolerance


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "unnamed"


def points_of(geom):
    """Pull Point geometries out of an intersection result."""
    if geom.is_empty:
        return []
    t = geom.geom_type
    if t == "Point":
        return [geom]
    if t == "MultiPoint":
        return list(geom.geoms)
    if t == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out += points_of(g)
        return out
    return []   # ignore line overlaps


def main() -> None:
    cfg = lib.load_config()
    crs = cfg["working_crs"]
    lib.WORK.mkdir(parents=True, exist_ok=True)

    roads = gpd.read_file(lib.RAW / "e911_roads.geojson").to_crs(crs)
    name_field = cfg["sources"]["e911_roads"]["name_field"]
    roads["name"] = roads[name_field].fillna("").str.strip().replace("", "(unnamed)")

    # Per-name dominant E911 jurisdiction + road class — carried onto segments and
    # used to decide public vs private, which sets where we split.
    def mode_of(s):
        m = s.fillna("").mode()
        return m.iloc[0] if len(m) else ""
    agg = roads.groupby("name").agg(e911_juris=("MDOTJURIS", mode_of),
                                    e911_rdclass=("RDCLASS", mode_of)).reset_index()

    # Dissolve to one geometry per named road; merge multipart where contiguous.
    by_name = roads.dissolve(by="name", as_index=False)[["name", "geometry"]]
    by_name["geometry"] = by_name.geometry.apply(shapely.line_merge)
    by_name = by_name.merge(agg, on="name", how="left")
    # Public = anything MaineDOT tracks as a jurisdiction other than Private.
    by_name["public"] = by_name["e911_juris"].fillna("") != "Private"
    print(f"[prepare] {int(by_name['public'].sum())} public / "
          f"{int((~by_name['public']).sum())} private named roads")

    # Optional: split at district boundaries too, when the digitized layer exists.
    dist_path = lib.WORK / "districts.gpkg"
    dist_lines = None
    if dist_path.exists():
        dgdf = gpd.read_file(dist_path).to_crs(crs)
        dist_lines = unary_union(dgdf.geometry.boundary.values)
        print(f"[prepare] district boundaries present — splitting at them too")

    sindex = by_name.sindex
    seg_rows = []
    counters: dict[str, int] = {}
    for i, row in by_name.iterrows():
        g = row.geometry
        if g is None or g.is_empty:
            continue
        rname = row["name"]                          # NB: row.name is the index, not the column
        # Principal intersections = crossings with PUBLIC roads only. Split this
        # road only where it meets another public road (not at private junctions).
        cand = list(sindex.query(g, predicate="intersects"))
        others = [by_name.geometry.iloc[j] for j in cand
                  if by_name["name"].iloc[j] != rname and bool(by_name["public"].iloc[j])]
        splitter_geoms = list(others)
        if dist_lines is not None:
            splitter_geoms.append(dist_lines)
        cut_pts = []
        for s in splitter_geoms:
            cut_pts += points_of(g.intersection(s))
        if cut_pts:
            mp = MultiPoint(cut_pts)
            try:
                pieces = list(split(shapely.snap(g, mp, SNAP), mp).geoms)
            except Exception:
                pieces = [g]
        else:
            pieces = [g] if g.geom_type == "LineString" else list(g.geoms)
        for piece in pieces:
            if piece.is_empty or piece.length < 1.0:
                continue
            counters[rname] = counters.get(rname, 0) + 1
            seg_rows.append({
                "name": rname, "n": counters[rname],
                "e911_juris": row.get("e911_juris", ""),
                "e911_rdclass": row.get("e911_rdclass", ""),
                "public": bool(row["public"]),
                "geometry": piece,
            })

    segs = gpd.GeoDataFrame(seg_rows, crs=crs)
    segs["id"] = [f"{slugify(n)}-{k}" for n, k in zip(segs["name"], segs["n"])]

    # Termini are the PUBLIC roads a segment meets (the principal intersections);
    # a free end (dead-end / town line / private-only junction) is labelled "end".
    name_geoms = [(nm, gg) for nm, gg, pub in
                  zip(by_name["name"], by_name.geometry, by_name["public"]) if pub]

    def cross_names(pt: Point, self_name: str):
        hits = []
        for nm, gg in name_geoms:
            if nm == self_name:
                continue
            if gg.distance(pt) <= SNAP:
                hits.append(nm)
        return sorted(set(hits))

    termini = []
    for _, r in segs.iterrows():
        g = r.geometry
        ends = [Point(g.coords[0]), Point(g.coords[-1])]
        labels = []
        for p in ends:
            cn = cross_names(p, r["name"])
            labels.append(" / ".join(cn) if cn else "end")
        termini.append(labels)
    segs["from_terminus"] = [t[0] for t in termini]
    segs["to_terminus"] = [t[1] for t in termini]
    segs["length_ft"] = (segs.length * 3.28084).round(0).astype(int)

    out = lib.WORK / "segments.gpkg"
    cols = ["id", "name", "public", "e911_juris", "e911_rdclass",
            "from_terminus", "to_terminus", "length_ft", "geometry"]
    segs[cols].to_file(out, driver="GPKG")
    print(f"[prepare] {len(by_name)} named roads -> {len(segs)} segments  ->  {out.relative_to(lib.REPO)}")
    print("  sample:")
    for _, r in segs.head(8).iterrows():
        print(f"    {r['id']:28} {r['name']:22} [{r['from_terminus']} -> {r['to_terminus']}]  {r['length_ft']} ft")


if __name__ == "__main__":
    main()
