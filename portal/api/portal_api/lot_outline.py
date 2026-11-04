"""A lot's outline for the guide's drawing (guided plan 4): the tax-map boundary in feet about
the lot's centre, split into lot lines (runs of nearly straight boundary), each with the road
alongside it, if any. Approximate: the tax maps are not a survey (decision 12).

Only the largest part's outer ring is split into lines; other parts are drawn, holes are not.
"""

import json
import math

from sqlalchemy import Connection, text

from portal_api.property import REACH_DEFAULT_M, REACH_M

FT_PER_M = 3.28084
LINE_BEND_DEG = 25      # a turn sharper than this starts a new lot line
MIN_EDGE_FT = 3         # shorter edges are tax-map noise and fold into their neighbours
MAX_LINES = 12
SAMPLE_FT = 5           # how finely a line is tested against the roads
CLIP_M = 40             # roads drawn this far round the lot (more than the widest reach)

Pt = tuple[float, float]


def _rings(conn: Connection, parcel_id: int, parcels_import_id: int):
    rows = conn.execute(text(
        "WITH p AS (SELECT geom FROM parcel WHERE id = :id AND import_id = :pi),"
        " parts AS (SELECT (ST_Dump(geom)).geom AS g FROM p)"
        " SELECT ST_AsGeoJSON(ST_ExteriorRing(g)) AS ring, ST_Area(g) AS area,"
        "  ST_X(ST_Centroid(g)) AS cx, ST_Y(ST_Centroid(g)) AS cy FROM parts ORDER BY ST_Area(g) DESC"
    ), {"id": parcel_id, "pi": parcels_import_id}).all()
    return rows


def _streets(conn: Connection, parcel_id: int, streets_import_id: int):
    return conn.execute(text(
        "SELECT s.name, s.type, s.ownership,"
        f" ST_AsGeoJSON(ST_Intersection(s.geom, ST_Expand(ST_Envelope(p.geom), {CLIP_M}))) AS gj"
        " FROM street_segment s JOIN parcel p ON p.id = :id"
        " WHERE s.import_id = :si AND ST_DWithin(s.geom, p.geom, CASE WHEN s.ownership = 'State Highway'"
        f" THEN {REACH_M['State Highway']} ELSE {REACH_DEFAULT_M} END)"
    ), {"id": parcel_id, "si": streets_import_id}).all()


def _local(xy, cx: float, cy: float) -> Pt:
    return ((xy[0] - cx) * FT_PER_M, (xy[1] - cy) * FT_PER_M)


def _r(p: Pt) -> list[float]:
    return [round(p[0], 1), round(p[1], 1)]


