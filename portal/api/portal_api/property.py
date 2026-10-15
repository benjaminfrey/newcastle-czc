"""Property facts from the active GIS imports. Read-only; nothing is logged."""

import json
import re
from datetime import date, timedelta

from sqlalchemy import Connection, text

_FT_PER_M = 3.28084
_SQ_M_PER_ACRE = 4046.8564224


class ParcelsUnavailable(Exception):
    """No usable parcel import: none loaded, or too old for applicants."""


def active_import(conn: Connection, layer: str):
    return conn.execute(text(
        "SELECT id, source, source_date FROM gis_import WHERE layer = :l AND active"
    ), {"l": layer}).one_or_none()


def parcels_import(conn: Connection, settings):
    imp = active_import(conn, "parcels")
    if imp is None:
        raise ParcelsUnavailable("none loaded")
    too_old = date.today() - imp.source_date > timedelta(days=settings.parcel_max_age_days)
    if too_old and not settings.allow_stale_parcels:
        raise ParcelsUnavailable("out of date")
    return imp


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_MAP_LOT = re.compile(r"^\s*(\d{1,3})\D+(\d{1,3})\s*$")


def search(conn: Connection, q: str, parcels_import_id: int) -> list[dict]:
    hits: list[dict] = []
    m = _MAP_LOT.match(q)
    if m:
        prefix = f"{int(m.group(1)):03d}-{int(m.group(2)):03d}"
        for r in conn.execute(text(
            "SELECT id, map_lot, ST_X(c) AS lon, ST_Y(c) AS lat FROM ("
            " SELECT id, map_lot, ST_Transform(ST_PointOnSurface(geom), 4326) AS c FROM parcel"
            " WHERE import_id = :pi AND map_lot LIKE :p ESCAPE '\\') s ORDER BY map_lot LIMIT 8"
        ), {"pi": parcels_import_id, "p": _like_escape(prefix) + "%"}):
            parts = r.map_lot.split("-")
            lot = "-".join(p.lstrip("0") or "0" for p in parts[1:])
            hits.append({"label": f"Map {int(parts[0])}, Lot {lot}", "lon": r.lon, "lat": r.lat, "parcel_id": r.id})
    addr = active_import(conn, "addresses")
    if addr is not None:
        for r in conn.execute(text(
            "SELECT a.label, ST_X(ST_Transform(a.geom, 4326)) AS lon, ST_Y(ST_Transform(a.geom, 4326)) AS lat,"
            " (SELECT p.id FROM parcel p WHERE p.import_id = :pi AND ST_Contains(p.geom, a.geom) LIMIT 1) AS parcel_id"
            " FROM address_point a WHERE a.import_id = :ai"
            " AND (lower(a.label) LIKE '%' || lower(:q) || '%' ESCAPE '\\' OR similarity(lower(a.label), lower(:raw)) > 0.3)"
            " ORDER BY (lower(a.label) LIKE lower(:q) || '%' ESCAPE '\\') DESC,"
            " similarity(lower(a.label), lower(:raw)) DESC, a.label LIMIT 8"
        ), {"pi": parcels_import_id, "ai": addr.id, "q": _like_escape(q.strip()), "raw": q.strip()}):
            hits.append({"label": r.label, "lon": r.lon, "lat": r.lat, "parcel_id": r.parcel_id})
    return hits[:8]


def parcel_at(conn: Connection, lon: float, lat: float, parcels_import_id: int) -> int | None:
    return conn.execute(text(
        "SELECT id FROM parcel WHERE import_id = :pi AND ST_Contains(geom,"
        " ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 26919)) LIMIT 1"
    ), {"pi": parcels_import_id, "lon": lon, "lat": lat}).scalar()


def facts(conn: Connection, parcel_id: int, parcels_imp) -> dict | None:
    p = conn.execute(text(
        "SELECT id, map_lot, location, ST_Area(geom) AS area, ST_AsGeoJSON(ST_Transform(geom, 4326), 6) AS gj"
        " FROM parcel WHERE id = :id AND import_id = :pi"
    ), {"id": parcel_id, "pi": parcels_imp.id}).one_or_none()
    if p is None:
        return None
    dist_imp = active_import(conn, "districts")
    districts = [] if dist_imp is None else [dict(r._mapping) for r in conn.execute(text(
        "SELECT d.code, d.name, d.in_ruleset,"
        " round((ST_Area(ST_Intersection(d.geom, p.geom)) / ST_Area(p.geom))::numeric, 3)::float AS share"
        " FROM district_area d, parcel p WHERE p.id = :id AND d.import_id = :di AND ST_Intersects(d.geom, p.geom)"
        " AND ST_Area(ST_Intersection(d.geom, p.geom)) / ST_Area(p.geom) >= 0.01 ORDER BY share DESC"
    ), {"id": parcel_id, "di": dist_imp.id})]
    st_imp = active_import(conn, "streets")
    streets = [] if st_imp is None else [{
        "name": r.name, "type": r.type, "type_name": r.type_name, "ownership": r.ownership,
        "frontage_ft": int(5 * round(r.metres * _FT_PER_M / 5)),
    } for r in conn.execute(text(
        # Per segment: the stretch of street alongside the lot = the span, along the street,
        # of the lot-boundary vertices within 20 m of it.
        "WITH seg AS ("
        " SELECT s.name, s.type, s.type_name, s.ownership,"
        "  (max(ST_LineLocatePoint(l.line, d.geom)) - min(ST_LineLocatePoint(l.line, d.geom))) * ST_Length(l.line) AS metres"
        " FROM street_segment s"
        " JOIN parcel p ON p.id = :id"
        " CROSS JOIN LATERAL (SELECT ST_GeometryN(s.geom, 1) AS line) l"
        " CROSS JOIN LATERAL ST_DumpPoints(ST_Intersection(ST_Boundary(p.geom), ST_Buffer(s.geom, 20))) d"
        " WHERE s.import_id = :si AND ST_DWithin(s.geom, p.geom, 20)"
        " GROUP BY s.id, s.name, s.type, s.type_name, s.ownership, l.line)"
        " SELECT name, type, max(type_name) AS type_name, max(ownership) AS ownership, sum(metres) AS metres"
        " FROM seg GROUP BY name, type HAVING sum(metres) >= 3 ORDER BY metres DESC"
    ), {"id": parcel_id, "si": st_imp.id})]
    return {
        "parcel_id": p.id, "map_lot": p.map_lot, "location": p.location,
        "acres": round(p.area / _SQ_M_PER_ACRE, 2),
        "districts": districts, "streets": streets,
        "on_state_highway": any(s["ownership"] == "State Highway" for s in streets),
        "as_of": {"parcels": parcels_imp.source_date.isoformat(), "parcels_source": parcels_imp.source,
                  "districts_source": dist_imp.source if dist_imp else None},
        "geometry": json.loads(p.gj),
    }


def adopted_districts(conn: Connection) -> list[dict]:
    imp = active_import(conn, "districts")
    if imp is None:
        return []
    return [dict(r._mapping) for r in conn.execute(text(
        "SELECT DISTINCT code, name FROM district_area WHERE import_id = :i AND in_ruleset ORDER BY code"
    ), {"i": imp.id})]
