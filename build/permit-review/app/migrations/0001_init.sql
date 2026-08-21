-- =============================================================================
-- Newcastle Permit Review — 0001_init.sql
-- THE FULL v1 SCHEMA (not just Phase 0/1), so later workflows add data, not columns.
--
-- Implements CONTRACT.md §3 (SQLite schema contract).
-- Every table below names the CONTRACT.md section it implements.
--
-- FRAMING RULE (CONTRACT.md, preamble): this app produces THE WORKING DRAFT THE
-- BOARD AMENDS, not a decision. There is deliberately NO column anywhere in this
-- schema that records "standard met" / "standard not met" as an app-derived fact.
-- findings_nodes.conclusion is NULLABLE and ships NULL; only a human, acting for
-- the Board, ever fills it. Honest blanks beat confident guesses.
--
-- Connection PRAGMAs are set in app/db.py on EVERY connect (CONTRACT.md §3.1):
--     PRAGMA foreign_keys = ON;      -- per-connection; must be re-set each time
--     PRAGMA journal_mode = WAL;     -- persistent; db.py asserts result == 'wal'
--     PRAGMA busy_timeout = 5000;    -- milliseconds
--     PRAGMA synchronous = FULL;     -- a legal record: durability over throughput
-- They are NOT set here, because a migration file runs inside a transaction and
-- journal_mode cannot change there. db.py asserts foreign_keys=1 and
-- journal_mode='wal' after opening and raises if either did not take.
--
-- Conventions:
--   * ids are TEXT (uuid4 hex or ULID), generated in Python, never AUTOINCREMENT,
--     except events.seq which exists solely to order the hash chain.
--   * timestamps are TEXT, ISO-8601 UTC with a 'Z' suffix, millisecond precision.
--   * booleans are INTEGER 0/1 with an explicit CHECK.
--   * JSON columns are TEXT holding json.dumps(obj, sort_keys=True,
--     separators=(",", ":"), ensure_ascii=False)  -- reproducible bytes (§3.3).
--   * EVERY mutating table carries actor_user_id (CONTRACT.md §3.3).
--
-- EXPLICITLY OUT OF v1: referral tracking (Road Commissioner / Fire Chief /
-- Life Safety / GSBSWD). Do not add that table. (CONTRACT.md §3.5)
-- =============================================================================


-- ---------------------------------------------------------------------------
-- schema_migrations — migration bookkeeping.  CONTRACT.md §3.1
-- app/db.py:migrate() applies app/migrations/NNNN_*.sql in lexical order, each
-- inside a single transaction, and records it here. Re-running is a no-op.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    name        TEXT PRIMARY KEY,
    applied_at  TEXT NOT NULL,
    sha256      TEXT NOT NULL            -- of the .sql file, so drift is detectable
);


-- ---------------------------------------------------------------------------
-- users — every actor the audit chain can name.  CONTRACT.md §3.3
-- Local, single-machine app; this is attribution, not authentication. The
-- literal string 'system' is reserved and is NOT a row here: an events row with
-- actor_user_id IS NULL hashes the word 'system' (§3.3).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    email           TEXT,
    role            TEXT NOT NULL CHECK (role IN
                        ('planner','ceo','chair','board_member','clerk','observer')),
    active          INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL   -- who created this user
);
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role) WHERE active = 1;


