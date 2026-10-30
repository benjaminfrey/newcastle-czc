# Guided builder, plan 1 of 6: Foundations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay the two foundations every later guided-builder plan stands on: the adopted Code's
district standards as values a program can check (with an audit of what is and isn't checkable),
and a Material UI shell with a swappable theme, showing the chosen mockup screen on the VM.

**Architecture:**
- **Half A (API, Python)** adds a read-only `standards` layer over the pinned, hash-checked ruleset.
  It turns every district dimension and every Permitted Buildings table cell into a `Standard`
  with an explicit status. It never infers a minimum, a maximum or a unit the Code doesn't state.
  It then generates a coverage memo that answers the spec's fact questions (§12 items 7–9) and
  lists the questions only the chair can answer.
- **Half B (web, React)** installs MUI next to the existing HeroUI app, inside a scoped subtree,
  builds the theme from named tokens, and makes the mockup's pieces real as components on a
  preview route.
- Half A and Half B share no files and can be built in parallel.

**Tech Stack:**
- API: Python 3.14, FastAPI app package `portal_api`, pytest.
- Web: React 19.3, TypeScript 5.9, Vite 8, Vitest 5, Testing Library, Playwright 1.64 with axe;
  new packages `@mui/material` 9.5.0, `@emotion/react` 11.14.0, `@emotion/styled` 11.14.1,
  `@fontsource/roboto` 5.3.0.

**Spec:** `specs/2026-10-30-applicant-portal-guided-builder.md` (approved by the chair 2026-10-30).
This plan implements §11's "before anything else, the rulesets need work", §12 items 7–9 (the
audit), and §10 (the look) as far as a shell and components. Later plans: 2 conversation engine,
3 conversation screens, 4 lot drawing, 5 pictures, 6 applicant packet view.

## Global Constraints

- **Never guess a legal value** (CLAUDE.md rule 6). This covers:
  - a number the Code states without "min" or "max";
  - a number with no unit;
  - a footnote whose text is missing.

  Each of these yields a non-checkable status and a question for the chair. None gets a default.
  This follows `build/permit-review/DECISIONS-NEEDED.md`'s rule: "If the Code does not say whether
  a number is a minimum or a maximum, do not pick one."
- **A standard that can't be checked never produces "outside".** `check()` returns
  `"cannot_check"` (spec §4.5: an uncertain "no" is never shown as a result).
- **The vendored ruleset stays untouched.**
  - `portal_api/rulesets/adopted-v1.0/` is hash-checked, and `tests/test_ruleset.py` requires
    exactly 6 files that are byte-identical to `build/permit-review/rulesets/adopted-v1.0/`.
  - Overrides and new data live outside that folder.
- **Overrides carry provenance:** `decided_by`, `decided_at` and `basis`, all required. The
  committed override file starts empty; only the chair's recorded answers ever fill it.
- **The HeroUI app keeps working unchanged until the public launch** (spec decision 13). MUI
  lives only under the new `src/guide/` subtree and the preview route. Every existing Vitest
  test and Playwright journey must still pass.
- **Material UI's global baseline must not leak into HeroUI pages.** Use `ScopedCssBaseline`
  around the guide subtree, never `CssBaseline`.
- **Every color, font, corner radius and spacing value in `src/guide/` comes from
  `src/guide/theme/tokens.ts`.** Behavior is not themeable (spec §10.2).
- **Pin package versions exactly** (no `^` or `~`), matching `package.json`'s existing style.
- **Copy on the preview** is the mockup's draft wording. The preview shows "Draft wording, not
  approved" in its app bar. D4's two-story limit there is sketch data, labeled as such.
- **Accessibility:** WCAG 2.1 AA, checked by axe in Playwright at desktop (1280×800) and phone
  (Pixel 7). Targets are at least 48 px, Material's own minimum.
- **Python dataclasses and module style** follow `portal_api/ruleset.py`: frozen dataclasses,
  module docstrings in plain words, `functools.cache` for loaded data.
- **Commits:**
  - Stage files by name, never `git add -A` or `git add .`.
  - End each message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - Work on branch `portal-guided-1-foundations`, cut from `main` (8f1783a or later).
  - Commit per task; push only on the chair's OK.

