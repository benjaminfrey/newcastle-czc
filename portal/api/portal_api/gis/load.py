"""Load a GIS layer into PostGIS: any OGR-readable file in, EPSG:26919 out.

Each load is one gis_import row. It becomes the active import for its layer only
when every feature has been inserted, inside the caller's transaction, so a
failed load leaves the previous import active.
"""

import re
from dataclasses import dataclass
from datetime import date

import pyogrio
import shapely
from sqlalchemy import Connection, text

from portal_api.events import append_event

WORKING_SRID = 26919  # NAD83 / UTM 19N, metres — the CZC GIS pipeline's CRS


@dataclass(frozen=True)
class Feature:
    attrs: dict
    geom: shapely.Geometry
    srid: int


def _srid(crs: str | None) -> int:
    m = re.search(r"EPSG:+(\d+)", crs or "")
    if not m:
        raise ValueError(f"cannot tell the coordinate system of this file ({crs!r})")
    return int(m.group(1))


def read_features(path: str) -> list[Feature]:
    meta, _fids, geometry, field_data = pyogrio.raw.read(path)
    srid = _srid(meta["crs"])
    names = list(meta["fields"])
    out = []
    for i, wkb in enumerate(geometry):
        if wkb is None:
            continue
        attrs = {name: field_data[j][i] for j, name in enumerate(names)}
        out.append(Feature(attrs=attrs, geom=shapely.from_wkb(wkb), srid=srid))
    return out


def _geom_sql(multi: bool) -> str:
    g = f"ST_Transform(ST_SetSRID(ST_GeomFromWKB(:wkb), :srid), {WORKING_SRID})"
    return f"ST_Multi({g})" if multi else g


_INSERT = {
    "parcels": ("INSERT INTO parcel (import_id, map_lot, location, geom) "
                f"VALUES (:imp, :map_lot, :location, {_geom_sql(True)})"),
    "addresses": ("INSERT INTO address_point (import_id, label, geom) "
                  f"VALUES (:imp, :label, {_geom_sql(False)})"),
    "districts": ("INSERT INTO district_area (import_id, code, name, in_ruleset, geom) "
                  f"VALUES (:imp, :code, :name, :in_ruleset, {_geom_sql(True)})"),
    "streets": ("INSERT INTO street_segment (import_id, segment_id, name, type, type_name, ownership, geom) "
                f"VALUES (:imp, :segment_id, :name, :type, :type_name, :ownership, {_geom_sql(True)})"),
}


def load_layer(conn: Connection, *, layer: str, source: str, source_date: date, rows: list[dict]) -> int:
    import_id = conn.execute(text(
        "INSERT INTO gis_import (layer, source, source_date) VALUES (:l, :s, :d) RETURNING id"
    ), {"l": layer, "s": source, "d": source_date}).scalar()
    sql = text(_INSERT[layer])
    for row in rows:
        params = {k: v for k, v in row.items() if k not in ("geom", "srid")}
        conn.execute(sql, {**params, "imp": import_id, "wkb": shapely.to_wkb(row["geom"]), "srid": row["srid"]})
    conn.execute(text("UPDATE gis_import SET active = false WHERE layer = :l AND active"), {"l": layer})
    conn.execute(text("UPDATE gis_import SET active = true, feature_count = :n WHERE id = :i"),
                 {"n": len(rows), "i": import_id})
    append_event(conn, actor="system", kind="gis.imported", payload={
        "layer": layer, "import_id": import_id, "source": source,
        "source_date": source_date.isoformat(), "features": len(rows),
    })
    return int(import_id)
