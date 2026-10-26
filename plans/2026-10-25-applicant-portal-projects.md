# Applicant Portal — projects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the portal into an app where a signed-in person starts a project, names its parts, and sees the permits, reviews, fees and clocks it needs worked out by the approved rules. The project is sent to the Town as one unit and stays editable until staff lock it.

**Architecture:**
- **API:** `application` becomes `project`, with `project_part`, `project_form`, `submission` and `review`. Answers, notes and files move to the project; the account holds the applicant's details.
- **Rules:** a new data file, `parts.yaml`, says what each part asks and which rule inputs it fills. The screener's `run()` is called once per part (and per chosen use) to give the reviews. Those are priced from the Town's fee schedule (`fees.yaml`) and timed by the Code's clocks, which start at the staff lock.
- **Web:** the window becomes Home · Project · Messages · You. The project dashboard is home. Parts open into the existing cards; check pages and the buildings list stay.

**Tech Stack:** FastAPI, Postgres, Alembic, pytest; React 19, HeroUI 3, Tailwind 4, Vite, Vitest, Playwright + axe.

**Spec:** `specs/2026-10-25-applicant-portal-projects.md` (approved 2026-10-25, its §12 settled). It revises `specs/2026-10-25-applicant-portal-task-list.md`, whose card rules all stand. **Prototype:** https://claude.ai/artifact/V5GqmeZQ2RiVQhydtLjq2U (flow only; its permit names and fees are examples).

**Branch:** `portal-projects`, cut from `portal-design-pass` at 2d71fc7. PR #20 can merge first; this branch then rebases onto `main`. Push only on the chair's OK.

## Global Constraints

- Applicant text: plain words; no verdict words (approved, denied, compliant, meets, fails, violates); no "Why", no Code citations on applicant screens.
- Never guess a legal value. Every new question, part, plain clock sentence and fee mapping lands as `status: draft` in the YAML, for the chair's approval through the forms sheet. The exceptions are the fee schedule itself (approved by the chair on 2026-10-25, brief §12.5) and the rules (already approved).
- Everything in the task-list brief's §4 still holds: card values, tokens, Tabler icons at 3.49.0, the near-black Continue, no teal filled buttons.
- **Sign in first.** Every page except Home's sign-in card and `/signin/verify` sends a signed-out person to Home.
- Answers stay insert-only, and every write carries `base_revision` (409 on a stale one). After the lock, every applicant write is refused with 409 `locked`.
- Clocks start at the lock (brief §12.1). Business days count Monday to Friday. The Town's holidays are not in the ruleset, so "Decision due by" for a business-day clock says "about": "Decision due by about November 14".
- VM work: `portal/vm.sh sync|run|lan`, always with `</dev/null`. Typecheck with `npx tsc --noEmit -p tsconfig.json`, never `tsc -b`. Restart the dev API after a YAML change, by the pid on :8000. Alembic migrations run on the VM.
- Commits: stage by name, never `git add -A`; end every commit with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. New test files are written with the Write tool, so an existing file is never overwritten unread.

## Review Focus

1. **Edits after Send, then the lock.** A save racing a staff lock: the lock takes `base_revision`. The snapshot must hold exactly the answers at that revision, and a save after it must get 409 `locked`, never be half-applied.
2. **A part removed after its form was pinned.** Its answers leave the needs and the printout, and its form unpins when nothing else needs it. Re-adding the part re-pins at the then-current form version. The answers stay insert-only, so they are still in history.
3. **Rules run per part.** Two new buildings, one over 10,000 sf: one Small Project Plan and one Large Project Plan, each listed once, and "needed" beats "may need" for the same review. Homes are summed across new buildings.
4. **Fees.** An application fee counts once per permit per project. Structure counts once per new building. A driveway-only project is a BUILDING PERMIT ($30) with Entrances $0. Two uses give two Use reviews and one $30 USE PERMIT application fee. "Varies" never shows a number.
5. **Due dates.** Calendar days, business days (Monday to Friday, "about") and months, across a month end and a year end; no date before the lock.

---

### Task 1: The account's details

