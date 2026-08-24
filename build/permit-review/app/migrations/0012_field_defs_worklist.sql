-- =============================================================================
-- Newcastle Permit Review — 0012_field_defs_worklist.sql
--
-- Renumbered from 0008_field_defs_worklist.sql (2026-08-21 reconciliation
-- pass): two independently-authored migrations both landed as "0008"
-- (this one and 0008_case_form_generation.sql — see that file's own
-- history note, and 0009_document_formgen.sql's comment, which already
-- flagged the pair as "a naming collision risk, not a runtime one" back
-- when it happened). Renumbering to 0012 (after the highest number then
-- in use, 0011) removes the ambiguity outright rather than leaving two
-- files sharing a prefix relying on lexical tie-breaking. Purely a
-- filename change — the DDL below is byte-identical to what shipped as
-- 0008_field_defs_worklist.sql; any database that already recorded that
-- name in schema_migrations needs a fresh (or manually re-keyed) DB, since
-- app/db.py:migrate() treats a changed filename as a new migration.
--
-- W4 task: "the absence worklist" (ingest/worklist.py). CONTRACT.md §3.6
-- already gives field_defs a full row shape for an ARTICLE-2 DIMENSIONAL
-- standard (panel_key/panel_title/label/unit/applicability/citation_json,
-- seeded per-district). This workflow reuses the SAME table for a second,
-- disjoint population: the ~23 case-level fields (district_key IS NULL)
-- that appear in a real decision's Project Information / Site Information /
-- Application Information blocks (Applicant, Owner Deed Reference, Tax
-- Lot, Core Zoning District, Proposed Use, ...) — see ingest/worklist.py's
-- FIELD_DEF_SEED, derived verbatim from the real Findings of Fact & CoL
-- documents under docs/Findings of Fact and Conclusions of Law/.
--
-- Two things that population needs and 0001_init.sql's DDL has no column
-- for:
--
-- 1. WHERE a value must come from, when the application is silent on it —
--    the worklist's own grouping key (CONTRACT.md task brief: "Registry of
--    Deeds / Assessing · GIS or map · a plan or survey sheet · staff
--    determination · post-submittal record · the applicant"). Called
--    `source_category` here (not `panel_key`, which already means
--    something else — a citation's panel, e.g. "LOT DIMENSIONS").
--
-- 2. WHICH form generation structurally has a field for this label at all
--    (task brief's own central example: "the Gen-1 form has no deed
--    field, so the deed reference comes from the Registry" — but GEN-2's
--    Cover Sheet DOES print `Deed Book: ___ Page: ___`, verified against
--    the real M002/L053 Dalton and M011/L046-A Morrissey Gen-2 Cover
--    Sheets under docs/). A single flat `typically_absent` flag cannot
--    represent that split, so this is TWO columns, one per generation,
--    not one — see CONTRACT.md §1 S7 ("no silent guessing"): collapsing
--    them into one flag would force a guess for whichever generation the
--    flag doesn't match. A field absent from BOTH known generations
--    (`Existing Development`, `Documents Included` — neither form asks for
--    either verbatim; both are staff-compiled) carries both flags = 1.
--    A field on neither list yet (an unrecognized THIRD generation — see
--    the task brief's "UNKNOWN GENERATION MUST FAIL LOUDLY") is simply not
--    scored against either column; ingest/worklist.py's
--    case_form_generation() returning "unknown" is the code-level guard,
--    not a DB constraint, because no CHECK here can see which generation a
--    given CASE turned out to be.
--
-- Plain ALTER TABLE ADD COLUMN — field_defs has zero rows before
-- ingest/worklist.py's seed_field_defs() ever runs (same "no existing row
-- to reclassify" situation as every prior additive migration in this
-- directory), so a CHECK-bearing new column needs no table rebuild.
-- =============================================================================

ALTER TABLE field_defs ADD COLUMN source_category TEXT CHECK (source_category IS NULL OR source_category IN (
    'applicant', 'registry', 'gis', 'plan_survey', 'staff', 'post_submittal'
));

ALTER TABLE field_defs ADD COLUMN typically_absent_gen1 INTEGER NOT NULL DEFAULT 0
    CHECK (typically_absent_gen1 IN (0, 1));
ALTER TABLE field_defs ADD COLUMN typically_absent_gen2 INTEGER NOT NULL DEFAULT 0
    CHECK (typically_absent_gen2 IN (0, 1));

-- The absence worklist's own hot path (ingest/worklist.py:worklist()) always
-- starts from "every case-level field_def for this ruleset" before joining
-- out to field_candidates/field_values per case.
CREATE INDEX IF NOT EXISTS ix_field_defs_case_level
    ON field_defs(ruleset_id, sort_order) WHERE district_key IS NULL;

-- =============================================================================
-- END 0012_field_defs_worklist.sql
-- =============================================================================
