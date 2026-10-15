"""Where each GIS layer comes from, and how its features become rows."""

import json
from datetime import date, datetime

import httpx
import shapely

from portal_api.gis.load import Feature

# Verified against the live services 2026-10-15.
GEOLIBRARY_PARCELS = ("https://services1.arcgis.com/RbMX0mRVOFNTdLzd/arcgis/rest/services/"
                      "Maine_Parcels_Organized_Towns/FeatureServer/10")
E911_ADDRESSES = ("https://services1.arcgis.com/RbMX0mRVOFNTdLzd/arcgis/rest/services/"
                  "Maine_E911_Addresses_Feature/FeatureServer/0")
NEWCASTLE = "UPPER(TOWN)='NEWCASTLE'"
_PAGE = 1000


def fetch_arcgis(url: str, where: str, out_path: str, client: httpx.Client) -> int:
    features, offset = [], 0
    while True:
        r = client.get(f"{url}/query", params={
            "where": where, "outFields": "*", "outSR": "4326", "f": "geojson",
            "orderByFields": "OBJECTID", "resultOffset": str(offset), "resultRecordCount": str(_PAGE),
        }, timeout=60)
        r.raise_for_status()
        page = r.json()
        if "error" in page:
            raise RuntimeError(f"ArcGIS error: {page['error']}")
        features += page["features"]
        if len(page["features"]) < _PAGE and not page.get("exceededTransferLimit"):
            break
        offset += _PAGE
    with open(out_path, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    return len(features)


def geolibrary_source_date(features: list[Feature]) -> date:
    return max(datetime.strptime(f.attrs["FMUPDAT"], "%m/%d/%Y").date()
               for f in features if f.attrs.get("FMUPDAT"))


def parcel_rows(features: list[Feature], map_lot_field: str, location_field: str | None = None) -> list[dict]:
    return [{"map_lot": str(f.attrs[map_lot_field]).strip(),
             "location": (str(f.attrs[location_field]).strip() or None) if location_field else None,
             "geom": f.geom, "srid": f.srid}
            for f in features if f.attrs.get(map_lot_field)]


def address_rows(features: list[Feature]) -> list[dict]:
    rows = []
    for f in features:
        label = f"{f.attrs['ADDRESS_NUMBER']} {f.attrs['ST_FULLNAME']}".strip()
        if (f.attrs.get("UNIT") or "").strip():
            label += f", Unit {f.attrs['UNIT'].strip()}"
        rows.append({"label": label, "geom": f.geom, "srid": f.srid})
    return rows


def _district_name(trace_code: str, ruleset: list[dict]) -> str | None:
    if trace_code.upper().startswith("SD-"):
        want = trace_code[3:].upper()
        for d in ruleset:
            if d["code"] == "SD" and d["name"].upper() == want:
                return f"{d['name'].title()} special district"
        return None
    for d in ruleset:
        if d["code"] == trace_code.upper():
            return f"{d['name'].title()} ({d['code']})"
    return None


def district_rows(features: list[Feature], ruleset: list[dict]) -> list[dict]:
    rows = []
    for f in features:
        code = str(f.attrs["district"]).strip()
        name = _district_name(code, ruleset)
        rows.append({"code": code, "name": name, "in_ruleset": name is not None, "geom": f.geom, "srid": f.srid})
    return rows


def street_rows(inventory: dict, type_names: dict[str, str]) -> list[dict]:
    return [{"segment_id": s["id"], "name": s["name"], "type": s.get("type"),
             "type_name": type_names.get(s.get("type") or ""), "ownership": s.get("ownership"),
             "geom": shapely.LineString(s["geometry"]), "srid": 26919}
            for s in inventory["segments"] if s.get("geometry")]
