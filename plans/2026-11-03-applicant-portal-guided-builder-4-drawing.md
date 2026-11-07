# Guided builder, plan 4 of 6: the lot drawing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When *where* matters, the guide shows the person's own lot. The drawing shows:
- the outline from the tax map, labelled approximate;
- the roads beside it;
- the front lot line, which the applicant confirms;
- the strips along each lot line where the Code's setback minimums keep the building out;
- the house placed by the distances the person entered.

Beside it, a checklist ticks each setback as the API reports it fits. The drawing never decides
(decision 12): dragging only changes the number in the field, and the API checks that number as
it does a typed one.

**Architecture:**
- **API.**
  - The project's property snapshot keeps the lot's outline. Today `_snapshot` drops it. The
    outline is stored in local feet, with its lot lines (runs of nearly straight boundary) and the
    roads alongside each line. This is a new module, `portal_api/lot_outline.py`.
  - A new guide turn, `front_line`, asks which line is the front. Its answers are made from the
    lot's lines.
  - `GET /api/projects/{id}/guide/drawing` returns the outline, each line's role (front, side,
    rear or another frontage), and the setback limits for this lot. All of it comes from the
    rulesets, through a new `limit_for` in `checks.py`.
- **Web.** A new `src/guide/drawing/` folder:
  - `geometry.ts`, pure drawing geometry: fit to the view, the front frame, the house box, drag
    to distance;
  - `LotDrawing`, the SVG;
  - `DrawingList`, the checklist, which is also the drawing's non-visual equivalent (§10.4);
  - `FrontLineAnswer`, the front turn.
  `NumberAnswer` becomes controllable, so a drag can set its field. The drawing sits in the
  right-hand column on a computer and inside the turn on a phone.
- Everything stays behind `VITE_GUIDE_PREVIEW=1`, in the guide's own chunk.

**Tech Stack:**
- API: Python 3.14, FastAPI, SQLAlchemy `text()`, PostGIS, pytest, as in `portal/api`.
- Web: React 19.3, TypeScript 5.9, MUI 9.5.0, Vitest 5, Testing Library, Playwright 1.64 with
  axe.
- The drawing is hand-written SVG. **No new packages.**

**Spec:** `specs/2026-10-30-applicant-portal-guided-builder.md` (approved by the chair 2026-10-30).
This plan implements:
- §4.1, which lot line is the front;
- the lot drawing in §4.4, with its live checklist;
- decision 12;
- the drawing's place in each layout (§4.8);
- the drawing's non-visual equivalent (§10.4).

The drawing in the review packet (§7.4) is plan 6.

**Branch:** `portal-guided-4-drawing`, cut from `portal-guided-3-screens`, because PR #25 is not
merged yet. If #25 merges first, merge `main` into this branch. Never rebase a pushed branch.

