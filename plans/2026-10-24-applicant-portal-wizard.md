# Applicant Portal — one question at a time: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the redesigned portal (PR #20) into a horizontal wizard: one question per screen, answers as chips above, single choices moving on at a tap, plain dots below, and no "Why we ask".

**Architecture:** A form's steps stay the sections in the sidebar. A new pure model, `screensOf`, turns each step's applicable rows into an ordered list of screens: one per question, except the fields a form groups with `screen:`. Buildings and additions run inline as loops. One `WizardPane` renders whichever screen the URL names, and the shell's footer gains dots. The screener becomes the same kind of screens. The API gains the `screen` grouping and the front-facing question, loses sheet `pages` and `add_options`, and carries the screener's answers into a new application.

**Tech Stack:** FastAPI + Postgres, pytest (`portal/api`); React 19, HeroUI 3, Tailwind 4, Vitest, Playwright + axe (`portal/web`). Tests run on the VM through `portal/vm.sh`.

**Spec:** `specs/2026-10-24-applicant-portal-wizard.md` (approved 2026-10-24), which revises `specs/2026-10-23-applicant-portal-redesign.md`. The prototype is https://claude.ai/artifact/HVaTbirFXVbMfHYb1DxGjq.

## Global Constraints

- Work continues on `portal-design-pass`, so PR #20 carries the whole redesign. Commit by name; push only on the chair's OK.
- Every commit ends `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Never run `tsc -b` on the VM: tsconfig has no `noEmit`, and it writes `.js` files into `src/`. Typecheck with `npx tsc --noEmit -p tsconfig.json`.
- Every `ssh` and `portal/vm.sh` call ends with `</dev/null`. Never use `pkill -f` with a pattern that matches the SSH command's own shell.
- Restart the dev API after any form YAML change; it caches forms.
- **No applicant-facing text** may contain "Why we ask", "Why the Code calls for it", a Code citation, or a verdict word (approved, denied, compliant, meets, fails, violates).
- Never guess a legal value. The front-facing question and the `screen:` groupings are **drafts** on the forms review sheet, and every new form entry is `status: draft`.
- Single choices (tiles, yes / no) move on at a tap and never show Continue. Continue appears for choose-several, typed values, numbers, steppers, sliders, measurement sets, uploads, the map pin and uses.
- Dots: 7 px circles at the bottom left, the current one in the label colour, the rest in the separator colour, not interactive. Above 12 screens in a group, show "12 of 20" instead.
- Window sliders run 0–100 % in steps of 5. Building types: all nine from the form.
- A corrected map value is never credited to the map, and "Yes, that's right" writes no answer.

## Review Focus

1. **Answers lost between screens.** A typed answer must be saved when Continue, Return, a chip, a dot or the sidebar moves on; `commitFocused` and the unmount commit from the review fixes must keep working in the new pane.
2. **Answers that change which screens apply.** Turning "Do you own this property?" to Yes removes the owner screens; the current screen index must stay valid, and the trail must not show answers from screens that no longer apply.
3. **Loops.** "Another building?" must add exactly one item, even on a double tap or a slow network, and Back from a new item's first screen must go to the previous item's last screen. "No" must leave the count unchanged.
4. **Change from review.** Answering returns to review, but when the answer adds screens (owner = No), the new screens must be asked first.
5. **Carried answers.** The screener's floor area and homes must reach Building 1 only for new-building work, and an edited carried value must stop showing as carried.

---

### Task 1: Form format: `screen` groupings in, sheet pages and presets out; the front-facing question

**Files:**
- Modify: `portal/api/portal_api/forms/formdefs.py`, `portal/api/portal_api/routes/applications.py` (`form_json`, `ItemBody`), `portal/api/portal_api/forms/forms_sheet.py`, `portal/api/portal_api/applications.py` (`new_item` loses `preset`)
- Modify: the four YAML files under `portal/api/portal_api/forms/definitions/forms/`
- Modify: `memos/2026-10-21-application-forms-for-approval.md` (regenerated)
- Test: `portal/api/tests/test_formdefs.py`, `test_form_content.py`, `test_forms_sheet.py`, `test_applications_api.py` (preset tests removed)

**Interfaces:**
- Produces, in the form JSON:
  - section `screens: [{id, layout}]`, where `layout` is `null`, `"lot-diagram"` or `"compass"`;
  - field `screen: string | null`.
  - `pages`, field `page` and `repeat.add_options` are gone.
- Produces the new field `front_facing`: choice, `control: tiles`, options north / east / south / west, label "Which way does the front of the building face?", in `building_windows` directly before the walls, `allow_unknown: true`, `status: draft`. Also `component_front_facing`, worded the same, in the component section directly before its walls and with the same show rule as those walls (additions and attached garages).
- A building's questions start with its type: `building_class` and `dwelling_units` move ahead of `building_name` and `renovation_only` in the Small Project Plan's section order.

- [ ] **Step 1: Write the failing tests.**
  - `test_screen_groups_load`: a fixture section with `screens: [{id: walls, layout: compass}]` and four fields with `screen: walls` loads with `section.screens[0].layout == "compass"`, and `f.screen == "walls"` for each.
  - `test_rejects_undeclared_screen`: a field with `screen: nowhere` gives a `DefinitionError` naming `nowhere`.
  - `test_rejects_bad_screen_layout`: `layout: spiral` raises.
  - `test_pages_and_add_options_are_gone`: a fixture with `pages:` raises "pages", and one with `add_options:` raises "add_options". Remove the old page and preset tests.
  - `test_front_facing_before_walls`: in `small_project_plan`, `front_facing` comes directly before `windows_north`, and `component_front_facing` directly before `component_windows_north` with the same `show_if`. The options' officials are North, East, South and West, and both are drafts.
  - `test_building_starts_with_its_type`: among the building's questions in form order, `building_class` comes first.
  - `test_groupings`: `deed_book` and `deed_page` share a screen; so do `mass_width` and `mass_depth`; the four setbacks (layout `lot-diagram`); the four walls (layout `compass`); `component_width` and `component_depth`; `sight_distance_left` and `sight_distance_right`; and `homes_single_family` and `homes_two_family`.
- [ ] **Step 2:** Run `portal/vm.sh run 'cd portal/api && .venv/bin/pytest -q tests/test_formdefs.py tests/test_form_content.py' </dev/null`. Expected: the new tests fail.
- [ ] **Step 3: Implement.**
  - `Screen(id, layout)` dataclass; `Section.screens`; `Field.screen`. Validate that every field's `screen` is declared in its own section; reuse `LAYOUTS`.
  - Delete `Page`, `AddOption`, `_check_steps`' page rule, the preset checks, `ItemBody.preset` and the `unknown_preset` path.
  - Regroup the YAMLs: `page:` keys become `screen:` only where fields share a screen.
  - `forms_sheet` prints "Screen: <id> (<layout>)" for grouped fields and no longer prints pages or add options.
- [ ] **Step 4:** Rerun those two files, then the whole API suite. Expected: all pass. Restart the dev API.
- [ ] **Step 5:** Regenerate the memo with `.venv/bin/python -m portal_api.forms forms-sheet` on the VM, saved to `memos/2026-10-21-application-forms-for-approval.md`. Check that the diff shows the new screens and `front_facing`, and nothing else.
- [ ] **Step 6:** Commit `portal: form screens replace sheet pages; the front-facing question (wizard Task 1)`.

### Task 2: Carry the screener's answers into a new application; say who set an answer

**Files:**
- Modify: `portal/api/portal_api/routes/applications.py` (`NewApplication`, `create_application`, `app_json`), `portal/api/portal_api/applications.py` (`answers` returns `set_by`)
- Modify: `portal/web/src/applications.ts` (`NewApplication`, `Answer.carried`), `portal/web/src/pages/ApplyStart.tsx`, `portal/web/src/pendingStart.ts`
- Test: `portal/api/tests/test_applications_api.py`, `portal/web/src/pages/ApplyStart.test.tsx`

**Interfaces:**
- `NewApplication.carry: { work_kind: "new"|"addition"|"renovation"|"site"|None, floor_area: float|None, new_homes: int|None } | None`
- GET application answers: each gains `carried: bool`, true when `set_by == "screener"`.
- `PendingStart` gains `carry`.

- [ ] **Step 1: Write the failing tests.**
  - `test_carry_fills_work_kinds_and_building_one`: create a `small_project_plan` with `carry={work_kind:"new", floor_area:1200, new_homes:1}`. Then `work_kinds == ["new_building"]` and Building 1's `floor_area == 1200` and `dwelling_units == 1`, each with `carried: true`.
  - `test_carry_for_an_addition_fills_only_work_kinds`: with `work_kind:"addition"`, `work_kinds == ["addition"]`, and Building 1 has no `floor_area`.
  - `test_carry_ignored_by_forms_without_those_fields`: a `use_permit` with `carry` is created with none of these answers.
  - `test_carry_values_are_checked`: `floor_area: -5` gives 422 `invalid`.
  - `test_an_edited_answer_is_not_carried`: save `floor_area = 900`, and it comes back `carried: false`.
  - Web, `ApplyStart.test.tsx` "sends the screener's carry": `createApplication` is called with `carry` built from `loadAnswers()`. The mapping is `building.kind` to `work_kind`, `gross_floor_area_sf` to `floor_area` and `new_dwelling_units` to `new_homes`.
- [ ] **Step 2:** Run them. Expected: they fail.
- [ ] **Step 3: Implement.**
  - Map `work_kind` to the `work_kinds` option value: new to `new_building`, addition to `addition`, renovation to `renovation`, site to `site`.
  - Save under `set_by = "screener"`, using `check_value` for each value and skipping fields the form doesn't have.
  - Building 1 is the first `building` item made in `create`; fill its floor area and homes only when `work_kind == "new"`.
- [ ] **Step 4:** Run them. Expected: they pass. Then run the whole API suite.
- [ ] **Step 5:** Commit `portal: carry the screener's answers into a new application (wizard Task 2)`.

