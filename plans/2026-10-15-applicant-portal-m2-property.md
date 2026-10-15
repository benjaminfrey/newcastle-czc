# Applicant Portal M2 — Property Lookup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The "Where is it?" step: an applicant types an address or taps the map, sees their lot
outlined with its map/lot, district, approximate size and street, and confirms it or says "this
doesn't look right"; when lookup is impossible they enter map/lot and district by hand.

**Architecture:** GIS layers (parcels, E911 address points, traced districts, the Street Type
inventory) are loaded into PostGIS by a CLI (`python -m portal_api.gis`) that reads any
OGR-readable file or an ArcGIS service, records each import's source and date, and activates it.
FastAPI serves address search, point-in-parcel, property facts and parcel vector tiles; a
production guard refuses parcel data older than a set age. The web app draws a self-hosted
Protomaps basemap (no third-party map requests) with MapLibre, plus our parcel tiles.

**Tech Stack:** M1's stack, plus PostGIS `pg_trgm`, pyogrio 0.13.0, shapely 2.2.0, httpx 0.28.1
(runtime), pmtiles 3.8.1 (Python, basemap tool only), maplibre-gl 6.14.0, pmtiles 4.5.0 (npm),
@protomaps/basemaps 5.7.2.

**Spec:** `specs/2026-10-14-applicant-portal-design.md` (§3 component 5, §4 step 2, §6) ·
**Roadmap:** `plans/2026-10-14-applicant-portal-roadmap.md` (M2) · **Built on:** M1, merged as
`d3b5890`.

## Decisions made with the chair (2026-10-15)

- **Parcels: GeoLibrary's Newcastle layer is from 2012.** All 1,558 parcels in
  `Maine_Parcels_Organized_Towns` carry `FMUPDAT 4/1/2012`, `FMUPDORG NorthernGeo`. AxisGIS (CAI)
  is current but its services are behind a sign-in; the chair is requesting a file export from the
  assessor/CAI. So the import takes **any parcel file or service**, development and tests use the
  2012 layer, every response carries the data's date, and **production refuses parcel data older
  than `parcel_max_age_days` (default 1095) unless `PORTAL_ALLOW_STALE_PARCELS=true`** — set only
  on the dev VM. 2012 lines never reach a real applicant.
- **Basemap: self-hosted.** A Protomaps extract of the Newcastle area plus its fonts and sprites,
  served from our own server. No applicant's map view is requested from anyone else.
- **Districts are an approximate trace** of the District Map (`data/street-types/districts.geojson`,
  EPSG:26919, 14 areas). Every district answer says so and that the CEO confirms it.
- **Only adopted districts are named.** The trace has 14 areas; the adopted ruleset
  (`build/permit-review/rulesets/adopted-v1.0/districts.json`) has 13 — **SD-Civic is not in it**.
  An area not in the pinned ruleset is stored with `in_ruleset = false` and shown as "staff will
  confirm the district", never by its draft name.
- **Street Types come from the adopted Exhibit 3.1** (`source/exhibits/street-types/inventory.json`,
  214 segments, unchanged since `v1.0`). Its `_meta.banner` says "DRAFT"; that string is stale
  data the Code's renderer replaces in the adopted edition — ignore it.

## Global Constraints

- All M1 Global Constraints still hold (VM workflow via `portal/vm.sh`; stage by name; commit
  trailer; no push/merge without the chair; no trackers, no AI, ids-only events).
- **No third-party request from the applicant's browser.** Basemap tiles, fonts and sprites are
  served from our origin. Attribution "© OpenStreetMap contributors" is shown on the map.
- **Never guess a legal value.** District names come from the pinned ruleset; Type names from
  `source/exhibits/cross-sections/types.json`; nothing is restated from memory.
- **Every derived fact is labelled approximate** where it is (lot area and frontage measured from
  the map; district from a trace) and says the Code Enforcement Officer confirms it.
- **Production refuses stale parcels** (above). The guard applies to search, point lookup, facts
  and parcel tiles alike.
- Property endpoints are public (no sign-in): spec §4 step 2 comes before sign-in. They read only.
- Lookups are not written to the event log; imports are (`gis.imported`, ids and counts only).

## Review Focus

1. **A lot in two districts.** The applicant must see both, with the larger first, not a silent
   pick — Task 4 `test_facts_lists_every_district_by_share`.
2. **An address point that falls on no parcel** (a point on a road or a boundary). The result must
   still come back, with no parcel, and the page must ask the person to tap their lot — Task 4
   `test_search_returns_address_without_parcel`, Task 7 "asks for a tap when the address has no lot".
3. **Stale parcel data in production.** Lookup must answer 503 and the page must fall back to
   manual entry, never show the old lines — Task 4 `test_stale_parcels_are_refused_by_default`,
   Task 5 `test_tiles_refuse_stale_parcels`, Task 7 "falls back to entering it by hand".
4. **Search text with `%`, `_`, quotes or SQL.** Literal matching, no error — Task 4
   `test_search_treats_wildcards_literally`.
5. **A tap in the river or outside town.** A plain "no lot there", not an error page — Task 4
   `test_at_returns_404_off_any_parcel`, Task 7 "says so when nothing is at the tapped spot".

---

## Task 0: Data on the VM

The loaders read four files that live outside `portal/`. `portal/vm.sh` syncs only `portal/`.

**Files:**
- Modify: `portal/vm.sh` (sync four reference files to the same paths under `~/newcastle-czc/`)

- [ ] **Step 1:** In `sync()`, after the existing `rsync`, add:

```bash
  # Reference data the GIS loaders read, kept at the same repo-relative paths on the VM.
  (cd "$HERE/.." && rsync -azR \
    data/street-types/districts.geojson \
    source/exhibits/street-types/inventory.json \
    source/exhibits/cross-sections/types.json \
    build/permit-review/rulesets/adopted-v1.0/districts.json \
    "$VM:$REMOTE_ROOT/")
```

- [ ] **Step 2:** Run `portal/vm.sh run 'ls -la data/street-types source/exhibits/street-types build/permit-review/rulesets/adopted-v1.0'`
Expected: the four files listed.

- [ ] **Step 3:** Commit: `git add portal/vm.sh` → `portal: sync the GIS reference files to the VM (M2 Task 0)`.

---

## Task 1: GIS schema and the stale-data settings

**Files:**
- Create: `portal/api/migrations/versions/0004_gis.py`
- Create: `portal/api/tests/test_gis_schema.py`
- Modify: `portal/api/portal_api/config.py`, `portal/api/tests/conftest.py` (TRUNCATE list)

**Interfaces:**
- Produces tables `gis_import(id, layer, source, source_date, imported_at, feature_count, active)`
  (one active row per layer), `parcel(id, import_id, map_lot, location, geom MultiPolygon/26919)`,
  `address_point(id, import_id, label, geom Point/26919)`,
  `district_area(id, import_id, code, name, in_ruleset, geom MultiPolygon/26919)`,
  `street_segment(id, import_id, segment_id, name, type, type_name, ownership, geom MultiLineString/26919)`.
- Produces settings `allow_stale_parcels: bool = False`, `parcel_max_age_days: int = 1095`.

- [ ] **Step 1: Write the failing test** — `portal/api/tests/test_gis_schema.py`:

