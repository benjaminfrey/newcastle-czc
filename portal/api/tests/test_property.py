import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from portal_api.gis.load import load_layer, read_features
from portal_api.gis.sources import address_rows, district_rows, parcel_rows, street_rows
from portal_api.main import create_app
from tests.test_gis_load import FIX

RULESET = [{"code": "D1", "name": "RURAL"}, {"code": "D2", "name": "NEIGHBORHOOD RESIDENTIAL"}]


def _south_edge_utm(conn):
    """A street line 5 m south of the three test lots, in EPSG:26919."""
    gj = conn.execute(text(
        "SELECT ST_AsGeoJSON(ST_Translate(ST_Transform(ST_SetSRID(ST_MakeLine("
        "ST_MakePoint(-69.581, 44.040), ST_MakePoint(-69.573, 44.040)), 4326), 26919), 0, -5))"
    )).scalar()
    return json.loads(gj)["coordinates"]


@pytest.fixture
def layers(engine):
    with engine.begin() as conn:
        load_layer(conn, layer="parcels", source="GeoLibrary test", source_date=date(2012, 4, 1),
                   rows=parcel_rows(read_features(str(FIX / "parcels_4326.geojson")), "MAP_BK_LOT", "PROP_LOC"))
        load_layer(conn, layer="addresses", source="E911 test", source_date=date(2026, 10, 15),
                   rows=address_rows(read_features(str(FIX / "addresses_4326.geojson"))))
        load_layer(conn, layer="districts", source="trace test", source_date=date(2026, 6, 1),
                   rows=district_rows(read_features(str(FIX / "districts_26919.geojson")), RULESET))
        load_layer(conn, layer="streets", source="inventory test", source_date=date(2026, 9, 14),
                   rows=street_rows({"segments": [{"id": "sheepscot-1", "name": "Sheepscot Road", "type": "R2",
                                                   "ownership": "State Highway", "geometry": _south_edge_utm(conn)}]},
                                    {"R2": "Rural Road"}))


@pytest.fixture
def open_client(engine, settings, outbox, layers):
    settings.allow_stale_parcels = True
    with TestClient(create_app(settings, outbox)) as c:
        yield c


def _id(client, map_lot):
    hits = client.get("/api/property/search", params={"q": map_lot}).json()
    return next(h["parcel_id"] for h in hits if h["parcel_id"])


def test_search_finds_an_address_and_its_lot(open_client):
    hits = open_client.get("/api/property/search", params={"q": "461 sheep"}).json()
    assert hits[0]["label"] == "461 Sheepscot Road" and hits[0]["parcel_id"]


def test_search_tolerates_a_typo(open_client):
    hits = open_client.get("/api/property/search", params={"q": "461 Sheepscott Rd"}).json()
    assert "461 Sheepscot Road" in [h["label"] for h in hits]


def test_search_by_map_and_lot(open_client):
    hits = open_client.get("/api/property/search", params={"q": "4-36"}).json()
    assert hits[0]["label"] == "Map 4, Lot 36" and hits[0]["parcel_id"]


def test_search_returns_address_without_parcel(open_client):
    hits = open_client.get("/api/property/search", params={"q": "12 Main"}).json()
    assert hits[0]["label"] == "12 Main Street" and hits[0]["parcel_id"] is None


def test_search_treats_wildcards_literally(open_client):
    for q in ("%%", "__", "'; DROP TABLE parcel; --", "\\"):
        r = open_client.get("/api/property/search", params={"q": q})
        assert r.status_code in (200, 422) and (r.status_code == 422 or r.json() == [])


def test_search_query_length_is_bounded(open_client):
    assert open_client.get("/api/property/search", params={"q": "x"}).status_code == 422
    assert open_client.get("/api/property/search", params={"q": "x" * 101}).status_code == 422


def test_at_finds_the_lot_under_a_point(open_client):
    pid = open_client.get("/api/property/at", params={"lon": -69.579, "lat": 44.041}).json()["parcel_id"]
    assert open_client.get(f"/api/property/{pid}").json()["map_lot"] == "004-036"


def test_at_returns_404_off_any_parcel(open_client):
    r = open_client.get("/api/property/at", params={"lon": -69.60, "lat": 44.00})
    assert r.status_code == 404 and r.json() == {"detail": "no_parcel_here"}


def test_facts_lists_every_district_by_share(open_client):
    f = open_client.get(f"/api/property/{_id(open_client, '4-36')}").json()
    assert [d["code"] for d in f["districts"]] == ["D2", "D1"]
    assert 0.70 < f["districts"][0]["share"] < 0.80
    assert f["districts"][0]["name"] == "Neighborhood Residential (D2)"


def test_facts_name_the_civic_district(open_client):
    f = open_client.get(f"/api/property/{_id(open_client, '4-38')}").json()
    civic = next(d for d in f["districts"] if d["code"] == "SD-Civic")
    assert civic["in_ruleset"] is True and civic["name"] == "Civic district (Town-owned land)"


def test_facts_give_area_street_frontage_and_dates(open_client):
    f = open_client.get(f"/api/property/{_id(open_client, '4-36')}").json()
    assert 8.0 < f["acres"] < 9.5  # ~160 m x ~222 m = ~8.8 acres
    (st,) = f["streets"]
    assert st["name"] == "Sheepscot Road" and st["type_name"] == "Rural Road"
    assert 500 < st["frontage_ft"] < 560 and st["frontage_ft"] % 5 == 0  # the lot is ~160 m (525 ft) wide
    assert f["on_state_highway"] is True
    assert f["as_of"]["parcels"] == "2012-04-01"
    assert f["geometry"]["type"] == "MultiPolygon"


def test_unknown_parcel_is_404(open_client):
    r = open_client.get("/api/property/999999")
    assert r.status_code == 404 and r.json() == {"detail": "no_such_parcel"}


def test_districts_list_only_adopted_ones(open_client):
    assert open_client.get("/api/property/districts").json() == [
        {"code": "D1", "name": "Rural (D1)"}, {"code": "D2", "name": "Neighborhood Residential (D2)"},
        {"code": "SD-Civic", "name": "Civic district (Town-owned land)"}]


def test_stale_parcels_are_refused_by_default(engine, settings, outbox, layers):
    with TestClient(create_app(settings, outbox)) as c:
        for path, params in (("/api/property/search", {"q": "461"}), ("/api/property/at", {"lon": -69.579, "lat": 44.041}),
                             ("/api/property/1", {})):
            r = c.get(path, params=params)
            assert r.status_code == 503 and r.json() == {"detail": "parcel_data_unavailable"}
        assert c.get("/api/property/districts").status_code == 200


def test_no_parcels_loaded_is_unavailable(engine, settings, outbox):
    settings.allow_stale_parcels = True
    with TestClient(create_app(settings, outbox)) as c:
        assert c.get("/api/property/search", params={"q": "461"}).status_code == 503
