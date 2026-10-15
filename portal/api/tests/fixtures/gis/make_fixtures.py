"""Regenerate the GIS test fixtures (run from portal/api with the dev services up):

    PYTHONPATH=. .venv/bin/python tests/fixtures/gis/make_fixtures.py

Three lots in a row on Sheepscot Road, each 0.002 deg square (~160 m x ~222 m),
and three districts drawn so each lot's district shares are predictable:
004-036 is 75 % D2 / 25 % D1, 004-037 is all D1, 004-038 is half D1, half
SD-Civic (an area the adopted ruleset does not name). District coordinates are
EPSG:26919, converted by PostGIS so no projection library is needed.
"""

import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text

HERE = Path(__file__).parent
LOTS = [("004-036", "SHEEPSCOT ROAD", -69.580), ("004-037", "SHEEPSCOT ROAD", -69.578),
        ("004-038", "RIVER ROAD", -69.576)]
DISTRICTS = [("D2", -69.590, -69.5785), ("D1", -69.5785, -69.575), ("SD-Civic", -69.575, -69.570)]
ADDRESSES = [(461, "Sheepscot Road", -69.579, 44.041), (465, "Sheepscot Road", -69.577, 44.041),
             (12, "Main Street", -69.580, 44.030)]


def box(x1, y1, x2, y2):
    return {"type": "Polygon", "coordinates": [[[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]]}


def write(name, features, crs=None):
    fc = {"type": "FeatureCollection", "features": features}
    if crs:
        fc["crs"] = {"type": "name", "properties": {"name": crs}}
    (HERE / name).write_text(json.dumps(fc, indent=1) + "\n")


def main():
    write("parcels_4326.geojson", [
        {"type": "Feature", "properties": {"MAP_BK_LOT": ml, "PROP_LOC": loc, "FMUPDAT": "4/1/2012"},
         "geometry": box(x, 44.040, round(x + 0.002, 6), 44.042)} for ml, loc, x in LOTS])
    write("addresses_4326.geojson", [
        {"type": "Feature", "properties": {"ADDRESS_NUMBER": n, "ST_FULLNAME": st, "UNIT": ""},
         "geometry": {"type": "Point", "coordinates": [x, y]}} for n, st, x, y in ADDRESSES])
    url = os.environ.get("PORTAL_TEST_DATABASE_URL", "postgresql+psycopg://portal:portal@localhost:5433/portal_test")
    eng = create_engine(url.rsplit("/", 1)[0] + "/postgres")
    feats = []
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        for code, x1, x2 in DISTRICTS:
            gj = conn.execute(text(
                "SELECT ST_AsGeoJSON(ST_Multi(ST_Transform(ST_MakeEnvelope(:x1, 44.03, :x2, 44.05, 4326), 26919)), 3)"
            ), {"x1": x1, "x2": x2}).scalar()
            feats.append({"type": "Feature", "properties": {"district": code}, "geometry": json.loads(gj)})
    write("districts_26919.geojson", feats, crs="urn:ogc:def:crs:EPSG::26919")
    print("wrote", ", ".join(sorted(p.name for p in HERE.glob("*.geojson"))))


if __name__ == "__main__":
    main()
