-- =============================================================================
-- Newcastle Permit Review — 0010_clock_extensions.sql
--
-- HARD-FINAL adversarial-review Finding 3 fix. Article 7 §6.e.1: "Upon
-- mutual agreement by the applicant and the Permitting Authority, the
-- following procedural requirements may be extended: (a) The time limit
-- required for commencement of a public hearing; (b) The time limit
-- required to make a decision." §6.e.2: "Time limit extensions shall be
-- recorded in writing." §8.d.1's own auto-approval trigger is itself
-- qualified "...within the maximum time requirement OR PERMITTED
-- EXTENSIONS, AS APPLICABLE" -- so a lawfully extended clock is, by the
-- Code's own words, not a §8.d.1 failure at all.
--
-- Before this migration, NOTHING in this schema could represent that a
-- §6.e.1 agreement had ever happened -- engine/deadlines.py computed every
-- decision/hearing due_date from the clock's bare statutory day count, with
-- no way to add the agreed days back in. A lawfully extended case therefore
-- showed a PERMANENT, un-clearable false AUTO-APPROVAL banner, because the
-- app had no way to know the deadline the Code itself says was moved.
-- engine/deadlines.CaseFacts.waived_clocks / na_clocks had the same defect
-- one layer up: both fields existed on the dataclass and both are read by
-- _evaluate_clock(), but case_facts_from_row() never populated them from
-- anything in the database -- no case_milestones.kind, no column, no write
-- path -- so they were permanently empty outside of tests. Neither escape
-- hatch (extend the clock, or mark it waived/not applicable) was reachable
-- by an operator.
--
-- This migration adds THREE new case_milestones.kind values, all
-- resolvable through the SAME append-only, audited, write-once-superseded
-- machinery every other dated event already uses (app.cases.record_dates;
-- CONTRACT.md §3.3's one-events-row-per-write discipline is unchanged --
-- no new write path bypasses it):
--
--   extension_agreed     -- a §6.e.1 agreement. Requires target_clock_key
--                            (which clock the agreement extends -- restricted
--                            at the app layer, engine.deadlines.
--                            clock_is_extendable(), to the municipal_duty /
--                            conditional_duty clocks whose satisfying_event is
--                            a hearing-commencement or a decision, matching
--                            §6.e.1(a)/(b) -- see DECISIONS-NEEDED D-0024),
--                            extension_days (a positive integer -- the
--                            number of days, in the CLOCK'S OWN basis
--                            (calendar/business/months), the agreement
--                            adds), and written_agreement_ref (§6.e.2 -- a
--                            human-readable pointer to the writing itself:
--                            a letter date/description, a document id,
--                            whatever the case file actually holds).
--                            Multiple LIVE extension_agreed rows against the
--                            same clock ACCUMULATE (engine/deadlines.py
--                            sums them) -- a second written agreement is a
--                            second extension, not a replacement of the
--                            first; §6.e.1 imposes no cap on how many times
--                            the parties may agree again.
--   clock_waived          -- a human determination that a clock does not
--                            apply to this case and the app should not treat
--                            a missed due date as a Town failure. Requires
--                            target_clock_key and a non-empty `note` (why).
--   clock_not_applicable  -- same shape as clock_waived, the other of the
--                            two pre-existing ClockStatus values
--                            (engine.deadlines.ClockStatus.NOT_APPLICABLE)
--                            that had no write path before this migration.
--
-- Same "create the replacement under its own temporary name, DROP the
-- ORIGINAL, RENAME the replacement into place" recipe as every prior
-- case_milestones rebuild (0002/0003/0005/0006) -- see 0002_case_tracking.sql's
-- own note for why the original must never be renamed away first. This is
-- the table's FIFTH rebuild; 0007_supersede_reason.sql's plain ALTER TABLE
-- ADD COLUMN (no CHECK spanning the whole table) is carried forward as a
-- column here, same as every rebuild since 0007 must do.
--
-- No existing kind is removed or renamed; zero case_milestones rows exist
-- on any shipped checkout (same note as every migration before it), so
-- there is nothing to backfill or reclassify.
-- =============================================================================

