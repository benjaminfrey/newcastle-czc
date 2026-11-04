import json
import math

from sqlalchemy import text

from portal_api.lot_outline import outline
from portal_api.property import active_import
from tests.test_projects import alice, app, create, get, lookup_property  # noqa: F401  (fixtures)
from tests.test_property import layers  # noqa: F401  (fixture)

FT = 3.28084


def _imports(conn):
    return active_import(conn, "parcels").id, active_import(conn, "streets").id


def _parcel(conn, map_lot):
    pi, _ = _imports(conn)
    return conn.execute(text("SELECT id FROM parcel WHERE import_id = :pi AND map_lot = :m"),
                        {"pi": pi, "m": map_lot}).scalar()


def _insert(conn, wkt, map_lot):
    """A lot from WKT in EPSG:26919, placed 2 km from the test lots."""
    pi, _ = _imports(conn)
    return conn.execute(text(
        "INSERT INTO parcel (import_id, map_lot, geom) VALUES (:pi, :m, ST_Multi(ST_GeomFromText(:w, 26919)))"
        " RETURNING id"), {"pi": pi, "m": map_lot, "w": wkt}).scalar()


def _of(engine, map_lot=None, wkt=None):
    with engine.begin() as conn:
        pid = _parcel(conn, map_lot) if map_lot else _insert(conn, wkt, "test-lot")
        return outline(conn, pid, *_imports(conn))


def test_outline_is_in_feet_about_the_centroid(engine, layers):  # noqa: F811
    o = _of(engine, "004-036")
    xs = [p[0] for p in o["parts"][0]]
    ys = [p[1] for p in o["parts"][0]]
    with engine.begin() as conn:
        width = conn.execute(text("SELECT ST_XMax(geom) - ST_XMin(geom) FROM parcel WHERE id = :id"),
                             {"id": _parcel(conn, "004-036")}).scalar()
    assert o["units"] == "ft" and o["approximate"] is True
    assert abs((max(xs) + min(xs)) / 2) < 1 and abs((max(ys) + min(ys)) / 2) < 1
    assert abs((max(xs) - min(xs)) - width * FT) < 1


def test_a_rectangular_lot_has_four_lines(engine, layers):  # noqa: F811
    o = _of(engine, "004-036")
    with engine.begin() as conn:
        perim = conn.execute(text("SELECT ST_Perimeter(geom) FROM parcel WHERE id = :id"),
                             {"id": _parcel(conn, "004-036")}).scalar()
    assert len(o["lines"]) == 4
    assert abs(sum(L["length_ft"] for L in o["lines"]) - perim * FT) <= 2


def test_the_line_along_the_road_names_it(engine, layers):  # noqa: F811
    o = _of(engine, "004-036")
    along = [L for L in o["lines"] if L["street"]]
    assert [L["street"] for L in along] == [{"name": "Sheepscot Road", "type": "R2"}]
    mean_y = {L["id"]: sum(p[1] for p in L["points"]) / len(L["points"]) for L in o["lines"]}
    assert min(mean_y, key=mean_y.get) == along[0]["id"]
    assert o["streets"] and o["streets"][0]["name"] == "Sheepscot Road"


def _noisy_square(x0, y0, side, extra=10):
    """A square with `extra` jittered vertices along each edge (each ≤ 0.3 m off the edge)."""
    corners = [(x0, y0), (x0, y0 + side), (x0 + side, y0 + side), (x0 + side, y0)]
    pts = []
    for i, (ax, ay) in enumerate(corners):
        bx, by = corners[(i + 1) % 4]
        pts.append((ax, ay))
        for k in range(1, extra + 1):
            t = k / (extra + 1)
            jitter = 0.3 * math.sin(k * 1.7)
            nx, ny = (by - ay) / side, -(bx - ax) / side
            pts.append((ax + t * (bx - ax) + jitter * nx, ay + t * (by - ay) + jitter * ny))
    pts.append(pts[0])
    return "POLYGON((" + ",".join(f"{x} {y}" for x, y in pts) + "))"


def test_noisy_boundary_merges_into_few_lines(engine, layers):  # noqa: F811
    o = _of(engine, wkt=_noisy_square(450000, 4880000, 60))
    assert len(o["lines"]) == 4
    assert all(L["street"] is None for L in o["lines"])


def test_outline_of_a_multipart_lot_uses_its_largest_part(engine, layers):  # noqa: F811
    wkt = ("MULTIPOLYGON(((450100 4880000,450105 4880000,450105 4880005,450100 4880005,450100 4880000)),"
           "((450000 4880000,450000 4880050,450050 4880050,450050 4880000,450000 4880000)))")
    o = _of(engine, wkt=wkt)
    assert len(o["parts"]) == 2
    big = max(abs(p[0]) for p in o["parts"][0])
    assert abs(big - 25 * FT) < 1   # the 50 m square, centred
    assert len(o["lines"]) == 4
    assert all(abs(L["length_ft"] - 50 * FT) <= 1 for L in o["lines"])


def test_snapshot_keeps_the_outline_and_drops_geometry(alice, engine):  # noqa: F811
    pid = create(alice, ("building",))
    with engine.begin() as conn:
        facts = conn.execute(text("SELECT facts FROM property_snapshot WHERE project_id = :p"), {"p": pid}).scalar()
    facts = facts if isinstance(facts, dict) else json.loads(facts)
    assert "geometry" not in facts and len(facts["outline"]["lines"]) == 4


def test_a_manual_lot_has_no_outline(alice, engine):  # noqa: F811
    pid = create(alice, ("driveway",), prop={"source": "manual", "map_lot": "4-36", "district_code": None})
    with engine.begin() as conn:
        facts = conn.execute(text("SELECT facts FROM property_snapshot WHERE project_id = :p"), {"p": pid}).scalar()
    facts = facts if isinstance(facts, dict) else json.loads(facts)
    assert "outline" not in facts
