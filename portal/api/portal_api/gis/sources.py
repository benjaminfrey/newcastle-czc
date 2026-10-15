"""Where each GIS layer comes from, and how its features become rows."""

import json
import re
from collections import defaultdict
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


def fetch_arcgis(url: str, where: str, out_path: str, client: httpx.Client, *,
                 out_fields: str = "*", params: dict | None = None, headers: dict | None = None) -> int:
    features, offset = [], 0
    while True:
        r = client.get(f"{url}/query", params={
            "where": where, "outFields": out_fields, "outSR": "4326", "f": "geojson",
            "orderByFields": "OBJECTID", "resultOffset": str(offset), "resultRecordCount": str(_PAGE),
            **(params or {}),
        }, headers=headers, timeout=60)
        r.raise_for_status()
        page = r.json()
        if "error" in page:
            raise RuntimeError(f"ArcGIS error: {page['error']}")
        got = page["features"]
        features += got
        # GeoJSON responses put exceededTransferLimit under "properties"; a server may also
        # cap a page below what was asked, so advance by what actually came back.
        more = page.get("exceededTransferLimit") or page.get("properties", {}).get("exceededTransferLimit")
        if not got or (len(got) < _PAGE and not more):
            break
        offset += len(got)
    with open(out_path, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    return len(features)


# AxisGIS (CAI) hosts the Town's current tax maps. Its public viewer page gives every
# visitor an ArcGIS token in window.appConfig; we use that token, with the same
# Referer/Origin a browser sends, to read the parcel layer. Only map/lot fields are
# requested — never owner (CAMA) data. Verified 2026-10-15 (layer 10 on gisserver1).
AXISGIS = "https://www.axisgis.com"
AXISGIS_SERVERS = ("gisserver1.axisgis.com", "gisserver2.axisgis.com", "gisserver3.axisgis.com")
AXISGIS_PARCEL_LAYER = "Parcel - Poly"
AXISGIS_FIELDS = "OBJECTID,Map,Lot,Sublot,Subsublot,Full_Num"
_UA = "Newcastle-Applicant-Portal (parcel import)"


def _axis_headers(slug: str) -> dict:
    return {"Referer": f"{AXISGIS}/{slug}", "Origin": AXISGIS, "User-Agent": _UA}


def fetch_axisgis_parcels(slug: str, out_path: str, client: httpx.Client) -> int:
    html = client.get(f"{AXISGIS}/{slug}", headers={"User-Agent": _UA}, timeout=60).text
    m = re.search(r"window\.appConfig\s*=\s*(\{.*?\})\s*;\s*\n", html, re.DOTALL)
    folder = re.search(r"window\.appConfig\.app\.townName\s*=\s*['\"]([^'\"]+)['\"]", html)
    if not (m and folder):
        raise RuntimeError(f"no window.appConfig on {AXISGIS}/{slug}; has the AxisGIS page changed?")
    token = json.loads(m.group(1)).get("root", {}).get("arcgis", {}).get("token", {}).get("www.axisgis.com")
    if not token:
        raise RuntimeError("the AxisGIS appConfig carries no token; has AxisGIS changed how it issues them?")
    folder = folder.group(1)
    headers = _axis_headers(slug)
    root = None
    for host in AXISGIS_SERVERS:
        listing = client.get(f"https://{host}/arcgis/rest/services", params={"f": "json"}, headers=headers, timeout=60)
        if listing.status_code == 200 and folder in listing.json().get("folders", []):
            root = f"https://{host}/arcgis/rest/services/{folder}/{folder}Dynamic/MapServer"
            break
    if root is None:
        raise RuntimeError(f"folder {folder!r} not found on {', '.join(AXISGIS_SERVERS)}")
    layers = client.get(root, params={"f": "json", "token": token}, headers=headers, timeout=60).json().get("layers", [])
    layer = next((L["id"] for L in layers
                  if L.get("type") == "Feature Layer" and L.get("name") == AXISGIS_PARCEL_LAYER), None)
    if layer is None:
        raise RuntimeError(f"no {AXISGIS_PARCEL_LAYER!r} layer in {root}")
    return fetch_arcgis(f"{root}/{layer}", "1=1", out_path, client,
                        out_fields=AXISGIS_FIELDS, params={"token": token}, headers=headers)


def geolibrary_source_date(features: list[Feature]) -> date:
    return max(datetime.strptime(f.attrs["FMUPDAT"], "%m/%d/%Y").date()
               for f in features if f.attrs.get("FMUPDAT"))


def parcel_rows(features: list[Feature], map_lot_field: str, location_field: str | None = None) -> list[dict]:
    if features and map_lot_field not in features[0].attrs:
        raise ValueError(f"the file has no {map_lot_field!r} field; its fields are {sorted(features[0].attrs)}")
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


# Article 2 §5 adopts the Civic District: municipally owned land, "not subject to the
# standards of this Ordinance". It has no district page, so the ruleset's districts.json
# (built from the 13 district pages) does not list it; it is recognised here instead.
CIVIC_CODE = "SD-CIVIC"
CIVIC_NAME = "Civic district (Town-owned land)"


def _district_name(trace_code: str, ruleset: list[dict]) -> str | None:
    if trace_code.upper() == CIVIC_CODE:
        return CIVIC_NAME
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


def dissolve_by_map_lot(rows: list[dict]) -> list[dict]:
    """One row per map/lot: a lot drawn as separate pieces (split by a road, say)
    becomes one MultiPolygon, so its area and outline are the whole lot's."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["map_lot"]].append(r)
    out = []
    for parts in groups.values():
        if len(parts) == 1:
            out.append(parts[0])
            continue
        geom = shapely.union_all([p["geom"] for p in parts])
        if geom.geom_type == "Polygon":
            geom = shapely.MultiPolygon([geom])
        out.append({**parts[0], "geom": geom})
    return out