def _clockwise(ring: list[Pt]) -> list[Pt]:
    """Open ring (no repeated last point), clockwise with y north."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))
    return ring[::-1] if area > 0 else ring


def _dist(a: Pt, b: Pt) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _turn(a: Pt, b: Pt, c: Pt) -> float:
    """Degrees the boundary turns at b, going a → b → c."""
    h1 = math.atan2(b[1] - a[1], b[0] - a[0])
    h2 = math.atan2(c[1] - b[1], c[0] - b[0])
    return abs(math.degrees((h2 - h1 + math.pi) % (2 * math.pi) - math.pi))


def _thin(ring: list[Pt]) -> list[Pt]:
    out: list[Pt] = []
    for p in ring:
        if not out or _dist(out[-1], p) >= MIN_EDGE_FT:
            out.append(p)
    while len(out) > 3 and _dist(out[-1], out[0]) < MIN_EDGE_FT:
        out.pop()
    return out


def _split(ring: list[Pt]) -> list[list[Pt]]:
    """Runs of the ring between corners, each as its points (corner to corner)."""
    n = len(ring)
    corners = [i for i in range(n) if _turn(ring[i - 1], ring[i], ring[(i + 1) % n]) > LINE_BEND_DEG]
    if not corners:
        return [ring + ring[:1]]
    lines = []
    for k, i in enumerate(corners):
        j = corners[(k + 1) % len(corners)]
        idx = list(range(i, j + 1)) if j > i else list(range(i, n)) + list(range(0, j + 1))
        lines.append([ring[m] for m in idx])
    while len(lines) > MAX_LINES:
        turns = [_turn(lines[k][0], lines[k][-1], lines[(k + 1) % len(lines)][-1]) for k in range(len(lines))]
        k = turns.index(min(turns))
        nxt = (k + 1) % len(lines)
        lines[k] = lines[k] + lines[nxt][1:]
        del lines[nxt]   # lines stay in ring order; _south_first picks the start afterwards
    return lines


def _south_first(lines: list[list[Pt]]) -> list[list[Pt]]:
    def off_south(p: Pt) -> float:
        return abs((math.atan2(p[1], p[0]) + math.pi / 2 + math.pi) % (2 * math.pi) - math.pi)
    k = min(range(len(lines)), key=lambda i: off_south(lines[i][0]))
    return lines[k:] + lines[:k]


def _length(pts: list[Pt]) -> float:
    return sum(_dist(a, b) for a, b in zip(pts, pts[1:]))


def _samples(pts: list[Pt]):
    for a, b in zip(pts, pts[1:]):
        d = _dist(a, b)
        steps = max(1, int(d // SAMPLE_FT))
        for s in range(steps):
            t = (s + 0.5) / steps
            yield (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), d / steps


def _to_segment(p: Pt, a: Pt, b: Pt) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return _dist(p, (a[0] + t * dx, a[1] + t * dy))


def _street_of(pts: list[Pt], streets: list[dict]) -> dict | None:
    """The road alongside at least half the line's length, if any."""
    total = _length(pts)
    near: dict[tuple, float] = {}
    for p, w in _samples(pts):
        for s in streets:
            reach = s["reach_ft"]
            if any(_to_segment(p, a, b) <= reach for piece in s["pieces"] for a, b in zip(piece, piece[1:])):
                key = (s["name"], s["type"])
                near[key] = near.get(key, 0) + w
    if not near:
        return None
    (name, type_), got = max(near.items(), key=lambda kv: kv[1])
    return {"name": name, "type": type_} if total and got >= total / 2 else None


def _pieces(gj: str | None) -> list[list]:
    if not gj:
        return []
    g = json.loads(gj)
    if g["type"] == "LineString":
        return [g["coordinates"]]
    if g["type"] == "MultiLineString":
        return g["coordinates"]
    if g["type"] == "GeometryCollection":
        return [c for sub in g["geometries"] for c in _pieces(json.dumps(sub))]
    return []


def outline(conn: Connection, parcel_id: int, parcels_import_id: int, streets_import_id: int | None) -> dict | None:
    rows = _rings(conn, parcel_id, parcels_import_id)
    if not rows:
        return None
    cx, cy = rows[0].cx, rows[0].cy
    parts = [_clockwise([_local(xy, cx, cy) for xy in json.loads(r.ring)["coordinates"][:-1]]) for r in rows]
    streets = []
    if streets_import_id is not None:
        for s in _streets(conn, parcel_id, streets_import_id):
            pieces = [[_local(xy, cx, cy) for xy in piece] for piece in _pieces(s.gj)]
            pieces = [p for p in pieces if len(p) >= 2]
            if pieces:
                reach_m = REACH_M.get(s.ownership, REACH_DEFAULT_M)
                streets.append({"name": s.name, "type": s.type, "reach_ft": reach_m * FT_PER_M, "pieces": pieces})
    ring = _thin(parts[0])
    lines = _south_first(_split(ring)) if len(ring) >= 3 else []
    return {
        "units": "ft", "approximate": True,
        "parts": [[_r(p) for p in part] for part in parts],
        "lines": [{"id": f"L{i + 1}", "points": [_r(p) for p in pts], "length_ft": round(_length(pts)),
                   "street": _street_of(pts, streets)} for i, pts in enumerate(lines)],
        "streets": [{"name": s["name"], "points": [_r(p) for p in piece]} for s in streets for piece in s["pieces"]],
    }