### Task 3: The screens model

**Files:**
- Create: `portal/web/src/forms/screens.ts`, `portal/web/src/forms/screens.test.ts`
- Modify: `portal/web/src/forms/steps.ts` (hub items stay for the sidebar; `pages` go), `portal/web/src/forms/form-fixtures.json` (screens, no pages), `portal/web/src/applications.ts` (types)

**Interfaces:**
- Produces:

```ts
export type ScreenKind = "choice" | "multi" | "picker" | "number" | "stepper" | "slider" | "text" | "long"
  | "set" | "confirm" | "setbacks" | "walls" | "facing" | "upload" | "point" | "uses" | "another" | "any";
export type Screen = {
  id: string;              // first field's id; "another:<kind>" or "any:<kind>" for loop questions
  step: string; itemId: string | null; kind: ScreenKind; rows: Row[];
  auto: boolean;           // moves on at a tap
  optional: boolean;       // shows "Skip for now"
  unknown: boolean;        // offers "I don't know yet"
};
export function screensOf(form: FormDef, cur: Current, step: StepModel): Screen[];
export function groupOf(screens: Screen[], s: Screen): Screen[];  // same step and itemId; "another" joins its last item
export function screenAfter(form: FormDef, cur: Current, models: StepModel[], at: { step: string; screen: string }):
  { step: string; screen: string } | { review: true };
```

