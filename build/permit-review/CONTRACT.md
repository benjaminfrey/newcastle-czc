# Newcastle Permit Review — Integration Contract

**Status:** normative. **Version:** `contract/1.0.0`. **Phase:** written at W1 (Phases 0–1);
§2 and §3 deliberately describe the **whole v1 app**, so later workflows have a home to build into.

**Scope root:** `build/permit-review/` (hereafter `APP`). The only file this project writes
outside `APP` is `style/findings-template.typ` (§8).

**What the app is.** The Planner / CEO / Chair uploads a permit application; the app reviews it
against the **adopted** Zoning Code and drafts the *Findings of Fact & Conclusions of Law* document
that the Planning Board marks up and adopts at its meeting.

> **THE FRAMING RULE (governs every other section).** The app produces **the working draft the
> Board amends**, not a decision. Real Newcastle drafts contain blank vote slots, `TBD…` fields and
> first-person questions to the Board. **Honest blanks beat confident guesses.** The app **MUST
> NEVER** state, imply, or store that a standard *is met* or *is not met* — that is the Board
> acting. Every conclusion slot ships **empty**, with the Code text, the applicant's proposed
> value, and the question the Board must answer.

Anything marked **MUST** is required for integration. **SHOULD** is a quality bar. *(optional)* may
be omitted in v1.

**Implementation citation rule.** Every module implementing a normative rule below **MUST** name
the section in its docstring, e.g. `"""Implements CONTRACT.md §4.2 (dimension normalization)."""`.

---

## Table of contents

