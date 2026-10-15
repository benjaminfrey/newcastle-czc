import json
from datetime import date
from pathlib import Path

import httpx

from portal_api.gis.load import Feature, read_features
from portal_api.gis.sources import (
    address_rows, district_rows, fetch_arcgis, geolibrary_source_date, street_rows,
)
from tests.test_gis_load import FIX

RULESET = [{"code": "D1", "name": "RURAL"}, {"code": "D2", "name": "NEIGHBORHOOD RESIDENTIAL"},
           {"code": "SD", "name": "MARINE"}]


def test_fetch_arcgis_pages_until_done(tmp_path):
    pages = [
        {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"OBJECTID": i},
         "geometry": {"type": "Point", "coordinates": [-69.57, 44.04]}} for i in range(1000)],
         "exceededTransferLimit": True},
        {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"OBJECTID": 1000},
         "geometry": {"type": "Point", "coordinates": [-69.57, 44.04]}}]},
    ]
    seen = []

    def handler(request):
        seen.append(dict(request.url.params))
        return httpx.Response(200, json=pages[len(seen) - 1])

    out = tmp_path / "x.geojson"
    n = fetch_arcgis("https://example.test/FeatureServer/0", "TOWN='X'", str(out),
                     httpx.Client(transport=httpx.MockTransport(handler)))
    assert n == 1001
    assert [p["resultOffset"] for p in seen] == ["0", "1000"]
    assert seen[0]["outSR"] == "4326" and seen[0]["where"] == "TOWN='X'"
    assert len(json.loads(out.read_text())["features"]) == 1001


def test_geolibrary_source_date_is_the_latest_update():
    feats = [Feature({"FMUPDAT": "4/1/2012"}, None, 4326), Feature({"FMUPDAT": "11/30/2011"}, None, 4326)]
    assert geolibrary_source_date(feats) == date(2012, 4, 1)


def test_districts_are_named_only_from_the_ruleset():
    rows = {r["code"]: r for r in district_rows(read_features(str(FIX / "districts_26919.geojson")), RULESET)}
    assert rows["D2"]["name"] == "Neighborhood Residential (D2)" and rows["D2"]["in_ruleset"]
    assert rows["SD-Civic"]["name"] is None and rows["SD-Civic"]["in_ruleset"] is False


def test_special_districts_match_by_name():
    feats = [Feature({"district": "SD-Marine"}, None, 26919)]
    (row,) = district_rows(feats, RULESET)
    assert row["name"] == "Marine special district" and row["in_ruleset"]


def test_address_labels_read_naturally():
    feats = [Feature({"ADDRESS_NUMBER": 461, "ST_FULLNAME": "Sheepscot Road", "UNIT": ""}, None, 4326),
             Feature({"ADDRESS_NUMBER": 12, "ST_FULLNAME": "Main Street", "UNIT": "2"}, None, 4326)]
    assert [r["label"] for r in address_rows(feats)] == ["461 Sheepscot Road", "12 Main Street, Unit 2"]


def test_street_rows_carry_type_names_from_types_json():
    inv = {"segments": [{"id": "s-1", "name": "Sheepscot Road", "type": "R2", "ownership": "Town Way",
                         "geometry": [[453000.0, 4876000.0], [453500.0, 4876100.0]]}]}
    (row,) = street_rows(inv, {"R2": "Rural Road"})
    assert (row["segment_id"], row["type"], row["type_name"], row["srid"]) == ("s-1", "R2", "Rural Road", 26919)


def test_type_names_come_from_types_json():
    from portal_api.gis.__main__ import _type_names
    path = Path(__file__).resolve().parents[3] / "source/exhibits/cross-sections/types.json"
    raw = json.loads(path.read_text())
    names = _type_names(str(path))
    assert names["R2"] == raw["R2"]["name"].title() and names["S1"] == raw["S1"]["name"].title()
    assert "_meta" not in names
