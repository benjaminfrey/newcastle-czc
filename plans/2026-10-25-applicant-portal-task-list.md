# Applicant Portal — tasks and cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the applicant's flow as a task list of short card runs — contained cards with icons, related questions grouped, a check page per task and per building, Copy Building 1 — matching the approved comp value by value.

**Architecture:**
- **Form content:** the grouping lives in the form YAML (`screens:` and each field's `screen:`, now allowed across sections of one step), with new `icon` on options and `copies` on fields.
- **API:** gains Copy Building 1 on the add-item route.
- **Web:** keeps the wizard's screen model (now "cards"), autosave and controls, and replaces the shell with:
  - a task list (sidebar on a desktop, home screen on a phone);
  - one contained card with a progress bar, a sliding body and its own footer;
  - check pages and the items list.

**Tech Stack:** React 19, HeroUI 3, Tailwind 4, Vite, Vitest, Playwright + axe; FastAPI, Postgres, pytest; `@tabler/icons-react` (new).

**Spec:** `specs/2026-10-25-applicant-portal-task-list.md` (approved 2026-10-25). It revises `specs/2026-10-24-applicant-portal-wizard.md`. **Reference comp:** `specs/assets/2026-10-25-task-list-comp.html`; the build matches it, and where the brief's text and the comp disagree, the comp wins.

**Branch:** `portal-design-pass` (PR #20), on top of the wizard (10f7107). Push only on the chair's OK.

## Global Constraints

- Every applicant-facing string: plain words; no "Why", no Code citations, no verdict words (approved, denied, compliant, meets, fails, violates).
- Never guess a legal value. Which fields copy, which questions group, and which icons appear are form content: they print on the forms sheet, and the regrouped forms go back to the chair for approval (brief §11.4).
- Colours only from tokens in `portal/web/src/index.css`. The three new tokens are `--app-edge`, `--app-done-bg` and `--app-done-text` (brief §4.8). `src/theme/tokens.test.ts` must hold:
  - text at 4.5:1;
  - edges at 3:1 against `--app-row`.
  Adjust a value, never the rule.
- Sizes are the brief's §4 values exactly:
  - card: 0.5 px border, 12 px radius;
  - header: 10/16 px padding;
  - progress bar: segments 3 px tall, 3 px apart, 2 px radius;
  - body padding 22/24/18 px; question 20 px weight 500; help 13 px;
  - tiles: min 48 px tall, 10/12 px padding, 0.5 px `--app-edge` border, 8 px radius, 18 px icon, 14 px label; chosen = 1.5 px `--app-label` border;
  - footer: 10/16 px padding; buttons 36 px tall, 8 px radius; Continue filled `--app-label` on `--app-row`;
  - card width 640 px (760 px for the lot drawing or the compass); phone gutter 12 px.
- Icons: `@tabler/icons-react` at one exact version, the newest 3.x at least two weeks old, recorded without a range in `package.json`.
  - Outline only, 18 px, stroke 1.75.
  - A question's tiles have icons on every option or on none.
- Motion: only the card body slides, 300 ms `cubic-bezier(0.32, 0.72, 0, 1)`. With reduced motion, a 120 ms fade.
- VM work: `portal/vm.sh sync|run|lan`, always with `</dev/null`.
  - Typecheck with `npx tsc --noEmit -p tsconfig.json`, never `tsc -b`.
  - Restart the dev API after a YAML change, by the pid on :8000.
- Commits: stage by name; end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **The progress total moving.** An answer that adds or removes a card mid-task (Do you own this property? → the owner card; building type → the homes question) may change the total. Moving forward or back without changing an answer must never change it, and the bar must never show fewer segments than are already answered.
2. **Change from a check page.** Change opens the card and Continue returns to the check page. If the change adds a card (owner = No), that card is asked first, then the check page.
3. **Copy Building 1 edge cases:**
   - Building 1 unfinished or holding "I don't know yet" answers: unknowns copy as unknowns, blanks stay blank.
   - Copying at the 20-building maximum is refused with a message.
   - Copying after Building 1 was deleted: the button names the first remaining finished building.
4. **Task gating.** "Check and send" opens only when every task is done. A task that stops applying (site-only work removes Buildings) must not block it. A task that starts applying again shows as Not started.
5. **A phone with a long card.** On the materials tiles or the walls, the body scrolls between the header and footer. The footer stays reachable when the iOS keyboard is open (`100dvh`, `env(safe-area-inset-bottom)`). Its test lives in Task 8's journey.

---

### Task 1: Form content — cards, icons, copies (API)

**Files:**
- Modify: `portal/api/portal_api/forms/formdefs.py` (`Option.icon`, `Field.copies`, cross-section `screen:` within a step, icon validation)
- Create: `portal/api/portal_api/forms/icons.txt` (the pinned Tabler outline names the loader accepts; one per line; generated once from the pinned package and committed)
- Modify: `portal/api/portal_api/routes/applications.py` (`form_json` serves `icon` and `copies`)
- Modify: `portal/api/portal_api/forms/forms_sheet.py` (prints a card's members together, an option's icon, and "Copied by Copy Building 1")
- Modify: `portal/api/portal_api/forms/definitions/forms/{cover-sheet,small-project-plan,entrance-permit}.v1.yaml`
- Modify: `memos/2026-10-21-application-forms-for-approval.md` (regenerated)
- Test: `portal/api/tests/test_formdefs.py`, `portal/api/tests/test_form_content.py`, `portal/api/tests/test_forms_sheet.py`

**Interfaces:**
- Produces:
  - `Option(value, label, official, icon: str | None = None)`
  - `Field(..., copies: bool = False)`
  - form JSON options gain `"icon"`, fields gain `"copies"`
- A field's `screen:` may name a screen declared in any section of the same step and the same repeat kind (or none). The loader refuses:
  - an unknown screen;
  - a screen whose fields span two repeat kinds;
  - duplicate screen ids within a step;
  - an `icon` not in `icons.txt`;
  - a question whose options carry icons on some but not all;
  - `copies: true` on a field outside a repeat.

The cards (brief §3), as YAML. `screen` ids are new unless marked:
- **cover sheet:**
  - `site`: `lot_width`, `lot_depth` → `lot_size`;
  - `applicant`: `applicant_name`, `applicant_phone`, `applicant_address` → `contact`;
  - `owner`: all four → `owner`;
  - `agent`: all four → `agent`;
  - `deed` unchanged.
- **small project plan:**
  - `ask_first` moves from `dwelling_units` to `renovation_only`; `building_class` keeps it;
  - `building_name` + `dwelling_units` → `about`;
  - `mass_width`, `mass_depth`, `stories`, `floor_area`, `first_floor_elevation`, `floor_height_1..4` → `size` (existing);
  - `roof_style` + `roof_slope` → `roof`;
  - `exterior_finish` + `exterior_finish_other` → `outside`;
  - `front_facing` joins `walls` (compass);
  - `component_kind` + `component_other_name` → `kind`;
  - `component_width`, `component_depth`, `component_height` → `size`;
  - `component_roof_style` + `component_roof_slope` → `roof`;
  - `component_finish` + `component_finish_other` → `outside`;
  - `component_front_facing` joins `walls`.
- **entrance permit:**
  - `driveway_width`, `first_20ft_slope`, `entrance_angle` → `driveway`;
  - `sight_distance_left/right`, `intersection_distance`, `intersection_signal` → `sight` (existing, widened).
- **copies: true:** `building_class`, `renovation_only`, `mass_width`, `mass_depth`, `stories`, `floor_area`, `first_floor_elevation`, `floor_height_1..4`, `roof_style`, `roof_slope`, `exterior_finish`, `exterior_finish_other` (brief §6).
- **icons:** the brief §5 table for `work_kinds`, `component_kind`, `front_facing`, `component_front_facing`. The building-type first step's icons live in the web (it is a control's grouping, not form options; Task 3).

- [ ] **Step 1: Write the failing tests**

```python
# test_form_content.py
def test_a_building_is_eight_cards(spp):        # distinct (screen or field id) among building question fields
    assert cards(spp, "building") == ["building_class", "renovation_only", "about", "setbacks",
                                      "size", "roof", "outside", "walls"]
def test_an_addition_is_seven_cards(spp):
    assert cards(spp, "component") == ["kind", "component_renovation_only", "attached_to", "size",
                                       "roof", "outside", "walls"]
def test_copies_are_the_briefs_list(spp): ...      # exactly the 15 ids above
def test_icons_all_or_none(all_forms): ...         # every choice field: all options have icon, or none
def test_lot_contact_owner_agent_cards(cover): ... # the cover sheet's four new screens and their members
# test_formdefs.py
def test_refuses_icon_not_in_the_set(): ...
def test_refuses_some_icons(): ...
def test_refuses_copies_outside_a_repeat(): ...
def test_refuses_duplicate_screen_ids(): ...
def test_screen_may_span_sections_of_one_step(): ...
def test_refuses_screen_across_repeat_kinds(): ...
# test_forms_sheet.py
def test_sheet_prints_cards_icons_and_copies(): ...
```

`cards(form, kind)` (a test helper): walk that repeat's question fields in asking order (ask_first, then form order). Map each to its `screen` or its own id, and keep the first occurrence.

- [ ] **Step 2:** Run `portal/vm.sh run 'cd portal/api && .venv/bin/python -m pytest -q tests/test_form_content.py tests/test_formdefs.py tests/test_forms_sheet.py' </dev/null`. Expected: the new tests FAIL (unknown keys, wrong card lists).
- [ ] **Step 3:** Implement the loader changes, then the YAML, then the sheet. Regenerate the memo with the sheet's existing command.
- [ ] **Step 4:** Rerun the step 2 command plus the whole API suite. Expected: all pass.
- [ ] **Step 5:** Commit: `portal: forms grouped into cards, with icons and Copy Building 1's fields (task-list Task 1)`.

### Task 2: Copy Building 1 (API)

**Files:**
- Modify: `portal/api/portal_api/routes/applications.py` (`ItemBody.copy_from: str | None`)
- Modify: `portal/api/portal_api/applications.py` (`copy_item_answers`, `COPIED = "copied"`)
- Test: `portal/api/tests/test_applications.py`

**Interfaces:**
- Consumes: `Field.copies` (Task 1).
- Produces: `POST /api/applications/{id}/items {base_revision, kind, copy_from?}`. It returns `{id, revision}`, or:
  - 404 when `copy_from` isn't a live item of this application;
  - 422 `wrong_kind` when its kind differs;
  - 422 `too_many` at the maximum.

  The new item gets the form's defaults, then every `copies` field's current answer from `copy_from` (unknowns included, blanks not), saved with `set_by="copied"`, in the same transaction. An `application.item_added` event carries `copied_from`.
- Web: `addItem(kind, copyFrom?)` in `applications.ts` and the store.

- [ ] **Step 1: Write the failing tests**

```python
def test_copy_brings_exactly_the_copies_fields(client, app_with_building): ...
def test_copy_keeps_unknowns_and_skips_blanks(...): ...
def test_copy_from_another_application_is_404(...): ...
def test_copy_from_a_component_into_buildings_is_422(...): ...
def test_copy_at_the_maximum_is_422_too_many(...): ...
def test_copy_writes_nothing_when_refused(...): ...   # no item row, no answers
```

- [ ] **Step 2:** Run them. Expected: FAIL (422 for the unknown field `copy_from`).
- [ ] **Step 3:** Implement. Validate before `bump`, as `create_application` does for carry.
- [ ] **Step 4:** Run the API suite. Expected: all pass.
- [ ] **Step 5:** Commit: `portal: Copy Building 1 (task-list Task 2)`.

### Task 3: Tokens, icons and the card's parts (web)

**Files:**
- Modify: `portal/web/package.json` (`@tabler/icons-react` exact)
- Modify: `portal/web/src/index.css` (the three tokens, light and dark; `.btn`, `.btn-filled`)
- Modify: `portal/web/src/theme/tokens.ts`
- Modify: `portal/web/src/theme/tokens.test.ts` (adds `edge` at 3:1 against row; `doneText` on `doneBg` at 4.5:1)
- Create: `portal/web/src/controls/Icon.tsx` (`<Icon name size? />`, a static map of only the names in use, so the bundle stays small; unknown name → nothing, plus a dev warning)
- Create: `portal/web/src/shell/Card.tsx` (`Card`, `Card.Header`, `Card.Body`, `Card.Footer`)
- Create: `portal/web/src/shell/ProgressBar.tsx`
- Modify: `portal/web/src/controls/Tiles.tsx` (restyle to brief §4.5; option icons; a `tap?: boolean` prop: inside a set, tiles answer without moving on)
- Modify: `portal/web/src/controls/pickers.tsx` (`BuildingTypeControl` first step: home → `home`, business → `building-store`, smaller → `building-warehouse`, farm → `tractor`, other → `building`)
- Modify: `portal/web/src/applications.ts` (`FormOption.icon?`, `FormField.copies?`)
- Test: `portal/web/src/shell/Card.test.tsx`, `ProgressBar.test.tsx`, `controls/controls.test.tsx`, `theme/tokens.test.ts`

**Interfaces:**
- Produces:
  - `ProgressBar({ count, at }: { count: number; at: number })`: `role="img"` with the label "Question {at+1} of {count}"; segments with `data-on` for index ≤ at.
  - `Card({ wide?: boolean; children })`: 640 px, or 760 px when `wide`.
  - `Card.Header({ title, count?, at? })`: the title, the bar and "{at+1} of {count}" when count is given.
  - `Card.Body({ motionKey, direction, children })`: only this slides.
  - `Card.Footer({ back?: {label, onPress}; next?: {label, onPress} | {hint: string} })`.

- [ ] **Step 1:** Write the failing tests:
  - the bar's aria label and segment count;
  - the header's "3 of 6";
  - Footer: the Back label, Continue filled (`data-filled`), and the hint text when no next is given;
  - Tiles: an option with `icon` renders an `svg` before the label; a chosen tile has `data-chosen`; with `tap={false}`, a tap calls `onValue` but not `onPick`;
  - tokens: the new contrast rules.
- [ ] **Step 2:** Run `npx vitest run src/shell src/controls src/theme`. Expected: FAIL.
- [ ] **Step 3:** Implement. Values come from brief §4, with no other sizes.
- [ ] **Step 4:** Rerun, then the whole web suite and `tsc`. Expected: all pass. Existing tile tests may change only where the brief changed the look.
- [ ] **Step 5:** Commit: `portal: the card, its bar and footer, tiles with icons, three new tokens (task-list Task 3)`.

### Task 4: The task model (web)

**Files:**
- Modify: `portal/web/src/forms/screens.ts`:
  - grouping keyed by `${step}:${itemId}:${screen}` across sections;
  - no `another`/`any` screens;
  - `set` kinds accept tiles, pickers and text;
  - `walls` accepts the facing tiles.
- Modify: `portal/web/src/forms/steps.ts` (task status and the item summary)
- Create: `portal/web/src/forms/tasks.ts`
- Test: `portal/web/src/forms/screens.test.ts`, `steps.test.ts`, `tasks.test.ts`

**Interfaces:**
- Consumes: Task 1's form JSON.
- Produces (`tasks.ts`):
  - `type TaskStatus = { kind: "done" } | { kind: "progress"; answered: number; total: number } | { kind: "todo" }`
  - `taskStatus(form, cur, step: StepModel, visited): TaskStatus`: done when visited, nothing required is missing and the hub has at least its minimum items. "progress" counts cards with every row answered (a form default isn't an answer), out of the cards that apply.
  - `canSend(models, statuses): boolean`: every task done.
  - `cardsOf(form, cur, step, itemId?): Screen[]`: a fields task's cards, or one item's cards.
  - `progressOf(cards: Screen[], at: Screen, answeredBefore: number): { count, at }`: `count` = cards.length, never less than `answeredBefore`.
  - `itemSummary(form, cur, itemId): string`: "28 × 40 ft · 2 floors · 2,240 sq ft · front faces north", or "3 answers to go" while unfinished. Built from the item's own answers, skipping any that are blank.
  - `firstCopySource(form, cur, kind): { id: string; label: string } | null`: the first finished item of that kind.
  - `TASK_ICONS: Record<string, string>` and `TASK_HINTS: Record<string, string>` (brief §4.2 and §5, keyed by step id).

- [ ] **Step 1:** Write the failing tests:
  - a building's cards are the eight of Task 1's list, in order, from a fixture built like the real form;
  - `taskStatus` for todo, progress "2 of 4" and done;
  - a site-only application has no Buildings task, and `canSend` ignores it;
  - `progressOf` never shrinks below answered;
  - `itemSummary` in both forms;
  - `firstCopySource` skips unfinished and deleted items.
- [ ] **Step 2:** Run `npx vitest run src/forms`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun, plus `tsc`. Expected: pass. (ApplicationPage may not compile until Task 6. If not, keep the old exports beside the new ones until Task 6 removes them, and ledger a Ruling.)
- [ ] **Step 5:** Commit: `portal: tasks, cards, progress and item summaries (task-list Task 4)`.

### Task 5: The window — task list, card frame, phone bar (web)

**Files:**
- Rewrite: `portal/web/src/shell/AppShell.tsx`:
  - **desktop:** the sidebar is `TaskList` (compact), and the main area centres the card 32 px from the top on `--app-grouped-ground`;
  - **phone:** a 44 px top bar with ‹ Tasks and the save status, then the card in 12 px gutters, filling to the safe area; the card's footer is its own bottom band, and the body scrolls.
- Create: `portal/web/src/shell/TaskList.tsx` (rows per brief §4.2, used as the sidebar and as the phone's home)
- Delete: `portal/web/src/shell/StepList.tsx`, `StepSidebar.tsx`, `StatusGlyph.tsx`, `Dots.tsx`, `ActionBar.tsx`, `app/AnswerTrail.tsx` and their tests, once nothing imports them
- Modify: `portal/web/src/shell/NavBar.tsx` (the 44 px bar only; no large title)
- Modify: `portal/web/src/shell/types.ts`
- Test: `portal/web/src/shell/TaskList.test.tsx`, `AppShell.test.tsx`, `motion.test.tsx`

**Interfaces:**
- Consumes: `TaskStatus`, `canSend`, `TASK_ICONS`, `TASK_HINTS` (Task 4); `Card` and friends (Task 3).
- Produces:
  - `TaskList({ formTitle, mapLot, saveState, tasks: { id, title, href, status: TaskStatus; current?: boolean }[]; send: { href: string; open: boolean }; compact?: boolean })`
  - `AppShell({ tasks, send, current, formTitle, mapLot, saveState, onDone, onReload, phoneTitle?, children })`: `children` is a `Card`.

- [ ] **Step 1:** Write the failing tests:
  - pills read Done / "2 of 4" / Not started with their token classes;
  - "Check and send" shows no pill and secondary text until open, then links;
  - the whole row is the link;
  - desktop renders the sidebar list plus the card, phone renders the bar plus the card;
  - ‹ Tasks goes to the list;
  - reduced motion uses the fade, and only `Card.Body` carries the motion class.
- [ ] **Step 2:** Run `npx vitest run src/shell`. Expected: FAIL.
- [ ] **Step 3:** Implement. Remove the deleted parts' imports.
- [ ] **Step 4:** Rerun, plus `tsc`. Expected: pass, or failures only in `app/` (Task 6).
- [ ] **Step 5:** Commit: `portal: the task list and the card window (task-list Task 5)`.

### Task 6: The application in cards (web)

**Files:**
- Rewrite: `portal/web/src/app/ApplicationPage.tsx`:
  - routes `/applications/:id` (task list), `/:task` (first card, or the items list for a hub), `?screen=&item=`, `/:task/check` (with `?item=`);
  - keeps the fixes in 10f7107: pending moves, Change from check, tap timer, `commitFocused`, form defaults, the `?start=1` landing.
- Rewrite: `portal/web/src/app/WizardPane.tsx` → `CardBody` content per brief §4.5:
  - a set as a two-column name/field grid;
  - repeated floors under a hairline;
  - "I don't know some of these yet";
  - the walls card's sliders appear once the front is chosen;
  - "Is this right?", the lot drawing and the compass inside a 760 px card.
- Create: `portal/web/src/app/CheckPane.tsx` (the task's or item's answers with Change; Done → task list)
- Create: `portal/web/src/app/ItemsPane.tsx`:
  - summary rows with Change or Finish and Delete;
  - "+ Add a building", "Copy <first finished>" and "Done with buildings";
  - an empty additions task shows only "+ Add an addition, porch or deck" and "No additions" (the old "any" question becomes this card).
- Modify: `portal/web/src/app/ApplicationStore.tsx` (`addItem(kind, copyFrom?)`)
- Test: `portal/web/src/app/wizard.test.tsx` (rewritten as `cards.test.tsx`), `CheckPane.test.tsx`, `ItemsPane.test.tsx`

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces:
  - a task's last card goes to `/:task/check`, and an item's last card to `/:task/check?item=`;
  - an item's check page Done goes to the items list;
  - a fields task's check page Done goes to `/applications/:id` with the next unfinished task highlighted.
  - Back on a task's first card reads "Tasks". In an item, Back on the first card goes to the items list.
  - The footer hint "A tap moves on" appears on the first tap card of an application only (`localStorage` key `portal.taphint.<id>`, read in a try/catch).

- [ ] **Step 1:** Write the failing tests. Keep every behaviour test from `wizard.test.tsx` that still applies, renamed. New tests:
  - a building runs eight cards, then its check page, then the items list;
  - Copy Building 1 calls `addItem("building", "b1")` and opens the new item's check page;
  - Delete on the items list (with a confirmation) is absent on the last required building;
  - a check page's Change returns to the check page (Review Focus 2), and a change that adds a card asks it first;
  - roof shape tiles inside the set don't move on; Continue does;
  - "I don't know some of these yet" marks only the blank values;
  - the walls' sliders appear after the front is chosen;
  - the header reads "Building 1 · A home", and the bar never shrinks (Review Focus 1);
  - the hint shows once.
- [ ] **Step 2:** Run `npx vitest run src/app`. Expected: FAIL.
- [ ] **Step 3:** Implement. Delete `wizard.test.tsx` only once its kept tests live in `cards.test.tsx`.
- [ ] **Step 4:** Run the whole web suite and `tsc`. Expected: all pass.
- [ ] **Step 5:** Commit: `portal: the application as tasks and cards, check pages, the buildings list (task-list Task 6)`.

### Task 7: Check and send, and "Do I need a permit?" in cards (web)

**Files:**
- Modify: `portal/web/src/app/ReviewPane.tsx` (title "Check and send"; reachable only when `canSend`; otherwise the task list with the send row closed)
- Modify: `portal/web/src/forms/steps.ts` (`REVIEW_STEP.title`)
- Rewrite: `portal/web/src/pages/Start.tsx`, `Where.tsx`, `Results.tsx` and `start/StartFlow.tsx` into the same card:
  - header "Your project · 2 of 5", whose total never drops below answered;
  - the plan tiles with icons (brief §5): build → `home-plus`, use → `building-store`, driveway → `road`, divide → `layout-grid`, other → `help-circle`;
  - "What kind of building work?" with its four icons;
  - no intro sentence;
  - the result as the card's 20 px line, with its rows below.
- Test: `ReviewPane.test.tsx`, `Start.test.tsx`, `Where.test.tsx`, `Results.test.tsx`, `StartFlow.test.tsx`

- [ ] **Step 1:** Write the failing tests:
  - `/review` before `canSend` lands on the task list;
  - the start card shows icons on every plan tile;
  - the bar's total for build+new is stable while moving forward;
  - "What you'll need" heads its card with "You'll need a Use Permit";
  - no intro sentence.
- [ ] **Step 2:** Run `npx vitest run src/pages src/start src/app/ReviewPane.test.tsx`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the web suite and `tsc`. Expected: all pass.
- [ ] **Step 5:** Commit: `portal: Check and send, and "Do I need a permit?" in cards (task-list Task 7)`.

### Task 8: Journeys, the design finish, docs

**Files:**
- Modify: `portal/web/e2e/helpers.ts` (`answerScreen` for cards, sets, check pages and the items list), `redesign.spec.ts` (renamed `cards.spec.ts`), and the four application specs
- Modify: `portal/web/DESIGN.md`, `portal/web/.impeccable/design.json` (via `impeccable-documenter`), and `portal/web/.impeccable/surfaces/portal-web-src-app-tsx.md` (direction contract → this brief and the comp)
- Modify: `portal/README.md`, `OPEN_ITEMS.md` (the forms come back for approval; the front-facing question still open), `plans/2026-10-14-applicant-portal-roadmap.md`

- [ ] **Step 1:** Update the journeys. New checks:
  - a Small Project Plan with Copy Building 1;
  - on a phone, the footer stays visible with the keyboard open on a set card (Review Focus 5): focus a field, then assert the Continue button is inside the viewport;
  - axe on the task list, a card and a check page, in light and dark.
- [ ] **Step 2:** Run the dev journeys. Expected: 10/10 or more, desktop and phone.
- [ ] **Step 3:** Capture the four-mode tour. Hand the finish review to `impeccable-finish-reviewer` **with the comp** (`specs/assets/2026-10-25-task-list-comp.html`) and brief §4 as the bar, and act on its disposition once. Rerun the critique as two isolated assessments and record the score against 32/40.
- [ ] **Step 4:** Docs, then `vm.sh lan` and the LAN journeys (mind the hourly sign-in limit).
- [ ] **Step 5:** Commit: `portal: journeys, design finish and docs for tasks and cards (task-list Task 8)`.

### Task 9: Whole-branch review

- [ ] **Step 1:** A fresh Opus reviewer on `git diff 10f7107..HEAD`, against this brief, the comp, this plan's Review Focus and the ledger's rulings.
- [ ] **Step 2:** One fix pass, each fix RED→GREEN, full suites rerun, LAN journeys rerun.
- [ ] **Step 3:** Report: rulings, deferred minors, the critique score and the side-by-side with the comp.

**Done when:**
- API suite, web suite, typecheck, build and detector all pass.
- The journeys (dev and LAN) pass.
- A building is 8 cards and an addition 7, by the Task 1 test.
- The finish review finds no material difference from the comp.
- The critique score is recorded.
