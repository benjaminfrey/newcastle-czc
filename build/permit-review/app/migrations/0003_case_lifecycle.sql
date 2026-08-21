-- =============================================================================
-- Newcastle Permit Review — 0003_case_lifecycle.sql
--
-- W3 "cases + the audit-backed case lifecycle" task. Builds on top of
-- 0002_case_tracking.sql (already shipped in this checkout by a sibling W3
-- task covering document upload / statutory deadline clocks), which widened
-- cases.application_type and added case_milestones. This file does NOT
-- duplicate that work; it adds exactly the two things that task's schema did
-- not cover:
--
--   (a) the case STATUS state machine app/cases.py implements:
--       intake -> extracting -> review -> draft_issued -> meeting -> decided
--       -> closed (+ withdrawn from any non-terminal status). 0002 kept
--       0001_init.sql's placeholder status vocabulary (under_review,
--       draft_ready, in_packet, heard) verbatim; this replaces it with the
--       lifecycle's own words. There are zero real case rows anywhere this
--       app has shipped, so this is a clean cutover, not a data migration.
--
--   (b) an explicit, audited exception to the CONTRACT.md §3.2 binding gate
--       (`binding_override` + `override_reason`) -- a real (non-scratch)
--       case still cannot cite a non-binding ruleset by default; a human can
--       choose to, on the record, and app/cases.py requires a reason and
--       writes it into the same `case.created` events row every case
--       creation already produces (CONTRACT.md §3.3 -- one event per
--       mutation, not a second row).
--
--   (c) two more case_milestones.kind values -- 'application_received' and
--       'meeting' -- alongside every kind 0002_case_tracking.sql already
--       defined (none removed, none renamed). 'application_received' is
--       kept distinct from 0002's 'application_dated': the date PRINTED on
--       an application and the date the Town RECEIVED it are different
--       facts (the real Shattuck record shows an application "dated
--       2025-10-02, updated through 2025-12-18" -- multiple dates already,
--       none of them necessarily "received"), and the §5.c.3 notice-mailed
--       clock and similar deadlines anchor on receipt, not on the form's own
--       date. 'meeting' records every Board session a case is actually taken
--       up at (a hearing opened at one meeting and closed at a later one,
--       per the Shattuck pattern, is TWO 'meeting' rows plus the one
--       'hearing_opened' and one 'hearing_closed' row that already existed).
--
-- Same rebuild recipe as 0002_case_tracking.sql, verified the same way
-- (temp-named replacement table, drop the ORIGINAL, rename the replacement
-- into place -- never rename the original away, which would rewrite every
-- other table's `REFERENCES cases(id)` clause out from under it; see that
-- file's own note). `case_milestones` has no inbound FK from any other
-- table (only its own self-referential `superseded_by`) and zero rows in
-- any shipped checkout, so its rebuild is lower-risk still.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- (a) + (b): rebuild `cases`.
-- ---------------------------------------------------------------------------
CREATE TABLE cases_new_0003 (
    id                  TEXT PRIMARY KEY,
    case_number         TEXT UNIQUE,            -- town file number, when assigned
    label               TEXT NOT NULL,          -- 'M003, L059 (White Rd, Shattuck)'
    map_lot             TEXT,                   -- 'M003, L059'
    situs_address       TEXT,
    applicant_name      TEXT,
    application_type    TEXT NOT NULL CHECK (application_type IN
                            ('use','zoning','subdivision','shoreland','site_plan',
                             'special_permit','expanded_use','other',
                             'small_project_plan','large_project_plan','variance')),
    district_key        TEXT,                   -- 'd1' | 'sd-marine' | ... (CONTRACT.md §4.1.1)
    ruleset_id          TEXT NOT NULL REFERENCES rulesets(id) ON DELETE RESTRICT,
    is_scratch          INTEGER NOT NULL DEFAULT 0 CHECK (is_scratch IN (0,1)),

    -- CONTRACT.md §3.2's binding gate keeps its default-deny shape (see the
    -- triggers below); this is the one narrow, audited exception the W3
    -- brief calls for. binding_override=1 requires a non-empty
    -- override_reason (CHECK below); app/cases.py additionally requires the
    -- caller to state who authorized it, carried in the same `case.created`
    -- events row (CONTRACT.md §3.3) -- never a silent flip.
    binding_override    INTEGER NOT NULL DEFAULT 0 CHECK (binding_override IN (0,1)),
    override_reason     TEXT,

    -- W3 case-lifecycle state machine (app/cases.py:ALLOWED_TRANSITIONS owns
    -- the transition table; this CHECK is the DB-level backstop, same
    -- pattern 0001/0002 already used for is_scratch/binding_override).
    status              TEXT NOT NULL DEFAULT 'intake' CHECK (status IN
                            ('intake','extracting','review','draft_issued',
                             'meeting','decided','closed','withdrawn')),

    received_at         TEXT,                   -- convenience mirror of the latest
                                                  -- case_milestones 'application_received' row
    meeting_date        TEXT,                   -- computed by app/dates.py (§3.4), never typed
    draft_due           TEXT,                   -- meeting_date - 7 days
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL,

    CHECK (binding_override = 0 OR override_reason IS NOT NULL)
);