- Kind by control and type:
  - `auto` (moves on at a tap): choice, tiles, segmented, switch, yesno, building-type, building-picker, street-picker.
  - `picker`: roof slope.
  - `multi`: multichoice or chips.
  - `number`, `stepper`, `slider`, `text`, `long`, `upload`, `point` and `uses` by their type or control.
  - `confirm`: a `may_correct` property field with a map value.
  - A `screen:` group becomes `setbacks` (layout lot-diagram), `walls` (layout compass) or `set` (no layout).
  - `front_facing` is `facing`, which is `auto`.
- Loops:
  - A repeat step's screens are each item's screens in item order, then `another:<kind>`.
  - A repeat with no items starts with `any:<kind>` ("Are you adding an addition, porch or deck?").

- [ ] **Step 1: Write the failing tests** in `screens.test.ts`, using `form-fixtures.json` and small inline forms:
  - "one screen per question": "About you" with owner = Yes gives `[applicant_name, applicant_phone, applicant_address, applicant_is_owner, has_agent]`.
  - "owner questions slot in": with owner = No, the four owner screens follow `applicant_is_owner`.
  - "a screen group is one screen": `deed_book` and `deed_page` give one `set` screen, and `setbacks` gives one screen whose kind is `setbacks` and which has 4 rows.
  - "single choices are auto, the rest aren't": `applicant_is_owner` is `auto`, `work_kinds` is not, roof slope is `picker`, and `front_facing` is `facing`.
  - "a map value asks Is this right?": `lot_area`, with the property's acres, is `confirm`; with no acres, it is `number`.
  - "buildings loop": two buildings give b1's screens, then b2's, then `another:building`, and `groupOf` that screen includes b2's screens.
  - "an empty additions step asks first": no components gives `[any:component]` alone.
  - "screenAfter crosses steps and ends at review".
  - "screenAfter skips screens that stopped applying".
