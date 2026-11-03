"""The guided builder's record (guided plan 2): which picture a project's conversation started
from, every action in it with the turn exactly as it was shown, and what the person typed, which
is kept for staff and read by nothing (spec decision 14). Actions and notes are insert-only:
backing up is a new row, because it is evidence of where the Code pinches (spec §9).

Revision ID: 0009
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE guide_conversation (
        project_id      uuid PRIMARY KEY REFERENCES project(id) ON DELETE CASCADE,
        opening         text NOT NULL,
        content_digest  text NOT NULL,
        started_at      timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE guide_action (
        project_id      uuid NOT NULL REFERENCES guide_conversation(project_id) ON DELETE CASCADE,
        seq             integer NOT NULL,
        kind            text NOT NULL CHECK (kind IN ('answer', 'back', 'restart')),
        turn_id         text,
        value           jsonb,
        shown           jsonb NOT NULL,
        content_digest  text NOT NULL,
        at              timestamptz NOT NULL DEFAULT now(),
        by              text NOT NULL,
        PRIMARY KEY (project_id, seq)
    );
    CREATE TABLE guide_note (
        id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        n           bigint GENERATED ALWAYS AS IDENTITY,  -- the order notes were written in
        project_id  uuid NOT NULL REFERENCES guide_conversation(project_id) ON DELETE CASCADE,
        body        text NOT NULL CHECK (length(body) BETWEEN 1 AND 4000),
        at          timestamptz NOT NULL DEFAULT now(),
        by          text NOT NULL
    );
    CREATE INDEX guide_note_project ON guide_note (project_id, n);

    CREATE TRIGGER guide_action_append_only BEFORE UPDATE OR DELETE ON guide_action
        FOR EACH ROW EXECUTE FUNCTION event_append_only();
    CREATE TRIGGER guide_note_append_only BEFORE UPDATE OR DELETE ON guide_note
        FOR EACH ROW EXECUTE FUNCTION event_append_only();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE guide_note;
    DROP TABLE guide_action;
    DROP TABLE guide_conversation;
    """)