INSERT INTO cases_new_0003 (
    id, case_number, label, map_lot, situs_address, applicant_name,
    application_type, district_key, ruleset_id, is_scratch,
    binding_override, override_reason, status,
    received_at, meeting_date, draft_due, created_at, updated_at, actor_user_id
)
SELECT
    id, case_number, label, map_lot, situs_address, applicant_name,
    application_type, district_key, ruleset_id, is_scratch,
    0, NULL, 'intake',   -- every prior status value collapses to 'intake' (no real rows anywhere)
    received_at, meeting_date, draft_due, created_at, updated_at, actor_user_id
FROM cases;

DROP TABLE cases;
ALTER TABLE cases_new_0003 RENAME TO cases;

CREATE INDEX IF NOT EXISTS ix_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS ix_cases_meeting ON cases(meeting_date);
CREATE INDEX IF NOT EXISTS ix_cases_ruleset ON cases(ruleset_id);

-- CONTRACT.md §3.2 — the binding gate, enforced in the database, now with
-- the one explicit, audited override the W3 brief calls for.
DROP TRIGGER IF EXISTS trg_cases_binding_insert;
CREATE TRIGGER trg_cases_binding_insert
BEFORE INSERT ON cases
WHEN NEW.is_scratch = 0
 AND NEW.binding_override = 0
 AND (SELECT binding FROM rulesets WHERE id = NEW.ruleset_id) <> 1
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.2: a non-scratch case must cite a binding ruleset (set binding_override=1 with a non-null override_reason for an explicit, audited exception)');
END;

DROP TRIGGER IF EXISTS trg_cases_binding_update;
CREATE TRIGGER trg_cases_binding_update
BEFORE UPDATE ON cases
WHEN NEW.is_scratch = 0
 AND NEW.binding_override = 0
 AND (SELECT binding FROM rulesets WHERE id = NEW.ruleset_id) <> 1
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.2: a non-scratch case must cite a binding ruleset (set binding_override=1 with a non-null override_reason for an explicit, audited exception)');
END;


-- ---------------------------------------------------------------------------
-- (c) widen case_milestones.kind with 'application_received' and 'meeting'.
-- Self-referential FK only (superseded_by -> case_milestones.id); no other
-- table references this one, and it has zero rows in any shipped checkout.
-- ---------------------------------------------------------------------------
CREATE TABLE case_milestones_new_0003 (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN
                        ('application_dated','application_received','pre_submittal_meeting',
                         'circulated','notice_mailed','notice_published',
                         'completeness_determined','hearing_opened','hearing_closed','meeting',
                         'forwarded_to_planning_board','decision_issued','decision_filed',
                         'plat_recorded','appeal_filed','reconsideration_requested','other')),
    occurred_on     TEXT NOT NULL,              -- ISO date (YYYY-MM-DD)
    note            TEXT,
    superseded_by   TEXT REFERENCES case_milestones(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL
);

INSERT INTO case_milestones_new_0003
    (id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id)
SELECT id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id
FROM case_milestones;

DROP TABLE case_milestones;
ALTER TABLE case_milestones_new_0003 RENAME TO case_milestones;

CREATE INDEX IF NOT EXISTS ix_case_milestones_case ON case_milestones(case_id, kind, occurred_on);
CREATE INDEX IF NOT EXISTS ix_case_milestones_live ON case_milestones(case_id) WHERE superseded_by IS NULL;

-- Same write-once discipline 0002_case_tracking.sql defined (dropped along
-- with the table it was attached to; re-declared verbatim here).
DROP TRIGGER IF EXISTS trg_case_milestones_supersede_once;
CREATE TRIGGER trg_case_milestones_supersede_once
BEFORE UPDATE OF superseded_by ON case_milestones
WHEN OLD.superseded_by IS NOT NULL AND NEW.superseded_by IS NOT OLD.superseded_by
BEGIN
    SELECT RAISE(ABORT, '0002_case_tracking.sql: case_milestones.superseded_by is write-once; insert a new row');
END;

-- =============================================================================
-- END 0003_case_lifecycle.sql
-- =============================================================================
