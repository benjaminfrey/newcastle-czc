# Applicant Portal M4 — The Three Applications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A signed-in applicant starts a Use Permit, Small Project Plan or Entrance/Driveway Permit
from "Here's what you'll need", answers short plain questions (saved as they go, with uploads
scanned for viruses), and reaches a review-and-edit page that shows the Town's official form filled
in, where each section can be edited in place or given more detail.

**Architecture:** Each application is a YAML **form definition**: the official form's sections
and fields, each field with the plain question that fills it (or a note that the property lookup,
the signature at submit, or staff fill it). The same `show_if` language as the screener decides which
questions apply, evaluated identically in Python and TypeScript. Applications, the property
snapshot, insert-only answers, repeat items (buildings, components), section notes and attachments
live in Postgres; files go to an S3-compatible store (MinIO on the VM) after a ClamAV scan. Every
entry starts as a draft the chair approves, and production refuses a form with any draft in it, as
in M3.

**Tech Stack:** M3's stack, plus boto3 (S3 client — vendor-neutral), python-multipart (FastAPI
uploads), MinIO (dev/LAN object store), ClamAV `clamd` (scanning), Playwright + `@axe-core/playwright`
(journeys and accessibility checks). Every new version is pinned to the current release at
implementation time (`pip index versions …`, `npm view … version`, `docker pull` of the exact tag)
and recorded in the commit.

**Spec:** `specs/2026-10-14-applicant-portal-design.md` (§4 steps 4–5, §5 "Form definitions" and
"Records", §6 "Uploads" and "Never lose a submission" (the two-tab warning) and "Version safety",
§7) · **Roadmap:** M4 · **Built on:** `main` at `5e395ae`.

## Decisions made with the chair (2026-10-21)

- **The fields come from the Town's current Planning Application packet.** Every field of the
  Cover Sheet, Use Form, Building Form and Components Section carries into the new forms, asked in
  plain words. The Entrance/Driveway Form has no paper ancestor; its fields are drafted from Art. 3
  §§7–8 and §12. (The packet's printed fields were read from the scanned 2025 applications in
  `docs/Findings of Fact and Conclusions of Law/`: Verney Use Application 2025-04-02 (Cover Sheet,
  Use Form), Dalton 2025-09-09 (Building Form, Components Section). If the Town's blank packet has
  pages those scans lack, e.g. a second Building Form page or the "Other Structures Form" the Board
  app knows by name, the review sheet will show the gap; ask Ben for the blank packet then.)
- **The chair approves, as in M3.** Every section, field and option list starts as `status:
  draft`. A generated review sheet lists them for the chair, and production refuses a form with any
  draft in it. The CEO and Planning Board plain-language sign-off (O5) stays open, for M7.
- **Buildings and components repeat.** "Add another building" and "Add an addition, porch or
  deck" loop the same questions. The form prints one Building Form per building and one
  Components Section per component, as the packet says.

## Decisions made in planning (recorded for the reviewer)

- **"Standard Met?" is not carried over.** The paper Building Form has "District Standard /
  Standard Met?" columns. "Standard Met?" is a verdict column, which spec §5 forbids (no pass/fail
  field). The District Standard column becomes M6's standards-check flags. Neither prints in M4.
- **Building classes follow the Code, not the paper.** Art. 5 §1.c lists Special Use Building,
  which the paper form omits. The option list is Art. 5 §1.c, and a test reads it from the
  ruleset.
- **Signatures, dates and "Name (print)" are filled at submit (M6).** M4 marks them `source:
  at_submit`, so "every official field is filled or marked" still holds.
- **Files are served through the API** to the signed-in owner (`GET /api/attachments/{id}`, streamed
  with `Content-Disposition: attachment`), not as presigned S3 links. The browser never reaches the
  store, which keeps the VM's MinIO off the network. On a managed platform this can become a
  short-lived presigned link by configuration.
- **Tests never need ClamAV or MinIO.** `create_app(store=…, scanner=…)` takes fakes, as it already
  takes a mailer. No setting can turn scanning off: the production app always builds `ClamdScanner`,
  and a scanner that cannot be reached refuses the upload (503).
- **Playwright journeys run on the VM** against the LAN-shaped dev stack with real MinIO and ClamAV.
  CI does not run them: ClamAV's signature download is routinely refused from CI runners. CI runs
  the API and web unit tests, plus an S3 contract test against a MinIO service container.
- **A question with an unknown `show_if` is shown.** `show_if` evaluates three-valued; only `false`
  hides a question. So a manual property (`on_state_highway: null`) still gets the MaineDOT
  question. The Python and TypeScript sides share one rule and one fixture file.
- **Not in M4:** the reviewed glossary (spec §4) waits for M7's plain-language review, because
  question wording is approved on the review sheet in the meantime. Fees, standards-check flags and
  signing are M6.
- **Hidden answers are kept, not printed.** If a change hides a question, its answer stays in
  `answer` but is neither printed nor counted. If the question comes back, so does the answer.

## The field inventory (the content Task 3 transcribes)

Each official field has a `source`: `question` (asked in the wizard), `property` (from the
snapshot; shown, with "staff confirm"), `account` (the signed-in email), `derived` (copied from
another field, e.g. Map/Lot in a form header), `at_submit` (M6) or `staff` ("Official use only").
Citations are given where the Code grounds the field. Cover-sheet and packet fields with no Code
section cite `8.2.a.2` ("all necessary information… to determine compliance").

**Cover Sheet** (every application; `cover-sheet.v1.yaml`)

| Section | Official field | Source | Plain question (draft) / note |
|---|---|---|---|
| Location of Proposed Project | Map · Lot · Street Address | property (question if manual) | — |
| | Deed Book · Page | question, optional, "I don't know" | "If you know it, your deed's book and page at the Registry" |
| Applicant | Name · Email · Phone · Address | question / account / question / question | Name is new to the cover (the paper takes it at the signature) |
| Property Owner (if different) | "same as applicant" · Name · Email · Phone · Address | question (yes/no), then questions `show_if` not owner | Name is added |
| Agent (if applicable) | "someone is applying for you" · Name · Email · Phone · Address | question (yes/no), then questions | Name is added |
| Site Information (existing) | Zoning District | property | "staff will confirm" when manual/split |
| | Lot Area (acres) | property, applicant may correct | shown measured value; "Is this about right?" |
| | Lot Width (ft) | question, unknown allowed | help = the paper's footnote (widest point between side lot lines, Front Lot Line to Maximum Front Setback) |
| | Street Frontage (ft) | property per street, may correct | |
| | Lot Depth (ft) | question, unknown allowed | |
| | Number of Existing Dwelling Units | question | |
| Signature | Applicant Signature · Date · Name (print) | at_submit | |
| Official Use Only | Date Received | staff | |

