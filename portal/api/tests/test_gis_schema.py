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
