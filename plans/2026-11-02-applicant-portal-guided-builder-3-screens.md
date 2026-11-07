# Guided builder, plan 3 of 6: the conversation screens — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put plan 2's engine in front of a person. A signed-in applicant opens a project's guide
on the LAN copy and answers it turn by turn: the lot as the Town knows it, "So you mean…", the
building's numbers with the limit and the room left shown as they type, the "doesn't fit" page,
Back, Change, and an ending. A project that is ready goes on to "Check and send".

**Architecture:**
- **API (small).** Two additions to plan 2's routes:
  - `GET /api/projects/{id}/guide/openings`, the openings this project's parts can start;
  - `POST /api/projects/{id}/guide/revisit`, a new action kind, `revisit`, which takes one answer
    out of force so its turn is asked again and every later answer still stands (GOV.UK's
    "Change" link).
- **Web.** A new `src/guide/` layer over plan 1's components:
  - `api.ts`, the guide's calls and refusals;
  - `useGuide`, the one place that holds the conversation, the revision and what is in flight;
  - `TurnView`, one view per turn kind, and `NumberAnswer`, with the live check;
  - `EndingView`;
  - `GuidePage` at `/projects/:id/guide` and `CheckAndSend` at `/projects/:id/guide/check`.
- Everything stays behind `VITE_GUIDE_PREVIEW=1`, as plan 1's preview does, and loads in its own
  chunk, so HeroUI pages never load MUI.

**Tech Stack:**
- API: Python 3.14, FastAPI, SQLAlchemy `text()`, Alembic, pytest, as in `portal/api`.
- Web: React 19.3, TypeScript 5.9, MUI 9.5.0, react-router 8.4, Vitest 5, Testing Library,
  Playwright 1.64 with axe.
- No new packages.

**Spec:** `specs/2026-10-30-applicant-portal-guided-builder.md` (approved by the chair
2026-10-30). This plan implements:
- §4.1, the lot screen with its "That's not right" path;
- §4.3, "So you mean…", reading the picture's opening (decision 14 is still open);
- §4.4 without the drawing: the turns, number controls with the limit and room left, the "why"
  card, the step bar, save and come back;
- §4.5, the "doesn't fit" page;
- §4.6, the four endings the engine produces;
- §4.7, Check and send, for the "ready" ending;
- §4.8, one column on a phone and two on a computer;
- §10.3–10.4, words and accessibility.