-- ---------------------------------------------------------------------------
-- board_members — Planning Board seats over time.  CONTRACT.md §3.4
-- Term windows drive quorum and the conflict_disclosures roll call. A member is
-- a user; the seat is the thing with a term.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS board_members (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    seat            TEXT,                       -- e.g. 'Seat 3', 'Alternate 1'
    is_alternate    INTEGER NOT NULL DEFAULT 0 CHECK (is_alternate IN (0,1)),
    is_chair        INTEGER NOT NULL DEFAULT 0 CHECK (is_chair IN (0,1)),
    term_start      TEXT NOT NULL,              -- ISO date
    term_end        TEXT,                       -- NULL = sitting
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_board_members_user ON board_members(user_id);
CREATE INDEX IF NOT EXISTS ix_board_members_sitting ON board_members(term_end) WHERE term_end IS NULL;


-- ---------------------------------------------------------------------------
-- rulesets — a versioned body of Code the app can review against.
-- CONTRACT.md §3.2 · §4.5
--
-- binding = 1  ->  a REAL decision may cite this ruleset (the ADOPTED Code).
-- binding = 0  ->  draft only (v0.22-draft and successors); scratch cases only.
-- Enforced by trg_cases_binding_* below AND re-checked in app/rulesets.py.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rulesets (
    id              TEXT PRIMARY KEY,
    ruleset_key     TEXT NOT NULL UNIQUE,       -- 'adopted', 'v0.22-draft'
    label           TEXT NOT NULL,
    binding         INTEGER NOT NULL CHECK (binding IN (0,1)),
    article_scheme  TEXT NOT NULL CHECK (article_scheme IN ('adopted','draft')),
    adopted_on      TEXT,                       -- Town Meeting date, ISO; NULL for drafts
    built_at        TEXT NOT NULL,
    builder_version TEXT NOT NULL,
    manifest_path   TEXT NOT NULL,              -- relative to APP, e.g. 'rulesets/adopted/manifest.json'
    source_sha_json TEXT NOT NULL,              -- {"source/article-02-data.json":"<64 hex>", ...}
    is_current      INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0,1)),
    superseded_by   TEXT REFERENCES rulesets(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL,
    -- only an adopted body of Code is binding; a draft can never be current+binding
    CHECK (is_current = 0 OR binding = 1)
);
-- History is kept: many binding rulesets may exist over time (the adopted Code as
-- amended at successive Town Meetings), but exactly ONE is current. New cases take
-- the current one; decided cases keep citing the ruleset they were decided under.
CREATE UNIQUE INDEX IF NOT EXISTS ux_rulesets_one_current
    ON rulesets(is_current) WHERE is_current = 1;
CREATE INDEX IF NOT EXISTS ix_rulesets_binding ON rulesets(binding);


