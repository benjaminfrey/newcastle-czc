# Explanation library, plan 1: the format, the record and Article 2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The library exists as checked files with a live rule nobody can bypass. The chair can
work through Article 2's drafted entries on a review page. His decisions become a commit, the
Board gets a memo to ratify, the chair or the CEO can pull an entry at once, and an amendment
flags the entries it touches.

**Architecture:**
- **A new package, `portal_api/library/`**, holds every library entry and its checks:
  - `model.py`: the entry, its kinds and statuses, and the live rule;
  - `load.py`: loading and checking the files in `library/entries/*.yaml`;
  - `render.py`: filling slots from the standards for one district and building;
  - `readability.py`: the reading-grade check;
  - `changes.py`: the section-level change list between two rulesets;
  - `memo.py`: the Board memo;
  - `records.py`: the decision and pull tables;
  - `__main__.py`: the CLI.
- **The guide keeps working:**
  - `guide/content.py` takes its entries from the library, not from its own `entries.yaml`;
  - `guide/engine.py` shows an entry only when its mode allows it;
  - `guide/checks.py` sends a standard with no visible entry to the Town.
- **Staff:** a `require_staff` dependency, `routes/library.py` (batches, preview, decide, pull) and
  a web review page at `/library`, in the guide's theme.
- **The record:**
  - `decisions` (on the VM) prints pending decisions as JSON;
  - `apply` (on the Mac) writes them into the YAML files for a commit;
  - `ratify` stamps a Board vote;
  - `memo` writes the Board memo, rendered with `build/build-memo.sh`.

**Tech Stack:**
- API: Python 3.14, FastAPI, SQLAlchemy `text()`, Alembic, pytest, PyYAML.
- Web: React 19.3, TypeScript 5.9, MUI 9.5.0, Vitest 5, Testing Library, Playwright 1.64 with axe.
- **No new packages.** The reading grade is computed in-house.

**Spec:** `specs/2026-11-08-applicant-portal-guided-builder-library.md` (approved by the chair
2026-11-08), under `specs/2026-10-30-applicant-portal-guided-builder.md` §6 and §11.

**Branch:** `portal-guided-library-design`, cut from `main` (05d85da), which also carries the
spec. Never rebase a pushed branch.

**Later library plans** (not this one):
- **2.** Fold the existing words in (form strings, `guide/definitions/*.yaml`, `words.ts`) and the
  "So you mean…" templates (spec §4, decision 15).
- **3+.** One batch per Article (3–9), and the interpretations, once the chair and the CEO supply
  their list.
- **Pictures** for the spatial entries beyond stories and setbacks.

## Global Constraints

- **Nothing unapproved reaches the public.** In public mode (`PORTAL_PUBLIC=true`), only live
  entries are shown, and the API refuses to start if `allow_draft_rules` is also set. No setting
  reaches the live rule (spec §5).
- **Live** means `status == "ratified"`. The one exception: `status == "approved"` with
  `approved_on` before `2026-11-08` (`GRANDFATHERED_BEFORE`), for the words approved before this
  design (decision 15). A `pulled` entry, or one with a row in `library_pull`, is never live.
- **The LAN copy** (`allow_draft_rules`) shows every entry that isn't pulled. An entry that isn't
  live raises the draft chip through the existing `drafts` list.
- **A standard with no visible entry goes to the Town** with reason `no_entry`, shown with the
  approved words `town_decides` ("The Town will look at this one"). Its number is never shown
  without an entry (decision 12).
- **Numbers come only from `standards.py`.** Entry text holds `{slot}` placeholders, never typed
  numbers, for district values. A value with `provenance == "override"` is marked as the Town's
  interpretation and cites the chair's decision (decision 16).
- **Never guess a legal value** (CLAUDE.md rule 6). A draft that would need a value the Code
  doesn't state stops. Its question goes in the batch file's `open_questions` list.
- **The never-used words** (`NEVER_WORDS`) are refused at load in every entry field, not only in
  tests.