## Review Focus

1. **A bare Permitted Buildings number such as "60 ft" or "2".** A reasonable person expects no
   check at all, never an assumed maximum. Pinned in Task 2,
   `test_bare_matrix_number_cannot_be_checked`.
2. **A floor area written without a unit** ("12,000" beside "12,000 sf" in other districts).
   Expect status `needs_unit` and `cannot_check`, never an assumed "sf". Pinned in Task 1,
   `test_unitless_area_needs_a_unit`.
3. **A district with no Permitted Buildings table** (SD-Conservation, SD-Campus, SD-Marine).
   Expect the dimensions only, and the Board's question surfaced in the audit, not an empty
   "nothing applies". Pinned in Task 2, `test_districts_without_a_buildings_table`, and Task 3,
   `test_audit_lists_districts_without_a_buildings_table`.
4. **A malformed or provenance-free override entry.** Expect a load-time error, never a silently
   applied qualifier. Pinned in Task 2, `test_override_without_provenance_is_refused`.
5. **A HeroUI page opened after visiting the guide preview** (shared document, two style
   systems). Expect the HeroUI page unchanged: no MUI baseline, fonts or colors leaking. Pinned in
   Task 6's Playwright step, `existing pages keep their look after the guide preview`.

---

## Half A — the rules

### Task 1: Parse a Permitted Buildings cell without guessing

**Files:**
- Create: `portal/api/portal_api/standards.py`
- Test: `portal/api/tests/test_standards.py`

**Interfaces:**
- Produces:
  ```python
  Status = Literal["checkable", "needs_qualifier", "needs_unit", "not_established",
                   "unresolved", "not_a_number"]

  @dataclass(frozen=True)
  class Parsed:
      status: Status
      min: float | None
      max: float | None
      unit: str | None        # "ft" | "sf" | "stories" | "units" | None
      note: str | None        # why it isn't checkable, in plain words

  def parse_matrix_cell(row_label: str, raw: str) -> Parsed
  ```
- Row labels and the unit each implies only when the cell gives none, because the label itself
  names a count:
  - `"Total Stories"` → `"stories"`
  - `"Number of Units"` → `"units"`

  Length rows (`Building Width`, `Building Depth`, `First Floor Height`, `Upper Floor Height`)
  and `Building Floor Area` take their unit only from the cell.
  `"Permitting Authority"` → `not_a_number`, with the raw text kept.

- [ ] **Step 1: Write the failing tests.** These use real cell strings from
  `districts.json`'s `building_matrix` rows (the full set is listed in the Task 3 audit).

```python
import pytest
from portal_api.standards import parse_matrix_cell

@pytest.mark.parametrize("label,raw,status,lo,hi,unit", [
    ("Total Stories", "1 max.", "checkable", None, 1, "stories"),
    ("Total Stories", "2 min. - 3 max.", "checkable", 2, 3, "stories"),
    ("Total Stories", "2", "needs_qualifier", None, None, "stories"),
    ("Building Width", "60 ft", "needs_qualifier", None, None, "ft"),
    ("Building Floor Area", "8,000 sf", "needs_qualifier", None, None, "sf"),
    ("Number of Units", "-", "not_established", None, None, None),
    ("Permitting Authority", "Planning Board", "not_a_number", None, None, None),
])
def test_matrix_cells(label, raw, status, lo, hi, unit):
    p = parse_matrix_cell(label, raw)
    assert (p.status, p.min, p.max, p.unit) == (status, lo, hi, unit)

def test_unitless_area_needs_a_unit():
    p = parse_matrix_cell("Building Floor Area", "12,000")
    assert p.status == "needs_unit" and p.min is None and p.max is None
    assert "unit" in p.note

def test_a_cell_it_cannot_read_is_reported_not_dropped():
    p = parse_matrix_cell("Building Width", "about sixty")
    assert p.status == "unresolved" and p.note
```

- [ ] **Step 2: Run them to see them fail.**
  Run: `portal/vm.sh run 'cd portal/api && .venv/bin/pytest tests/test_standards.py -q' </dev/null`
  Expected: FAIL, with `ModuleNotFoundError: portal_api.standards`.

