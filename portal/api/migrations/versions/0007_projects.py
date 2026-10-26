"""Projects (projects brief §5.1): a project made of parts, the official forms it has
pinned, and what the Town locks — the submission and the reviews it gives.

Each draft application becomes a project with the same id, and its items become parts
with the same ids, so answers, notes and attachments gain a project and part without
losing anything. The application columns stay until the routes have moved (0008).

Revision ID: 0007
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

TITLES = {
    "small_project_plan": "Small Project Plan Application",
    "use_permit": "Use Permit Application",
    "entrance_permit": "Entrance / Driveway Permit Application",
}
# A form with no items gains the one part it was about.
FIRST_PART = {"use_permit": "use", "entrance_permit": "driveway", "small_project_plan": "building"}
KEYED = ("answer", "section_note", "attachment")


def upgrade() -> None:
    op.execute("""
    CREATE TABLE project (
        id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        applicant_id  uuid NOT NULL REFERENCES applicant(id) ON DELETE CASCADE,
        title         text NOT NULL,
        ruleset_key   text NOT NULL,
        status        text NOT NULL DEFAULT 'draft'
                      CHECK (status IN ('draft', 'submitted', 'locked', 'decided')),
        revision      int NOT NULL DEFAULT 0,
        created_at    timestamptz NOT NULL DEFAULT now(),
        updated_at    timestamptz NOT NULL DEFAULT now(),
        submitted_at  timestamptz,
        locked_at     timestamptz,
        locked_by     uuid REFERENCES applicant(id)
    );
    CREATE INDEX project_applicant ON project (applicant_id, updated_at DESC);

    CREATE TABLE project_part (
        id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id  uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
        kind        text NOT NULL,
        position    int NOT NULL,
        created_at  timestamptz NOT NULL DEFAULT now(),
        removed_at  timestamptz
    );
    CREATE INDEX project_part_project ON project_part (project_id, kind, position);

    CREATE TABLE project_form (
        project_id    uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
        form_key      text NOT NULL,
        form_version  int NOT NULL,
        PRIMARY KEY (project_id, form_key)
    );

    CREATE TABLE submission (
        id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id  uuid NOT NULL REFERENCES project(id) ON DELETE CASCADE,
        seq         int NOT NULL,
        locked_at   timestamptz NOT NULL DEFAULT now(),
        locked_by   uuid REFERENCES applicant(id),
        snapshot    jsonb NOT NULL,
        sha256      char(64) NOT NULL,
        UNIQUE (project_id, seq)
    );
    CREATE TRIGGER submission_append_only BEFORE UPDATE OR DELETE ON submission
        FOR EACH ROW EXECUTE FUNCTION event_append_only();

    CREATE TABLE review (
        id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        submission_id  uuid NOT NULL REFERENCES submission(id),
        review_key     text NOT NULL,
        use_key        text,
        permit_key     text NOT NULL,
        reviewer       text,  -- none for a fee line such as Structure
        status         text NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'in_review', 'decided')),
        submitted_at   timestamptz NOT NULL,
        decision_at    timestamptz
    );
    CREATE INDEX review_submission ON review (submission_id);

    ALTER TABLE property_snapshot ADD COLUMN project_id uuid UNIQUE REFERENCES project(id) ON DELETE CASCADE;
    ALTER TABLE property_snapshot DROP CONSTRAINT property_snapshot_pkey;
    ALTER TABLE property_snapshot ALTER COLUMN application_id DROP NOT NULL;
    ALTER TABLE property_snapshot ADD CONSTRAINT property_snapshot_application_key UNIQUE (application_id);
    """)
    for t in KEYED:
        op.execute(f"""
        ALTER TABLE {t} ADD COLUMN project_id uuid REFERENCES project(id) ON DELETE CASCADE;
        ALTER TABLE {t} ADD COLUMN part_id uuid REFERENCES project_part(id) ON DELETE CASCADE;
        ALTER TABLE {t} ALTER COLUMN application_id DROP NOT NULL;
        """)

    titles = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in TITLES.items())
    firsts = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in FIRST_PART.items())
    op.execute(f"""
    INSERT INTO project (id, applicant_id, title, ruleset_key, status, revision, created_at, updated_at)
        SELECT id, applicant_id, CASE form_key {titles} ELSE form_key END, ruleset_key, 'draft', revision,
               created_at, updated_at
        FROM application;
    INSERT INTO project_form (project_id, form_key, form_version) SELECT id, form_key, form_version FROM application;
    INSERT INTO project_part (id, project_id, kind, position, created_at, removed_at)
        SELECT id, application_id, CASE kind WHEN 'component' THEN 'addition' ELSE kind END, position,
               created_at, removed_at
        FROM application_item;
    INSERT INTO project_part (project_id, kind, position)
        SELECT a.id, CASE a.form_key {firsts} END, 0 FROM application a
        WHERE a.form_key IN ({", ".join(f"'{k}'" for k in FIRST_PART)})
          AND NOT EXISTS (SELECT 1 FROM application_item i WHERE i.application_id = a.id AND i.removed_at IS NULL);
    UPDATE property_snapshot SET project_id = application_id;
    """)
    for t in KEYED:
        # answer and section_note are insert-only; the new keys are filled once, here.
        trigger = {"answer": "answer_append_only", "section_note": "section_note_append_only"}.get(t)
        if trigger:
            op.execute(f"ALTER TABLE {t} DISABLE TRIGGER {trigger}")
        op.execute(f"UPDATE {t} SET project_id = application_id, part_id = item_id")
        if trigger:
            op.execute(f"ALTER TABLE {t} ENABLE TRIGGER {trigger}")
    op.execute("""
    CREATE INDEX answer_project_current ON answer (project_id, field_id, part_id, seq DESC);
    CREATE INDEX section_note_project_current ON section_note (project_id, section_id, part_id, seq DESC);
    CREATE INDEX attachment_project ON attachment (project_id);
    """)


def downgrade() -> None:
    for t in KEYED:
        trigger = {"answer": "answer_append_only", "section_note": "section_note_append_only"}.get(t)
        if trigger:
            op.execute(f"ALTER TABLE {t} DISABLE TRIGGER {trigger}")
        op.execute(f"DELETE FROM {t} WHERE application_id IS NULL")
        if trigger:
            op.execute(f"ALTER TABLE {t} ENABLE TRIGGER {trigger}")
        op.execute(f"""
        ALTER TABLE {t} ALTER COLUMN application_id SET NOT NULL;
        ALTER TABLE {t} DROP COLUMN part_id;
        ALTER TABLE {t} DROP COLUMN project_id;
        """)
    op.execute("""
    DELETE FROM property_snapshot WHERE application_id IS NULL;
    ALTER TABLE property_snapshot DROP CONSTRAINT property_snapshot_application_key;
    ALTER TABLE property_snapshot ADD PRIMARY KEY (application_id);
    ALTER TABLE property_snapshot DROP COLUMN project_id;
    DROP TABLE review;
    DROP TABLE submission;
    DROP TABLE project_form;
    DROP TABLE project_part;
    DROP TABLE project;
    """)
