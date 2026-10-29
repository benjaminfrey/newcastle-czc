# Applicant Portal Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild every applicant page of the portal as a macOS / iOS-style app with a quiet civic
identity. Each application takes about ten steps (the screener included), with a step sidebar of
checkmarks, structured controls, autosave and sheets for buildings and additions.

**Architecture:**
- **Forms.** The YAML gains a step and page layer:
  - each form declares `steps`; each section (or field) names its `step`;
  - repeating sections declare `pages`;
  - fields may carry a `control`, a `default` and `autocomplete`;
  - repeats may offer `add_options` presets.

  The API validates the new keys, serves them, seeds defaults and presets, and leaves answering
  logic (`answers.py`, `applicability.ts`) unchanged.
- **Browser.** A new shell is a two-pane window on desktop and a navigation stack on phone. It
  renders steps from a pure `steps.ts` model, saves each answer as it is given through one
  application store, and draws every control from HeroUI 3.
- **Old pages.** Start/Where/Results/Wizard/Review become panes of the shell.

**Tech Stack:** M4's stack. React 19.3.1, HeroUI 3.2.6 (NumberField, Slider, Switch,
ToggleButtonGroup, Select, TagGroup, Modal, Drawer, Toolbar, Toast, Disclosure), Tailwind 4,
react-router 8.4.0, FastAPI and pytest; Playwright 1.64.1 with `@axe-core/playwright` 4.14.0 for
the journeys. No new dependencies.

**Spec:** `specs/2026-10-23-applicant-portal-redesign.md` (approved 2026-10-23); with
`specs/2026-10-14-applicant-portal-design.md`, `portal/web/PRODUCT.md`, and the critique snapshot
`.impeccable/critique/2026-10-24T01-25-15Z__portal-web-src.md`. **Built on:** branch
`portal-design-pass` at `326d233`.

## Decisions made in planning (for the reviewer)

