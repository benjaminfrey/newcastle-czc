# Guided builder, plan 2 of 6: the conversation engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the API the engine behind the guided conversation. It reads Town-written turns,
asks them in order for a project, checks each number against the Code's standards for the
lot, offers the nearest version that fits, and ends in one of the spec's endings. It records
every turn exactly as shown, and it never interprets free text.

**Architecture:**
- A new package `portal_api/guide/` with five parts:
  - **content**: YAML files with draft/approved status, like `forms/definitions/`;
  - **engine**: a pure function that replays the recorded answers into facts and the next turn,
    so Back and reloads need no saved state;
  - **checks**: over plan 1's `standards` layer;
  - **endings**: over the existing screener;
  - **store**: an append-only table.
- New routes under `/api/projects/{id}/guide` run it for an existing project. They respect the
  project's revision, the lock and the draft gate.
- A bridge copies the guide's numbers into the project's existing form answers, so
  `needs.py`, fees and Send keep working unchanged.
- No screens; plan 3 builds them.

**Tech Stack:**
- Python 3.14, FastAPI, SQLAlchemy Core with `text()`, Alembic, pydantic, PyYAML and pytest,
  as in `portal/api`.
- No new packages.

**Spec:** `specs/2026-10-30-applicant-portal-guided-builder.md` (approved by the chair
2026-10-30). This plan implements:
- §4.1, the lot as the Town knows it, confirmed;
- §4.3 for pictures only, since decision 14 is open;
- §4.4 without the drawing;
- §4.5 and §4.6;
- §5's rule that the rulesets do every number;
- §10.3's word list.

Earlier plan: `plans/2026-10-30-applicant-portal-guided-builder-1-foundations.md`, merged as PR
#22. Later plans: 3 conversation screens, 4 lot drawing, 5 pictures, 6 applicant packet view.

## Global Constraints

- **Never guess a legal value** (CLAUDE.md rule 6).
  - A standard whose status isn't `checkable` gives `cannot_check`, never "outside".
  - An uncertain "no" becomes a question for the Town, never a result (spec §4.5).
  - `standards_overrides.json` stays empty; only the chair's recorded answers fill it.
- **The engine never reads free text.** Decision 14: until the chair rules on an outside AI,
  what a person types is stored for staff and shown back to them, and nothing branches on it.
  No code in `portal_api/guide/` may pass note text to any function except the store.
- **Every word an applicant reads comes from the content files**, each entry `draft` or
  `approved` with `approved_by` and `approved_on` (the `forms/definitions.py` rules).
  - All content this plan adds is `draft`.
  - A state that rests on any draft is refused with `503 guide_not_approved` unless
    `allow_draft_rules` is set, as `_refused` does for forms.