- [ ] **Step 3: Implement `parse_matrix_cell`** in `standards.py`.
  - Use a small regex over the forms the tests show: a number with optional commas, an optional
    unit (`ft` | `sf`), and an optional `min.` / `max.` qualifier, or a `<n> min. - <m> max.`
    range.
  - `-` → `not_established`.
  - Anything else → `unresolved`, with a note.
  - A qualifier is read only from the text, never from the label.

- [ ] **Step 4: Run the tests to see them pass.** Same command. Expected: PASS.

- [ ] **Step 5: Commit**
  `git add portal/api/portal_api/standards.py portal/api/tests/test_standards.py`
  Message: `portal: read a Permitted Buildings cell without guessing its limit (guided plan 1, Task 1)`

### Task 2: Every district's standards, overrides and `check()`

**Files:**
- Modify: `portal/api/portal_api/standards.py`
- Create: `portal/api/portal_api/standards_overrides.json`, containing `{"overrides": []}`
- Test: `portal/api/tests/test_standards.py`

**Interfaces:**
- Consumes: `load_ruleset()` and `Ruleset.districts` from `portal_api/ruleset.py`, and
  `parse_matrix_cell` from Task 1.
- Produces:
  ```python
  @dataclass(frozen=True)
  class Standard:
      key: str                 # "d4/dimension/primary_building_placement.side_setback"
                               # "d4/building/Residential/total_stories"
      district_key: str
      source: Literal["dimension", "building_matrix"]
      building: str | None     # the Permitted Buildings column, e.g. "Residential"
      field: str               # dimension field_key, or snake_case of the matrix row label
      label: str
      raw: str
      status: Status
      min: float | None
      max: float | None
      unit: str | None
      provenance: Literal["literal", "override"] | None
      citation: dict           # the ruleset's citation dict, plus {"building": ...} for matrix cells
      note: str | None

  def load_standards(root: Path | None = None) -> tuple[Standard, ...]   # cached, like _load
  def standards_for(district_key: str) -> tuple[Standard, ...]
  def check(standard: Standard, value: float) -> Literal["within", "outside", "cannot_check"]
  def missing_buildings_table(district_key: str) -> str | None   # the ruleset's board_question
  class OverrideError(Exception)
  ```
- **Dimensions** (`district["dimensions"]`) are already parsed.
  - `applicability == "not_established"` → `not_established`.
  - `unresolved: true` → `unresolved`, with the ruleset's own note.
  - Otherwise `checkable`, with min/max taken from `constraints` and provenance from each
    constraint's `source` (`literal` or `override`).
- **Matrix cells** come from Task 1, then the overrides are applied.
- **Override entry schema:** `{district_key: str | "*", building: str | "*", field: str,
  qualifier: "min" | "max", unit?: "ft" | "sf", decided_by, decided_at, basis}`.
  - An override may turn `needs_qualifier` or `needs_unit` into `checkable`. The value stays the
    Code's number.
  - Any entry missing `decided_by`, `decided_at` or `basis`, or naming a field that doesn't
    exist, raises `OverrideError` at load.

- [ ] **Step 1: Write the failing tests.**