CREATE TABLE case_milestones_new_0010 (
    id                      TEXT PRIMARY KEY,
    case_id                 TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    kind                    TEXT NOT NULL CHECK (kind IN
                                ('application_dated','application_received','pre_submittal_meeting',
                                 'circulated','notice_mailed','notice_published',
                                 'completeness_determined','hearing_opened','hearing_closed','meeting',
                                 'forwarded_to_planning_board','decision_issued','decision_filed',
                                 'findings_issued','certificate_recorded',
                                 'plat_recorded','appeal_filed','reconsideration_requested',
                                 'appeal_hearing_opened','appeal_hearing_closed','appeal_decision',
                                 'reconsideration_decided',
                                 'extension_agreed','clock_waived','clock_not_applicable',
                                 'other')),
    occurred_on             TEXT NOT NULL,              -- ISO date (YYYY-MM-DD)
    note                    TEXT,
    superseded_by           TEXT REFERENCES case_milestones(id) ON DELETE SET NULL,
    created_at              TEXT NOT NULL,
    actor_user_id           TEXT REFERENCES users(id) ON DELETE SET NULL,
    supersede_reason        TEXT
                                CHECK (supersede_reason IS NULL OR supersede_reason IN ('reschedule', 'correction')),
    -- Which clock_key (rulesets/<key>/clocks.json) this row names. NULL for
    -- every kind except the three added by this migration -- app.cases.
    -- record_dates enforces that at the boundary; the CHECK below backstops
    -- it at the DB level too (CONTRACT.md §1 S1 -- the same
    -- app-check-plus-DB-CHECK-backstop posture as the cases.status/binding
    -- gate triggers).
    target_clock_key        TEXT,
    -- Only meaningful for kind='extension_agreed' -- the number of days
    -- (in the target clock's own basis) this ONE written agreement adds.
    extension_days          INTEGER CHECK (extension_days IS NULL OR extension_days > 0),
    -- Only meaningful for kind='extension_agreed' -- §6.e.2's "recorded in
    -- writing" requirement, captured as a pointer to the writing (a letter
    -- date/description, a document id, ...), never inferred.
    written_agreement_ref   TEXT,
    CHECK (
        CASE kind
            WHEN 'extension_agreed' THEN
                target_clock_key IS NOT NULL AND target_clock_key <> ''
                AND extension_days IS NOT NULL AND extension_days > 0
                AND written_agreement_ref IS NOT NULL AND written_agreement_ref <> ''
            WHEN 'clock_waived' THEN
                target_clock_key IS NOT NULL AND target_clock_key <> ''
                AND note IS NOT NULL AND note <> ''
                AND extension_days IS NULL AND written_agreement_ref IS NULL
            WHEN 'clock_not_applicable' THEN
                target_clock_key IS NOT NULL AND target_clock_key <> ''
                AND note IS NOT NULL AND note <> ''
                AND extension_days IS NULL AND written_agreement_ref IS NULL
            ELSE
                target_clock_key IS NULL AND extension_days IS NULL AND written_agreement_ref IS NULL
        END
    )
);

INSERT INTO case_milestones_new_0010
    (id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id, supersede_reason)
SELECT id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id, supersede_reason
FROM case_milestones;

DROP TABLE case_milestones;
ALTER TABLE case_milestones_new_0010 RENAME TO case_milestones;

CREATE INDEX IF NOT EXISTS ix_case_milestones_case ON case_milestones(case_id, kind, occurred_on);
CREATE INDEX IF NOT EXISTS ix_case_milestones_live ON case_milestones(case_id) WHERE superseded_by IS NULL;
-- New: the dashboard/case-detail deadlines view needs "every live extension/
-- waiver/n-a row targeting clock X on case Y" -- this index makes that a
-- direct lookup instead of a table scan, exactly mirroring ix_case_milestones_live
-- above for the same table.
CREATE INDEX IF NOT EXISTS ix_case_milestones_target_clock
    ON case_milestones(case_id, target_clock_key) WHERE target_clock_key IS NOT NULL;

DROP TRIGGER IF EXISTS trg_case_milestones_supersede_once;
CREATE TRIGGER trg_case_milestones_supersede_once
BEFORE UPDATE OF superseded_by ON case_milestones
WHEN OLD.superseded_by IS NOT NULL AND NEW.superseded_by IS NOT OLD.superseded_by
BEGIN
    SELECT RAISE(ABORT, '0002_case_tracking.sql: case_milestones.superseded_by is write-once; insert a new row');
END;

-- =============================================================================
-- END 0010_clock_extensions.sql
-- =============================================================================
