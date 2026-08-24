-- =============================================================================
-- Newcastle Permit Review — 0013_findings_tree.sql
--
-- W6 task: "the findings tree" (engine/findings.py). findings_nodes already
-- existed in full per CONTRACT.md §3.6 (0001_init.sql) -- the versioned tree,
-- the write-once superseded_by trigger, unresolved/board_question/
-- provenance_json were all already there and untouched by any code (grep
-- confirms: before this migration, findings_nodes had zero readers or
-- writers anywhere in app/ or engine/). This migration is additive to that
-- table, not a redesign, adding exactly the four columns engine/findings.py
-- needs that 0001_init.sql did not yet carry:
--
--   quoted_standard_text -- the VERBATIM Code standard text this node quotes,
--                           kept SEPARATE from `body` (the finding prose
--                           beneath it) because the one formatting rule that
--                           is ~80% of every real Newcastle decision is that
--                           the quoted standard prints FLUSH LEFT and the
--                           finding prints INDENTED underneath it -- two
--                           different printed treatments need two different
--                           stored strings, not one column doing both jobs.
--                           Verbatim: never regenerated, reworded or
--                           summarised by this module (mirrors rules.code_text's
--                           own "VERBATIM Code language; never paraphrased
--                           here" comment two tables over).
--
--   finding_source        -- 'engine' | 'model' | 'operator'. The W6 task
--                           brief: "finding_source must distinguish
--                           deterministic-engine output from model-drafted
--                           prose from operator text. A reader must always be
--                           able to tell which produced a sentence." NULL
--                           for nodes with no authored prose yet (a pure
--                           honest blank -- section headers, an unfilled
--                           question with only board_question set).
--
--   applicability_verdict -- 'true' | 'false' | 'unknown'. The (separately
--                           built) applicability gate's three-valued output
--                           for this node's standard: TRUE/FALSE it applies,
--                           or UNKNOWN -- and UNKNOWN never suppresses the
--                           node, it still renders and asks the Board. This
--                           is NOT the banned met/not_met Conclusion of Law
--                           (findings_nodes.conclusion, nullable, human-only,
--                           untouched by this migration) -- it answers "does
--                           this standard apply at all", not "is it met".
--
--   citation_display      -- a CACHE of app.citation.render(citation_json),
--                           written at the same time as citation_json so a
--                           reader of the row does not have to deserialize
--                           and re-render just to see what it cites. Per
--                           CONTRACT.md §5.1 ("Where a rendered string is
--                           persisted ... it is a cache ... any consumer
--                           re-renders rather than trusting it") this is
--                           NEVER the source of truth -- citation_json is,
--                           and engine/findings.py always derives
--                           citation_display FROM citation_json via
--                           app.citation.render(), never the other way
--                           round, never typed by a caller independently.
--
-- One new CHECK constraint: a node with a stated finding_source must carry
-- the body it is claiming authorship of (finding_source IS NULL OR body IS
-- NOT NULL). Additive -- no existing row can violate it, findings_nodes has
-- zero rows on every checkout to date.
--
-- A SECOND cross-column CHECK was drafted here first -- "a node carrying
-- EITHER quoted_standard_text or body must carry a non-trivial
-- provenance_json", enforcing 0001_init.sql's own comment ("A node with
-- prose and an empty provenance object is a bug") in DDL, not just prose --
-- and then DELIBERATELY DROPPED before this migration shipped: it broke
-- render/case_findings.py's already-written tests (tests/test_case_findings.py's
-- `_insert_node()` fixture defaults provenance_json to '{}' and several of
-- its rows carry `body` without overriding it), a concurrently-built W6
-- workflow (CONTRACT.md §1.2's engine/ + render/, the "draft document" task)
-- discovered mid-build in this same directory -- the same kind of parallel
-- construction BUILD-STATE.md's W5 section already documents once. Per that
-- entry's own resolution ("adapt to the other build's architecture rather
-- than fight it"), the DB-level half of this rule is not shipped; the exact
-- same requirement is enforced in Python instead, unconditionally, for
-- every call through engine/findings.py -- see
-- engine.findings.validate_provenance() and its callers in create_node()/
-- amend_node(), which raise ValidationError before any write for precisely
-- the case this CHECK would have caught. A raw SQL INSERT (as test
-- fixtures elsewhere in this repo already do for other tables) bypasses
-- Python validation regardless of whether this CHECK exists -- most of this
-- schema's business rules already work this way, DB CHECKs reserved for the
-- highest-value, narrowest invariants (the framing rule's conclusion
-- CHECKs, kept, below) rather than every rule this module enforces.
--
-- SQLite cannot add a CHECK that references another column via a plain
-- ALTER TABLE ADD COLUMN, so this follows the same "build the replacement
-- under a temporary name, copy, DROP the original, RENAME into place"
-- recipe 0002/0003/0005/0006/0007/0010/0011 already established for
-- case_milestones -- verified safe here too even though (unlike
-- case_milestones) another table, conditions.findings_node_id, holds a live
-- REFERENCES findings_nodes(id): with PRAGMA foreign_keys=ON and zero rows
-- in `conditions` (true on every checkout to date), DROP TABLE / RENAME
-- leaves that FK resolving correctly by table name, confirmed empirically
-- before writing this migration. Every column, CHECK, index and trigger
-- 0001_init.sql defined is carried forward byte-for-byte; nothing already
-- shipped is renamed, narrowed or removed.
-- =============================================================================

CREATE TABLE findings_nodes_new_0013 (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    case_review_id      TEXT REFERENCES case_reviews(id) ON DELETE SET NULL,
    parent_id           TEXT REFERENCES findings_nodes_new_0013(id) ON DELETE CASCADE,
    root_id             TEXT,                   -- stable identity across revisions
    revision            INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    superseded_by       TEXT REFERENCES findings_nodes_new_0013(id) ON DELETE SET NULL,
    sort_order          INTEGER NOT NULL DEFAULT 0,
    node_type           TEXT NOT NULL CHECK (node_type IN
                            ('section','required_review','finding','conclusion',
                             'condition_ref','question','note')),
    number_label        TEXT,                   -- '4.A.1', 'II.3'  -- as printed
    heading             TEXT,

    -- NEW (0013): the verbatim standard, printed flush left.
    quoted_standard_text TEXT,

    body                TEXT,                   -- the finding prose (facts, not verdicts) -- printed
                                                  -- indented beneath quoted_standard_text

    -- NEW (0013): who is answerable for `body`'s wording.
    finding_source      TEXT CHECK (finding_source IS NULL
                            OR finding_source IN ('engine','model','operator')),

    rule_id             TEXT REFERENCES rules(id) ON DELETE SET NULL,
    criteria_set_id     TEXT REFERENCES criteria_sets(id) ON DELETE SET NULL,
    field_value_id      TEXT REFERENCES field_values(id) ON DELETE SET NULL,
    citation_json       TEXT,                   -- §5.2 struct; NEVER a rendered string

    -- NEW (0013): cache of app.citation.render(citation_json) -- §5.1 cache,
    -- never the source of truth.
    citation_display    TEXT,

    -- NEW (0013): the applicability gate's three-valued verdict for this
    -- node -- NOT the banned met/not_met Conclusion of Law.
    applicability_verdict TEXT CHECK (applicability_verdict IS NULL
                            OR applicability_verdict IN ('true','false','unknown')),

    conclusion          TEXT CHECK (conclusion IS NULL OR conclusion IN ('met','not_met','n_a')),
    conclusion_by       TEXT REFERENCES users(id) ON DELETE SET NULL,
    conclusion_at       TEXT,
    unresolved          INTEGER NOT NULL DEFAULT 1 CHECK (unresolved IN (0,1)),
    board_question      TEXT,                   -- first-person question put to the Board
    placeholder         TEXT,                   -- the literal 'TBD...' text as it prints
    provenance_json     TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL,

    -- Carried forward verbatim from 0001_init.sql --
    -- Only a HUMAN may set a conclusion. The app writes NULL. (framing rule)
    CHECK (conclusion IS NULL OR (conclusion_by IS NOT NULL AND conclusion_at IS NOT NULL)),
    -- A resolved node has either a conclusion or an explicit reason to be blank.
    CHECK (unresolved = 1 OR conclusion IS NOT NULL OR node_type IN ('section','note','required_review')),

    -- NEW (0013) --
    -- A stated finding_source is a claim of authorship over `body`; it must
    -- have a body to be the author of. (The companion "prose requires
    -- non-trivial provenance" rule is enforced in Python -- see this
    -- migration's header comment for why.)
    CHECK (finding_source IS NULL OR body IS NOT NULL)
);

INSERT INTO findings_nodes_new_0013
    (id, case_id, case_review_id, parent_id, root_id, revision, superseded_by, sort_order,
     node_type, number_label, heading, body, rule_id, criteria_set_id, field_value_id,
     citation_json, conclusion, conclusion_by, conclusion_at, unresolved, board_question,
     placeholder, provenance_json, created_at, actor_user_id)
SELECT
     id, case_id, case_review_id, parent_id, root_id, revision, superseded_by, sort_order,
     node_type, number_label, heading, body, rule_id, criteria_set_id, field_value_id,
     citation_json, conclusion, conclusion_by, conclusion_at, unresolved, board_question,
     placeholder, provenance_json, created_at, actor_user_id
FROM findings_nodes;

DROP TABLE findings_nodes;
ALTER TABLE findings_nodes_new_0013 RENAME TO findings_nodes;

CREATE INDEX IF NOT EXISTS ix_findings_current ON findings_nodes(case_id, sort_order)
    WHERE superseded_by IS NULL;
CREATE INDEX IF NOT EXISTS ix_findings_parent ON findings_nodes(parent_id, sort_order);
CREATE INDEX IF NOT EXISTS ix_findings_root ON findings_nodes(root_id, revision DESC);
CREATE INDEX IF NOT EXISTS ix_findings_unresolved ON findings_nodes(case_id)
    WHERE unresolved = 1 AND superseded_by IS NULL;

-- NEW (0013): the Board-facing "what still needs a human look" queue --
-- the applicability gate's whole reason for being three-valued rather than
-- boolean is that UNKNOWN must never silently vanish (W6 brief).
CREATE INDEX IF NOT EXISTS ix_findings_verdict_unknown ON findings_nodes(case_id)
    WHERE applicability_verdict = 'unknown' AND superseded_by IS NULL;

DROP TRIGGER IF EXISTS trg_findings_supersede_once;
CREATE TRIGGER trg_findings_supersede_once
BEFORE UPDATE OF superseded_by ON findings_nodes
WHEN OLD.superseded_by IS NOT NULL AND NEW.superseded_by IS NOT OLD.superseded_by
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.6: findings_nodes.superseded_by is write-once; insert a new revision');
END;

-- =============================================================================
-- END 0013_findings_tree.sql
-- =============================================================================