```python
from portal_api.standards import (OverrideError, check, load_standards,
                                  missing_buildings_table, standards_for)

def test_every_district_has_standards():
    keys = {s.district_key for s in load_standards()}
    assert len(keys) == 13

def test_a_checkable_setback():
    s = next(s for s in standards_for("d1") if s.field == "primary_building_placement.side_setback")
    assert (s.status, s.min, s.unit, s.provenance) == ("checkable", 15.0, "ft", "literal")
    assert check(s, 15) == "within" and check(s, 14.5) == "outside"

def test_bare_matrix_number_cannot_be_checked():
    s = next(s for s in standards_for("d4")
             if s.building == "Residential" and s.field == "total_stories")
    assert s.status == "needs_qualifier"
    assert check(s, 3) == "cannot_check" and check(s, 99) == "cannot_check"

def test_unresolved_footnote_cannot_be_checked():
    s = next(s for s in standards_for("d6") if s.field == "primary_building_placement.side_setback")
    assert s.status == "unresolved" and check(s, 3) == "cannot_check"

def test_districts_without_a_buildings_table():
    for key in ("sd-conserve", "sd-campus", "sd-marine"):
        assert all(s.source == "dimension" for s in standards_for(key))
        assert "What dimensional standards" in missing_buildings_table(key)
    assert missing_buildings_table("d4") is None

def test_override_turns_a_bare_number_checkable(tmp_path):
    ...  # write an override {district_key:"d4", building:"Residential", field:"total_stories",
         # qualifier:"max", decided_by:"Test", decided_at:"2026-10-30", basis:"test"} to tmp_path;
         # load_standards(root=tmp_path) → that cell is checkable, max 2, provenance "override"

def test_override_without_provenance_is_refused(tmp_path):
    ...  # same entry without "basis" → pytest.raises(OverrideError, match="basis")

def test_committed_overrides_are_empty():
    import json, portal_api.standards as m
    assert json.loads((Path(m.__file__).parent / "standards_overrides.json").read_text()) == {"overrides": []}
```

  The 13 district keys are `d1`–`d6`, `sd-historic`, `sd-conserve`, `sd-hwy`, `sd-rhwy`,
  `sd-campus`, `sd-marine`, `sd-fab`.

- [ ] **Step 2: Run them to see them fail.** Same command as Task 1. Expected: FAIL, with
  `ImportError` on `load_standards`.

- [ ] **Step 3: Implement** `load_standards`, `standards_for`, `check`,
  `missing_buildings_table` and the override loader.
  - `root` points at a folder containing `standards_overrides.json`. The default is the
    package folder.
  - `check` returns `"cannot_check"` for every status other than `checkable`. A checkable
    standard with both bounds checks `min <= value <= max`.

- [ ] **Step 4: Run the tests to see them pass**, then run the whole API suite.
  Run: `portal/vm.sh run 'cd portal/api && .venv/bin/pytest -q' </dev/null`
  Expected: all pass, including `test_ruleset.py`, which proves the vendored folder is
  untouched.

- [ ] **Step 5: Commit**
  `git add portal/api/portal_api/standards.py portal/api/portal_api/standards_overrides.json portal/api/tests/test_standards.py`
  Message: `portal: the Code's district standards as checkable values, with overrides that need provenance (guided plan 1, Task 2)`

### Task 3: The coverage audit memo

**Files:**
- Create: `portal/api/portal_api/standards_audit.py`
- Modify: `portal/api/portal_api/standards.py`, adding a `__main__`-style entry. Alternatively
  create `portal/api/portal_api/standards_cli.py` and follow `forms/__main__.py`'s argparse
  pattern.
- Create: `memos/2026-10-30-guided-builder-rules-coverage.md` (generated, then committed)
- Test: `portal/api/tests/test_standards_audit.py`

**Interfaces:**
- Consumes: `load_standards`, `missing_buildings_table` (Task 2), and `load_ruleset()._nodes`
  (the article nodes).
- Produces:
  - `render_audit(today: str) -> str`, the memo's markdown;
  - the CLI command `python -m portal_api.standards audit --out <path>`.

The memo's sections, in this order. Every count and list is computed, not typed.

1. **Summary.** Counts of standards by status, across all 13 districts.
2. **District by district.** A table per district with the columns
   `| Building | Field | Raw | Status | Bounds |`. Field is the row label for matrix cells, and
   Bounds is blank unless the standard is checkable.
3. **Questions only the chair can answer.**
   - Group the `needs_qualifier` cells **by matrix row label**, one question per row: "Is
     Building Width in the Permitted Buildings tables a maximum?" List the districts and cells
     each question covers. Quote `Ruleset.cite("5.3.c.4")`, which gives what Width, Depth and
     Total Square Feet apply to, including that habitable space in the roof pitch isn't counted.
   - One question per `needs_unit` cell.
   - One per `unresolved` item, carrying the ruleset's note.
   - One per district without a Permitted Buildings table, carrying the ruleset's
     `board_question`.