- [ ] **Step 2:** Run `portal/vm.sh run 'cd portal/web && npx vitest run src/forms' </dev/null`. Expected: the new tests fail.
- [ ] **Step 3:** Implement `screens.ts`. Remove the `pages` use from `steps.ts`, keeping `HubItem` for the sidebar's nested items.
- [ ] **Step 4:** Run them. Expected: they pass. Then the typecheck.
- [ ] **Step 5:** Commit `portal: the screens model (wizard Task 3)`.

### Task 4: Pieces of a screen: tiles, the trail, the dots, the footer

**Files:**
- Create: `portal/web/src/controls/Tiles.tsx` (`ChoiceTiles`, `MultiTiles`), `portal/web/src/shell/Dots.tsx`, `portal/web/src/app/AnswerTrail.tsx`
- Modify: `portal/web/src/shell/ActionBar.tsx` (dots on the left; Back and Continue on the right; Continue optional; "Skip for now"), `portal/web/src/controls/FieldControl.tsx` (no `WhyWeAsk`), `portal/web/src/controls/pickers.tsx` (`BuildingPicker` and `StreetPicker` as tiles)
- Test: `portal/web/src/controls/controls.test.tsx`, `portal/web/src/shell/Dots.test.tsx`, `portal/web/src/app/AnswerTrail.test.tsx`

**Interfaces:**
- `ChoiceTiles({ field, value, onPick })`: `role=radiogroup`, each tile a `radio`, with an icon where `field.options[].icon` (or a built-in map by value) gives one. `onPick(value)` fires once per tap.
- `MultiTiles({ field, value, onValue })`: `role=group`, each tile a `checkbox`; a ✓ shows on chosen tiles.
- `Dots({ count, index })`: `role="img"`, `aria-label="Question {index+1} of {count}"`; above 12 it renders "{index+1} of {count}".
- `AnswerTrail({ screens, current, onGo })`: one chip per answered screen in the group, before the current one. Chip text comes from `display` in `OfficialGroup.tsx`. A screen whose answer is `carried` gets the class `carried` (dashed). Empty, it shows "Your answers appear here as you go".
- `ActionBar({ dots, onBack, onContinue?, continueLabel })`.

- [ ] **Step 1: Write the failing tests.**
  - `ChoiceTiles` "a tap picks once and names the choice": clicking "No" calls `onPick("no")` once, and the tile has `aria-checked="true"` after a rerender with value `"no"`.
  - `MultiTiles` "toggles and shows a check".
  - `Dots` "marks the current dot" and "says 13 of 20 past twelve".
  - `AnswerTrail` "chips go back" (clicking a chip calls `onGo(screenId)`) and "carried chips are dashed".
  - `FieldControl` "no Why we ask": `queryByText("Why we ask")` is null for a field with `why`.
  - `ActionBar` "no Continue for a single choice" and "Skip for now on an optional, empty screen".
- [ ] **Step 2:** Run `npx vitest run src/controls src/shell src/app/AnswerTrail.test.tsx` on the VM. Expected: they fail.
- [ ] **Step 3:** Implement. Tiles are full-width rows on a phone and two columns on a desktop, with 58 px minimum height and the selected tile in a 2 px accent border. Delete `components/WhyWeAsk.tsx` once nothing imports it (Task 7 removes the last use, on Results).
- [ ] **Step 4:** Run them. Expected: they pass. Then the typecheck.
- [ ] **Step 5:** Commit `portal: tiles, answer trail, dots (wizard Task 4)`.

### Task 5: The wizard pane in the application

**Files:**
- Create: `portal/web/src/app/WizardPane.tsx`, `portal/web/src/app/screens/ConfirmScreen.tsx`, `SetbacksScreen.tsx` (from `LotDiagramLayout`), `WallsScreen.tsx` (from `CompassLayout`, with the facing labels)
- Modify: `portal/web/src/app/ApplicationPage.tsx` (URL `?screen=`; moving on; loops), `portal/web/src/shell/AppShell.tsx` (the trail row under the toolbar; the footer from Task 4; slide direction), `portal/web/src/index.css` (`pane-push` reversed for Back)
- Delete: `app/HubPane.tsx`, `app/ItemSheet.tsx`, `app/StepPane.tsx` (move `REASONS` and `useRowControls` into `WizardPane.tsx`), `app/layouts/*` once moved
- Test: `portal/web/src/app/panes.test.tsx` (rewritten), `portal/web/src/app/wizard.test.tsx`

