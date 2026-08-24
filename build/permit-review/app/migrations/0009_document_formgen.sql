-- =============================================================================
-- Newcastle Permit Review — 0009_document_formgen.sql
--
-- W4 task: "form-generation and module-set detection" (ingest/formgen.py).
-- Implements the DOCUMENT-level home CONTRACT.md's task brief calls for:
-- "Persist generation, version_stamp and module_set onto the documents row
-- (columns exist from W1; add a migration if not)." They did not exist —
-- 0001_init.sql's `documents` table (CONTRACT.md §3.6) has no column for
-- any of this — so this migration adds them, following 0004/0007/0008's
-- established purely-additive, nullable-column pattern.
--
-- NOT to be confused with 0008_case_form_generation.sql's
-- `cases.form_generation` column (a separate, concurrently-built task's
-- CASE-level rollup banner, read by app/extraction.py's not-yet-built
-- case_form_generation()). This migration is the PER-DOCUMENT fact that
-- rollup is computed FROM: one case can carry several documents (a native
-- Gen-2 cover sheet plus a scanned attachment, say), and ingest/formgen.py's
-- detect_generation() runs once per document, never once per case. Two
-- concurrently-authored migrations briefly both numbered 0008 existed in
-- this directory (case_form_generation, field_defs_worklist) — app/db.py's
-- migrate() applies app/migrations/*.sql in lexical (filename) order, not
-- numeric order, so two files sharing a number was a naming collision
-- risk, not a runtime one; this file was numbered 0009 at the time to stay
-- unambiguous, because both 0008 files landed first. The collision was
-- resolved 2026-08-21 by renumbering field_defs_worklist to 0012 (see that
-- file's own history note) — case_form_generation kept 0008 since it
-- landed there first and nothing outside this comment ever referenced the
-- other file's old name.
--
-- doc_role vs generation: a document's doc_role/kind (0004_page_triage.sql,
-- app/routes/documents.py) is a human/upload-time classification of WHAT
-- the document is (an application form vs. a plan sheet vs. a deed).
-- `generation` is a DIFFERENT, orthogonal, DETECTED fact about a
-- doc_role='application_form' document specifically: WHICH of the two known
-- Newcastle permit-application form layouts it is (or 'unknown' if neither
-- fingerprint matched — CONTRACT.md §1 S7, never guessed, never defaulted
-- to 'gen1'). A non-form document (a deed, a plan sheet) is simply never
-- run through detect_generation() at all, so its generation/version_stamp/
-- module_set columns stay NULL — NULL here means "not applicable / not yet
-- run," exactly the same reading 0008_case_form_generation.sql gives its
-- own NULL (distinct from the explicit, loud 'unknown').
--
-- module_set is TEXT holding a JSON array of module_key strings (e.g.
-- '["cover","subdivision_form"]'), sorted, so two equal sets always
-- serialize identically. Empty JSON array '[]' for a Gen-1 document (Gen-1
-- is a fixed, non-modular form — see ingest/formgen.py) or for 'unknown'.
-- Kept as a JSON TEXT column rather than a join table: this is exactly the
-- kind of small, fixed-vocabulary, read-mostly set CONTRACT.md's own
-- provenance_json / required_json / footnote_refs columns already use this
-- pattern for elsewhere in 0001_init.sql, and a document's module set is
-- never queried by individual module membership at this phase.
--
-- Plain ALTER TABLE ADD COLUMN — `documents` has zero real rows in every
-- checkout so far (same "no existing row to reclassify" situation as every
-- prior additive migration), so a CHECK-bearing new column needs no table
-- rebuild (SQLite allows ADD COLUMN with a CHECK; it does not allow ADD
-- COLUMN with a non-constant DEFAULT that could conflict with an existing
-- CHECK on other columns, which is not the case here).
-- =============================================================================

ALTER TABLE documents ADD COLUMN generation TEXT
    CHECK (generation IS NULL OR generation IN ('gen1', 'gen2', 'unknown'));

ALTER TABLE documents ADD COLUMN version_stamp TEXT;

ALTER TABLE documents ADD COLUMN module_set TEXT;  -- JSON array of module_key strings, sorted

-- Evidentiary trail alongside the verdict — CONTRACT.md's own framing rule
-- ("Honest blanks beat confident guesses") and findings_nodes.provenance_json
-- precedent both say a detected fact should carry HOW it was determined, not
-- just the bare answer, so an operator (or a later re-run) can see why a
-- document was called gen1/gen2/unknown without re-running detection.
ALTER TABLE documents ADD COLUMN formgen_confidence TEXT
    CHECK (formgen_confidence IS NULL OR formgen_confidence IN ('high', 'medium', 'low'));
ALTER TABLE documents ADD COLUMN formgen_evidence_json TEXT;  -- JSON array, see ingest/formgen.py

CREATE INDEX IF NOT EXISTS ix_documents_generation ON documents(case_id, generation);

-- =============================================================================
-- END 0009_document_formgen.sql
-- =============================================================================
