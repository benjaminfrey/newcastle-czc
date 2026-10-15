import math

from fastapi.testclient import TestClient

from portal_api.main import create_app
from tests.test_property import layers  # noqa: F401  (fixture)


def _tile(lon, lat, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def test_tile_over_the_lots_has_parcels(engine, settings, outbox, layers):
    settings.allow_stale_parcels = True
    x, y = _tile(-69.577, 44.041, 15)
    with TestClient(create_app(settings, outbox)) as c:
        r = c.get(f"/api/tiles/parcels/15/{x}/{y}.pbf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/vnd.mapbox-vector-tile"
    assert b"parcels" in r.content and b"004-036" in r.content


def test_low_zoom_and_empty_tiles_are_204(engine, settings, outbox, layers):
    settings.allow_stale_parcels = True
    with TestClient(create_app(settings, outbox)) as c:
        assert c.get("/api/tiles/parcels/8/77/93.pbf").status_code == 204
        x, y = _tile(-70.5, 43.5, 15)
        assert c.get(f"/api/tiles/parcels/15/{x}/{y}.pbf").status_code == 204


def test_tiles_refuse_stale_parcels(engine, settings, outbox, layers):
    x, y = _tile(-69.577, 44.041, 15)
    with TestClient(create_app(settings, outbox)) as c:
        assert c.get(f"/api/tiles/parcels/15/{x}/{y}.pbf").status_code == 503
