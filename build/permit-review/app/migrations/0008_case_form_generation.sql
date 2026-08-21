-- =============================================================================
-- Newcastle Permit Review — 0008_case_form_generation.sql
--
-- W4 task: "the operator confirm UI" (app/extraction.py, app/routes/extraction.py).
-- The task brief is explicit that an UNKNOWN form generation "MUST FAIL
-- LOUDLY: every field to the worklist, a banner on the case" — this app has
-- no home anywhere for the fact "this case's intake form was recognized as
-- Gen-1 / Gen-2 / could not be identified at all" until now. Detecting the
-- generation (the literal "OFFICE ADMINSTRATION USE ONLY" typo fingerprint
-- for Gen-1, the "PLANNING APPLICATION" + version-stamp fingerprint for
-- Gen-2) is a SEPARATE, not-yet-built task — this migration only adds the
-- schema home the confirm-UI banner reads; it does not implement detection
-- and writes no rows.
--
-- Case-level (not per-document): a case is reviewed as one application, and
-- the task brief's own wording ("a banner on the case") frames this as a
-- case-wide fact, not a per-document one — a case with a Gen-1 native form
-- plus scanned attachments is still, as a whole, "a Gen-1 case."
--
-- Purely additive: a new NULLABLE column with its own CHECK, matching
-- 0004/0005/0007's established pattern for this kind of change. NULL means
-- "not yet run / not applicable" (e.g. every scratch case seeded before
-- detection exists) and renders NO banner — only the explicit value
-- 'unknown' does. This is deliberate: NULL and 'unknown' are NOT the same
-- fact. NULL is "nobody has looked"; 'unknown' is "detection ran and could
-- not identify the generation" (CONTRACT.md §1 S7 — an honest, collected
-- ambiguity, never guessed at) — only the latter is loud.
-- =============================================================================

ALTER TABLE cases ADD COLUMN form_generation TEXT
    CHECK (form_generation IS NULL OR form_generation IN ('gen1', 'gen2', 'unknown'));

-- =============================================================================
-- END 0008_case_form_generation.sql
-- =============================================================================
