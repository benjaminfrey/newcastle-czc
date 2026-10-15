"""PostGIS, for the property lookup in M2.

Revision ID: 0001
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    # Deliberately a no-op. The PostGIS image installs postgis_topology and
    # postgis_tiger_geocoder on top of postgis, and dropping postgis with CASCADE
    # would also drop every geometry column. Extensions outlive this migration.
    pass