4. **What the Code says in prose, not yet checkable.** For Articles 1 and 3–8, a list of
   sections (`article`, `section`, `section_name`, node count), each marked "prose — needs a
   rule or a library entry". This is the work list later plans size from.
5. **Shoreland (spec §12 item 8).**
   - Every article node whose text mentions "shoreland", with its citation and quoted text.
   - Whether any GIS layer in `portal_api/gis/sources.py` maps a shoreland zone. As of this
     plan none does; the memo says so from the code, not from memory.
   - No interpretation.
6. **Existing permits and established uses on record (spec §12 item 9).** Whether any portal
   data source carries them. As of this plan none does; the memo says so and lists what would
   be needed as a question for the chair.

- [ ] **Step 1: Write the failing tests.**

```python
from portal_api.standards_audit import render_audit

def test_audit_groups_bare_numbers_into_one_question_per_row():
    md = render_audit("2026-10-30")
    assert md.count("Is Building Width in the Permitted Buildings tables a maximum?") == 1
    assert "Total Stories" in md

def test_audit_lists_districts_without_a_buildings_table():
    md = render_audit("2026-10-30")
    for name in ("SD - Conservation", "SD - Campus", "SD - Marine"):
        assert name in md

def test_audit_quotes_every_shoreland_mention():
    md = render_audit("2026-10-30")
    assert md.count("shoreland") + md.count("Shoreland") >= 8   # 8 nodes mention it today

def test_audit_shows_no_bound_for_a_bare_number():
    md = render_audit("2026-10-30")
    row = next(l for l in md.splitlines() if "| Residential | Total Stories | 2 |" in l)
    assert "needs_qualifier" in row and "max" not in row.split("| 2 |")[1]
```

- [ ] **Step 2: Run them to see them fail.**
  Run: `portal/vm.sh run 'cd portal/api && .venv/bin/pytest tests/test_standards_audit.py -q' </dev/null`
  Expected: FAIL, with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `render_audit`** and the CLI. Write it in the memos' plain style (see
  `memos/2026-10-21-application-forms-for-approval.md`): short sentences, the chair as reader.

- [ ] **Step 4: Run the tests to see them pass, then generate the memo.**
  Run: `portal/vm.sh run 'cd portal/api && .venv/bin/python -m portal_api.standards audit --out /tmp/rules-coverage.md' </dev/null`
  Then copy it back into `memos/2026-10-30-guided-builder-rules-coverage.md`, the way the forms
  sheet is fetched today.
  Expected: the file opens with the summary counts. 148 dimension standards appear (109
  established, 39 not established, 2 of them unresolved) plus the matrix cells.

- [ ] **Step 5: Commit**
  `git add portal/api/portal_api/standards_audit.py portal/api/portal_api/standards.py portal/api/tests/test_standards_audit.py memos/2026-10-30-guided-builder-rules-coverage.md`
  Message: `portal: the rules coverage audit for the guided builder (guided plan 1, Task 3)`

---

## Half B — the Material shell

### Task 4: MUI installed, the theme built from tokens

**Files:**
- Modify: `portal/web/package.json` and `portal/web/package-lock.json`
- Create: `portal/web/src/guide/theme/tokens.ts`, `portal/web/src/guide/theme/theme.ts`,
  `portal/web/src/guide/theme/GuideTheme.tsx`
- Test: `portal/web/src/guide/theme/theme.test.tsx`

**Interfaces:**
- Produces:
  ```ts
  export type GuideTokens = {
    color: { light: Palette; dark: Palette };   // Palette: primary, onPrimary, primaryContainer,
                                                // onPrimaryContainer, surface, surfaceContainer,
                                                // onSurface, onSurfaceVariant, outline,
                                                // outlineVariant, error, success, warning
    font: { body: string; display: string };
    radius: { small: number; medium: number; large: number; full: number };
    spacing: number;                            // MUI spacing unit, px
    density: "comfortable" | "compact";
  };
  export const newcastleTokens: GuideTokens;
  export function createGuideTheme(tokens?: GuideTokens): Theme;   // MUI Theme, light + dark schemes
  export function GuideTheme(props: { tokens?: GuideTokens; children: ReactNode }): JSX.Element;
  // GuideTheme = ThemeProvider + ScopedCssBaseline, scoped to its children only
  ```