**Interfaces:**
- Consumes `screensOf`, `groupOf` and `screenAfter` (Task 3); `ChoiceTiles`, `Dots`, `AnswerTrail` and `ActionBar` (Task 4); and the store's `setAnswer`, `flush`, `addItem` and `markVisited`.
- URL: `/applications/:id/:stepId?screen=<id>&item=<itemId>&return=review`. With no `screen`, the step's first screen.
- Walls labels: with `front_facing = north` and the property's first street, the north wall is "Front (north, faces Sheepscot Road)" and the south wall "Back (south)". East is "Right side (east)" and west "Left side (west)", seen from the road. Unknown or unanswered facing: the compass names alone.

- [ ] **Step 1: Write the failing tests** in `wizard.test.tsx`:
  - "a single choice moves on at a tap": on `applicant_is_owner`, clicking "Yes" saves `true` and the URL becomes the `has_agent` screen.
  - "Continue saves a typed answer and moves on; Return does the same".
  - "Back slides to the previous screen, across steps": Back on the first screen of About you lands on Your lot's last screen.
  - "chips go back to their question".
  - "Is this right? Yes moves on and saves nothing; I'll correct it saves the typed value".
  - "another building adds exactly one": a double click on "Yes, add another" calls `addItem("building")` once and lands on the new item's first screen.
  - "No, that's all goes to the next step".
  - "an empty additions step asks first; No moves on and marks the step visited".
  - "Change from review returns to review after the answer, unless new screens now apply": with owner switched to No, the owner screens come first.
  - "the walls name the front": with facing north, the north slider is labelled "Front (north, faces Sheepscot Road)".
  - "I don't know yet answers as unknown and moves on".
  - "a chip saves the typed answer first": type in the phone field, click the trail's name chip, and `saveAnswers` has the phone number.
  - "the trail drops answers whose screens stopped applying": answer the owner screens, switch owner to Yes, and no owner-name chip remains.
  - "Back from a new building's first screen goes to the previous building's last screen".
  - "Skip for now leaves an optional upload empty and moves on".
  - Keep the store-level tests from the review fixes (Return saves; ⌘↓ saves).
- [ ] **Step 2:** Run `npx vitest run src/app` on the VM. Expected: they fail.
- [ ] **Step 3:** Implement `WizardPane` and the rewiring.
  - Moving on goes through `screenAfter`.
  - A tap on an `auto` screen calls `commitFocused`, `setAnswer`, then a 200 ms pause, then `go`.
  - Loops call `addItem` behind a pending flag, so a second tap is ignored.
  - `markVisited(step)` when a step's last screen is passed.
  - The slide runs right to left forward and left to right back; `prefers-reduced-motion` cross-fades.
  - The announcer says "Question n of N: <question>", and focus moves to the question heading.
- [ ] **Step 4:** Run them. Expected: they pass. Then the full unit suite and the typecheck.
- [ ] **Step 5:** Commit `portal: one question at a time in the application (wizard Task 5)`.

### Task 6: Review in plain words

**Files:**
- Modify: `portal/web/src/app/ReviewPane.tsx`, `portal/web/src/app/OfficialGroup.tsx`
- Test: `portal/web/src/app/ReviewPane.test.tsx`

**Interfaces:**
- Each row shows the question as asked (`field.label`) as its main text and the official term (`field.official_label`) small beneath, with **Change** linking to `?screen=<screen id>&item=<item>&return=review`.
- Still-to-answer rows say **Still to answer** in the destructive colour.
- The printout model (`printed`) is unchanged.

- [ ] **Step 1: Write the failing tests.**
  - "rows lead with the question as asked": the lot-width row's text starts "How wide is your lot, in feet?" and contains "Lot Width (ft)".
  - "Change opens the screen and comes back": the link is `/applications/abc/your_lot?screen=lot_width&return=review`.
  - "a grouped screen's Change opens the group": deed page links to `screen=deed_book`.
  - "no Edit sheets": `queryByRole("dialog")` stays null after clicking Change.
  - Keep "What happens next", "Everything is answered.", map provenance, and "Attached to" by name.
- [ ] **Step 2:** Run them. Expected: they fail.
- [ ] **Step 3:** Implement. Remove the edit sheet and its `Sheet` use from review; keep "Add more detail".
- [ ] **Step 4:** Run them. Expected: they pass.
- [ ] **Step 5:** Commit `portal: review in plain words, Change returns to it (wizard Task 6)`.

### Task 7: The screener as screens; sign-in as a screen