**Use Form** (`use-permit.v1.yaml` = cover + this; cites `8.15.b.1`)

| Section | Official field | Source | Note |
|---|---|---|---|
| Proposed Project | Applicant Name · Street Address · Map · Lot | derived | |
| Existing | Existing Use(s) | question, `uses` type (use-table picker) + "none / something else" | |
| | Description | question, long text | |
| Proposed | Uses to be Established | question, `uses`, prefilled from the screener's `use_key` | |
| | Description | question, long text | |
| | Uses to be Discontinued · Description | question, optional | |
| Attachments | other relevant documentation | upload, optional, many | |
| Signature | Signature · Date · Name | at_submit | |
| Official Use Only | Permit Type Required | staff | the paper's note about Special Use Permits (an out-of-date "Article 7 §18" reference) is not carried |

**Small Project Plan** (`small-project-plan.v1.yaml` = cover + the three parts below; cites
`8.10.b.1`–`5`)

*Your Project* (new section; drafted): kind of work (choice, multi: new building · addition ·
renovation · site improvements · change to a nonconforming lot, use or structure, citing §10.b.1–5);
description (long text); site plan or sketch (upload, optional, "staff may ask for one"; whether it
is required is a question for the chair on the review sheet).

*Building Form*, repeated per building (Art. 4 §3, Art. 5 §1; ids align with `districts.json`
panel keys for M6):

| Section | Official field | Type |
|---|---|---|
| Header | Map · Lot · Street Address · Zoning District | derived |
| | Building reference (name) | text |
| | Only being renovated, not changing size or location | yes/no |
| Building Location (proposed) | Setback from front lot line · from side lot line (two) · from rear lot line | number ft, unknown allowed; help: "measured from the lot line to the closest part of the building" |
| Building Details (proposed) | building class | choice from Art. 5 §1.c (Residential; Single Unit Commercial; Multi-unit Commercial; Mixed-Use; Residential Accessory; Commercial Accessory; General Accessory; Special Use; Agricultural) |
| | Proposed number of dwelling units | number |
| Main Building Mass | Width · Depth (ft) · Total number of stories · Floor Area (sf) · Elevation of first floor (ft, relative to grade at front) | number |
| | First–Fourth floor height (floor-to-floor, ft) | number, `show_if` stories ≥ n |
| | Roof style | choice: Gable, Mansard, Gambrel, Hipped, Shed |
| | Roof slope · Exterior finish material (list all) | text |
| Windows & Doors | North · East · South · West facing façade % | number 0–100 |

*Components Section*, repeated per component (Art. 4 §5, Art. 5 §2):

| Official field | Type |
|---|---|
| Only being renovated | yes/no |
| Kind | choice: Addition · Garage · Porch · Deck · Patio · Other architectural component (+ name) |
| Building attached to | choice of this application's buildings + "free standing" (garage: attached/detached) |
| Width × Depth × Height (Patio: Width × Length) | numbers, ft |
| Roof style · Roof slope · Exterior finish | `show_if` kind in (addition, garage) |
| Windows & Doors N/E/S/W % | `show_if` kind in (addition, garage) |

**Entrance / Driveway Form** (`entrance-permit.v1.yaml` = cover + this; new, every field drafted)

| Official field | Type | Cites |
|---|---|---|
| Street or Road the entrance is on (+ its Type) | choice from the snapshot's streets, or text | 3.8.b.1 |
| Work | choice: new driveway · relocate a driveway · new entrance to a parking lot | 3.7.b.1, 3.8.b.1 |
| Dwellings served: single-family · two-family | numbers | 3.7.c.7–8 |
| Shared with a neighbouring lot? · access easement | yes/no; upload `show_if` shared | 3.7.c.3 |
| Driveway width (ft) | number | 3.7.e.1 |
| Slope of the first 20 ft (%) | number, unknown allowed | 3.7.d.2 |
| Angle where it meets the road (degrees) | number, unknown allowed | 3.8.e.1 |
| Distance to the nearest intersection (ft) · is it signalled? | number; yes/no/unknown | 3.8.f.2 |
| Sight distance, each direction (ft) | numbers, unknown allowed | 3.8.f.1.a |
| Ditch along the road where the driveway goes? | yes/no/unknown | 3.7.d.3 |
| Location of the entrance | map point on the lot | 3.8.d.2 |
| Sketch | upload, optional | 8.2.a.2 |
| MaineDOT entrance permit | `show_if` `property.on_state_highway` ≠ false: have it (upload) · applied · not yet; help says it is needed before the Zoning Permit is issued | 3.12.d.1–2 |

## Global Constraints

- All M1–M3 Global Constraints hold. In brief:
  - the VM workflow;
  - stage by name;
  - the model trailer;
  - no push, PR or merge unasked;
  - never guess a legal value;
  - never a verdict (the M1 word list `approved, denied, compliant, meets, fails, violates` is
    checked against every applicant-facing string in the form definitions and the new pages);
  - the adopted ruleset only, pinned.
- **Drafts never reach applicants in production.** `GET /api/forms/{key}` and `POST
  /api/applications` answer `503 form_not_approved` while any entry the form uses (including the
  cover sheet) is a draft, unless `PORTAL_ALLOW_DRAFT_RULES=true` (dev VM and LAN only).
- **Applicant A can never read or change B's anything.** Every application, item, note and
  attachment route answers **404** for someone else's id, the same as for an id that doesn't
  exist.
- **Uploads:**
  - PDF, JPEG, PNG and HEIC only, decided by the file's first bytes, not its name or the browser's
    type;
  - 25 MB each (`PORTAL_UPLOAD_MAX_BYTES=26214400`);
  - scanned before anything is stored;
  - an infected file, a refused type, an oversized file or an unreachable scanner stores nothing;
  - uploads per applicant are limited (`PORTAL_UPLOAD_LIMIT_PER_HOUR=60`).
