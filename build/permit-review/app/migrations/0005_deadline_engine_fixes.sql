-- =============================================================================
-- Newcastle Permit Review — 0005_deadline_engine_fixes.sql
--
-- Adversarial-review fixes to the W3 statutory deadline engine
-- (engine/deadlines.py) and its milestone model (case_milestones). Two
-- schema changes, both additive/widening, neither touching any populated
-- production table (this checkout has zero real case rows anywhere, same
-- as every migration before it):
--
--   (a) F6 — promote 'findings_issued' (§12.e.6) and 'certificate_recorded'
--       (§19.c.3) to FIRST-CLASS case_milestones.kind values. Before this
--       migration, engine/deadlines.py bridged both statutory events through
--       the generic 'other' kind's free-text `note` field via a casefold
--       substring match on "finding" / "certificate" — an undocumented
--       magic string an operator had no way to discover from the UI, and
--       one that silently failed to record the CERTIFICATE at all if a note
--       happened to mention "finding" first (the if/elif in the old code).
--       engine/deadlines.py's own bridging code is deleted in the same
--       change that ships this migration; see that file's
--       `_MILESTONE_TO_FIELD` dict and case_facts_from_row(). This migration
--       ALSO reclassifies any existing 'other' row whose note matches the
--       old bridging convention (case-insensitive substring, "finding"
--       checked before "certificate", exactly mirroring the code path being
--       retired) — conservative, and a no-op on every shipped checkout,
--       which has zero case_milestones rows of any kind.
--
--   (b) F9b — the `deadlines` table (0001_init.sql) has no columns for a
--       Deadline's `conflict_group` / `conflict_note` /
--       `never_autogenerate_condition` (Clock fields carried on the Python
--       object since W3, e.g. the two subdivision plat-recording clocks that
--       CONFLICT with each other — §2.e.1's 90 days vs §8.f.5/§12.j.1's six
--       months). Before this migration, engine.deadlines.deadline_row()
--       silently dropped all three when shaping a row for a future writer to
--       INSERT — once persisted, a protected/conflicted deadline would have
--       been indistinguishable from any ordinary one. Plain ALTER TABLE ADD
--       COLUMN (SQLite allows this without the temp-table rebuild recipe
--       0002/0003/this file's own (a) needed for `case_milestones.kind`,
--       because a CHECK on the WHOLE table, not a single new column, is what
--       forces that recipe — see 0002_case_tracking.sql's note on why).
--
-- Same "create the replacement under its own temporary name, DROP the
-- ORIGINAL, RENAME the replacement into place" recipe as 0002/0003 for (a)
-- — see 0002_case_tracking.sql's own note for why the original must never
-- be renamed away first (SQLite's "smart" FK rename would rewrite every
-- other table's `REFERENCES case_milestones(...)` — in fact nothing
-- references case_milestones except its own self-referential
-- `superseded_by`, but the recipe is kept identical to its predecessors on
-- purpose: one rebuild pattern for this table, never two).
-- =============================================================================


-- ---------------------------------------------------------------------------
-- (a) widen case_milestones.kind with 'findings_issued' and
-- 'certificate_recorded'; reclassify any 'other' row the old bridging
-- convention would have matched.
-- ---------------------------------------------------------------------------
CREATE TABLE case_milestones_new_0005 (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN
                        ('application_dated','application_received','pre_submittal_meeting',
                         'circulated','notice_mailed','notice_published',
                         'completeness_determined','hearing_opened','hearing_closed','meeting',
                         'forwarded_to_planning_board','decision_issued','decision_filed',
                         'findings_issued','certificate_recorded',
                         'plat_recorded','appeal_filed','reconsideration_requested','other')),
    occurred_on     TEXT NOT NULL,              -- ISO date (YYYY-MM-DD)
    note            TEXT,
    superseded_by   TEXT REFERENCES case_milestones(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL
);

-- Reclassification mirrors engine/deadlines.py's retired bridging convention
-- EXACTLY (finding checked before certificate — the old if/elif order) so
-- no existing row's effective meaning changes, only its `kind` becomes
-- explicit. A row that matches neither substring, or is not 'other' at all,
-- passes through with its original kind untouched.
INSERT INTO case_milestones_new_0005
    (id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id)
SELECT
    id, case_id,
    CASE
        WHEN kind = 'other' AND note IS NOT NULL AND LOWER(note) LIKE '%finding%'
            THEN 'findings_issued'
        WHEN kind = 'other' AND note IS NOT NULL AND LOWER(note) LIKE '%certificate%'
            THEN 'certificate_recorded'
        ELSE kind
    END,
    occurred_on, note, superseded_by, created_at, actor_user_id
FROM case_milestones;

DROP TABLE case_milestones;
ALTER TABLE case_milestones_new_0005 RENAME TO case_milestones;

CREATE INDEX IF NOT EXISTS ix_case_milestones_case ON case_milestones(case_id, kind, occurred_on);
CREATE INDEX IF NOT EXISTS ix_case_milestones_live ON case_milestones(case_id) WHERE superseded_by IS NULL;

DROP TRIGGER IF EXISTS trg_case_milestones_supersede_once;
CREATE TRIGGER trg_case_milestones_supersede_once
BEFORE UPDATE OF superseded_by ON case_milestones
WHEN OLD.superseded_by IS NOT NULL AND NEW.superseded_by IS NOT OLD.superseded_by
BEGIN
    SELECT RAISE(ABORT, '0002_case_tracking.sql: case_milestones.superseded_by is write-once; insert a new row');
END;


-- ---------------------------------------------------------------------------
-- (b) deadlines — carry the never_autogenerate_condition conflict metadata
-- through to the persisted row (F9b). never_autogenerate_condition defaults
-- to 0 (false) so every deadline kind this app has ever computed before
-- this migration remains correctly unprotected; only the two subdivision
-- plat-recording clocks set it true, via deadline_row() (engine/deadlines.py).
-- ---------------------------------------------------------------------------
ALTER TABLE deadlines ADD COLUMN conflict_group TEXT;
ALTER TABLE deadlines ADD COLUMN conflict_note TEXT;
ALTER TABLE deadlines ADD COLUMN never_autogenerate_condition INTEGER NOT NULL DEFAULT 0
    CHECK (never_autogenerate_condition IN (0, 1));

-- =============================================================================
-- END 0005_deadline_engine_fixes.sql
-- =============================================================================
