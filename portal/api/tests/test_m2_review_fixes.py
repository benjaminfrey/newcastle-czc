"""Fixes from the M2 whole-branch review."""

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from portal_api.gis.load import load_layer, read_features
from portal_api.gis.sources import parcel_rows, street_rows
from portal_api.main import create_app
from tests.test_gis_load import FIX
from tests.test_property import layers  # noqa: F401  (fixture)


# An import with no features must never replace a working one.

def test_parcel_rows_refuse_a_missing_map_lot_field():
    with pytest.raises(ValueError, match="MAPLOT"):
        parcel_rows(read_features(str(FIX / "parcels_4326.geojson")), "MAPLOT")


def test_an_empty_import_is_refused_and_the_old_one_stays(engine):
    feats = read_features(str(FIX / "parcels_4326.geojson"))
    with engine.begin() as conn:
        good = load_layer(conn, layer="parcels", source="ok", source_date=date(2012, 4, 1),
                          rows=parcel_rows(feats, "MAP_BK_LOT"))
    with pytest.raises(ValueError, match="no features"):
        with engine.begin() as conn:
            load_layer(conn, layer="parcels", source="empty", source_date=date(2026, 1, 1), rows=[])
    with engine.connect() as conn:
        assert conn.execute(text("SELECT id FROM gis_import WHERE layer='parcels' AND active")).scalar() == good


# Lots along a State Highway sit farther from its centreline (wide right-of-way).

def test_state_highway_frontage_reaches_past_20_m(engine, settings, outbox):
    feats = read_features(str(FIX / "parcels_4326.geojson"))
    with engine.begin() as conn:
        load_layer(conn, layer="parcels", source="t", source_date=date(2012, 4, 1), rows=parcel_rows(feats, "MAP_BK_LOT"))
        line = json.loads(conn.execute(text(
            "SELECT ST_AsGeoJSON(ST_Translate(ST_Transform(ST_SetSRID(ST_MakeLine("
            "ST_MakePoint(-69.581, 44.040), ST_MakePoint(-69.573, 44.040)), 4326), 26919), 0, -28))"
        )).scalar())["coordinates"]
        load_layer(conn, layer="streets", source="t", source_date=date(2026, 9, 14), rows=street_rows(
            {"segments": [{"id": "rt1", "name": "US Route 1", "type": "R5", "ownership": "State Highway", "geometry": line}]},
            {"R5": "Rural Highway"}))
    settings.allow_stale_parcels = True
    with TestClient(create_app(settings, outbox)) as c:
        pid = c.get("/api/property/at", params={"lon": -69.579, "lat": 44.041}).json()["parcel_id"]
        f = c.get(f"/api/property/{pid}").json()
    (st,) = f["streets"]
    assert st["name"] == "US Route 1" and 500 < st["frontage_ft"] < 560
    assert f["on_state_highway"] is True


# Public lookups are rate-limited (spec §6).

def test_lookups_are_rate_limited(engine, settings, outbox, layers):
    settings.allow_stale_parcels = True
    settings.lookup_limit_per_minute = 3
    with TestClient(create_app(settings, outbox)) as c:
        codes = [c.get("/api/property/search", params={"q": "461"}).status_code for _ in range(4)]
        assert codes == [200, 200, 200, 429]
        assert c.get("/api/property/at", params={"lon": -69.579, "lat": 44.041}).json() == {"detail": "too_many_requests"}


def test_tiles_have_their_own_larger_limit(engine, settings, outbox, layers):
    settings.allow_stale_parcels = True
    settings.lookup_limit_per_minute = 1
    settings.tile_limit_per_minute = 2
    with TestClient(create_app(settings, outbox)) as c:
        assert c.get("/api/property/search", params={"q": "461"}).status_code == 200
        codes = [c.get("/api/tiles/parcels/8/77/93.pbf").status_code for _ in range(3)]
    assert codes == [204, 204, 429]


def test_limits_are_per_address(engine, settings, outbox, layers):
    settings.allow_stale_parcels = True
    settings.lookup_limit_per_minute = 1
    app = create_app(settings, outbox)
    with TestClient(app, client=("203.0.113.1", 1)) as a, TestClient(app, client=("203.0.113.2", 1)) as b:
        assert a.get("/api/property/search", params={"q": "461"}).status_code == 200
        assert b.get("/api/property/search", params={"q": "461"}).status_code == 200
        assert a.get("/api/property/search", params={"q": "461"}).status_code == 429
