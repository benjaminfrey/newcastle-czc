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
