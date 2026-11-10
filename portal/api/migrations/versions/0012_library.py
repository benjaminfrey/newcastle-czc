"""The explanation library's records (design 2, §7–8): the chair's and the CEO's decisions on the
review page, kept as pending until the builder writes them into the library's files, and the pulls,
which take an entry down at once.

Revision ID: 0012
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE library_decision (
            id          bigserial PRIMARY KEY,
            entry_id    text NOT NULL,
            version     int NOT NULL,
            action      text NOT NULL CHECK (action IN ('approve', 'edit', 'send_back')),
            body        jsonb,
            note        text,
            decided_by  uuid NOT NULL REFERENCES applicant(id) ON DELETE CASCADE,
            decided_at  timestamptz NOT NULL DEFAULT now(),
            exported_at timestamptz
        );
        CREATE TABLE library_pull (
            entry_id    text PRIMARY KEY,
            version     int NOT NULL,
            why         text NOT NULL,
            pulled_by   uuid NOT NULL REFERENCES applicant(id) ON DELETE CASCADE,
            pulled_at   timestamptz NOT NULL DEFAULT now(),
            exported_at timestamptz
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE library_pull; DROP TABLE library_decision;")