- **The record keeps history.** Answers are insert-only rows; a change appends. Each write appends
  an `event` naming the application, the fields and the items, but **not the values**: the answer
  table holds those, and the hash chain is permanent.
- **Version safety.** An application stores `form_key`, `form_version` and `ruleset_key` when it is
  created and is always read with those, even after a v2 of the form exists.
- **The official form keeps the Code's exact terms**; the plain question and the help carry the
  plain words.
- Phone width works throughout (WCAG 2.1 AA aims; axe checks in Task 13).

## Review Focus

1. **Two tabs on one application.** The later save must be refused, never silently overwrite the
   first. The page then says so and offers "Load the latest" or "Keep mine". Tests: Task 6
   `test_stale_revision_is_refused`; Task 10 "warns when the application changed in another tab".
2. **An edit that changes which questions apply** (owner → not owner; 3 stories → 1). New questions
   are flagged on review as "a few new questions apply" and the wizard visits only those. A hidden
   answer is kept and not printed. Tests: Task 5 `test_hidden_answers_are_kept_not_counted`;
   Task 11 "sends the applicant through only the new questions".
3. **Uploads that must be refused**: an `.exe` renamed `.pdf`, a 26 MB photo, the EICAR test file,
   or ClamAV down. Each gets a plain message and nothing is stored. Tests: Task 8
   `test_renamed_executable_is_refused`, `test_oversized_upload_is_refused_without_reading_it_all`,
   `test_infected_upload_stores_nothing`, `test_scanner_down_refuses_upload`.
4. **Signing in mid-flow.** The emailed link opens a new tab, which has none of the old tab's
   session storage. The application must still start with the chosen property and the screener's
   use. Tests: Task 9 `pendingStart` "survives a new tab" and "Verify resumes a pending start".
5. **A property entered by hand** (lookup down, or "I can't find my property"). The application
   starts and is marked "property not verified", and the MaineDOT question shows because the road
   is unknown. Tests: Task 6 `test_manual_property_is_not_verified`; the Task 4 fixture
   `unknown_show_if_is_shown`.

---

## Task 0: Branch and VM

- [ ] On `portal-m4-applications` (already cut from `main` at `5e395ae`). Check: `git log -1
  --oneline` shows `5e395ae`. Run `portal/vm.sh run 'cd portal/api && .venv/bin/pytest -q'`;
  expected: all pass (1,022).

---

## Task 1: The application records (migration 0005)

**Files:**
- Create: `portal/api/migrations/versions/0005_applications.py`
- Test: `portal/api/tests/test_applications_schema.py`

**Interfaces:**
- Produces tables:
  - `application`: `id uuid pk`, `applicant_id → applicant`, `form_key text`, `form_version int`,
    `ruleset_key text`, `status text CHECK (status IN ('draft'))` (M6 widens it), `revision int
    NOT NULL DEFAULT 0`, `created_at`, `updated_at`.
  - `property_snapshot`: `application_id pk → application`, `source CHECK IN ('lookup','manual')`,
    `parcel_id int NULL`, `map_lot text`, `facts jsonb` (M2's facts minus geometry, or the manual
    entry), `parcels_as_of date NULL`, `verified bool`, `disputed bool`, `note text`.
  - `application_item`: `id uuid pk`, `application_id`, `kind text` (`building` | `component`),
    `position int`, `created_at`, `removed_at NULL`.
  - `answer`: `seq bigserial pk`, `application_id`, `field_id text`, `item_id uuid NULL →
    application_item`, `value jsonb NULL` (NULL clears), `set_by text`, `set_at timestamptz`.
    Index `(application_id, field_id, item_id, seq DESC)`.
  - `section_note`: the same insert-only shape, with `section_id` and `text`.
  - `attachment`: `id uuid pk`, `application_id`, `field_id`, `item_id NULL`, `filename`,
    `content_type`, `size_bytes`, `sha256 char(64)`, `storage_key text UNIQUE`, `created_at`,
    `removed_at NULL`.
- `answer` and `section_note` get the event table's `BEFORE UPDATE OR DELETE` refusal trigger
  (reuse `event_append_only()`).

