from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Connection

from portal_api import property as prop
from portal_api.db import transaction

router = APIRouter()


def _unavailable() -> JSONResponse:
    return JSONResponse({"detail": "parcel_data_unavailable"}, status_code=503)


def _parcels(conn, request):
    try:
        return prop.parcels_import(conn, request.app.state.settings)
    except prop.ParcelsUnavailable:
        return None


@router.get("/api/property/search")
def search(request: Request, q: str = Query(min_length=2, max_length=100), conn: Connection = transaction):
    imp = _parcels(conn, request)
    return _unavailable() if imp is None else prop.search(conn, q, imp.id)


@router.get("/api/property/at")
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


@router.get("/api/property/{parcel_id}")
def facts(parcel_id: int, request: Request, conn: Connection = transaction):
    imp = _parcels(conn, request)
    if imp is None:
        return _unavailable()
    f = prop.facts(conn, parcel_id, imp)
    return f if f else JSONResponse({"detail": "no_such_parcel"}, status_code=404)