- **The ruleset is hash-pinned.** Never edit `portal_api/rulesets/adopted-v1.0/`. Task 3 needs
  Article 9's defined terms. It reads `build/permit-review/rulesets/adopted-v1.0/definitions.json`,
  verifies it against the pinned manifest's `content_sha256["definitions"]`, and copies nothing
  into the pinned directory.
- **New screen words** (the review page, and the interpretation mark) start as drafts in
  `words.ts`, for the chair.
- **Tests run on the VM:**
  `portal/vm.sh run 'cd portal/api && .venv/bin/pytest -q'` for the API, `npm test`,
  `npx tsc --noEmit -p .` and `npm run build` in `portal/web`. The journeys run from the Mac
  against the LAN copy, at no more than 20 sign-ins an hour; this plan's journey uses 1.
- **Commits** are made on this branch only, staged by name, and end with the `Co-Authored-By`
  trailer. Pushing waits for the chair.

## Review Focus

1. **A district where a slot's standard is `not_established` or `cannot_check`.** Expect the entry
   not to render for that district, and the standard to go to the Town with `no_entry`. No blank
   or "None" is ever shown. Test: `test_an_unestablished_value_does_not_render` (Task 2).
2. **Two people deciding the same entry at once** (the chair approves while the CEO pulls).
   Expect the pull to win at once. The approval stays pending and `apply` refuses to approve a
   pulled entry without saying so. Test: `test_apply_will_not_approve_a_pulled_entry` (Task 6).
3. **An edit made on the review page, then a second edit before `apply`.** Expect the last decision
   per entry to win, and exactly one version bump. Test: `test_two_edits_bump_the_version_once`
   (Task 6).
4. **A resident (role `applicant`) calling the staff routes**, or a signed-out caller. Expect 403
   `staff_only` and 401 `signed_out`, with nothing written. Test:
   `test_residents_cannot_reach_the_library` (Task 5).
5. **A YAML file hand-edited between `decisions` and `apply`** (the version on disk no longer
   matches the decided version). Expect `apply` to refuse that entry by name and apply the rest.
   Test: `test_apply_refuses_a_stale_decision` (Task 6).

---

### Task 1: The entry, its statuses and the live rule

**Files:**
- Create: `portal/api/portal_api/library/__init__.py`, `model.py`, `load.py`
- Create: `portal/api/portal_api/library/entries/guide.yaml` (the four entries now in
  `guide/definitions/entries.yaml`, moved unchanged in text, with `kind: standard` for
  `setbacks` and `how_stories_count` and `kind: word` for `use_table` and `use_not_listed`. Their
  comments are dropped, since the files are rewritten by `apply`.)
- Modify: `portal/api/portal_api/guide/content.py` (entries come from `library.load_library()`;
  `_FILES` loses `entries.yaml`; the digest includes the library files)
- Delete: `portal/api/portal_api/guide/definitions/entries.yaml`
- Test: `portal/api/tests/test_library_load.py`

