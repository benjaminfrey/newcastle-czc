-- =============================================================================
-- Newcastle Permit Review — 0006_appeal_recordability.sql
--
-- N2 fix (event recordability). rulesets/adopted/clocks.json's three §23
-- appeal-track clocks added at F3 -- administrative_appeal_hearing (§23.d.2),
-- administrative_appeal_decision (§23.d.3), reconsideration_decision
-- (§23.e.4) -- name FOUR events (appeal_hearing_opened_at,
-- appeal_hearing_closed_at, appeal_decision_at, reconsideration_decided_at)
-- that engine/deadlines.py's CaseFacts dataclass has carried as fields since
-- F3 (see that file's own "F3's §23 appeal-track clocks ... name these four
-- events; case_milestones has no dedicated `kind` for any of them yet"
-- comment), but which NO case_milestones.kind, anywhere, could ever record.
-- Two of the three clocks (administrative_appeal_hearing,
-- administrative_appeal_decision) carry the §8.d.1 auto-approval
-- consequence -- so a Board of Appeals that held its hearing and decided an
-- appeal exactly on time still showed a PERMANENT, un-clearable
-- auto-approval alarm. This migration is the schema half of the fix; the
-- code half (app.cases.CASE_MILESTONE_KINDS, engine.deadlines.
-- _MILESTONE_TO_FIELD, app.main.MILESTONE_KIND_LABELS) ships in the same
-- change. ruleset_build.verify_structure.check_clock_event_recordability
-- (run via `python run.py --verify-structure` and folded into
-- `--selftest`) now asserts, as a standing build gate, that every clock's
-- start_event/satisfying_event is recordable through ALL FOUR layers this
-- migration is the first of -- so this exact defect class (a clock naming
-- an event no operator can ever record) can never ship silently again.
--
-- Four new case_milestones.kind values, all additive:
--   appeal_hearing_opened    -- §23.d.2, satisfying administrative_appeal_hearing
--   appeal_hearing_closed    -- starts administrative_appeal_decision (§23.d.3)
--   appeal_decision          -- §23.d.3, satisfying administrative_appeal_decision
--   reconsideration_decided  -- §23.e.4, satisfying reconsideration_decision
--
-- Deliberately NAMED DISTINCT from the case's own original-review
-- hearing_opened / hearing_closed / decision_issued kinds -- reusing those
-- would silently overwrite the underlying case's OWN hearing/decision date
-- with the Appellate Authority's later, separate one and corrupt that
-- clock's status if ever recomputed (exactly the collision
-- administrative_appeal_hearing's own clocks.json notes already warn
-- against). No existing kind is removed or renamed; zero case_milestones
-- rows exist on any shipped checkout, so there is nothing to backfill.
--
-- Same "create the replacement under its own temporary name, DROP the
-- ORIGINAL, RENAME the replacement into place" recipe as 0002/0003/0005 --
-- see 0002_case_tracking.sql's own note for why the original must never be
-- renamed away first. This is the table's FOURTH rebuild; the DB's own
-- sqlite_master.sql for case_milestones (not any single migration file in
-- isolation) is therefore the only reliable place to read its CURRENT CHECK
-- constraint from -- see check_clock_event_recordability's own docstring.
-- =============================================================================

CREATE TABLE case_milestones_new_0006 (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN
                        ('application_dated','application_received','pre_submittal_meeting',
                         'circulated','notice_mailed','notice_published',
                         'completeness_determined','hearing_opened','hearing_closed','meeting',
                         'forwarded_to_planning_board','decision_issued','decision_filed',
                         'findings_issued','certificate_recorded',
                         'plat_recorded','appeal_filed','reconsideration_requested',
                         'appeal_hearing_opened','appeal_hearing_closed','appeal_decision',
                         'reconsideration_decided','other')),
    occurred_on     TEXT NOT NULL,              -- ISO date (YYYY-MM-DD)
    note            TEXT,
    superseded_by   TEXT REFERENCES case_milestones(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL
);

INSERT INTO case_milestones_new_0006
    (id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id)
SELECT id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id
FROM case_milestones;

DROP TABLE case_milestones;
ALTER TABLE case_milestones_new_0006 RENAME TO case_milestones;

CREATE INDEX IF NOT EXISTS ix_case_milestones_case ON case_milestones(case_id, kind, occurred_on);
CREATE INDEX IF NOT EXISTS ix_case_milestones_live ON case_milestones(case_id) WHERE superseded_by IS NULL;

DROP TRIGGER IF EXISTS trg_case_milestones_supersede_once;
CREATE TRIGGER trg_case_milestones_supersede_once
BEFORE UPDATE OF superseded_by ON case_milestones
WHEN OLD.superseded_by IS NOT NULL AND NEW.superseded_by IS NOT OLD.superseded_by
BEGIN
    SELECT RAISE(ABORT, '0002_case_tracking.sql: case_milestones.superseded_by is write-once; insert a new row');
END;

-- =============================================================================
-- END 0006_appeal_recordability.sql
-- =============================================================================