- Values:
  - The primary color is the Town seal teal already in `src/theme/tokens.ts` (`--app-accent`
    `#0C727E`). Derive the Material containers from it.
  - Radius: small 8, medium 12, large 16, full 999. Spacing 8.
  - Fonts: Roboto, self-hosted via `@fontsource/roboto`, with a system fallback stack.
- Dark mode follows the device. Reuse `followDeviceScheme()` from `src/theme/colorScheme.ts`,
  which sets `data-theme` on `<html>`. Configure MUI's CSS-variables theme so its color-scheme
  selector reads that same attribute.

- [ ] **Step 1: Install the packages at exact versions**, on the VM so the lockfile matches CI.
  Run: `portal/vm.sh run 'cd portal/web && npm install --save-exact @mui/material@9.5.0 @emotion/react@11.14.0 @emotion/styled@11.14.1 @fontsource/roboto@5.3.0' </dev/null`
  Expected: the four packages added without `^`. Run `npm test`: the existing suite still
  passes.

- [ ] **Step 2: Write the failing tests.**

```ts
test("the theme takes its primary color from the tokens", () => {
  const t = createGuideTheme();
  expect(t.colorSchemes.light.palette.primary.main).toBe(newcastleTokens.color.light.primary);
  expect(t.colorSchemes.dark.palette.primary.main).toBe(newcastleTokens.color.dark.primary);
});
test("swapping tokens changes the look without touching components", () => {
  const warm = { ...newcastleTokens, color: { ...newcastleTokens.color,
    light: { ...newcastleTokens.color.light, primary: "#8A4B00" } } };
  expect(createGuideTheme(warm).colorSchemes.light.palette.primary.main).toBe("#8A4B00");
});
test("radius and spacing come from the tokens", () => {
  const t = createGuideTheme();
  expect(t.shape.borderRadius).toBe(newcastleTokens.radius.medium);
  expect(t.spacing(2)).toBe("16px");
});
test("GuideTheme scopes the baseline to its children", () => {
  render(<><p data-testid="outside">x</p><GuideTheme><p>y</p></GuideTheme></>);
  expect(document.querySelector(".MuiScopedCssBaseline-root")).not.toBeNull();
  expect(screen.getByTestId("outside").closest(".MuiScopedCssBaseline-root")).toBeNull();
});
```

- [ ] **Step 3: Run them to see them fail.**
  Run: `portal/vm.sh run 'cd portal/web && npx vitest run src/guide/theme' </dev/null`
  Expected: FAIL, with the module not found.

- [ ] **Step 4: Implement** `tokens.ts`, `theme.ts` and `GuideTheme.tsx`.
  - Component defaults that make MUI look like the mockup belong in the theme's `components`
    overrides, not in individual components:
    - pill-shaped buttons;
    - 8 px chips;
    - 12 px cards with tonal surfaces;
    - a 4 px rounded LinearProgress.
  - While doing this, record in a comment at the top of `theme.ts` how far MUI 9.5's components
    follow Material 3 (spec §10.1, "builder to confirm"), and what the theme overrides to close
    the gap.

- [ ] **Step 5: Run the tests to see them pass**, then run the whole web suite and the build.
  Run: `portal/vm.sh run 'cd portal/web && npm test && npm run build' </dev/null`
  Expected: all pass, and the build succeeds.

- [ ] **Step 6: Commit**
  `git add portal/web/package.json portal/web/package-lock.json portal/web/src/guide/theme/tokens.ts portal/web/src/guide/theme/theme.ts portal/web/src/guide/theme/GuideTheme.tsx portal/web/src/guide/theme/theme.test.tsx`
  Message: `portal: Material UI with a theme built from named tokens, scoped to the guide (guided plan 1, Task 4)`

### Task 5: The mockup's pieces as components

**Files:**
- Create in `portal/web/src/guide/components/`: `Bubble.tsx`, `AnswerList.tsx`,
  `SuggestionChips.tsx`, `WhyCard.tsx`, `ReplyBox.tsx`, `StepBar.tsx`, each with a `.test.tsx`
  beside it.