- **Steps live in the form YAML, not in the browser.** A step is a list of sections (or fields)
  declared by the form, so the review sheet shows the chair the grouping, and a later form version
  can regroup without code.
  - The three shared start steps (project, property, what you'll need) are app steps, not form
    steps.
  - "Review and sign" is an app step.
- **Switch defaults are seeded answers, not evaluator magic.** A field with `default:` (e.g.
  `applicant_is_owner: true`, `has_agent: false`) gets that answer written when the application is
  created, with `set_by: "form-default"`.
  - The applicant sees the switch in that state and changes it if they need to.
  - `answers.py` / `applicability.ts` stay untouched, and the history shows the value was a
    default.
- **Required yes/no questions without a natural default stay segmented** Yes / No (unanswered
  stays distinct from No). `control: switch` is used only where the spec names a switch:
  - owner ("I own this property");
  - agent ("Someone is helping me…");
  - renovation only;
  - shared driveway.
- **The garage preset is data.** A repeat's `add_options: [{label, preset: {field: value}}]`, sent
  as `POST …/items {kind, preset}`; the API validates each preset value with `check_value` and saves
  it like any answer.
- **Pickers that list the application's own buildings or the lot's roads store the shown text**
  (type stays `text`; `control: building-picker | street-picker`), so printing and the API's
  checking need no new types.
- **Concept roll skipped by the chair's explicit choice of the category standard.** The chair pinned
  the look: Apple's own apps, executed straight. So the impeccable direction round takes its
  canon exit; the contract records it (Task 0).
- **Small Project Plan is 9 steps, not 10.** The brief's heading says 10, but its own step list is
  nine (eight for site-only work); the plan follows the list.
- **Old pages are removed, not kept beside the new ones.** One flow, so the tests and journeys
  exercise only what applicants see.

## Global Constraints

- All M1–M4 constraints hold:
  - the VM workflow (`portal/vm.sh`, with stdin closed: `</dev/null`);
  - stage by name; the model trailer; no push or PR without being asked;
  - never guess a legal value;
  - the no-verdict word list (`approved, denied, compliant, meets, fails, violates`) checked over
    all applicant-facing text, sidebar status words included;
  - drafts refused in production;
  - an application keeps its form version.
- **Every changed form entry goes back to `status: draft`** and onto the forms review sheet; the
  chair re-approves.
- **WCAG 2.1 AA in light and dark** (spec §8):
  - text contrast ≥ 4.5:1 and large text ≥ 3:1, checked by a unit test over the theme tokens;
  - every interactive target ≥ 44 × 44 CSS px;
  - visible focus;
  - focus moves to the step title on every step change.
- **The seal's teal is `#1098A8`** (identity and selection only). Text and buttons use a deeper teal
  meeting 4.5:1 on the page ground in both modes.
- **Continue never saves; answers save as they are given** (change for switches, pickers, sliders
  and chips; blur for typed text and numbers). The toolbar shows Saving… and Saved.
- **Step counts** (spec §4): Use Permit 9, Small Project Plan 9 (8 for site-only work), Entrance / Driveway 10,
  each counting the three shared start steps and Review and sign.
- **Phone (< 1024 px):**
  - Continue is in a fixed bottom bar, clear of the home indicator;
  - Back is only the top-left chevron;
  - sheets are full-height.
- **Desktop (≥ 1024 px):** sidebar plus content pane; Back and Continue bottom right, Continue
  rightmost, Return triggers it; Esc cancels a sheet.
- **Reduced motion:** with `prefers-reduced-motion: reduce`, push and sheet transitions become
  fades of 150 ms or less.

## Review Focus

1. **A switch default nobody touched** prints as the applicant's answer. The applicant must have
   seen it: Review shows default-seeded answers exactly as answers, and the sidebar marks a step
   done only after it has been opened. Task 5 `step_status_needs_a_visit`; Task 1
   `test_defaults_are_seeded_and_marked`.
2. **Typing quickly, then Continue before the blur save lands.** The answer must not be lost or
   saved twice out of order. The store queues saves in order and Continue waits for pending saves.
   Task 6 "Continue waits for the pending save"; "saves stay in order".
3. **Two tabs.** The autosave in tab B meets tab A's newer revision. The toolbar shows "Changed in
   another tab — Load the latest" and stops autosaving until it is pressed, never overwriting. Task 6
   "a conflict stops autosave and offers Load the latest".
4. **Deleting a building with answers on a phone.** Requires the confirmation sheet; deleting the
   last building is impossible when the minimum is 1. Task 8 "delete asks first" and "the last
   building cannot be deleted".
5. **Sign-in from the email link on another device.** The link opens on the phone and the pending
   start isn't there. It resumes at "What you'll need" with the property asked again, not a dead
   end. Task 9 "a link without a pending start lands on My applications with Start an application".

---

## Task 0: Record the direction

- [ ] Write the direction contract (six blocks, ≤ 150 words) with
  `node /Users/ben/.claude/skills/impeccable/scripts/surface-brief.mjs write portal/web/src/App.tsx <body-file>`.
  It names:
  - THESIS: a document with sections, not a corridor of questions; refuses one-field screens.
  - OWN-WORLD: Apple System Settings and iOS Settings grammar; system UI type; grouped inset
    lists; seal teal `#1098A8` for identity, a deeper teal for actions; light and dark from the
    device.
  - STORY: find out, confirm your lot, apply in about ten steps, review the official form.
  - FIRST VIEWPORT: the step sidebar with the seal beside "Your project" on desktop; the large-title
    root list on phone.
  - SIGNATURE: your lot's map carried from "Your property" into Placement and "Where it meets the
    road".
  - RISK: a web app imitating native chrome can feel uncanny, so use native grammar, never fake
    window controls.

  Include the seed key `canon (chair's explicit choice, 2026-10-23)`. Read it back with
  `surface-brief.mjs read portal/web/src/App.tsx`, then commit
  `portal: design direction contract (redesign Task 0)`.

---

## Task 1: Steps, pages, controls, defaults and presets in the form format (API)

**Files:**
- Modify: `portal/api/portal_api/forms/formdefs.py`, `portal/api/portal_api/routes/applications.py`
  (`form_json`, `create_application`, `add_item`), `portal/api/portal_api/applications.py` (`create`,
  seeding)
- Test: `portal/api/tests/test_formdefs.py`, `portal/api/tests/test_applications.py`

**Interfaces:**

YAML additions:
- Each form file (and `cover-sheet.v1.yaml`) declares `steps: [{id, title}]`; an included file's
  steps come first.
- Each section may name a `step:`, and each field may name its own, which overrides the section's.
  Every question field must resolve to a declared step.
- A repeating section declares `pages: [{id, title, layout?}]`. `layout` is one of `compass` or
  `lot-diagram`. Every question field in it names a `page:`.
- Repeats may declare `add_options: [{label, preset: {field_id: value}}]`.
- Fields may declare:
  - `control:` one of `stepper`, `slider`, `switch`, `segmented`, `tiles`, `picker`, `chips`,
    `building-picker`, `street-picker`, `building-type`;
  - `step:` (number; default 1);
  - `default:` (a value `check_value` accepts);
  - `autocomplete:` one of `name`, `tel`, `email`, `street-address`.

Python:
- `Step(id: str, title: str)`.
- `FormDef.steps: tuple[Step, ...]`.
- `Section.step`, `Section.pages: tuple[Page, ...]`, `Section.add_options: tuple[AddOption, ...]`.
- `Page(id, title, layout)`; `AddOption(label, preset: dict)`.
- `Field.step`, `Field.page`, `Field.control`, `Field.step_size`, `Field.default`,
  `Field.autocomplete`.
- `FormDef.step_of(field_id) -> str`.

API:
- `form_json` adds all of the above. The JSON keys are `steps`, `step`, `pages`, `page`,
  `control`, `step_size`, `default`, `autocomplete`, `add_options`.
- `POST /api/applications/{id}/items` accepts `preset: int | None` (an index into the repeat's
  `add_options`) and saves the preset answers with the item, in the same revision.

Seeding: `apps.create` writes every top-level field `default` as an answer with
`set_by="form-default"`, and every repeat field `default` for each item it creates.

- [ ] **Step 1: Write the failing tests** in `test_formdefs.py` (using the tmp-dir fixture style):
  - `test_steps_load_in_order_with_the_cover_first`;
  - `test_field_step_overrides_section_step`;
  - `test_rejects_question_without_a_step`;
  - `test_rejects_unknown_step`;
  - `test_rejects_repeat_question_without_a_page`;
  - `test_rejects_unknown_control`;
  - `test_rejects_bad_default`: `default: "maybe"` on a yesno field, checked with `check_value`;
  - `test_rejects_preset_for_unknown_field`;
  - `test_rejects_bad_layout`.

  In `test_applications.py`:
  - `test_defaults_are_seeded_and_marked`: the `answer` row has `set_by = 'form-default'`, and GET
    shows the value;
  - `test_item_preset_saves_its_answers`: `preset: 0` on a fixture form gives
    `building_class = residential_accessory` on the new item;
  - `test_bad_preset_index_is_422`;
  - `test_form_json_carries_steps_pages_and_controls`.
- [ ] **Step 2:** Run `portal/vm.sh run 'cd portal/api && .venv/bin/pytest tests/test_formdefs.py tests/test_applications.py -q -o addopts=' </dev/null`.
  Expected: the new tests fail.
- [ ] **Step 3:** Implement. Validation messages name the file and the id, as now.
- [ ] **Step 4:** The same command passes. Then run the whole API suite; it passes except
  `test_form_content.py`, which fails because the real forms have no steps yet. Task 2 fixes that;
  note it in the ledger.
- [ ] **Step 5:** Commit `portal: steps, pages, controls, defaults and presets in form definitions (redesign Task 1)`.

---

## Task 2: The four forms regrouped, with the four proposals (content)

**Files:**
- Modify: the four YAMLs in `portal/api/portal_api/forms/definitions/forms/`,
  `portal/api/portal_api/forms/forms_sheet.py` (show step, page, control, default and presets;
  add the proposals to the decisions section), `memos/2026-10-21-application-forms-for-approval.md`
  (regenerated)
- Test: `portal/api/tests/test_form_content.py`, `portal/api/tests/test_forms_sheet.py`

**Content:**

- **Steps** (titles exact):
  - Cover: `your_lot` "Your lot" (sections `location`, `site`); `about_you` "About you"
    (`applicant`, `owner`, `agent`). `certification` and `office` have no questions and take no
    step.
  - Use Permit: `uses_today` "Uses today" (`existing`); `your_plan` "Your plan" (`proposed`);
    `photos` "Photos and plans" (`use_documents_section`).
  - Small Project Plan: `the_work` "The work" (`project`); `buildings` "Buildings" (the five
    building sections); `additions` "Additions, porches and decks" (`component`).
  - Entrance: `driveway` "The driveway"; `meets_road` "Where it meets the road"; `safety`
    "Safety at the road"; `state_permit` "State permit and sketch". Assign by field, following
    spec §4.
- **Pages:**
  - Building sections, in order: `basics` "Basics", `placement` "Placement" (layout
    `lot-diagram`), `size` "Size", `roof_walls` "Roof and walls" (window fields there, layout
    `compass` applies to the four `windows_*` fields).
  - Component: `kind` "What and where", `size` "Size, roof and windows".
- **Controls and defaults:**
  - Switches with defaults: `applicant_is_owner` (true), `has_agent` (false), `renovation_only`
    (false), `component_renovation_only` (false), `shared_driveway` (false).
  - Steppers: `existing_dwelling_units`, `dwelling_units`, `stories`, `homes_single_family`,
    `homes_two_family`.
  - Sliders: `windows_*` and `component_windows_*` (step 5); `first_20ft_slope` (0–25, step 1);
    `entrance_angle` (45–90, step 5; min becomes 45, still 0–90 valid in `check_value` if typed).
    Decision: keep `min: 0`; the slider's track starts at 45, with "Less than 45°" as the first
    stop.
  - Segmented: `entrance_work`, `mainedot_permit`, `intersection_signal`, `roadside_ditch`, and
    all other yesno fields without a switch.
  - Tiles: `roof_style`, `component_roof_style`, `component_kind`.
  - Building type: `building_class`.
  - Chips: `work_kinds`, `exterior_finish`, `component_finish`.
  - Autocomplete: `applicant_name`/`owner_name`/`agent_name` → `name`; phones → `tel`; emails →
    `email`; addresses → `street-address`.
- **Proposal 1 (garage):**
  - Building repeat `add_options`: `{label: "A building"}`; `{label: "A detached garage or shed",
    preset: {building_class: residential_accessory, building_name: "Garage"}}`.
  - Component option `garage` becomes label "An attached garage", official "Garage (attached)".
  - Delete field `garage_attached`.
- **Proposal 2 (windows):** labels become "North wall", "East wall", "South wall", "West wall".
  Help: "About what share of this wall is windows and doors?"
- **Proposal 3 (pickers):**
  - `roof_slope` and `component_roof_slope`: `type: choice`, `control: picker`, options `flat`
    "Flat (under 2/12)"; `2_12` … `12_12` (label and official "2/12" … "12/12"); `steeper`
    "Steeper than 12/12".
  - `exterior_finish` and `component_finish`: `type: multichoice`, `control: chips`. Options with
    official = label: Clapboard; Wood shingle; Vinyl siding; Fibre-cement siding; Brick; Stone;
    Board-and-batten; Metal siding; Asphalt shingle roof; Metal roof; Slate roof; Other.
  - New fields `exterior_finish_other` and `component_finish_other` (text, `show_if` has `other`).
  - `attached_to`: `control: building-picker`.
  - `entrance_street`: `control: street-picker`.
- **Proposal 4 (setbacks):** layout only; no field change.
- **Everything touched** gets `status: draft` (drop `approved_by`/`approved_on` on any entry
  changed).

**Steps:**

- [ ] **Step 1: Write the failing tests** in `test_form_content.py`:
  - `test_step_counts` (counting the three shared start steps and Review and sign):
    `len(form.steps) + 4` equals 9, 9 and 10 for use, small and entrance;
  - `test_every_question_has_a_step_and_repeat_questions_a_page`;
  - `test_garage_preset_is_a_residential_accessory_building`;
  - `test_roof_slope_options` (exactly flat, 2/12 to 12/12 and steeper; prints "8/12");
  - `test_finish_chips_have_an_other_field`;
  - `test_switch_defaults` (the five fields with their defaults);
  - `test_no_garage_attached_question`;
  - `test_changed_entries_are_drafts`.

  Update `test_every_packet_field_is_present`: "Garage attached or detached" leaves
  `COMPONENTS`; the Components Section's `Component` options still include "Garage (attached)".

  In `test_forms_sheet.py`: `test_sheet_shows_steps_and_controls` ("Step: Your lot", "Control:
  switch (starts on)").
- [ ] **Step 2:** Run the API suite. Expected: the new tests fail.
- [ ] **Step 3:** Edit the YAML and the sheet; regenerate the memo with
  `portal/vm.sh run 'cd portal/api && .venv/bin/python -m portal_api.forms forms-sheet' </dev/null > memos/2026-10-21-application-forms-for-approval.md`.
- [ ] **Step 4:** Run the whole API suite. Expected: pass.
- [ ] **Step 5:** Commit `portal: regroup the forms into steps; the four redesign proposals, as drafts (redesign Task 2)`.

---

## Task 3: Theme: system type, the seal's teal, light and dark

**Files:**
- Modify: `portal/web/src/index.css`, `portal/web/src/main.tsx`
- Create: `portal/web/src/theme/tokens.ts`, `portal/web/src/theme/colorScheme.ts`,
  `portal/web/src/theme/tokens.test.ts`

**Interfaces:**
- `tokens.ts` exports `LIGHT` and `DARK`: `{ ground, groupedGround, row, separator, label,
  secondaryLabel, tertiaryLabel, accent, accentText, onAccent, seal, destructive, selection }`
  as hex strings.
- `contrast(fg: string, bg: string): number`, using the WCAG formula.
- `index.css` sets `--app-*` custom properties from the same values. Light on `:root`; dark under
  `:root[data-theme="dark"]` and inside `@media (prefers-color-scheme: dark)` guarded by
  `:root:not([data-theme="light"])`. It also maps HeroUI's `--accent`, `--background`,
  `--foreground`, `--surface` and `--border` to them.
- The font stack is `-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, "Segoe UI",
  Roboto, sans-serif`.
- `colorScheme.ts` exports `followDeviceScheme(): () => void`. It sets `data-theme` and HeroUI's
  `.dark` class from `matchMedia`, and updates on change. `main.tsx` calls it.
- `seal` is `#1098A8` in both modes.

**Steps:**

- [ ] **Step 1:** Write `tokens.test.ts`:
  - "text meets 4.5:1 on its grounds": label, secondaryLabel and accentText on ground, row and
    groupedGround, in both modes;
  - "buttons meet 4.5:1": onAccent on accent, both modes;
  - "the seal colour is the seal's" (`LIGHT.seal === "#1098A8"`);
  - "css and tokens agree": read `index.css` with `?raw` and assert each `--app-*` value equals
    the token.

  Write `colorScheme.test.ts`: "follows the device and its changes", with a stubbed `matchMedia`.
- [ ] **Step 2:** `portal/vm.sh run 'cd portal/web && npx vitest run src/theme' </dev/null` fails.
- [ ] **Step 3:** Implement. Choose `accent` and `accentText` as the deepest teal of the seal's hue
  that passes (start from oklch hue of `#1098A8`, lowering lightness until both tests pass).
- [ ] **Step 4:** The tests pass. The whole web suite passes.
- [ ] **Step 5:** Commit `portal: theme tokens from the Town seal, light and dark (redesign Task 3)`.

---

## Task 4: The app shell (window on desktop, stack on phone)

**Files:**
- Create in `portal/web/src/shell/`:
  - `useWideLayout.ts` (`(min-width: 1024px)`);
  - `AppShell.tsx`, `StepSidebar.tsx`, `StepList.tsx` (the phone root list), `NavBar.tsx`,
    `Toolbar.tsx`, `ActionBar.tsx`, `Sheet.tsx`, `InsetGroup.tsx`;
  - `StatusGlyph.tsx`;
  - tests beside each.
- Modify: `portal/web/src/components/Layout.tsx` (thin header only for pages outside the shell:
  home and My applications).

**Interfaces:**
- `type StepStatus = "todo" | "started" | "done"`.
- `type ShellStep = { id: string; title: string; status: StepStatus; unknowns: number; href: string; children?: ShellStep[] }`.
- `<AppShell steps currentId title saveState onDone actions?>`:
  - `actions = { back?: () => void; continueLabel?: string; onContinue?: () => void }`;
  - `saveState: "idle" | "saving" | "saved" | "error" | "conflict"`.
- **Wide layout:**
  - `StepSidebar` (seal 32 px plus "Town of Newcastle", then the steps with `StatusGlyph`);
  - the content pane with `Toolbar` (title, save state, Done);
  - `ActionBar` with Back and Continue at the bottom right; the form's submit triggers Continue.
- **Narrow layout:**
  - at the root, `StepList` (large title "Your application", grouped list with glyphs);
  - in a step, `NavBar` (‹ back to the root, title collapsing on scroll);
  - `ActionBar` fixed at the bottom with `padding-bottom: env(safe-area-inset-bottom)` and a
    full-width Continue.
- `<Sheet open title onCancel onDone pages? pageIndex? onPage?>` is a HeroUI `Modal` (wide) or a
  full-height `Drawer` (narrow). Cancel is on the left and Done on the right; page dots appear
  when there are pages.
- `<InsetGroup title? footer?>` with `<InsetGroup.Row label htmlFor? stacked?>`: label left and
  control right when wide, stacked when narrow. Rows are at least 44 px.
- `StatusGlyph`: `todo` is an empty circle, `started` a half circle, `done` a checkmark. When
  `unknowns > 0` it adds a dot. Each has an accessible name ("Not started", "Started", "Done",
  "Done, with answers to follow up").
- Sidebar keyboard: Up/Down move focus, Enter opens, ⌥⌘↑/↓ go to the previous or next step from
  anywhere.

**Steps:**

- [ ] **Step 1:** Write tests:
  - `AppShell`: "wide shows sidebar, toolbar and Back/Continue at the bottom right"; "narrow root
    shows the step list and no Continue"; "narrow step shows the chevron and a fixed Continue";
    "Return in a field triggers Continue"; "save state reads Saving… then Saved".
  - `StepSidebar`: "glyph names are announced"; "arrow keys move and Enter opens";
    "⌥⌘↓ goes to the next step".
  - `Sheet`: "Esc cancels"; "Done calls onDone"; "dots show pages".
  - `InsetGroup`: "rows are at least 44px" (assert the `min-h-11` class).

  Mock `useWideLayout` per test.
- [ ] **Step 2:** `portal/vm.sh run 'cd portal/web && npx vitest run src/shell' </dev/null` fails.
- [ ] **Step 3:** Implement with HeroUI parts. No fake window controls (no traffic lights).
- [ ] **Step 4:** The tests pass.
- [ ] **Step 5:** Commit `portal: app shell — sidebar window and phone navigation stack (redesign Task 4)`.

---

## Task 5: The steps model

**Files:**
- Create: `portal/web/src/forms/steps.ts`, `portal/web/src/forms/steps.test.ts`
- Delete: `portal/web/src/forms/wizard.ts`, `wizard.test.ts` (replaced)

**Interfaces:**
- `START_STEPS = [{id: "project", title: "Your project"}, {id: "property", title: "Your property"}, {id: "needs", title: "What you'll need"}]`.
- `REVIEW_STEP = {id: "review", title: "Review and sign"}`.
- `type StepModel = { id; title; kind: "fields" | "hub"; rows: Row[]; hub?: { kind: string; repeat: Repeat; pages: Page[]; items: {id, label, status}[] } }`.
  `Row` comes from `applicability.ts`.
- `stepModels(form: FormDef, cur: Current): StepModel[]` lists the form's steps in order. A step
  whose rows are all hidden is omitted. That includes Buildings for site-only work, so the count
  shrinks honestly.
- `statusOf(step: StepModel, cur: Current, visited: Set<string>): { status: StepStatus; unknowns: number }`:
  - `done` when the step was visited and no required applicable question in it is missing;
  - `started` when it was visited or any question in it has a non-default answer;
  - else `todo`.

  `unknowns` counts `{unknown: true}` answers.
- `itemLabel(form, cur, itemId)` moves here unchanged in behaviour.
- `visited` is kept per application in `localStorage` (`portal.visited.<appId>`) with try/catch.

**Steps:**

- [ ] **Step 1:** Write `steps.test.ts` against `form-fixtures.json`, extended with `steps`,
  `step`, `pages` and `page` keys:
  - "steps follow the form's order";
  - "a step with nothing applicable is left out";
  - "hub steps list items with their status";
  - `step_status_needs_a_visit` (Review Focus 1: a step whose only questions have form defaults
    is `todo` until visited);
  - "unknowns are counted";
  - "items are labelled by type when unnamed".

  Extend `api/tests/test_form_fixtures.py` so the fixture still loads with the new keys.
- [ ] **Step 2:** The tests fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** The web and API suites pass.
- [ ] **Step 5:** Commit `portal: the steps model (redesign Task 5)`.

---

## Task 6: The application store and autosave

**Files:**
- Create: `portal/web/src/app/ApplicationStore.tsx` and `portal/web/src/app/ApplicationStore.test.tsx`

**Interfaces:**
- `<ApplicationProvider id>` loads the application and its pinned form.
- `useApplication()` returns:
  - `app`, `form`, `cur: Current`;
  - `saveState`;
  - `setAnswer(fieldId, itemId, value, how: "now" | "blur")`;
  - `flush(): Promise<void>` (resolves when every queued save has finished);
  - `addItem(kind, preset?)`, `removeItem(itemId)`, `saveNote(sectionId, itemId, text)`;
  - `reload()`, `markVisited(stepId)`, `visited`.
- Saves go through a single promise chain, in order. Each uses the latest revision; a 409 sets
  `saveState = "conflict"` and drops later queued saves until `reload()`.
- `how: "blur"` saves are triggered by the control's blur; `"now"` immediately.
- Values are checked with `fromDraft` first; an error stays on the field (returned to the caller),
  is not saved, and doesn't block navigation.

**Steps:**

- [ ] **Step 1:** Write the tests (`applications.ts` mocked):
  - "saves stay in order" (two quick `setAnswer` calls → two calls, the second with the first's
    returned revision);
  - "Continue waits for the pending save" (`flush` resolves only after the slow save);
  - "a conflict stops autosave and offers Load the latest" (Review Focus 3);
  - "a failed save keeps the value and says it couldn't save" (`saveState === "error"`, a retry
    on the next change);
  - "saved answers update cur immediately".
- [ ] **Step 2:** The tests fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** The tests pass.
- [ ] **Step 5:** Commit `portal: application store with ordered autosave (redesign Task 6)`.

---

## Task 7: Controls

**Files:**
- Create: `portal/web/src/controls/FieldControl.tsx` (the dispatcher) and one file per control in
  `portal/web/src/controls/`:
  - `NumberControl` (plain or stepper, with a unit suffix);
  - `SliderControl` (with a live readout and an editable value);
  - `SwitchControl`;
  - `SegmentedControl` (ToggleButtonGroup; yesno → Yes / No);
  - `TileControl` (options as large tiles, with `RoofGlyph` silhouettes for roof values);
  - `PickerControl` (Select);
  - `ChipsControl` (TagGroup multi-select);
  - `BuildingPicker` (options are this application's buildings via `itemLabel`, plus
    "Free-standing");
  - `StreetPicker` (options from `cur.property.streets`, plus "Another road", which reveals a text
    field);
  - `BuildingTypeControl` (two-stage: Home / A business / A smaller building that goes with… /
    Farm / Not sure, then the refining options from the field's nine, only where a group has more
    than one);
  - `UsesControl` (chips, plus `UseSearch` in a sheet);
  - `UploadControl` (restyled `UploadField`: a large "Take a photo or choose a file" button,
    `accept` as now, image thumbnails, a progress bar, and a "PDF, JPEG, PNG or HEIC · up to 25 MB"
    note);
  - `PointControl` (restyled `PointField`).

  Tests beside each.
- Delete: `components/QuestionField.tsx`, `components/UploadField.tsx` and `components/PointField.tsx`
  (absorbed), and their tests (the cases move to the new tests).

**Interfaces:**
- `<FieldControl field itemId value onValue(value, how) error? />`. Mapping:
  - `control` when set;
  - otherwise by type: number → `NumberControl`; choice with ≤ 4 options → `SegmentedControl`,
    more → `TileControl`; yesno → `SegmentedControl`; multichoice → `ChipsControl`; uses →
    `UsesControl`; upload → `UploadControl`; point → `PointControl`; text and longtext → HeroUI
    text fields with `autocomplete`.
- Every control:
  - offers "I don't know yet" where `allow_unknown` (a small trailing link button ≥ 44 px);
  - shows `help` under the control and `why` via `WhyWeAsk` (restyled: inline "Why we ask" with
    the chevron beside the text);
  - reports blur-type values with `how: "blur"`.

**Steps:**

- [ ] **Step 1:** Write the tests:
  - `FieldControl`: "maps each type and control to its component" (a table test).
  - `NumberControl`: "stepper increments within min and max"; "a typed value saves on blur";
    "suffix shows the unit".
  - `SliderControl`: "steps by 5 and announces its value".
  - `SwitchControl`: "saves now".
  - `SegmentedControl`: "Yes/No are distinct from unanswered".
  - `TileControl`: "roof tiles show silhouettes and have names".
  - `PickerControl`: "roof slope picker saves 8_12".
  - `ChipsControl`: "toggles chips; Other reveals its field" (via the form, at the step level).
  - `BuildingPicker`: "lists this application's buildings".
  - `StreetPicker`: "lists the lot's roads; Another road asks for a name".
  - `BuildingTypeControl`: "Home leads straight to Residential Building"; "A smaller building asks
    which kind".
  - `UploadControl`: the moved refusal and size cases, plus "offers the camera on phones" (the
    `accept` includes `image/*`).
  - `PointControl`: the moved case.
- [ ] **Step 2:** The tests fail.
- [ ] **Step 3:** Implement with HeroUI components only.
- [ ] **Step 4:** The tests pass.
- [ ] **Step 5:** Commit `portal: structured controls (redesign Task 7)`.

---

## Task 8: Step panes, the two layouts, hubs and sheets

**Files:**
- Create: `portal/web/src/app/StepPane.tsx` (a fields step: `InsetGroup` per section, conditional
  sections inline), `portal/web/src/app/HubPane.tsx` (a list of items plus add options),
  `portal/web/src/app/ItemSheet.tsx` (a `Sheet` with the repeat's pages),
  `portal/web/src/app/layouts/CompassLayout.tsx`, `portal/web/src/app/layouts/LotDiagramLayout.tsx`,
  `portal/web/src/app/ApplicationPage.tsx` (route `/applications/:id/:stepId?`, inside
  `ApplicationProvider` and `AppShell`)
- Delete: `pages/Wizard.tsx`, `pages/Wizard.test.tsx`
- Tests beside each

**Interfaces:**
- `ApplicationPage`:
  - **Wide.** With no `stepId`, it redirects to the first step that isn't done. The sidebar lists
    `START_STEPS` (done, linking to read-only summaries), then the form's steps, then
    `REVIEW_STEP`.
  - **Narrow.** With no `stepId`, it shows `StepList`.
  - **Continue.** `await flush()`, `markVisited(current)`, then go to the next step. On the last
    form step, Continue goes to review.
  - **Reloads.** The sheet state lives in the URL (`?item=<id>&page=<pageId>`), so a reload
    reopens it.
- `CompassLayout`: the four `windows_*` fields around a small plan square labelled N/E/S/W, with
  "Front faces {first street name}" above it when the property knows the street.
- `LotDiagramLayout`:
  - an SVG of the lot's outline (from `getProperty(parcel_id).geometry`, projected to fit, else a
    square) with a building box;
  - the four setback fields placed beside the front, the sides and the rear;
  - "Not to scale" printed under it;
  - the front side is the side nearest the first street (a square when unknown).
- `HubPane`:
  - "Add a building" (or the `add_options` labels in a menu when there are several) is the last
    row of the group;
  - each item row shows `itemLabel` and its `StatusGlyph`, and opens `ItemSheet`;
  - "Delete Building" is a red row inside the sheet's last page, behind an `AlertDialog`
    confirmation;
  - the item can't be deleted at the minimum.

**Steps:**

- [ ] **Step 1:** Write the tests:
  - `StepPane`: "groups sections and reveals the owner group when the switch turns off"; "focus
    moves to the step title" (`document.activeElement` is the h1); "the page title names the step".
  - `HubPane`: "add options create the preset item" (`addItem` is called with the preset index);
    "delete asks first" (Review Focus 4); "the last building cannot be deleted".
  - `ItemSheet`: "pages and dots"; "Done returns to the hub with the item's status updated".
  - `CompassLayout`: "four sliders around the plan, labelled by wall".
  - `LotDiagramLayout`: "draws the lot from its outline"; "falls back to a square"; "says not to
    scale".
  - `ApplicationPage`: "Continue waits for saves, then moves on"; "site-only work has no Buildings
    step"; "a reload reopens the sheet".
- [ ] **Step 2:** The tests fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** The tests pass. Run the web suite and the build.
- [ ] **Step 5:** Commit `portal: step panes, lot diagram, compass, hubs and sheets (redesign Task 8)`.

---

## Task 9: The start steps and sign-in, inside the shell

**Files:**
- Create: `portal/web/src/start/StartFlow.tsx` (routes `/start/:stepId?` in `AppShell`, signed
  out), `portal/web/src/start/ProjectPane.tsx` (from `pages/Start.tsx`),
  `portal/web/src/start/PropertyPane.tsx` (from `pages/Where.tsx`; the map is the pane's anchor,
  with the lot card beside it when wide and below it when narrow; the "I can't find my property"
  path is a visible secondary button), `portal/web/src/start/NeedsPane.tsx` (from
  `pages/Results.tsx`: each application is a grouped row with reviewer and time; the applications
  this site takes have a primary "Start this application" button),
  `portal/web/src/start/SignInSheet.tsx` (email field, then "Check your email" naming the address,
  "The link works once, for 15 minutes", and "Send it again")
- Modify:
  - `App.tsx` (routes);
  - `pages/Verify.tsx` (restyled; resumes the pending start or, without one, goes to My
    applications);
  - `pages/ApplyStart.tsx` (now only creates the application and goes to
    `/applications/:id/your_lot`);
  - `pages/Home.tsx` (one screen: the seal, "Planning a project in Newcastle?", a primary
    "Find out what you need" button to `/start`, and "Continue an application" when signed in);
  - `pages/MyApplications.tsx` (a grouped list with status and last change; an empty state with
    "Start an application").
- Delete: `pages/Start.tsx`, `Where.tsx`, `Results.tsx`, `UsePicker.tsx`, `SignIn.tsx` and their
  tests (cases move to the new tests). `/where`, `/start/use`, `/start/results` and `/signin`
  redirect to their new homes.

**Steps:**

- [ ] **Step 1:** Write the tests:
  - `ProjectPane`, `PropertyPane` and `NeedsPane`: the moved cases, plus "Start this application
    opens the sign-in sheet when signed out".
  - `SignInSheet`: "shows Check your email with the address and the expiry"; "Send it again asks
    again".
  - `Verify`: "a link without a pending start lands on My applications with Start an application"
    (Review Focus 5).
  - `Home`: "one primary action".
  - `MyApplications`: "empty state offers Start an application".
- [ ] **Step 2:** The tests fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the web suite and the build. Expected: pass.
- [ ] **Step 5:** Commit `portal: the start steps and sign-in in the shell (redesign Task 9)`.

---

## Task 10: Review and sign

**Files:**
- Rewrite: `portal/web/src/pages/Review.tsx` as `portal/web/src/app/ReviewPane.tsx` (the `review`
  step of `ApplicationPage`), `components/OfficialSection.tsx` as
  `portal/web/src/app/OfficialGroup.tsx`
- Delete: `pages/Review.tsx` and its test (the cases move)

**Interfaces:**
- The paper form's sections become `InsetGroup`s, in form order, with Certification and Office use
  last.
- Each group has "Edit", which opens that step's `StepPane` in a `Sheet` (Done closes it), and
  "Add more detail", which opens a sheet with a text area.
- "Still to answer" is a grouped list linking to the step (with `?focus=<fieldId>`).
- The ending is an `InsetGroup` that says "Your application is saved. Sending it to the Town
  arrives soon." There is no Submit button.
- Removing items is done only from the hub (Task 8), not here.

**Steps:**

- [ ] **Step 1:** Write the tests:
  - the moved cases: official labels; property marks; uploads linked; optional new questions
    flagged; no verdict words;
  - "Certification and Office use come last";
  - "Edit opens the step in a sheet";
  - "Still to answer links focus the field";
  - "no Submit button".
- [ ] **Step 2:** The tests fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the web suite and the build. Expected: pass.
- [ ] **Step 5:** Commit `portal: review and sign in the shell (redesign Task 10)`.

---

## Task 11: Motion, focus and the finishing behaviours

**Files:**
- Modify: `AppShell.tsx`, `Sheet.tsx`, `index.css` (transitions), `ApplicationPage.tsx`,
  `StartFlow.tsx`

**Content:**
- Narrow: the step push is a 250 ms slide from the right (`ease-out`); going back slides the other
  way. Wide: the content pane cross-fades in 150 ms.
- Sheets rise in 250 ms.
- All of this is fades of 150 ms or less when the device asks for reduced motion.
- The iOS edge swipe: a pointer drag starting within 20 px of the left edge and moving right past
  80 px goes back.
- On every pane change, focus goes to the title, `document.title` updates, and an
  `aria-live="polite"` region announces "Step 4 of 9: About you".

**Steps:**

- [ ] **Step 1:** Write the tests:
  - "reduced motion uses fades" (stubbed `matchMedia`; the class on the pane);
  - "edge swipe goes back";
  - "the live region announces the step";
  - "the title updates".
- [ ] **Step 2:** The tests fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** The tests pass.
- [ ] **Step 5:** Commit `portal: motion and focus (redesign Task 11)`.

---

## Task 12: Journeys, the tour and accessibility

**Files:**
- Rewrite: `portal/web/e2e/helpers.ts` (`answerStep` fills whichever controls a step shows;
  `completeApplication` drives steps via Continue and hubs via Add and Done),
  `portal/web/e2e/use-permit.spec.ts`, `small-project-plan.spec.ts`, `entrance-permit.spec.ts`,
  `refusals.spec.ts`
- Create: `portal/web/e2e/redesign.spec.ts` with these cases:
  - "Small Project Plan in 9 steps": count the sidebar steps;
  - "site-only work has 8";
  - "a detached garage is a building";
  - "the sidebar shows checkmarks as steps finish";
  - "phone: Continue sits in the bottom bar and Back is the chevron";
  - "dark mode passes axe".

**Steps:**

- [ ] **Step 1:** Write the specs.
- [ ] **Step 2:** On the VM (dev API with the raised sign-in limit, as in the README) run
  `PORTAL_E2E_URL=http://127.0.0.1:5173 PORTAL_E2E_MAILPIT=http://127.0.0.1:8025 npm run e2e`.
  Expected: all pass at desktop and phone, with no serious or critical axe findings in light and
  dark (`colorScheme` per test).
- [ ] **Step 3:** Fix what they find; re-run once.
- [ ] **Step 4:** Commit `portal: journeys for the redesign (redesign Task 12)`.

---

## Task 13: Finish: detector, critique, documentation

- [ ] Run `node /Users/ben/.claude/skills/impeccable/scripts/detect.mjs --json portal/web/src`. Fix
  the mechanical findings.
- [ ] Capture the screenshot tour again, as for the critique (every pane at 1280 × 800 and Pixel 7,
  light and dark), into the scratchpad.
- [ ] Spawn `impeccable-finish-reviewer` with:
  - the brief;
  - the direction contract;
  - the screenshots;
  - the critique snapshot as the reference.

  Act on its disposition once.
- [ ] Spawn `impeccable-documenter` to write `portal/web/DESIGN.md` from the built world.
- [ ] Re-run `/impeccable critique` on `portal/web/src`, aiming at **32/40 or better**, and record
  the score.
- [ ] Update the docs:
  - `portal/README.md` (the shell, the form keys `steps`, `pages`, `control`, `default` and
    `add_options`);
  - the roadmap status;
  - `OPEN_ITEMS.md` (the forms are back to drafts for re-approval; the chip list for the chair or
    CEO).

  Commit `portal: redesign finish — DESIGN.md, critique, docs (redesign Task 13)`.

---

## Task 14: LAN and the whole-branch review

- [ ] Run `portal/vm.sh lan </dev/null`, then the journeys against https://192.168.1.6. Expected:
  all pass.
- [ ] Run the full API suite with both integration variables, and the web suite and build. Record
  the counts.
- [ ] Hand off for the whole-branch review (a fresh reviewer, the most capable model) against this
  plan and the brief.

## Done when

- Each application completes in the brief's step counts at desktop and phone width, with
  checkmarks, autosave, sheets and the macOS / iOS navigation (Task 12 journeys).
- Theme contrast passes in both modes (Task 3); axe is clean in light and dark (Task 12).
- The critique scores 32/40 or better (Task 13), and `portal/web/DESIGN.md` records the world.
- The forms review sheet shows the steps, controls and four proposals as drafts for the chair.