```python
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from portal_api.config import Settings


def test_stale_parcels_are_refused_unless_allowed():
    s = Settings()
    assert s.allow_stale_parcels is False
    assert s.parcel_max_age_days == 1095


def test_only_one_active_import_per_layer(engine):
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO gis_import (layer, source, source_date, active) VALUES ('parcels','a','2026-01-01',true)"
        ))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO gis_import (layer, source, source_date, active) VALUES ('parcels','b','2026-01-02',true)"
            ))


def test_layer_is_restricted(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO gis_import (layer, source, source_date) VALUES ('zoning','a','2026-01-01')"
            ))


def test_trigram_extension_installed(engine):
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1 FROM pg_extension WHERE extname='pg_trgm'")).scalar() == 1
```

- [ ] **Step 2:** Run `portal/vm.sh run 'cd portal/api && .venv/bin/pytest -p no:warnings tests/test_gis_schema.py'` — Expected: FAIL (`no field allow_stale_parcels`, `relation "gis_import" does not exist`).

- [ ] **Step 3: Implement.** `portal/api/migrations/versions/0004_gis.py`:

```python
"""GIS layers for the property lookup: each import is recorded with its source
and date, and exactly one import per layer is active.

Revision ID: 0004
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    CREATE TABLE gis_import (
        id             bigserial PRIMARY KEY,
        layer          text NOT NULL CHECK (layer IN ('parcels', 'addresses', 'districts', 'streets')),
        source         text NOT NULL,
        source_date    date NOT NULL,
        imported_at    timestamptz NOT NULL DEFAULT now(),
        feature_count  integer NOT NULL DEFAULT 0,
        active         boolean NOT NULL DEFAULT false
    );
    CREATE UNIQUE INDEX gis_import_one_active ON gis_import (layer) WHERE active;

    CREATE TABLE parcel (
        id         bigserial PRIMARY KEY,
        import_id  bigint NOT NULL REFERENCES gis_import(id) ON DELETE CASCADE,
        map_lot    text NOT NULL,
        location   text,
        geom       geometry(MultiPolygon, 26919) NOT NULL
    );
    CREATE INDEX parcel_geom ON parcel USING gist (geom);
    CREATE INDEX parcel_import_map_lot ON parcel (import_id, map_lot);

    CREATE TABLE address_point (
        id         bigserial PRIMARY KEY,
        import_id  bigint NOT NULL REFERENCES gis_import(id) ON DELETE CASCADE,
        label      text NOT NULL,
        geom       geometry(Point, 26919) NOT NULL
    );
    CREATE INDEX address_point_geom ON address_point USING gist (geom);
    CREATE INDEX address_point_label_trgm ON address_point USING gin (lower(label) gin_trgm_ops);

    CREATE TABLE district_area (
        id          bigserial PRIMARY KEY,
        import_id   bigint NOT NULL REFERENCES gis_import(id) ON DELETE CASCADE,
        code        text NOT NULL,
        name        text,
        in_ruleset  boolean NOT NULL,
        geom        geometry(MultiPolygon, 26919) NOT NULL
    );
    CREATE INDEX district_area_geom ON district_area USING gist (geom);

    CREATE TABLE street_segment (
        id          bigserial PRIMARY KEY,
        import_id   bigint NOT NULL REFERENCES gis_import(id) ON DELETE CASCADE,
        segment_id  text NOT NULL,
        name        text NOT NULL,
        type        text,
        type_name   text,
        ownership   text,
        geom        geometry(MultiLineString, 26919) NOT NULL
    );
    CREATE INDEX street_segment_geom ON street_segment USING gist (geom);
    """)


def downgrade() -> None:
    # pg_trgm is left installed, like postgis in 0001.
    op.execute("""
    DROP TABLE street_segment;
    DROP TABLE district_area;
    DROP TABLE address_point;
    DROP TABLE parcel;
    DROP TABLE gis_import;
    """)
```

In `config.py`, after `signin_limit_global`, add:

```python
    # Parcel data older than this is refused (lookup falls back to manual entry).
    # Only the dev VM sets allow_stale_parcels, so old lot lines never reach applicants.
    allow_stale_parcels: bool = False
    parcel_max_age_days: int = 1095
```

In `conftest.py` change the TRUNCATE to
`"TRUNCATE applicant, signin_token, session, event, gis_import RESTART IDENTITY CASCADE"`.

- [ ] **Step 4:** Run the whole API suite. Expected: `50 passed`. Also run the migration round trip
  (`alembic upgrade head`, `downgrade base`, `upgrade head` against the dev database) — no errors.

- [ ] **Step 5:** Commit `0004_gis.py`, `test_gis_schema.py`, `config.py`, `conftest.py` →
  `portal: GIS schema and the stale-parcel guard settings (M2 Task 1)`.

---

## Task 2: The layer loader

**Files:**
- Modify: `portal/api/requirements.txt` (add `pyogrio==0.13.0`, `shapely==2.2.0`, `httpx==0.28.1`; remove `httpx` from `requirements-dev.txt`)
- Create: `portal/api/portal_api/gis/__init__.py` (empty), `portal/api/portal_api/gis/load.py`
- Create: `portal/api/tests/fixtures/gis/parcels_4326.geojson`, `districts_26919.geojson`, `addresses_4326.geojson`
- Create: `portal/api/tests/test_gis_load.py`

**Interfaces:**
- Produces `read_features(path: str) -> list[Feature]`; `Feature(attrs: dict, geom: shapely geometry, srid: int)`.
- Produces `load_layer(conn, *, layer: str, source: str, source_date: date, rows: list[dict]) -> int`
  (returns the import id; inserts, activates, deactivates the previous import of that layer,
  appends a `gis.imported` event). Row keys by layer — parcels: `map_lot, location, geom, srid`;
  addresses: `label, geom, srid`; districts: `code, name, in_ruleset, geom, srid`;
  streets: `segment_id, name, type, type_name, ownership, geom, srid`.

Fixture geometry (all in Newcastle; designed so tests can predict answers):
- `parcels_4326.geojson` — three parcels, CRS default (WGS84), property `MAP_BK_LOT`, `PROP_LOC`:
  - `004-036`, "SHEEPSCOT ROAD": square lon −69.580…−69.578, lat 44.040…44.042.
  - `004-037`, "SHEEPSCOT ROAD": square lon −69.578…−69.576, lat 44.040…44.042 (east neighbour).
  - `004-038`, "RIVER ROAD": square lon −69.576…−69.574, lat 44.040…44.042.
- `districts_26919.geojson` — CRS `urn:ogc:def:crs:EPSG::26919`, property `district`. Build it
  with shapely in the test-fixture generation step below from the lon/lat boxes:
  - `D2`: everything west of lon −69.5785 inside lat 44.03…44.05.
  - `D1`: lon −69.5785…−69.575.
  - `SD-Civic`: lon −69.575…−69.570 (a district **not** in the ruleset).
  So `004-036` is ~75 % D2 / 25 % D1, `004-037` is all D1, `004-038` is half D1, half SD-Civic.
- `addresses_4326.geojson` — `ADDRESS_NUMBER`, `ST_FULLNAME`, `UNIT`:
  - 461 Sheepscot Road at the centre of `004-036`;
  - 465 Sheepscot Road at the centre of `004-037`;
  - 12 Main Street at lon −69.5800, lat 44.0300 (on no parcel).

- [ ] **Step 1: Generate the fixtures.** Write `portal/api/tests/fixtures/gis/make_fixtures.py`,
  kept in the repo so the fixtures can be regenerated. It writes the parcel and address files
  directly in WGS84 with `shapely.geometry.box`/`Point` and `json`, and gets the district boxes'
  EPSG:26919 coordinates from PostGIS (no projection library needed offline): for each box it runs
  `SELECT ST_AsGeoJSON(ST_Transform(ST_MakeEnvelope(:x1, :y1, :x2, :y2, 4326), 26919))` against
  `PORTAL_TEST_DATABASE_URL`'s server and writes the result with the
  `{"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::26919"}}` `crs` member. Run it
  once and copy the files back so they are committed:

```bash
portal/vm.sh run 'cd portal/api && PYTHONPATH=. .venv/bin/python tests/fixtures/gis/make_fixtures.py'
```

```bash
rsync -az ben@192.168.1.6:newcastle-czc/portal/api/tests/fixtures/gis/ portal/api/tests/fixtures/gis/
```

  Expected: three files; `districts_26919.geojson` coordinates around x ≈ 453 000–454 500,
  y ≈ 4 876 000–4 878 300.

- [ ] **Step 2: Write the failing test** — `portal/api/tests/test_gis_load.py`:

```python
from datetime import date
from pathlib import Path

from sqlalchemy import text

from portal_api.gis.load import load_layer, read_features

FIX = Path(__file__).parent / "fixtures" / "gis"


def _parcel_rows():
    return [
        {"map_lot": f.attrs["MAP_BK_LOT"], "location": f.attrs["PROP_LOC"], "geom": f.geom, "srid": f.srid}
        for f in read_features(str(FIX / "parcels_4326.geojson"))
    ]


def test_read_features_reports_the_files_crs():
    assert {f.srid for f in read_features(str(FIX / "parcels_4326.geojson"))} == {4326}
    assert {f.srid for f in read_features(str(FIX / "districts_26919.geojson"))} == {26919}


def test_load_reprojects_to_utm_and_activates(engine):
    with engine.begin() as conn:
        import_id = load_layer(conn, layer="parcels", source="test", source_date=date(2012, 4, 1),
                               rows=_parcel_rows())
    with engine.connect() as conn:
        imp = conn.execute(text("SELECT active, feature_count, source_date FROM gis_import WHERE id=:i"),
                           {"i": import_id}).one()
        srid, x = conn.execute(text("SELECT ST_SRID(geom), ST_X(ST_Centroid(geom)) FROM parcel LIMIT 1")).one()
    assert imp.active and imp.feature_count == 3 and imp.source_date == date(2012, 4, 1)
    assert srid == 26919 and 440_000 < x < 470_000


def test_a_new_import_replaces_the_active_one(engine):
    with engine.begin() as conn:
        first = load_layer(conn, layer="parcels", source="old", source_date=date(2012, 4, 1), rows=_parcel_rows())
        second = load_layer(conn, layer="parcels", source="new", source_date=date(2026, 10, 1), rows=_parcel_rows())
    with engine.connect() as conn:
        active = conn.execute(text("SELECT id FROM gis_import WHERE layer='parcels' AND active")).scalars().all()
    assert active == [second] and first != second


def test_import_is_logged_without_personal_details(engine):
    with engine.begin() as conn:
        load_layer(conn, layer="parcels", source="test", source_date=date(2012, 4, 1), rows=_parcel_rows())
    with engine.connect() as conn:
        kind, payload = conn.execute(text("SELECT kind, payload_json FROM event")).one()
    assert kind == "gis.imported" and '"features":3' in payload and '"layer":"parcels"' in payload


def test_a_failed_load_leaves_the_previous_import_active(engine):
    with engine.begin() as conn:
        good = load_layer(conn, layer="parcels", source="ok", source_date=date(2012, 4, 1), rows=_parcel_rows())
    bad = _parcel_rows()
    bad[1]["map_lot"] = None  # violates NOT NULL
    try:
        with engine.begin() as conn:
            load_layer(conn, layer="parcels", source="bad", source_date=date(2026, 1, 1), rows=bad)
    except Exception:
        pass
    with engine.connect() as conn:
        assert conn.execute(text("SELECT id FROM gis_import WHERE layer='parcels' AND active")).scalar() == good
```

- [ ] **Step 3:** Run it. Expected: FAIL — `No module named 'portal_api.gis'`.

- [ ] **Step 4: Implement** `portal/api/portal_api/gis/load.py`:

```python
"""Load a GIS layer into PostGIS: any OGR-readable file in, EPSG:26919 out.

Each load is one gis_import row. It becomes the active import for its layer only
when every feature has been inserted, inside the caller's transaction, so a
failed load leaves the previous import active.
"""

import re
from dataclasses import dataclass
from datetime import date

import pyogrio
import shapely
from sqlalchemy import Connection, text

from portal_api.events import append_event

WORKING_SRID = 26919  # NAD83 / UTM 19N, metres — the CZC GIS pipeline's CRS


@dataclass(frozen=True)
class Feature:
    attrs: dict
    geom: shapely.Geometry
    srid: int


def _srid(crs: str | None) -> int:
    m = re.search(r"EPSG:+(\d+)", crs or "")
    if not m:
        raise ValueError(f"cannot tell the coordinate system of this file ({crs!r})")
    return int(m.group(1))


def read_features(path: str) -> list[Feature]:
    meta, _fids, geometry, field_data = pyogrio.raw.read(path)
    srid = _srid(meta["crs"])
    names = list(meta["fields"])
    out = []
    for i, wkb in enumerate(geometry):
        if wkb is None:
            continue
        attrs = {name: field_data[j][i] for j, name in enumerate(names)}
        out.append(Feature(attrs=attrs, geom=shapely.from_wkb(wkb), srid=srid))
    return out


def _geom_sql(multi: bool) -> str:
    g = f"ST_Transform(ST_SetSRID(ST_GeomFromWKB(:wkb), :srid), {WORKING_SRID})"
    return f"ST_Multi({g})" if multi else g


_INSERT = {
    "parcels": ("INSERT INTO parcel (import_id, map_lot, location, geom) "
                f"VALUES (:imp, :map_lot, :location, {_geom_sql(True)})"),
    "addresses": ("INSERT INTO address_point (import_id, label, geom) "
                  f"VALUES (:imp, :label, {_geom_sql(False)})"),
    "districts": ("INSERT INTO district_area (import_id, code, name, in_ruleset, geom) "
                  f"VALUES (:imp, :code, :name, :in_ruleset, {_geom_sql(True)})"),
    "streets": ("INSERT INTO street_segment (import_id, segment_id, name, type, type_name, ownership, geom) "
                f"VALUES (:imp, :segment_id, :name, :type, :type_name, :ownership, {_geom_sql(True)})"),
}


def load_layer(conn: Connection, *, layer: str, source: str, source_date: date, rows: list[dict]) -> int:
    import_id = conn.execute(text(
        "INSERT INTO gis_import (layer, source, source_date) VALUES (:l, :s, :d) RETURNING id"
    ), {"l": layer, "s": source, "d": source_date}).scalar()
    sql = text(_INSERT[layer])
    for row in rows:
        params = {k: v for k, v in row.items() if k not in ("geom", "srid")}
        conn.execute(sql, {**params, "imp": import_id, "wkb": shapely.to_wkb(row["geom"]), "srid": row["srid"]})
    conn.execute(text("UPDATE gis_import SET active = false WHERE layer = :l AND active"), {"l": layer})
    conn.execute(text("UPDATE gis_import SET active = true, feature_count = :n WHERE id = :i"),
                 {"n": len(rows), "i": import_id})
    append_event(conn, actor="system", kind="gis.imported", payload={
        "layer": layer, "import_id": import_id, "source": source,
        "source_date": source_date.isoformat(), "features": len(rows),
    })
    return int(import_id)
```

