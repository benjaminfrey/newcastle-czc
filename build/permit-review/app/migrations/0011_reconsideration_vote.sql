-- =============================================================================
-- Newcastle Permit Review — 0011_reconsideration_vote.sql
--
-- HARD-FINAL adversarial-review Finding 6 fix. rulesets/adopted/clocks.json's
-- reconsideration_decision clock (§23.e.4: "If the Board of Appeals
-- reconsiders its original decision, the Board must conclude its
-- deliberations and vote within 45 days of the original decision") is
-- textually conditional on the Board actually RECONSIDERING -- and "reconsiders"
-- is itself a defined, later step: §23.e.1 lets an applicant REQUEST
-- reconsideration; §23.e.2/.e.3 require the Board to hold a hearing and take
-- a majority VOTE TO RECONSIDER before it "reconsiders" anything at all.
--
-- Before this migration, reconsideration_decision's predicate_event was
-- reconsideration_requested_at (the §23.e.1 REQUEST, recorded via the
-- pre-existing 'reconsideration_requested' kind) -- so a bare request, never
-- acted on by a vote, was already enough to flip this clock from
-- NOT_TRIGGERED to a live, ordinarily-branching duty, over-triggering
-- relative to the clock's own "if ... reconsiders" text. This migration adds
-- the missing case_milestones.kind for the actual §23.e.2/.e.3 vote, so
-- engine/deadlines.py can gate reconsideration_decision on that vote instead
-- of the request -- see engine/deadlines.py's CaseFacts.
-- reconsideration_voted_at, _MILESTONE_TO_FIELD, and
-- ruleset_build/build_clocks.py's reconsideration_decision duty_kind_note.
--
-- One new case_milestones.kind, additive:
--   reconsideration_voted -- §23.e.2/.e.3, the Board's vote TO reconsider its
--                            original decision (a majority of the Board
--                            members who originally voted). Shaped exactly
--                            like the pre-existing 'reconsideration_decided'/
--                            'appeal_decision' kinds -- occurred_on + optional
--                            note, no target_clock_key/extension_days/
--                            written_agreement_ref (those three columns are
--                            0010_clock_extensions.sql's, meaningful only for
--                            'extension_agreed'/'clock_waived'/
--                            'clock_not_applicable' -- this kind falls into
--                            that migration's CHECK ELSE branch, same as
--                            every other ordinary dated event).
--
-- Same "create the replacement under its own temporary name, DROP the
-- ORIGINAL, RENAME the replacement into place" recipe as every prior
-- case_milestones rebuild (0002/0003/0005/0006/0010) -- see
-- 0002_case_tracking.sql's own note for why the original must never be
-- renamed away first. This is the table's SIXTH rebuild; every column and
-- CHECK constraint 0007's supersede_reason and 0010's extension/waiver
-- columns added is carried forward verbatim -- this migration widens ONLY
-- the `kind` CHECK's IN-list, touching nothing else 0010 established.
--
-- No existing kind is removed or renamed; zero case_milestones rows exist on
-- any shipped checkout (same note as every migration before it), so there is
-- nothing to backfill or reclassify.
-- =============================================================================

CREATE TABLE case_milestones_new_0011 (
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
                                 'reconsideration_decided','reconsideration_voted',
                                 'extension_agreed','clock_waived','clock_not_applicable',
                                 'other')),
    occurred_on             TEXT NOT NULL,              -- ISO date (YYYY-MM-DD)
    note                    TEXT,
    superseded_by           TEXT REFERENCES case_milestones(id) ON DELETE SET NULL,
    created_at              TEXT NOT NULL,
    actor_user_id           TEXT REFERENCES users(id) ON DELETE SET NULL,
    supersede_reason        TEXT
                                CHECK (supersede_reason IS NULL OR supersede_reason IN ('reschedule', 'correction')),
    -- 0010_clock_extensions.sql's three columns, carried forward verbatim --
    -- this migration does not touch their semantics, only widens `kind`.
    target_clock_key        TEXT,
    extension_days          INTEGER CHECK (extension_days IS NULL OR extension_days > 0),
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

INSERT INTO case_milestones_new_0011
    (id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id,
     supersede_reason, target_clock_key, extension_days, written_agreement_ref)
SELECT id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id,
       supersede_reason, target_clock_key, extension_days, written_agreement_ref
FROM case_milestones;

DROP TABLE case_milestones;
ALTER TABLE case_milestones_new_0011 RENAME TO case_milestones;

CREATE INDEX IF NOT EXISTS ix_case_milestones_case ON case_milestones(case_id, kind, occurred_on);
CREATE INDEX IF NOT EXISTS ix_case_milestones_live ON case_milestones(case_id) WHERE superseded_by IS NULL;
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
-- END 0011_reconsideration_vote.sql
-- =============================================================================
