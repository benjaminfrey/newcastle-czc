-- =============================================================================
-- Newcastle Permit Review — 0002_case_tracking.sql
-- W3 (Phase 3): cases, document upload, page census/tiering, statutory deadline
-- clocks, case dashboard. Implements CONTRACT.md §3 (schema contract) — additive
-- to 0001_init.sql, which already carries the FULL v1 table list; this file only
-- (a) widens cases.application_type to the statutory review-track vocabulary the
--     Article 7 Administration deadline clocks are keyed on (app/deadlines.py),
--     and
-- (b) adds case_milestones, the dated-event log the clocks are computed FROM.
--
-- Both changes are additive-only and safe against an EMPTY cases table (this is
-- the first workflow to write case rows at all — see README/CONTRACT state as of
-- 2026-08). Nothing here is ever run against a populated production table.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- (a) Widen cases.application_type.
--
-- 0001_init.sql's CHECK allowed 8 values, none of which named the specific
-- Article 7 review tracks the W3 deadline clocks are keyed on (§10 "Small
-- Project Plan", §11 "Large Project Plan", §19 "Variance" before the Board of
-- Appeals). 'subdivision' and 'special_permit' already matched (§12, §18) and
-- are untouched in meaning. Rather than overload 'zoning' / 'site_plan' / 'other'
-- to mean something the Code names precisely, this adds the three missing
-- values so a case's application_type says, in the Code's own words, which
-- clock set applies (CONTRACT.md §1 S7 — no silent guessing; a clock computed
-- against the wrong track would be a wrong legal deadline).
--
-- SQLite has no ALTER TABLE ... ALTER COLUMN / DROP CONSTRAINT, so widening a
-- CHECK requires the documented recreate procedure (sqlite.org/lang_altertable
-- "Making Other Kinds Of Table Schema Changes"): create the new table under a
-- temporary name, copy rows in, DROP the ORIGINAL 'cases' (not a renamed copy —
-- see note below), then RENAME the new table into place. Every other table's
-- `REFERENCES cases(id)` clause is untouched TEXT naming "cases" throughout, so
-- it resolves correctly against the new table the moment the rename completes;
-- this table has zero inbound rows anywhere at this point in the project, so no
-- PRAGMA foreign_keys juggling (which cannot happen mid-transaction anyway —
-- app/db.py:migrate() wraps this whole file in one BEGIN/COMMIT) is needed.
--
-- IMPORTANT: do NOT rename 'cases' itself first. `ALTER TABLE cases RENAME TO
-- x` would rewrite every OTHER table's `REFERENCES cases(...)` to `REFERENCES
-- x(...)` (SQLite's "smart" rename, on by default since 3.25.0) — and then
-- dropping x would leave those tables referencing a name that no longer
-- exists. Creating the replacement under its own temporary name and dropping
-- the untouched original avoids that trap entirely.
-- ---------------------------------------------------------------------------

CREATE TABLE cases_0002_new (
    id                  TEXT PRIMARY KEY,
    case_number         TEXT UNIQUE,
    label               TEXT NOT NULL,
    map_lot             TEXT,
    situs_address       TEXT,
    applicant_name      TEXT,
    application_type    TEXT NOT NULL CHECK (application_type IN
                            ('use','zoning','subdivision','shoreland','site_plan',
                             'special_permit','expanded_use','other',
                             'small_project_plan','large_project_plan','variance')),
    district_key        TEXT,
    ruleset_id          TEXT NOT NULL REFERENCES rulesets(id) ON DELETE RESTRICT,
    is_scratch          INTEGER NOT NULL DEFAULT 0 CHECK (is_scratch IN (0,1)),
    status              TEXT NOT NULL DEFAULT 'intake' CHECK (status IN
                            ('intake','under_review','draft_ready','in_packet',
                             'heard','decided','withdrawn','closed')),
    received_at         TEXT,
    meeting_date        TEXT,
    draft_due           TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL
);

INSERT INTO cases_0002_new
    (id, case_number, label, map_lot, situs_address, applicant_name,
     application_type, district_key, ruleset_id, is_scratch, status,
     received_at, meeting_date, draft_due, created_at, updated_at, actor_user_id)
SELECT id, case_number, label, map_lot, situs_address, applicant_name,
       application_type, district_key, ruleset_id, is_scratch, status,
       received_at, meeting_date, draft_due, created_at, updated_at, actor_user_id
FROM cases;

DROP TABLE cases;

ALTER TABLE cases_0002_new RENAME TO cases;

CREATE INDEX IF NOT EXISTS ix_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS ix_cases_meeting ON cases(meeting_date);
CREATE INDEX IF NOT EXISTS ix_cases_ruleset ON cases(ruleset_id);

-- Re-declare the CONTRACT.md §3.2 binding-gate triggers dropped along with the
-- original table (trigger bodies are byte-identical to 0001_init.sql's).
CREATE TRIGGER IF NOT EXISTS trg_cases_binding_insert
BEFORE INSERT ON cases
WHEN NEW.is_scratch = 0
 AND (SELECT binding FROM rulesets WHERE id = NEW.ruleset_id) <> 1
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.2: a non-scratch case must cite a binding ruleset');
END;

CREATE TRIGGER IF NOT EXISTS trg_cases_binding_update
BEFORE UPDATE ON cases
WHEN NEW.is_scratch = 0
 AND (SELECT binding FROM rulesets WHERE id = NEW.ruleset_id) <> 1
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.2: a non-scratch case must cite a binding ruleset');
END;


-- ---------------------------------------------------------------------------
-- (b) case_milestones — every dated procedural event for a case: submission,
-- pre-submittal meeting, circulation to departments, notice mailed/published,
-- completeness determination, hearing opened/closed, forwarding from CEO to
-- Planning Board, decision issued/filed, plat recorded, appeal filed,
-- reconsideration requested.
--
-- Modeled as ROWS, not columns on `cases`, because a hearing can be
-- RESCHEDULED AND RE-NOTICED — Newcastle's own Shattuck subdivision decision
-- (M003, L059) shows exactly this: notice went out ahead of an Oct 16 meeting,
-- the hearing was rescheduled to Nov 20, and RE-NOTICED. A single
-- `hearing_opened_at` column could not hold both notice events or both
-- proposed hearing dates without smoothing away a fact the real record
-- contains — which the W3 brief explicitly forbids. An amended/corrected
-- milestone is a NEW row; `superseded_by` marks the one it replaces (never
-- overwritten, never deleted — the same amendment discipline as
-- findings_nodes in 0001_init.sql).
--
-- app/deadlines.py reads the LIVE set (superseded_by IS NULL) as the anchor
-- dates its clocks compute from; a kind with more than one live row (a
-- re-notice) is exactly the case the dashboard must show, not collapse.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_milestones (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN
                        ('application_dated','pre_submittal_meeting','circulated',
                         'notice_mailed','notice_published','completeness_determined',
                         'hearing_opened','hearing_closed','forwarded_to_planning_board',
                         'decision_issued','decision_filed','plat_recorded',
                         'appeal_filed','reconsideration_requested','other')),
    occurred_on     TEXT NOT NULL,              -- ISO date (YYYY-MM-DD)
    note            TEXT,
    superseded_by   TEXT REFERENCES case_milestones(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_case_milestones_case ON case_milestones(case_id, kind, occurred_on);
CREATE INDEX IF NOT EXISTS ix_case_milestones_live ON case_milestones(case_id) WHERE superseded_by IS NULL;

-- Same write-once discipline as findings_nodes.superseded_by (0001_init.sql).
CREATE TRIGGER IF NOT EXISTS trg_case_milestones_supersede_once
BEFORE UPDATE OF superseded_by ON case_milestones
WHEN OLD.superseded_by IS NOT NULL AND NEW.superseded_by IS NOT OLD.superseded_by
BEGIN
    SELECT RAISE(ABORT, '0002_case_tracking.sql: case_milestones.superseded_by is write-once; insert a new row');
END;

-- =============================================================================
-- END 0002_case_tracking.sql
-- =============================================================================