Earlier plans:
- 1, Foundations (PR #22);
- 2, the engine (PR #23), with the coverage answers (PR #24);
- 3, the screens (PR #25).

Later plans: 5, the pictures; 6, the applicant packet view.

## Global Constraints

- **The drawing never decides** (decision 12).
  - Every limit, "fits" and role comes from the API.
  - The web code does geometry only to draw: scaling, offsets, where the house box sits, and
    turning a drag into a distance. It never compares a number with a standard.
  - A dragged distance goes into the turn's number field, where the person sees it. It is checked
    and sent exactly like a typed one.
- **Always labelled approximate.** Every view of the drawing shows "Approximate: from the Town's
  tax map, not a survey" (draft) next to the SVG, never only in a tooltip.
- **Never guess a legal value** (CLAUDE.md rule 6). The Code's §2 lot rules decide some of this:
  - "each frontage must be evaluated to determine whether it qualifies as a primary or secondary
    frontage";
  - "No frontage that fronts onto a road, except an alley, may be treated as a rear lot line";
  - "Where a lot has more than one side, front, or rear lot line, the setback must be observed in
    each instance".

  So:
  - A lot with two or more lines along a road goes to the Town (unsettled reason
    `more_than_one_frontage`). The drawing draws no limit along a frontage that isn't the chosen
    front.
  - A line along a road is never given the rear role.
  - A front choice of "A different line" goes to the Town (unsettled `front_not_on_a_road`).
  - Districts that disagree draw no limit. Their row says why, using the reasons `checks.py`
    already returns.
- **The data says what it doesn't know.** There is no water, building or easement layer. The
  drawing doesn't draw them, and its list says so in one line (draft).
- **Every word is draft** and lives where plan 3 put it:
  - turn and answer words in `turns.yaml` and `wording.yaml` (`status: draft`);
  - screen words in `src/guide/words.ts`.
- **Words never used** (§10.3), as plan 3's tests enforce.
- **A limit is never red.** The strips are a neutral tint from the theme. A number past its limit
  is shown the way plan 3 shows it: "For the Town", never an error.
- **Accessibility** (§10.4):
  - The SVG has `role="img"` and an `aria-label` sentence.
  - `DrawingList` beside it carries every feature and limit as text.
  - Dragging is pointer-only, and the number field is its keyboard equivalent.
  - Lines tapped to choose the front have the same choice as answer buttons below.
  - Targets are 48 px.
  - axe runs on every journey that shows the drawing.
- **Old snapshots still work.** A project whose snapshot has no outline gets no `front_line`
  turn and no drawing, and nothing errors. Nothing is backfilled.
- **The vendored ruleset `portal_api/rulesets/adopted-v1.0/` is hash-pinned.** Don't edit it.
- **Tests run on the VM** (`portal/vm.sh run '…'`). Journeys run from the Mac against the LAN copy
  (`portal/README.md`, "The guide's screens"), at no more than 20 sign-in links an hour.

## Review Focus

1. **Real lots are messy.** The active import has 1,503 parcels:
   - median 14 vertices, 90th percentile 40, 99th percentile 96;
   - 42 multipolygons;
   - 5 lots with holes.

   Expect every one to produce an outline of at most a dozen lines, render without error, and
   keep the lot line roles sensible. Test: `test_outline_of_a_multipart_lot_uses_its_largest_part`
   and `test_noisy_boundary_merges_into_few_lines` (Task 1). A web test renders a 96-vertex
   outline.
2. **A lot with no road beside it** (a back lot reached by a right of way). Expect `front_line`
   to offer only "A different line" and "I'm not sure yet", and to end with the Town. Test:
   `test_a_lot_with_no_road_line_offers_only_a_different_line` (Task 2).
3. **Changing the front after the setbacks are entered.** Expect the roles to be worked out again.
   The setback numbers stand, the drawing redraws, and nothing is lost. Test:
   `test_changing_the_front_keeps_the_setbacks` (Task 2) and a GuidePage test (Task 6).
4. **A distance bigger than the lot** (side setbacks of 400 ft on a 100 ft lot). Expect the house
   box to be omitted, never drawn inside out. The list still shows the numbers and the API's
   checks. Test: `houseBox returns null when the distances cross` (Task 4).
5. **A snapshot made before this plan.** Expect no front turn, no drawing request error and the
   whole guide still working. Tests: `test_old_snapshot_has_no_front_turn` (Task 2) and
   `test_drawing_is_null_without_an_outline` (Task 3).

---

### Task 1: The lot's outline, kept in the snapshot

**Files:**
- Create: `portal/api/portal_api/lot_outline.py`
- Modify: `portal/api/portal_api/routes/forms.py` (`_snapshot`: keep `facts["outline"]`; still
  drop `facts["geometry"]`)
- Test: `portal/api/tests/test_lot_outline.py`

**Interfaces:**
- Produces: `outline(conn, parcel_id: int, parcels_import_id: int, streets_import_id: int | None)
  -> dict | None`, which returns:
  ```
  {"units": "ft", "approximate": True,
   "parts": [[[x, y], ...], ...],                # every part's outer ring; largest first
   "lines": [{"id": "L1", "points": [[x, y], ...], "length_ft": int,
              "street": {"name": str, "type": str | None} | None}, ...],
   "streets": [{"name": str, "points": [[x, y], ...]}, ...]}
  ```
  - Coordinates are feet, x east and y north, measured from the largest part's centroid and
    rounded to 0.1 ft. The data is EPSG:26919, so feet = metres × 3.28084.
  - Lines go round the largest part's outer ring, starting from the vertex nearest due south of
    the centroid and running clockwise.
  - Holes are ignored.
  - `None` when the parcel has no geometry.
- `_snapshot` adds `facts["outline"]` for a lookup lot. A manual lot has no `outline` key.

- [ ] **Step 1: Write the failing tests**

  Use `tests/test_property.py`'s `layers` fixture and `_id` helper. Its three test lots sit 5 m
  north of the Sheepscot Road line.
  - `test_outline_is_in_feet_about_the_centroid`: for the first test lot:
    - `parts[0]`'s bounding box is centred within 1 ft of (0, 0);
    - its width is within 1 ft of the PostGIS width × 3.28084.
  - `test_a_rectangular_lot_has_four_lines`: the lot gives 4 lines, and their lengths sum to
    within 2 ft of `ST_Perimeter` × 3.28084.
  - `test_the_line_along_the_road_names_it`: exactly one line has
    `street == {"name": "Sheepscot Road", "type": "R2"}`. It is the southern one: its points'
    mean y is the lowest.
  - `test_noisy_boundary_merges_into_few_lines`: a lot inserted with 40 extra vertices along its
    edges, each jittered ≤ 0.3 m off the edge, still gives 4 lines.
  - `test_outline_of_a_multipart_lot_uses_its_largest_part`: a MultiPolygon of a 50 × 50 m square
    and a 5 × 5 m square:
    - `parts` has 2 rings, the large one first;
    - `lines` traces only the large one.
  - `test_snapshot_keeps_the_outline_and_drops_geometry`: create a project through the API on a
    looked-up lot. Its snapshot facts have `outline` and no `geometry`.
  - `test_a_manual_lot_has_no_outline`: a manual-property project's facts have no `outline`.

- [ ] **Step 2: Run them and watch them fail**

  Run: `portal/vm.sh run 'cd portal/api && pytest -p no:warnings -o addopts="" -q tests/test_lot_outline.py'`
  Expected: FAIL, with an ImportError for `portal_api.lot_outline`.

- [ ] **Step 3: Implement `outline()` in `lot_outline.py`**

  - **Coordinates.** Read the parts and rings with `ST_Dump` and `ST_ExteriorRing`, in 26919, as
    GeoJSON. Then convert in Python.
  - **Merging edges into lines.** Merge consecutive ring edges into one line while:
    - the bearing turns by no more than `LINE_BEND_DEG = 25`; and
    - an edge shorter than `MIN_EDGE_FT = 3` is always merged into its neighbour.

    Then merge until at most `MAX_LINES = 12`, by repeatedly joining the pair of neighbours whose
    bearing turn is smallest.
  - **Streets.** Use one SQL query for the active streets import's segments within 30 m of the
    parcel, as local-feet points, clipped to the parcel's envelope expanded by 30 m.
  - **Which line is along a road.** A line is along a road when at least half its length lies
    within reach of a segment. Reach is the same as `property.py`'s `_REACH_SQL`: 35 m for a State
    Highway, else 20 m. Test it by sampling points every 5 ft along the line in Python against the
    segments' local points. Expose the 35/20 m values once, shared with `property.py`, rather
    than copying them.
  - Wire it into `_snapshot` for `source == "lookup"`.

- [ ] **Step 4: Run them and watch them pass, then run the whole API suite**

  Run: `portal/vm.sh run 'cd portal/api && pytest -p no:warnings -o addopts="" -q'`
  Expected: all pass. If a snapshot-equality test fails because facts gained `outline`, update it
  to expect the key. That is not a behaviour change.

- [ ] **Step 5: Commit**

  ```bash
  git add portal/api/portal_api/lot_outline.py portal/api/portal_api/routes/forms.py portal/api/tests/test_lot_outline.py
  git commit -m "portal: keep the lot's outline and its lines in the snapshot"
  ```
  Add any test file updated in Step 4 by name.

### Task 2: Which line is the front

**Files:**
- Modify:
  - `portal/api/portal_api/guide/engine.py`:
    - `Lot` gains `lines`;
    - facts seed `lot.has_outline`;
    - `answers_from: lot_lines`;
    - `Shown` gains `drawing`.
  - `portal/api/portal_api/guide/content.py`: `Turn` gains `drawing`; `TEMPLATE_SLOTS` allows
    `street`.
  - `portal/api/portal_api/guide/definitions/turns.yaml`:
    - the `front_line` turn;
    - a `drawing:` key on the four setback turns.
  - `portal/api/portal_api/guide/definitions/wording.yaml`: `front_along` and `front_other`.
  - `portal/api/portal_api/guide/endings.py`: the two new unsettled reasons.
- Test:
  - `portal/api/tests/test_guide_engine.py`;
  - `portal/api/tests/test_guide_endings.py`;
  - `portal/api/tests/test_guide_routes.py` (helpers only).

**Interfaces:**
- Consumes: Task 1's `facts["outline"]["lines"]`.
- Produces:
  - `Lot.lines: tuple[dict, ...]`: each `{"id", "length_ft", "street"}`, from the snapshot's
    outline, or `()`.
  - The turn `front_line`, defined as:

    ```yaml
    - id: front_line
      order: 15
      step: Your lot
      kind: choice
      when: {eq: [lot.has_outline, true]}
      ask: "Which lot line is the front?"
      help: "The front is the line along the road, as the Code counts it. We've drawn the lot from the tax map."
      answers_from: lot_lines
      fact: lot.front
      drawing: front
      status: draft
    ```

    Its answers:
    - one per line with a `street`, in line order: `{"id": <line id>, "label": "The line along
      {street}"}`, from `wording.front_along` with the street name;
    - then `{"id": "other", "label": wording.front_other}`, "A different line";
    - and the engine's "I'm not sure yet", as on every turn.
  - `Shown.drawing: Literal["front", "front_setback", "side_1", "side_2", "rear"] | None`. The
    setback turns carry `drawing: front_setback | side_1 | side_2 | rear`; every other turn has
    `None`.
  - New unsettled reasons:
    - `{"turn_id": "front_line", "reason": "more_than_one_frontage"}`, when the lot has two or
      more lines with a street, whichever was chosen;
    - `{"turn_id": "front_line", "reason": "front_not_on_a_road"}`, when the answer is `other`.

- [ ] **Step 1: Write the failing tests**

  The tests use a `Lot` with `lines` built in the test:
  - **Engine** (`test_guide_engine.py`):
    - `test_front_line_comes_after_the_lot_when_there_is_an_outline`: after `lot: yes` the
      current turn is `front_line`, and its answers are
      `["L1", "other", "unsure"]` for a lot with one road line `L1`. `L1`'s label is
      "The line along Sheepscot Road".
    - `test_old_snapshot_has_no_front_turn`: `Lot.from_snapshot` on facts without `outline`
      gives `lines == ()`, and after `lot: yes` the current turn is `confirm`.
    - `test_a_lot_with_no_road_line_offers_only_a_different_line`: the answers are
      `["other", "unsure"]`.
    - `test_changing_the_front_keeps_the_setbacks`:
      - walk to the end with front `L1`;
      - revisit `front_line` and answer `other`;
      - the four `building.setback.*` facts are unchanged.
    - `test_setback_turns_say_which_line_they_draw`: `Shown.drawing` is `"front_setback"` on
      `setback_front`, `"side_1"` on `setback_side_1`, and `None` on `full_stories`.
  - **Endings** (`test_guide_endings.py`):
    - `test_two_road_lines_go_to_the_town`: a ready house on a lot with two road lines ends
      `town_judgment`, with `more_than_one_frontage`.
    - `test_a_different_front_goes_to_the_town`: answering `other` ends `town_judgment`, with
      `front_not_on_a_road`.
    - `test_one_road_line_and_its_front_is_still_ready`: the D1 ready case, with front `L1`, stays
      `ready`.
  - **Routes** (`test_guide_routes.py`): the fixture lots now have an outline, so `started()` and
    `walk()` must answer `front_line`. Update the helpers to answer it with the first road line
    whenever it is the current turn. No route assertion changes.

- [ ] **Step 2: Run them and watch them fail**

  Run: `portal/vm.sh run 'cd portal/api && pytest -p no:warnings -o addopts="" -q tests/test_guide_engine.py tests/test_guide_endings.py'`
  Expected: FAIL, because `Lot` has no `lines` and there is no turn `front_line`.

- [ ] **Step 3: Implement**

  - Seed `facts["lot"]["has_outline"]` in `_derive`. First check that `evaluate` reads dotted
    paths, as `opening` does. If it doesn't, use the form it does read and ledger a ruling.
  - Add `lot_lines` beside `use_groups` in `_Build.answers`.
  - Add the two reasons in `endings.finish`, after the `unsure` reasons.
  - Content validation (`test_guide_content.py`) must accept `drawing` and `answers_from:
    lot_lines`. Extend it the way `use_groups` is accepted.

- [ ] **Step 4: Run the whole API suite and watch it pass**

  Run: `portal/vm.sh run 'cd portal/api && pytest -p no:warnings -o addopts="" -q'`
  Expected: all pass.

- [ ] **Step 5: Commit**

  ```bash
  git add portal/api/portal_api/guide/engine.py portal/api/portal_api/guide/content.py portal/api/portal_api/guide/endings.py portal/api/portal_api/guide/definitions/turns.yaml portal/api/portal_api/guide/definitions/wording.yaml portal/api/tests/test_guide_engine.py portal/api/tests/test_guide_endings.py portal/api/tests/test_guide_routes.py
  git commit -m "portal: the guide asks which lot line is the front"
  ```
  Add `test_guide_content.py` by name if Step 3 touched it.

### Task 3: The drawing's roles and limits

**Files:**
- Create: `portal/api/portal_api/guide/drawing.py`
- Modify:
  - `portal/api/portal_api/guide/checks.py` (`limit_for`);
  - `portal/api/portal_api/routes/guide.py` (`GET …/guide/drawing`).
- Test:
  - `portal/api/tests/test_guide_drawing.py`;
  - `portal/api/tests/test_guide_checks.py`.

**Interfaces:**
- Consumes: Task 1's outline (with points) and Task 2's `lot.front` fact.
- Produces:
  - `Limit` (frozen dataclass): `min: float | None`, `max: float | None`, `unit: str | None`,
    `reason: str | None`, `standard_keys: tuple[str, ...]`.
  - `limit_for(turn, lot) -> Limit | None`, in `checks.py`.
    - It uses the same district and standard lookup as `check_turn`. Factor the shared part out;
      don't copy it.
    - It returns `None` when the turn has no standard.
    - Disputed lot → `reason "lot_disputed"`; no district → `"no_district"`; a missing standard
      → `"not_checkable"`. These are the same reasons `check_turn` gives.
    - Districts that disagree on `(min, max)` → `reason "two_districts"`, no numbers.
    - Districts that agree → their bounds.
  - `roles(lines: list[dict], front_id: str | None) -> dict[str, str] | None`, in `drawing.py`:
    - `None` when `front_id` is `None`, `"other"` or not a line id;
    - otherwise `"front"` for the chosen line;
    - `"frontage"` for any other line with a street;
    - `"rear"` for the one non-street line whose outward normal is closest to opposite the
      front's, if any is within 60°;
    - `"side"` for the rest.
  - `GET /api/projects/{id}/guide/drawing` returns
    `{"outline": <Task 1's outline> | null, "front": str | null, "roles": {...} | null,
    "limits": {"front": L, "side": L, "rear": L}}`. Each `L` is `Limit` as a dict, or null.
    - The limits come from the turns `setback_front`, `setback_side_1` and `setback_rear`,
      through `limit_for`.
    - Someone else's project → 404, as the guide's other routes do.
    - No draft gate: the route returns no words.

- [ ] **Step 1: Write the failing tests**
  - `test_guide_checks.py`:
    - `test_limit_for_a_d1_side_is_its_minimum`: `limit_for(side_1, lot("D1"))` gives
      `min 15, max None, reason None`.
    - `test_limit_for_two_districts_that_disagree_has_no_numbers`: `("D1", "D4")` side gives
      `min None`, `reason "two_districts"`.
    - `test_limit_for_a_disputed_lot`: gives `reason "lot_disputed"`.
    - `test_limit_for_a_turn_without_a_standard_is_none`: `floor_area` gives `None`.
  - `test_guide_drawing.py`:
    - `test_rectangle_roles`: a square with the road on the south, front `L-south` →
      north `rear`, east and west `side`.
    - `test_a_second_road_line_is_a_frontage_not_a_rear`: a corner lot with roads south and
      north, front south → north is `frontage`, and there is no `rear`.
    - `test_no_roles_until_the_front_is_chosen`: `front_id` `None` or `"other"` gives `None`.
    - `test_drawing_route_returns_outline_roles_and_limits`, using the route fixtures: after
      `front_line` is answered, `roles` has the chosen id as `front`, and `limits.side.min` is
      the D1 value from `test_limit_for_a_d1_side_is_its_minimum`.
    - `test_drawing_is_null_without_an_outline`: a manual-lot project gets `outline: null` and
      `roles: null`, with status 200.
    - `test_someone_elses_drawing_is_404`.

- [ ] **Step 2: Run them and watch them fail**

  Run: `portal/vm.sh run 'cd portal/api && pytest -p no:warnings -o addopts="" -q tests/test_guide_drawing.py tests/test_guide_checks.py'`
  Expected: FAIL, with an ImportError for `limit_for` and `portal_api.guide.drawing`.

- [ ] **Step 3: Implement `limit_for`, `roles` and the route**

  An outward normal comes from each line's first-to-last chord, turned toward the outside of the
  clockwise ring.

- [ ] **Step 4: Run the whole API suite and watch it pass**

  Run: `portal/vm.sh run 'cd portal/api && pytest -p no:warnings -o addopts="" -q'`
  Expected: all pass, and the `check_turn` tests are unchanged.

- [ ] **Step 5: Commit**

  ```bash
  git add portal/api/portal_api/guide/drawing.py portal/api/portal_api/guide/checks.py portal/api/portal_api/routes/guide.py portal/api/tests/test_guide_drawing.py portal/api/tests/test_guide_checks.py
  git commit -m "portal: the drawing's lot line roles and setback limits"
  ```

### Task 4: Drawing geometry (web)

**Files:**
- Create:
  - `portal/web/src/guide/drawing/geometry.ts`;
  - `portal/web/src/guide/drawing/geometry.test.ts`;
  - `portal/web/src/guide/drawing/fixtures.ts`.
- Modify: `portal/web/src/guide/api.ts` (the `Drawing` types and `getDrawing`).

**Interfaces:**
- Consumes: Task 3's route.
- Produces:
  - In `api.ts`:
    - the types `Pt = [number, number]`, `LotLine`, `Outline`, `Limit` and
      `Drawing = { outline: Outline | null; front: string | null; roles: Record<string,
      "front"|"side"|"rear"|"frontage"> | null; limits: Record<"front"|"side"|"rear", Limit |
      null> }`;
    - `getDrawing(projectId: string): Promise<Drawing | GuideRefusal>`.
  - In `geometry.ts`:
    - `fitView(outline: Outline, pad = 20): { viewBox: string; scale: number }`, where `scale` is
      view units per foot;
    - `frontFrame(outline, frontId): { origin: Pt; u: Pt; v: Pt }`. `u` is the unit vector along
      the front line, oriented so that +`v` (its left-hand normal) points into the lot;
    - `toFrame(f, p): Pt` and `fromFrame(f, q): Pt`;
    - `rayToBoundary(polygon: Pt[], from: Pt, dir: Pt): number | null`, the distance to the
      nearest boundary crossing;
    - `houseBox(outline, frontId, d: { front?: number; side_1?: number; side_2?: number; rear?:
      number }, flip = false): Pt[] | null`;
    - `dragDistance(outline, frontId, edge: "front"|"side_1"|"side_2"|"rear", pointer: Pt, flip =
      false): number`, rounded to the nearest whole foot and never below 0.
  - `fixtures.ts`: `RECT`, a 100 × 200 ft lot with its road on the south, front `L1`;
    `TRAPEZOID`; `CORNER`; `NOISY96`, with 96 vertices.

- [ ] **Step 1: Write the failing tests** (`geometry.test.ts`)
  - `fitView keeps the whole outline inside the view with its padding`.
  - `frontFrame points v into the lot`: for `RECT`, `v ≈ [0, 1]`.
  - `houseBox places each edge at its entered distance`: on `RECT`, with `{front: 30, side_1: 20,
    side_2: 20, rear: 40}`, the box in the frame spans u 20–80 and v 30–160, each within 0.5.
    - `side_1` is the left side seen from the road.
    - With `flip`, `side_1` is the right side. With `{side_1: 10, side_2: 30}` that gives u 30–90
      instead of 10–70.
  - `houseBox needs the front distance`: without `front` it returns `null`.
  - `houseBox uses the lot's own edge for a distance not entered yet`: with `{front: 30}` only,
    the box's other three edges lie on the boundary, each within 0.5.
  - `houseBox returns null when the distances cross`: `{front: 30, side_1: 400, side_2: 400}` on
    `RECT` → `null`.
  - `houseBox works on a trapezoid`: on `TRAPEZOID` the box lies inside the polygon. Check every
    corner with a point-in-polygon test written in the test.
  - `dragDistance reads the distance a pointer sets`: on `RECT`, a pointer at frame v 55 on the
    front edge gives 55, and a pointer outside the lot gives 0.
  - `geometry copes with 96 vertices`: on `NOISY96`, `houseBox` gives a 4-point box and no
    `NaN`.

- [ ] **Step 2: Run them and watch them fail**

  Run: `portal/vm.sh run 'cd portal/web && npx vitest run src/guide/drawing/geometry.test.ts'`
  Expected: FAIL, because the module isn't found.

- [ ] **Step 3: Implement `geometry.ts`**

  The house box algorithm:
  1. Work in the front frame. `vFront = d.front`.
  2. Cast a ray from `(uMid, vFront)` along +v, where `uMid` is the middle of the front line's
     u-span. `vRear` is the hit, minus `d.rear` (or minus 0 when it isn't entered).
  3. Cast rays both ways along u from `(uMid, (vFront + vRear) / 2)`. `uLeft` is the left hit
     plus the left distance, and `uRight` is the right hit minus the right distance.
  4. Without `flip`, the left distance is `side_1` and the right is `side_2`. With `flip`,
     `side_2` is on the left and `side_1` on the right.
  5. Return `null` if `uLeft >= uRight`, `vFront >= vRear` or any ray misses.

  No standards and no `limits` are read here.

- [ ] **Step 4: Run them and watch them pass, then run `npm test` and `npx tsc --noEmit`**

  Run: `portal/vm.sh run 'cd portal/web && npm test && npx tsc --noEmit'`
  Expected: all pass, and tsc is clean.

- [ ] **Step 5: Commit**

  ```bash
  git add portal/web/src/guide/drawing/geometry.ts portal/web/src/guide/drawing/geometry.test.ts portal/web/src/guide/drawing/fixtures.ts portal/web/src/guide/api.ts
  git commit -m "portal: the lot drawing's geometry"
  ```

### Task 5: `LotDrawing` and `DrawingList`

**Files:**
- Create:
  - `portal/web/src/guide/drawing/LotDrawing.tsx` and `LotDrawing.test.tsx`;
  - `portal/web/src/guide/drawing/DrawingList.tsx` and `DrawingList.test.tsx`.
- Modify: `portal/web/src/guide/words.ts` (the `drawing` words, draft).

**Interfaces:**
- Consumes: Task 4's geometry and types, and plan 3's `Guide.checks` and `Check`.
- Produces:
  - `LotDrawing(props: { drawing: Drawing; distances: { front?: number; side_1?: number;
    side_2?: number; rear?: number }; asking?: "front" | "front_setback" | "side_1" | "side_2" |
    "rear"; onPickLine?: (id: string) => void; onDrag?: (n: number) => void })`. It renders:
    - the outline parts;
    - the road lines, with their names;
    - each lot line, labelled "about N ft" (draft words);
    - the front line, drawn heavier;
    - a strip along every line whose role has a limit with `min`: an SVG mask stroke of width
      2 × min × scale with round caps, clipped to the lot;
    - for a `max`, a dashed line offset `max` ft inward from each line of that role;
    - the house box, when `houseBox` gives one, with each entered distance labelled;
    - a visible caption, `WORDS.drawing.approximate`;
    - a "Swap sides" button, which only flips the picture. It is shown when `distances.side_1`
      or `side_2` is known.

    When `asking` names a setback, the box's matching edge has a 48 px pointer handle. Dragging
    it calls `onDrag(dragDistance(...))`. The handle is `aria-hidden`, because the number field
    is the keyboard path.

    When `asking === "front"`, each lot line is a 48 px hit target that calls `onPickLine(id)`,
    with an `aria-label` from `WORDS.drawing.pick_line`.

    `role="img"`, with an `aria-label` built from `WORDS.drawing.summary`.
  - `DrawingList(props: { drawing: Drawing; guide: Guide })`, a list with one row per role in
    the order front, side, rear, then any frontage. Each row shows:
    - the role's name;
    - its limit as the API gives it ("at least 15 ft"), or the plain reason when there are no
      numbers (reuse `WORDS.unsettled` keys for `two_districts` and the others);
    - the person's number;
    - the mark plan 3's `ProjectPanel` uses ("Fits" / "For the Town"), from `guide.checks` for
      that turn.

    A frontage row says the Town decides its setback. One last row says
    `WORDS.drawing.not_shown`: water, buildings and easements aren't on the Town's data.

- [ ] **Step 1: Write the failing tests**
  - `LotDrawing.test.tsx`:
    - `it shows the approximate caption`;
    - `it labels each line with its length`;
    - `it draws a strip for each role with a minimum and none for a frontage` (`CORNER`): one
      mask stroke per side and rear line, none on the frontage;
    - `it draws no strip when the limit has no numbers`;
    - `it draws the house box once the front distance is known`;
    - `picking a line calls onPickLine` (only when `asking === "front"`);
    - `dragging the asked edge calls onDrag with the new distance`: fire pointer events on the
      handle, then expect `onDrag(55)` with `RECT`;
    - `only the asked edge has a handle`;
    - `Swap sides flips which side the first distance is on`;
    - `the svg has an accessible name`;
    - `it renders a 96-vertex lot` (`NOISY96`).
  - `DrawingList.test.tsx`:
    - `rows follow the roles with the API's limits`;
    - `a row's mark comes from guide.checks, never from comparing numbers`: give a check of
      `fits` with a value that is below `min`, and expect "Fits";
    - `a frontage row says the Town decides`;
    - `it says what the Town's data doesn't show`.
  - `words.test.ts` already scans the whole of `WORDS`, so the new words are covered.

- [ ] **Step 2: Run them and watch them fail**

  Run: `portal/vm.sh run 'cd portal/web && npx vitest run src/guide/drawing'`
  Expected: FAIL, because the modules aren't found.

- [ ] **Step 3: Implement both components**

  - Colours come from the theme: lines in `text.primary`, strips in `action.selected`, roads in
    `grey`. Nothing uses `error`.
  - The SVG scales to its container width. On a phone its height is capped at 50 dvh.

- [ ] **Step 4: Run `npm test`, `npx tsc --noEmit` and `npm run build`**

  Run: `portal/vm.sh run 'cd portal/web && npm test && npx tsc --noEmit && npm run build'`
  Expected: all pass, with no MUI in the entry chunk (plan 3's check).

- [ ] **Step 5: Commit**

  ```bash
  git add portal/web/src/guide/drawing/LotDrawing.tsx portal/web/src/guide/drawing/LotDrawing.test.tsx portal/web/src/guide/drawing/DrawingList.tsx portal/web/src/guide/drawing/DrawingList.test.tsx portal/web/src/guide/words.ts
  git commit -m "portal: the lot drawing and its checklist"
  ```

### Task 6: The drawing in the conversation

**Files:**
- Create:
  - `portal/web/src/guide/drawing/useDrawing.ts`;
  - `portal/web/src/guide/turns/FrontLineAnswer.tsx` and `FrontLineAnswer.test.tsx`.
- Modify:
  - `portal/web/src/guide/turns/NumberAnswer.tsx`: optional controlled `text` and
    `onTextChange`;
  - `portal/web/src/guide/turns/TurnView.tsx`: routes `drawing === "front"` to
    `FrontLineAnswer`;
  - `portal/web/src/guide/GuidePage.tsx`: the drawing in the aside, inline on a phone, and the
    drag draft;
  - `portal/web/src/guide/ProjectPanel.tsx`: the drawing and list at the top when there is an
    outline;
  - `portal/web/src/guide/CheckAndSend.tsx`: the drawing and list in the summary;
  - `portal/web/src/guide/api.ts`: `Shown.drawing`.
- Test:
  - `GuidePage.test.tsx`;
  - `NumberAnswer.test.tsx`;
  - `CheckAndSend.test.tsx`;
  - `ProjectPanel.test.tsx`.

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces:
  - `useDrawing(projectId: string, revision: number | undefined): Drawing | null`. It fetches
    again whenever the revision changes, and gives `null` while loading, on a refusal, or when
    `outline` is null.
  - `NumberAnswer` accepts `text?: string` and `onTextChange?: (t: string) => void`. When given,
    the field is controlled; the live check, steppers and slider still work from that text.
    Without them it behaves as in plan 3.
  - `FrontLineAnswer({ shown, drawing, busy, locked, onAnswer })`: the drawing with
    `asking="front"`, with plan 3's `AnswerList` of the same answers below it. Tapping a line
    calls `onAnswer(id)`, exactly as its button does.
  - In `GuidePage`:
    - when `current.drawing` names a setback, the page holds the field's text. The drawing's
      `onDrag` sets it to `String(n)`, and `NumberAnswer` shows it.
    - **Wide:** the drawing and list head the aside panel.
    - **Phone:** they appear inside the turn, above the field, on `front` and setback turns only.
      They are also in the "Your project" sheet.
  - The distances passed to `LotDrawing` come from the facts the guide already shows (the
    history values and `checks`), plus the field's draft for the turn being asked.

- [ ] **Step 1: Write the failing tests**
  - `NumberAnswer.test.tsx`: `a controlled field shows the text it is given and reports typing`.
    The plan 3 tests are unchanged.
  - `FrontLineAnswer.test.tsx`:
    - `tapping a line answers with its id`;
    - `the same choice is offered as buttons`;
    - `I'm not sure yet is offered`.
  - `GuidePage.test.tsx`:
    - `the front turn shows the drawing`;
    - `on a setback turn, dragging fills the field and Next sends that number`: mock `getDrawing`
      with `RECT`, then drag, expect the field to read "55", press Next, and expect `answerTurn`
      to be called with 55;
    - `no drawing when the lot has no outline`: `outline: null`, and no SVG;
    - `changing the front redraws`: the revision changes, so `getDrawing` is called again;
    - `on a phone the drawing is inside the turn, not the aside`.
  - `ProjectPanel.test.tsx`: `the panel heads with the drawing when there is one`.
  - `CheckAndSend.test.tsx`: `check and send shows the drawing and its list`.

- [ ] **Step 2: Run them and watch them fail**

  Run: `portal/vm.sh run 'cd portal/web && npx vitest run src/guide'`
  Expected: FAIL on the new tests only.

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run `npm test`, `npx tsc --noEmit` and `npm run build`**

  Run: `portal/vm.sh run 'cd portal/web && npm test && npx tsc --noEmit && npm run build'`
  Expected: all pass, with no MUI in the entry chunk.

- [ ] **Step 5: Commit**

  ```bash
  git add portal/web/src/guide/drawing/useDrawing.ts portal/web/src/guide/turns/FrontLineAnswer.tsx portal/web/src/guide/turns/FrontLineAnswer.test.tsx portal/web/src/guide/turns/NumberAnswer.tsx portal/web/src/guide/turns/NumberAnswer.test.tsx portal/web/src/guide/turns/TurnView.tsx portal/web/src/guide/GuidePage.tsx portal/web/src/guide/GuidePage.test.tsx portal/web/src/guide/ProjectPanel.tsx portal/web/src/guide/ProjectPanel.test.tsx portal/web/src/guide/CheckAndSend.tsx portal/web/src/guide/CheckAndSend.test.tsx portal/web/src/guide/api.ts
  git commit -m "portal: the lot drawing in the guide, with the front line and dragging"
  ```

### Task 7: Journeys, docs and the chair's questions

**Files:**
- Modify:
  - `portal/web/e2e/guide.spec.ts`;
  - `portal/README.md` ("The guide's screens");
  - `OPEN_ITEMS.md`.

- [ ] **Step 1: Update and add journeys** (`guide.spec.ts`)
  - `openGuide` answers the front turn: after the lot, the question is "Which lot line is the
    front?"; run axe ("guide: the front line"); choose the first "The line along …" button.
    Every existing journey then runs as before.
  - New: `the drawing shows the lot and the setbacks`. At "nearest side lot line":
    - the drawing's caption "Approximate" is visible;
    - the list shows the side row with "at least 15 ft";
    - run axe ("guide: the drawing").
  - New, desktop only: `dragging the side edge fills the field`. Drag the handle and expect the
    field to change to a whole number. Press Next, and the next question is asked.
  - The phone journeys check that the drawing sits inside the turn, and that the page is no wider
    than the screen.
  - Lot 4-36 must have a road line, and the journeys depend on it. If it doesn't, stop and
    report: don't pick another lot silently.

- [ ] **Step 2: Rebuild the LAN copy and run the journeys**

  Run `portal/vm.sh lan`. Then run, from `portal/web`, with the README's inline Mailpit auth:
  `npx playwright test e2e/guide.spec.ts e2e/projects.spec.ts e2e/refusals.spec.ts e2e/guide-preview.spec.ts`
  Expected: all pass at desktop and phone. Check the sign-in window first and stay at 20 links
  an hour or fewer. Split the run across hours if needed.

- [ ] **Step 3: Look at it**

  Take screenshots of the front turn, a setback turn and Check and send, at desktop and phone, to
  the scratchpad (not committed). Read them. Fix anything a person would trip on, test-first.
  Ledger what was found.

- [ ] **Step 4: Docs and open items**
  - `portal/README.md`: one paragraph on the drawing:
    - what it shows;
    - that it never decides;
    - where the outline comes from;
    - that old snapshots have none.
  - `OPEN_ITEMS.md`: plan 4 is on its branch; next is plan 5. Add for the chair:
    - the drawing's words (draft, in `words.ts`, `turns.yaml` and `wording.yaml`);
    - whether "the nearest side" should default to the left as seen from the road;
    - that corner and through lots go to the Town (Code §2's "each frontage must be
      evaluated"), until the library has an entry for the primary-frontage rule.

- [ ] **Step 5: Commit**

  ```bash
  git add portal/web/e2e/guide.spec.ts portal/README.md OPEN_ITEMS.md
  git commit -m "portal: drawing journeys, docs and the chair's questions"
  ```