**Interfaces:**
- Consumes: `GuideTheme` (Task 4). Tests render inside it.
- Produces:
  ```ts
  Bubble(props: { from: "you" | "app"; children: ReactNode })
  AnswerList(props: { question: string; answers: { id: string; label: string; hint?: string }[];
                      onAnswer: (id: string) => void })
  SuggestionChips(props: { chips: { id: string; label: string; icon?: ReactNode }[];
                           onChip: (id: string) => void })
  WhyCard(props: { overline: string; picture?: ReactNode; pictureAlt?: string; answer: string;
                   detail: string; codeHref?: string; codeLabel?: string })  // codeLabel default "Read it in the Code"
  ReplyBox(props: { placeholder: string; onSend: (text: string) => void })
  StepBar(props: { step: number; of: number; label: string })   // "Step 3 of 6 · The building"
  ```
- Behavior the tests pin:
  - **AnswerList** is a radio group named by `question`. Choosing an answer by click or keyboard
    (arrows, then Enter or Space) calls `onAnswer` once. Each row is at least 48 px tall.
  - **SuggestionChips** are buttons.
  - **WhyCard:**
    - It is an `article`.
    - If `picture` is given, it carries `role="img"` and an accessible name from `pictureAlt`.
      `pictureAlt` is required whenever `picture` is set; a picture without it is a type
      error.
    - The Code link appears only when `codeHref` is set.
  - **ReplyBox:** Send is disabled while the box is empty or only whitespace, and Enter sends.
  - **StepBar:** a `progressbar` with `aria-valuenow` = step and `aria-valuemax` = of, plus
    visible text in the form "Step 3 of 6 · The building".
  - **Bubble:** the `from` prop is conveyed to screen readers, as "You said" or "Newcastle".

- [ ] **Step 1: Write the failing tests**, one file per component, covering the behavior above.
  Example for the one with the most rules:

```tsx
test("AnswerList answers once, by click or keyboard", async () => {
  const onAnswer = vi.fn();
  render(<GuideTheme><AnswerList question="Is your third floor inside the roof?"
    answers={[{ id: "yes", label: "Yes, inside the roof", hint: "like a finished attic" },
              { id: "no", label: "No, it has full walls" },
              { id: "unsure", label: "I'm not sure yet" }]} onAnswer={onAnswer} /></GuideTheme>);
  const group = screen.getByRole("radiogroup", { name: "Is your third floor inside the roof?" });
  await userEvent.click(within(group).getByRole("radio", { name: /Yes, inside the roof/ }));
  expect(onAnswer).toHaveBeenCalledOnce();
  expect(onAnswer).toHaveBeenCalledWith("yes");
});
```

- [ ] **Step 2: Run them to see them fail.**
  Run: `portal/vm.sh run 'cd portal/web && npx vitest run src/guide/components' </dev/null`
  Expected: FAIL, with the modules not found.

- [ ] **Step 3: Implement** the components with MUI primitives:
  - `List` and `ListItemButton` with `Radio` for the answers;
  - `Chip` for the suggestions;
  - `Card` for the "why" card;
  - `TextField` plus `IconButton` for the reply box;
  - `LinearProgress` for the step bar.

  Styling comes only through the theme (Task 4); no literal colors.

- [ ] **Step 4: Run the tests to see them pass**, then the whole web suite. Command as in Task 4
  Step 5. Expected: all pass.

- [ ] **Step 5: Commit** the six components and their tests, by name.
  Message: `portal: the guided builder's conversation pieces in Material (guided plan 1, Task 5)`

### Task 6: The shell and the preview the chair can open

**Files:**
- Create: `portal/web/src/guide/GuideShell.tsx`, `portal/web/src/guide/GuidePreview.tsx`,
  `portal/web/src/guide/GuideShell.test.tsx`, `portal/web/e2e/guide-preview.spec.ts`