Note for the implementer: confirm `pyogrio.raw.read` in 0.13.0 returns
`(meta, fids, geometry, field_data)` with `meta["crs"]` and `meta["fields"]`; if the signature
differs, adapt `read_features` and record a ruling — the test pins the behaviour.

- [ ] **Step 5:** Install the new requirements on the VM venv
  (`portal/vm.sh run 'cd portal/api && .venv/bin/pip install -q -r requirements-dev.txt'`) and run
  the whole suite. Expected: `55 passed`.

- [ ] **Step 6:** Commit the requirement files, `gis/__init__.py`, `gis/load.py`, the fixtures and
  `make_fixtures.py`, `test_gis_load.py` → `portal: load any GIS file into PostGIS (M2 Task 2)`.

---

## Task 3: Sources and the import command

**Files:**
- Create: `portal/api/portal_api/gis/sources.py`, `portal/api/portal_api/gis/__main__.py`
- Create: `portal/api/tests/test_gis_sources.py`

**Interfaces:**
- Consumes: `read_features`, `load_layer` (Task 2).
- Produces:
  - `fetch_arcgis(url: str, where: str, out_path: str, client: httpx.Client) -> int` — pages
    `/query` (`outFields=*`, `outSR=4326`, `f=geojson`, `orderByFields=OBJECTID`,
    `resultOffset`, `resultRecordCount=1000`) until a page is short and not
    `exceededTransferLimit`; writes one FeatureCollection; returns the count.
  - `GEOLIBRARY_PARCELS`, `E911_ADDRESSES` URL constants (verified 2026-10-15).
  - `geolibrary_source_date(features) -> date` — latest `FMUPDAT` (`M/D/YYYY`).
  - `parcel_rows(features, map_lot_field, location_field=None)`, `address_rows(features)`,
    `district_rows(features, ruleset_districts: list[dict])`,
    `street_rows(inventory: dict, types: dict)`.
  - CLI: `python -m portal_api.gis {parcels|addresses|districts|streets} …` (see Step 4).

District matching: trace code `D1`…`D6` ↔ ruleset `{"code": "D1"}`; trace `SD-<Name>` ↔ ruleset
`{"code": "SD", "name": "<NAME>"}` (case-insensitive). Display name: ruleset name in title case,
then `(D2)` for base districts or ` special district` for SD — e.g. "Neighborhood Residential (D2)",
"Marine special district". Unmatched → `name = None`, `in_ruleset = False`.

Type names: from `types.json`; the implementer reads its structure first and maps code → name
(e.g. `R2` → "Rural Road") without restating any name in code.

- [ ] **Step 1: Write the failing test** — `portal/api/tests/test_gis_sources.py`:

```python
import json
from datetime import date

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
```

- [ ] **Step 2:** Run it. Expected: FAIL — `No module named 'portal_api.gis.sources'`.

- [ ] **Step 3: Implement** `portal/api/portal_api/gis/sources.py`:

```python
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
```

Note: `title()` turns "NEIGHBORHOOD RESIDENTIAL" into "Neighborhood Residential"; check every
ruleset name renders sensibly (e.g. no "Rural Highway" surprises) and record a ruling if a name
needs special handling.

- [ ] **Step 4: Implement the command** `portal/api/portal_api/gis/__main__.py`:

```python
"""Load GIS layers for the property lookup.

  python -m portal_api.gis parcels --geolibrary
  python -m portal_api.gis parcels --file PATH --map-lot-field F [--location-field F] --source TEXT --source-date YYYY-MM-DD
  python -m portal_api.gis addresses --e911
  python -m portal_api.gis districts --file PATH --ruleset PATH --source TEXT --source-date YYYY-MM-DD
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
```

Add to `test_gis_sources.py` (expected names read from the real file, never typed by hand):

```python
def test_type_names_come_from_types_json():
    import json
    from pathlib import Path
    from portal_api.gis.__main__ import _type_names
    path = Path(__file__).resolve().parents[3] / "source/exhibits/cross-sections/types.json"
    raw = json.loads(path.read_text())
    names = _type_names(str(path))
    assert names["R2"] == raw["R2"]["name"].title() and names["S1"] == raw["S1"]["name"].title()
    assert "_meta" not in names
```

On the VM this test needs `source/exhibits/cross-sections/types.json`, which Task 0 syncs; in CI
the checkout has it.

- [ ] **Step 5:** Run the suite. Expected: all pass (`62 passed` with the new test).