**Files:**
- Create: `portal/api/migrations/versions/0006_account_details.py`
- Modify: `portal/api/portal_api/routes/auth.py` (`GET /api/me` adds `name`, `phone`, `mailing_address`; new `PUT /api/me`)
- Modify: `portal/api/portal_api/forms/definitions/forms/cover-sheet.v1.yaml` (`applicant_name` / `applicant_phone` / `applicant_address` → `source: account`, `from: name|phone|mailing_address`)
- Modify: `portal/api/portal_api/forms/formdefs.py` (`ACCOUNT_KEYS` += `name`, `phone`, `mailing_address`)
- Test: `portal/api/tests/test_auth.py`, `test_form_content.py`

**Interfaces:**
- Produces:
  - `PUT /api/me {name, phone, mailing_address}` → 200 with the updated `{email, role, name, phone, mailing_address}`. Each value is trimmed; blank becomes null. Lengths: 200 for name, 40 for phone, 400 for address. Over a limit → 422.
  - The event `account.details_changed` names the fields that changed, never their values.

- [ ] **Step 1: Write the failing tests**

```python
def test_me_saves_the_details_once(alice): ...          # PUT then GET returns them
def test_me_refuses_overlong_details(alice): ...         # 422
def test_details_change_event_names_fields_not_values(alice, engine): ...
def test_cover_sheet_takes_the_applicant_from_the_account(forms): ...  # source account for the three
```

- [ ] **Step 2:** Run `portal/vm.sh run 'cd portal/api && .venv/bin/python -m pytest -q -p no:warnings tests/test_auth.py tests/test_form_content.py' </dev/null`. Expected: the new tests FAIL.
- [ ] **Step 3:** Implement: migration (`ALTER TABLE applicant ADD COLUMN mailing_address text`), the route, the YAML change (drafts), `ACCOUNT_KEYS`.
- [ ] **Step 4:** Run the whole API suite. Expected: exit 0.
- [ ] **Step 5:** Commit: `portal: the applicant's details on the account (projects Task 1)`.

### Task 2: Projects in the database

**Files:**
- Create: `portal/api/migrations/versions/0007_projects.py`
- Create: `portal/api/portal_api/projects.py` (replaces `applications.py`, which is deleted at the end of Task 3)
- Test: `portal/api/tests/test_projects_schema.py`

**Interfaces:**
- Produces (tables, brief §5.1):
  - `project(id, applicant_id, title, ruleset_key, status CHECK IN ('draft','submitted','locked','decided'), revision, created_at, updated_at, submitted_at, locked_at, locked_by)`
  - `property_snapshot.project_id`
  - `project_part(id, project_id, kind, position, created_at, removed_at)`
  - `project_form(project_id, form_key, form_version, PRIMARY KEY (project_id, form_key))`
  - `answer` / `section_note` / `attachment`, with `project_id` and `part_id` replacing `application_id` and `item_id`
  - `submission(id, project_id, seq, locked_at, locked_by, snapshot jsonb, sha256)`, insert-only by trigger
  - `review(id, submission_id, review_key, use_key, permit_key, reviewer, status, submitted_at, decision_at)`
