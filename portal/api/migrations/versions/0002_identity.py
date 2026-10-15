"""Applicants, sign-in tokens, sessions, and the append-only event log.

Revision ID: 0002
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE applicant (
        id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        email       text NOT NULL UNIQUE CHECK (email = lower(btrim(email))),
        name        text,
        phone       text,
        role        text NOT NULL DEFAULT 'applicant'
                    CHECK (role IN ('applicant', 'staff', 'admin')),
        created_at  timestamptz NOT NULL DEFAULT now()
    );

    CREATE TABLE signin_token (
        id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        applicant_id  uuid NOT NULL REFERENCES applicant(id),
        token_hash    text NOT NULL UNIQUE,
        requested_ip  text,
        created_at    timestamptz NOT NULL DEFAULT now(),
        expires_at    timestamptz NOT NULL,
        used_at       timestamptz
    );
    CREATE INDEX signin_token_applicant_created ON signin_token (applicant_id, created_at);
    CREATE INDEX signin_token_ip_created ON signin_token (requested_ip, created_at);

    CREATE TABLE session (
        id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        applicant_id  uuid NOT NULL REFERENCES applicant(id),
        token_hash    text NOT NULL UNIQUE,
        created_at    timestamptz NOT NULL DEFAULT now(),
        expires_at    timestamptz NOT NULL,
        revoked_at    timestamptz
    );

    -- `at` is the exact ISO string that was hashed, so verification never
    -- depends on how the database round-trips a timestamp.
    CREATE TABLE event (
        seq           bigserial PRIMARY KEY,
        id            uuid NOT NULL UNIQUE,
        at            text NOT NULL,
        actor         text NOT NULL,
        kind          text NOT NULL,
        payload_json  text NOT NULL,
        prev_hash     char(64) NOT NULL,
        hash          char(64) NOT NULL UNIQUE
    );

    CREATE FUNCTION event_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'event is append-only';
    END $$;
    CREATE TRIGGER event_append_only BEFORE UPDATE OR DELETE ON event
        FOR EACH ROW EXECUTE FUNCTION event_append_only();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE event;
    DROP FUNCTION event_append_only();
    DROP TABLE session;
    DROP TABLE signin_token;
    DROP TABLE applicant;
    """)