- **Words never used** (§10.3; builder's proposed list, for the chair to approve):
  `approved`, `denied`, `granted`, `rejected`, `permit issued`, `compliant`, `violates`.
  Allowed: "fits", "within the limit", "over the limit by", and Code citations.
- **"I'm not sure yet" is an answer on every question turn**, and it never ends the
  conversation (§4.3).
- **The engine is deterministic.** The same content, lot and answers always give the same turns,
  byte for byte (§5, "consistency is tested").
- **Every citation in the content resolves** through `Ruleset.cite` (a missing one fails loading,
  as `_check_cite` does).
- **The guide's records are append-only**, like `answer` and `section_note`: Back is a new row,
  not a delete, because backing up is pattern data (§9).
- **The HeroUI app and its journeys keep working unchanged** (decision 13).
- **Style:**
  - frozen dataclasses;
  - plain-words module docstrings;
  - `functools.cache` for loaded content;
  - SQL through `text()` with the caller's connection, as `projects.py` does.
- **Commits:**
  - branch `portal-guided-2-engine`, cut from `main` at 8b1ce9e;
  - stage files by name;
  - end each message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`;
  - commit per task; push only on the chair's OK.

## Review Focus

1. **A lot in two districts whose limits differ.** Expect `cannot_check` with the reason "two
   districts", never the stricter or looser limit picked silently. Pinned in Task 3,
   `test_two_districts_that_disagree_cannot_be_checked`.
2. **The person says the lot facts are wrong** ("That's not right"). Expect every
   district-based check to become `cannot_check` from then on, and the conversation to
   continue. Pinned in Task 3, `test_disputed_lot_makes_district_checks_uncertain`.
3. **Content changes mid-conversation**: a turn is removed or reordered after someone answered
   it. Expect the replay to skip answers to turns that no longer exist, without an error, and
   to ask what is now unanswered. Pinned in Task 2, `test_replay_skips_answers_to_removed_turns`.
4. **Back past the first answer, or Back twice in a row.** Expect the first turn, never an
   error or a negative index. Pinned in Task 2, `test_back_at_the_start_is_harmless`.
5. **A number at exactly the limit, and a number that isn't a number** (a string, NaN, a bool).
   Expect "fits" at the bound, and `422 bad_value` for anything else. Pinned in Task 3,
   `test_the_bound_itself_fits`, and Task 6, `test_answer_rejects_non_numbers`.

---

## File map

- **Create:**
  - `portal/api/portal_api/guide/__init__.py`
  - `content.py`: load and validate the content;
  - `engine.py`: replay and the next turn;
  - `checks.py`: numbers against standards;
  - `endings.py`;
  - `store.py`;
  - `bridge.py`.
- **Create the content** in `portal/api/portal_api/guide/definitions/`:
  - `openings.yaml`;
  - `turns.yaml`;
  - `entries.yaml`, a draft seed of the library (design 2 replaces how it is stored, not its
    fields);
  - `wording.yaml`: the shared words, endings and "So you mean…" templates.
- **Create** `portal/api/portal_api/routes/guide.py` and
  `portal/api/migrations/versions/0009_guide.py`.
- **Modify** `portal/api/portal_api/main.py` to include the router.
- **Tests** in `portal/api/tests/`:
  - `test_guide_content.py`
  - `test_guide_engine.py`
  - `test_guide_checks.py`
  - `test_guide_endings.py`
  - `test_guide_store.py`
  - `test_guide_routes.py`
- **Docs:**
  - `portal/README.md` (a "Guide engine" section);
  - `OPEN_ITEMS.md` (plan 1 merged, plan 2 on its branch, the word list for the chair).

Tests that touch the database need the dev services, as `tests/conftest.py` says. Run them on
the VM with `portal/vm.sh run 'cd portal/api && .venv/bin/pytest tests/<file> -q'`, after
`portal/vm.sh sync`. Pure tests (content, engine, checks, endings) run on the VM the same way.

---

### Task 1: The content files and their loader

**Files:**
- Create: `guide/__init__.py`, `guide/content.py`, the four YAML files.
- Test: `tests/test_guide_content.py`.

**Interfaces:**
- **Consumes:**
  - `load_ruleset()` and `Ruleset.cite` (`portal_api/ruleset.py`);
  - `validate` from `portal_api/forms/expr.py` for `when` conditions;
  - `load_parts()` for part ids.
- **Produces:**

```python
class ContentError(Exception): ...

@dataclass(frozen=True)
class Answer:   id: str; label: str; hint: str | None; set: dict[str, object]  # fact path -> value
@dataclass(frozen=True)
class Entry:    id: str; overline: str; answer: str; detail: str; why: str; cites: tuple[str, ...]
                version: int; status: str; approved_by: str | None; approved_on: str | None
@dataclass(frozen=True)
class Turn:     id: str; order: int; step: str; kind: Literal["lot", "confirm", "choice", "number"]
                when: dict | None; ask: str; help: str | None; answers: tuple[Answer, ...]
                fact: str | None            # number turns: the fact path the value sets
                unit: str | None; min: float | None; max: float | None
                standard: dict | None       # {source, field, building?} for checks.py
                computed: str | None        # a named calculation in checks.py, e.g. "stories"
                answer_field: str | None    # the project form field the bridge fills
                why: str | None; defines: tuple[str, ...]; cite: str | None; status: str
@dataclass(frozen=True)
class Opening:  id: str; label: str; picture: str; part: str; facts: dict[str, object]
                screener: dict; confirm: str; status: str
@dataclass(frozen=True)
class Content:  openings: dict[str, Opening]; turns: tuple[Turn, ...]; entries: dict[str, Entry]
                wording: dict[str, dict]; digest: str   # sha256 of the four files, in name order

def load_content(root: Path | None = None) -> Content     # functools.cache on the resolved root
def drafts_in(content: Content, *, opening: str, turn_ids: list[str], entry_ids: list[str],
              wording_keys: list[str]) -> list[str]        # "turns.yaml: stories_full" etc.
NEVER_WORDS: re.Pattern   # the §10.3 list in Global Constraints, word-bounded, case-insensitive
TEMPLATE_SLOTS = frozenset({"opening", "map_lot", "districts"})
```

- [ ] **Step 1: Write the failing tests.**
  - `test_content_loads`: `load_content()` returns 2 openings (`new_house`, `change_of_use`),
    turns sorted by `order`, and a 64-character digest.
  - `test_every_cite_resolves`: in a temp copy, a turn whose `cite` is `"99.1.a"` makes
    `load_content(tmp)` raise `ContentError` naming `turns.yaml` and the turn id. Entries
    with a bad `cites` item fail the same way.
  - `test_status_rules`: a turn with `status: approved` and no `approved_on` raises.
  - `test_answers_only_set_known_facts`: an answer whose `set` names a path not in
    `content.FACTS` raises.
    - `FACTS` is the closed set of fact paths the engine knows, listed in `content.py`:
      `lot.confirmed`, `building.full_stories`, `building.roof_floors`, `building.top_knee_over_3ft`,
      `building.basement_exposed_5ft`, `building.floor_area_sf`, `building.dwelling_units`,
      `building.setback.front`, `building.setback.side_1`, `building.setback.side_2`,
      `building.setback.rear`, `use.group` and `use.use_key`.
  - `test_number_turns_need_bounds_and_a_fact`: a `number` turn without `fact`, `min` or
    `max` raises.
  - `test_templates_use_known_slots`: a `wording.yaml` template with `{owner}` raises. Only
    `TEMPLATE_SLOTS` are allowed.
  - `test_no_never_words`: every string a person can read (`ask`, `help`, answer labels and
    hints, entry `overline/answer/detail/why`, every `wording` value, opening labels) has no
    match for `NEVER_WORDS`. Also check that `NEVER_WORDS` matches "Approved" and
    "permit issued" but not "approval" in "fits".
  - `test_all_new_content_is_draft`: every entry in the four files has `status: draft`. This
    test changes only when the chair approves wording.

- [ ] **Step 2: Run them.** `portal/vm.sh run 'cd portal/api && .venv/bin/pytest tests/test_guide_content.py -q'`.
  Expected: FAIL with `ModuleNotFoundError: portal_api.guide`.

- [ ] **Step 3: Write the content (all `draft`).** The wording is the builder's first draft, at
  an 8th-grade level.
  - **`openings.yaml`:**
    - `new_house`: part `building`; picture `house`; facts `{}`; confirm template `confirm_build`;
      screener `{project: [build], building.kind: new}`.
    - `change_of_use`: part `use`, `picture: shopfront`; screener `{project: [use]}`;
      confirm `confirm_use`.
  - **`turns.yaml`**, in this order:
    1. `lot` (kind `lot`, step "Your lot");
    2. `confirm` (kind `confirm`, step "Your project");
    3. for `new_house`, using a `when` on an `opening` fact the engine sets, step "The building":
       - `full_stories` (number 1–6, `computed: stories`, `standard: {source: building_matrix,
         field: total_stories, building: Residential}`, `answer_field: stories`, why
         `how_stories_count`, cites `5.7.c.3`–`5.7.c.6`);
       - `roof_floors` (number 0–3);
       - `top_knee_over_3ft` (choice yes/no, when `roof_floors >= 1`);
       - `basement_exposed_5ft` (choice yes/no);
       - `floor_area` (number 1–10,000,000 sf, `answer_field: floor_area`);
       - `dwelling_units` (number 0–100, `answer_field: dwelling_units`);
    4. step "Where it sits": the four setbacks (number 0–50,000 ft, `standard: {source: dimension,
       field: primary_building_placement.<primary_front|side|rear>_setback}`, both side turns using `side_setback`, `answer_field`
       `setback_front`, `setback_side_1`, `setback_side_2`, `setback_rear`, cite `2.3.c.3`). The
       pairing of a new house with the Residential column and the primary-building placement
       panel follows the chair's approved form (`compare: primary_building_placement`), and
       stays draft here for him to confirm;
    5. for `change_of_use`, step "The use": `use_group` (choice, answers from the approved groups
       in `use-groups.yaml`, generated at load, never retyped) and `use_key` (choice, the chosen
       group's uses with their Code names).
  - **`entries.yaml`:**
    - `how_stories_count`: answer "Only floors with full-height outside walls count."; cites
      `5.7.c.3`, `5.7.c.4`, `5.7.c.5`, `5.7.c.6`;
    - `setbacks`: cite `2.3.c.3`;
    - `use_table`: cite `8.15.b.1`;
    - `use_not_listed`: cite `8.19.b.1`, reworded from the screener's text, which has the word "granted".
  - **`wording.yaml`:**
    - `unsure` "I'm not sure yet";
    - `talk_to_town` "Talk to the Town Office";
    - `keep_mine` "Keep my number and ask the Town";
    - `nearest` "Make it {value} {unit}" (the one non-slot template, filled by checks.py with a
      number and unit only);
    - `governs` "The adopted Code governs if anything here differs from it.";
    - templates `confirm_build` "So you'd like to build {opening} on lot {map_lot}, in
      {districts}. Is that right?" and `confirm_use`;
    - the five endings' titles and one-line bodies (`no_permit`, `covered`, `ready`,
      `town_judgment`, `not_here`). `no_permit`'s body says the Town may confirm it in writing,
      and its wording waits on counsel (spec §12 item 2).

- [ ] **Step 4: Implement `content.py`.**
  - Reuse `forms/definitions.py`'s `_check_status` and `_check_cite` by importing them (rename
    them public only if a linter objects; don't copy them).
  - Load the YAML files with `yaml.safe_load`.

- [ ] **Step 5: Run the tests.** Expected: PASS (8 tests).

- [ ] **Step 6: Commit** `portal: the guide's content files and loader, all draft (guided plan 2, Task 1)`.

### Task 2: The engine: replay, the next turn, Back, "So you mean…"

**Files:**
- Create: `guide/engine.py`.
- Test: `tests/test_guide_engine.py`.

**Interfaces:**
- **Consumes:** `Content`, `Turn`, `Answer` (Task 1); `evaluate` (`forms/expr.py`); a `Lot`
  built from the project's property snapshot.
- **Produces:**

```python
@dataclass(frozen=True)
class Lot:      map_lot: str | None; district_codes: tuple[str, ...]; district_names: tuple[str, ...]
                acres: float | None; frontage_ft: int | None   # approximate, from the tax map
                @staticmethod
                def from_snapshot(snapshot: dict) -> "Lot"
@dataclass(frozen=True)
class Step:     n: int; of: int; label: str
@dataclass(frozen=True)
class Shown:    turn_id: str; kind: str; step: Step; ask: str; help: str | None
                answers: tuple[dict, ...]     # {"id","label","hint"}; "unsure" always last
                input: dict | None            # {"unit","min","max"} for number turns
                why: dict | None; defines: tuple[dict, ...]   # entries as dicts, with "governs"
                check: dict | None            # Task 3 fills it for a recorded number
                facts_shown: dict | None      # lot turns: what the Town knows, labeled approximate
@dataclass(frozen=True)
class Action:   kind: Literal["answer", "back"]; turn_id: str | None; value: object
@dataclass(frozen=True)
class State:    opening: str; facts: dict; history: tuple[tuple[Shown, object], ...]
                current: Shown | None; ending: dict | None; unsure: tuple[str, ...]
                drafts: tuple[str, ...]

class AnswerRejected(Exception):
    reason: str   # "not_current", "not_an_answer", "bad_value", "out_of_range"

def replay(content: Content, opening: str, lot: Lot, actions: list[Action]) -> State
def apply(content: Content, state: State, lot: Lot, action: Action) -> State   # raises AnswerRejected
```

- **Rules the tests pin:**
  - **Next turn:** the first turn in `order` whose `when` is true on the facts and that has no
    live answer.
  - **The `opening` fact:** `facts["opening"]` is set from the opening id before any turn.
  - **Back:** removes the last live answer. With none, it does nothing.
  - **Removed content:** answers to turn ids no longer in the content are skipped in replay.
  - **"I'm not sure yet":** it records `unsure` for that turn, leaves the turn's fact unknown and
    moves on.
  - **`confirm` turns:**
    - The text is the template with its slots filled: `opening` is the opening's label,
      lower-cased; `map_lot` is from the lot; `districts` is the district names joined with "and".
    - "No" sets `facts["confirmed"] = False`. The current turn then becomes the opening picker
      (kind `choice`, answers = openings; `wording.yaml` has its ask), and the engine waits for
      the start route to restart it.
  - **`lot` turns:** the turn shows `facts_shown` (districts, acres, frontage, each with
    `"approximate": True` where it comes from the tax map), and its answers are `yes` and
    `not_right`. `not_right` sets `lot.confirmed = False` and continues.
  - **`drafts`:** the result of `drafts_in` for everything the state shows.

- [ ] **Step 1: Write the failing tests.** Use a fixed `Lot` (`map_lot "012-034"`, `("D4",)`,
  `("Village Residential",)`, 0.5 acres) and the real content.
  - `test_first_turn_is_the_lot`
  - `test_confirm_sentence_is_assembled_from_the_template`: assert the exact string "So you'd
    like to build a new house on lot 012-034, in Village Residential. Is that right?"
  - `test_unsure_is_always_offered_last_and_never_ends`
  - `test_number_out_of_its_turns_range_is_rejected` (`out_of_range`)
  - `test_answer_to_a_turn_that_is_not_current_is_rejected` (`not_current`)
  - `test_back_removes_the_last_answer`
  - `test_back_at_the_start_is_harmless`
  - `test_replay_skips_answers_to_removed_turns`: monkeypatch a `Content` with `full_stories`
    removed.
  - `test_knee_wall_is_asked_only_with_a_roof_floor`
  - `test_steps_count_the_projects_own_steps`: a new house sees "Step 3 of 4 · The building";
    a change of use sees 3 steps.
  - `test_same_actions_give_identical_states`: replay the same 8 actions 50 times and compare
    `repr(state)` (§5 consistency).
  - `test_free_text_is_not_an_action`: `Action` has no "note" kind, and notes never reach
    `replay`.

- [ ] **Step 2: Run them.** Expected: FAIL (`ImportError: cannot import name 'replay'`).

- [ ] **Step 3: Implement `engine.py`.**
  - `replay` folds `apply` over the actions, skipping any action whose turn id is unknown, and
    then computes `current` and `ending`.
  - `ending` comes from `endings.finish` (Task 4). Until Task 4 lands, call it through a module
    attribute so Task 4 can supply it.

- [ ] **Step 4: Run the tests.** Expected: PASS (12 tests).

- [ ] **Step 5: Commit** `portal: the guide engine replays answers into the next turn (guided plan 2, Task 2)`.

### Task 3: Checks: numbers against the lot's standards, the stories count, the nearest version

**Files:**
- Create: `guide/checks.py`.
- Modify: `guide/engine.py`, so a recorded number turn carries its check, and an "outside"
  result inserts a `doesnt_fit` turn.
- Test: `tests/test_guide_checks.py`.

**Interfaces:**
- **Consumes:** `standards_for(district_key)` and `check(standard, value)` (plan 1);
  `district_key_for(code)` (`ruleset.py`); `Turn`, `Lot`, the facts.
- **Produces:**

```python
@dataclass(frozen=True)
class Check:    result: Literal["fits", "outside", "cannot_check"]; value: float | None
                min: float | None; max: float | None; unit: str | None
                room: float | None      # how far inside the limit (fits)
                gap: float | None       # how far over or under (outside)
                reason: str | None      # cannot_check: "not_checkable", "two_districts", "no_district",
                                        #   "lot_disputed", "unknown_input"
                standard_keys: tuple[str, ...]; nearest: tuple[dict, ...]   # {"id","value","label"}

def check_turn(turn: Turn, facts: dict, lot: Lot) -> Check | None   # None: the turn has no standard
def counted_stories(facts: dict) -> int | None                       # None if any input is unknown or unsure
```

- **Rules:**
  - **One standard per district.** For each lot district, find the standard whose `source`,
    `field` and (for the matrix) `building` match the turn's `standard`.
  - **Results across districts:**
    - all districts "within" → `fits`;
    - all "outside" → `outside`;
    - anything else → `cannot_check`: `two_districts` when the districts disagree, and
      `not_checkable` when every district gives `cannot_check` from plan 1's `check`.
  - **No district.** No district codes, or none that `district_key_for` maps, → `no_district`.
  - **A disputed lot.** `lot.confirmed is False` → `lot_disputed` for every district-based check.
  - **`computed: stories`** uses `counted_stories`, following the Code's text:
    - full stories,
    - plus `roof_floors - 1` when there is more than one floor inside the roof (5.7.c.4),
    - plus 1 for the top roof floor when `top_knee_over_3ft` (5.7.c.5),
    - plus 1 when `basement_exposed_5ft` (5.7.c.6).
  - **When the check runs.** The stories check runs on the last of its inputs. It is attached to
    the turn that completes the count and carries `standard_keys` from the Residential column.
  - **`room` and `gap`.** `room = max - value`, or `value - min`, whichever bound is nearer.
    `gap` is the amount past the bound that was missed.
  - **`nearest`:** the single value at the missed bound (`min` or `max`), labeled with
    `wording.nearest`. It is offered only for turns with a `fact` the person sets directly, never
    for `computed` ones. For stories, the doesnt_fit turn offers only `keep_mine` and
    `talk_to_town`, and plan 4 adds roof-shape suggestions.
  - **The `doesnt_fit` turn** (engine-made, kind `choice`, same step):
    - its `ask` comes from `wording.yaml` `doesnt_fit`, with the gap in numbers;
    - its answers are each `nearest`, then `keep_mine`, then `talk_to_town`;
    - choosing a nearest value replaces the fact and re-checks;
    - `keep_mine` and `talk_to_town` add the turn id to `unsure` and continue.

- [ ] **Step 1: Write the failing tests.**
  - `test_the_bound_itself_fits`: D1 side setback 15 → `fits`, room 0.
  - `test_short_of_a_minimum_is_outside_with_the_gap_and_nearest`: D1 side setback 11 → `outside`,
    gap 4, nearest value 15.
  - `test_needs_qualifier_is_cannot_check_never_outside`: D4 Residential stories 3 →
    `cannot_check`, reason `not_checkable`.
  - `test_range_checks_both_sides`: D6 Residential, counted stories 1 → outside (gap 1), 2 →
    fits, 4 → outside.
  - `test_two_districts_that_disagree_cannot_be_checked`: lot `("D1", "D6")`, rear setback 10.
    It fits D6 (5 ft min) but not D1 (15 ft min).
  - `test_disputed_lot_makes_district_checks_uncertain`
  - `test_no_district_cannot_be_checked`: lot `("SD-Civic",)`.
  - `test_counted_stories_follows_5_7_c`, a parametrized table of (full, roof, knee, basement) →
    count:
    - (2, 0, –, no) → 2;
    - (2, 1, no, no) → 2;
    - (2, 1, yes, no) → 3;
    - (2, 2, no, no) → 3;
    - (2, 1, no, yes) → 3;
    - any unsure input → None.
  - `test_the_chairs_three_story_house`: D6, two full stories plus one floor inside the roof
    with low knee walls → the count is 2, and the check says `fits`. Assert also that
    `full_stories` alone (3 entered as "full") is never what is checked.
  - `test_outside_inserts_doesnt_fit_with_nearest_first`
  - `test_keeping_my_number_marks_it_for_the_town_and_continues`

- [ ] **Step 2: Run them.** Expected: FAIL (`ModuleNotFoundError: portal_api.guide.checks`).

- [ ] **Step 3: Implement `checks.py`, and the engine changes.**

- [ ] **Step 4: Run tests 2 and 3.**
  `.venv/bin/pytest tests/test_guide_engine.py tests/test_guide_checks.py -q`. Expected: PASS.

- [ ] **Step 5: Commit** `portal: the guide checks numbers against the lot's standards and offers the nearest fit (guided plan 2, Task 3)`.

### Task 4: The endings

**Files:**
- Create: `guide/endings.py`.
- Test: `tests/test_guide_endings.py`.

**Interfaces:**
- **Consumes:**
  - `run(answers, ruleset, defs)` (`forms/screener.py`) and `load_definitions`;
  - `Opening.screener`;
  - the facts, the `unsure` list, the checks and the `Lot`.
- **Produces:** `finish(content, opening, facts, unsure, checks, lot) -> dict`, called only when
  no turn is left. It returns:

```python
{"kind": "no_permit" | "ready" | "town_judgment" | "not_here",
 "title": str, "body": str,                    # from wording.yaml
 "settled": [...], "unsettled": [...],         # turn ids with their checks, for town_judgment
 "reviews": [...],                             # the screener's outcomes, for ready
 "allowed_uses": [...],                        # not_here: use keys and Code names the district lists
 "notes": [...], "drafts": [...]}              # the screener's notes and drafts_used
```

- **Order:**
  1. **`not_here`:** the chosen use is in the screener's `not_listed` for every lot district.
     `allowed_uses` lists, per district, the use-table uses whose cell has a permit code. The
     `use_not_listed` entry is attached. "Talk to the Town Office" is always in the wording.
  2. **`town_judgment`:** any of these hold:
     - `unsure` is not empty;
     - any check is `cannot_check`;
     - the screener's `town_only` is set;
     - any screener note is `contact_town`;
     - `lot.confirmed is False`.
  3. **`ready`:** the screener returns at least one outcome.
  4. **`no_permit`:** otherwise.
- **Never produced:** `covered` ("you're already covered"). The Town has no permits or
  established uses on record in a form the portal can read (spec §12 item 9, coverage memo §6).
  The docstring says so.
- **Screener inputs:** answers are built from `Opening.screener` plus the facts:
  - `building.gross_floor_area_sf` ← `building.floor_area_sf`;
  - `building.new_dwelling_units` ← `building.dwelling_units`;
  - `use_key` ← `use.use_key`;
  - `property.district_codes` ← the lot's codes.

- [ ] **Step 1: Write the failing tests.**
  - `test_a_house_that_fits_is_ready_with_its_reviews`: use a `Content` copy without the four
    stories turns, a D1 lot, setbacks that fit and floor area 2,000. Expect `ready`, with
    `reviews` naming `small_project_plan`.
  - `test_no_new_house_is_ready_on_todays_ruleset`: with the real content and the empty
    overrides, every district gives `town_judgment` for a new house. Total Stories is a bare
    number (`needs_qualifier`) everywhere except D6, and D6's side setback is `unresolved`. This
    is the coverage memo's question 1 seen from the applicant's side. The test is expected to
    change when the chair answers it.
  - `test_cannot_check_goes_to_the_town_not_to_no`: D4 stories → `town_judgment`, with the
    stories turn in `unsettled`.
  - `test_unsure_goes_to_the_town`
  - `test_use_not_listed_anywhere_on_the_lot_is_not_here_with_what_is_allowed`: pick a use the
    pinned use table leaves blank in D1. Find it in the test from `ruleset.cells`; don't
    hard-code it.
  - `test_use_listed_in_one_of_two_districts_is_not_not_here`
  - `test_covered_is_never_an_ending`: across every scenario above.
  - `test_ending_words_have_no_never_words`

- [ ] **Step 2: Run them.** Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `endings.py`, and wire it into `engine.replay`.**

- [ ] **Step 4: Run Tasks 2–4's tests.** Expected: PASS.

- [ ] **Step 5: Commit** `portal: the guide's endings, from the screener and the checks (guided plan 2, Task 4)`.

### Task 5: The store

**Files:**
- Create: `migrations/versions/0009_guide.py` and `guide/store.py`.
- Test: `tests/test_guide_store.py`.

**Interfaces:**
- **Schema:**
  - `guide_conversation(project_id uuid PK REFERENCES project ON DELETE CASCADE, opening text NOT NULL,
    content_digest text NOT NULL, started_at timestamptz NOT NULL DEFAULT now())`
  - `guide_action(project_id uuid REFERENCES guide_conversation ON DELETE CASCADE, seq int, kind text
    CHECK (kind IN ('answer','back','restart')), turn_id text, value jsonb, shown jsonb NOT NULL,
    content_digest text NOT NULL, at timestamptz NOT NULL DEFAULT now(), by text NOT NULL,
    PRIMARY KEY (project_id, seq))`
    - `shown` is the `Shown` the person answered, exactly as drawn: the record for the packet
      (§7).
  - `guide_note(id uuid PK DEFAULT gen_random_uuid(), project_id uuid REFERENCES guide_conversation
    ON DELETE CASCADE, body text NOT NULL CHECK (length(body) BETWEEN 1 AND 4000),
    at timestamptz NOT NULL DEFAULT now(), by text NOT NULL)`
  - Append-only triggers on `guide_action` and `guide_note`, written like `answer_append_only`
    in `0005`/`0007`: UPDATE and DELETE raise, except for the cascade from `project`. Copy the
    existing trigger's handling.
- **Produces:**

```python
def start(conn, project_id: str, opening: str, digest: str) -> None
def conversation(conn, project_id: str) -> tuple[str, list[Action]] | None   # opening, live actions in seq order
def record(conn, project_id: str, action: Action, shown: dict, digest: str, by: str) -> int  # the new seq
def add_note(conn, project_id: str, body: str, by: str) -> None
def notes(conn, project_id: str) -> list[dict]
```

- `restart` (after "No" on "So you mean…") records the new opening as `value`.
  `conversation()` returns the latest opening and only the actions after the last restart.

- [ ] **Step 1: Write the failing tests** (need the database):
  - `test_actions_come_back_in_order`
  - `test_a_restart_starts_the_actions_over`
  - `test_actions_cannot_be_changed_or_deleted`: a raw `UPDATE guide_action` and a raw `DELETE`
    each raise.
  - `test_deleting_the_project_removes_its_conversation`
  - `test_a_note_longer_than_4000_characters_is_refused`

- [ ] **Step 2: Run them.** `portal/vm.sh sync`, then
  `portal/vm.sh run 'cd portal/api && .venv/bin/pytest tests/test_guide_store.py -q'`.
  Expected: FAIL (no table `guide_conversation`).

- [ ] **Step 3: Write the migration and `store.py`.**

- [ ] **Step 4: Run them, and the schema test.** Run
  `tests/test_guide_store.py tests/test_schema.py -q`. If `test_schema.py` lists the tables,
  add the three new ones there. Expected: PASS.

- [ ] **Step 5: Commit** `portal: the guide's append-only record (guided plan 2, Task 5)`.

### Task 6: The routes and the bridge to the project's form answers

**Files:**
- Create: `routes/guide.py` and `guide/bridge.py`.
- Modify: `main.py`.
- Test: `tests/test_guide_routes.py`.

**Interfaces:**
- **Consumes:**
  - Tasks 1–5;
  - `projects.owned`, `bump`, `snapshot`, `parts`, `save_answers` and `EDITABLE`;
  - `routes/projects.py`'s `Loaded` and `_refuse_stale`, and `check_value`
    (`forms/answers.py`);
  - `append_event`;
  - `auth.require`;
  - `transaction`.
- **Routes** (all applicant-owned; another person's project is 404):

| Method and path | Body | Result |
|---|---|---|
| `POST /api/projects/{id}/guide` | `{opening, base_revision}` | 201 state; 409 `already_started` unless the conversation's current turn is the opening picker (then it records `restart`); 422 `wrong_project` if the opening's `part` isn't one of the project's parts |
| `GET /api/projects/{id}/guide` | — | state, or 404 `not_started` |
| `POST /api/projects/{id}/guide/answers` | `{turn_id, value, base_revision}` | state; 422 with `AnswerRejected.reason` |
| `POST /api/projects/{id}/guide/back` | `{base_revision}` | state |
| `POST /api/projects/{id}/guide/check` | `{turn_id, value}` | the `Check` for a value not yet given (live room-left, §4.4); saves nothing and needs no revision |
| `POST /api/projects/{id}/guide/notes` | `{body, base_revision}` | 201; the text is stored and returned in state's `notes`, and nothing reads it |

- **State JSON:**
  `{revision, opening, current, history: [{shown, value}], ending, step, unsure, notes,
  drafts}`.
- **Every change:**
  - checks the owner, then `status in EDITABLE` (else 409 `locked`);
  - replays and applies (422 on rejection);
  - calls `bump` (None → `_refuse_stale`), records the action with its `shown`, and runs the
    bridge;
  - appends an event: `guide.started`, `guide.answered`, `guide.back`, `guide.restarted` or
    `guide.note`, with payload `{project_id, turn_id}` and never the note text.
- **Draft gate:** a response whose state `drafts` (or the ending's) is non-empty is `503
  guide_not_approved` unless `settings.allow_draft_rules`. It is checked after the replay and
  before any write.
- **The bridge:** `bridge.sync(conn, loaded, state, by) -> None`.
  - **What it fills:** for each live answer to a turn with `answer_field`, it validates the value
    with `check_value` against that form field and saves it with `pj.save_answers`. The part id
    is the first project part whose kind is the opening's `part`. Stories saves
    `counted_stories`, not the full-story count.
  - **What it skips:** it writes only values that changed, and an unsure answer writes nothing.
  - **Undoing an answer:** a value that a Back removed is written as unknown, using the form's
    `allow_unknown` sentinel, so `needs` and the dashboard match the conversation.

- [ ] **Step 1: Write the failing tests.** Use `tests/conftest.py`'s signed-in client and a
  project made with `POST /api/projects` (`parts: ["building"]`). Follow `test_projects.py`'s
  fixtures for the parcel and the snapshot.
  - `test_start_and_first_turn_is_the_lot`
  - `test_someone_elses_project_is_404`
  - `test_wrong_opening_for_the_project_is_422`
  - `test_answer_advances_and_bumps_the_revision`
  - `test_stale_revision_is_refused`
  - `test_locked_project_refuses_answers`
  - `test_answer_rejects_non_numbers`: `"three"`, `true`, `null` and `1e400` each give 422
    `bad_value`.
  - `test_back_is_recorded_not_deleted`
  - `test_check_saves_nothing`
  - `test_note_is_kept_and_never_changes_the_turn`: the state before and after a note is equal
    except `notes` and `revision`.
  - `test_the_bridge_fills_the_form_answers`: after the stories and setback answers, `GET
    /api/projects/{id}` shows `stories` = the counted stories and `setback_front` = the value
    given.
  - `test_back_clears_the_bridged_answer`
  - `test_drafts_are_refused_without_the_dev_setting`: build the app with
    `allow_draft_rules=False` → 503 `guide_not_approved`.
  - `test_events_never_carry_note_text`
  - `test_guide_bounds_fit_the_form_fields`: for every turn with `answer_field`, the turn's
    `min`/`max` lie within the form field's. This keeps the bridge from failing on a value the
    guide accepted.

- [ ] **Step 2: Run them on the VM.** Expected: FAIL (404 on `/guide`).

- [ ] **Step 3: Implement `bridge.py` and `routes/guide.py`, and include the router in
  `main.py`.**

- [ ] **Step 4: Run the whole API suite on the VM.**
  `portal/vm.sh run 'cd portal/api && .venv/bin/pytest'`. Expected: exit 0. Read the exit code;
  addopts already has `-q`.

- [ ] **Step 5: Commit** `portal: the guide's routes, and its numbers carried into the project's answers (guided plan 2, Task 6)`.

### Task 7: Docs, and a run-through on the VM

**Files:**
- Modify: `portal/README.md` and `OPEN_ITEMS.md`.

- [ ] **Step 1: Update `portal/README.md`.** Add a short "Guide engine" section covering:
  - where the content lives;
  - that all of it is draft;
  - the routes;
  - that free text is kept and not read (decision 14);
  - how to run the guide tests on the VM.

- [ ] **Step 2: Update `OPEN_ITEMS.md`.** Under the guided builder, record:
  - plan 1 merged as PR #22 on 2026-11-01;
  - plan 2's branch and plan file;
  - for the chair:
    - the §10.3 word list in Global Constraints, to approve;
    - the pairing of a new house with the Residential column and primary-building placement;
    - the first-draft wording in `portal_api/guide/definitions/`.

- [ ] **Step 3: Run the guide on the VM by hand.** Start the API with drafts allowed (README
  line 27), sign in through Mailpit and create a building project. Then drive the guide with
  `curl` through to an ending:
  - a new house on a D4 lot gives `town_judgment` at stories, with stories in `unsettled`;
  - a change of use to `residence` on a lot whose district lists it gives `ready`. Pick the lot
    from the use table, not from memory. Paste both final states, trimmed, into the PR description.

- [ ] **Step 4: Run the web unit tests and the journeys** (`npm test`, then the Playwright
  journeys as in README line 226). This shows the HeroUI app is unchanged. Expected: all pass.

- [ ] **Step 5: Commit** `portal: guide engine docs, and open items for the chair (guided plan 2, Task 7)`.
