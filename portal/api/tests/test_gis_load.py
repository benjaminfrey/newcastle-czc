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
