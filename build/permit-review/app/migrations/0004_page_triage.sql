-- =============================================================================
-- Newcastle Permit Review — 0004_page_triage.sql
--
-- W3 task: "uploads, content-addressed blobs, page census and tiering"
-- (ingest/triage.py, app/blobs.py, app/routes/documents.py). Implements
-- CONTRACT.md §2's `ingest/` home ("upload, PDF page split") and §3.6's
-- `documents` / `pages` tables, extended with the columns this workflow's
-- task brief calls for that 0001_init.sql's schema has no home for.
--
-- Purely additive. Does NOT touch `cases`, `case_milestones`, or any other
-- table another concurrent W3 task owns (verified against the migrations
-- present in this directory at the time this file was written: 0001_init.sql,
-- 0002_case_tracking.sql, 0003_case_lifecycle.sql — none of which reach
-- `documents` or `pages`). Every column below is NULLABLE with a CHECK that
-- explicitly allows NULL, so it is safe to add regardless of migration order
-- and never conflicts with 0001_init.sql's own CHECKs/triggers on these two
-- tables (documents.source_priority's canonical-value trigger is untouched).
--
-- WHY A MIGRATION (0001_init.sql's own comment says later workflows should
-- "add data, not columns"): there is no existing column anywhere for a
-- page's per-page triage census (char/image counts, rotation, a content
-- hash for vision-result caching, the A/B/C/D tier) or for the more granular
-- submission role (`doc_role`) this task's brief names. Encoding that into
-- an unstructured JSON blob would make the tier census / plan-sheet
-- detection this workflow exists to produce un-queryable, defeating the
-- point. This is the documented exception, not a casual schema churn.
--
-- doc_role vs. kind/source_priority: CONTRACT.md §3.6 already fixes
-- `documents.kind` to a 9-value enum with a DB trigger pinning
-- source_priority for kind IN (plan,survey,deed,form) to exactly
-- 100/90/80/40 — "the form is wrong, the plan governs." `doc_role` is a
-- STRICTLY ADDITIONAL, more granular descriptive tag layered on top (the
-- task brief's own 10-value vocabulary), never a replacement for kind or
-- source_priority; see app/routes/documents.py's DOC_ROLE_TO_KIND mapping
-- for how the two stay in sync at upload time.
-- =============================================================================

ALTER TABLE documents ADD COLUMN doc_role TEXT CHECK (doc_role IS NULL OR doc_role IN (
    'application_form', 'plan_sheet', 'survey', 'deed', 'engineer_letter',
    'applicant_narrative', 'staff_review', 'abutter_comment', 'state_permit', 'other'
));

-- Per-page triage census (ingest/triage.py). One row per PDF page, written
-- once at upload time; triage classifies pages, it does not read them (no
-- OCR/vision/LLM output is ever stored in these columns).
ALTER TABLE pages ADD COLUMN char_count      INTEGER CHECK (char_count IS NULL OR char_count >= 0);
ALTER TABLE pages ADD COLUMN image_count     INTEGER CHECK (image_count IS NULL OR image_count >= 0);
ALTER TABLE pages ADD COLUMN rotation        INTEGER CHECK (rotation IS NULL OR rotation IN (0, 90, 180, 270));
ALTER TABLE pages ADD COLUMN vector_path_count INTEGER CHECK (vector_path_count IS NULL OR vector_path_count >= 0);

-- Deterministic hash of the page's RENDERED content (fixed-DPI pixmap, see
-- ingest/triage.py) — NOT the raw PDF bytes. This is what lets a later
-- vision pass cache its result per page (CONTRACT.md ingest task brief:
-- "page_sha256 exists so later vision results can be cached per page").
ALTER TABLE pages ADD COLUMN page_sha256 TEXT;

-- The A/B/C/D triage tier (task brief §"YOUR TASK"):
--   A native     — char_count >= 200 and label-like tokens present
--   B hybrid     — 20 <= char_count < 200, OR text present with no label
--                  tokens (the "values with no labels" trap)
--   C scan       — char_count < 20
--   D plansheet  — page area > tabloid, OR high vector-line density, OR
--                  rotated (forces the owning document's source_priority to
--                  100 — see app/routes/documents.py)
ALTER TABLE pages ADD COLUMN tier TEXT CHECK (tier IS NULL OR tier IN ('A', 'B', 'C', 'D'));
ALTER TABLE pages ADD COLUMN has_label_tokens INTEGER CHECK (has_label_tokens IS NULL OR has_label_tokens IN (0, 1));
ALTER TABLE pages ADD COLUMN is_plansheet     INTEGER CHECK (is_plansheet IS NULL OR is_plansheet IN (0, 1));

CREATE INDEX IF NOT EXISTS ix_pages_tier ON pages(document_id, tier);
CREATE INDEX IF NOT EXISTS ix_pages_sha256 ON pages(page_sha256);

-- END 0004_page_triage.sql