- [ ] **Step 6: Load the real layers into the dev database** (the dev VM sets
  `PORTAL_ALLOW_STALE_PARCELS=true` only in its dev servers' environment — see Task 8):

```bash
portal/vm.sh run 'cd portal/api && export PORTAL_DATABASE_URL=postgresql+psycopg://portal:portal@localhost:5433/portal && .venv/bin/python -m alembic upgrade head && .venv/bin/python -m portal_api.gis parcels --geolibrary && .venv/bin/python -m portal_api.gis addresses --e911 && .venv/bin/python -m portal_api.gis districts --file ../../data/street-types/districts.geojson --ruleset ../../build/permit-review/rulesets/adopted-v1.0/districts.json --source-date 2026-06-01 && .venv/bin/python -m portal_api.gis streets --inventory ../../source/exhibits/street-types/inventory.json --types ../../source/exhibits/cross-sections/types.json --source-date 2026-09-14'
```

Expected: `parcels: … 1558 features, source date 2012-04-01`; `addresses: … 1227 features`
(± E911 edits since 2026-10-15); `districts: … 14 features`; `streets: … 214 features`.

- [ ] **Step 7:** Commit `sources.py`, `__main__.py`, `test_gis_sources.py` →
  `portal: GIS sources and the import command (M2 Task 3)`.

---

## Task 4: Property search, point lookup and facts

**Files:**
- Create: `portal/api/portal_api/property.py`, `portal/api/portal_api/routes/property.py`
- Create: `portal/api/tests/test_property.py`
- Modify: `portal/api/portal_api/main.py` (include the router)

**Interfaces:**
- Consumes: the layers (Tasks 1–3), `db.transaction`.
- Produces HTTP (public, read-only):
  - `GET /api/property/search?q=` (2–100 chars) → `200 [{"label", "lon", "lat", "parcel_id": int|null}]` (≤ 8)
  - `GET /api/property/at?lon=&lat=` → `200 {"parcel_id"}` or `404 {"detail": "no_parcel_here"}`
  - `GET /api/property/{parcel_id}` → `200 Facts` or `404 {"detail": "no_such_parcel"}`
  - `GET /api/property/districts` → `200 [{"code", "name"}]` (in-ruleset only; does **not** need parcels)
  - search, at and facts → `503 {"detail": "parcel_data_unavailable"}` when there is no active
    parcel import, or it is older than `parcel_max_age_days` and `allow_stale_parcels` is false.
- `Facts` JSON:

```json
{
  "parcel_id": 12, "map_lot": "004-036", "location": "SHEEPSCOT ROAD",
  "acres": 2.1,
  "districts": [{"code": "D2", "name": "Neighborhood Residential (D2)", "in_ruleset": true, "share": 0.75}],
  "streets": [{"name": "Sheepscot Road", "type": "R2", "type_name": "Rural Road",
               "ownership": "Town Way", "frontage_ft": 160}],
  "on_state_highway": false,
  "as_of": {"parcels": "2012-04-01", "parcels_source": "Maine GeoLibrary, …",
            "districts_source": "Traced from the District Map (Exhibit 1.1); approximate"},
  "geometry": {"type": "MultiPolygon", "coordinates": []}
}
```

Rules: `acres` = map area / 4046.8564224, 2 decimals. `districts` = every district covering ≥ 1 %
of the lot, by share, largest first. `streets` = segments within 20 m of the lot. **Frontage is
how far the street runs alongside the lot**, not the length of lot line near it (which would
count the side lot lines too): take the part of the lot boundary within 20 m of the street, locate
each of its vertices along the street (`ST_LineLocatePoint`), and measure the street between the
first and last. Summed per street name+Type, kept if ≥ 3 m, `frontage_ft` = metres × 3.28084
rounded to the nearest 5 ft. (Inventory segments are single lines; the stored MultiLineString's
first part is the line.) `on_state_highway` = any street with `ownership == "State Highway"`.
`geometry` in EPSG:4326.

Search: case-insensitive; literal (escape `\`, `%`, `_`); matches where the label contains the
query, plus trigram-similar labels (`similarity > 0.3`); ordered starts-with first, then
similarity, then label. A query that looks like a map/lot (`^\d{1,3}\D+\d{1,3}`, e.g. `4-36`,
`4/36`, `004 036`) also matches parcels whose `map_lot` starts with the zero-padded `004-036`,
returned with label `Map 4, Lot 36` and the parcel's centroid.

- [ ] **Step 1: Write the failing tests** — `portal/api/tests/test_property.py` (fixture layers
  loaded through the real loader; `settings.allow_stale_parcels = True` unless the test is about
  the guard):

```python
from datetime import date

import pytest
from fastapi.testclient import TestClient

from portal_api.gis.load import load_layer, read_features
from portal_api.gis.sources import address_rows, district_rows, parcel_rows, street_rows
from portal_api.main import create_app
from tests.test_gis_load import FIX

RULESET = [{"code": "D1", "name": "RURAL"}, {"code": "D2", "name": "NEIGHBORHOOD RESIDENTIAL"}]


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


def _south_edge_utm(conn):
    """A street line 5 m south of the three test lots, in EPSG:26919."""
    from sqlalchemy import text
    wkt = conn.execute(text(
        "SELECT ST_AsGeoJSON(ST_Translate(ST_Transform(ST_SetSRID(ST_MakeLine("
        "ST_MakePoint(-69.581, 44.040), ST_MakePoint(-69.573, 44.040)), 4326), 26919), 0, -5))"
    )).scalar()
    import json
    return json.loads(wkt)["coordinates"]


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


def test_facts_never_name_a_district_outside_the_ruleset(open_client):
    f = open_client.get(f"/api/property/{_id(open_client, '4-38')}").json()
    civic = next(d for d in f["districts"] if d["code"] == "SD-Civic")
    assert civic["in_ruleset"] is False and civic["name"] is None


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
        {"code": "D1", "name": "Rural (D1)"}, {"code": "D2", "name": "Neighborhood Residential (D2)"}]


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
```

(The fixture lots are ~0.002° × 0.002° ≈ 160 m × 222 m ≈ 8.8 acres; adjust the expected ranges if
the generated fixture differs, and record a ruling — the point is that each assertion is
derivable from the fixture, not tuned to the output.)

- [ ] **Step 2:** Run it. Expected: FAIL — 404s on `/api/property/*`.

- [ ] **Step 3: Implement** `portal/api/portal_api/property.py`:

```python
"""Property facts from the active GIS imports. Read-only; nothing is logged."""

import re
from datetime import date, timedelta

from sqlalchemy import Connection, text

_FT_PER_M = 3.28084
_SQ_M_PER_ACRE = 4046.8564224


class ParcelsUnavailable(Exception):
    """No usable parcel import: none loaded, or too old for applicants."""


def active_import(conn: Connection, layer: str):
    return conn.execute(text(
        "SELECT id, source, source_date FROM gis_import WHERE layer = :l AND active"
    ), {"l": layer}).one_or_none()


def parcels_import(conn: Connection, settings):
    imp = active_import(conn, "parcels")
    if imp is None:
        raise ParcelsUnavailable("none loaded")
    too_old = date.today() - imp.source_date > timedelta(days=settings.parcel_max_age_days)
    if too_old and not settings.allow_stale_parcels:
        raise ParcelsUnavailable("out of date")
    return imp


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_MAP_LOT = re.compile(r"^\s*(\d{1,3})\D+(\d{1,3})\s*$")


def search(conn: Connection, q: str, parcels_import_id: int) -> list[dict]:
    hits: list[dict] = []
    m = _MAP_LOT.match(q)
    if m:
        prefix = f"{int(m.group(1)):03d}-{int(m.group(2)):03d}"
        for r in conn.execute(text(
            "SELECT id, map_lot, ST_X(c) AS lon, ST_Y(c) AS lat FROM ("
            " SELECT id, map_lot, ST_Transform(ST_PointOnSurface(geom), 4326) AS c FROM parcel"
            " WHERE import_id = :pi AND map_lot LIKE :p ESCAPE '\\') s ORDER BY map_lot LIMIT 8"
        ), {"pi": parcels_import_id, "p": _like_escape(prefix) + "%"}):
            parts = r.map_lot.split("-")
            hits.append({"label": f"Map {int(parts[0])}, Lot {'-'.join(p.lstrip('0') or '0' for p in parts[1:])}",
                         "lon": r.lon, "lat": r.lat, "parcel_id": r.id})
    addr = active_import(conn, "addresses")
    if addr is not None:
        for r in conn.execute(text(
            "SELECT a.label, ST_X(ST_Transform(a.geom, 4326)) AS lon, ST_Y(ST_Transform(a.geom, 4326)) AS lat,"
            " (SELECT p.id FROM parcel p WHERE p.import_id = :pi AND ST_Contains(p.geom, a.geom) LIMIT 1) AS parcel_id"
            " FROM address_point a WHERE a.import_id = :ai"
            " AND (lower(a.label) LIKE '%' || lower(:q) || '%' ESCAPE '\\' OR similarity(lower(a.label), lower(:raw)) > 0.3)"
            " ORDER BY (lower(a.label) LIKE lower(:q) || '%' ESCAPE '\\') DESC,"
            " similarity(lower(a.label), lower(:raw)) DESC, a.label LIMIT 8"
        ), {"pi": parcels_import_id, "ai": addr.id, "q": _like_escape(q.strip()), "raw": q.strip()}):
            hits.append({"label": r.label, "lon": r.lon, "lat": r.lat, "parcel_id": r.parcel_id})
    return hits[:8]


def parcel_at(conn: Connection, lon: float, lat: float, parcels_import_id: int) -> int | None:
    return conn.execute(text(
        "SELECT id FROM parcel WHERE import_id = :pi AND ST_Contains(geom,"
        " ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 26919)) LIMIT 1"
    ), {"pi": parcels_import_id, "lon": lon, "lat": lat}).scalar()


def facts(conn: Connection, parcel_id: int, parcels_imp) -> dict | None:
    p = conn.execute(text(
        "SELECT id, map_lot, location, ST_Area(geom) AS area, ST_AsGeoJSON(ST_Transform(geom, 4326), 6) AS gj"
        " FROM parcel WHERE id = :id AND import_id = :pi"
    ), {"id": parcel_id, "pi": parcels_imp.id}).one_or_none()
    if p is None:
        return None
    dist_imp = active_import(conn, "districts")
    districts = [] if dist_imp is None else [dict(r._mapping) for r in conn.execute(text(
        "SELECT d.code, d.name, d.in_ruleset,"
        " round((ST_Area(ST_Intersection(d.geom, p.geom)) / ST_Area(p.geom))::numeric, 3)::float AS share"
        " FROM district_area d, parcel p WHERE p.id = :id AND d.import_id = :di AND ST_Intersects(d.geom, p.geom)"
        " AND ST_Area(ST_Intersection(d.geom, p.geom)) / ST_Area(p.geom) >= 0.01 ORDER BY share DESC"
    ), {"id": parcel_id, "di": dist_imp.id})]
    st_imp = active_import(conn, "streets")
    streets = [] if st_imp is None else [{
        "name": r.name, "type": r.type, "type_name": r.type_name, "ownership": r.ownership,
        "frontage_ft": int(5 * round(r.metres * _FT_PER_M / 5)),
    } for r in conn.execute(text(
        # Per segment: the stretch of street alongside the lot = the span, along the street,
        # of the lot-boundary vertices within 20 m of it.
        "WITH seg AS ("
        " SELECT s.name, s.type, s.type_name, s.ownership,"
        "  (max(ST_LineLocatePoint(l.line, d.geom)) - min(ST_LineLocatePoint(l.line, d.geom))) * ST_Length(l.line) AS metres"
        " FROM street_segment s"
        " JOIN parcel p ON p.id = :id"
        " CROSS JOIN LATERAL (SELECT ST_GeometryN(s.geom, 1) AS line) l"
        " CROSS JOIN LATERAL ST_DumpPoints(ST_Intersection(ST_Boundary(p.geom), ST_Buffer(s.geom, 20))) d"
        " WHERE s.import_id = :si AND ST_DWithin(s.geom, p.geom, 20)"
        " GROUP BY s.id, s.name, s.type, s.type_name, s.ownership, l.line)"
        " SELECT name, type, max(type_name) AS type_name, max(ownership) AS ownership, sum(metres) AS metres"
        " FROM seg GROUP BY name, type HAVING sum(metres) >= 3 ORDER BY metres DESC"
    ), {"id": parcel_id, "si": st_imp.id})]
    import json
    return {
        "parcel_id": p.id, "map_lot": p.map_lot, "location": p.location,
        "acres": round(p.area / _SQ_M_PER_ACRE, 2),
        "districts": districts, "streets": streets,
        "on_state_highway": any(s["ownership"] == "State Highway" for s in streets),
        "as_of": {"parcels": parcels_imp.source_date.isoformat(), "parcels_source": parcels_imp.source,
                  "districts_source": dist_imp.source if dist_imp else None},
        "geometry": json.loads(p.gj),
    }


def adopted_districts(conn: Connection) -> list[dict]:
    imp = active_import(conn, "districts")
    if imp is None:
        return []
    return [dict(r._mapping) for r in conn.execute(text(
        "SELECT DISTINCT code, name FROM district_area WHERE import_id = :i AND in_ruleset ORDER BY code"
    ), {"i": imp.id})]
```

`portal/api/portal_api/routes/property.py`:

```python
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Connection

from portal_api import property as prop
from portal_api.db import transaction

router = APIRouter()
_UNAVAILABLE = JSONResponse({"detail": "parcel_data_unavailable"}, status_code=503)


def _parcels(conn, request):
    try:
        return prop.parcels_import(conn, request.app.state.settings)
    except prop.ParcelsUnavailable:
        return None


@router.get("/api/property/search")
def search(request: Request, q: str = Query(min_length=2, max_length=100), conn: Connection = transaction):
    imp = _parcels(conn, request)
    return _UNAVAILABLE if imp is None else prop.search(conn, q, imp.id)


@router.get("/api/property/at")
def at(request: Request, lon: float = Query(ge=-180, le=180), lat: float = Query(ge=-90, le=90),
       conn: Connection = transaction):
    imp = _parcels(conn, request)
    if imp is None:
        return _UNAVAILABLE
    pid = prop.parcel_at(conn, lon, lat, imp.id)
    return {"parcel_id": pid} if pid else JSONResponse({"detail": "no_parcel_here"}, status_code=404)


@router.get("/api/property/districts")
def districts(conn: Connection = transaction):
    return prop.adopted_districts(conn)


@router.get("/api/property/{parcel_id}")
def facts(parcel_id: int, request: Request, conn: Connection = transaction):
    imp = _parcels(conn, request)
    if imp is None:
        return _UNAVAILABLE
    f = prop.facts(conn, parcel_id, imp)
    return f if f else JSONResponse({"detail": "no_such_parcel"}, status_code=404)
```

(`_UNAVAILABLE` is a shared response object; if Starlette refuses to send one instance twice,
build it per call and record a ruling.) Register with `app.include_router(property_routes.router)`.

- [ ] **Step 4:** Run the suite. Expected: all pass.

- [ ] **Step 5: Real-data spot check** on the dev database (loaded in Task 3 Step 6), through the
  running dev API with `PORTAL_ALLOW_STALE_PARCELS=true`:
  `curl 'http://127.0.0.1:8000/api/property/search?q=461%20Sheepscot'` returns the address with a
  parcel id; its facts name a district from the ruleset, an area in acres, and Sheepscot Road with
  its Type. Record what came back in the ledger.

- [ ] **Step 6:** Commit → `portal: property search, point lookup and facts (M2 Task 4)`.

---

## Task 5: Parcel vector tiles

**Files:**
- Modify: `portal/api/portal_api/routes/property.py`
- Create: `portal/api/tests/test_tiles.py`

**Interfaces:** `GET /api/tiles/parcels/{z}/{x}/{y}.pbf` → `200 application/vnd.mapbox-vector-tile`
(layer `parcels`, properties `id`, `map_lot`), `204` below zoom 12 or for an empty tile, `503` under
the same guard as Task 4. `Cache-Control: public, max-age=3600`.

- [ ] **Step 1: Write the failing test** — `portal/api/tests/test_tiles.py`:

```python
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
```

- [ ] **Step 2:** Run it. Expected: FAIL (404).

- [ ] **Step 3: Implement** — add to `routes/property.py`:

```python
from fastapi import Path, Response
from sqlalchemy import text


@router.get("/api/tiles/parcels/{z}/{x}/{y}.pbf")
def parcel_tile(request: Request, z: int = Path(ge=0, le=22), x: int = Path(ge=0), y: int = Path(ge=0),
                conn: Connection = transaction):
    imp = _parcels(conn, request)
    if imp is None:
        return _UNAVAILABLE
    if z < 12 or x >= 2 ** z or y >= 2 ** z:
        return Response(status_code=204)
    tile = conn.execute(text(
        "WITH b AS (SELECT ST_TileEnvelope(:z, :x, :y) AS env),"
        " t AS (SELECT p.id, p.map_lot, ST_AsMVTGeom(ST_Transform(p.geom, 3857), b.env) AS geom"
        "  FROM parcel p, b WHERE p.import_id = :i AND p.geom && ST_Transform(b.env, 26919))"
        " SELECT ST_AsMVT(t.*, 'parcels') FROM t WHERE t.geom IS NOT NULL"
    ), {"z": z, "x": x, "y": y, "i": imp.id}).scalar()
    if not tile:
        return Response(status_code=204)
    return Response(bytes(tile), media_type="application/vnd.mapbox-vector-tile",
                    headers={"Cache-Control": "public, max-age=3600"})
```

- [ ] **Step 4:** Run the suite. Expected: all pass.
- [ ] **Step 5:** Commit → `portal: parcel vector tiles (M2 Task 5)`.

---

## Task 6: The self-hosted basemap

**Files:**
- Create: `portal/basemap/extract.py`, `portal/basemap/requirements.txt` (`pmtiles==3.8.1`, `httpx==0.28.1`), `portal/basemap/README.md`
- Modify: `.gitignore` (add `portal/web/public/basemap/`)

**Interfaces:** writes `portal/web/public/basemap/newcastle.pmtiles`,
`portal/web/public/basemap/fonts/<fontstack>/<range>.pbf`,
`portal/web/public/basemap/sprites/light{.json,.png,@2x.json,@2x.png}`. Vite serves them in dev;
the web image copies them into `/srv` (they exist on the VM at build time).

- [ ] **Step 1: Write `extract.py`.** It:
  1. picks the most recent `https://build.protomaps.com/YYYYMMDD.pmtiles` that answers a HEAD
     (today, then up to 7 days back);
  2. reads it by HTTP range requests (`httpx`, `Range: bytes=a-b`) through
     `pmtiles.reader.Reader(get_bytes)`;
  3. copies every tile for zooms 0–15 inside the bounding box
     `(-69.66, 43.96, -69.49, 44.13)` (Newcastle, measured from
     `data/street-types/raw/town_boundary.geojson` as −69.6378, 43.9798, −69.5140, 44.1156, plus a
     margin) into a new archive with `pmtiles.writer.Writer`, in ascending tile-id order, with
     the source header's tile type and compression, `min_zoom 0`, `max_zoom 15`, the bounding box,
     centre (−69.576, 44.048, z12), and the source metadata plus
     `"attribution": "© OpenStreetMap contributors"`;
  4. downloads fonts `Noto Sans Regular`, `Noto Sans Medium`, `Noto Sans Italic`, ranges
     `0-255`, `256-511`, `8192-8447`, and sprites `light`, `light@2x` (`.json`, `.png`) from
     `https://raw.githubusercontent.com/protomaps/basemaps-assets/main/` (`fonts/…`,
     `sprites/v4/…`), failing loudly on any non-200;
  5. prints the tile count and archive size.
  Before writing, check the installed `pmtiles` 3.8.1 API (`Reader`, `Writer`, `zxy_to_tileid`,
  header keys) and the sprites path; record any difference as a ruling.

- [ ] **Step 2: Run it on the VM:**

```bash
portal/vm.sh run 'cd portal && api/.venv/bin/pip install -q -r basemap/requirements.txt && api/.venv/bin/python basemap/extract.py'
```

Expected: a few thousand tiles, an archive of a few MB, 9 font files, 4 sprite files. The files
stay on the VM (gitignored); `vm.sh` already excludes nothing under `public/`, so add
`--exclude 'web/public/basemap/'` to `vm.sh`'s rsync so a sync from the Mac does not delete them.

- [ ] **Step 3:** Write `portal/basemap/README.md` (what it is, how to refresh, licence: map data
  © OpenStreetMap contributors, ODbL; fonts OFL; Protomaps basemap BSD/CC0 — check the
  basemaps-assets licence file and quote its name). Commit `extract.py`, `requirements.txt`,
  `README.md`, `.gitignore`, `vm.sh` → `portal: self-hosted basemap extract (M2 Task 6)`.

---

## Task 7: The "Where is it?" page

**Files:**
- Modify: `portal/web/package.json` (+ `maplibre-gl 6.14.0`, `pmtiles 4.5.0`, `@protomaps/basemaps 5.7.2`), `package-lock.json`
- Create: `portal/web/src/components/ParcelMap.tsx`, `portal/web/src/property.ts`, `portal/web/src/pages/Where.tsx`, `portal/web/src/pages/Where.test.tsx`
- Modify: `portal/web/src/api.ts` (property calls), `portal/web/src/App.tsx` (route `/where`), `portal/web/src/pages/Home.tsx` (start link)

**Interfaces:**
- `api.ts` adds: `type Facts` (Task 4 shape); `searchProperty(q): Promise<Hit[] | "unavailable">`;
  `parcelAt(lon, lat): Promise<number | null | "unavailable">`;
  `getProperty(id): Promise<Facts | null | "unavailable">`; `getDistricts(): Promise<{code,name}[]>`.
- `ParcelMap` props: `{ selected: Facts["geometry"] | null; focus: {lon: number; lat: number} | null; onPick(lon: number, lat: number): void }`.
- `property.ts`: `type ChosenProperty = { source: "lookup" | "manual"; parcel_id: number | null; map_lot: string; district_code: string | null; disputed: boolean; note: string; as_of: string | null }`; `saveProperty(p)`, `loadProperty()` in `sessionStorage` under `portal.property`, wrapped in try/catch. (Persisting it with an application is M4.)

Page behaviour (`/where`, public):
1. Heading "Where is your project?"; a search field ("Street address, or map and lot"); results
   as a list of buttons; the map below.
2. Picking a result with a lot, or tapping a lot on the map, shows **"Here's what we found"**:
   - "Map 4, Lot 36" (from `map_lot`), the street address location;
   - District: the name, or for several "This lot is in more than one district: … (most of it),
     …"; any `in_ruleset: false` area → "Part of this lot is in an area staff will confirm.";
   - "About 2.1 acres (measured from the map)"; for each street "About 160 ft along Sheepscot
     Road, a Rural Road";
   - a small print line: "Lot lines from the Town's tax maps as of April 1, 2012. District from a
     tracing of the District Map. The Code Enforcement Officer confirms all of this when you apply."
     (date from `as_of.parcels`, written out);
   - buttons **"Yes, this is my property"** and **"This doesn't look right"** (the latter opens a
     text area "What looks wrong?" and a "Save" button; saved with `disputed: true`).
3. A result with no lot → "We found that address but not the lot it's on. Tap your lot on the map."
4. A tap on nothing → "There's no lot at that spot. Try tapping inside your lot's lines."
5. `unavailable` from any call, or the link "I can't find my property" → **manual entry**:
   "Map and lot" text field (help: "It's on your property tax bill"), "District" select from
   `getDistricts()` plus "I'm not sure", "Save" → `source: "manual"`.
6. After saving: "Saved. The next steps are coming soon." (M3 takes over from here.)

- [ ] **Step 1: Install** — `portal/vm.sh run 'cd portal/web && npm install maplibre-gl@6.14.0 pmtiles@4.5.0 @protomaps/basemaps@5.7.2 --save-exact'`, then copy `package.json` and `package-lock.json` back to the Mac with `rsync -az ben@192.168.1.6:newcastle-czc/portal/web/{package.json,package-lock.json} portal/web/`. Expected: no peer-dependency errors (stop and report if any).

- [ ] **Step 2: Write the failing tests** — `portal/web/src/pages/Where.test.tsx`. `ParcelMap` is
  replaced by a stub (jsdom has no WebGL) that renders a button "tap the map" calling
  `onPick(-69.579, 44.041)`. Tests (each mocks the `api` functions with `vi.spyOn`):
  - "shows the lot, districts, size, street and the map's date after picking a search result"
    (two districts → both named, larger first; asserts "April 1, 2012" and "approximate"/"measured
    from the map" wording appears);
  - "says when part of a lot is in an area staff will confirm" (`in_ruleset: false`);
  - "asks for a tap when the address has no lot";
  - "finds the lot from a tap on the map";
  - "says so when nothing is at the tapped spot";
  - "saves the property when the person confirms it" (asserts `loadProperty()` result);
  - "records what looks wrong without blocking" (`disputed: true`, note text saved);
  - "falls back to entering it by hand when lookup is unavailable" (search → `"unavailable"`;
    manual form appears; save → `source: "manual"`, `parcel_id: null`);
  - "offers manual entry when the person can't find their property".

  Write each with concrete mocked `Facts` objects; follow the M1 tests' style (`MemoryRouter`,
  `userEvent`, `findBy…`).

- [ ] **Step 3:** Run — Expected: FAIL (`Where` not found).

- [ ] **Step 4: Implement** `api.ts` additions, `property.ts`, `ParcelMap.tsx`, `Where.tsx`, the
  route and the Home link. `ParcelMap`:

```tsx
import { layers, namedFlavor } from "@protomaps/basemaps";
import maplibregl, { type Map as MlMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";
import { useEffect, useRef } from "react";
import type { Facts } from "../api";

let protocolAdded = false;
const NEWCASTLE: [number, number, number, number] = [-69.66, 43.96, -69.49, 44.13];

type Props = {
  selected: Facts["geometry"] | null;
  focus: { lon: number; lat: number } | null;
  onPick: (lon: number, lat: number) => void;
};

export default function ParcelMap({ selected, focus, onPick }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<MlMap | null>(null);
  const pick = useRef(onPick);
  pick.current = onPick;

  useEffect(() => {
    if (!protocolAdded) {
      maplibregl.addProtocol("pmtiles", new Protocol().tile);
      protocolAdded = true;
    }
    const origin = window.location.origin;
    const m = new maplibregl.Map({
      container: el.current!,
      maxBounds: NEWCASTLE,
      center: [-69.576, 44.048],
      zoom: 12,
      style: {
        version: 8,
        glyphs: `${origin}/basemap/fonts/{fontstack}/{range}.pbf`,
        sprite: `${origin}/basemap/sprites/light`,
        sources: {
          protomaps: { type: "vector", url: `pmtiles://${origin}/basemap/newcastle.pmtiles`,
                       attribution: "© OpenStreetMap contributors" },
          parcels: { type: "vector", tiles: [`${origin}/api/tiles/parcels/{z}/{x}/{y}.pbf`], minzoom: 12, maxzoom: 18 },
          selected: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        },
        layers: [
          ...layers("protomaps", namedFlavor("light"), { lang: "en" }),
          { id: "parcel-fill", type: "fill", source: "parcels", "source-layer": "parcels", paint: { "fill-color": "#000", "fill-opacity": 0 } },
          { id: "parcel-line", type: "line", source: "parcels", "source-layer": "parcels", paint: { "line-color": "#6b5b3e", "line-width": 0.8 } },
          { id: "selected-line", type: "line", source: "selected", paint: { "line-color": "#c2410c", "line-width": 3 } },
        ],
      },
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }));
    m.on("click", (e) => pick.current(e.lngLat.lng, e.lngLat.lat));
    map.current = m;
    return () => m.remove();
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const apply = () => {
      const src = m.getSource("selected") as maplibregl.GeoJSONSource | undefined;
      src?.setData(selected ? { type: "Feature", properties: {}, geometry: selected } : { type: "FeatureCollection", features: [] });
      if (selected) {
        const b = new maplibregl.LngLatBounds();
        for (const poly of selected.coordinates) for (const ring of poly) for (const c of ring) b.extend(c as [number, number]);
        m.fitBounds(b, { padding: 40, maxZoom: 18 });
      }
    };
    if (m.isStyleLoaded()) apply(); else m.once("load", apply);
  }, [selected]);

  useEffect(() => {
    if (focus && map.current) map.current.flyTo({ center: [focus.lon, focus.lat], zoom: 17 });
  }, [focus]);

  return <div ref={el} className="h-80 w-full rounded-lg sm:h-96" role="region" aria-label="Map of Newcastle" />;
}
```

  `Facts["geometry"]` is typed `{ type: "MultiPolygon"; coordinates: number[][][][] }`.
  Write `Where.tsx` to the behaviour above with HeroUI components (`SearchField` or `TextField`,
  `Button`, `Card`, `Select`/`ListBox`, `TextArea`), plain words throughout; read the HeroUI 3.2.6
  exports before using a component not used in M1. Write dates out ("April 1, 2012").

- [ ] **Step 5:** Run tests and `npm run build`. Expected: all pass; build clean. Note the bundle
  size (MapLibre adds ~800 kB); acceptable for a page used once per application.

- [ ] **Step 6:** Commit → `portal: the "Where is it?" page with a self-hosted map (M2 Task 7)`.

---

## Task 8: Real data in the dev and LAN stacks, and a hands-on check

**Files:**
- Modify: `portal/deploy/compose.lan.yml` (API env `PORTAL_ALLOW_STALE_PARCELS: "true"` — the LAN
  stack is development, per the chair; the base `compose.yml` never sets it)
- Modify: `portal/README.md` (loading GIS data; the stale guard), `portal/deploy/README.md`
- Modify: `plans/2026-10-14-applicant-portal-roadmap.md` (M2 status; open item: current parcels from the assessor/CAI)

- [ ] **Step 1:** Restart the dev API with `PORTAL_ALLOW_STALE_PARCELS=true` (dev servers only) and
  rebuild the LAN stack (`portal/vm.sh lan`). Load the four layers into the LAN database:

```bash
ssh ben@192.168.1.6 'cd newcastle-czc/portal/deploy && sudo docker compose -f compose.yml -f compose.lan.yml --env-file .env run --rm -v $HOME/newcastle-czc:/repo:ro api sh -c "python -m portal_api.gis parcels --geolibrary && python -m portal_api.gis addresses --e911 && python -m portal_api.gis districts --file /repo/data/street-types/districts.geojson --ruleset /repo/build/permit-review/rulesets/adopted-v1.0/districts.json --source-date 2026-06-01 && python -m portal_api.gis streets --inventory /repo/source/exhibits/street-types/inventory.json --types /repo/source/exhibits/cross-sections/types.json --source-date 2026-09-14"'
```

- [ ] **Step 2: Hands-on (browser pane, LAN URL `https://192.168.1.6/where`):** search "461
  Sheepscot", confirm the lot outline, district, acres, street and the 2012 date; tap a
  neighbouring lot; tap the river ("no lot at that spot"); open "I can't find my property" and save
  a manual entry; check at 375 px; check the browser's network log shows **no request to any host
  but 192.168.1.6**.
- [ ] **Step 3: The guard in production shape:** with `PORTAL_ALLOW_STALE_PARCELS` unset (the
  base `compose.yml` alone, bound to 127.0.0.1 as in M1's trial), `/api/property/search?q=461`
  returns 503 and the page shows manual entry.
- [ ] **Step 4:** Update the READMEs and roadmap; commit →
  `portal: M2 data loaded on the VM; docs (M2 Task 8)`.

---

## Milestone 2 done when

- API and web suites green on the VM; CI green on the PR.
- On the LAN stack: address search, map tap, facts with dates and approximation notes, "doesn't
  look right", manual fallback — all working, no third-party requests.
- With the production default, 2012 parcels are refused and the page falls back to manual entry.
- One fresh-context review of the whole M2 branch, findings ruled on.
- Open for the chair: the current parcel export from the assessor/CAI (then
  `python -m portal_api.gis parcels --file … --source "…" --source-date …`), and whether SD-Civic
  belongs in the adopted districts (it is on the trace, not in v1.0).
