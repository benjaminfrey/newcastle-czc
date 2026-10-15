"""AxisGIS (CAI) parcels: the public viewer page hands every visitor an ArcGIS
token; the fetch uses it, asks only for map/lot fields, and never owner data."""

import json

import httpx
import pytest
import shapely

from portal_api.gis.load import Feature
from portal_api.gis.sources import AXISGIS_FIELDS, dissolve_by_map_lot, fetch_axisgis_parcels

PAGE = """<html><script>
window.appConfig = {"root": {"arcgis": {"token": {"www.axisgis.com": "TOK123"}}}};
window.appConfig.app.townName = 'NewcastleME'
window.appConfig.app.town = 'Newcastle'
</script></html>
"""


def _square(x):
    return {"type": "Polygon", "coordinates": [[[x, 44.0], [x + 0.001, 44.0], [x + 0.001, 44.001], [x, 44.001], [x, 44.0]]]}


def _transport(layers=None, pages=None):
    seen = []
    layers = layers if layers is not None else [{"id": 3, "name": "Roads", "type": "Feature Layer"},
                                                {"id": 10, "name": "Parcel - Poly", "type": "Feature Layer"}]
    pages = pages if pages is not None else [
        [{"type": "Feature", "properties": {"Full_Num": "004-036"}, "geometry": _square(-69.6)}],
    ]

    def handler(request: httpx.Request):
        seen.append(request)
        url = str(request.url)
        if url.startswith("https://www.axisgis.com/NewcastleME"):
            return httpx.Response(200, text=PAGE)
        if url.startswith("https://gisserver1.axisgis.com/arcgis/rest/services?"):
            return httpx.Response(200, json={"folders": ["CamdenME"]})
        if url.startswith("https://gisserver2.axisgis.com/arcgis/rest/services?"):
            return httpx.Response(200, json={"folders": ["NewcastleME", "WellsME"]})
        if url.startswith("https://gisserver2.axisgis.com/arcgis/rest/services/NewcastleME/NewcastleMEDynamic/MapServer?"):
            return httpx.Response(200, json={"layers": layers})
        if "/MapServer/10/query" in url:
            n = sum(1 for r in seen if "/MapServer/10/query" in str(r.url))
            return httpx.Response(200, json={"type": "FeatureCollection", "features": pages[n - 1] if n <= len(pages) else []})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def test_fetch_finds_the_town_and_asks_only_for_map_lot_fields(tmp_path):
    client, seen = _transport()
    out = tmp_path / "p.geojson"
    assert fetch_axisgis_parcels("NewcastleME", str(out), client) == 1
    q = next(r for r in seen if "/query" in str(r.url))
    assert q.url.params["token"] == "TOK123"
    assert q.url.params["outFields"] == AXISGIS_FIELDS and "*" not in AXISGIS_FIELDS
    assert q.headers["Referer"] == "https://www.axisgis.com/NewcastleME"
    assert q.headers["Origin"] == "https://www.axisgis.com"
    assert json.loads(out.read_text())["features"][0]["properties"]["Full_Num"] == "004-036"


def test_fields_requested_carry_no_owner_data():
    assert not {"owner", "name", "address"} & {f.lower() for f in AXISGIS_FIELDS.split(",")}


def test_fetch_pages_by_what_came_back(tmp_path):
    full = [{"type": "Feature", "properties": {"Full_Num": f"001-{i:03d}"}, "geometry": _square(-69.6)} for i in range(1000)]
    client, seen = _transport(pages=[full, full[:3]])
    assert fetch_axisgis_parcels("NewcastleME", str(tmp_path / "p.geojson"), client) == 1003
    offsets = [r.url.params["resultOffset"] for r in seen if "/query" in str(r.url)]
    assert offsets == ["0", "1000"]


def test_fetch_refuses_a_service_without_the_parcel_layer(tmp_path):
    client, _ = _transport(layers=[{"id": 3, "name": "Roads", "type": "Feature Layer"}])
    with pytest.raises(RuntimeError, match="Parcel - Poly"):
        fetch_axisgis_parcels("NewcastleME", str(tmp_path / "p.geojson"), client)


def test_fetch_explains_a_changed_page(tmp_path):
    def handler(request):
        return httpx.Response(200, text="<html>redesigned</html>")
    with pytest.raises(RuntimeError, match="appConfig"):
        fetch_axisgis_parcels("NewcastleME", str(tmp_path / "p.geojson"), httpx.Client(transport=httpx.MockTransport(handler)))


def test_dissolve_merges_pieces_of_one_lot():
    a, b = shapely.box(0, 0, 1, 1), shapely.box(5, 0, 6, 1)
    rows = dissolve_by_map_lot([
        {"map_lot": "004-036", "location": None, "geom": a, "srid": 4326},
        {"map_lot": "004-036", "location": None, "geom": b, "srid": 4326},
        {"map_lot": "004-037", "location": None, "geom": a, "srid": 4326},
    ])
    by = {r["map_lot"]: r for r in rows}
    assert len(rows) == 2 and by["004-036"]["geom"].area == 2 and by["004-036"]["geom"].geom_type == "MultiPolygon"
