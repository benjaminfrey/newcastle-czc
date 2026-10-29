"""The applicant's details, saved once on the account (projects brief §5.1).

Revision ID: 0006
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE applicant ADD COLUMN mailing_address text")


def downgrade() -> None:
    op.execute("ALTER TABLE applicant DROP COLUMN mailing_address")