1. [Safety posture](#1-safety-posture)
2. [Directory layout](#2-directory-layout)
3. [SQLite schema contract](#3-sqlite-schema-contract)
4. [Ruleset JSON schemas](#4-ruleset-json-schemas)
5. [The citation contract](#5-the-citation-contract)
6. [HTTP API — this phase only](#6-http-api--this-phase-only)
7. [The DECISIONS-NEEDED protocol](#7-the-decisions-needed-protocol)
8. [Repo hygiene](#8-repo-hygiene)
9. [The LLM layer](#9-the-llm-layer)
10. [The findings render mapping](#10-the-findings-render-mapping)

---

## 1. Safety posture

Adapted from `build/inventory-editor/CONTRACT.md` §1/§7. This app will eventually hold PII (names,
addresses, parcel/deed data) and will draft documents a public body relies on. The discipline is
therefore not optional.

### 1.1 Binding posture rules

- **S1 — Validate-all-then-write.** Nothing reaches disk until the *entire* payload has passed
  validation. A partially valid payload writes **nothing** and returns `400 validation_failed`
  with a per-item `details[]`.
- **S2 — Atomic writes only.** Every file write is:
  `serialize → round-trip verify (json.loads(text) == obj) → backup (if the file existed) →
  temp file in the SAME directory → f.write → f.flush → os.fsync(f.fileno()) → close →
  os.replace(tmp, target) → (best effort) fsync the containing directory fd`.
  Never an in-place truncating write. `tmp` files are removed in a `finally` on any failure.
  Temp name: `<target>.tmp-<pid>-<6 hex>`. Backup name: `<target>.bak-%Y%m%d-%H%M%S`
  (collision → `-2`, `-3`, …), pruned to the **10** newest.
- **S3 — Loopback only, non-configurable.** uvicorn binds `127.0.0.1`. The bind host is a module
  constant, **not** a CLI flag, **not** an environment variable, **not** a config key. Default
  port `8781`, overridable by `--port N` only.
- **S4 — Host / Origin checks.** Middleware rejects, with `403`:
  - any request whose `Host` header is not in `{"127.0.0.1:<port>", "localhost:<port>"}`;
  - any **state-changing** method (`POST`/`PUT`/`PATCH`/`DELETE`) carrying an `Origin` or
    `Referer` header that is not `http://127.0.0.1:<port>` or `http://localhost:<port>`.
  A state-changing request with **no** `Origin` and **no** `Referer` is accepted (curl / selftest).
- **S5 — No writes outside `APP`.** A single helper `app/paths.py:safe_path(p)` resolves a target
  and asserts `APP` is one of its `.parents` (plus the one §8 exception, which is compile-time, not
  runtime). Every writer **MUST** route through it. Path traversal is rejected before any I/O.
- **S6 — Offline `--selftest`.** `python -m app.main --selftest` **MUST** run with **no network**,
  **no LLM**, **no uploads** and **no PII**, exit `0` on success and non-zero on any failure, and
  print one line per check. Required checks at this phase:
  1. migrations apply to a throwaway temp DB and are idempotent on a second run;
  2. `PRAGMA foreign_keys`, `journal_mode`, `busy_timeout` report the §3.1 values;
  3. the audit chain verifies over a synthetic 3-event insert, and both the `BEFORE UPDATE` and
     `BEFORE DELETE` triggers on `events` raise;
  4. `rulesets/adopted/districts.json` and `use-matrix.json` load and match the §4 counts;
  5. every dimensional value in `districts.json` is either qualified or covered by
     `overrides/dimension-qualifiers.json` (§4.2, §7);
  6. `app/dates.py` reproduces the twelve 2026 meeting dates and their draft-due dates (§3.4);
  7. `app/citation.py` renders the four §5.5 golden citations byte-for-byte;
  8. the worksheet renders to a non-zero PDF in `data/exports/.selftest/`, which is removed
     again afterwards (skipped, not failed, with a printed `SKIP` line, if `pandoc` or `typst`
     is absent). It renders under `data/exports/` and not `data/tmp/` because §6.3/§8.6 make
     `data/exports/` the only permitted PDF output directory and `render/build-findings.sh`
     enforces that with a hard path guard; the selftest takes no exemption from it.
- **S7 — No silent guessing.** Any ambiguity in the Code is **collected, never resolved**:
  the normalizer raises, and the item is appended to `DECISIONS-NEEDED.md` (§7).
- **S8 — Binding gate.** A real (non-scratch) case **MUST NOT** be reviewed against, or cite, a
  ruleset whose `rulesets.binding = 0`. Enforced in code, not only by convention (§3.2).
- **S9 — Append-only audit.** Every mutation records an `events` row (§3.3). `events` is
  hash-chained and trigger-protected against `UPDATE` and `DELETE`.
- **S10 — Determinism.** Anything derivable (meeting dates, citations, permit type + authority)
  is **computed**, never typed in and never taken from model output.

### 1.2 Not in this workflow

W1 builds Phases 0 and 1 only. **Do not build** ingest, OCR/vision, the review engine, the LLM
layer, the meeting UI, or referral tracking. Their directories exist (§2) and their tables exist
(§3) so later workflows land without a migration rewrite. **No uploads, no OCR, no LLM, no PII in
this workflow.**

---

## 2. Directory layout

```
build/permit-review/
├── CONTRACT.md                  # this file — normative
├── DECISIONS-NEEDED.md          # §7 — the open-question ledger (append-only in spirit)
├── README.md                    # how to run; points here for rules
├── requirements.txt             # fastapi, uvicorn, jinja2, python-multipart (later phases add more)
│
├── app/                         # the FastAPI service  (Phase 0/1)
│   ├── __init__.py
│   ├── main.py                  # app factory, middleware (§1 S3/S4), routes (§6), --selftest (§1 S6)
│   ├── paths.py                 # APP root, safe_path (§1 S5), the ONE allowed outside path (§8)
│   ├── db.py                    # connect(), migrate(), PRAGMAs (§3.1)
│   ├── audit.py                 # append_event(), verify_chain() (§3.3)
│   ├── dates.py                 # meeting_date(), draft_due(), next_meeting() (§3.4)
│   ├── citation.py              # THE ONLY citation renderer (§5)
│   ├── rulesets.py              # load + cache rulesets/, enforce the binding gate (§1 S8)
│   ├── worksheet.py             # assembles the Phase-1 worksheet payload (§6.3)
│   ├── migrations/              # numbered .sql, applied in lexical order
│   │   └── 0001_init.sql        # the FULL v1 schema (§3)
│   ├── templates/               # Jinja2, server-rendered
│   │   ├── base.html
│   │   └── worksheet.html
│   └── static/                  # vanilla JS + CSS. NO npm, NO build step.
│       ├── app.js
│       └── styles.css
│
├── ruleset_build/               # offline builders: repo source  ->  rulesets/  (Phase 1)
│   ├── build_districts.py       # §4.1 districts.json
│   ├── build_use_matrix.py      # §4.3 use-matrix.json
│   ├── legend.py                # parses the §4.4 legend out of source/article-02.typ
│   └── slugs.py                 # district_key / panel_key / use_key derivation (§4.1.1)
│
├── rulesets/                    # BUILD OUTPUT, committed. One directory per ruleset_key.
│   └── adopted/
│       ├── manifest.json        # §4.5
│       ├── districts.json       # §4.1
│       └── use-matrix.json      # §4.3
│
├── overrides/                   # durable human decisions the builders merge (like street-types)
│   └── dimension-qualifiers.json   # §4.2.4 — the ONLY place an unqualified value may be resolved
│
├── ingest/                      # LATER: upload, PDF page split, text/vision extraction
├── engine/                      # LATER: rules -> criteria sets -> findings_nodes
├── llm/                         # LATER: prompt assembly, provenance capture. Never renders cites.
├── render/                      # pandoc -> Typst -> PDF  (§6.3 uses render/worksheet.py now)
│   └── worksheet.py
├── eval/                        # LATER: scoring drafts against the 9 real decisions
├── tests/                       # pytest; must run offline
└── data/                        # GITIGNORED. Runtime state. Never committed.
    ├── permit-review.db         # + -wal / -shm
    ├── blobs/                   # content-addressed uploads (LATER)
    ├── exports/                 # THE ONLY PDF OUTPUT DIRECTORY
    └── tmp/                     # scratch; selftest renders here
```

**`data/exports/` is the only export destination.** The app **MUST NEVER** write to `docs/`,
`releases/`, `source/`, or anywhere else in the repo (§1 S5, §8).

---

## 3. SQLite schema contract

Authoritative DDL: `app/migrations/0001_init.sql`. That file carries the **full v1 schema**, not
just this phase's tables, so later workflows add data, not columns. This section states the
properties the DDL must satisfy; the DDL comments name the section back.

### 3.1 Connection pragmas (set in `app/db.py`, documented here)

Every connection, on open, in this order:

```
PRAGMA foreign_keys = ON;      -- per-connection; MUST be re-set on every connect
PRAGMA journal_mode = WAL;     -- persistent, but assert the result is 'wal'
PRAGMA busy_timeout = 5000;    -- ms
PRAGMA synchronous = FULL;     -- a legal record; durability over throughput
```

`db.py` **MUST** assert `foreign_keys=1` and `journal_mode='wal'` after setting them and raise if
either did not take. Raw SQL only — **no ORM**. Migrations are numbered `NNNN_name.sql`, applied in
lexical order inside a single transaction each, recorded in `schema_migrations`.

### 3.2 The ruleset gate

`rulesets.binding INTEGER NOT NULL CHECK (binding IN (0,1))` answers exactly one question:
**may a real decision cite this ruleset?** The adopted Code is `binding = 1`. Every CZC draft
(`v0.22-draft` and successors) is `binding = 0`. A `case` whose `is_scratch = 0` **MUST** carry a
`ruleset_id` with `binding = 1`; enforced by a table trigger *and* re-checked in `app/rulesets.py`.

### 3.3 The audit chain

`events` is **append-only and hash-chained**:

```
hash = sha256( prev_hash || id || at || actor || kind || payload_json )
```

- Concatenation is of the **UTF-8 bytes of the exact stored strings**, in that order, with **no
  separator**. `prev_hash` for the first row is the 64-character string `"0" * 64`.
- `actor` is the stored `actor_user_id`, or the literal string `"system"` when it is NULL.
- `payload_json` is hashed **exactly as stored**. It **MUST** be serialized with
  `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` so the hash is
  reproducible.
- `at` is an ISO-8601 UTC string with a `Z` suffix and millisecond precision.
- `BEFORE UPDATE` and `BEFORE DELETE` triggers on `events` `RAISE(ABORT, …)`. There is no
  administrative override.
- `app/audit.py:verify_chain(conn)` walks `events` by `seq` ascending and recomputes every hash.

**Every mutating table carries `actor_user_id`** referencing `users(id)`, and every mutation
appends an `events` row in the same transaction.

### 3.4 Deterministic dates

The Planning Board meets the **3rd Thursday of every month at 6:30 pm**; the draft is due in the
packet **7 days before**.

```
meeting_date(year, month) = the 3rd Thursday of that month     # weekday 3 (Mon=0)
draft_due(meeting_date)   = meeting_date - 7 days
```

`app/dates.py` computes both. Meeting time is `18:30` **America/New_York**. These values are
**computed on read**, never typed by a user and never produced by a model. `deadlines` rows store
the computed result plus the `rule_key` that produced it, so a stored value can always be re-derived
and checked.

### 3.5 The v1 table list (24 tables + `schema_migrations`)

`users`, `board_members`, `rulesets`, `cases`, `case_reviews`, `blobs`, `documents`, `pages`,
`field_defs`, `field_candidates`, `field_values`, `rules`, `criteria_sets`, `criteria_set_rules`,
`findings_nodes`, `conditions`, `motions`, `decisions`, `conflict_disclosures`, `attendance`,
`deadlines`, `events`, `generated_documents`, `jobs`.

`attendance` (0017_meeting_attendance.sql, W7's "meeting model") is the one addition past the
original 23: one row per (case, board_member) roll call, `present` 0/1. Absence of a row is not a
finding either way -- same posture as `conflict_disclosures`. `motions`, `decisions`, and
`conflict_disclosures` themselves needed no schema change; 0001_init.sql already specified all
three in full, they simply had zero readers or writers anywhere in the codebase before app/meeting.py.

**No referral table.** Referral tracking (Road Commissioner / Fire Chief / Life Safety / GSBSWD) is
explicitly **out of v1**. Do not add it.

### 3.6 Named invariants the DDL must encode

- **`documents.source_priority INTEGER NOT NULL`** — encodes *"the form is wrong, the plan
  governs"*. Canonical values: **plan 100 · survey 90 · deed 80 · form 40**. Higher wins. When two
  documents supply the same `field_def`, the higher `source_priority` produces the surviving
  `field_candidate`; the loser is retained, never deleted, and the conflict is surfaced to the
  Board rather than silently resolved.
- **`field_values.state`** — `CHECK (state IN ('unconfirmed','confirmed','overridden',
  'not_in_application','not_applicable','contested'))`. New extractions are `unconfirmed`. Only a
  human moves a value to `confirmed` or `overridden`. `contested` means two sources disagree and
  the Board must pick. There is **no** `'verified'` and no implicit promotion.
- **`findings_nodes`** — a versioned tree: `parent_id`, `revision`, `superseded_by`.
  **An amendment INSERTs a new revision and points the old row's `superseded_by` at it. Nothing is
  ever overwritten and nothing is ever deleted.** The current tree is
  `WHERE superseded_by IS NULL`. Plus:
  - `unresolved INTEGER NOT NULL DEFAULT 1` — this node is still a blank the Board must fill;
  - `board_question TEXT` — the first-person question put to the Board;
  - `provenance_json TEXT NOT NULL` — where every assertion in this node came from
    (`document_id` + `page`, `field_value_id`, `rule_id`, `citation`, and for LLM-assisted text the
    model, prompt hash and generation id). A node with prose and an empty provenance object is a
    bug.
  - **`conclusion` is nullable and ships NULL.** There is no `met`/`not_met` column. See the
    framing rule.
- **`events`** — §3.3.
- Every table: `created_at TEXT NOT NULL`, and every mutating table `actor_user_id TEXT`.

### 3.7 `findings_nodes` — the W6 additions (`0013_findings_tree.sql`)

The table itself (§3.6) shipped in full at W1, unread and unwritten by any code until W6.
`0013_findings_tree.sql` is purely additive — four new nullable columns, carrying the same
"honest blanks" discipline as everything else in this table:

- **`quoted_standard_text TEXT`** — the VERBATIM standard THIS ROW quotes, separate from `body`
  (the finding prose beneath it), because the one formatting rule that is ~80% of every real
  Newcastle decision is that the quoted standard prints **flush left** and the finding prints
  **indented** underneath it. Never regenerated, reworded or summarised — same discipline as
  `rules.code_text`'s own comment. (§10.1's render mapping keys the printed standard off THIS
  column, not off `rules.code_text` via `rule_id` — the node is the record.)
- **`finding_source TEXT CHECK (... IN ('engine','model','operator'))`** — who is answerable for
  `body`'s wording, so "a reader must always be able to tell which produced a sentence" is a
  queryable fact, not a convention. `NULL` for nodes with no authored prose yet (a section
  heading, an unfilled question carrying only `board_question`). DB CHECK: a stated
  `finding_source` requires a non-NULL `body` — a source can't be claimed for text that doesn't
  exist.
- **`applicability_verdict TEXT CHECK (... IN ('true','false','unknown'))`** — the (separately
  built) applicability gate's three-valued output for this node's standard. **Not** the banned
  met/not_met Conclusion of Law (`conclusion`, unchanged, still nullable and human-only) — it
  answers "does this standard apply at all," not "is it met." `'unknown'` is a first-class value,
  not an absence: §10.1's render mapping never suppresses a node on `'unknown'`, it renders the
  standard and asks the Board.
- **`citation_display TEXT`** — a CACHE of `app.citation.render(citation_json)`, written by
  `engine/findings.py` at the same time as `citation_json`. Per §5.1 this is never the source of
  truth and no consumer is obliged to read it; `render/case_findings.py`'s own mapping (§10.1)
  deliberately re-renders from `citation_json` instead and does not read this column at all —
  the cache exists for a caller who wants the string without deserializing, not as a second
  authority.

**Provenance shape (`provenance_json`), as `engine/findings.py:validate_provenance()` enforces it**
at the Python layer (this is deliberately *not* a DB CHECK — see the note below):
a node carrying `body` or `quoted_standard_text` must carry non-empty `provenance_json`, and
depending on `finding_source`:

- `'engine'` → must trace to at least one of `rule_id`, `citation`, or `document_id`.
- `'model'` → must carry `provenance_json.model = {provider, model, prompt_sha256[, generation_id]}`
  — never raw prompt text (same discipline as §9.5's `record_llm_call()`).
- `'operator'` → must carry `provenance_json.operator = {user_id[, note]}`.

**Why this is Python-level, not a DB CHECK:** a cross-column CHECK enforcing the same rule in DDL
was drafted for `0013_findings_tree.sql` and then deliberately dropped before it shipped — it broke
`render/case_findings.py`'s own already-written test fixtures (`tests/test_case_findings.py`'s
`_insert_node()` helper defaults `provenance_json` to `'{}'`), a concurrently-built W6 workflow
(§10, discovered mid-build in this same directory — the same shape of parallel construction §9's
own W5 section documents once already). The rule is real and enforced for every call through
`engine.findings.create_node()`/`amend_node()` (raises `ValidationError` before any write); a raw
SQL insert bypassing this module — as test fixtures elsewhere in this repo already do for other
tables — is not blocked by the DDL, matching how most of this schema's business rules already work.

**The amendment model, restated in code terms:** `engine/findings.py:amend_node()` INSERTs a new
row (`revision = old.revision + 1`, same `root_id`) and UPDATEs the old row's `superseded_by` to
point at it, both inside one transaction, with exactly ONE `events` row for the whole amendment
(`kind='findings_node.amended'`). `root_id` is set to a node's own `id` at first creation
(`create_node()`) and carried forward unchanged by every amendment — the stable identity §3.6
already promised. `get_revision_chain(root_id)` returns every revision, current and superseded,
oldest first; the chain is walkable by following `superseded_by` pointers forward from the first
revision to the row whose `superseded_by IS NULL`.

---

## 4. Ruleset JSON schemas

Built offline by `ruleset_build/` from repo source; written into `rulesets/<ruleset_key>/`; loaded
read-only at runtime by `app/rulesets.py`. **Runtime never re-parses repo source.**

**Verified source facts (do not re-derive):**

- `source/article-02-data.json` is a JSON **array of 13** district objects.
- Article 2 is Article 2 in **both** adopted and draft numbering, so this data serves the
  **adopted** ruleset directly.
- **13 districts × 63 uses = 819 district×use cells.** The use-label list and its order are
  **identical in all 13 districts**. *(Earlier scoping said 769; the verified count is 819 —
  `by_code` = `u:218, rc:53, sp:58, ex:40, "":450`.)*
- `"code"` is **NOT unique** — seven districts all have code `"SD"`. A naive `code` lookup silently
  returns SD-Historic for all seven. **Key on `district_key`** (§4.1.1) or array index.
- `use_standards.items[]` is **polymorphic**: `{"text":…, "sub":[…]}` dicts in D1 / SD-Rural
  Highway / SD-Campus, bare strings elsewhere, empty lists in SD-Conservation / SD-Fabrication.
- `"matrix"` is **null** for SD-Conservation, SD-Campus and SD-Marine. **Null is a FINDING, not an
  error** (§4.1.4).
- Panel titles are **not unique within a side**: D1's `right[]` contains **two** panels titled
  `DESIGN STANDARDS`. Panel identity is `(side, index)` (§4.1.2).
- `D4.use_col1` contains a soft-hyphen extraction split: two adjacent categories titled
  `"TRANSPORTATION & UTIL­"` (empty `entries`) and `"ITIES"` (6 entries). The builder
  **MUST** merge them into `TRANSPORTATION & UTILITIES` (§4.3.2) — this is a mechanical
  de-hyphenation, not a legal judgement, so it does not go to `DECISIONS-NEEDED.md`.

### 4.1 `districts.json`

```json
{
  "schema": "newcastle.districts/1.0.0",
  "ruleset_key": "adopted",
  "generated_at": "2026-08-20T14:03:11Z",
  "source": { "path": "source/article-02-data.json", "sha256": "<64 hex>" },
  "article": { "adopted": 2, "draft": 2 },
  "counts": { "districts": 13, "dimensions": 0, "unresolved": 0 },
  "districts": [ /* district objects, in source array order */ ]
}
```

A **district object**:

```json
{
  "district_key": "d1",
  "source_index": 0,
  "code": "D1",
  "name": "RURAL",
  "display_name": "D1 - Rural",
  "group": "Core Zoning Districts",
  "color": "#CDE4CC",
  "band_text": "#231F20",

  "description": "The Rural D1 district consists of ...",
  "purpose": ["To provide the community with a predictable outcome ...", "..."],

  "panels":     [ /* §4.1.2 — ALL panels, both sides, source order, verbatim */ ],
  "dimensions": [ /* §4.2 — normalized; dimensional panels only */ ],

  "building_matrix": { /* §4.1.4 */ },
  "building_matrix_absent": null,

  "use_standards": {
    "title": "USE STANDARDS FOR D1 - RURAL",
    "items": [ { "text": "Gas stations are limited to ...", "sub": [] } ]
  },

  "citation": { "article": 2, "district": "D1", "district_name": "Rural" }
}
```

#### 4.1.1 Key derivation (`ruleset_build/slugs.py`)

`district_key` is **fixed by table** — never derived from `code`:

| index | code | name | `district_key` |
|---|---|---|---|
| 0 | D1 | RURAL | `d1` |
| 1 | D2 | NEIGHBORHOOD RESIDENTIAL | `d2` |
| 2 | D3 | NEIGHBORHOOD BUSINESS | `d3` |
| 3 | D4 | VILLAGE RESIDENTIAL | `d4` |
| 4 | D5 | VILLAGE BUSINESS | `d5` |
| 5 | D6 | TOWN CENTER | `d6` |
| 6 | SD | HISTORIC | `sd-historic` |
| 7 | SD | CONSERVATION | `sd-conserve` |
| 8 | SD | HIGHWAY COMMERCIAL | `sd-hwy` |
| 9 | SD | RURAL HIGHWAY | `sd-rhwy` |
| 10 | SD | CAMPUS | `sd-campus` |
| 11 | SD | MARINE | `sd-marine` |
| 12 | SD | FABRICATION | `sd-fab` |

The builder **MUST** assert the array is length 13 and that `(index, code, name)` matches this
table exactly; a mismatch is a hard failure, not a warning.

`slug(s)` = casefold → NFKD → strip soft hyphens (`­`) → non-alphanumerics to `_` → collapse
runs → strip leading/trailing `_`. Used for `panel_key`, `field_key` leaves, `use_key`,
`category_key`.

#### 4.1.2 `panels[]` — verbatim carry-through

```json
{ "side": "left", "index": 2, "ordinal": 2,
  "panel_key": "lot_dimensions", "title": "LOT DIMENSIONS",
  "kind": "para" | "list" | "lv",
  "body": "<string>" | ["<string>" | {"text":"…","sub":["…"]}] | [["<label>","<value>"]] }
```

- `kind: "para"` → `body` is a string.
- `kind: "list"` → `body` is a list of **str or dict** (polymorphic; normalize on **read**, never
  by rewriting the source).
- `kind: "lv"` → `body` is a list of `[label, value]` pairs.
- **Panel identity is `(side, index)`.** `panel_key` collisions inside one side get a `_2`, `_3`
  suffix in source order (D1 right: `design_standards`, then `design_standards_2`). `title` is
  always preserved verbatim for display and citation.
- Observed titles: left = `DESCRIPTION`, `PURPOSE`, `LOT DIMENSIONS`, `PRIMARY BUILDING PLACEMENT`,
  `ACCESSORY BUILDING PLACEMENT`, `BUILDING PLACEMENT` (SD-Campus, SD-Marine only); right =
  `DESIGN STANDARDS`, `BUILDINGS STANDARDS`, `DISTRICT STANDARDS` (D1),
  `LOT AND BUILDINGS STANDARDS` (SD-Rural Highway), `ADDITIONAL STANDARDS` (SD-Conservation),
  `PERMITTED BUILDING GROUPS`. The builder **MUST NOT** hard-code this list as a closed set; an
  unseen title is carried through and its `panel_key` slugged.

#### 4.1.3 Dimensional panel scope

Exactly these four titles are **dimensional** and feed `dimensions[]` (§4.2):

```
LOT DIMENSIONS · PRIMARY BUILDING PLACEMENT · ACCESSORY BUILDING PLACEMENT · BUILDING PLACEMENT
```

Every other `lv` panel (in practice only `DESIGN STANDARDS`) is **prose**: its values
(`Additions`, `Massing Components`, `Massing & Architectural`, `Components`,
`see Article 6 section 8`, `Parallel within 200 of road`, `Gable 5/12 min`, `20% min, 80% max`)
are carried verbatim in `panels[]` and are **not** parsed as dimensions and **never** raise.

#### 4.1.4 `building_matrix` — and its absence

```json
{ "title": "PERMITTED BUILDINGS",
  "cols": ["Residential", "General Accessory", "Agricultural Use"],
  "rows": [ ["Permitting Authority", "CEO", "CEO", "CEO"],
            ["Building Width", "50 ft", "30 ft", "-"] ] }
```

`rows[i][0]` is the row label; `rows[i][1..]` align to `cols`. Column count varies (2–5). Row
labels observed: `Permitting Authority`, `Building Width`, `Building Depth`, `Building Floor Area`,
`Total Stories`, `First Floor Height`, `Upper Floor Height`, `Number of Units`. `"-"` means the
standard is not established for that building type.

When the source `matrix` is **null** (SD-Conservation, SD-Campus, SD-Marine) the builder sets
`building_matrix: null` and:

```json
"building_matrix_absent": {
  "finding": "Article 2 does not establish building dimensional standards for this District.",
  "unresolved": true,
  "board_question": "Article 2 establishes no building dimensional standards for the <name> District. What dimensional standards, if any, does the Board apply to this proposal?"
}
```

This is a **finding for the worksheet**, not a builder error and not a `DECISIONS-NEEDED` entry.

### 4.2 `dimensions[]` — the normalizer

One object per `[label, value]` pair in a §4.1.3 dimensional panel:

```json
{
  "field_key": "primary_building_placement.side_setback",
  "panel_key": "primary_building_placement",
  "panel_title": "PRIMARY BUILDING PLACEMENT",
  "label": "Side Setback",
  "raw": "0 ft min (4) , 5 ft max (5)",
  "applicability": "established",
  "unit": "ft",
  "constraints": [
    { "qualifier": "min", "value": 0.0, "unit": "ft", "footnote_ref": "4", "source": "literal" },
    { "qualifier": "max", "value": 5.0, "unit": "ft", "footnote_ref": "5", "source": "literal" }
  ],
  "footnote_refs": ["4", "5"],
  "unresolved": true,
  "notes": ["Footnote text for (4) and (5) is not present in the Article 2 extract."],
  "citation": { "article": 2, "district": "D1", "panel": "PRIMARY BUILDING PLACEMENT", "label": "Side Setback" }
}
```

- `field_key` = `panel_key + "." + slug(label)`. Unique within a district.
- `qualifier` ∈ `{"min","max"}` only. `unit` ∈ `{"ft","pct",null}` at this phase.
- `source` ∈ `{"literal","override"}` — `literal` = the qualifier word was present in `raw`;
  `override` = supplied by `overrides/dimension-qualifiers.json` (§4.2.4).

#### 4.2.1 Not-established values

`raw` ∈ `{"", "n/a", "N/A", "-", "—", "none"}` (case-insensitive, trimmed) →
`applicability: "not_established"`, `constraints: []`, `unit: null`, `unresolved: false`.
This renders on the worksheet as **"Article 2 establishes no standard for this field."** — it does
**not** render as `0`, as "no limit", or as a blank cell.

#### 4.2.2 Grammar

```
value      := clause ( "," clause )*
clause     := number unit? qualifier footnote?
number     := digits ( "." digits )?
unit       := "ft" | "%"
qualifier  := "min" | "minimum" | "max" | "maximum"          (case-insensitive)
footnote   := "(" digits ")"
```

Verified to cover every dimensional value in the source, including `20% min, 80% max`,
`14 ft min, 35 ft max`, `0 ft max`, `1000 ft min (1)`, `0 ft min (4) , 5 ft max (5)`.

#### 4.2.3 FAIL LOUDLY

A `clause` that carries a number **and** no `qualifier`, in a §4.1.3 dimensional panel, with **no**
matching entry in `overrides/dimension-qualifiers.json`, **MUST** raise
`ruleset_build.AmbiguousDimension` and **abort the whole build**. The builder writes **no**
`districts.json`. It **MUST NOT** default to `min`, default to `max`, guess from a sibling
district, infer from the field name, or emit the value unqualified.

**Known occurrences (exactly two, both verified):**

| district | panel | label | raw |
|---|---|---|---|
| `sd-historic` | PRIMARY BUILDING PLACEMENT | Frontage Zone Setback | `20 ft` |
| `sd-marine` | BUILDING PLACEMENT | Frontage Zone Setback | `20 ft` |

Both are already logged in `DECISIONS-NEEDED.md`. Until a human resolves them, the build fails —
that is the intended behaviour.

#### 4.2.4 `overrides/dimension-qualifiers.json`

The **only** place an unqualified dimensional value may be resolved. Human-authored, committed,
never written by the app.

```json
{
  "_README": "Resolves unqualified Article 2 dimensional values. One entry per (district_key, field_key). CONTRACT.md §4.2.4. A human with the adopted Code in hand must fill 'qualifier' and 'decided_by'. Never machine-generated.",
  "entries": {
    "sd-historic:primary_building_placement.frontage_zone_setback": {
      "raw": "20 ft",
      "qualifier": null,
      "decided_by": null,
      "decided_at": null,
      "basis": null,
      "note": "Sibling districts render this field '20 ft min'. Not sufficient to assume. See DECISIONS-NEEDED.md."
    }
  }
}
```

`qualifier: null` is **not** a resolution — the build still fails. Only a non-null
`qualifier` ∈ `{"min","max"}` **with** a non-null `decided_by` and `basis` resolves it, and the
resulting constraint carries `"source": "override"` plus the `decided_by` / `basis` in
`dimensions[].notes`, so the provenance reaches the printed worksheet.

#### 4.2.5 Footnotes

`footnote_ref` values `(1)`, `(4)`, `(5)` appear in the source with **no footnote text** in the
extract. Any dimension with a non-empty `footnote_refs` gets `unresolved: true` and a `notes[]`
entry, and is listed in `DECISIONS-NEEDED.md`. It does **not** fail the build — the number and its
qualifier are known; only the qualification text is missing, and the worksheet prints the marker so
the Board sees it.

### 4.3 `use-matrix.json`

```json
{
  "schema": "newcastle.use-matrix/1.0.0",
  "ruleset_key": "adopted",
  "generated_at": "2026-08-20T14:03:11Z",
  "source": {
    "data_path": "source/article-02-data.json", "data_sha256": "<64 hex>",
    "legend_path": "source/article-02.typ",     "legend_sha256": "<64 hex>"
  },
  "legend": [ /* §4.4 */ ],
  "categories": [ { "category_key": "residential", "title": "RESIDENTIAL", "column": 1, "order": 3 } ],
  "uses": [ { "use_key": "residence", "label": "Residence",
              "category_key": "residential", "column": 1, "order": 17 } ],
  "district_keys": ["d1", "d2", "…"],
  "cells": [
    { "district_key": "d1", "use_key": "residence", "code": "u",
      "permit": "Use Permit", "permit_key": "use",
      "authority": "CEO", "authority_key": "ceo", "allowed": true }
  ],
  "counts": { "districts": 13, "uses": 63, "cells": 819,
              "by_code": { "u": 218, "rc": 53, "sp": 58, "ex": 40, "": 450 } }
}
```

- `cells` is **dense**: exactly `districts × uses` = **819** entries, prohibited cells included.
  A prohibited cell is `code: ""`, `permit: null`, `authority: null`, `allowed: false`,
  `permit_key: "prohibited"`. Prohibition is a **positive fact** that the worksheet must be able to
  print; it is never a missing row.
- The builder **MUST** assert `len(cells) == 819` and that every district presents the same 63
  `use_key`s in the same order (verified true), failing hard otherwise.
- Nine categories after the §4.3.2 merge: `TRANSPORTATION & UTILITIES`, `RECREATION`,
  `RESIDENTIAL`, `AGRICULTURAL`, `INDUSTRIAL`, `COMMERCIAL GOODS`, `COMMERCIAL SERVICES`
  (+ the remaining source categories, carried through, not hard-coded).

#### 4.3.2 The D4 soft-hyphen merge

In `d4.use_col1`, a category titled `"TRANSPORTATION & UTIL­"` with `entries: []` is
immediately followed by `"ITIES"` with the 6 Transportation & Utilities entries. The builder
**MUST**: detect a category whose title ends in `­` and whose `entries` is empty, join its
title with the next category's title (dropping the soft hyphen), adopt the next category's
`entries`, and drop the fragment. It **MUST** then assert D4 yields the same 63 `use_key`s as D1.

### 4.4 The use-status legend — the highest-value asset in the repo

Parsed by `ruleset_build/legend.py` from the `USE TABLE LEGEND` block in `source/article-02.typ`
(the `status(...)` rows, ~lines 325–336). **This legend exists nowhere else.** It converts a
one-or-two-letter cell into **permit type + permitting authority**, which *is* the
**"Required Review(s)"** table at the head of every real Newcastle decision.

| code | permit | `permit_key` | authority | `authority_key` | glyph | allowed |
|---|---|---|---|---|---|---|
| `u`  | Use Permit | `use` | CEO | `ceo` | `●` | true |
| `rc` | Residential Companion Permit | `residential_companion` | CEO | `ceo` | `❶` | true |
| `sp` | Special Permit | `special` | Planning Board | `planning_board` | `❷` | true |
| `ex` | Expanded Use Permit | `expanded_use` | Planning Board | `planning_board` | `✪` | true |
| `""` | *(none — prohibited)* | `prohibited` | — | — | — | false |

Source note, carried into `legend[].note` for the empty code:
*"Uses without u, rc, sp, or ex are not allowed in this District."*

`legend.py` **MUST** parse these rows out of the `.typ` rather than hard-coding them, and then
**assert** the parsed result equals the table above. If the `.typ` block moves or changes shape,
the build fails loudly rather than silently shipping a stale legend. Glyphs come from the
`#let glyphs = (u: "●", rc: "❶", sp: "❷", ex: "✪")` binding in the same file.

This produces the Buehner-style row verbatim:

> `Use Permit | CEO | A Residence use in the D1-Rural District requires a Use Permit which can be issued by the CEO.`

rendered by `app/citation.py` (§5), never by a stored string.

### 4.5 `rulesets/<key>/manifest.json`

```json
{
  "schema": "newcastle.ruleset-manifest/1.0.0",
  "ruleset_key": "adopted",
  "label": "Newcastle Core Zoning Code (adopted)",
  "binding": true,
  "article_scheme": "adopted",
  "adopted_on": null,
  "built_at": "2026-08-20T14:03:11Z",
  "builder_version": "ruleset_build/1.0.0",
  "files": { "districts": "districts.json", "use_matrix": "use-matrix.json" },
  "source_sha256": { "source/article-02-data.json": "<64 hex>", "source/article-02.typ": "<64 hex>" }
}
```

`binding` here mirrors `rulesets.binding` in the DB (§3.2); `app/rulesets.py` loads the manifest
and **MUST** refuse to serve a `binding: false` ruleset to a non-scratch case.

---

## 5. The citation contract

**Citations are rendered by `app/citation.py` from structured data. NEVER from a stored string.
NEVER from model output.**

### 5.1 The rule

- No table stores a rendered citation as its source of truth. Where a rendered string is persisted
  (e.g. inside `findings_nodes.provenance_json` for the record) it is a **cache**, produced by
  `citation.render()`, and any consumer re-renders rather than trusting it.
- The LLM layer (`llm/`) **MUST NOT** emit citation text. It emits a `Citation` **struct** (or a
  reference to one already in the payload); `citation.render()` produces every character the reader
  sees. A model-authored string that looks like a citation is a bug, and `engine/` **MUST** reject
  any LLM output containing an unstructured section reference.
- Rendering is **pure and deterministic**: same struct + same style → same bytes.

### 5.2 The struct

```python
@dataclass(frozen=True)
class Citation:
    ruleset_key: str                  # "adopted"
    scheme: str                       # "adopted" | "draft"  -- which numbering `article` is in
    article: int                      # article number IN `scheme`
    section: str | None = None        # "5", "5.D", "7.F"  -- preserved verbatim across schemes
    subsection: str | None = None
    district_key: str | None = None   # "d1"
    district_code: str | None = None  # "D1"
    district_name: str | None = None  # "Rural"
    panel_title: str | None = None    # "PRIMARY BUILDING PLACEMENT"
    label: str | None = None          # "Side Setback"
    use_label: str | None = None      # "Residence"
    exhibit: str | None = None        # "3.1"
    table: str | None = None          # "3.5"
```

### 5.3 Article renumbering — seeded from `extract/verso.py:18`

```python
RENUM_ADOPTED_TO_DRAFT = {1: 1, 2: 2, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9}
RENUM_DRAFT_TO_ADOPTED = {v: k for k, v in RENUM_ADOPTED_TO_DRAFT.items()}   # draft Article 3 (Thoroughfares) has NO adopted counterpart
```

**Section numbers are preserved; only article numbers shift.** Draft Article 3 (Thoroughfares) is
new — `to_scheme(3, frm="draft", to="adopted")` raises `NoCounterpart`, it does not return `3`.
`app/citation.py` owns this constant; nothing else may redefine it.

### 5.4 Functions

```python
def render(c: Citation, *, style: str = "long") -> str
def to_scheme(article: int, *, frm: str, to: str) -> int          # raises NoCounterpart
def in_scheme(c: Citation, scheme: str) -> Citation               # returns a renumbered copy
def from_dimension(ruleset_key: str, district: dict, dim: dict) -> Citation
def from_use_cell(ruleset_key: str, district: dict, use: dict, cell: dict) -> Citation
def required_review_row(district: dict, use: dict, cell: dict) -> dict
```

`style` ∈ `{"long", "short", "inline"}`.
`required_review_row(...)` returns `{"permit": …, "authority": …, "sentence": …, "citation": …}`
where `sentence` is exactly the §5.5 golden form.

### 5.5 Golden strings (asserted by `--selftest`; changing one is a contract change)

| call | output |
|---|---|
| `render(Citation("adopted","adopted",2,district_code="D1",district_name="Rural",panel_title="LOT DIMENSIONS",label="Primary Frontage Line Length"))` | `Article 2, D1-Rural District, Lot Dimensions: Primary Frontage Line Length` |
| the same, `style="short"` | `Art. 2, D1, Primary Frontage Line Length` |
| `render(Citation("adopted","adopted",7,section="34",subsection="b"))` | `Article 7, Section 34.b` |
| `required_review_row(d1, residence, cell)["sentence"]` | `A Residence use in the D1-Rural District requires a Use Permit which can be issued by the CEO.` |

Prohibited-cell sentence form: `A <Use> use is not allowed in the <Code>-<Name> District.`
Planning-Board form: `… requires a <Permit> which must be issued by the Planning Board.`

---

## 6. HTTP API — this phase only

Three endpoints. Nothing else is exposed. No uploads, no auth, no PII.

Envelope for every JSON response:
`{"ok": true, "data": {…}}` or `{"ok": false, "error": "<code>", "message": "<human>", "details": [...]}`.

### 6.1 `GET /healthz`

`200` `{"ok":true,"data":{"status":"ok","version":"<app version>","contract":"contract/1.0.0",
"db":"ok","migrations":["0001_init"],"rulesets":["adopted"],"binding_ruleset":"adopted",
"pragmas":{"foreign_keys":1,"journal_mode":"wal","busy_timeout":5000}}}`.
Never touches the network. Returns `503` with `error:"db_unavailable"` if the DB cannot be opened.

### 6.2 `GET /`

The **dimensional worksheet** page — server-rendered Jinja2 (`app/templates/worksheet.html`),
vanilla JS, no npm, no build step. Query params (all optional):
`?district=<district_key>&use=<use_key>`. Renders, for the selected district:

1. **Required Review(s)** — the §4.4 legend applied to the selected use (or the whole 63-row table
   when no use is selected), each row carrying its `citation`.
2. **Dimensional standards** — `dimensions[]`, each row: `Label · Required (from the Code) ·
   Proposed (blank) · Citation`, reproducing the Shattuck page-3 form, e.g.
   `Primary Frontage Line Length (min) | Required: 250 ft | Proposed: ______`.
   `not_established` rows print *"Article 2 establishes no standard for this field."*
   `unresolved` rows print their footnote marker and note.
3. **Permitted Buildings** — the matrix, or the §4.1.4 absence finding + board question.
4. **Use Standards / Design Standards / District Standards** — verbatim from `panels[]`.

An unknown `district` → `404 unknown_district` listing valid keys. **No conclusion is rendered
anywhere on this page.**

### 6.3 `POST /api/worksheet/render`

Body:

```json
{ "ruleset_key": "adopted",
  "district_key": "d1",
  "use_keys": ["residence"],
  "case_label": "M003, L059 (White Rd, Shattuck)",
  "meeting_month": "2026-09",
  "lots": [ { "label": "Lot 1" }, { "label": "Lot 2" } ],
  "notes": "" }
```

- Validates **everything** first (§1 S1). `ruleset_key` must resolve and, unless
  `"scratch": true`, must be `binding` (§1 S8) → else `403 non_binding_ruleset`.
- `meeting_month` (`YYYY-MM`) is used only to compute and print `meeting_date` and `draft_due`
  via `app/dates.py` (§3.4). If omitted, the next meeting after today.
- Renders **pandoc → Typst → PDF** using `style/findings-template.typ`, into
  `data/exports/<YYYYMMDD-HHMMSS>-<district_key>-worksheet.pdf`, written atomically (§1 S2).
- `200` → `{"ok":true,"data":{"path":"data/exports/…","bytes":123456,"sha256":"…",
  "meeting_date":"2026-09-17","draft_due":"2026-09-10","unresolved":[…]}}`.
  `path` is **relative to `APP`** and always inside `data/exports/`.
- `unresolved[]` lists every blank, footnote and board question in the rendered document — the
  worksheet's honest-blanks inventory.
- `500 render_unavailable` if `pandoc` or `typst` is missing; the message names the missing tool.
- Appends an `events` row (`kind: "worksheet.rendered"`) and a `generated_documents` row.

---

## 7. The DECISIONS-NEEDED protocol

`APP/DECISIONS-NEEDED.md` is the ledger of everything the Code does not answer. **Ambiguity is
collected, never guessed** (§1 S7).

### 7.1 What goes in it

- An unqualified dimensional value — the Code does not say `min` or `max` (§4.2.3).
- A footnote marker whose text is not in the source (§4.2.5).
- A value whose unit is missing or unclear.
- Two source documents that disagree and no `source_priority` rule settles it.
- Any place a reasonable implementer would be tempted to pick a value.

### 7.2 What does NOT go in it

- Mechanical extraction artifacts with one correct answer (the D4 soft-hyphen merge, §4.3.2) —
  fix them in the builder.
- `matrix: null` (§4.1.4) — that is a **finding for the Board**, and belongs in the worksheet.
- Bugs. Those are bugs.

### 7.3 Format

One `##` entry per item, appended, newest last, never edited except to fill in **Resolution**.

```markdown
## D-0003 — SD-Marine · Frontage Zone Setback · unqualified "20 ft"

- **Status:** OPEN
- **Raised:** 2026-08-20 by ruleset_build/build_districts.py
- **Ruleset:** adopted
- **District:** `sd-marine` (SD - Marine, source index 11)
- **Field:** `building_placement.frontage_zone_setback` — panel `BUILDING PLACEMENT`, label `Frontage Zone Setback`
- **Raw string:** `20 ft`
- **Why ambiguous:** Article 2 states the number without `min` or `max`. Every other Frontage Zone
  Setback in the Code reads `20 ft min`, but a setback rendered without a qualifier could as easily
  be a maximum in a form-based code, and a wrong guess would produce a Finding that misstates the
  standard to the Board.
- **What we will NOT do:** infer from sibling districts, default to `min`, or emit it unqualified.
- **Blocking:** yes — `ruleset_build` raises `AmbiguousDimension` and writes no `districts.json`
  until this is resolved in `overrides/dimension-qualifiers.json`.
- **Needs:** a human reading the adopted Article 2 SD-Marine spread.
- **Resolution:** _(pending — record qualifier, who decided, date, and the basis)_
```

Ids are `D-NNNN`, monotonic, never reused. `Status` ∈ `OPEN` · `RESOLVED` · `WITHDRAWN`.
A blocking item stays blocking until a matching `overrides/dimension-qualifiers.json` entry has a
non-null `qualifier`, `decided_by` and `basis` (§4.2.4).

### 7.4 The rule, restated

> If the Code does not say whether a number is a minimum or a maximum, **do not pick one.**
> The normalizer fails loudly, the build produces nothing, and the question goes to a human.
> A blank in a Board draft is honest. A guess in a Board draft is a defect with legal consequences.

---

## 8. Repo hygiene

Binding on every agent working in this project.

1. **NEVER modify anything in `docs/`.** Immutable baseline PDFs — the adopted Code, the Comp Plan,
   the RDEO, and the nine real decisions. Read-only, always.
2. **Write ONLY inside `build/permit-review/`**, with exactly **ONE** exception:
   `style/findings-template.typ` (created by this project; the house-style Typst template for
   §6.3 output, cloned from the proven `build/build-memo.sh` + `style/memo-template.typ` pattern —
   palette `article_blue #367AAC`, `body_dark #231F20`, `subsection_gray #7C766F`, Barlow at
   `style/fonts/`).
3. **Do NOT `git add`, `git commit`, or `git push`. Ever.** (Repo standing rule #1: only Ben
   commits, and only when he asks.)
4. **Do NOT modify any existing repo file** except: append two lines to `.gitignore`
   (`build/permit-review/data/` and `build/permit-review/.venv/`), and create
   `style/findings-template.typ`.
5. **Never guess a legal or dimensional value** (§7).
6. Output PDFs go to `APP/data/exports/` only. Never `docs/`, never `releases/`, never `source/`.
7. `APP/data/` and `APP/.venv/` are gitignored. `APP/rulesets/` and `APP/overrides/` are **meant to
   be committed** (by Ben) — they are the reproducible, reviewable ruleset.
8. Python 3.14. FastAPI + uvicorn (127.0.0.1 only), Jinja2 server-rendered, vanilla JS.
   SQLite WAL, raw SQL, numbered `.sql` migrations. **No ORM. No npm. No build step.**

---

## 9. The LLM layer

Built ahead of **D-0025**, which is now **RESOLVED — approved** (see DECISIONS-NEEDED.md for the
verbatim decision, the FOAA basis, and why the entry was briefly reverted). Building ahead of it was
deliberate, so the decision could land without re-architecting: the safeguards below apply
regardless of how it resolved, `null` remains THE DEFAULT provider everywhere, and nothing here has
yet been exercised against a real key or network — no key is set in this environment. Implements §1.1 S6/S7/S10 at the model boundary: `--selftest` and
every test in this repo run fully offline; a shortfall is a Board flag, never a conclusion; a
model-authored citation or numeral is never trusted on its say-so.

### 9.1 The protocol

ONE interface, `llm/protocol.py:LLMClient` (`@runtime_checkable` `Protocol`), covers both a
text-only call and a vision call — a vision call is simply an `LLMRequest` with `images` populated;
there is no separate method or request type.

```python
class LLMClient(Protocol):
    provider_name: str
    def complete(self, request: LLMRequest) -> LLMResponse: ...
```

`llm/types.py` carries the request/response shapes and the error hierarchy every provider maps its
own failures onto (`LLMError` → `LLMAuthError` / `LLMRateLimitError` / `LLMBadRequestError` /
`LLMServerError` / `LLMTransportError` / `LLMResponseParseError`), so a caller writes one `except`
chain regardless of which provider raised.

### 9.2 The four providers (`llm/factory.py:get_client()`)

Resolution order: explicit `provider` argument → `PERMIT_REVIEW_LLM_PROVIDER` env var → `"null"`.

- **`null`** (`llm/null.py`) — **THE DEFAULT.** Deterministic, offline, zero-cost; always answers a
  syntactically valid empty field-candidate envelope (`"[]"`). Makes `--selftest` and every test in
  this repo runnable with no key and no network.
- **`anthropic`** (`llm/anthropic_provider.py`) — the real provider. Reads `ANTHROPIC_API_KEY` from
  the environment at **call time only**, never stores or logs it; a missing key raises
  `LLMAuthError` with an actionable message before any transport is attempted. Model id is the
  single constant `DEFAULT_MODEL = "claude-opus-5"`. Retries transient failures
  (`LLMRateLimitError`/`LLMServerError`/`LLMTransportError`) with exponential backoff (default 2
  retries), never retries a bad request. **Not exercised by any test or by `--selftest`** — every
  test injects a fake `transport` callable; correctness is proven by construction
  (`build_message_params()`, `parse_message()`, `_map_exception()` are each pure and independently
  tested). The `anthropic` package itself is deliberately **not** a declared dependency; its import
  in the real (uninjected) transport is lazy, so this whole module loads and every test passes
  whether or not the package happens to be installed.
- **`recorded`** (`llm/recorded.py` + `llm/cassette.py`) — replays a cassette file. Deterministic
  and free; used for reproducible evals (W8) and for exercising real-shaped prompts without a key.
  Cassette format v1 (`llm/cassette.py`): a JSON file with `format_version: 1`, a **required**
  boolean `synthetic` field, a `note` that must say so in plain language when `synthetic: true`, and
  `entries[]` keyed by `compute_key()` (a SHA-256 over prompt + system + sorted metadata + per-image
  content hash — never the image bytes). Every cassette shipped in this repo is `synthetic: true`
  and hand-authored (`llm/cassettes/fixtures/`); a **real** recording (`synthetic: false`) can only
  ever be produced once a key exists and an actual call is made — nothing in this repo does that.
- **`local`** (`llm/local.py`) — a documented stub seam for a future local model (D-0025 option
  (c)). Constructible and protocol-conformant today; `complete()` raises `NotImplementedError`.

### 9.3 Redaction (`llm/redact.py`)

Known-token substitution, not generic NER — the case already knows its own names, addresses,
phones, emails, and deed references. `KnownTokens` is a closed 5-field dataclass (names, addresses,
phones, emails, deed_refs); there is no field for a number, dimension, date, or district, so there
is no call shape that can ever redact one. `redact_text()` returns a `RedactionResult` (redacted
text, a class-and-count-only `RedactionReport`, and a `token_map` for round-trip `restore()` before
a model's answer is shown to anyone). **Honest limitation, enforced in code:** a page image cannot
be name-redacted; `require_operator_ticked_for_image()` raises `ImagePagesNotRedactable` unless the
caller passes `operator_ticked=True` for that specific document.

### 9.4 The output guards (`llm/guards.py`)

Run in this order (`run_guards()`): **(1) citation stripping** — every citation-shaped substring a
model wrote is removed and the real citation(s), if any, are re-rendered from `app/citation.py`
(§5.1) — a model-authored citation never reaches a document. Case-insensitive (critic finding
A3.1): a lowercase `article 7, section 15.d` is stripped exactly like `Article 7, Section 15.D`.
**(2) numeral grounding** — every numeral in the (citation-stripped) text must already appear in
the caller's fact set (handling `1,330` vs `1330`, `74.2` vs `74.20`, and mixed fractions honestly,
never by loosening); an ungrounded numeral flags its whole sentence and the caller sets
`findings_nodes.unresolved = 1`. **(3) conclusion-verb downgrade** — output containing "complies",
"satisfies", "fails to meet", "does not meet", "is/are consistent with", "in compliance with", and
the house-style equivalents read off the real decisions downgrades the node to a Board flag; a
modal-obligation *clause* (critic finding A2.1 — scoped to the clause, not the whole sentence, so a
modal earlier in a compound sentence can't swallow a real conclusion later in it) stating what the
Code *requires* (not what this application *achieved*) is excluded. **(4) residual placeholder**
(critic finding A4.3) — a `[REDACTED_..._N]` redaction placeholder still present in text *after*
`llm/redact.py`'s `restore()` step means the model referenced a token this call gave it no grounds
to use; the node is flagged rather than shown as clean prose. Each guard is tested in **both
directions** — it fires on the bad case and stays silent on the good one.

### 9.5 The `events` row (D-0025's audit safeguard)

`llm/events.py:record_llm_call()` appends one `events` row (via `app/audit.py:append_event()`,
`kind="llm.call"`) for **every** LLM call, success or failure alike. Payload fields: `purpose`,
`provider`, `prompt_sha256` (never the prompt text itself), `image_count`, `max_tokens`, a
`redaction_report` (class/count only), `success`, and on success `model` / `provider` /
`stop_reason` / `input_tokens` / `output_tokens`, or on failure `error_type` / `error_message`.
Never logs: the prompt text, image bytes, or the API key.

**This is enforced structurally, not by call-site convention.** `llm/audited.py:AuditedClient`
wraps any `LLMClient` and itself satisfies the `LLMClient` protocol (`provider_name` + one
`complete()` method), so a call site holding an `AuditedClient` cannot reach the wrapped provider's
`complete()` without the wrapper's `record_llm_call()` write happening around it — success or a
raised `LLMError` alike, in that order (call, then record, then return-or-reraise). The one real
call site today, `ingest/vision.py:run_vision_extraction()`, requires a `conn` argument for exactly
this reason and builds an `AuditedClient` internally before ever calling `client.complete()`; a
future `engine/` call site is expected to do the same rather than calling a raw provider directly.
`tests/test_audited.py` covers the wrapper in isolation (success, failure, redaction-report
pass-through, and that the request forwarded to the inner provider is never mutated — `llm/recorded.py`
computes its cassette key from the exact request, `metadata` included).

### 9.6 Few-shot index (`llm/fewshot.py`) and the vision path (`ingest/vision.py`)

`llm/fewshot.py` indexes the **6 matched pairs** in `docs/Findings of Fact and Conclusions of Law/`
(an application PDF plus its Board decision PDF) by `(review_type, rule_id)`, `rule_id` resolved via
`ruleset_build.verify_citations`'s already-verified citation extraction. **Dalton** and **Stantec**
(applications with no matching decision on file yet — the W8 held-out eval set) are marked
`holdout=True` and are refused, in code, before any file I/O — proven by a test that monkeypatches
the PDF-open primitive to fail loudly if it is ever reached for either one.

`ingest/vision.py` is the Tier C/D page → `field_candidates` path: render one page to PNG at 200 dpi
→ build one `LLMRequest` (one call per page, not per field) → `client.complete()` → parse the
model's JSON array into `ingest.fields.FieldCandidate` rows. `require_operator_ticked_for_image()`
is called first, before any byte is rendered. Every candidate this module produces carries
`method="vision"`, `page_no`, and `confidence`, and — like every `FieldCandidate`
(`ingest/fields.py`) — `needs_confirmation=True` always, enforced by the dataclass itself. A
malformed or unparsable model response yields **zero** candidates, never a guessed one.

---

## 10. The findings render mapping

`render/case_findings.py` implements CONTRACT.md's W6 "draft document" step: a case's CURRENT
`findings_nodes` tree (§3.6, widened by `0013_findings_tree.sql`) → the `render.findings_to_md`
node list → `render/build-findings.sh` → a PDF in `data/exports/`. It is the last mile only — it
builds nothing that isn't already durable in the database (no applicability decisions, no engine
logic, no drafted prose); that is engine/'s job. This module is read-only against every table it
touches except `generated_documents`, written by its one HTTP caller (below), never by this module
itself — mirroring `render/worksheet.py`'s existing split from a built ruleset to a PDF.

**THE FRAMING RULE, restated for this mapping specifically:** nothing here ever renders a
conclusion. The DB enforces this structurally — `findings_nodes.conclusion` is nullable and only a
human may set it (§3.6's own CHECK) — so every node this mapping cannot fill honestly renders as a
highlighted blank (`#unresolved`/`#boardq`) rather than being omitted. A case with an empty or
near-empty `findings_nodes` tree still produces a COMPLETE document: Project Information, a single
board flag noting no findings have been drafted yet, a blank Decision section, one blank numbered
condition slot, and a signature grid — never a short document, because a short document on a
contradictory or unbuilt record is the one thing this app must never produce.

### 10.1 node_type → render nodes

Walks the tree `WHERE case_id = ? AND superseded_by IS NULL`, parent before children, siblings in
`sort_order`. A root node (depth 0) is Code-derived (an Article, a District) → heading level 2; its
children → level 3; deeper → level 4 (clamped) — level 1 is reserved for the document's own top
divisions (FINDINGS OF FACT / CONCLUSIONS OF LAW / DECISION OF THE PLANNING BOARD), which this
module assembles itself, never from a `findings_nodes` row.

- **`section` / `required_review`** → `heading(row.heading, level)` + `para(row.body)` if present.
  (`required_review` does not yet get its own table — a future enhancement could join
  `criteria_sets.authority` via `criteria_set_id` for a Permitting-Authority column; today it
  renders exactly like a `section`, honestly, rather than fabricating columns nothing populates.)
- **`finding`** → the core mapping, keyed on the three `0013_findings_tree.sql` columns:
  - `quoted_standard_text` (VERBATIM, never `rules.code_text` — the row is the record) →
    `standard(text, citation=...)`, flush left. `citation` is *always* re-rendered from the row's
    own `citation_json` via `app/citation.py:render()` (§5.1) — the `citation_display` cache column
    is never read here, matching §5.1's "any consumer re-renders rather than trusting it".
  - `body` ("the finding prose — facts, not verdicts") → `finding(text)`, indented, beneath it.
  - `applicability_verdict` (`'true'|'false'|'unknown'|NULL`, the applicability gate's output):
    **`'unknown'` NEVER suppresses the node** — the standard still renders, `body` (if any) still
    renders, and a `boardq()` is always appended (the node's own `board_question`, or a generic
    "Does this standard apply to this application?" if none was supplied). `'false'` still renders
    the standard and whatever reasoning `body` carries (the real decisions' "does not address, and
    therefore does not apply to, …" pattern) — never dropped from the document. `'true'` or `NULL`
    (not yet gated) render normally.
  - `board_question` → `boardq(text)` when present (for `'true'`/`NULL`/`'false'` verdicts; always
    present for `'unknown'`, per above).
  - No `body` and no `board_question` at all → `unresolved(row.placeholder or a generic TBD)` — the
    honest-blank fallback that keeps the decisive W6 test true: an empty case still lists every
    standard, each one flagged.
  - `finding_source` (`'engine'|'model'|'operator'|NULL`) → when set, a small gray provenance tag
    via the template's existing `#provenance()` helper (reused generically, not citation-specific),
    shown only when the PDF is rendered with `PROVENANCE=1`. This is how §9's "a reader must always
    be able to tell which produced a sentence" requirement reaches the actual document.
- **`conclusion`** → the terser "Conclusions of Law" restatement the real decisions use (one line
  per applicable standard, e.g. Uberoi's lettered a./c./d./…/u. list) — `number_label` + (`body` or
  `quoted_standard_text` or `heading`, in that preference order) as a bold-labelled `para()`, plus
  the same `finding_source` marker. `conclusion` itself is always NULL here (framing rule); nothing
  in this mapping can render "met"/"not met" — the renderer has no node type for it at all.
- **`condition_ref`** → skipped in the tree walk. Conditions are rendered once, consolidated, from
  the `conditions` table directly (§10.2), not scattered through the tree at each reference point.
- **`question`** → `boardq(board_question or body)`.
- **`note`** → `para(body)` if present.

Free text pulled from the database and handed to `para()`/`kv()` is always passed through
`render.findings_to_md.md_escape()` first — `para()` itself does not escape (by design, so a
caller-composed string like a bold label prefix survives), so this module is the one responsible
for escaping anything DB-sourced before it reaches `para()`.

### 10.2 The Decision section

Assembled once, after the tree walk, never per-node:

- **Motions.** `SELECT * FROM motions WHERE case_id = ? ORDER BY sort_order`. If any rows exist,
  one `motionblock()` per row, with `moved_by`/`seconded_by` resolved to `users.display_name` via
  `board_members`, and `yea`/`nay`/`abstain`/`result` from the row. **If none exist — the normal
  state before W7's meeting workflow — exactly one blank `motionblock()`** (every field `none`,
  rendering as a highlighted `…`), matching every pre-meeting DRAFT sample in
  `docs/Findings of Fact and Conclusions of Law/` (the Profenno and Uberoi drafts both do this;
  only the ADOPTED FINAL documents carry real vote counts). Per-standard motion blocks (as the
  Shattuck ADOPTED FINAL shows for a subdivision) are a W7 concern — this module does not fabricate
  them ahead of a real recorded vote.
- **Conditions.** `SELECT * FROM conditions WHERE case_id = ? AND superseded_by IS NULL ORDER BY
  number_label, created_at` → one `conditions([...])` call. Empty list still renders one genuinely
  blank numbered slot (the renderer's own behavior, per style/findings-template.typ).
- **Signatures.** Currently sitting `board_members` (`term_end IS NULL`), chair first
  (`is_chair DESC`), then alphabetically → `signaturegrid([...])`, chair carrying the title "Chair",
  everyone else untitled — matching every real decision's signature block.

### 10.3 `generated_documents` and the render route

`render_case_findings(conn, case_id, out_dir, *, draft=True, provenance=False)` returns
`(pdf_path, unresolved_inventory)` — it does not itself write `generated_documents`; that write
(kind `'findings_draft'`, `template='style/findings-template.typ'`, `renderer='pandoc->typst'`,
`unresolved_json` = the returned inventory) happens in its one caller,
`POST /api/cases/{case_id}/findings/render` (`app/routes/cases.py`), inside the same
BEGIN/COMMIT transaction as the `events` row it appends (`kind="findings.rendered"`) — mirroring
`app/cases.py`'s own write pattern (§3.3: every mutation appends an `events` row in the same
transaction). This is the row `engine/deadlines.py`'s F8 check already reads
(`generated_documents.kind IN ('findings_draft','findings_final')`) to know a draft has been
produced for a case — so wiring this write is not optional polish, it is what makes that already-
built deadline check ever see a real row. `draft` defaults `True` (every document this app produces
is a draft until a human Board adopts it — CONTRACT.md's framing rule; there is no honest way to
call this `draft=False` for a real case before W7's adoption workflow exists). The route is a
visible action in `app/templates/case_detail.html` ("Findings Draft" panel), not a shell script an
operator has to find.
