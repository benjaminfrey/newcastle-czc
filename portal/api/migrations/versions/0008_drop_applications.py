"""The routes have moved to projects: the application tables and columns go (projects brief §5.1).

Revision ID: 0008
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

KEYED = ("answer", "section_note", "attachment")
TRIGGERS = {"answer": "answer_append_only", "section_note": "section_note_append_only"}


def upgrade() -> None:
    for t in KEYED:
        if t in TRIGGERS:
            op.execute(f"ALTER TABLE {t} DISABLE TRIGGER {TRIGGERS[t]}")
        op.execute(f"DELETE FROM {t} WHERE project_id IS NULL")
        if t in TRIGGERS:
            op.execute(f"ALTER TABLE {t} ENABLE TRIGGER {TRIGGERS[t]}")
        op.execute(f"""
        ALTER TABLE {t} ALTER COLUMN project_id SET NOT NULL;
        ALTER TABLE {t} DROP COLUMN item_id;
        ALTER TABLE {t} DROP COLUMN application_id;
        """)
    op.execute("""
    DELETE FROM property_snapshot WHERE project_id IS NULL;
    ALTER TABLE property_snapshot DROP CONSTRAINT property_snapshot_application_key;
    ALTER TABLE property_snapshot DROP COLUMN application_id;
    ALTER TABLE property_snapshot DROP CONSTRAINT property_snapshot_project_id_key;
    ALTER TABLE property_snapshot ADD PRIMARY KEY (project_id);
    DROP TABLE application_item;
    DROP TABLE application;
    """)


def downgrade() -> None:
    # Back to 0007's shape: each project an application of its first official form, its
    # buildings and additions items again. Parts that were never items keep no item.
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
    CREATE TABLE application_item (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        application_id  uuid NOT NULL REFERENCES application(id) ON DELETE CASCADE,
        kind            text NOT NULL,
        position        int NOT NULL,
        created_at      timestamptz NOT NULL DEFAULT now(),
        removed_at      timestamptz
    );
    CREATE INDEX application_item_app ON application_item (application_id, position);
    INSERT INTO application (id, applicant_id, form_key, form_version, ruleset_key, revision, created_at, updated_at)
        SELECT p.id, p.applicant_id, coalesce(f.form_key, 'use_permit'), coalesce(f.form_version, 1), p.ruleset_key,
               p.revision, p.created_at, p.updated_at
        FROM project p LEFT JOIN LATERAL (
            SELECT form_key, form_version FROM project_form
            WHERE project_id = p.id AND form_key NOT IN ('cover_sheet', 'project_questions') ORDER BY form_key LIMIT 1
        ) f ON true;
    INSERT INTO application_item (id, application_id, kind, position, created_at, removed_at)
        SELECT id, project_id, CASE kind WHEN 'addition' THEN 'component' ELSE kind END, position, created_at, removed_at
        FROM project_part WHERE kind IN ('building', 'addition');
    ALTER TABLE property_snapshot DROP CONSTRAINT property_snapshot_pkey;
    ALTER TABLE property_snapshot ADD CONSTRAINT property_snapshot_project_id_key UNIQUE (project_id);
    ALTER TABLE property_snapshot ADD COLUMN application_id uuid REFERENCES application(id) ON DELETE CASCADE;
    UPDATE property_snapshot SET application_id = project_id;
    ALTER TABLE property_snapshot ADD CONSTRAINT property_snapshot_application_key UNIQUE (application_id);
    """)
    for t in KEYED:
        op.execute(f"""
        ALTER TABLE {t} ADD COLUMN application_id uuid REFERENCES application(id) ON DELETE CASCADE;
        ALTER TABLE {t} ADD COLUMN item_id uuid REFERENCES application_item(id) ON DELETE CASCADE;
        ALTER TABLE {t} ALTER COLUMN project_id DROP NOT NULL;
        """)
        if t in TRIGGERS:
            op.execute(f"ALTER TABLE {t} DISABLE TRIGGER {TRIGGERS[t]}")
        op.execute(f"UPDATE {t} SET application_id = project_id,"
                   f" item_id = (SELECT i.id FROM application_item i WHERE i.id = {t}.part_id)")
        if t in TRIGGERS:
            op.execute(f"ALTER TABLE {t} ENABLE TRIGGER {TRIGGERS[t]}")
    op.execute("""
    CREATE INDEX answer_current ON answer (application_id, field_id, item_id, seq DESC);
    CREATE INDEX section_note_current ON section_note (application_id, section_id, item_id, seq DESC);
    CREATE INDEX attachment_app ON attachment (application_id);
    """)
