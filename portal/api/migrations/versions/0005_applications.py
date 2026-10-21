"""Applications: the draft, its property snapshot, repeat items, answers, notes, attachments.

Answers and notes are insert-only: a change appends a row, so the history of every
answer is kept (spec §5, "edits keep the previous value").

Revision ID: 0005
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE application (
        id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        applicant_id  uuid NOT NULL REFERENCES applicant(id) ON DELETE CASCADE,
        form_key      text NOT NULL,
        form_version  int NOT NULL,
        ruleset_key   text NOT NULL,
        status        text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft')),
        revision      int NOT NULL DEFAULT 0,
        created_at    timestamptz NOT NULL DEFAULT now(),
        updated_at    timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX application_applicant ON application (applicant_id, updated_at DESC);

    CREATE TABLE property_snapshot (
        application_id  uuid PRIMARY KEY REFERENCES application(id) ON DELETE CASCADE,
        source          text NOT NULL CHECK (source IN ('lookup', 'manual')),
        parcel_id       int,
        map_lot         text NOT NULL,
        facts           jsonb NOT NULL,
        parcels_as_of   date,
        verified        boolean NOT NULL,
        disputed        boolean NOT NULL DEFAULT false,
        note            text NOT NULL DEFAULT ''
    );

    CREATE TABLE application_item (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        application_id  uuid NOT NULL REFERENCES application(id) ON DELETE CASCADE,
        kind            text NOT NULL,
        position        int NOT NULL,
        created_at      timestamptz NOT NULL DEFAULT now(),
        removed_at      timestamptz
    );
    CREATE INDEX application_item_app ON application_item (application_id, position);

    CREATE TABLE answer (
        seq             bigserial PRIMARY KEY,
        application_id  uuid NOT NULL REFERENCES application(id) ON DELETE CASCADE,
        field_id        text NOT NULL,
        item_id         uuid REFERENCES application_item(id) ON DELETE CASCADE,
        value           jsonb,
        set_by          text NOT NULL,
        set_at          timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX answer_current ON answer (application_id, field_id, item_id, seq DESC);

    CREATE TABLE section_note (
        seq             bigserial PRIMARY KEY,
        application_id  uuid NOT NULL REFERENCES application(id) ON DELETE CASCADE,
        section_id      text NOT NULL,
        item_id         uuid REFERENCES application_item(id) ON DELETE CASCADE,
        text            text NOT NULL,
        set_by          text NOT NULL,
        set_at          timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX section_note_current ON section_note (application_id, section_id, item_id, seq DESC);

    CREATE TABLE attachment (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        application_id  uuid NOT NULL REFERENCES application(id) ON DELETE CASCADE,
        field_id        text NOT NULL,
        item_id         uuid REFERENCES application_item(id) ON DELETE CASCADE,
        filename        text NOT NULL,
        content_type    text NOT NULL,
        size_bytes      bigint NOT NULL,
        sha256          char(64) NOT NULL,
        storage_key     text NOT NULL UNIQUE,
        created_at      timestamptz NOT NULL DEFAULT now(),
        removed_at      timestamptz
    );
    CREATE INDEX attachment_app ON attachment (application_id);

    CREATE TRIGGER answer_append_only BEFORE UPDATE OR DELETE ON answer
        FOR EACH ROW EXECUTE FUNCTION event_append_only();
    CREATE TRIGGER section_note_append_only BEFORE UPDATE OR DELETE ON section_note
        FOR EACH ROW EXECUTE FUNCTION event_append_only();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE attachment;
    DROP TABLE section_note;
    DROP TABLE answer;
    DROP TABLE application_item;
    DROP TABLE property_snapshot;
    DROP TABLE application;
    """)
