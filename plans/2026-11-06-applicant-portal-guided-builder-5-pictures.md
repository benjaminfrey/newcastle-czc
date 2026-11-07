# Guided builder, plan 5 of 6: the pictures — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The guide opens on a picture of a Newcastle lot, seen from above at an angle. Its parts
are places to tap: the two projects the guide covers start their conversation, and the rest say
"coming soon". The hardest explanation, how stories are counted, gets a cut-away picture of the same
house. All of it goes to the chair as a sample sheet before the rest is drawn.

**Architecture:**
- **API.**
  - Every spot in the scene is an opening in `openings.yaml`, with `guided: true|false` and its
    spot id in `picture`.
  - `GET /guide/openings` lists every opening, saying for each whether the project has its part.
  - `POST /guide` refuses an unguided opening.
  - Entries gain an optional `picture` id and `picture_alt` description, which are approved wording.
- **Web.** A new `src/guide/pictures/` folder:
  - `palette.ts`, the shared colours from the theme;
  - `iso.ts`, the tilted-view projection;
  - `LotScene`, the scene's SVG and its spots;
  - `StoriesPicture`, the cut-away;
  - `index.ts`, which maps a picture id to its component.

  A new `OpeningPicker` replaces the pick step's answer list. It holds the scene, the same
  projects as a list, the text box, and the two pop-ups ("Add … to this project?" and "coming
  soon").
- Everything stays behind `VITE_GUIDE_PREVIEW=1`, in the guide's own chunk.

**Tech Stack:**
- API: Python 3.14, FastAPI, SQLAlchemy `text()`, pytest.
- Web: React 19.3, TypeScript 5.9, MUI 9.5.0, Vitest 5, Testing Library, Playwright 1.64 with axe.
- The pictures are hand-written SVG. **No new packages.**

**Spec:** `specs/2026-11-06-applicant-portal-guided-builder-pictures.md` (approved by the chair
2026-11-06), under `specs/2026-10-30-applicant-portal-guided-builder.md` §4.2, §6 and decision 15.

**Branch:** `portal-guided-5-pictures`, cut from `portal-guided-4-drawing` (PR #26 is not merged
yet). If #26 merges first, merge `main` into this branch. Never rebase a pushed branch.

**The plan stops after Task 6** for the chair's approval of the sample sheet (decision 15). Task 7
runs only on his answers.

## Global Constraints

- **Pictures illustrate; they never decide.** No picture carries a number of its own or draws a
  distance that could read as a limit. The 3-foot and 5-foot tests are labelled as the Code
  states them (Art. 5 §7.c.5–6).
- **One palette**, in `pictures/palette.ts`, read from the MUI theme (`theme.palette.picture`), so
  a later theme can change it. Colours:
  - clapboard `#fdfcf8`, its shaded side `#e9e5dc`;
  - barn red `#a8432f`, its shaded side `#93392a`;
  - roof grey `#59606a`, its shaded side `#4a4f57`;
  - lot green `#bcd3a0`, its edge `#8fae73`;
  - stone grey `#9a938a`;
  - maple orange `#d9822b`;
  - door blue `#2f5d7c`;
  - chimney brick `#8a4b3a`.

  Flat fills, with shading only on the side faces. No outlines, gradients or texture.
- **One view.** Every picture uses `iso.ts`'s projection, so every part lines up.
- **Every word is approved before the public sees it.** New words start as drafts:
  - spot names (`openings.yaml` `label`, `status: draft`);
  - picture descriptions (`entries.yaml` `picture_alt`; the changed entry goes back to
    `status: draft`);
  - screen words (`words.ts`, which turns `WORD_STATUS` back to `"draft"` until the chair approves
    them).
- **Words never used** (§10.3): the existing `NEVER_WORDS` and `words.test.ts` checks cover every
  new word.
- **Accessibility** (§10.4):
  - The scene is one `role="img"` with a description.
  - Its spots are pointer targets only, at least 48 px across at any width, and not tab stops.
  - The list under the scene is the keyboard and screen-reader way in, one button per project, in
    the same order.
  - axe runs on every journey that shows the scene or a picture.
- **Old projects still work.** A project mid-conversation never sees the scene; a project with no
  matching part gets the "add" question, never an error.
- **The vendored ruleset `portal_api/rulesets/adopted-v1.0/` is hash-pinned.** Don't edit it.
- **Tests run on the VM** (`portal/vm.sh run '…'`). Journeys run from the Mac against the LAN copy,
  at no more than 20 sign-in links an hour.

## Review Focus

1. **Adding the part fails**: a stale revision, a locked project, `too_many`, or the form not
   approved. Expect the dialog to show the refusal in plain words and the conversation not to
   start. Nothing is half-done: no part without a conversation, no orphan note. Test:
   `a refused add leaves the project as it was` (Task 4).
2. **A double tap.** Expect one part and one start, never two: the dialog's buttons and the list
   are disabled while a change is in flight. Test: `a second tap while adding is ignored` (Task 4).
3. **A narrow phone, 320 px wide.** Expect every spot's target to stay at least 48 px and inside
   the picture, with no two targets overlapping. Test: `spot targets are 48 px and apart at 320 px`
   (Task 3) and the journey's measurement (Task 6).
4. **Text typed, then "coming soon" or "No".** Expect the text to stay in the box. When a
   conversation starts it is saved exactly once, as the first note; a failed note shows "try
   again" and keeps the text. Test: `the box's text survives coming soon and is saved once on
   start` (Task 4).
5. **"No" on "So you mean…" sends the person back to the pick step.** Expect the scene again, with
   the part already in the project, so the next tap starts straight away without asking. Test:
   `after No the scene starts without asking again` (Task 4).

---

### Task 1: The API: every spot is an opening

**Files:**
- Modify: `portal/api/portal_api/guide/definitions/openings.yaml`
- Modify: `portal/api/portal_api/guide/content.py` (`Opening`, its loader)
- Modify: `portal/api/portal_api/routes/guide.py` (`openings`, `start`)
- Test: `portal/api/tests/test_guide_content.py`, `portal/api/tests/test_guide_routes.py`

**Interfaces:**
- Produces:
  - `Opening` gains `guided: bool`. `part: str | None` and `confirm: str | None` are required only
    when `guided` is true. `picture` is the spot id.
  - `GET /api/projects/{id}/guide/openings` returns
    `{"openings": [{"id", "label", "part", "picture", "guided", "in_project"}]}`, every opening in
    file order. `in_project` is whether the project has a part of that kind (false when `part` is
    null).
  - `POST /api/projects/{id}/guide` with an unguided opening returns 422 `not_guided`. It is
    checked before `wrong_project`.

The ten openings, in this order (`id`, `label`, `picture`, `part`):
1. `new_house`, "A new house", `house_outline`, `building`, guided, approved;
2. `change_of_use`, "A change of use", `barn`, `use`, guided, approved;
3. `addition`, "An addition", `addition`;
4. `deck`, "A deck", `deck`;
5. `solar`, "Solar panels", `solar`;
6. `outbuilding`, "A garage, barn or shed", `shed`;
7. `driveway`, "A driveway", `driveway`;
8. `fence_or_wall`, "A fence or wall", `wall`;
9. `sign`, "A sign", `sign`;
10. `home_business`, "A business at home", `shingle`.

Openings 3–10 are not guided, have no part and are drafts. `change_of_use`'s picture changes from
`shopfront` to `barn`, which is not a word change, so it stays approved.

- [ ] **Step 1: Write the failing tests.** In `test_guide_content.py`:
  - `test_every_spot_is_an_opening_and_only_two_are_guided`: the ids above, in order; `guided` true
    only for `new_house` and `change_of_use`; every `picture` distinct.
  - `test_a_guided_opening_needs_a_part_and_a_template`: using `copy`, dropping `part` from
    `new_house` raises `ContentError`. Dropping it from `deck` loads.
  - Add the eight new ids to `STILL_DRAFT` in `test_the_chair_approved_everything_shown_on_2026_11_06`.

  In `test_guide_routes.py`:
  - `test_openings_list_every_spot_and_say_which_the_project_has`, for a building-only project:
    10 openings; `in_project` true only for `new_house`; `change_of_use` has `in_project` false.
  - `test_an_unguided_opening_is_refused`: `start(alice, pid, "deck")` returns 422 `not_guided`.
  - Change `test_openings_for_the_projects_parts`: it no longer filters by part, so assert the
    full list.
- [ ] **Step 2: Run them on the VM.** Expected: they fail on the missing ids and the missing `guided`.
- [ ] **Step 3: Implement.** In the loader, `_status` still applies to every opening. `part` and
  `confirm` are checked only when `guided`. The route's draft refusal now covers every listed
  opening, so production refuses the scene until the new names are approved (spec §9).
- [ ] **Step 4: Run the whole API suite on the VM.** Expected: all pass.
- [ ] **Step 5: Commit** (`openings.yaml`, `content.py`, `routes/guide.py`, the two tests).

### Task 2: The API: an entry can carry a picture

**Files:**
- Modify: `portal/api/portal_api/guide/definitions/entries.yaml` (`how_stories_count`)
- Modify: `portal/api/portal_api/guide/content.py` (`Entry`), `portal/api/portal_api/guide/engine.py` (`_entry` dict at line ~136)
- Test: `portal/api/tests/test_guide_content.py`, `portal/api/tests/test_guide_engine.py`

**Interfaces:**
- Produces:
  - `Entry` gains `picture: str | None = None` and `picture_alt: str | None = None`.
  - The serialized entry gains `"picture"` and `"picture_alt"`, both null when absent.
  - A `picture` without a `picture_alt` is a `ContentError`.

`how_stories_count` gets `picture: stories` and draft `picture_alt`:
"A house cut open to show its floors. The first and second floors have full-height walls and
count as stories. A floor inside the roof counts only if the roof meets its wall more than 3 feet
above the floor. A basement counts if 5 feet or more of its wall shows above the ground along the
front."

Its `status` goes back to `draft`: drop `approved_by` and `approved_on`, and add it to
`STILL_DRAFT`.

- [ ] **Step 1: Write the failing tests:**
  - `test_a_picture_needs_its_description` (using `copy`);
  - `test_the_stories_entry_carries_its_picture`: replaying `new_house` to `full_stories`, the
    `why` entry has `picture == "stories"` and a `picture_alt` mentioning "3 feet" and "5 feet".
- [ ] **Step 2: Run them on the VM.** Expected: FAIL.
- [ ] **Step 3: Implement.** `picture_alt` is checked by `test_no_never_words` through `_readable`;
  add it there.
- [ ] **Step 4: Run the whole API suite on the VM.** Expected: all pass.
- [ ] **Step 5: Commit.**

### Task 3: The scene and the stories picture

**Files:**
- Create: `portal/web/src/guide/pictures/palette.ts`, `iso.ts`, `LotScene.tsx`, `StoriesPicture.tsx`, `index.ts`
- Modify: `portal/web/src/guide/theme/` (add `palette.picture` from the Global Constraints values)
- Modify: `portal/web/src/guide/GuidePreview.tsx` (`<Attic />` → `<StoriesPicture />`)
- Test: `portal/web/src/guide/pictures/iso.test.ts`, `LotScene.test.tsx`, `StoriesPicture.test.tsx`

**Interfaces:**
- Produces:
  - `iso(x: number, y: number, z: number): [number, number]`: lot feet to SVG units, as a 2:1
    dimetric projection. x runs east and y north, with the road along the south (y = 0). The view
    looks from the south-west, so the road runs along the front.
  - `usePicturePalette(): PicturePalette`: the theme's `palette.picture`, typed.
  - `SPOTS: { id: string; at: [number, number, number] }[]`: one per `picture` id from Task 1, at
    its place in the lot.
  - `LotScene(props: { onSpot?: (picture: string) => void; labels: Record<string, string>;
    description: string })`:
    - one `<svg role="img" aria-label={description}>`;
    - each spot is a `<g data-spot={id}>` with a visible marker and a transparent hit circle of
      radius `24 / ppu` (the plan 4 pattern in `LotDrawing.tsx`). The circle is `aria-hidden`, and
      clicking it calls `onSpot(id)`;
    - each spot's label shows by its marker.
  - `StoriesPicture()`: the cut-away, same house and view, labelled "1st story", "2nd story", "In
    the roof", "Basement", "More than 3 ft?" and "5 ft or more?". The labels come from `words.ts`
    `pictures.stories`.
  - `PICTURES: Record<string, () => JSX.Element>`, which maps `stories` to `StoriesPicture`.

The scene's subject is fixed by spec §5:
- the white cape with a centre chimney, its connected ell and the red barn, in a row along the
  road;
- the stone wall along the road edge;
- the maple at the front-left;
- the shed at the back of the lot;
- the empty back-right corner with a dashed house outline (`house_outline`).

Each spot sits where spec §6.1 puts it. Compose it within those rules.

- [ ] **Step 1: Write the failing tests:**
  - `iso.test.ts`: `iso(0,0,0)` is the origin; a step east and a step north move in opposite x
    directions and the same y direction; a step up moves straight up.
  - `LotScene.test.tsx`: one `img` with the description; a `[data-spot]` for every `SPOTS` id;
    clicking `[data-spot="deck"] circle` calls `onSpot("deck")`; no spot is focusable (no
    `tabindex`, no button role).
  - `spot targets are 48 px and apart at 320 px`: render at width 320 with a stubbed
    `getBoundingClientRect`. Each circle's radius × ppu ≥ 24, and no two circles' centres are
    closer than 48 px.
  - `StoriesPicture.test.tsx`: shows the six labels; contains no digit outside those labels.
- [ ] **Step 2: Run them.** `npm test -- src/guide/pictures` on the VM. Expected: FAIL.
- [ ] **Step 3: Implement.** Draw back to front: lot, wall, barn, ell, cape, then the spots. The
  palette comes only from `usePicturePalette`. No hex literal outside `theme/`, which a test
  greps for in `pictures/`.
- [ ] **Step 4: Run the web suite.** Expected: all pass.
- [ ] **Step 5: Commit.**

### Task 4: The opening picker

**Files:**
- Create: `portal/web/src/guide/OpeningPicker.tsx`
- Modify: `portal/web/src/guide/api.ts` (`Opening`, `Entry`), `useGuide.ts` (`start`), `GuidePage.tsx` (pick phase), `words.ts`, `turns/TurnView.tsx` and `turns/NumberAnswer.tsx` (the `card` helper passes the picture)
- Modify: `portal/web/src/app/Dashboard.tsx` (the guide link shows for every project)
- Test: `portal/web/src/guide/OpeningPicker.test.tsx`, `useGuide.test.tsx`, `GuidePage.test.tsx`, `words.test.ts`, `app/Dashboard.test.tsx`

**Interfaces:**
- Consumes: Task 1's openings shape; Task 2's entry fields; Task 3's `LotScene` and `PICTURES`;
  `addPart(id, baseRevision, kind)` from `src/projects.ts`.
- Produces:
  - `Opening = { id: string; label: string; part: string | null; picture: string; guided: boolean;
    in_project: boolean }`.
  - `Entry` gains `picture: string | null; picture_alt: string | null`. The `card` helpers pass
    `picture={PICTURES[e.picture]?.()}` and `pictureAlt={e.picture_alt}` when both are set.
  - `useGuide().start(opening: string, opts?: { addPart?: string; note?: string }): Promise<boolean>`:
    - with `addPart`, it calls `addPart` first, using the pick view's revision, then starts with
      the revision that returns;
    - with `note`, it posts the note once after a successful start;
    - a refusal at any step dispatches as `run` does today and returns false. `addPart`'s own
      results map as follows:
      - a `Refusal` string goes to the existing handling;
      - `{ conflict }` reloads with `changed_elsewhere`;
      - `{ invalid }` (for example `too_many` or `already_there`) reloads with `try_again`.
  - `OpeningPicker(props: { openings: Opening[]; busy: boolean; onStart: (id: string, opts) =>
    Promise<boolean> })`.

**Words (`words.ts`, `WORD_STATUS` back to `"draft"`):**
- `picker.ask`: "What would you like to do?" (the approved `pick_opening`, reused)
- `picker.description`: "A Newcastle lot with a cape, its ell and a barn, a stone wall and a maple. Tap a project, or choose one from the list below."
- `picker.list_heading`: "Or choose from the list"
- `picker.box_label`: "In your own words, what would you like to do? (optional)"
- `picker.add_title`: "Add {label} to this project?"
- `picker.add_body`: "Your project doesn't have this yet. Adding it adds its questions to your project's form."
- `picker.add_yes`: "Add it"
- `picker.add_no`: "Not now"
- `picker.soon_title`: "{label}: coming soon"
- `picker.soon_body`: "The guide can't walk you through this yet. You can still fill in your project's form, or contact the Town Office."
- `picker.soon_ok`: "OK"
- `pictures.stories`: the six labels from Task 3

The behaviour, spec §6.2:
- A guided opening already in the project: `onStart(id, { note })`.
- A guided opening not in the project: the "add" dialog. "Add it" calls
  `onStart(id, { addPart: part, note })`; "Not now" closes the dialog.
- Not guided: the "coming soon" dialog.
- The box's text is passed as `note` only when it isn't blank. It stays in the box until a start
  succeeds.

- [ ] **Step 1: Write the failing tests.** In `OpeningPicker.test.tsx`:
  - `a guided project in the project starts at once`;
  - `a guided project not in the project asks to add it` (the title reads "Add A new house to this
    project?", then "Add it" calls `onStart("new_house", { addPart: "building" })`);
  - `not now closes the question and starts nothing`;
  - `a project the guide doesn't cover says coming soon`;
  - `the list offers the same projects in the same order as the scene`;
  - `the box's text survives coming soon and is saved once on start`;
  - `a second tap while adding is ignored`.

  In `useGuide.test.tsx`:
  - `start adds the part, then starts with the new revision`;
  - `a refused add leaves the project as it was`: `addPart` returns `"locked"`, so `startGuide` and
    `addNote` are never called;
  - `a failed note after a start shows try again and keeps the guide started`.

  Also:
  - In `GuidePage.test.tsx`, `after No the scene starts without asking again`: the pick view with
    `new_house` `in_project: true`; tapping it calls `start` with no `addPart`.
  - In `Dashboard.test.tsx`, the guide link shows for a project with only a driveway.
  - In `words.test.ts`, `WORD_STATUS` is `"draft"` and the new words pass the banned-words check.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** The dialogs are MUI `Dialog`s with their buttons at least 48 px tall.
  The busy state disables both the list and the dialog buttons. `GuidePage`'s pick phase renders
  `OpeningPicker` in place of `AnswerList`.
- [ ] **Step 4: Run the web suite, tsc and the build.** Expected: all pass, the build is clean.
- [ ] **Step 5: Commit.**

### Task 5: The stories picture in the "Why" card

**Files:**
- Test: `portal/web/src/guide/turns/TurnView.test.tsx`

This task proves the end-to-end path from Tasks 2–4. Write it as its own test so a reviewer can
see it.

- [ ] **Step 1: Write the failing test** `the stories explanation shows its picture with its
  description`: a shown turn whose `why` entry has `picture: "stories"` and a `picture_alt`; the
  card has an `img` named by the `picture_alt`, containing the "In the roof" label.
- [ ] **Step 2: Run it.** If it already passes because of Task 4's `card` change, note that in the
  ledger and keep the test.
- [ ] **Step 3: Run the web suite.** Expected: all pass.
- [ ] **Step 4: Commit.**

### Task 6: Journeys, the LAN preview and the sample sheet

**Files:**
- Modify: `portal/web/e2e/guide.spec.ts`
- Create: `portal/web/e2e/sample-sheet.spec.ts`
- Create: `memos/2026-11-xx-guided-builder-pictures-sample-sheet.md` (the date it is written)
- Modify: `OPEN_ITEMS.md`

- [ ] **Step 1: Journeys** in `guide.spec.ts`, at desktop and phone, with axe on each:
  - The scene shows. Tapping the house outline on a building project starts the conversation, as
    the list did.
  - Tapping the deck shows "coming soon".
  - On a project with only a use, tapping the house outline asks to add it. "Add it" starts the
    conversation, and the project page then lists a building.
  - At the phone size, measure every spot's hit circle: at least 48 px, and inside the SVG's box.
  - The stories "Why" card shows its picture.

  Update the existing journeys that tapped the old list to tap the list under the scene.
- [ ] **Step 2: Rebuild the LAN copy** (`portal/vm.sh lan`) and run the journeys from the Mac.
  Expected: all pass, with the two device-specific skips as before.
- [ ] **Step 3: The sample sheet's pictures.** `sample-sheet.spec.ts` runs only when
  `PORTAL_SAMPLE_SHEET_OUT` is set. It saves PNGs of these:
  - the scene at 1280 and at 390 px wide;
  - close-ups of three spots (the deck, the solar panels, the house outline);
  - the stories card.
- [ ] **Step 4: Write the memo.** It contains:
  - the PNGs;
  - each spot's name and the picture descriptions;
  - the new screen words;
  - the decisions for the chair:
    1. the palette;
    2. the buildings and their arrangement;
    3. the spots and where they sit;
    4. one stories picture or three (spec §7);
    5. the words, as drafted.

  Render it with `build/build-memo.sh` into the scratchpad and check it by eye.
- [ ] **Step 5: `OPEN_ITEMS.md`.** Plan 5 is on its branch. The sample sheet is with the chair.
- [ ] **Step 6: Commit.**
- [ ] **STOP.** Report to the chair, with the LAN preview's address and the memo. Run the
  whole-branch review only after Task 7.

### Task 7: On the chair's answers — the setbacks picture and the approvals

Runs only after the chair approves the sample sheet. His answers go into the memo, as with the
wording memo.

- [ ] **Step 1: Make each change the chair asks for to the scene or the stories picture.** Write a
  test for each one that changes behaviour or words.
- [ ] **Step 2: The setbacks picture.** Same view and palette:
  - The house sits on the lot, with front, side and rear arrows from each lot line to the nearest
    part of the house, labelled "Front", "Side" and "Rear". No distances are drawn.
  - `entries.yaml` `setbacks` gets `picture: setbacks` and a `picture_alt`, which go to the chair.
  - Tests mirror Task 3's `StoriesPicture` tests and Task 5's.
- [ ] **Step 3: Record the approvals the chair gave**, as plan 4's wording round did:
  - `status: approved`, `approved_by` and `approved_on` on the openings and entries;
  - `WORD_STATUS` set to `"approved"`.

  Update the tests that pin statuses.
- [ ] **Step 4: Run the full API and web suites, rebuild the LAN copy and run the journeys.**
- [ ] **Step 5: Commit.** Then run the whole-branch review (one fresh reviewer, the most capable
  model).
