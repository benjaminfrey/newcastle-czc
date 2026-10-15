"""Sign-in tokens carry the email, not an applicant: the applicant record is
created only when a link is used. A token is redeemable only once its email
was actually handed to the relay (sent_at). Outstanding tokens are dropped.

Revision ID: 0003
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    DELETE FROM signin_token;
    DROP INDEX signin_token_applicant_created;
    ALTER TABLE signin_token DROP COLUMN applicant_id;
    ALTER TABLE signin_token ADD COLUMN email text NOT NULL CHECK (email = lower(btrim(email)));
    ALTER TABLE signin_token ADD COLUMN sent_at timestamptz;
    CREATE INDEX signin_token_email_created ON signin_token (email, created_at);
    CREATE INDEX signin_token_created ON signin_token (created_at);
    """)


def downgrade() -> None:
    op.execute("""
    DELETE FROM signin_token;
    DROP INDEX signin_token_created;
    DROP INDEX signin_token_email_created;
    ALTER TABLE signin_token DROP COLUMN sent_at;
    ALTER TABLE signin_token DROP COLUMN email;
    ALTER TABLE signin_token ADD COLUMN applicant_id uuid NOT NULL REFERENCES applicant(id);
    CREATE INDEX signin_token_applicant_created ON signin_token (applicant_id, created_at);
    """)
