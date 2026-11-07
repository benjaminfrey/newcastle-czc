"""The packet as sent (guided plan 6): what the Town reads, kept as it was at sending, so later
changes before staff lock the project never alter it. Sending again replaces it.

Revision ID: 0011
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE guide_packet (
        project_id uuid PRIMARY KEY REFERENCES project(id) ON DELETE CASCADE,
        sent_at timestamptz NOT NULL,
        body jsonb NOT NULL
    );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE guide_packet;")
