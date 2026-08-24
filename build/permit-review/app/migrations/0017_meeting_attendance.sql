-- =============================================================================
-- Newcastle Permit Review — 0017_meeting_attendance.sql
--
-- W7 task: "the meeting model -- disclosures, completeness, board members,
-- outcome." Read against the nine real Findings of Fact & Conclusions of Law
-- in `docs/Findings of Fact and Conclusions of Law/` (four DRAFTs, four
-- ADOPTED, plus Shattuck's per-standard adopted final), most of this ground
-- turned out to be ALREADY MODELED -- 0001_init.sql built "the full v1
-- schema" up front, and `motions`, `decisions`, and `conflict_disclosures`
-- (CONTRACT.md §3.5's 23-table list) were already there, unused by any code,
-- waiting for this workflow:
--
--   - conflict disclosures      -> conflict_disclosures (0001_init.sql)
--   - completeness determination -> motions WHERE kind = 'completeness'
--                                    (0001_init.sql's motions.kind CHECK
--                                    already lists it; the real Shattuck
--                                    adopted final's "Complete Application"
--                                    motion is exactly one motions row)
--   - the case outcome           -> decisions.outcome (0001_init.sql)
--
-- ONE gap remained: nothing recorded WHO WAS AT THE MEETING. The real
-- documents never print an explicit "Present:" roster (grepped for
-- "Present"/"Attend"/"Absent" across all nine -- zero hits) -- attendance is
-- only ever visible INDIRECTLY, through vote tallies and the signature
-- block. That indirection is the tell that a table was missing: Blood and
-- Sons's adopted final signs FIVE members (Ben Frey, Lucas Kostenbader,
-- Kevin Houghton, Scott Shott, Wanda Wilcox) against SEVEN sitting seats,
-- matching its "five (5) in favor" vote -- two members simply were not
-- there. render/case_findings.py's existing `_signature_render_node()`
-- signs EVERY currently-sitting board_member unconditionally, which is
-- right for a pre-meeting DRAFT (nobody's roll call has happened yet, so
-- anyone sitting could be the one who shows up and signs) and wrong for a
-- case that actually HAD a meeting with absences -- there was no recorded
-- fact to tell the difference. This migration adds that fact.
--
-- attendance -- one row per (case, board_member) roll call, mirroring
-- conflict_disclosures's own shape (same UNIQUE pair, same "the app records
-- what happened, never infers it" posture). `present` defaults 1 because
-- the ordinary reason to write a row at all is "this member is here";
-- recording an absent member is equally legitimate (a quorum question
-- someone wants on file) but never assumed.
--
-- OUTCOME VOCABULARY -- NOT CHANGED. The task brief that commissioned this
-- migration asked for an outcome set of "approve / approve with conditions
-- / deny / table / withdraw." decisions.outcome (0001_init.sql) already
-- has this: 'approved' / 'approved_with_conditions' / 'denied' / 'withdrawn'
-- / 'continued'. The one word that looks different -- 'continued' where the
-- brief says "table" -- is deliberately kept rather than renamed: Midcoast
-- Solar's real record uses exactly this word ("continued to the March 21,
-- 2024 Planning Board meeting where it was closed"), and "table" a motion
-- (Robert's Rules: set aside indefinitely) is a different, narrower act
-- from continuing a case to a date-certain future meeting, which is what a
-- Planning Board actually does with an unfinished application. Renaming a
-- term that is already grounded in this Town's own real record, to match a
-- generic word with no occurrence in any of the nine documents, would be
-- the wrong direction (CONTRACT.md's "never guess a legal value" cuts
-- against silently swapping settled house vocabulary too). motions.outcome
-- separately already has 'tabled' as one of its four PARLIAMENTARY results
-- ('carried'/'failed'/'tabled'/'withdrawn') for an individual motion -- a
-- different concept (a motion can be tabled without the whole case being
-- disposed of), also already correct, also untouched here.
-- =============================================================================
--
-- NUMBERING NOTE: originally drafted as 0015_meeting_attendance.sql; renumbered
-- to 0017 after discovering, mid-build, two concurrently-built sibling W7
-- migrations already claiming 0015 (0015_motion_conclusion.sql -- the
-- motion -> findings_nodes conclusion link) and 0016
-- (0016_motion_disposition_discussion.sql -- `motions.discussion` +
-- `motions.disposition`, the latter using the literal outcome words
-- 'approve'/'approve_with_conditions'/'deny'/'table'/'withdraw' on the
-- MOTION). Those two migrations are a different W7 unit's work ("the
-- meeting UI" / conclusion-recording) and are left untouched here -- same
-- "adapt to the other build's architecture rather than fight it" posture
-- 0013_findings_tree.sql's own header already established for exactly this
-- situation. `decisions.outcome` (the CASE's disposition, distinct from a
-- MOTION's `disposition`) keeps its own vocabulary unrenamed regardless --
-- see this file's own outcome-vocabulary note below -- so integration of
-- these two parallel efforts needs a small bridge
-- ('table'->'continued', etc.) wherever a carried decision-motion's
-- `disposition` is turned into a `decisions.outcome` row; that bridge is
-- flagged for the orchestrator/integration pass, not resolved by guessing
-- here.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- attendance — the roll call for one case's meeting(s). CONTRACT.md §3.4/§3.5
-- Present is recorded per board_member per case; a member with no row here
-- for a given case is simply unrecorded, not assumed absent OR present --
-- exactly conflict_disclosures's own "absence of a record is not a finding"
-- posture, and the same reason `_signature_render_node()` (render/
-- case_findings.py) falls back to "every sitting member" when this table
-- has zero rows for a case, rather than rendering an empty signature block.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    board_member_id     TEXT NOT NULL REFERENCES board_members(id) ON DELETE RESTRICT,
    present             INTEGER NOT NULL DEFAULT 1 CHECK (present IN (0,1)),
    role_note           TEXT,               -- e.g. 'arrived late', 'alternate seated for J. Doe'
    recorded_at         TEXT NOT NULL,      -- when the roll call happened (ISO-8601 UTC)
    created_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (case_id, board_member_id)
);
CREATE INDEX IF NOT EXISTS ix_attendance_case ON attendance(case_id);
CREATE INDEX IF NOT EXISTS ix_attendance_present ON attendance(case_id) WHERE present = 1;

-- =============================================================================
-- END 0017_meeting_attendance.sql
-- =============================================================================
