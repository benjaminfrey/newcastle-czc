-- =============================================================================
-- Newcastle Permit Review — 0015_motion_conclusion.sql
--
-- W7 task: "motions, votes, and amendments -- the ONLY path to a conclusion."
-- findings_nodes.conclusion (0001_init.sql) already carries the framing-rule
-- CHECK ("Only a HUMAN may set a conclusion") -- what was still missing is
-- the structural link FROM a motion TO the node it concludes, so that link
-- can be verified in the schema, not just trusted from application code.
--
-- Rebuilds `motions` (0001_init.sql) -- SQLite CHECK constraints referencing
-- other columns, and new FOREIGN KEYs, both require a table rebuild; every
-- column 0001_init.sql defined is carried forward byte-for-byte. Same
-- "temp name -> copy -> DROP original -> RENAME" recipe as every prior
-- rebuild in this migration set (0002/0003/0005/0006/0007/0010/0011/0013/
-- 0014). Verified safe: `motions` carries zero rows on every checkout to
-- date (W7 is the first workflow that writes to it), so nothing is migrated
-- and nothing can be lost.
--
-- Three new columns, all nullable so the widen is purely additive:
--
--   findings_node_id    -- which findings_nodes row this motion concludes.
--                          NULL for a motion that is not about one specific
--                          node (the completeness motion, the conditions
--                          vote, the adoption-of-the-whole-document motion,
--                          the final decision motion). CHECK below requires
--                          kind='findings' whenever this is set.
--
--   proposed_conclusion  -- 'met' | 'not_met' | 'n_a' -- the value that
--                          engine/meeting.py:apply_motion() writes to
--                          findings_nodes.conclusion IF AND ONLY IF this
--                          motion's own `outcome` is 'carried'. Drafted
--                          alongside `text` (CONTRACT.md's own real-document
--                          evidence -- the Shattuck adopted final -- shows
--                          every per-standard motion phrased as the
--                          affirmative "to conclude ... is consistent",
--                          never a pre-written negative; a motion that fails
--                          leaves the node unresolved for a follow-up
--                          motion, rather than the app guessing the inverse
--                          conclusion from a bare "failed").
--
--   applied_node_id      -- write-once, stamped in the SAME transaction as
--                          the findings_nodes UPDATE that actually records
--                          the conclusion (engine/meeting.py:apply_motion()).
--                          This is the audit anchor: a motion can be
--                          "carried" (a vote fact) without yet being
--                          "applied" (its conclusion actually written) for
--                          at most the width of one transaction, and once
--                          applied_node_id is set, a second apply_motion()
--                          call on the same motion is refused (CHECK's own
--                          "outcome='carried'" requirement plus the
--                          application-code idempotency guard together mean
--                          a motion can never write two conclusions, and a
--                          node can never receive a conclusion from a motion
--                          that did not carry).
--
--   applied_at           -- ISO-8601 UTC timestamp, set together with
--                          applied_node_id (CHECK enforces both-or-neither).
--                          Distinct from `voted_at` on purpose: voted_at is
--                          when the Board voted; applied_at is when that
--                          vote's conclusion was actually written to the
--                          node -- ordinarily the same instant (one
--                          transaction), but kept as two columns because
--                          they answer two different questions for anyone
--                          auditing the record later.
--
-- Four new CHECKs, all narrow and mechanical (CONTRACT.md's own stated
-- preference for what belongs in DDL vs. Python -- see 0013's header
-- comment on the provenance CHECK it deliberately did NOT add):
--
--   1. findings_node_id IS NULL OR kind = 'findings'
--        -- a node-linked motion is always a Findings/Conclusions-of-Law
--           motion; the completeness/conditions/decision motions never
--           reference a specific findings_nodes row.
--   2. proposed_conclusion IS NULL OR findings_node_id IS NOT NULL
--        -- a proposed conclusion is meaningless without a node to attach it to.
--   3. applied_node_id IS NULL OR (proposed_conclusion IS NOT NULL AND outcome = 'carried')
--        -- THE STRUCTURAL PROOF: a motion can only ever be "applied" if it
--           both proposed a conclusion AND carried. There is no row shape in
--           this table where applied_node_id is set on a motion that failed,
--           was tabled, was withdrawn, or never proposed a conclusion at all.
--   4. (applied_node_id IS NULL) = (applied_at IS NULL)
--        -- both or neither; no half-applied motion.
-- =============================================================================

CREATE TABLE motions_new_0015 (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    kind            TEXT NOT NULL CHECK (kind IN
                        ('completeness','findings','conditions','decision','continuance','other')),
    text            TEXT NOT NULL,              -- the motion language, drafted
    moved_by        TEXT REFERENCES board_members(id) ON DELETE SET NULL,
    seconded_by     TEXT REFERENCES board_members(id) ON DELETE SET NULL,
    votes_yes       INTEGER CHECK (votes_yes IS NULL OR votes_yes >= 0),
    votes_no        INTEGER CHECK (votes_no IS NULL OR votes_no >= 0),
    votes_abstain   INTEGER CHECK (votes_abstain IS NULL OR votes_abstain >= 0),
    outcome         TEXT CHECK (outcome IS NULL OR outcome IN ('carried','failed','tabled','withdrawn')),
    voted_at        TEXT,
    recorded_by     TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL,

    -- NEW (0015) -- the motion -> findings_nodes link.
    findings_node_id    TEXT REFERENCES findings_nodes(id) ON DELETE SET NULL,
    proposed_conclusion  TEXT CHECK (proposed_conclusion IS NULL
                            OR proposed_conclusion IN ('met','not_met','n_a')),
    applied_node_id      TEXT REFERENCES findings_nodes(id) ON DELETE SET NULL,
    applied_at            TEXT,

    -- Carried forward verbatim from 0001_init.sql --
    -- an outcome is a recorded human act
    CHECK (outcome IS NULL OR (recorded_by IS NOT NULL AND voted_at IS NOT NULL)),

    -- NEW (0015) --
    CHECK (findings_node_id IS NOT NULL OR proposed_conclusion IS NULL),
    CHECK (findings_node_id IS NULL OR kind = 'findings'),
    CHECK (applied_node_id IS NULL OR (proposed_conclusion IS NOT NULL AND outcome = 'carried')),
    CHECK ((applied_node_id IS NULL) = (applied_at IS NULL))
);

INSERT INTO motions_new_0015
    (id, case_id, sort_order, kind, text, moved_by, seconded_by,
     votes_yes, votes_no, votes_abstain, outcome, voted_at, recorded_by,
     created_at, actor_user_id)
SELECT
    id, case_id, sort_order, kind, text, moved_by, seconded_by,
    votes_yes, votes_no, votes_abstain, outcome, voted_at, recorded_by,
    created_at, actor_user_id
FROM motions;

DROP TABLE motions;
ALTER TABLE motions_new_0015 RENAME TO motions;

CREATE INDEX IF NOT EXISTS ix_motions_case ON motions(case_id, sort_order);
CREATE INDEX IF NOT EXISTS ix_motions_findings_node ON motions(findings_node_id)
    WHERE findings_node_id IS NOT NULL;

-- =============================================================================
-- END 0015_motion_conclusion.sql
-- =============================================================================
