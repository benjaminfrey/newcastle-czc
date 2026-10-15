"""Load GIS layers for the property lookup.

  python -m portal_api.gis parcels --geolibrary
  python -m portal_api.gis parcels --file PATH --map-lot-field F [--location-field F] --source TEXT --source-date YYYY-MM-DD
  python -m portal_api.gis addresses --e911
  python -m portal_api.gis districts --file PATH --ruleset PATH --source-date YYYY-MM-DD
  python -m portal_api.gis streets --inventory PATH --types PATH --source-date YYYY-MM-DD
"""

import argparse
import json
import tempfile
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import create_engine

from portal_api.config import Settings
from portal_api.gis import sources
from portal_api.gis.load import load_layer, read_features


def _type_names(types_path: str) -> dict[str, str]:
    """Code → plain name from source/exhibits/cross-sections/types.json, whose top level maps
    each code ("S1" … "R5", plus "_meta") to an object with "code" and "name" ("RURAL ROAD")."""
    data = json.loads(Path(types_path).read_text())
    return {k: v["name"].title() for k, v in data.items() if not k.startswith("_") and "name" in v}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m portal_api.gis")
    sub = p.add_subparsers(dest="layer", required=True)
    pa = sub.add_parser("parcels")
    g = pa.add_mutually_exclusive_group(required=True)
    g.add_argument("--geolibrary", action="store_true")
    g.add_argument("--file")
    pa.add_argument("--map-lot-field", default="MAP_BK_LOT")
    pa.add_argument("--location-field")
    pa.add_argument("--source")
    pa.add_argument("--source-date", type=date.fromisoformat)
    ad = sub.add_parser("addresses")
    g = ad.add_mutually_exclusive_group(required=True)
    g.add_argument("--e911", action="store_true")
    g.add_argument("--file")
    ad.add_argument("--source")
    ad.add_argument("--source-date", type=date.fromisoformat)
    di = sub.add_parser("districts")
    di.add_argument("--file", required=True)
    di.add_argument("--ruleset", required=True)
    di.add_argument("--source", default="Traced from the District Map (Exhibit 1.1); approximate")
    di.add_argument("--source-date", type=date.fromisoformat, required=True)
    st = sub.add_parser("streets")
    st.add_argument("--inventory", required=True)
    st.add_argument("--types", required=True)
    st.add_argument("--source", default="Street Type Inventory (Exhibit 3.1)")
    st.add_argument("--source-date", type=date.fromisoformat, required=True)
    a = p.parse_args(argv)

    engine = create_engine(Settings().database_url)
    with tempfile.TemporaryDirectory() as tmp, httpx.Client() as client, engine.begin() as conn:
        if a.layer == "parcels":
            if a.geolibrary:
                path = f"{tmp}/parcels.geojson"
                sources.fetch_arcgis(sources.GEOLIBRARY_PARCELS, sources.NEWCASTLE, path, client)
                feats = read_features(path)
                source = "Maine GeoLibrary, Maine_Parcels_Organized_Towns"
                when = sources.geolibrary_source_date(feats)
                rows = sources.parcel_rows(feats, "MAP_BK_LOT", "PROP_LOC")
            else:
                if not (a.source and a.source_date):
                    p.error("--file needs --source and --source-date")
                feats = read_features(a.file)
                source, when = a.source, a.source_date
                rows = sources.parcel_rows(feats, a.map_lot_field, a.location_field)
        elif a.layer == "addresses":
            if a.e911:
                path = f"{tmp}/addresses.geojson"
                sources.fetch_arcgis(sources.E911_ADDRESSES, sources.NEWCASTLE, path, client)
                feats = read_features(path)
                source, when = "Maine E911 Address Points (MEGIS)", date.today()
            else:
                if not (a.source and a.source_date):
                    p.error("--file needs --source and --source-date")
                feats, source, when = read_features(a.file), a.source, a.source_date
            rows = sources.address_rows(feats)
        elif a.layer == "districts":
            ruleset = json.loads(Path(a.ruleset).read_text())["districts"]
            rows = sources.district_rows(read_features(a.file), ruleset)
            source, when = a.source, a.source_date
        else:
            rows = sources.street_rows(json.loads(Path(a.inventory).read_text()), _type_names(a.types))
            source, when = a.source, a.source_date
        import_id = load_layer(conn, layer=a.layer, source=source, source_date=when, rows=rows)
    print(f"{a.layer}: import {import_id}, {len(rows)} features, source date {when}")


if __name__ == "__main__":
    main()
