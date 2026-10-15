from fastapi import APIRouter, Depends, Path, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import Connection, text

from portal_api import property as prop
from portal_api.db import transaction
from portal_api.ratelimit import lookup_limit, tile_limit

router = APIRouter()


def _unavailable() -> JSONResponse:
    return JSONResponse({"detail": "parcel_data_unavailable"}, status_code=503)


def _parcels(conn, request):
    try:
        return prop.parcels_import(conn, request.app.state.settings)
    except prop.ParcelsUnavailable:
        return None


@router.get("/api/property/search", dependencies=[Depends(lookup_limit)])
def search(request: Request, q: str = Query(min_length=2, max_length=100), conn: Connection = transaction):
    imp = _parcels(conn, request)
    return _unavailable() if imp is None else prop.search(conn, q, imp.id)


@router.get("/api/property/at", dependencies=[Depends(lookup_limit)])
def at(request: Request, lon: float = Query(ge=-180, le=180), lat: float = Query(ge=-90, le=90),
       conn: Connection = transaction):
    imp = _parcels(conn, request)
    if imp is None:
        return _unavailable()
    pid = prop.parcel_at(conn, lon, lat, imp.id)
    return {"parcel_id": pid} if pid else JSONResponse({"detail": "no_parcel_here"}, status_code=404)


@router.get("/api/property/districts")
def districts(conn: Connection = transaction):
    return prop.adopted_districts(conn)


@router.get("/api/property/{parcel_id}", dependencies=[Depends(lookup_limit)])
def facts(parcel_id: int, request: Request, conn: Connection = transaction):
    imp = _parcels(conn, request)
    if imp is None:
        return _unavailable()
    f = prop.facts(conn, parcel_id, imp)
    return f if f else JSONResponse({"detail": "no_such_parcel"}, status_code=404)


@router.get("/api/tiles/parcels/{z}/{x}/{y}.pbf", dependencies=[Depends(tile_limit)])
def parcel_tile(request: Request, z: int = Path(ge=0, le=22), x: int = Path(ge=0), y: int = Path(ge=0),
                conn: Connection = transaction):
    imp = _parcels(conn, request)
    if imp is None:
        return _unavailable()
    if z < 12 or x >= 2 ** z or y >= 2 ** z:
        return Response(status_code=204)
    tile = conn.execute(text(
        "WITH b AS (SELECT ST_TileEnvelope(:z, :x, :y) AS env),"
        " t AS (SELECT p.id, p.map_lot, ST_AsMVTGeom(ST_Transform(p.geom, 3857), b.env) AS geom"
        "  FROM parcel p, b WHERE p.import_id = :i AND p.geom && ST_Transform(b.env, 26919))"
        " SELECT ST_AsMVT(t.*, 'parcels') FROM t WHERE t.geom IS NOT NULL"
    ), {"z": z, "x": x, "y": y, "i": imp.id}).scalar()
    if not tile:
        return Response(status_code=204)
    return Response(bytes(tile), media_type="application/vnd.mapbox-vector-tile",
                    headers={"Cache-Control": "public, max-age=3600"})