- The conversion, in the same migration: each `application` → a `project` (`title` = the form's `official_title`, `status` `draft`) plus one `project_form` row. Its items become parts: `building` → `building`, `component` → `addition`. A form with no items gains one part: `use_permit` → `use`, `entrance_permit` → `driveway`, a `small_project_plan` without items → `building`.
- `projects.py` functions (signatures only; bodies follow `applications.py`):
  - `create(conn, applicant_id, ruleset_key, title) -> str`
  - `owned(conn, project_id, applicant_id) -> Row | None`
  - `bump(conn, project_id, base_revision) -> int | None`
  - `parts(conn, project_id) -> list[dict]`
  - `add_part(conn, project_id, kind) -> str`
  - `remove_part(conn, project_id, part_id) -> None`
  - `answers(conn, project_id) -> dict`
  - `save_answers(conn, project_id, changes, by) -> None`
  - `copy_part_answers(conn, project_id, fields, source_id, part_id) -> None`
  - `forms(conn, project_id) -> dict[str, int]`
  - `pin_forms(conn, project_id, wanted: dict[str, int]) -> None`: pins forms newly applying and unpins forms no longer applying (Review Focus 2)
  - `lock(conn, project_id, base_revision, staff_id, snapshot) -> int | None`: the submission's seq, or None when stale

- [ ] **Step 1: Write the failing tests:**
  - the migration converts a seeded application with two building items and one component into a project with three parts, its answers re-keyed;
  - `submission` refuses UPDATE and DELETE;
  - `pin_forms` pins and unpins;
  - `lock` with a stale revision returns None and writes nothing.
- [ ] **Step 2:** Run `tests/test_projects_schema.py`. Expected: FAIL.
- [ ] **Step 3:** Implement the migration (upgrade and downgrade) and `projects.py`.
- [ ] **Step 4:** Run the API suite. `test_applications.py` still passes: its routes keep working on `applications.py` until Task 3.
- [ ] **Step 5:** Commit: `portal: projects, parts, forms, submissions and reviews in the database (projects Task 2)`.

### Task 3: Parts and the project routes

**Files:**
- Create: `portal/api/portal_api/forms/definitions/parts.yaml`
- Create: `portal/api/portal_api/forms/definitions/forms/project-questions.v1.yaml`
- Create: `portal/api/portal_api/forms/parts.py` (loader)
- Create: `portal/api/portal_api/routes/projects.py`
- Delete: `portal/api/portal_api/routes/applications.py`, `portal/api/portal_api/applications.py` (and their tests, ported)
- Modify: `portal/api/portal_api/main.py`, `portal/api/portal_api/routes/attachments.py`
- Test: `portal/api/tests/test_parts.py`, `portal/api/tests/test_projects.py` (ports every behaviour of `test_applications.py`)

**Interfaces:**
- `parts.yaml`: one entry per part (brief §4), in tile order, each `status: draft`:

```yaml
- id: building
  label: A new building
  icon: building-cottage
  repeats: true
  sections: [small_project_plan:building, small_project_plan:building_location, small_project_plan:building_details,
             small_project_plan:building_mass, small_project_plan:building_windows]
  rule: {project: build, building.kind: new}
  inputs: {building.gross_floor_area_sf: floor_area, building.new_dwelling_units: dwelling_units}
```

  - The others:
    - `addition`: sections `small_project_plan:component`; rule `{project: build, building.kind: addition}`; inputs `{building.gross_floor_area_sf: added_floor_area}`.
    - `renovation`: sections `project_questions:renovation`; rule `{project: build, building.kind: renovation}`; inputs `{building.total_floor_area_sf: renovation_total_floor_area}`.
    - `site`: sections `project_questions:site_work`; rule `{project: build, building.kind: site}`; inputs `{building.parking_spaces: parking_spaces}`.
    - `use`: sections `use_permit:existing`, `use_permit:proposed`, `use_permit:use_documents_section`; rule `{project: use}`; inputs `{use_key: proposed_uses}`, one run per value.
    - `driveway`: sections `entrance_permit:entrance`; rule `{project: driveway}`.
    - `divide`: sections `project_questions:division`; rule `{project: divide}`; inputs `{division.lots_after: lots_after, division.divided_last_5_years: divided_last_5_years}`.
    - `other`: sections `project_questions:other`; rule `{project: other}`.
  - Project-level inputs:
    - `building.homes_within_5_years`: from `homes_last_5_years`;
    - `property.*`: from the snapshot.
- `project-questions.v1.yaml` (key `project_questions`): questions for no official form, never printed (`printed: false` on the form, a new loader key).
  - Sections `renovation`, `site_work`, `division`, `other`, `project`.
  - Fields `renovation_total_floor_area`, `renovation_building`, `parking_spaces`, `lots_after`, `divided_last_5_years`, `other_description`, and `homes_last_5_years` (in `project`, shown when any new building has `dwelling_units` ≥ 1).
  - Plus `added_floor_area` in the Small Project Plan's `component` section, printed.
  - Wording as today's screener (brief §6.2), all `status: draft`.
- Routes (brief §5.4): `POST /api/projects {property, parts: [ids], title?}` → 201 `{id}`. Rules:
  - the property is validated as `POST /api/applications` does today;
  - unknown part → 422 `unknown_part`;
  - no parts → 422 `no_parts`.
  The other routes: `GET /api/projects`, `GET /api/projects/{id}`, `PUT …/answers`, `POST …/parts {kind, base_revision, copy_from?}`, `DELETE …/parts/{part_id}`, `PUT …/notes`, `PUT …/title`, `POST …/submit`, `…/attachments`, and the staff test seam `POST /api/projects/{id}/lock` (allowed only when `settings.allow_test_lock`; Milestone 6 replaces it).
  - `GET` returns `{id, title, status, revision, property, parts, answers (with carried false), notes, attachments, forms: {key: version}, missing, needs}`. `needs` is Task 4's.
  - Writes after the lock → 409 `locked`. Submit with anything required missing → 422 `incomplete` with `missing`.
- The work's "Type of project" prints from the parts (brief §4): the printout's value for `work_kinds` is derived and never stored.

- [ ] **Step 1: Write the failing tests:**
  - `parts.yaml` loads, and every section it names exists;
  - project creation pins the forms its parts need;
  - adding and removing a part re-pins (Review Focus 2);
  - submit, then edit (still `submitted`), then the seam's lock, then 409 `locked` (Review Focus 1);
  - every `test_applications.py` behaviour, ported: carry tests become "the account fills the applicant", Copy Building 1 becomes `copy_from` on parts;
  - `/api/screener` is gone (404).
- [ ] **Step 2:** Run `tests/test_parts.py tests/test_projects.py`. Expected: FAIL.
- [ ] **Step 3:** Implement. Regenerate the forms memo (`python -m portal_api.forms forms-sheet`), which now has a section for `project_questions` and for `parts.yaml`.
- [ ] **Step 4:** Run the API suite. Expected: exit 0.
- [ ] **Step 5:** Commit: `portal: parts and the project routes (projects Task 3)`.

### Task 4: Needs — reviews, fees and clocks

**Files:**
- Create: `portal/api/portal_api/forms/definitions/fees.yaml`
- Create: `portal/api/portal_api/forms/needs.py`
- Modify: `portal/api/portal_api/forms/definitions/applications.yaml` (each application gains `clock_plain` per clock key, `status: draft`)
- Modify: `portal/api/portal_api/forms/screener.py` (`run()` unchanged; its pydantic `Answers` stays as the input contract)
- Test: `portal/api/tests/test_needs.py`, `portal/api/tests/test_fees.py`

**Interfaces:**
- `fees.yaml`: the brief §7 table verbatim, plus:
  - `source: {title: "Planning Fee Schedule", as_of: 2025-08-25, url: https://drive.google.com/file/d/1f2ZNZcp0ESJU3uDRK7aEFEooCpzGo5uB/view, read_on: 2026-10-25}`;
  - `approved_by: "Ben Frey, Planning Board chair"`, `approved_on: 2026-10-25`.
  - Each permit: `{key, name, application_fee: 30 | "varies" | null, reviews: [{key, name, fee: 0 | 30 | "varies" | {per_sf: 0.10}}]}`.
  - `review_map` (brief §7): `{small_project_plan: [building_permit, small_project_plan], large_project_plan: [building_permit, large_project_plan], entrance_permit: [building_permit, entrances], structure: [building_permit, structure], use_permit: [use_permit, basic_use], residential_companion: [use_permit, residential_companion_use], expanded_use: [use_permit, expanded_use], special_permit: [use_permit, special], subdivision: [subdivision, subdivision_major]}`.
- `needs.py`:
  - `needs(project: ProjectState, ruleset, defs, fees) -> dict` returns:
    - `permits: [{key, name, application_fee, reviews: [{review_key, use_key?, name, reviewer, certainty, in_portal, fee, clocks: [{label, plain, days, basis, due?}]}]}]`;
    - `application_fees_total`;
    - `notes` (the rules' notes);
    - `town_only`.
  - It runs `screener.run()` once per building-type part (with that part's `building.*` inputs), once per chosen use, and once for each of driveway, divide and other, then merges by `review_key` (+ `use_key`), with `needed` beating `may_need` (Review Focus 3).
  - It adds `structure` once per new-building part (brief §12.3).
  - `due` comes only with a lock date: `due_date(start: date, days: int, basis: "calendar"|"business"|"months") -> (date, approximate: bool)`. Business days skip Saturday and Sunday and return `approximate=True`.
- `clock_plain`: one sentence per clock key, e.g. `small_project_decision: "The Code Enforcement Officer decides within 10 days of accepting your project."`. `due` reads "Decision due by November 14" (or "by about …").

- [ ] **Step 1: Write the failing tests** (`test_needs.py` runs the real `rules.yaml`, `applications.yaml` and `fees.yaml`):

```python
def test_building_and_driveway_is_one_building_permit(): ...  # $30; Small Project Plan $0, Structure $30, Entrances $0
def test_two_new_buildings_two_structures_one_application_fee(): ...  # Structure ×2 ($60), $30 once
def test_one_large_one_small_building(): ...                   # both reviews, each once
def test_needed_beats_may_need(): ...
def test_new_homes_are_summed_across_buildings(): ...          # 2 + 1 → subdivision needed
def test_two_uses_two_use_reviews_one_fee(): ...
def test_driveway_only_pays_the_building_permit(): ...
def test_varies_never_shows_a_number(): ...                    # plumbing, if a rule ever names it
def test_same_outcomes_as_the_screener(): ...                  # every rule in rules.yaml: screener answers ↔ an equivalent project
def test_due_dates(): ...                                      # calendar across a month end; business (about); months; none before the lock
# test_fees.py
def test_fees_yaml_matches_the_schedule(): ...                 # every line of brief §7, exact
def test_every_review_maps_to_a_fee_line(): ...                # every applications.yaml key + structure
```

- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement `fees.yaml`, `needs.py`, `clock_plain`; wire `needs` into `GET /api/projects/{id}` and into the lock's snapshot and `review` rows.
- [ ] **Step 4:** Run the API suite. Expected: exit 0. Regenerate the forms memo (it lists `clock_plain` and the fee map as drafts).
- [ ] **Step 5:** Commit: `portal: what a project needs — reviews, fees and clocks (projects Task 4)`.

### Task 5: The web's project store

**Files:**
- Create: `portal/web/src/projects.ts` (the API client: types `Project`, `Part`, `Needs`, `Permit`, `ReviewNeed`; functions `getMe`/`putMe`, `createProject`, `listProjects`, `getProject`, `saveAnswers`, `addPart(id, rev, kind, copyFrom?)`, `removePart`, `saveNote`, `setTitle`, `submitProject`)
- Rename and modify: `portal/web/src/app/ApplicationStore.tsx` → `app/ProjectStore.tsx` (`useProject()`; same queue, autosave, conflict and `flush`; `parts` in place of `items`; `needs`; `status`, with writes refused locally when `locked`)
- Modify: `portal/web/src/forms/applicability.ts`, `forms/steps.ts`, `forms/tasks.ts` (read a project: the forms pinned, the parts as items)
- Delete: `portal/web/src/applications.ts` (moved into `projects.ts`)
- Test: `portal/web/src/projects.test.ts`, `app/ProjectStore.test.tsx` (ports `ApplicationStore.test.tsx`)

**Interfaces:**
- Produces: `useProject(): { project, form (the pinned forms merged into one FormDef, sections tagged with their form key), cur, needs, status, saveState, setAnswer, flush, addPart, removePart, saveNote, setTitle, submit, reload }`.
- The merged `FormDef` keeps today's shape, so `cardsOf`, `stepModels` and the card UI are unchanged. Its steps are the parts (one step per part kind present) plus `about_you` and `your_lot`.

- [ ] **Step 1:** Write the failing tests: the client's request bodies and paths; the store's queue across `addPart`; 409 `locked` → `saveState` "locked" with no retry; the merged form has one step per part present.
- [ ] **Step 2:** Run `npx vitest run src/projects.test.ts src/app/ProjectStore.test.tsx`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the web suite and `tsc`. Expected: pass. `ApplicationPage` is ported in Task 7; until then it imports from `ProjectStore` (rename only; ruling if needed).
- [ ] **Step 5:** Commit: `portal: the web's project client and store (projects Task 5)`.

### Task 6: Home and starting a project

**Files:**
- Rewrite: `portal/web/src/pages/Home.tsx`:
  - signed out: the seal, "Town of Newcastle — Permits", and the sign-in card;
  - signed in: Start a new application · Continue an application · Your applications.
- Create: `portal/web/src/start/NewProject.tsx` (the three start cards of brief §3.3, reusing the card parts, `Where.tsx`'s search, map and "Is this your property?", and the part tiles from `parts` in the form JSON)
- Modify: `portal/web/src/App.tsx` (routes: `/` Home, `/new` NewProject, `/projects/:id/*` the project, `/messages`, `/you`; `/start*`, `/apply/*` and `/applications/*` redirect to `/`; every route but `/` and `/signin/verify` needs a session)
- Delete:
  - `pages/Start.tsx`, `pages/Results.tsx`, `pages/UsePicker.tsx`, `start/StartFlow.tsx`, `start/startScreens.ts`, `screener.ts`, `pendingStart.ts`, `pages/ApplyStart.tsx`;
  - `pages/MyApplications.tsx`, folded into Home;
  - and their tests.
- Test: `portal/web/src/pages/Home.test.tsx`, `start/NewProject.test.tsx`

**Interfaces:**
- Consumes: `getMe`/`putMe`, `createProject` (Task 5); `GET /api/forms/parts` (Task 3 exposes `parts.yaml` with the forms).
- The default title: the part labels joined with "and", plus " at " and the street (brief §3.3), e.g. "A new building and a driveway at 461 Sheepscot Road". Lower-case after the first part.

- [ ] **Step 1:** Write the failing tests:
  - signed out, `/`, `/new` and `/projects/x` all show the sign-in card;
  - signed in, Home shows the two buttons and the list, newest first, with pills;
  - Continue with no project in progress says "You have no application in progress.";
  - card 1 is skipped when the account has name, phone and address;
  - card 1's Continue sends `PUT /api/me`;
  - card 3 needs a part, and "Go to my project" posts the parts and lands on `/projects/{id}`;
  - `/start` redirects to `/`.
- [ ] **Step 2:** Run the new tests. Expected: FAIL.
- [ ] **Step 3:** Implement and delete what goes.
- [ ] **Step 4:** Run the web suite and `tsc`. Expected: pass.
- [ ] **Step 5:** Commit: `portal: Home and starting a project; "Do I need a permit?" goes (projects Task 6)`.

### Task 7: The project dashboard and its parts

**Files:**
- Rewrite: `portal/web/src/shell/AppShell.tsx` (the window: desktop sidebar Home · Project · Messages · You under the seal; phone bottom tab bar with the same four, Tabler `home`, `clipboard-list`, `message`, `user`; Save and close goes)
- Create: `portal/web/src/app/Dashboard.tsx` (brief §3.4, every item)
- Rename and modify: `app/ApplicationPage.tsx` → `app/ProjectPage.tsx`:
  - routes `/projects/:id` (dashboard), `/projects/:id/:part?screen=&item=`, `/projects/:id/:part/check?item=`, `/projects/:id/send`;
  - the cards, check pages and buildings list as today, with a part's Back from its first card going to the dashboard;
  - the "About you" task opens from the dashboard's You card.
- Delete: `shell/TaskList.tsx` (its pills move into the dashboard rows).
- Modify: `controls/Icon.tsx` (add `clipboard-list`, `message`, `pencil`)
- Test: `app/Dashboard.test.tsx`, `app/cards.test.tsx` (ported to projects), `shell/AppShell.test.tsx`

**Interfaces:**
- Consumes: `useProject()` (Task 5), `needs` (Task 4).
- Dashboard pieces:
  - `PartRow({part, summary, status})`;
  - `AddTiles({kinds})`;
  - `NeedsPanel({needs})`: a permit as a 14 px semibold heading with its application fee ("Building Permit · $30 when you send"); its reviews as rows (name; the reviewer, 12 px secondary; the fee, "No permit fee" or "$30"; the plain clock sentence; "May be needed — the Code Enforcement Officer confirms"; "Not in the portal yet — the Town Office takes this one");
  - the things-left pill, using the new tokens `--app-warn-bg` and `--app-warn-text` (3:1 and 4.5:1 tests in `tokens.test.ts`).

- [ ] **Step 1:** Write the failing tests:
  - the dashboard shows the parcel card, one row per part with its summary and pill, and the add tiles for the parts not chosen;
  - adding a part opens its first card;
  - the needs panel for a building and a driveway reads exactly as Task 4's first test, in words;
  - the title renames;
  - "2 things left" counts the parts and the About-you task with required blanks;
  - the phone shows the tab bar and the desktop the sidebar;
  - every `cards.test.tsx` behaviour, ported to `/projects/…`.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the web suite and `tsc`. Expected: pass.
- [ ] **Step 5:** Commit: `portal: the project dashboard; parts open into their cards (projects Task 7)`.

### Task 8: Check and send, Messages, You

**Files:**
- Create: `portal/web/src/app/SendPane.tsx` (brief §3.5: things to finish first; the project at a glance; what's due when you send; the official forms with View, shown but inert until Milestone 5, reading "Printing arrives in the next update"; **Send to the Town**, and the confirmation sheet of brief §5.3)
- Create: `portal/web/src/pages/Messages.tsx` (the empty state, word for word from brief §3.6), `pages/You.tsx` (details with Change → `PUT /api/me`; Sign out)
- Delete: `app/ReviewPane.tsx`, `app/OfficialGroup.tsx` and their tests (the printout replaces them in Milestone 5; `display()` moves to `app/format.ts` for the check pages)
- Test: `app/SendPane.test.tsx`, `pages/Messages.test.tsx`, `pages/You.test.tsx`

**Interfaces:**
- Consumes: `useProject().submit()` → `POST …/submit`. After it, the status pill reads Sent, the dashboard says "Sent October 25. You can still add to your project until the Town locks it for review.", and editing still works.
- When `locked`: the dashboard and cards are read-only. Each card's controls are disabled with the line "The Town is reviewing this project; changes go through the Code Enforcement Officer." Messages becomes the way in (Milestone 6).

- [ ] **Step 1:** Write the failing tests:
  - Send is disabled-looking but answers with the first thing to finish while anything required is blank;
  - the confirmation lists the permits and the application-fee total;
  - Send → Sent → still editable;
  - a locked project is read-only, with the line;
  - Messages' empty state;
  - You saves and signs out.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the web suite and `tsc`. Expected: pass.
- [ ] **Step 5:** Commit: `portal: Check and send, Messages and You (projects Task 8)`.

### Task 9: Journeys, the design finish, docs

**Files:**
- Modify: `portal/web/e2e/helpers.ts` (sign in first; the start cards; the dashboard walk: open each part, complete its cards and check page, back to the dashboard; Send), all the specs, `cards.spec.ts` → `projects.spec.ts`
- Modify: `portal/web/DESIGN.md`, `.impeccable/design.json` (via `impeccable-documenter`), `.impeccable/surfaces/portal-web-src-app-tsx.md` (the direction contract → this brief and the prototype)
- Modify: `portal/README.md`, `OPEN_ITEMS.md` (O1 closed; the forms, parts, project questions, `clock_plain` and fee map come back to the chair as drafts), `plans/2026-10-14-applicant-portal-roadmap.md`, `specs/2026-10-14-applicant-portal-design.md` (a "superseded by" note at §3, §4, P5 and O1)

- [ ] **Step 1:** Update the journeys:
  - a building-and-driveway project sent, with Structure and Entrances on the dashboard;
  - a use project with two uses;
  - a refusal journey (uploads, the second tab);
  - the phone: the tab bar, a long check page's Done on screen;
  - axe on Home, the start cards, the dashboard, a card, a check page and Check and send, light and dark.
- [ ] **Step 2:** Run the dev journeys. Expected: all pass on desktop and phone.
- [ ] **Step 3:** Run the design finish:
  - capture the four-mode tour;
  - hand it to `impeccable-finish-reviewer` with the prototype and the task-list comp as the bar, and act on its disposition once;
  - rerun the critique (two isolated assessments) and record the score against 32/40.
- [ ] **Step 4:** Docs, `vm.sh lan`, then the LAN journeys.
- [ ] **Step 5:** Commit: `portal: journeys, design finish and docs for projects (projects Task 9)`.

### Task 10: Whole-branch review

- [ ] **Step 1:** A fresh Opus reviewer on `git diff 2d71fc7..HEAD`, against this brief, the plan's Review Focus and the ledger's rulings.
- [ ] **Step 2:** One fix pass, each fix RED→GREEN; full suites, dev and LAN journeys.
- [ ] **Step 3:** Report the rulings, the deferred minors and the critique score.

**Done when:**
- The API suite, web suite, typecheck, build and detector all pass.
- The journeys pass (dev and LAN).
- `test_same_outcomes_as_the_screener` passes over every rule.
- The fee tests match the schedule line for line.
- A sent project is editable, and a locked one is not.