- Modify:
  - `portal/web/src/App.tsx`: add the route when the preview flag is on.
  - The web image's build: `portal/deploy/` Dockerfile and `compose.lan.yml`, to pass
    `VITE_GUIDE_PREVIEW=1` on the LAN build only.
  - `portal/README.md`: one paragraph on the preview and the flag.
  - `OPEN_ITEMS.md`: point the portal bullet at this plan and the coverage memo.

**Interfaces:**
- Consumes: `GuideTheme` (Task 4) and all of Task 5's components.
- Produces:
  ```ts
  GuideShell(props: { title: string; back?: { href: string; label: string }; helpHref?: string;
                      draft?: boolean; step?: { step: number; of: number; label: string };
                      aside?: ReactNode; children: ReactNode })
  // ≥1024px: two columns, conversation (main) left, aside right (aria-label "Your project").
  // <1024px: one column, aside below the conversation. Uses the existing useWideLayout() hook.
  // draft=true shows "Draft wording, not approved" in the app bar.
  ```
- **The route:** `/guide/preview`, inside `RequireSignIn`, registered only when
  `import.meta.env.VITE_GUIDE_PREVIEW === "1"`. Without the flag the path falls through to
  Home, as unknown paths do today.
- **`GuidePreview`** renders the chosen mockup screen
  (`.superpowers/brainstorm/71861-1793378240/content/material-vs-apple.html`, left phone) with
  its exact draft content:
  - the person's words;
  - the app's reply;
  - the "why" card, with an inline-SVG attic diagram and `pictureAlt` "A house with two full
    stories and a floor inside the roof; the floor inside the roof is not counted";
  - the three answers, two chips and the reply box.

  Answering shows the chosen answer as a "you" bubble and nothing more. The preview has no
  server calls. Its aside, on wide screens, shows a placeholder "Your project" summary card.
  The chips and the Code link are inert in the preview, so the Code link is rendered without
  `codeHref`.

- [ ] **Step 1: Write the failing tests.**
  - **Vitest (`GuideShell.test.tsx`):**
    - the app bar shows the title and the draft label;
    - `StepBar` is present when `step` is given;
    - the aside is labelled "Your project".
  - **Playwright (`guide-preview.spec.ts`), at the desktop and phone projects:**
    - sign in with the existing `e2e/helpers.ts` sign-in;
    - open `/guide/preview` and pass axe with no violations;
    - answer "Yes, inside the roof" and see it as a "You said" bubble;
    - test `existing pages keep their look after the guide preview`: visit `/guide/preview`,
      then `/`. Assert that Home's computed `body` font-family and background match a fresh
      load of `/`, and that no `.MuiScopedCssBaseline-root` exists on Home.
- [ ] **Step 2: Run the Vitest test to see it fail.**
  Run: `portal/vm.sh run 'cd portal/web && npx vitest run src/guide' </dev/null`
  Expected: FAIL, with `GuideShell` not found.
- [ ] **Step 3: Implement** `GuideShell`, `GuidePreview`, the route, the flag and the LAN build
  argument.
- [ ] **Step 4: Run all tests.**
  - Run the web suite and build as in Task 4 Step 5.
  - Rebuild the LAN copy: `RSYNC_RSH="ssh -o ConnectTimeout=20" portal/vm.sh lan </dev/null`.
  - Run every journey against it, the new spec included: use the LAN journey command in
    `portal/README.md`, with `PORTAL_E2E_URL=https://192.168.1.6`, and
    `PORTAL_E2E_MAILPIT_AUTH` read from `portal/deploy/.env` on the VM, never printed.

  Expected: Vitest passes, the build passes, and the journeys pass at desktop and phone: the
  six existing ones plus the new ones.
- [ ] **Step 5: Commit** the files above, by name.
  Message: `portal: the guided builder's Material shell and a preview on the LAN copy (guided plan 1, Task 6)`

---

## Done when

- The API suite passes. `memos/2026-10-30-guided-builder-rules-coverage.md` exists, generated
  by the CLI, with its questions for the chair.
- The web suite and build pass. Every journey passes on the LAN copy, at desktop and phone.
- https://192.168.1.6/guide/preview shows the chosen Material screen. The rest of the portal is
  unchanged.
- The ledger and the branch are ready for one fresh whole-branch review before the chair is
  asked about a PR.