-- ---------------------------------------------------------------------------
-- cases — one application before the Board.  CONTRACT.md §3.2 · §3.4
-- is_scratch = 1 lets a planner dry-run a DRAFT ruleset. A non-scratch case MUST
-- point at a binding ruleset (triggers below).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cases (
    id                  TEXT PRIMARY KEY,
    case_number         TEXT UNIQUE,            -- town file number, when assigned
    label               TEXT NOT NULL,          -- 'M003, L059 (White Rd, Shattuck)'
    map_lot             TEXT,                   -- 'M003, L059'
    situs_address       TEXT,
    applicant_name      TEXT,
    application_type    TEXT NOT NULL CHECK (application_type IN
                            ('use','zoning','subdivision','shoreland','site_plan',
                             'special_permit','expanded_use','other')),
    district_key        TEXT,                   -- 'd1' | 'sd-marine' | ... (CONTRACT.md §4.1.1)
    ruleset_id          TEXT NOT NULL REFERENCES rulesets(id) ON DELETE RESTRICT,
    is_scratch          INTEGER NOT NULL DEFAULT 0 CHECK (is_scratch IN (0,1)),
    status              TEXT NOT NULL DEFAULT 'intake' CHECK (status IN
                            ('intake','under_review','draft_ready','in_packet',
                             'heard','decided','withdrawn','closed')),
    received_at         TEXT,
    meeting_date        TEXT,                   -- computed by app/dates.py (§3.4), never typed
    draft_due           TEXT,                   -- meeting_date - 7 days
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS ix_cases_meeting ON cases(meeting_date);
CREATE INDEX IF NOT EXISTS ix_cases_ruleset ON cases(ruleset_id);

-- CONTRACT.md §3.2 — the binding gate, enforced in the database.
CREATE TRIGGER IF NOT EXISTS trg_cases_binding_insert
BEFORE INSERT ON cases
WHEN NEW.is_scratch = 0
 AND (SELECT binding FROM rulesets WHERE id = NEW.ruleset_id) <> 1
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.2: a non-scratch case must cite a binding ruleset');
END;

CREATE TRIGGER IF NOT EXISTS trg_cases_binding_update
BEFORE UPDATE ON cases
WHEN NEW.is_scratch = 0
 AND (SELECT binding FROM rulesets WHERE id = NEW.ruleset_id) <> 1
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.2: a non-scratch case must cite a binding ruleset');
END;


-- ---------------------------------------------------------------------------
-- case_reviews — one review PASS over a case (LATER: engine/).
-- A case is reviewed many times: first draft, post-comment, post-amendment.
-- Each pass is immutable once complete; a new pass is a new row, never an edit.
-- CONTRACT.md §3.6
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_reviews (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    ruleset_id      TEXT NOT NULL REFERENCES rulesets(id) ON DELETE RESTRICT,
    pass_number     INTEGER NOT NULL,
    trigger         TEXT NOT NULL CHECK (trigger IN
                        ('initial','revised_submission','board_amendment','manual_rerun')),
    status          TEXT NOT NULL DEFAULT 'running' CHECK (status IN
                        ('running','complete','failed','superseded')),
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    engine_version  TEXT,
    stats_json      TEXT,                       -- {"nodes":..,"unresolved":..,"questions":..}
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (case_id, pass_number)
);
CREATE INDEX IF NOT EXISTS ix_case_reviews_case ON case_reviews(case_id, pass_number DESC);


-- ---------------------------------------------------------------------------
-- blobs — content-addressed bytes (LATER: ingest/).  CONTRACT.md §1 S2 · §2
-- Stored at APP/data/blobs/<sha256[0:2]>/<sha256>. Deduplicated by sha256.
-- Bytes are never mutated; a corrected upload is a new blob.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS blobs (
    id              TEXT PRIMARY KEY,
    sha256          TEXT NOT NULL UNIQUE,
    byte_size       INTEGER NOT NULL CHECK (byte_size >= 0),
    media_type      TEXT NOT NULL,              -- 'application/pdf', 'image/png'
    original_name   TEXT,
    rel_path        TEXT NOT NULL,              -- relative to APP; MUST start 'data/blobs/'
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL,
    CHECK (rel_path LIKE 'data/blobs/%')        -- CONTRACT.md §1 S5: never outside APP
);


-- ---------------------------------------------------------------------------
-- documents — one submitted item in a case (LATER: ingest/).  CONTRACT.md §3.6
--
-- source_priority ENCODES "the form is wrong, the plan governs":
--     plan 100  >  survey 90  >  deed 80  >  form 40
-- Higher wins when two documents supply the same field_def. The loser is
-- RETAINED (never deleted) and the disagreement surfaces to the Board as a
-- contested field_value, never as a silent overwrite.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    blob_id         TEXT REFERENCES blobs(id) ON DELETE RESTRICT,
    kind            TEXT NOT NULL CHECK (kind IN
                        ('plan','survey','deed','form','narrative','photo',
                         'correspondence','abutter_list','other')),
    source_priority INTEGER NOT NULL CHECK (source_priority BETWEEN 0 AND 1000),
    title           TEXT NOT NULL,
    sheet_label     TEXT,                       -- 'Sheet C-2', 'Exhibit A'
    doc_date        TEXT,
    page_count      INTEGER CHECK (page_count IS NULL OR page_count > 0),
    received_at     TEXT,
    superseded_by   TEXT REFERENCES documents(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_documents_case ON documents(case_id, source_priority DESC);
CREATE INDEX IF NOT EXISTS ix_documents_live ON documents(case_id) WHERE superseded_by IS NULL;

-- The canonical priorities, asserted at write time so a typo cannot invert them.
CREATE TRIGGER IF NOT EXISTS trg_documents_priority_insert
BEFORE INSERT ON documents
WHEN (NEW.kind = 'plan'   AND NEW.source_priority <> 100)
  OR (NEW.kind = 'survey' AND NEW.source_priority <>  90)
  OR (NEW.kind = 'deed'   AND NEW.source_priority <>  80)
  OR (NEW.kind = 'form'   AND NEW.source_priority <>  40)
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.6: canonical source_priority is plan 100 > survey 90 > deed 80 > form 40');
END;


-- ---------------------------------------------------------------------------
-- pages — one page of a document (LATER: ingest/).  CONTRACT.md §3.6
-- Provenance anchor: every extracted fact points at a (document_id, page_number)
-- and, where known, a bounding box, so the Board can be shown WHERE it came from.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pages (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number     INTEGER NOT NULL CHECK (page_number > 0),
    width_pt        REAL,
    height_pt       REAL,
    text            TEXT,                       -- extracted layer, if any
    text_source     TEXT CHECK (text_source IS NULL OR text_source IN
                        ('embedded','ocr','vision','manual')),
    ocr_confidence  REAL CHECK (ocr_confidence IS NULL OR (ocr_confidence >= 0 AND ocr_confidence <= 1)),
    thumb_blob_id   TEXT REFERENCES blobs(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (document_id, page_number)
);


-- ---------------------------------------------------------------------------
-- field_defs — the catalogue of things an application can state.
-- CONTRACT.md §4.2 (dimensions) · §4.3 (use cells)
--
-- Seeded from the ruleset in Phase 1: one row per district dimension
-- (field_key = '<panel_key>.<slug(label)>'), plus the case-level fields.
-- unit / qualifier / applicability mirror CONTRACT.md §4.2 exactly.
-- unresolved = 1 marks a field the Code itself leaves open (footnote with no
-- text, standard not established) -- an HONEST BLANK, propagated to the draft.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS field_defs (
    id              TEXT PRIMARY KEY,
    ruleset_id      TEXT NOT NULL REFERENCES rulesets(id) ON DELETE CASCADE,
    district_key    TEXT,                       -- NULL = case-level, not district-scoped
    field_key       TEXT NOT NULL,              -- 'lot_dimensions.width'
    panel_key       TEXT,
    panel_title     TEXT,
    label           TEXT NOT NULL,              -- 'Primary Frontage Line Length'
    value_kind      TEXT NOT NULL CHECK (value_kind IN
                        ('dimension','count','text','boolean','use','enum')),
    unit            TEXT CHECK (unit IS NULL OR unit IN ('ft','pct','stories','units','sqft')),
    applicability   TEXT NOT NULL DEFAULT 'established' CHECK (applicability IN
                        ('established','not_established')),
    required_json   TEXT,                       -- the §4.2 constraints[] array, verbatim
    raw_value       TEXT,                       -- the §4.2 raw string, e.g. '250 ft min'
    footnote_refs   TEXT,                       -- JSON array of markers, e.g. ["4","5"]
    unresolved      INTEGER NOT NULL DEFAULT 0 CHECK (unresolved IN (0,1)),
    citation_json   TEXT NOT NULL,              -- §5.2 Citation struct; NEVER a rendered string
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (ruleset_id, district_key, field_key)
);
CREATE INDEX IF NOT EXISTS ix_field_defs_district ON field_defs(ruleset_id, district_key, sort_order);


-- ---------------------------------------------------------------------------
-- field_candidates — every value ANY source offered for a field_def.
-- CONTRACT.md §3.6
-- Nothing here is ever deleted or overwritten. When the plan says 250 ft and the
-- form says 200 ft, BOTH rows live here; source_priority decides which becomes
-- the surviving field_value, and the loser is what makes it 'contested'.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS field_candidates (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    field_def_id    TEXT NOT NULL REFERENCES field_defs(id) ON DELETE RESTRICT,
    document_id     TEXT REFERENCES documents(id) ON DELETE SET NULL,
    page_id         TEXT REFERENCES pages(id) ON DELETE SET NULL,
    subject_key     TEXT,                       -- per-lot scope: 'lot-1', 'lot-2'; NULL = whole application
    source_priority INTEGER NOT NULL,           -- copied from documents at extraction time
    raw_text        TEXT,                       -- exactly as it appears in the document
    value_num       REAL,
    value_text      TEXT,
    unit            TEXT,
    bbox_json       TEXT,                       -- [x0,y0,x1,y1] on page_id, when known
    extractor       TEXT NOT NULL CHECK (extractor IN ('regex','table','vision','llm','manual')),
    confidence      REAL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    provenance_json TEXT NOT NULL,              -- model, prompt hash, generation id, or tool version
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_field_candidates_field
    ON field_candidates(case_id, field_def_id, subject_key, source_priority DESC);


-- ---------------------------------------------------------------------------
-- field_values — the ONE surviving value per (case, field_def, subject).
-- CONTRACT.md §3.6
--
-- state CHECK IN (unconfirmed, confirmed, overridden, not_in_application,
--                 not_applicable, contested)
--   unconfirmed        -- extracted, no human has looked at it. THE DEFAULT.
--   confirmed          -- a human verified it against the document.
--   overridden         -- a human replaced the extracted value; override_reason required.
--   not_in_application -- the application is SILENT. An honest blank, not a zero.
--   not_applicable     -- the standard does not reach this proposal.
--   contested          -- sources disagree; the Board must pick. NOT auto-resolved.
-- There is NO 'verified' state and NO implicit promotion out of 'unconfirmed'.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS field_values (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    field_def_id        TEXT NOT NULL REFERENCES field_defs(id) ON DELETE RESTRICT,
    subject_key         TEXT,                   -- 'lot-1' etc.; NULL = whole application
    chosen_candidate_id TEXT REFERENCES field_candidates(id) ON DELETE SET NULL,
    value_num           REAL,
    value_text          TEXT,
    unit                TEXT,
    state               TEXT NOT NULL DEFAULT 'unconfirmed' CHECK (state IN
                            ('unconfirmed','confirmed','overridden',
                             'not_in_application','not_applicable','contested')),
    override_reason     TEXT,
    contested_with_json TEXT,                   -- JSON array of losing field_candidate ids
    confirmed_by        TEXT REFERENCES users(id) ON DELETE SET NULL,
    confirmed_at        TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (case_id, field_def_id, subject_key),
    -- an override is a human act and must say why
    CHECK (state <> 'overridden' OR (override_reason IS NOT NULL AND confirmed_by IS NOT NULL)),
    CHECK (state <> 'confirmed'  OR confirmed_by IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS ix_field_values_case ON field_values(case_id, state);


-- ---------------------------------------------------------------------------
-- rules — one testable standard lifted from the Code (LATER: engine/).
-- CONTRACT.md §4 · §5
-- A rule NEVER stores a rendered citation string: citation_json holds the §5.2
-- struct and app/citation.py renders it (CONTRACT.md §5.1).
-- prompt_hint is guidance for llm/; it is never the source of a legal statement.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rules (
    id              TEXT PRIMARY KEY,
    ruleset_id      TEXT NOT NULL REFERENCES rulesets(id) ON DELETE CASCADE,
    rule_key        TEXT NOT NULL,              -- 'art2.d1.lot_dimensions.width'
    district_key    TEXT,                       -- NULL = applies regardless of district
    field_def_id    TEXT REFERENCES field_defs(id) ON DELETE SET NULL,
    kind            TEXT NOT NULL CHECK (kind IN
                        ('dimensional','use_permission','narrative','procedural','referenced')),
    title           TEXT NOT NULL,
    code_text       TEXT NOT NULL,              -- VERBATIM Code language; never paraphrased here
    test_json       TEXT,                       -- machine-checkable form, when one exists
    citation_json   TEXT NOT NULL,              -- §5.2 Citation struct
    prompt_hint     TEXT,
    unresolved      INTEGER NOT NULL DEFAULT 0 CHECK (unresolved IN (0,1)),
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (ruleset_id, rule_key)
);
CREATE INDEX IF NOT EXISTS ix_rules_district ON rules(ruleset_id, district_key, sort_order);


-- ---------------------------------------------------------------------------
-- criteria_sets — the ordered checklist for one application type (LATER).
-- e.g. 'Subdivision — 30-A M.R.S. §4404 criteria', 'Shoreland — Article 6'.
-- This is what turns into the numbered Findings sections of the real document.
-- CONTRACT.md §3.6
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS criteria_sets (
    id                  TEXT PRIMARY KEY,
    ruleset_id          TEXT NOT NULL REFERENCES rulesets(id) ON DELETE CASCADE,
    set_key             TEXT NOT NULL,
    label               TEXT NOT NULL,
    application_type    TEXT NOT NULL,
    authority           TEXT NOT NULL CHECK (authority IN ('ceo','planning_board')),
    citation_json       TEXT NOT NULL,          -- §5.2 struct
    sort_order          INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (ruleset_id, set_key)
);


-- ---------------------------------------------------------------------------
-- criteria_set_rules — ordered membership of rules in a criteria set.
-- CONTRACT.md §3.6
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS criteria_set_rules (
    id              TEXT PRIMARY KEY,
    criteria_set_id TEXT NOT NULL REFERENCES criteria_sets(id) ON DELETE CASCADE,
    rule_id         TEXT NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    heading         TEXT,                       -- overrides rules.title in this set's numbering
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (criteria_set_id, rule_id)
);
CREATE INDEX IF NOT EXISTS ix_criteria_set_rules_order ON criteria_set_rules(criteria_set_id, sort_order);


-- ---------------------------------------------------------------------------
-- findings_nodes — THE DRAFT ITSELF: a versioned tree of findings.
-- CONTRACT.md §3.6 (findings_nodes) · the framing rule
--
-- AMENDMENT MODEL: an amendment INSERTS a new row with revision = old.revision+1
-- and then sets the OLD row's superseded_by to the new id. NOTHING IS EVER
-- OVERWRITTEN AND NOTHING IS EVER DELETED. The current tree is the set of rows
-- WHERE superseded_by IS NULL. Every prior state of the document is recoverable,
-- which is what makes "the Board amended this at the meeting" auditable.
--
-- conclusion IS NULLABLE AND SHIPS NULL. The app must NEVER write it. There is
-- deliberately no 'met'/'not_met' enum the engine could reach for. A Conclusion
-- of Law is the Board acting; the app supplies the Code text, the proposed
-- value, and board_question -- the question the Board has to answer.
--
-- unresolved = 1  ->  this node is a blank awaiting the Board. HONEST BLANKS.
-- provenance_json ->  where every assertion came from: document_id + page,
--                     field_value_id, rule_id, citation struct, and for
--                     LLM-assisted prose the model, prompt hash, generation id.
--                     A node with prose and an empty provenance object is a bug.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS findings_nodes (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    case_review_id      TEXT REFERENCES case_reviews(id) ON DELETE SET NULL,
    parent_id           TEXT REFERENCES findings_nodes(id) ON DELETE CASCADE,
    root_id             TEXT,                   -- stable identity across revisions
    revision            INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    superseded_by       TEXT REFERENCES findings_nodes(id) ON DELETE SET NULL,
    sort_order          INTEGER NOT NULL DEFAULT 0,
    node_type           TEXT NOT NULL CHECK (node_type IN
                            ('section','required_review','finding','conclusion',
                             'condition_ref','question','note')),
    number_label        TEXT,                   -- '4.A.1', 'II.3'  -- as printed
    heading             TEXT,
    body                TEXT,                   -- the finding prose (facts, not verdicts)
    rule_id             TEXT REFERENCES rules(id) ON DELETE SET NULL,
    criteria_set_id     TEXT REFERENCES criteria_sets(id) ON DELETE SET NULL,
    field_value_id      TEXT REFERENCES field_values(id) ON DELETE SET NULL,
    citation_json       TEXT,                   -- §5.2 struct; NEVER a rendered string
    conclusion          TEXT CHECK (conclusion IS NULL OR conclusion IN ('met','not_met','n_a')),
    conclusion_by       TEXT REFERENCES users(id) ON DELETE SET NULL,
    conclusion_at       TEXT,
    unresolved          INTEGER NOT NULL DEFAULT 1 CHECK (unresolved IN (0,1)),
    board_question      TEXT,                   -- first-person question put to the Board
    placeholder         TEXT,                   -- the literal 'TBD...' text as it prints
    provenance_json     TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL,
    -- Only a HUMAN may set a conclusion. The app writes NULL. (framing rule)
    CHECK (conclusion IS NULL OR (conclusion_by IS NOT NULL AND conclusion_at IS NOT NULL)),
    -- A resolved node has either a conclusion or an explicit reason to be blank.
    CHECK (unresolved = 1 OR conclusion IS NOT NULL OR node_type IN ('section','note','required_review'))
);
CREATE INDEX IF NOT EXISTS ix_findings_current ON findings_nodes(case_id, sort_order)
    WHERE superseded_by IS NULL;
CREATE INDEX IF NOT EXISTS ix_findings_parent ON findings_nodes(parent_id, sort_order);
CREATE INDEX IF NOT EXISTS ix_findings_root ON findings_nodes(root_id, revision DESC);
CREATE INDEX IF NOT EXISTS ix_findings_unresolved ON findings_nodes(case_id)
    WHERE unresolved = 1 AND superseded_by IS NULL;

-- Revisions are inserted, never overwritten: superseded_by is write-once.
CREATE TRIGGER IF NOT EXISTS trg_findings_supersede_once
BEFORE UPDATE OF superseded_by ON findings_nodes
WHEN OLD.superseded_by IS NOT NULL AND NEW.superseded_by IS NOT OLD.superseded_by
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.6: findings_nodes.superseded_by is write-once; insert a new revision');
END;


-- ---------------------------------------------------------------------------
-- conditions — conditions of approval attached to a decision (LATER).
-- Drafted with source = 'draft' and status = 'proposed'; the Board adopts,
-- amends or strikes them at the meeting. CONTRACT.md §3.6
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conditions (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    findings_node_id    TEXT REFERENCES findings_nodes(id) ON DELETE SET NULL,
    number_label        TEXT,
    text                TEXT NOT NULL,
    source              TEXT NOT NULL CHECK (source IN ('draft','board','applicant','staff')),
    status              TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN
                            ('proposed','adopted','amended','struck')),
    rule_id             TEXT REFERENCES rules(id) ON DELETE SET NULL,
    citation_json       TEXT,                   -- §5.2 struct
    revision            INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    superseded_by       TEXT REFERENCES conditions(id) ON DELETE SET NULL,
    created_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_conditions_case ON conditions(case_id) WHERE superseded_by IS NULL;


-- ---------------------------------------------------------------------------
-- motions — the vote slots. CONTRACT.md framing rule · §3.4
-- The DRAFT ships these BLANK: moved_by / seconded_by NULL, tallies NULL,
-- outcome NULL. They print as empty slots the Chair fills at the meeting.
-- The app must never populate a tally.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS motions (
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
    -- an outcome is a recorded human act
    CHECK (outcome IS NULL OR (recorded_by IS NOT NULL AND voted_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ix_motions_case ON motions(case_id, sort_order);


-- ---------------------------------------------------------------------------
-- decisions — the Board's disposition of a case. CONTRACT.md framing rule
-- One row per disposition; a reconsideration is a new row. Like motions, the
-- DRAFT carries this row with outcome NULL. The app never fills outcome.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS decisions (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    motion_id           TEXT REFERENCES motions(id) ON DELETE SET NULL,
    outcome             TEXT CHECK (outcome IS NULL OR outcome IN
                            ('approved','approved_with_conditions','denied','withdrawn','continued')),
    decided_at          TEXT,
    meeting_date        TEXT,                   -- app/dates.py (§3.4)
    appeal_deadline     TEXT,                   -- computed; see deadlines.rule_key
    ruleset_id          TEXT NOT NULL REFERENCES rulesets(id) ON DELETE RESTRICT,
    summary             TEXT,
    recorded_by         TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL,
    CHECK (outcome IS NULL OR (recorded_by IS NOT NULL AND decided_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ix_decisions_case ON decisions(case_id);


-- ---------------------------------------------------------------------------
-- conflict_disclosures — the conflict-of-interest roll call. CONTRACT.md §3.6
-- Recorded per (case, board_member). Recusal is a fact the decision must recite.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conflict_disclosures (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    board_member_id     TEXT NOT NULL REFERENCES board_members(id) ON DELETE RESTRICT,
    disclosed           INTEGER NOT NULL DEFAULT 0 CHECK (disclosed IN (0,1)),
    recused             INTEGER NOT NULL DEFAULT 0 CHECK (recused IN (0,1)),
    nature              TEXT,
    disclosed_at        TEXT,
    created_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (case_id, board_member_id),
    CHECK (recused = 0 OR disclosed = 1)
);


-- ---------------------------------------------------------------------------
-- deadlines — every computed date, with the rule that produced it.
-- CONTRACT.md §3.4
--
-- The Board meets the 3rd Thursday of each month at 18:30 America/New_York;
-- the draft is due in the packet 7 days before:
--     meeting_date(y, m) = 3rd Thursday of that month
--     draft_due          = meeting_date - 7 days
-- app/dates.py computes both. rule_key is stored so any value here can be
-- RE-DERIVED and checked; a stored date that no longer matches its rule is a
-- detectable defect, not a silent drift. Dates are never typed by a user and
-- never produced by a model.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS deadlines (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN
                        ('meeting','draft_due','completeness_review','notice',
                         'abutter_notice','decision_due','appeal','condition_compliance')),
    due_date        TEXT NOT NULL,              -- ISO date
    due_time        TEXT,                       -- '18:30' for 'meeting'
    tz              TEXT NOT NULL DEFAULT 'America/New_York',
    rule_key        TEXT NOT NULL,              -- 'pb.third_thursday' | 'pb.draft_due_minus_7'
    computed_from   TEXT,                       -- the anchor date the rule consumed
    satisfied_at    TEXT,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (case_id, kind, due_date)
);
CREATE INDEX IF NOT EXISTS ix_deadlines_due ON deadlines(due_date) WHERE satisfied_at IS NULL;


-- ---------------------------------------------------------------------------
-- events — APPEND-ONLY, HASH-CHAINED AUDIT LOG.  CONTRACT.md §3.3 · §1 S9
--
--   hash = sha256( prev_hash || id || at || actor || kind || payload_json )
--
-- concatenated UTF-8 bytes of the exact stored strings, in that order, NO
-- separator. prev_hash for the first row is '0'*64. actor is actor_user_id, or
-- the literal 'system' when NULL. payload_json is hashed EXACTLY as stored and
-- MUST be json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False).
-- at is ISO-8601 UTC, 'Z' suffix, millisecond precision.
--
-- seq orders the chain. The triggers below make UPDATE and DELETE impossible;
-- there is no administrative override. app/audit.py:verify_chain() walks seq
-- ascending and recomputes every hash.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    seq             INTEGER PRIMARY KEY AUTOINCREMENT,
    id              TEXT NOT NULL UNIQUE,
    at              TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE RESTRICT,
    kind            TEXT NOT NULL,              -- 'case.created', 'worksheet.rendered', ...
    case_id         TEXT REFERENCES cases(id) ON DELETE RESTRICT,
    entity_table    TEXT,
    entity_id       TEXT,
    payload_json    TEXT NOT NULL,
    prev_hash       TEXT NOT NULL CHECK (length(prev_hash) = 64),
    hash            TEXT NOT NULL UNIQUE CHECK (length(hash) = 64)
);
CREATE INDEX IF NOT EXISTS ix_events_case ON events(case_id, seq);
CREATE INDEX IF NOT EXISTS ix_events_kind ON events(kind, seq);

CREATE TRIGGER IF NOT EXISTS trg_events_no_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.3: events is append-only; UPDATE is forbidden');
END;

CREATE TRIGGER IF NOT EXISTS trg_events_no_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'CONTRACT.md 3.3: events is append-only; DELETE is forbidden');
END;


-- ---------------------------------------------------------------------------
-- generated_documents — every artifact the app produced. CONTRACT.md §6.3 · §8
-- rel_path is relative to APP and MUST live under data/exports/ (enforced by the
-- CHECK): the app never writes to docs/, releases/ or source/.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS generated_documents (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT REFERENCES cases(id) ON DELETE CASCADE,   -- NULL for a bare worksheet
    case_review_id      TEXT REFERENCES case_reviews(id) ON DELETE SET NULL,
    ruleset_id          TEXT NOT NULL REFERENCES rulesets(id) ON DELETE RESTRICT,
    kind                TEXT NOT NULL CHECK (kind IN
                            ('worksheet','findings_draft','findings_final','notice','packet')),
    rel_path            TEXT NOT NULL,          -- 'data/exports/20260820-140311-d1-worksheet.pdf'
    sha256              TEXT NOT NULL,
    byte_size           INTEGER NOT NULL CHECK (byte_size > 0),
    template            TEXT NOT NULL,          -- 'style/findings-template.typ'
    renderer            TEXT NOT NULL DEFAULT 'pandoc->typst',
    unresolved_json     TEXT NOT NULL DEFAULT '[]',   -- the honest-blanks inventory (§6.3)
    generated_at        TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    actor_user_id       TEXT REFERENCES users(id) ON DELETE SET NULL,
    CHECK (rel_path LIKE 'data/exports/%')      -- CONTRACT.md §8.6
);
CREATE INDEX IF NOT EXISTS ix_generated_documents_case ON generated_documents(case_id, generated_at DESC);


-- ---------------------------------------------------------------------------
-- jobs — background work (LATER: ingest/, engine/, llm/). CONTRACT.md §2
-- Single-machine queue. attempts/last_error make a stuck job visible rather than
-- silently retried forever.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,
    case_id         TEXT REFERENCES cases(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN
                        ('ingest','page_split','ocr','extract','review','render','reindex')),
    status          TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
                        ('queued','running','done','failed','cancelled')),
    priority        INTEGER NOT NULL DEFAULT 100,
    payload_json    TEXT NOT NULL DEFAULT '{}',
    result_json     TEXT,
    attempts        INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts    INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 1),
    last_error      TEXT,
    queued_at       TEXT NOT NULL,
    started_at      TEXT,
    finished_at     TEXT,
    created_at      TEXT NOT NULL,
    actor_user_id   TEXT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_jobs_ready ON jobs(status, priority, queued_at) WHERE status = 'queued';

-- =============================================================================
-- END 0001_init.sql — 23 tables + schema_migrations.
-- Tables: users, board_members, rulesets, cases, case_reviews, blobs, documents,
--         pages, field_defs, field_candidates, field_values, rules,
--         criteria_sets, criteria_set_rules, findings_nodes, conditions,
--         motions, decisions, conflict_disclosures, deadlines, events,
--         generated_documents, jobs.
-- No referral table by design (CONTRACT.md §3.5).
-- =============================================================================