**Interfaces:**
- Produces:
  - `Kind = Literal["standard", "interpretation", "template", "word"]`
  - `Status = Literal["draft", "approved", "ratified", "pulled"]`
  - `GRANDFATHERED_BEFORE = date(2026, 11, 8)`
  - `@dataclass(frozen=True) class LibraryEntry`, with fields:
    - the existing `Entry` fields;
    - `kind`, `standards: tuple[str, ...] = ()`, `slots: dict = {}`, `terms: tuple[str, ...] = ()`,
      `district_notes: dict = {}`;
    - `decided_by`, `decided_on`, `source`;
    - `ruleset: str = "adopted-v1.0"`;
    - `ratified_on`, `ratified_by`;
    - `pulled_on`, `pulled_by`, `pulled_why`, `review_note`;
    - `batch: str` (the file's stem, e.g. `article-02`), set by the loader.
  - `is_live(e: LibraryEntry, pulled: frozenset[str] = frozenset()) -> bool`
  - `@dataclass(frozen=True) class Library: entries: dict[str, LibraryEntry]; open_questions: dict[str, tuple[str, ...]]; digest: str`
  - `load_library(root: Path | None = None) -> Library` (cached on the resolved root, as
    `content._load` is)
  - `LibraryError(Exception)`
- The guide's `Entry` stays the type `content.py` exposes. `Content.entries` maps id to
  `LibraryEntry`, which keeps every attribute `Entry` had.

- [ ] **Step 1: Write the failing tests:**
  - `test_the_four_entries_load_from_the_library`: the same four ids, texts and approvals as
    before;
  - `test_an_unknown_key_is_refused`: today it is silently dropped;
  - `test_ratified_needs_approval_and_a_date`: `ratified` without `approved_by`, `approved_on`,
    `ratified_on` and `ratified_by == "Planning Board"` raises `LibraryError`;
  - `test_pulled_needs_who_when_and_why`;
  - `test_interpretation_needs_who_decided_when_and_source`;
  - `test_never_words_are_refused_in_every_field`: "approved" in `detail` raises;
  - `test_live_rule`: draft False; approved 2026-11-06 True (grandfathered); approved 2026-11-08
    False; ratified True; ratified and in `pulled` False; `pulled` False;
  - `test_a_file_may_list_open_questions`: a top-level `open_questions:` list is kept, by batch.

  A file is a mapping `{entries: [...], open_questions: [...]}`.
- [ ] **Step 2: Run them.** `portal/vm.sh run 'cd portal/api && .venv/bin/pytest -q tests/test_library_load.py'`
  Expected: FAIL, `portal_api.library` not found.
- [ ] **Step 3: Implement `model.py` and `load.py`.** Reuse `forms.definitions._check_cite`. Write
  the status checks fresh, since `_check_status` knows only draft and approved.
- [ ] **Step 4: Run the library tests and `tests/test_guide_*.py`.** Expected: all pass. The guide
  tests that referenced `entries.yaml` through the `copy` fixture now copy `library/entries/` as
  well (update the fixture, and keep the tests' intent).
- [ ] **Step 5: Commit** "library: the entry, its statuses and the live rule (library plan 1, task 1)".

### Task 2: Slots, filled from the standards

**Files:**
- Create: `portal/api/portal_api/library/render.py`
- Modify: `portal/api/portal_api/library/load.py` (check that every slot names a real standard key
  and every `{name}` in the text is a declared slot)
- Test: `portal/api/tests/test_library_render.py`

**Interfaces:**
- The spec's `standard` field is `standards`, a list, here, because one entry may explain field
  keys that the Code treats alike (Task 9 groups them). The loader still refuses two entries
  claiming one key.
- A **standard key** is `dimension:<field_key>` (e.g. `dimension:building_placement.side_setback`)
  or `building:<field>` (e.g. `building:total_stories`). Use `standard_key(s: Standard) -> str` in
  `render.py`.
- A slot is `{name: {standard: <key>, part: "min" | "max" | "raw"}}`. `min` and `max` are filled
  as `f"{n:g} {unit}"`, using the "sq ft" spelling the forms use for `sf`. `raw` fills the
  Standard's `raw` text, for "Permitting Authority".
- Produces:
  - `render(e: LibraryEntry, district_key: str, building: str | None) -> Rendered | None`, where
    `@dataclass(frozen=True) class Rendered: answer: str; detail: str; interpretations: tuple[str, ...]`.
    `interpretations` holds each override note used. When `district_notes` has the district, its
    note is appended to `detail`. A note is part of the entry, so it is approved with it.
  - It returns `None` when any slot's standard is missing for that district and building, or its
    status isn't `checkable` (for `min` and `max`).
  - `entry_for(lib: Library, key: str) -> LibraryEntry | None` returns the entry whose `standards`
    include `key`. The loader refuses two entries claiming the same key.

- [ ] **Step 1: Write the failing tests:**
  - `test_total_stories_fills_from_the_district`: an entry `"At most {stories}."` with
    `{stories: {standard: building:total_stories, part: max}}` renders "At most 2 stories." for
    D1 Residential;
  - `test_an_unestablished_value_does_not_render`: Agricultural Use in D1, whose Total Stories is
    `-`, gives `None`;
  - `test_an_override_value_carries_its_note`: the D6 side setback's override gives
    `interpretations == ("Decided by … on …: …",)`, the note from `standards_overrides.json`;
  - `test_a_placeholder_without_a_slot_is_refused` and `test_a_slot_naming_no_standard_is_refused`
    (at load);
  - `test_a_district_note_joins_the_detail`;
  - `test_two_entries_cannot_claim_one_standard`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Look standards up with `standards_for(district_key)`, matching
  `standard_key(s)` and `s.building`.
- [ ] **Step 4: Run the library tests.** Expected: pass.
- [ ] **Step 5: Commit** "library: slots, filled from the standards (task 2)".

### Task 3: The draft checks: reading grade and defined terms

**Files:**
- Create: `portal/api/portal_api/library/readability.py`, `portal/api/portal_api/library/terms.py`
- Modify: `portal/api/portal_api/library/load.py`
- Test: `portal/api/tests/test_library_checks.py`

**Interfaces:**
- Produces:
  - `grade(text: str, skip: frozenset[str] = frozenset()) -> float`: Flesch–Kincaid grade level.
    Words in `skip` (an entry's terms) and numbers are left out of the count. Syllables come from
    a vowel-group heuristic with silent final "e"; there is no dictionary.
  - `flags(e: LibraryEntry) -> tuple[str, ...]`, the warnings an entry carries:
    - `"grade {g:.1f}"` when above 8.0, over `answer + detail + why`;
    - `"term not in Article 9: {t}"`.
  - These are flags, not refusals (spec §6), and `Library.flags: dict[str, tuple[str, ...]]`
    holds them.
  - `article_9_terms() -> frozenset[str]` reads
    `build/permit-review/rulesets/adopted-v1.0/definitions.json` (path from `Settings` or a
    module constant, relative to the repo root). It refuses with `LibraryError` when the file's
    sha256 differs from the pinned manifest's `content_sha256["definitions"]`. When the file is
    absent (an API container without `build/`), it returns `None`, and the terms flag is skipped
    with one flag on the library: `"article 9 terms not available"`.

- [ ] **Step 1: Write the failing tests:**
  - `test_short_plain_text_is_low_grade`: "Only floors with full-height outside walls count." is
    under 8;
  - `test_a_long_legal_sentence_is_flagged`: a sentence of 40 words with several four-syllable
    words is flagged;
  - `test_terms_are_left_out_of_the_grade`;
  - `test_an_unknown_term_is_flagged`;
  - `test_a_changed_definitions_file_is_refused`: a tmp copy with one byte changed raises.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the library tests.** Expected: pass. Record the four existing entries' grades
  in the ledger.
- [ ] **Step 5: Commit** "library: the reading grade and Article 9 terms (task 3)".

### Task 4: The guide shows only what its mode allows

**Files:**
- Modify: `portal/api/portal_api/config.py` (`public: bool = False`, env `PORTAL_PUBLIC`)
- Modify: `portal/api/portal_api/main.py` (`create_app` raises `RuntimeError("public_with_drafts")`
  when `public` and `allow_draft_rules` are both set)
- Modify: `portal/api/portal_api/guide/engine.py` (`_Build.entry` returns `None` for an entry that
  isn't visible; non-live visible entries go into `drafts`)
- Modify: `portal/api/portal_api/guide/checks.py` (a check whose standard has no visible entry
  becomes a Town item with reason `no_entry`; the visible entry, rendered for the lot's district,
  rides as the check's `why`)
- Modify: `portal/web/src/guide/words.ts` (`unsettled.no_entry` points at the approved
  `town_decides` text, so no new words are needed)
- Modify: `portal/deploy/compose.yml` (`PORTAL_PUBLIC: "true"` on `api`) and
  `portal/deploy/compose.lan.yml` (`PORTAL_PUBLIC: "false"`)
- Test: `portal/api/tests/test_library_modes.py`, plus updates in `test_guide_checks.py`

**Interfaces:**
- Produces:
  - `visible(e: LibraryEntry, *, public: bool, pulled: frozenset[str]) -> bool`: public mode
    returns `is_live`; otherwise it returns not pulled.
  - The engine reads `public` and `pulled` from the request's settings and Task 5's
    `records.pulled(conn)`. Until Task 5 lands, `pulled` is `frozenset()`.

- [ ] **Step 1: Write the failing tests:**
  - `test_public_with_drafts_will_not_start`;
  - `test_public_shows_only_live_entries`: a draft `why` is absent and the turn still renders;
  - `test_lan_shows_a_draft_and_marks_it`: present, and listed in `drafts`;
  - `test_a_standard_with_no_entry_goes_to_the_town`: reason `no_entry`, and the number isn't
    shown;
  - `test_a_standard_with_an_entry_carries_it_filled_in`: the D1 total-stories check's `why` says
    "2 stories";
  - `test_the_packet_keeps_each_entry_id_and_version`: a sent packet's checklist rows carry their
    entry's `id` and `version`, so staff can tell a later change (spec §9). No new storage is
    needed, since `as_sent` keeps the whole body.

  The fixture library has one entry claiming `building:total_stories`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Until Task 9 drafts Article 2, the real library claims no standards,
  so every check would go to the Town on the LAN copy. Gate the `no_entry` fallback behind
  `library_covers_standards: bool` (`Settings`, default `False`). Task 9 turns it on and deletes
  the setting.
- [ ] **Step 4: Run the whole API suite.** Expected: pass (1,528 before this plan, plus the new
  tests).
- [ ] **Step 5: Commit** "library: the guide shows only what its mode allows (task 4)".

### Task 5: Staff, the records and the review API

**Files:**
- Create: `portal/api/migrations/versions/0012_library.py`
- Create: `portal/api/portal_api/library/records.py`, `portal/api/portal_api/routes/library.py`
- Modify:
  - `portal/api/portal_api/auth.py` (`require_staff`, roles `staff` and `admin`, 403 `staff_only`);
  - `portal/api/portal_api/main.py` (include the router; add `"/api/library"` to `_PRIVATE`);
  - `portal/api/portal_api/library/__main__.py` (`role <email> <applicant|staff|admin>`, which
    prints the old and new role).
- Test: `portal/api/tests/test_library_routes.py`

**Interfaces:**
- Tables (raw SQL, as `0011`):
  - `library_decision (id bigserial PK, entry_id text NOT NULL, version int NOT NULL, action text NOT NULL CHECK (action IN ('approve','edit','send_back')), body jsonb, note text, decided_by uuid NOT NULL REFERENCES applicant(id) ON DELETE CASCADE, decided_at timestamptz NOT NULL DEFAULT now(), exported_at timestamptz)`.
    For `edit`, `body` holds the edited `overline`, `answer`, `detail` and `why`.
  - `library_pull (entry_id text PRIMARY KEY, version int NOT NULL, why text NOT NULL, pulled_by uuid NOT NULL REFERENCES applicant(id) ON DELETE CASCADE, pulled_at timestamptz NOT NULL DEFAULT now(), exported_at timestamptz)`.
- `records.py`:
  - `decide(conn, entry_id: str, version: int, action: str, by: str, body: dict | None, note: str | None) -> int`
  - `pending(conn) -> list[dict]`, the last unexported decision per entry
  - `pull(conn, entry_id: str, version: int, why: str, by: str) -> None`
  - `pulled(conn) -> frozenset[str]`
  - `mark_exported(conn, decision_ids: list[int], pull_ids: list[str]) -> None`

  Each write also appends an `event` (`library.decide`, `library.pull`).
- Routes (all `require_staff`):
  - `GET /api/library/batches` returns `[{batch, total, draft, approved, ratified, pulled, pending}]`.
  - `GET /api/library/batches/{batch}` returns `{batch, open_questions, entries: [{entry, flags, code: [{cite, text}], pending, pulled}]}`.
    `code` comes from `load_ruleset().cite`.
  - `GET /api/library/entries/{id}/preview?district=d1&building=Residential` returns the
    `_Build.entry` shape, rendered, or 404 `not_for_this_district`.
  - `POST /api/library/entries/{id}/decision` takes `{version, action, body?, note?}`. It returns
    409 `stale` when `version` isn't the file's version, and 422 when `send_back` has no note or
    `edit` has no body.
  - `POST /api/library/entries/{id}/pull` takes `{version, why}`. The pull takes effect on the next
    request.

- [ ] **Step 1: Write the failing tests:**
  - `test_residents_cannot_reach_the_library`: 403, and 401 signed out, for every route; nothing
    written;
  - `test_role_cli_sets_and_reports`;
  - `test_batches_count_by_status`;
  - `test_a_decision_is_pending_until_exported`;
  - `test_a_stale_version_is_refused`;
  - `test_send_back_needs_a_note`;
  - `test_a_pull_hides_the_entry_at_once`: after the pull, the guide's `why` for that turn is
    absent on the next `GET /guide`, in both modes;
  - `test_preview_fills_the_district`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Wire `records.pulled(conn)` into Task 4's `visible` call.
- [ ] **Step 4: Run the whole API suite.** Expected: pass.
- [ ] **Step 5: Commit** "library: staff, the records and the review API (task 5)".

### Task 6: The record: decisions, apply, ratify

**Files:**
- Modify: `portal/api/portal_api/library/__main__.py`
- Create: `portal/api/portal_api/library/write.py`
- Test: `portal/api/tests/test_library_record.py`

**Interfaces:**
- CLI:
  - `decisions` (VM; reads the DB) prints JSON
    `{"decisions": [...pending rows...], "pulls": [...unexported pulls...]}`.
  - `apply <file.json>` (Mac; files only) rewrites `library/entries/<batch>.yaml`:
    - `approve` sets `status: approved`, `approved_by` (the decider's display name from
      `LIBRARY_PEOPLE`, a module dict of email → name, starting with the chair as "Ben Frey,
      Planning Board chair") and `approved_on` (the decision's date);
    - `edit` replaces the four texts, adds 1 to `version`, sets `status: draft` and keeps
      `review_note`. An edit then needs its own approve: the chair approves the edited text,
      never the text before it (spec §5). The review page offers "Approve" right after an edit.
    - `send_back` sets `status: draft` and `review_note`;
    - a pull sets `status: pulled` and `pulled_on`, `pulled_by`, `pulled_why`.
    - It prints the applied ids and the refused ids, each with its reason. The JSON's ids are
      reused by `mark-exported`.
  - `mark-exported <file.json>` (VM).
  - `ratify <batch> <YYYY-MM-DD>` (Mac) stamps `ratified_on` and `ratified_by: "Planning Board"`
    on every `approved` entry of the batch, then sets `status: ratified`. It refuses when any entry
    of the batch is still a draft, unless `--partial`, which stamps only the approved ones.
- `write.py`: `dump_batch(path: Path, entries: list[dict], open_questions: list[str]) -> None`
  writes keys in a fixed order (`id`, `kind`, `standards`, `overline`, `answer`, `detail`, `why`,
  `slots`, `terms`, `cites`, `picture`, `picture_alt`, then the record fields), so diffs stay
  small. The loader must read back exactly what it wrote.

- [ ] **Step 1: Write the failing tests:**
  - `test_round_trip_is_byte_stable`: load, then dump an unchanged batch, gives the same bytes;
  - `test_apply_approves`;
  - `test_two_edits_bump_the_version_once`;
  - `test_apply_refuses_a_stale_decision`;
  - `test_apply_will_not_approve_a_pulled_entry`;
  - `test_ratify_stamps_the_set`;
  - `test_ratify_refuses_while_drafts_remain`;
  - `test_a_ratified_entry_is_live`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the library tests.** Expected: pass.
- [ ] **Step 5: Commit** "library: decisions, apply and ratify (task 6)".

### Task 7: Amendments flag their entries

**Files:**
- Create: `portal/api/portal_api/library/changes.py`
- Modify: `portal/api/portal_api/library/__main__.py` (`flag --old <ruleset dir> --new <ruleset dir> [--apply]`)
- Test: `portal/api/tests/test_library_changes.py`

**Interfaces:**
- Produces:
  - `section_texts(root: Path) -> dict[str, str]` reads `articles.json` from any ruleset directory
    (no adopted or status check, so drafts can be compared). It maps the cite form
    `"5.7.c.3"` to the node's text.
  - `changed(old: dict, new: dict) -> frozenset[str]`: refs added, removed or with different text.
    A cite counts as changed when it, or any ref under it, changed.
  - `flagged(lib: Library, changed: frozenset[str]) -> list[tuple[str, tuple[str, ...]]]`:
    entry id and its changed cites, for entries not already `pulled`.
  - `flag --apply` sets `status: pulled`, `pulled_why: "Amended: <cites>"`,
    `pulled_by: "the amendment check"` and the date, through `write.dump_batch`. It is run when an
    adopted ruleset is pinned, never for a draft (spec §10).
- A test also guards the pinned library:
  `test_no_live_entry_cites_a_section_changed_since_its_ruleset`. Each live entry's `ruleset` must
  equal `PINNED_KEY`, or it compares that ruleset's texts with the pinned one's when both are on
  disk.

- [ ] **Step 1: Write the failing tests:**
  - `test_identical_rulesets_change_nothing`;
  - `test_a_changed_subsection_flags_its_parent_cite`;
  - `test_flag_lists_only_entries_citing_changes`;
  - `test_apply_pulls_them`;
  - the guard test above.

  Use the vendored `adopted-v1.0` and a tmp copy with one node's text changed.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the library tests**, and once by hand:
  `flag --old portal_api/rulesets/adopted-v1.0 --new ../../build/permit-review/rulesets/draft-v0.22`.
  Expected: tests pass; the hand run lists flagged entries without applying. Record its output in
  the ledger.
- [ ] **Step 5: Commit** "library: amendments flag their entries (task 7)".

### Task 8: The review page

**Files:**
- Create: `portal/web/src/library/` (`api.ts`, `LibraryHome.tsx`, `BatchPage.tsx`,
  `EntryReview.tsx`, `words.ts`, and tests beside each)
- Modify: `portal/web/src/App.tsx` (`/library` and `/library/:batch`, lazy, inside
  `RequireSignIn`, **not** behind `GUIDE_PREVIEW`, since the page is the same at launch)
- Test: `portal/web/src/library/*.test.tsx`, `portal/web/e2e/library.spec.ts`

**Interfaces:**
- Consumes Task 5's routes. `api.ts` follows `guide/api.ts`'s `call` and `read`, adding 403 →
  `"staff_only"`.
- `LibraryHome` lists the batches, with their counts.
- `BatchPage` shows the open questions first, then each entry as an `EntryReview`.
- `EntryReview`:
  - **district and building pickers** (the districts whose standards the entry claims);
  - **the entry**, through `guide/components/entryCard` and the preview route, exactly as a
    resident sees it, with the interpretation mark when `interpretations` is non-empty;
  - **the cited Code text** beside it (below it on a phone);
  - **the flags and the status**, and "Pending: approved by you, not yet recorded" when a decision
    is pending (spec §7);
  - **Approve**, **Edit** (an inline form for the four texts, then Save, which posts `edit`, then
    Approve), **Send back** (a note is required), and **Pull** (a reason is required, with a
    confirming dialog).
- **The words:** new drafts in `src/library/words.ts`, with `LIBRARY_WORD_STATUS = "draft"`:
  - the page title "Explanation library";
  - the button and status words above;
  - the interpretation mark "The Town's reading, where the Code doesn't say";
  - the refusal "This page is for Town staff."

  The draft chip shows through `GuideShell`'s `draft` prop.

- [ ] **Step 1: Write the failing unit tests:**
  - a resident sees "This page is for Town staff." and no entries;
  - the counts show per batch;
  - picking a district fetches its preview;
  - Send back is disabled until a note is typed;
  - Pull asks to confirm;
  - an edit posts `edit` with the four texts, then offers Approve;
  - a pending decision shows the pending line;
  - the interpretation mark shows only with interpretations.
- [ ] **Step 2: Run them.** `npm test -- src/library` Expected: FAIL.
- [ ] **Step 3: Implement**, in `GuideTheme` with `GuideShell`. There are 48 px targets, one `h1`
  per page, and one `h2` per entry; axe runs in the journey.
- [ ] **Step 4: Run `npm test`, `npx tsc --noEmit -p .` and `npm run build`.** Expected: pass.
- [ ] **Step 5: The journey** (`e2e/library.spec.ts`, desktop, 1 sign-in). On the VM, grant
  `staff` to the journey's address with the `role` CLI. Then: open `/library`, open `guide`,
  approve `setbacks`' current version and see it pending, then run axe. Rebuild the LAN copy
  (`portal/vm.sh lan`) and run it. Expected: pass. Clear the journey's decision afterwards with
  `mark-exported`, so the record stays clean.
- [ ] **Step 6: Commit** "library: the review page (task 8)".

### Task 9: Article 2's batch, and the Board memo

**Files:**
- Create: `portal/api/portal_api/library/entries/article-02.yaml`
- Create: `portal/api/portal_api/library/memo.py`, and the `memo <batch>` CLI command
- Modify: `portal/api/portal_api/config.py` (delete `library_covers_standards`; the `no_entry`
  fallback is always on), and its uses
- Create: `memos/2026-11-xx-library-article-02-for-review.md` (the date it is written; generated
  by `memo article-02`)
- Modify: `OPEN_ITEMS.md`
- Test: `portal/api/tests/test_library_article_02.py`, `portal/api/tests/test_library_memo.py`

**Interfaces:**
- `render_memo(lib: Library, batch: str, today: str) -> str` returns markdown in the memo template's
  header form (`**To:**`, `**From:**`, `**Date:**`, `**Re:**`). Its sections:
  - one section per entry: its overline and answer, a table of each district and building with the
    filled answer (or "Goes to the Town" where it doesn't render), why the rule exists, its
    citations, its approval line (or "Draft") and any interpretation notes;
  - the batch's open questions, last.
- The PDF is built with `bash build/build-memo.sh <md> <pdf> "Explanation library: Article 2" "For Planning Board ratification"`.
  The PDF is not committed (release PDFs are gitignored).

- [ ] **Step 1: Size the batch.** Count Article 2's standards:
  - the 18 dimension `field_key`s;
  - the distinct building-matrix row labels across the 13 districts.

  Decide which `field_key`s one entry covers together (e.g. `building_placement.side_setback` and
  `primary_building_placement.side_setback` share an entry if the Code's text treats them alike).
  Record the count and the groupings in the ledger.
- [ ] **Step 2: Write the failing tests:**
  - `test_every_standard_the_guide_checks_has_an_article_2_entry`: every `standard` in
    `turns.yaml` is claimed;
  - `test_every_article_2_entry_cites_article_2_or_9`;
  - `test_every_article_2_entry_renders_for_some_district`;
  - `test_article_2_entries_are_drafts`.
  - `test_the_memo_lists_every_entry_and_the_open_questions`;
  - `test_the_memo_shows_goes_to_the_town_where_a_value_is_missing`.
- [ ] **Step 3: Run them.** Expected: FAIL.
- [ ] **Step 4: Draft the entries** from `source/article-02-*.md`, `source/article-02.typ` and the
  pinned ruleset. Every entry is `status: draft` and `kind: standard`, claims its `standards`,
  fills district numbers only through `slots`, cites the sections it rests on, and links its
  Article 9 terms. Pictures go only on the setback and stories entries, which reuse the existing
  pictures. Where the Code is unclear or silent, write no entry for that standard. Put the question
  in `open_questions`, saying which standard and which district.
- [ ] **Step 5: Run the library tests, then the whole API suite, then the LAN journeys**
  (`guide.spec`, `packet.spec`, `library.spec`; mind the sign-in limit). The guide now shows the
  Article 2 drafts with the draft chip. Expected: all pass, with the guide's two device skips. A
  check that went to the Town before still does, and one that fit before still fits.
- [ ] **Step 6: The memo.** Run `memo article-02 > memos/<date>-library-article-02-for-review.md`
  and build its PDF. This memo is the chair's reading copy, and the Board's after his approval.
- [ ] **Step 7: `OPEN_ITEMS.md`.** Library plan 1 is on its branch. Article 2's batch is ready for
  the chair on the review page, with N open questions. The `staff` role needs granting to the
  chair's and the CEO's addresses (spec §13 item 2). The new review-page words are drafts.
- [ ] **Step 8: Commit.** Then the whole-branch review (one fresh reviewer, the most capable
  model).