- [ ] **Step 1:** Write tests:
  - `test_tables_exist`;
  - `test_answer_is_insert_only` (an UPDATE raises `ProgrammingError`, as in M1's event test);
  - `test_snapshot_source_is_checked`;
  - `test_downgrade_removes_tables` (runs `alembic downgrade 0004`, then `upgrade head`).
- [ ] **Step 2:** Run `portal/vm.sh run 'cd portal/api && .venv/bin/pytest tests/test_applications_schema.py -q'`.
  Expected: FAIL (no tables).
- [ ] **Step 3:** Write the migration.
- [ ] **Step 4:** Run the same command. Expected: PASS. Then run the whole suite.
- [ ] **Step 5:** Commit `portal: application records (M4 Task 1)`.

---

## Task 2: The form-definition format and loader

**Files:**
- Create: `portal/api/portal_api/forms/formdefs.py`
- Create: `portal/api/tests/test_formdefs.py` and `portal/api/tests/fixtures/forms/` (small valid
  and broken definitions)

**Interfaces:**
- YAML shape (one file per form and version, in `portal_api/forms/definitions/forms/`, named
  `<form-key-with-dashes>.v<N>.yaml`):
  - Top level: `key`, `version`, `ruleset_key`, `official_title`, `include: [cover-sheet.v1]`,
    `sections: [...]`.
  - Each **section**: `id`, `official_title`, `chapter` (plain wizard chapter title), `repeat:
    {kind, add_label, min, max}` or absent, `status`/`approved_by`/`approved_on`, and `fields: [...]`.
  - Each **field**:
    - `id`, `official_label`;
    - `source` (`question` | `property` | `account` | `derived` | `at_submit` | `staff`);
    - for `property` and `derived`: `from` (a property key, or `<section>.<field>`);
    - `may_correct: bool` (a property value the applicant may change, which makes it a question
      prefilled from the snapshot);
    - for `question`:
      - `label`, `help`, `why` (a citation);
      - `type` (`text` | `longtext` | `number` | `choice` | `multichoice` | `yesno` | `date` |
        `uses` | `point` | `upload`);
      - `unit`, `min`, `max`, `options: [{value, label, official}]`;
      - `required: bool`, `allow_unknown: bool`, `show_if`;
    - `compare` (optional; M6 uses it);
    - `status` and the approval fields.
- `load_form(key: str, version: int, ruleset: Ruleset, root: Path | None = None) -> FormDef`
  (cached per key and version, with the cover sheet merged in first).
- `latest_version(key, root=None) -> int`.
- `form_drafts(form: FormDef) -> list[DraftEntry]`.
- `FORM_KEYS = ("use_permit", "small_project_plan", "entrance_permit")`, matching
  `applications.yaml`.
- Dataclasses `FormDef(key, version, ruleset_key, official_title, sections)`, `Section(...)`,
  `Field(...)`, `Option(value, label, official)`, `Repeat(kind, add_label, min, max)`.
  `FormDef.fields()` yields `(section, field)`.
- `DefinitionError` is reused from `definitions.py`.
- Validation, which raises `DefinitionError` naming the file and the id:
  - ids are unique across the merged form;
  - the `type` is known; `choice`/`multichoice` have options with unique values;
  - `min` ≤ `max`;
  - `show_if` passes `expr.validate`, and its paths start with `answers.`, `item.` or `property.`;
  - every `why` resolves (`ruleset.cite`);
  - `ruleset_key` equals the pinned key;
  - `from` names a known property key (`map_lot`, `location`, `acres`, `districts`, `streets`,
    `on_state_highway`) or an existing field;
  - a `question` field has a label and a type; `upload` fields are never `required`;
  - repeat `min` ≤ `max`;
  - an approved entry names `approved_by` and `approved_on`, using `_check_status` from
    `definitions.py`.

- [ ] **Step 1:** Write tests:
  - `test_valid_fixture_loads`, which checks the merged field order (cover first);
  - one `test_rejects_*` per validation rule above, each with its own broken fixture;
  - `test_form_version_is_pinned` (with v1 and v2 fixtures, `load_form(k, 1)` returns v1 and
    `latest_version` returns 2);
  - `test_drafts_lists_sections_and_fields`.
- [ ] **Step 2:** Run the tests. Expected: FAIL (no module).
- [ ] **Step 3:** Implement. Move `_check_status` and `_check_cite` from `definitions.py` into a
  small shared helper only if both files need them unchanged. Otherwise import them.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `portal: form-definition format and loader (M4 Task 2)`.

---

## Task 3: The three forms and the cover sheet (content)

**Files:**
- Create in `portal/api/portal_api/forms/definitions/forms/`: `cover-sheet.v1.yaml`,
  `use-permit.v1.yaml`, `small-project-plan.v1.yaml`, `entrance-permit.v1.yaml`
- Test: `portal/api/tests/test_form_content.py`

Transcribe the field inventory above. Every entry is `status: draft`. Plain questions aim at about an
8th-grade reading level: short words, one idea, units and an example in the help.

- [ ] **Step 1:** Write tests:
  - `test_every_packet_field_is_present`: a literal list of the packet's official labels per
    section, copied from the inventory tables, compared with each form's `official_label`s;
  - `test_every_field_has_a_source`;
  - `test_building_classes_follow_article_5`: the options' `official` names equal the nine
    classes in `ruleset.cite("5.1.c.1")`'s text;
  - `test_no_standard_met_column`: no field label contains "Standard Met";
  - `test_no_verdict_words_in_form_text`: labels, help and option labels against the M1 list;
  - `test_mainedot_question_shows_unless_known_off_highway`: evaluate its `show_if` with
    `on_state_highway` true, false and null, expecting shown, hidden, shown;
  - `test_all_entries_start_as_drafts`;
  - `test_form_keys_match_applications_yaml`: `FORM_KEYS` are exactly the `in_portal: true`
    applications.
- [ ] **Step 2:** Run the tests. Expected: FAIL (no files).
- [ ] **Step 3:** Write the four YAML files.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `portal: the three application forms and the cover sheet, as drafts (M4 Task 3)`.

---

## Task 4: The condition language, ready for the browser

The TypeScript evaluator now runs in applicants' browsers, so close the parity gaps the M3 review
deferred, and add the `item.` scope.

**Files:**
- Modify: `portal/api/portal_api/forms/expr.py`, `portal/web/src/forms/expr.ts`,
  `portal/web/src/forms/expr-fixtures.json`
- Create: `portal/web/src/forms/applicability.ts`, `portal/web/src/forms/applicability.test.ts`,
  `portal/api/portal_api/forms/applicability-fixtures.json` (shared; the web test imports it by
  relative path as M3's fixtures are shared)
- Test: `portal/api/tests/test_expr.py`, `portal/api/tests/test_applicability.py`

**Interfaces:**
- `validate` rejects a non-scalar value for `eq`, `ne` and `has` in both languages. TypeScript `get`
  uses `Object.hasOwn`.
- `shown(show_if: dict | None, data: dict) -> bool`. It is `True` unless `evaluate` returns
  `False`. The TS twin is `shown(showIf, data): boolean`.
- `data` shape: `{"answers": {field_id: value}, "item": {field_id: value}, "property": {...}}`.
  An `{"unknown": true}` answer reads as missing, so a comparison against it gives `None`.

- [ ] **Step 1:** Add fixtures:
  - `eq_with_list_is_invalid`;
  - `prototype_key_is_missing` (`answers.constructor`);
  - `unknown_answer_reads_as_missing`;
  - `unknown_show_if_is_shown`;
  - `item_scope`.
  Write the Python and TS tests that run both fixture files.
- [ ] **Step 2:** Run both suites. Expected: the new fixtures FAIL.
- [ ] **Step 3:** Implement in both languages.
- [ ] **Step 4:** Run `pytest tests/test_expr.py tests/test_applicability.py` and `npm test`.
  Expected: PASS, with the same fixture count on both sides.
- [ ] **Step 5:** Commit `portal: condition language parity and item scope (M4 Task 4)`.

---

## Task 5: Answers — checking values and working out what applies

**Files:**
- Create: `portal/api/portal_api/forms/answers.py`, `portal/api/tests/test_answers.py`

**Interfaces:**
- `AnswerError(field_id, reason)`. `reason` is one of `not_a_question`, `wrong_type`,
  `not_an_option`, `out_of_range`, `unknown_not_allowed`, `too_long` (text > 2,000 chars, long text
  > 10,000).
- `check_value(field: Field, value) -> object`. It returns the normalised value: numbers become
  floats, `uses` must be use keys from the pinned ruleset, `point` is `{lon, lat}` with finite
  numbers inside a `bounds` argument (the route passes the active parcels import's extent, with
  `ST_Extent`), `{"unknown": true}` is accepted only if `allow_unknown`, and `None` clears.
- `Current` holds the current values: `answers: dict[(field_id, item_id|None), value]`,
  `items: list[(id, kind, position)]` and `property: dict`.
- `applicable(form: FormDef, cur: Current) -> list[(Section, Field, item_id|None)]` returns the
  question fields shown, in wizard order. Repeat sections appear once per live item, and `item.`
  reads that item's answers.
- `missing(form, cur) -> list[(field_id, item_id)]` returns the required applicable questions with
  no value. An `{"unknown": true}` answer is not missing.
- `printed(form, cur) -> list[(Section, item_id|None, list[(Field, value)])]` returns what the
  official form shows: applicable fields only, with `property`, `derived` and `account` fields
  resolved.

- [ ] **Step 1:** Write tests:
  - `test_check_value_*`, one per reason, plus the happy path for each type;
  - `test_not_owner_adds_owner_questions`;
  - `test_floor_heights_follow_stories`;
  - `test_components_ask_roof_only_for_additions_and_garages`;
  - `test_hidden_answers_are_kept_not_counted` (Review Focus 2);
  - `test_unknown_is_not_missing`;
  - `test_removed_item_drops_its_questions`;
  - `test_printed_resolves_property_and_derived_fields`.
  All run against the real forms from Task 3.
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `portal: answer checking and applicability (M4 Task 5)`.

---

## Task 6: The applications API

**Files:**
- Create: `portal/api/portal_api/applications.py` (database functions),
  `portal/api/portal_api/routes/applications.py`, `portal/api/portal_api/routes/forms.py`
- Modify: `portal/api/portal_api/main.py` (include the routers),
  `portal/api/tests/conftest.py` (a `signed_in(client, email)` helper if none exists, and a
  `two_applicants` fixture)
- Test: `portal/api/tests/test_applications.py`

**Interfaces:**
- `GET /api/forms/{key}` returns the latest version as JSON. Each `why` becomes `{cite, text}`
  (the Code text from `ruleset.cite`). Answers: 404 for an unknown key; `503 form_not_approved` on
  any draft unless allowed. Public and lookup-rate-limited, like the screener.
- `GET /api/forms/{key}/v/{version}` returns a pinned version (for existing applications).
- `POST /api/applications` (signed in) takes `{form_key, property: {source: "lookup", parcel_id} |
  {source: "manual", map_lot, district_code|null}, disputed, note, use_key?}` and returns 201
  `{id}`.
  - For a lookup, the server recomputes facts with `property.facts`, so the browser's copy is not
    trusted. If parcels are unavailable it answers `503 property_unavailable` (the page falls back
    to manual entry).
  - A manual entry sets `verified=false`.
  - A `use_key` prefills the Use Form's "Uses to be Established".
  - For a Small Project Plan, one `building` item is created.
  - Events: `application.created`.
- `GET /api/applications` returns the caller's applications: `id`, `form_key`, `official_title`,
  `map_lot`, `updated_at`, `status`.
- `GET /api/applications/{id}` returns `{form_key, form_version, ruleset_key, revision, property,
  items, answers: [{field_id, item_id, value}], notes: [{section_id, item_id, text}], attachments,
  missing, newer_version: bool}`.
- `PUT /api/applications/{id}/answers` takes `{base_revision, changes: [{field_id, item_id, value}]}`.
  - It checks every change with `check_value`, all or nothing: one bad change gives 422 with
    `[{field_id, item_id, reason}]` and saves nothing.
  - `base_revision` ≠ `revision` gives `409 {detail: "changed_elsewhere", revision}`.
  - Otherwise it inserts the rows, adds 1 to `revision`, appends `application.answers_saved` with
    the field and item ids, and returns `{revision, missing}`.
- `POST /api/applications/{id}/items {kind, base_revision}` and `DELETE …/items/{item_id}` (soft
  delete, never below `min`) follow the same revision rule.
- `PUT …/notes {base_revision, section_id, item_id, text}` (≤ 10,000 chars) follows the same
  revision rule.
- All of these answer 404 when the application is not the caller's.

- [ ] **Step 1:** Write tests:
  - `test_create_from_lookup_snapshots_server_facts` (the client sends a wrong `map_lot`; the
    stored one is the server's);
  - `test_manual_property_is_not_verified`;
  - `test_create_refused_while_form_has_drafts` (with production defaults, using a `one_form_draft`
    fixture like M3's `one_draft`);
  - `test_create_requires_sign_in`;
  - `test_answers_round_trip_and_history_is_kept` (two saves produce two rows, and the GET shows
    the latest);
  - `test_bad_change_saves_nothing`;
  - `test_stale_revision_is_refused` (Review Focus 1);
  - `test_items_add_and_remove_respect_min`;
  - `test_notes_round_trip`;
  - `test_other_applicant_gets_404_everywhere` (loops over every route with B's session on A's ids);
  - `test_events_name_fields_not_values` (the payload has no submitted value);
  - `test_application_keeps_its_form_version` (a v2 fixture root gives `newer_version: true`, and
    the GET still lists v1's fields);
  - `test_use_key_prefills_uses_to_be_established`;
  - `test_forms_endpoint_includes_code_text`.
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement. Answers are read with `DISTINCT ON (field_id, item_id) … ORDER BY seq
  DESC`. A NULL `value` means cleared.
- [ ] **Step 4:** Run the whole suite on the VM. Expected: PASS.
- [ ] **Step 5:** Commit `portal: applications API — drafts, answers, items, notes (M4 Task 6)`.

---

## Task 7: The file store and the virus scanner

**Files:**
- Create: `portal/api/portal_api/storage.py`, `portal/api/portal_api/scan.py`,
  `portal/api/tests/test_storage.py`, `portal/api/tests/test_scan.py`
- Modify:
  - `portal/api/portal_api/config.py`: add `s3_endpoint`, `s3_bucket` (`portal-uploads`),
    `s3_access_key`, `s3_secret_key`, `s3_region` (`us-east-1`), `clamd_host`, `clamd_port`
    (3310), `upload_max_bytes` (26,214,400) and `upload_limit_per_hour` (60);
  - `portal/api/portal_api/main.py`: `create_app(…, store=None, scanner=None)`. The defaults are
    `S3Store(settings)` and `ClamdScanner(settings)`;
  - `portal/api/requirements.txt`: boto3 and python-multipart, pinned;
  - `portal/deploy/compose.yml`: a `minio` service (pinned tag, no published ports, volume
    `uploads`, root credentials from `.env`, a bucket created by a one-shot `minio/mc` service or
    by `S3Store.ensure_bucket()` at API start) and a `clamav` service (`clamav/clamav:<pinned
    1.x>`, no published ports, volume for signatures). Both join the default network; the `api`
    gets the `PORTAL_S3_*` and `PORTAL_CLAMD_*` environment variables;
  - `portal/deploy/compose.dev.yml`: the same two services, on `127.0.0.1:9000` and
    `127.0.0.1:3310`;
  - `portal/deploy/env.example`: `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`, with a note that
    the password must be URL-safe;
  - `.github/workflows/portal.yml`: a `minio` service on the `api` job, with
    `PORTAL_TEST_S3_ENDPOINT` set.

**Interfaces:**
- `ObjectStore` protocol: `put(key: str, data: bytes, content_type: str) -> None`,
  `get(key) -> Iterator[bytes]`, `ensure_bucket() -> None`. Implementations: `S3Store(settings)`
  (boto3, `endpoint_url`, path-style addressing) and `MemoryStore()` (tests).
- `StoreUnavailable(Exception)`.
- `ScanResult(clean: bool, signature: str | None)`; `Scanner` protocol `scan(data: bytes) ->
  ScanResult`.
- `ClamdScanner(host, port, timeout=30)` speaks clamd's `zINSTREAM` (4-byte big-endian chunk
  lengths, zero terminator). It reads `stream: OK` as clean and `stream: <sig> FOUND` as infected.
  Anything else, or a socket error, raises `ScannerUnavailable`.
- `FakeScanner()` (tests only) marks data containing the EICAR string as infected. It lives in
  `tests/`, never in `portal_api/`.

- [ ] **Step 1:** Write tests:
  - `test_memory_store_round_trip`;
  - `test_s3_store_round_trip` (skipped unless `PORTAL_TEST_S3_ENDPOINT` is set; CI and the VM
    set it);
  - `test_clamd_protocol_clean_and_found` (against a fake clamd on a local socket thread that
    checks the chunk framing and replies);
  - `test_clamd_garbage_reply_is_unavailable`;
  - `test_clamd_refused_connection_is_unavailable`;
  - `test_real_clamd_finds_eicar` (skipped unless `PORTAL_TEST_CLAMD_HOST` is set; run on the VM);
  - `test_production_app_builds_real_scanner` (`create_app(settings)` with no scanner gives
    `ClamdScanner`).
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement. Add the compose services. Pin image tags only after `docker pull`
  succeeds on the VM.
- [ ] **Step 4:**
  - Start the dev services with `portal/vm.sh run 'sudo docker compose -f
    portal/deploy/compose.dev.yml up -d --wait'`.
  - Run the suite with `PORTAL_TEST_S3_ENDPOINT=http://127.0.0.1:9000
    PORTAL_TEST_CLAMD_HOST=127.0.0.1`. Expected: PASS, including the two integration tests (not
    skipped).
- [ ] **Step 5:** Commit `portal: file store and virus scanner (M4 Task 7)`.

---

## Task 8: Uploads

**Files:**
- Create: `portal/api/portal_api/uploads.py` (type sniffing),
  `portal/api/portal_api/routes/attachments.py`, `portal/api/tests/test_uploads.py`
- Modify: `portal/api/portal_api/main.py`, `portal/deploy/caddy/Caddyfile` (`request_body
  max_size 26MB` on `/api/applications/*/attachments`)

**Interfaces:**
- `sniff(head: bytes) -> str | None` returns the content type from magic bytes:
  - `%PDF-` → `application/pdf`;
  - `FF D8 FF` → `image/jpeg`;
  - the PNG signature → `image/png`;
  - `....ftypheic|heix|hevc|mif1|msf1` at offset 4 → `image/heic`;
  - anything else → `None`.
- `POST /api/applications/{id}/attachments` (multipart: `field_id`, `item_id?`, `file`) returns
  201 `{id, filename, size_bytes, content_type}`.
  - Order of checks:
    1. ownership (404);
    2. the field is an `upload` question in this form (422 `not_an_upload_field`);
    3. the per-applicant hourly limit (429);
    4. read at most `upload_max_bytes + 1` bytes (413 `too_large`; the file is never read past
       the limit);
    5. sniff (415 `unsupported_type`);
    6. scan (422 `infected`; 503 `scanner_unavailable`);
    7. SHA-256, store under `applications/{application_id}/{attachment_id}` (503
       `store_unavailable`);
    8. the row, then the `attachment.added` event (sha256, size, type, no filename).
  - Filenames are kept for display only, trimmed to 200 chars, with path separators and control
    characters removed.
- `GET /api/attachments/{id}` streams the file to its owner, with `Content-Type` from the row,
  `Content-Disposition: attachment; filename*=UTF-8''…` and `X-Content-Type-Options: nosniff`.
  It answers 404 otherwise.
- `DELETE /api/attachments/{id}` sets `removed_at` and appends `attachment.removed`. The stored
  object stays (history).

- [ ] **Step 1:** Write tests (with `MemoryStore` and the tests' `FakeScanner`):
  - `test_pdf_jpeg_png_heic_accepted`;
  - `test_renamed_executable_is_refused` (MZ header, `.pdf` name, `application/pdf` declared);
  - `test_oversized_upload_is_refused_without_reading_it_all` (a generator body that counts the
    bytes read);
  - `test_infected_upload_stores_nothing` (EICAR inside a PDF: no row, no object);
  - `test_scanner_down_refuses_upload` (a scanner raising `ScannerUnavailable` gives 503 and
    nothing stored);
  - `test_store_down_leaves_no_row`;
  - `test_upload_limit_per_hour`;
  - `test_not_an_upload_field`;
  - `test_download_is_owner_only_and_not_sniffable`;
  - `test_filename_is_sanitised`;
  - `test_removed_attachment_not_listed_but_kept`.
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the whole suite. Expected: PASS.
- [ ] **Step 5:** Commit `portal: uploads — type-checked, size-limited, scanned (M4 Task 8)`.

---

## Task 9: Starting an application (web)

**Files:**
- Create: `portal/web/src/applications.ts` (API client), `portal/web/src/pendingStart.ts`,
  `portal/web/src/pages/ApplyStart.tsx`, and tests beside each
- Modify:
  - `portal/web/src/pages/Results.tsx`: "Start this application" on `in_portal` outcomes;
  - `portal/web/src/pages/Verify.tsx`: resume a pending start;
  - `portal/web/src/pages/MyApplications.tsx`: list drafts with "Continue";
  - `portal/web/src/App.tsx`: the routes `/apply/:formKey`, `/applications/:id`,
    `/applications/:id/review`

**Interfaces:**
- `applications.ts`:
  - `getForm(key, version?)`;
  - `createApplication(body)`;
  - `listApplications()`;
  - `getApplication(id)`;
  - `saveAnswers(id, baseRevision, changes)`, which returns `{revision, missing}`, `{conflict:
    revision}` or `{invalid: [...]}`;
  - `addItem`, `removeItem`, `saveNote`;
  - `uploadFile(id, fieldId, itemId, file, onProgress)`, using `XMLHttpRequest` for progress and
    mapping 413, 415, 422 infected, 429 and 503 to plain messages;
  - `removeAttachment(id)`.
  - Refusals use M3's shapes: `"not_approved" | "unavailable" | "signed_out"`.
- `pendingStart.ts`: `savePendingStart({formKey, property, useKey})`, `takePendingStart()` (reads
  and clears). Both use `localStorage` inside try/catch, so storage that is blocked or full means
  "nothing pending" and the page asks for the property again.
- `ApplyStart` (`/apply/:formKey`):
  1. With no chosen property it sends the applicant to `/where` and back.
  2. Signed out, it saves a pending start and goes to `/signin`.
  3. Signed in, it creates the application and goes to `/applications/:id`.
  4. Lookup down (503 `property_unavailable`) → the manual property form.

- [ ] **Step 1:** Write tests:
  - `pendingStart`: "survives a new tab" (simulate with a fresh `sessionStorage` and the same
    `localStorage`), "is taken once" and "blocked storage is nothing pending";
  - `Verify` "resumes a pending start";
  - `Results` "offers Start only for the three portal applications";
  - `ApplyStart` "sends a signed-out visitor to sign in with the start saved" and "falls back to
    manual property when lookup is down";
  - `MyApplications` "lists drafts with Continue".
- [ ] **Step 2:** Run `portal/vm.sh run 'cd portal/web && npm test'`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the web tests. Expected: PASS. Then run `npm run build`.
- [ ] **Step 5:** Commit `portal: start an application from the screener (M4 Task 9)`.

---

## Task 10: The wizard (web)

**Files:**
- Create:
  - `portal/web/src/forms/wizard.ts`: the screen list from the definition, the answers and the
    property;
  - `portal/web/src/pages/Wizard.tsx`;
  - `portal/web/src/components/QuestionField.tsx`: one widget per type;
  - `portal/web/src/components/WhyWeAsk.tsx`;
  - `portal/web/src/components/UploadField.tsx`;
  - `portal/web/src/components/PointField.tsx`, which reuses `ParcelMap` with the lot outlined
    and a pin;
  - tests beside each
- Modify: `portal/web/src/pages/UsePicker.tsx`, to pull its group-and-search list into a reusable
  `UsesField` that the `uses` type uses

**Interfaces:**
- `screens(form, current): Screen[]`. A `Screen` is `{chapter, section_id, item_id, field}`, one
  question per screen, in order, filtered by the shared `shown` rule. After a repeat section's
  last question comes an `{add: kind}` screen ("Add another building?").
- `Wizard`:
  - It shows the chapter as a heading and a step count within the chapter.
  - Next saves the answer, then advances. Back does not save.
  - "I don't know yet" sets `{unknown: true}` where it is allowed.
  - A save failure keeps the answer on screen with "We couldn't save that — try again".
  - A 409 shows "This application was changed in another tab or window", with "Load the latest"
    and "Keep mine" (the second resends on the new revision).
  - The last screen goes to the review page.
  - The URL carries the screen (`?s=<section>.<field>[.<item>]`), so a reload or Back keeps the
    place.
- `WhyWeAsk` is a HeroUI Disclosure: "Why we ask", then the citation and the Code's text.

- [ ] **Step 1:** Write tests:
  - `wizard.ts`: "one screen per applicable question", "owner questions appear only when not the
    owner", "repeat offers to add another", "uses the shared shown rule";
  - `Wizard`: "saves on Next and advances", "keeps the answer when the save fails", "warns when
    the application changed in another tab" (Review Focus 1), "offers I don't know yet only where
    allowed", "rejects a number out of range with a plain message", "reload resumes at the same
    screen";
  - `UploadField`: "shows each refusal in plain words";
  - `PointField`: "saves the tapped point".
- [ ] **Step 2:** Run the web tests. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the web tests. Expected: PASS. Run the build. Click through each form on the
  dev stack at phone width (Chrome device mode).
- [ ] **Step 5:** Commit `portal: the application wizard (M4 Task 10)`.

---

## Task 11: Review and edit (web)

**Files:**
- Create: `portal/web/src/pages/Review.tsx`, `portal/web/src/components/OfficialSection.tsx`, and
  tests

**Interfaces:**
- `Review` (`/applications/:id/review`) renders the form as it will print. It reads the
  section-by-section layout from the API's `GET` together with a client `printed()` in
  `forms/applicability.ts` (the TS twin of Task 5's `printed`). One case added to the shared
  applicability fixtures checks that both sides print the same fields. It shows:
  - the official title;
  - one block per section (one per building and per component) with the official labels and the
    values;
  - property values marked "from the Town's maps — staff confirm";
  - "property not verified" when the property was entered by hand;
  - unknown answers as "Not known yet";
  - fields filled later as "Signed when you submit" or "Office use";
  - a "Still to answer" list linking into the wizard;
  - the notes, printed under their sections.
- Each section has:
  - **Edit**, which shows the section's questions in place, saving with the same validation and
    the same 409 handling;
  - **Add more detail**, a text area saved with `saveNote`.
- After an edit, any newly applicable unanswered question puts "A few new questions apply" at the
  top, with Continue. It opens the wizard with `?only=` and the new screens, and comes back here
  (Review Focus 2).
- "Submit" is shown disabled with "Coming soon" (M6).

- [ ] **Step 1:** Write tests:
  - "prints official labels, not questions";
  - "marks property facts and manual property";
  - "edit in place saves and re-renders";
  - "sends the applicant through only the new questions";
  - "Add more detail prints under its section";
  - "lists what is still to answer";
  - "has no verdict words" (renders every form and checks the text against the M1 list).
- [ ] **Step 2:** Run the web tests. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the web tests. Expected: PASS. Run the build.
- [ ] **Step 5:** Commit `portal: review and edit (M4 Task 11)`.

---

## Task 12: The forms review sheet, README and roadmap

**Files:**
- Modify: `portal/api/portal_api/forms/__main__.py` (a `forms-sheet` subcommand),
  `portal/README.md`, `plans/2026-10-14-applicant-portal-roadmap.md`, `OPEN_ITEMS.md`
- Create: `portal/api/tests/test_forms_sheet.py`,
  `memos/2026-10-21-application-forms-for-approval.md` (generated)

**Interfaces:**
- `python -m portal_api.forms forms-sheet` prints Markdown. For each form, then each section,
  then each field it gives:
  - the official label;
  - the source;
  - the plain question and help;
  - the options (official ↔ plain);
  - `show_if` in words. A small renderer covers the operators the forms use, e.g. "asked when:
    the applicant is not the owner"; an operator it doesn't know prints the raw condition;
  - the citation with the Code text quoted;
  - the status line (M3's `_status_line`).

  It opens with the decisions above and these questions for the chair:
  - Is a site sketch required for a Small Project Plan?
  - Name added to the Owner and Agent blocks.
  - The dropped "Standard Met?" column.
  - Special Use Building added.
  - The blank-packet check.

- [ ] **Step 1:** Write tests: `test_sheet_lists_every_field_of_every_form`,
  `test_sheet_quotes_code_text`, `test_sheet_renders_conditions_in_words`,
  `test_sheet_marks_drafts`.
- [ ] **Step 2:** Run the tests. Expected: FAIL.
- [ ] **Step 3:** Implement. Generate the memo.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 4b:** Update the docs:
  - README: "Applying" (forms, approval, uploads, MinIO and ClamAV, where files live);
  - roadmap status: M4 built, forms awaiting the chair;
  - OPEN_ITEMS: the blank packet; the site-sketch question; O5 still open.
- [ ] **Step 5:** Commit `portal: application forms review sheet and docs (M4 Task 12)`.

---

## Task 13: Journeys and accessibility (Playwright, on the VM)

**Files:**
- Create: `portal/web/playwright.config.ts` (projects `desktop` 1280×800 and `phone` = Playwright's
  "Pixel 7"; `baseURL` from `PORTAL_E2E_URL`), `portal/web/e2e/helpers.ts` (sign in by reading the
  link from Mailpit's API at `PORTAL_E2E_MAILPIT`), `portal/web/e2e/use-permit.spec.ts`,
  `small-project-plan.spec.ts`, `entrance-permit.spec.ts`, `refusals.spec.ts`
- Modify: `portal/web/package.json` (`@playwright/test`, `@axe-core/playwright`, pinned; script
  `e2e`), `portal/README.md` (how to run)

Each journey runs signed in against the dev stack (API with `PORTAL_ALLOW_DRAFT_RULES=true`, real
MinIO and ClamAV):
1. screener;
2. property;
3. Start;
4. every question, with one "I don't know yet", one upload (a small PDF fixture), and for the Small
   Project Plan a second building and a deck;
5. review shows every official field filled or marked;
6. Edit one answer so new questions apply, answer them, and return;
7. Add more detail;
8. reload, and the answers are still there.

Each page visited runs an axe check that fails on serious or critical violations.

`refusals.spec.ts`:
- the EICAR file is refused with the plain message;
- a renamed `.exe` is refused;
- a second tab's save is warned about.

- [ ] **Step 1:** Write the specs.
- [ ] **Step 2:** On the VM, run `npx playwright install --with-deps chromium` once, then
  `portal/vm.sh run 'cd portal/web && PORTAL_E2E_URL=http://127.0.0.1:5173 PORTAL_E2E_MAILPIT=http://127.0.0.1:8025 npm run e2e'`
  (dev API and `npm run dev` running). Expected: 8 journeys (3 forms × 2 widths + refusals × 2)
  pass, with no serious or critical axe findings.
- [ ] **Step 3:** Fix anything found and re-run. Keep the passing report output for the PR
  description.
- [ ] **Step 4:** Commit `portal: application journeys and accessibility checks (M4 Task 13)`.

---

## Task 14: LAN stack and demo

- [ ] Run `portal/vm.sh lan`. MinIO and ClamAV start, and ClamAV's first signature download takes
  a few minutes, so `--wait` covers it via the healthcheck: `clamdcheck.sh` in the official
  image.
- [ ] On https://192.168.1.6 at phone width, complete one application of each kind to review.
  Upload a photo from the phone (HEIC on an iPhone). Download it back.
- [ ] Run the full API suite on the VM with both integration variables set, and `npm test`.
  Expected: all pass. Record the counts in the PR description.
- [ ] Commit any fixes. Then the whole-branch review (fresh reviewer, most capable model) against
  this plan and the spec, before the PR.

## Done when (from the roadmap)

- A signed-in applicant completes each of the three applications to review-and-edit at desktop and
  phone width (Task 13 journeys green).
- Every official field is filled or marked (`test_every_field_has_a_source`, and the review
  page's journey check).
- Uploads are scanned and size- and type-limited (Task 8 tests, and the real-ClamAV test on the
  VM).
- The forms review sheet is in front of the chair. Production keeps refusing the forms until the
  chair approves them.
