"""The guide's Change link (guided plan 3): a `revisit` action takes one answer out of force so
its turn is asked again. Like Back, it is a new row, never an edit.

Revision ID: 0010
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE guide_action DROP CONSTRAINT guide_action_kind_check;
    ALTER TABLE guide_action ADD CONSTRAINT guide_action_kind_check
        CHECK (kind IN ('answer', 'back', 'restart', 'revisit'));
    """)


def downgrade() -> None:
    # The record is append-only, so a downgrade with Change rows on it refuses rather than delete.
    op.execute("""
    DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM guide_action WHERE kind = 'revisit') THEN
            RAISE EXCEPTION 'guide_action holds revisit rows; they are part of the record';
        END IF;
    END $$;
    ALTER TABLE guide_action DROP CONSTRAINT guide_action_kind_check;
    ALTER TABLE guide_action ADD CONSTRAINT guide_action_kind_check
        CHECK (kind IN ('answer', 'back', 'restart'));
    """)