Earlier plans: 1 Foundations (PR #22) and 2 the engine (PR #23), with the chair's coverage
answers (PR #24). Later plans: 4 lot drawing, 5 pictures, 6 applicant packet view.

## Global Constraints

- **The screens never decide anything.** Every limit, room-left figure, "fits" and ending comes
  from the API (spec §5). The web code does no arithmetic on standards. It shows `check` and
  `ending` exactly as the API returns them.
- **Every word an applicant reads is draft until the chair approves it.**
  - Turn, answer, entry and ending words come from the API, as plan 2 built them.
  - The screens' own words (button labels, headings, refusal messages) live in one file,
    `src/guide/words.ts`. Each one is listed there, and nowhere else in `src/guide/`.
  - Every guide screen shows the "Draft wording, not approved" chip, as the preview does.
- **Words never used** (§10.3), on screen and in `words.ts`: `approved`, `denied`, `granted`,
  `rejected`, `permit issued`, `compliant`, `violates`. One test scans `words.ts` with plan 2's
  list.
- **A limit is never shown as a red error** (§4.5).
  - No `error` color, error icon or `aria-invalid` for a number past its limit.
  - `error` styling is only for input the API can't take: not a number, or out of the turn's
    range.
- **What a person types is never read.** The reply box posts to `/guide/notes` and shows the
  note back. Nothing in the web code inspects it (decision 14).
- **"I'm not sure yet" is offered on every question,** number turns included, and never ends the
  conversation (§4.3).
- **Nothing is sent from "This needs the Town's judgment".** The CEO handoff is design 4. That
  ending shows what was and wasn't settled and how to reach the Town Office, and keeps the
  project saved. (Ruling for the chair, listed in Task 7.)
- **No Town contact details are made up.** The Town Office's phone, hours and address are not in
  the repo. The screens say "the Town Office" without them. The real details are an open item
  for the chair.
- **The HeroUI app keeps working unchanged** (decision 13). Every existing Vitest test and
  Playwright journey still passes. MUI loads only under `src/guide/`, inside `GuideTheme`'s
  `ScopedCssBaseline`.
- **Every color, font, radius and spacing value in `src/guide/` comes from the theme tokens**
  (plan 1's rule; spec §10.2).
- **Accessibility:** WCAG 2.1 AA, checked by axe in Playwright at desktop (1280×800) and phone
  (Pixel 7). Targets are at least 48 px. When a new turn appears, focus moves to its question,
  and the turn is announced once.
- **Revision discipline**, as the HeroUI app does:
  - every change sends `base_revision`;
  - `409 changed_elsewhere` reloads the conversation and says so;
  - `409 locked` turns the page read-only;
  - one change is in flight at a time, so a double tap never sends twice.
- **Commits:**
  - work on branch `portal-guided-3-screens`, cut from `main` at 474e174;
  - stage files by name;
  - end each message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`;
  - commit per task; push only on the chair's OK.

## Review Focus

1. **Live-check answers arriving out of order.** A person types "1", "12", "120" quickly, and
   the reply for "1" arrives last. Expect the room-left line to show 120's check, never a stale
   one. Pinned in Task 4, `test_a_stale_check_never_replaces_a_newer_one`.
2. **The same project open in two tabs.** One tab answers; the other answers the same turn.
   Expect the second to get `changed_elsewhere`, reload, show the turn the first tab reached, and
   say why. Never send twice, and never lose the first answer. Pinned in Task 3,
   `test_a_stale_revision_reloads_and_says_so`.
3. **A number typed the way people write it:** "1,800", " 25 ", "25.5", "", "twenty". Expect the
   first three to be read as numbers, "" to keep Next disabled, and "twenty" to be refused with
   an inline message (not a limit message). Pinned in Task 4,
   `test_numbers_are_read_the_way_people_write_them`.
4. **Change on an answer that later answers depend on.** For example, the person changes
   `roof_floors` from 1 to 0, so `top_knee_over_3ft` no longer applies. Expect the guide to
   re-ask only what the new answer opens up, and the summary to drop the answer that no longer
   applies. Pinned in Task 1, `test_revisit_keeps_later_answers_that_still_apply`, and Task 6,
   `test_change_from_check_and_send_returns_to_it`.
5. **A reload, or coming back next week, mid-conversation.** Expect the same turn, history and
   step bar, from the server alone, with no client-side saved state. Pinned in Task 7's journey,
   `the guide picks up where it left off`.

---

## File map

- **API, modify:**
  - `portal/api/portal_api/guide/engine.py`: the `revisit` action;
  - `portal/api/portal_api/guide/store.py`: record it;
  - `portal/api/portal_api/routes/guide.py`: the two routes.
- **API, create:** `portal/api/migrations/versions/0010_guide_revisit.py`, which lets
  `guide_action.kind` hold `revisit`.
- **API tests:** `portal/api/tests/test_guide_engine.py`, `test_guide_store.py` and
  `test_guide_routes.py`.
- **Web, create, in `portal/web/src/guide/`:**
  - `api.ts`, `api.test.ts`;
  - `words.ts`, `words.test.ts`;
  - `useGuide.ts`, `useGuide.test.tsx`;
  - `turns/TurnView.tsx`, `turns/NumberAnswer.tsx`, `turns/LotFacts.tsx`, with tests;
  - `EndingView.tsx`, `ProjectPanel.tsx`, `GuidePage.tsx`, `CheckAndSend.tsx`, with tests.
- **Web, modify:**
  - `portal/web/src/App.tsx`: the two routes, behind the flag;
  - `portal/web/src/app/Dashboard.tsx`: a flag-only link to the guide.
- **Journeys:** `portal/web/e2e/guide.spec.ts`.
- **Docs:** `portal/README.md`, `OPEN_ITEMS.md`.

Tests run on the VM:
- API: `portal/vm.sh run 'cd portal/api && .venv/bin/pytest tests/<file> -q' </dev/null`.
- Web: `portal/vm.sh run 'cd portal/web && npx vitest run <path>' </dev/null`.
- The whole web suite and the build: `portal/vm.sh run 'cd portal/web && npm test && npm run build' </dev/null`.
- Journeys: from the Mac against the LAN copy after `portal/vm.sh lan`, as `portal/README.md`
  says, with `PORTAL_E2E_MAILPIT_AUTH` read from the VM's `.env` inline and never printed.

---

### Task 1: The API: openings, and Change ("revisit")

**Files:**
- Modify: `portal/api/portal_api/guide/engine.py`, `store.py`, `portal/api/portal_api/routes/guide.py`
- Create: `portal/api/migrations/versions/0010_guide_revisit.py`
- Test: `portal/api/tests/test_guide_engine.py`, `test_guide_store.py`, `test_guide_routes.py`

**Interfaces:**
- Consumes: plan 2's `Action`, `replay`, `apply`, `_derive`, `store.record`, `_change`.
- Produces:
  - `Action.kind: Literal["answer", "back", "revisit"]`.
  - `revisit` removes the entry for `turn_id`, and for `doesnt_fit:<turn_id>`, from `live`. It
    keeps the order of the rest. An unanswered turn raises `AnswerRejected("not_answered")`.
  - `replay` treats a recorded `revisit` the same way.
  - `POST /api/projects/{id}/guide/revisit`, body `{turn_id, base_revision}`. It answers with
    the same shape as `/answers`, and records event `guide.revisited` with the turn id.
  - `GET /api/projects/{id}/guide/openings`, which answers
    `{"openings": [{"id", "label", "part"}]}` for this project's parts. It is draft-gated like
    `GET /guide`, and someone else's project gets 404.

- [ ] **Step 1: Write the failing engine tests** in `test_guide_engine.py`:
  - `test_revisit_asks_that_turn_again`: after START, STORIES and `floor_area`, revisit
    `full_stories`. Expect `current.turn_id == "full_stories"`, and `floor_area` still in
    `live`.
  - `test_revisit_keeps_later_answers_that_still_apply`: with `roof_floors=1` and
    `top_knee_over_3ft="no"` given, revisit `roof_floors` and answer 0. Expect the next turn to be
    `basement_exposed_5ft` (or the first unanswered turn after it), and no `top_knee_over_3ft` in
    `history`.
  - `test_revisit_clears_the_doesnt_fit_choice`: after keeping 11 ft on D1's side setback,
    revisit `setback_side_1` and answer 11 again. Expect `current.turn_id ==
    "doesnt_fit:setback_side_1"`. The old "keep_mine" must not apply silently.
  - `test_revisit_of_an_unanswered_turn_is_refused`: expect `AnswerRejected` with reason
    `"not_answered"`.
  - `test_replay_of_a_recorded_revisit_matches_apply`: the same actions, given to `replay` and
    to repeated `apply`, give equal `State`s.
- [ ] **Step 2: Run them.** Expected: FAIL, because `revisit` is not an action.
- [ ] **Step 3: Implement `revisit`** in `replay` and `apply`, using one helper
  `_without(live, turn_id) -> tuple`.
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Write the failing store and route tests:**
  - `test_guide_store.py::test_a_revisit_is_recorded_and_replayed`.
  - `test_guide_routes.py::test_revisit_route` covers four cases:
    - 200 with the turn current;
    - 409 `changed_elsewhere` on a stale revision;
    - 422 `not_answered`;
    - 409 `locked` once staff lock the project.
  - `test_guide_routes.py::test_revisit_event_carries_no_value`: the event payload has
    `turn_id` only.
  - `test_guide_routes.py::test_openings_for_the_projects_parts`:
    - a building project lists `new_house` and not `change_of_use`;
    - someone else's project gets 404;
    - with drafts refused, it answers 503 `guide_not_approved`.
- [ ] **Step 6: Run them.** Expected: FAIL. The migration is missing, so the insert breaks the
  CHECK constraint, and the routes don't exist.
- [ ] **Step 7: Write migration 0010.** Drop and re-create the CHECK on `guide_action.kind` as
  `kind IN ('answer', 'back', 'restart', 'revisit')`, with a downgrade that restores 0009's.
  Then add the two routes. `revisit` goes through `_change`, as `back` does.
- [ ] **Step 8: Run the whole API suite.**
  Expected: all pass (1,425 + the new ones, 2 skipped).
- [ ] **Step 9: Commit:** `portal: the guide's Change action and its openings list`.

### Task 2: The guide's calls and its words

**Files:**
- Create: `portal/web/src/guide/api.ts`, `api.test.ts`, `words.ts`, `words.test.ts`

**Interfaces:**
- Consumes: the routes of plan 2 and Task 1. Also `Refusal` and the `request` handling style of
  `src/projects.ts`: `credentials: "include"`, with 401 → `signed_out`, 429 → `busy`, and a
  network failure → `unavailable`.
- Produces, in `api.ts`:
  ```ts
  type Step = { n: number; of: number; label: string };
  type Entry = { id: string; overline: string; answer: string; detail: string; why: string | null;
    cites: string[]; version: number; governs: string };
  type Check = { result: "fits" | "outside" | "cannot_check"; value: number | null; min: number | null;
    max: number | null; unit: string | null; room: number | null; gap: number | null;
    direction: "over" | "short" | null; reason: string | null; standard_keys: string[]; nearest: { id: string; value: number }[] };
  type Shown = { turn_id: string; kind: "lot" | "confirm" | "choice" | "number"; step: Step; ask: string;
    help: string | null; answers: { id: string; label: string; hint: string | null }[];
    input: { unit: string | null; min: number; max: number } | null; why: Entry | null; defines: Entry[];
    check: Check | null; facts_shown: LotFacts | null };
  type Ending = { kind: "not_here" | "town_judgment" | "ready" | "no_permit"; title: string; body: string;
    entry: Entry | null; settled: { turn_id: string; check: Check }[];
    unsettled: { turn_id: string | null; reason: string; district?: string; standard_keys?: string[] }[];
    reviews: unknown[]; allowed_uses: { district: string; uses: { use_key: string; code_name: string }[] }[];
    not_listed: unknown[]; notes: unknown[] };
  type Guide = { revision: number; opening: string; current: Shown | null; history: { shown: Shown; value: unknown }[];
    ending: Ending | null; step: Step | null; unsure: string[]; notes: { body: string; at: string }[]; drafts: string[] };
  type GuideRefusal = Refusal | "not_started" | "not_approved" | { conflict: true } | { rejected: string };
  getGuide(id): Promise<Guide | GuideRefusal>
  getOpenings(id): Promise<{ id: string; label: string; part: string }[] | GuideRefusal>
  startGuide(id, opening, rev), answerTurn(id, turnId, value, rev), goBack(id, rev),
  revisit(id, turnId, rev), addNote(id, body, rev): Promise<Guide | GuideRefusal>
  checkValue(id, turnId, value, signal?: AbortSignal): Promise<Check | { result: null } | GuideRefusal>
  ```
  Before writing these types, read `_out`, `store.notes` and `endings.finish`. Each type must
  match the JSON those produce. Where they differ from the sketch above, the code wins; write
  the difference in the ledger.
- Produces, in `words.ts`: `export const WORDS = { … } as const`, every screen string, each with
  a short comment saying where it shows. `export const WORD_STATUS = "draft"`.

- [ ] **Step 1: Write the failing tests:**
  - `api.test.ts`, with fetch mocked as `src/projects.test.ts` does:
    - `test_each_refusal_maps` covers 401, 404 `not_found`, 404 `not_started`,
      409 `changed_elsewhere`, 409 `locked`, 422 with a reason, 429, 503 `guide_not_approved`,
      and a network error;
    - `test_check_passes_its_abort_signal`.
  - `words.test.ts`:
    - `test_no_never_words` uses the list from plan 2's `NEVER_WORDS`, copied as a regex. A
      comment names `portal_api/guide/content.py` as the source to keep in step with.
    - `test_words_are_strings_without_markup`.
- [ ] **Step 2: Run them.** Expected: FAIL, because the modules don't exist.
- [ ] **Step 3: Implement `api.ts` and `words.ts`.**
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit:** `portal: the guide's calls and screen words (draft)`.

### Task 3: `useGuide`: the one place the conversation lives

**Files:**
- Create: `portal/web/src/guide/useGuide.ts`, `useGuide.test.tsx`

**Interfaces:**
- Consumes: Task 2's `api.ts`.
- Produces:
  ```ts
  type GuideView =
    | { phase: "loading" }
    | { phase: "pick"; openings: { id: string; label: string }[] }          // not started
    | { phase: "talk"; guide: Guide; busy: boolean; notice: keyof typeof WORDS.notices | null; locked: boolean }
    | { phase: "refused"; why: "signed_out" | "not_found" | "not_approved" | "unavailable" | "busy" };
  useGuide(projectId: string): {
    view: GuideView;
    start(opening: string): void; answer(turnId: string, value: unknown): void;
    back(): void; change(turnId: string): void; note(body: string): void; dismissNotice(): void;
  }
  ```
- Rules:
  - One change in flight. While `busy`, every action is ignored, not queued.
  - `{conflict}` reloads with `getGuide` and sets `notice: "changed_elsewhere"`.
  - `locked` sets `locked: true` and keeps the guide shown.
  - `{rejected}` reloads and sets `notice: "try_again"`.
  - `not_started` loads the openings and goes to `pick`.

- [ ] **Step 1: Write the failing tests**, with `api.ts` mocked through `vi.mock`:
  - `test_loads_then_talks`.
  - `test_not_started_offers_the_openings`.
  - `test_a_second_tap_while_busy_sends_nothing`.
  - `test_a_stale_revision_reloads_and_says_so`: answer gets `{conflict}`. Expect `getGuide`
    called once, the view to hold the reloaded guide, and `notice === "changed_elsewhere"`.
  - `test_locked_keeps_the_guide_read_only`.
  - `test_each_change_sends_the_latest_revision`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement it** with `useReducer`, keeping the revision in the reducer state, so a
  slow reply never sends an old revision.
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit:** `portal: useGuide, the guide's state and revision`.

### Task 4: The turns, and numbers with their limit

**Files:**
- Create: `portal/web/src/guide/turns/TurnView.tsx`, `NumberAnswer.tsx`, `LotFacts.tsx`, with
  `.test.tsx` beside each

**Interfaces:**
- Consumes:
  - plan 1's `AnswerList`, `WhyCard` and `Bubble`;
  - Task 2's `Shown`, `Check` and `checkValue`;
  - Task 2's `WORDS`.
- Produces:
  - `TurnView({ shown, projectId, busy, locked, onAnswer(value) })`. Its question heading is an
    `h2` with `tabIndex={-1}` and `data-turn-heading`, so `GuidePage` can focus it.
  - `NumberAnswer({ shown, projectId, busy, locked, onAnswer })`.
  - `LotFacts({ facts })`.
  - `parseNumber(text: string): number | null | "not_a_number"`, exported for its test.
- Behavior by kind:
  - **`lot`.** `LotFacts` lists the map-lot, the districts, and the acres and frontage. Acres and
    frontage say "approximate, from the tax maps" where `approximate` is true. A missing value
    is said as unknown (`WORDS.unknown`), never left blank. The turn's answers follow as an
    `AnswerList`.
  - **`confirm`, `choice`.** An `AnswerList` with `shown.answers`. `help` shows under the
    question. `why` and each of `defines` show as a `WhyCard`, with `codeHref` left out
    until the Code viewer exists.
    - **`doesnt_fit:` turns** (their `turn_id` starts with it) render as their own page, never
      as an error:
      - `shown.ask` (the gap, in the API's words) as the heading;
      - the `why` card;
      - the answers, with `nearest` first, as the API orders them.
  - **`number`.** A text field with `inputMode="decimal"` and the unit as an end adornment. A −
    and a + button step by 1, within `input.min`–`input.max`. A Next button and an
    "I'm not sure yet" button send `"unsure"`.
    - **Check MUI 9.5 first.** If `@mui/material` 9.5 exports a `NumberField`, use it.
      Otherwise use this composition. Record which one in the ledger.
    - **The live check.** As the value changes (debounced 300 ms), `checkValue` runs. The line
      under the field then shows one of:
      - `WORDS.room_left` (for example "Within the limit · 4 ft to spare") for `fits`;
      - `WORDS.past_limit` with the gap ("4 ft short of the limit here") for `outside`, in the
        normal text color;
      - `WORDS.town_decides` for `cannot_check`.
    - **The slider.** It appears once a check has returned a bound. It runs from `input.min` to
      the smaller of `input.max` and twice the bound. It has one labeled mark at the limit and
      moves the same value as the field.
    - **Stale replies.** Each call has its own `AbortController`. The newest request wins, and
      an older reply is dropped even if it arrives last.
- `parseNumber`:
  - strips spaces, and commas used as thousands separators;
  - accepts one decimal point;
  - gives `null` for "";
  - gives `"not_a_number"` for anything else.

- [ ] **Step 1: Write the failing tests:**
  - `LotFacts.test.tsx::test_unknowns_are_said_and_approximates_labeled`.
  - `TurnView.test.tsx`:
    - `test_choice_answers_once`;
    - `test_why_and_defines_render_as_cards`;
    - `test_doesnt_fit_is_a_page_not_an_error`: there is no element with `aria-invalid` or the
      `Mui-error` class, and `nearest` is the first answer;
    - `test_locked_turns_cannot_be_answered`.
  - `NumberAnswer.test.tsx`:
    - `test_numbers_are_read_the_way_people_write_them`: `parseNumber` on "1,800", " 25 ",
      "25.5", "", "twenty" gives 1800, 25, 25.5, null and "not_a_number";
    - `test_not_a_number_is_an_input_error_not_a_limit`;
    - `test_room_left_follows_the_check` (fits, outside, cannot_check);
    - `test_a_stale_check_never_replaces_a_newer_one`: three `checkValue` promises resolve in
      reverse order, and the line shows the newest value's check;
    - `test_steppers_stay_in_range`;
    - `test_slider_marks_the_limit_once_known`;
    - `test_unsure_sends_unsure`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement the three components.**
- [ ] **Step 4: Run them, then the whole web suite.** Expected: PASS, and the existing tests are
  unchanged.
- [ ] **Step 5: Commit:** `portal: the guide's turns and number answers`.

### Task 5: The guide page: conversation, step bar, Back, your project

**Files:**
- Create: `portal/web/src/guide/GuidePage.tsx`, `GuidePage.test.tsx`, `ProjectPanel.tsx`,
  `ProjectPanel.test.tsx`
- Modify: `portal/web/src/App.tsx`, `portal/web/src/app/Dashboard.tsx`

**Interfaces:**
- Consumes:
  - Tasks 3 and 4;
  - plan 1's `GuideShell`, `GuideTheme`, `Bubble` and `ReplyBox`;
  - `getProject` from `src/projects.ts`, for the project's title.
- Produces:
  - `/projects/:id/guide`, lazy, inside `RequireSignIn`, only when `VITE_GUIDE_PREVIEW=1`.
  - `ProjectPanel({ guide, onChange(turnId) })` shows two things:
    - the lot (map-lot, districts);
    - every answered turn, grouped by step, with its value (the answer's label, or the number
      and unit) and a Change button. A turn with a check carries a small "fits" tick, or a
      neutral "for the Town" mark. It never carries a red one.
- Layout and behavior:
  - **The shell.**
    - The title is the project's title, with the "Draft wording" chip.
    - The step bar comes from `guide.step`. Once the guide reaches an ending, it shows the last
      step.
  - **Back.** The app bar's back button runs `back()` while there is history. With no history,
    it links to `/projects/:id` ("Back to your project").
  - **The conversation.** History renders as pairs: `Bubble from="app"` with the question, and
    `Bubble from="you"` with the answer as said. Then comes the current `TurnView`, or the
    `EndingView` (Task 6), or the openings as an `AnswerList` in phase `pick`.
  - **Notes.**
    - `ReplyBox` sits under the current turn, with `WORDS.reply_placeholder`. It sends `note()`.
    - Notes show back as `Bubble from="you"`, with a one-line `WORDS.notes_kept` under the
      first: the Town reads them, and the guide doesn't act on them.
    - The reply box is hidden when `locked`.
  - **Focus.** When `current.turn_id` changes, focus moves to `[data-turn-heading]`. A polite
    live region reads its text once.
  - **Notices.** A `notice` shows as an MUI `Alert`, severity `info`, that can be dismissed.
    `locked` shows `WORDS.locked` in place of the reply box.
  - **The panel.** It sits in the shell's `aside` on a computer. On a phone, a "Your project"
    button in the app bar opens it in a bottom `Drawer`.
  - **The entry point.** A link on the HeroUI dashboard, shown only with the flag:
    `WORDS.try_guide` ("Try the guided version (preview)"). It is the one HeroUI file that
    changes. Its words are imported from `src/guide/words.ts` without importing MUI.

- [ ] **Step 1: Write the failing tests**, with `useGuide` mocked:
  - `test_history_shows_as_said`;
  - `test_back_with_history_goes_back_and_without_it_links_to_the_project`;
  - `test_focus_moves_to_each_new_question`;
  - `test_notes_are_kept_and_shown_back`;
  - `test_pick_lists_the_openings`;
  - `ProjectPanel.test.tsx::test_answers_grouped_by_step_with_change`;
  - `test_no_limit_mark_is_red`;
  - `Dashboard.test.tsx::test_guide_link_only_with_the_flag`, using `vi.stubEnv`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement the page, the panel, the route and the link.**
- [ ] **Step 4: Run the whole web suite and the build.** Expected: all pass. The build's
  HeroUI entry chunk does not contain `@mui`; check this with `grep -L` on the built
  `index-*.js`, as plan 1 did.
- [ ] **Step 5: Commit:** `portal: the guide page, with Back and your project`.

### Task 6: The endings, and Check and send

**Files:**
- Create: `portal/web/src/guide/EndingView.tsx`, `EndingView.test.tsx`, `CheckAndSend.tsx`,
  `CheckAndSend.test.tsx`
- Modify: `portal/web/src/App.tsx` (the `/projects/:id/guide/check` route, behind the flag)

**Interfaces:**
- Consumes:
  - Task 2's `Ending`;
  - `getProject` and `submitProject` from `src/projects.ts`: `needs` for fees, and `missing`
    for what the official form still lacks;
  - Task 3's `change()`.
- Produces:
  - `EndingView({ guide, project })`.
  - `CheckAndSend`, at `/projects/:id/guide/check`.
- Each ending shows `ending.title` as the heading, `ending.body`, and `ending.entry` as a
  `WhyCard` when present. Then, by kind:
  - **`ready`.** Each permit and review from `project.needs`: its name, `plain`, and fee words.
    Then the fee totals, as `NeedsPanel` words them, and a button to Check and send.
  - **`no_permit`.** No button to send. Show `WORDS.no_permit_keep` (keep to what you told us)
    and the settled checks.
  - **`town_judgment`.** Show two lists:
    - what was settled: each settled turn's question and "fits";
    - what goes to the Town: each `unsettled` reason in `WORDS.unsettled[reason]`, one per
      reason the engine produces.

    The Town Office line follows (`WORDS.talk_to_town`), with no contact details made up. There
    is no Send button (see Global Constraints).
  - **`not_here`.** Show `allowed_uses` per district as a list, and the Town Office line.
  - **An unknown `kind` or `reason`** shows `WORDS.town_decides`, never a blank and never a no.
- **Check and send:**
  - **The summary.** It is grouped by step: `ProjectPanel`'s rows, and each Change runs
    `change(turnId)` and returns to `/projects/:id/guide`. When the guide is back at its ending,
    `GuidePage` shows a "Back to Check and send" button.
  - **Then the fees**, from `project.needs`.
  - **Then "Send to the Town"**, which runs `submitProject` with the project's revision:
    - On success, it shows `WORDS.sent` and links to `/projects/:id`.
    - On `incomplete`, it lists what the official form still needs. Each item is the field's
      label from `project.form`, linking to the HeroUI project page's step for it.
    - Any refusal shows the matching `WORDS.refusals` line.
  - **Not ready.** The page is only for `ending.kind === "ready"`. Any other state redirects to
    `/projects/:id/guide`.

- [ ] **Step 1: Write the failing tests:**
  - `EndingView.test.tsx`:
    - `test_each_kind_shows_its_words` covers the four kinds;
    - `test_town_judgment_has_no_send`;
    - `test_every_unsettled_reason_has_words`, which lists the reasons from `endings.py` and
      `checks.py`: `not_listed`, `not_listed_in_one_district`, `unsure`,
      `kept_past_the_limit`, `talk_to_town`, `lot_disputed`, `no_district`,
      `not_checkable`, `two_districts`, `unknown_input`, `board_decides`, `town_only`,
      `contact_town`;
    - `test_unknown_reason_is_for_the_town`.
  - `CheckAndSend.test.tsx`:
    - `test_summary_fees_and_send`;
    - `test_change_from_check_and_send_returns_to_it`;
    - `test_incomplete_lists_the_forms_missing_fields_with_links`;
    - `test_not_ready_redirects`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement them.**
- [ ] **Step 4: Run the whole web suite and the build.** Expected: all pass.
- [ ] **Step 5: Commit:** `portal: the guide's endings, and Check and send`.

### Task 7: Journeys on the LAN, docs, and the chair's list

**Files:**
- Create: `portal/web/e2e/guide.spec.ts`
- Modify: `portal/README.md`, `OPEN_ITEMS.md`

- [ ] **Step 1: Write the journeys.** Each one signs in, starts a building project on a D1 lot
  (with `startProject` from `e2e/helpers.ts`, as `projects.spec.ts` does) and opens
  `/projects/:id/guide`. The journeys:
  - `a new house that fits reaches Check and send`. It goes lot → "Yes" → "So you mean…" →
    "Yes" → stories → floor area → units → setbacks → "ready" → Check and send. Run axe on the
    lot turn, a number turn, the ending and Check and send. It does not press Send: the
    official form still has fields the guide doesn't ask, so the journey checks that the
    "still needs" list shows.
  - `a side setback that doesn't fit offers the nearest`. It enters 11 ft on D1, sees the page,
    takes "Make it 15 ft", and the summary shows 15 ft with a tick. Run axe on the
    "doesn't fit" page.
  - `the guide picks up where it left off`. It answers three turns, reloads, and the same turn,
    history and step bar show.
  - `Change keeps what still applies`. From the panel, it changes the floor area; the guide
    asks only that, and returns to the next unanswered turn or the ending.
  - `on a phone, your project opens from the app bar` (Pixel 7). Nothing scrolls sideways.
  - The existing journeys still pass: `projects.spec.ts`, `refusals.spec.ts` and
    `guide-preview.spec.ts`.
- [ ] **Step 2: Rebuild the LAN copy and run them:** `portal/vm.sh lan`, then the journeys from
  the Mac. Expected: all pass at desktop and on the phone.
- [ ] **Step 3: Look at it.** Take screenshots at 1280×800 and Pixel 7 of the lot turn, a number
  turn with the slider, the "doesn't fit" page, the ready ending and Check and send. Write the
  paths in the ledger, and fix anything clipped, overlapping or below 48 px.
- [ ] **Step 4: Docs.**
  - **`portal/README.md`:** a "The guide's screens" section covering the routes, the flag,
    `words.ts`, and how to run the journeys.
  - **`OPEN_ITEMS.md`:** plan 3 on its branch. The chair's new questions:
    - approve the screens' words in `src/guide/words.ts`;
    - whether "This needs the Town's judgment" may send the project before design 4's handoff
      exists;
    - the Town Office's phone, hours and address for the screens;
    - whether a Change should say which later answers it reopened.
- [ ] **Step 5: Run the whole API suite, the whole web suite and the build.**
  Expected: all pass.
- [ ] **Step 6: Commit:** `portal: guide journeys, docs and the chair's questions`.