**Files:**
- Create: `portal/web/src/start/startScreens.ts`, `portal/web/src/start/StartWizard.tsx`
- Modify: `portal/web/src/start/StartFlow.tsx`, `portal/web/src/pages/Start.tsx` (its questions become screens), `portal/web/src/pages/Where.tsx` (search, then "Is this your property?"), `portal/web/src/pages/UsePicker.tsx`, `portal/web/src/pages/Results.tsx` (no `WhyWeAsk`; Start goes to the sign-in screen), `portal/web/src/App.tsx` (route `/start/signin`)
- Test: `Start.test.tsx`, `Where.test.tsx`, `Results.test.tsx`, `start/StartFlow.test.tsx`

**Interfaces:**
- `startScreens(answers: ScreenerAnswers): StartScreen[]`, in the same shape as `Screen`, built from the screener's existing questions and their show rules. A screen's answers write through the existing `saveAnswers` in `screener.ts`.
- The sign-in screen reuses `SignInForm`; after "Check your email" the link returns as now.

- [ ] **Step 1: Write the failing tests.**
  - "What are you planning? is choose-several with Continue".
  - "building work is a tap": tapping "A new building" moves on to the floor-area screen.
  - "the floor area shows only for building work".
  - "Is this your property? moves on at Yes and searches again at No".
  - "Results has no Why": `queryByText(/Why the Code/)` is null and no citation text such as "Art. 8" shows.
  - "Start goes to the sign-in screen when signed out".
  - Keep the screener's existing assertions on what it saves and where it ends up.
- [ ] **Step 2:** Run them. Expected: they fail.
- [ ] **Step 3:** Implement with the same `WizardPane` building blocks (tiles, trail, dots, footer). Delete `components/WhyWeAsk.tsx`.
- [ ] **Step 4:** Run them. Expected: they pass. Then the full unit suite, the typecheck and the detector (`node /Users/ben/.claude/skills/impeccable/scripts/detect.mjs --json portal/web/src`). Expected: exit 0.
- [ ] **Step 5:** Commit `portal: the screener one question at a time (wizard Task 7)`.

### Task 8: Journeys, tour, critique and docs

**Files:**
- Rewrite: `portal/web/e2e/helpers.ts` (`answerScreen` answers whatever screen shows; `completeApplication` drives screens until review), and the five specs
- Modify: `portal/README.md` (form keys `screen` and `screens`; `pages` and `add_options` gone; the wizard), `portal/web/DESIGN.md` (via `impeccable-documenter`), `OPEN_ITEMS.md` (front-facing question as a draft for the chair), `.superpowers/sdd/2026-10-24-applicant-portal-wizard/progress.md` (the ledger)

- [ ] **Step 1: Rewrite the journeys.**
  - Each application is completed screen by screen at desktop and phone width, with axe in light and dark.
  - `redesign.spec.ts` checks:
    - a single choice shows no Continue;
    - the dots count the group;
    - chips go back;
    - no screen contains "Why we ask", "Why the Code" or "Art. ";
    - a second building comes from "Yes, add another".
- [ ] **Step 2:** Run `PORTAL_E2E_URL=http://127.0.0.1:5173 PORTAL_E2E_MAILPIT=http://127.0.0.1:8025 npx playwright test` on the VM. Expected: 10/10 (and any new specs) pass.
- [ ] **Step 3:** Capture the tour in four modes, then hand the finish review to `impeccable-finish-reviewer` and act on its disposition once. Rerun the critique as two isolated assessments, record the score, and aim for 32/40.
- [ ] **Step 4:** Update the docs and regenerate DESIGN.md. Run `portal/vm.sh lan </dev/null`, then the journeys against https://192.168.1.6, at most once an hour because of the sign-in limit.
- [ ] **Step 5:** Commit `portal: wizard journeys, finish and docs (wizard Task 8)`.

### Task 9: Whole-branch review and fix pass

- [ ] Spawn a fresh `reviewer` (Opus) on `git diff origin/main...HEAD` against both briefs and this plan. Fix its findings test-first; log what is deferred, with reasons, in the ledger; rerun the full API suite, the unit suite, the typecheck, the build and the journeys. Report, then push to PR #20 on the chair's OK.

## Done when

- All three applications and the screener run one question per screen at desktop and phone width, with chips, dots, a tap to move on for single choices, and no "Why" anywhere.
- Buildings and additions loop inline; review is in plain words and Change returns to it.
- The screener's work kind, floor area and homes arrive carried in the application.
- The front-facing question labels the walls, and is a draft on the forms review sheet.
- API suite, unit suite, typecheck, build, detector and journeys (dev and LAN) pass; the critique score is recorded against 32/40.
