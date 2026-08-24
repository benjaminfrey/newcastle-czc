-- =============================================================================
-- Newcastle Permit Review — 0014_criteria_kind.sql
--
-- W6 task: "the criteria set + the applicability gate". Rebuilds `rules`
-- (SQLite CHECK constraints and column additions both require a table
-- rebuild; 0001_init.sql's `rules` DDL is otherwise untouched — see
-- CONTRACT.md's own rule that a shipped migration is never edited, only
-- superseded by a new numbered file). `rules` carries zero rows in every
-- checkout as of this migration (engine/ was explicitly "LATER" through
-- W5 — CONTRACT.md §1.2), and criteria_set_rules/findings_nodes/conditions
-- (the three tables with an FK to rules.id) are equally empty, so this is
-- a schema-only change: nothing is migrated, nothing can be lost.
--
-- Two changes, bundled because both need the same rebuild:
--
-- 1. `kind`'s CHECK widens from the five placeholder values 0001_init.sql
--    guessed at before any real rule existed
--    ('dimensional','use_permission','narrative','procedural','referenced')
--    to ALSO allow the taxonomy the W6 task brief specifies for a
--    lifted-from-prose statutory standard: 'numeric' (a quantifiable
--    comparison), 'boolean' (a yes/no fact), 'judgement' (an evaluative
--    standard — "undue", "unreasonable", "adequate", ... — that can only
--    ever render as a question to the Board, never a computed verdict).
--    The original five are KEPT, not replaced: 'dimensional' and
--    'use_permission' are what an Article 2 rule (a future, disjoint
--    population of this same table) will need, and dropping them here
--    would be exactly the kind of narrowing CONTRACT.md §7.4 warns against
--    -- picking a value nothing yet requires picking.
--
-- 2. Four new columns, all with safe defaults so the widen is purely
--    additive: `applicability_json` (the three-valued predicate struct —
--    engine/predicates.py; defaults to {"op":"always"}, i.e. "no gate"),
--    `exceptions_json` (an array of exception/waiver notes the review
--    engine's escape hatch must check BEFORE any disposition — empty by
--    default; none of the 21 subdivision standards this migration's rows
--    will carry textually name an exception, but a future Article 6
--    Shoreland rule will), `mandates_condition_json` (nullable — set only
--    on the one rule, art7.12.f.1.n Flood Areas, that mandates a specific
--    condition of approval; NULL means "no mandated condition"),
--    `judgement_tells_json` (the array of tell words that triggered a
--    'judgement' classification, e.g. ["undue"] — empty for every other
--    kind; kept on the row so the classification is inspectable in the
--    data itself, per the task brief's "decided at RULESET BUILD TIME so
--    it is inspectable in the data, not recomputed at review time").
--
-- Verified safe against an FK-enabled connection with dependent (empty)
-- tables still referencing rules(id) — SQLite's standard 12-step rebuild
-- (create the new table under a temp name, drop the old one, rename)
-- works inside a single transaction with foreign_keys=ON as long as no
-- row would violate, which is trivially true here (0 rows everywhere).
-- =============================================================================

CREATE TABLE rules_new (
    id                        TEXT PRIMARY KEY,
    ruleset_id                TEXT NOT NULL REFERENCES rulesets(id) ON DELETE CASCADE,
    rule_key                  TEXT NOT NULL,              -- 'art2.d1.lot_dimensions.width'
    district_key              TEXT,                       -- NULL = applies regardless of district
    field_def_id              TEXT REFERENCES field_defs(id) ON DELETE SET NULL,
    kind                      TEXT NOT NULL CHECK (kind IN
                                  ('dimensional','use_permission','narrative','procedural',
                                   'referenced','numeric','boolean','judgement')),
    title                     TEXT NOT NULL,
    code_text                 TEXT NOT NULL,              -- VERBATIM Code language; never paraphrased here
    test_json                 TEXT,                       -- machine-checkable form, when one exists
    citation_json             TEXT NOT NULL,              -- §5.2 Citation struct
    prompt_hint               TEXT,
    -- --- added 0013 (W6: the criteria set + the applicability gate) -----
    applicability_json        TEXT NOT NULL DEFAULT '{"op":"always"}',
                                                           -- engine/predicates.py three-valued gate struct
    exceptions_json           TEXT NOT NULL DEFAULT '[]', -- [] unless the Code text names an exception/waiver
    mandates_condition_json   TEXT,                       -- NULL, or {"text": "...", "fires": "..."} verbatim
    judgement_tells_json      TEXT NOT NULL DEFAULT '[]', -- e.g. ["undue"] -- [] unless kind = 'judgement'
    -- ----------------------------------------------------------------------
    unresolved                INTEGER NOT NULL DEFAULT 0 CHECK (unresolved IN (0,1)),
    sort_order                INTEGER NOT NULL DEFAULT 0,
    created_at                TEXT NOT NULL,
    actor_user_id             TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (ruleset_id, rule_key)
);

INSERT INTO rules_new (
    id, ruleset_id, rule_key, district_key, field_def_id, kind, title, code_text,
    test_json, citation_json, prompt_hint, unresolved, sort_order, created_at, actor_user_id
)
SELECT
    id, ruleset_id, rule_key, district_key, field_def_id, kind, title, code_text,
    test_json, citation_json, prompt_hint, unresolved, sort_order, created_at, actor_user_id
FROM rules;

DROP TABLE rules;
ALTER TABLE rules_new RENAME TO rules;

CREATE INDEX IF NOT EXISTS ix_rules_district ON rules(ruleset_id, district_key, sort_order);
