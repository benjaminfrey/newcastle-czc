# Applicant Portal M3 — Form Engine and "Do I need a permit?" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A signed-out visitor answers a few plain questions — what they're planning, where, which
use, how big — and the portal says which applications the adopted Code calls for, who reviews
each, how long the Code gives the reviewer, and why (with the Code section), never claiming more
than the chair has approved.

**Architecture:** The adopted ruleset (`adopted-v1.0`) is vendored into the API package and pinned by
key and SHA-256. A small declarative condition language (`show_if`/`when`) has identical Python and
TypeScript evaluators proven against one shared fixture file. The screener's rules, the catalogue of
applications and the plain-language use groups are YAML data; every entry carries a Code citation
and a `status` (`draft`/`approved`). The engine evaluates the rules against the answers plus the
use table; **production refuses any answer that rests on a draft entry** until the chair approves it.

**Tech Stack:** M2's stack, plus PyYAML 6.0.3 (definitions) and the `yaml` npm package is **not**
needed (the API serves the definitions as JSON).

**Spec:** `specs/2026-10-14-applicant-portal-design.md` (§4 steps 1 and 3, §5 "Form definitions" and
"The screener", §7 "Screener scenarios") · **Roadmap:** M3 · **Built on:** `main` at `202355b`.

## Decisions made with the chair (2026-10-15)

- **Rules start as drafts; the chair approves each.** Every rule, application entry and plain
  "for example" line has `status: draft` until the chair sets `status: approved` (with `approved_by`,
  `approved_on`). The API refuses to give applicants an answer that uses any draft entry
  (`PORTAL_ALLOW_DRAFT_RULES=true` only on the dev VM and the LAN stack, like the stale-parcel switch).
  A generated **review sheet** lists every draft entry with its citation and Code text, for the chair.
- **Uses are found by plain groups plus search.** Each of the 63 uses in the adopted use table shows
  its Code name and the Code's own definition word for word, plus one short plain "for example"
  line (drafted here, approved by the chair).

## What the Code says that the rules rest on (read 2026-10-15, unchanged since v1.0)

| Application | Applies to (Art. 8) | Reviewer | Clock in `clocks.json` |
|---|---|---|---|
| Use Permit (`u` ●) | new Use or change of Use (§15.b.1) | per District page — the use table says CEO | `use_permit_decision` 30 days (§15.d.1) |
| Residential Companion (`rc`) | new RC use or change to/from (§17.b.1) | follows §15.C (§17.c.1) | **none names it** — show no days |
| Expanded Use (`ex`) | new Expanded Use or change to/from (§16.b.1) | follows §15.C; table says Planning Board | `use_permit_decision` 30 days |
| Special Permit (`sp`) | only as the Code authorizes (§18.b.1) | Planning Board (§18.c.1) | `special_permit_review_hearing` 30, `special_permit_decision` 45 |
| Small Project Plan | new buildings/accessory ≤ 10,000 sf GFA; renovations ≤ 10,000 sf; additions of building components; site improvements; changes to a nonconforming lot/use/structure ≤ 10 acres (§10.b.1–5) | CEO (§10.c.1; may forward to PB, §10.c.3) | `small_project_decision` 10 days |
| Large Project Plan | significant impacts; new/accessory > 10,000 sf; renovations > 10,000 sf; > 50 parking spaces; nonconforming changes > 10 acres; building groups not triggering subdivision (§11.b.1–6) | CEO (§11.c.1) | `large_project_ceo_decision` 45 days |
| Subdivision | 3+ lots in 5 years; 3+ dwelling units by division, construction or placement; roads; utilities (§12.b.1–6) | Planning Board (§12.c.2) | (Board app: subdivision clocks) |
| Variance | dimensional only — lot area, coverage, frontage, setbacks; never uses (§19.b) | Board of Appeals | — |
| Driveway / Entrance permit | new Driveways and relocations, not maintenance (Art. 3 §7.b); any new access from a Street or Road (§8.b.1) | CEO (Art. 3 §13.c.1.a–b) | none in `clocks.json` |
| MaineDOT entrance permit | entrance onto a State Highway (Art. 3 §12.d.1, §8.c.1) | MaineDOT, outside the Town | — |
| Civic land | SD-Civic (Art. 2 §5.b.1) + chair's ruling P13 | Town Meeting | — |

A blank use-table cell (`code: ""`, `permit_key: "prohibited"`) means the use is not allowed in that
district. One cell (D3 × Retail Service General) is `rc sp` with `reviews_rule: all_required`.
`uses.json` names two uses differently from the use table (`paid_parking_lot` ↔ "PARKING LOT",
`banking_services` ↔ "BANKING & FINANCIAL SERVICES"); "FARMSTAND" has a definition but no use-table
row. The use groups file maps each use-table key to its definition key explicitly.

## Global Constraints

- All M1/M2 Global Constraints hold (VM workflow; stage by name; trailer; no push/merge unasked).
- **Never guess a legal value.** Every rule cites a Code section and quotes it from the vendored
  `articles.json`; a citation that does not resolve fails the test suite. Clocks are shown only when
  `clocks.json` lists the application in `applies_to`.
- **Never a verdict.** The screener says "the Code calls for…", "you may need…", "the Code doesn't list
  this use in…"; never "approved", "allowed to build", "denied". The M1 no-verdict word list
  (`approved, denied, compliant, meets, fails, violates`) is checked against every applicant-facing
  string in the definitions and the results page.
- **Drafts never reach applicants in production** (above).
- **The adopted ruleset only**, pinned by key and per-file SHA-256 from its manifest; a draft or
  non-binding ruleset is refused.
- Screener endpoints are public, read-only, rate-limited with the M2 lookup limiter, and not logged.

## Review Focus

1. **A lot in two districts** with different use-table answers — the result must show both
   districts' answers, not pick one: Task 4 `test_use_in_two_districts_shows_both`.
2. **A use the Code doesn't allow in the district** — a plain "the Code doesn't list this use in
   …" with the Variance limit (§19.b: variances are never for uses) and "contact the Town Office",
   not an error or silence: Task 4 `test_use_not_listed_in_district`.
3. **Unknown size** ("I don't know yet") — both Small and Large Project Plan shown as "may need", with
   the 10,000 sf line explained: Task 4 `test_unknown_building_size_gives_both_with_the_threshold`.
4. **A draft rule in production** — the endpoint answers `503 screener_not_approved` and the page
   says the tool isn't ready and to contact the Town Office: Task 4
   `test_draft_rules_are_refused_by_default`, Task 6 "says when answers aren't approved yet".
5. **Civic land** — town-only answer, nothing else: Task 4 `test_civic_land_is_town_only`.

---

## Task 0: Sync the whole adopted ruleset to the VM

- [ ] In `portal/vm.sh` `sync()`, replace the single `build/permit-review/rulesets/adopted-v1.0/districts.json`
  line with `build/permit-review/rulesets/adopted-v1.0/` (rsync `-R` keeps the path). Check:
  `portal/vm.sh run 'ls build/permit-review/rulesets/adopted-v1.0'` lists the eight files. Commit
  `portal: sync the adopted ruleset to the VM (M3 Task 0)`.

---

## Task 1: The pinned ruleset

**Files:**
- Create: `portal/api/portal_api/rulesets/adopted-v1.0/` — copies of `manifest.json`, `articles.json`,
  `uses.json`, `use-matrix.json`, `districts.json`, `clocks.json` from `build/permit-review/rulesets/adopted-v1.0/`
- Create: `portal/api/portal_api/ruleset.py`, `portal/api/tests/test_ruleset.py`
- Modify: `portal/api/Dockerfile` (nothing — the folder is inside `portal_api`, already copied)

**Interfaces:**
- `PINNED_KEY = "adopted-v1.0"`; `load_ruleset(key: str = PINNED_KEY, root: Path | None = None) -> Ruleset`
  (cached per key); `RulesetError`.
- `Ruleset` fields: `key`, `adopted_on: date`, `uses: list[dict]` (use-table rows), `cells: dict[(district_key, use_key), dict]`,
  `legend: dict[code, dict]`, `clocks: dict[clock_key, dict]`, `districts: list[dict]`,
  `definitions: dict[str, dict]` (uses.json), `articles: dict` (articles.json), and
  `cite(ref: str) -> str` returning the Code text for a citation like `"8.10.b.1"` (Article.Section.sub…)
  or raising `RulesetError`.
- `district_key_for(trace_code: str) -> str | None`: `D1`→`d1`; `SD-Marine`→`sd-marine` via the
  ruleset's SD name; `SD-Civic`→`None`.

- [ ] **Step 1: Write the failing tests** — `test_ruleset.py`:

```python
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from portal_api.ruleset import PINNED_KEY, RulesetError, district_key_for, load_ruleset

VENDORED = Path(__file__).resolve().parents[1] / "portal_api" / "rulesets" / PINNED_KEY
SOURCE = Path(__file__).resolve().parents[3] / "build" / "permit-review" / "rulesets" / PINNED_KEY


def test_loads_the_adopted_ruleset():
    r = load_ruleset()
    assert r.key == "adopted-v1.0" and str(r.adopted_on) == "2026-09-14"
    assert len(r.uses) == 63 and len(r.cells) == 819 and len(r.districts) == 13


def test_vendored_files_match_the_board_apps_ruleset():
    for f in VENDORED.iterdir():
        assert f.read_bytes() == (SOURCE / f.name).read_bytes(), f.name


def test_a_tampered_file_is_refused(tmp_path):
    shutil.copytree(VENDORED, tmp_path / PINNED_KEY)
    p = tmp_path / PINNED_KEY / "use-matrix.json"
    p.write_text(p.read_text().replace('"Use Permit"', '"Use Permit!"', 1))
    with pytest.raises(RulesetError, match="use_matrix"):
        load_ruleset(PINNED_KEY, root=tmp_path)


def test_a_non_binding_ruleset_is_refused(tmp_path):
    shutil.copytree(VENDORED, tmp_path / PINNED_KEY)
    m = tmp_path / PINNED_KEY / "manifest.json"
    data = json.loads(m.read_text())
    data["binding"] = False
    m.write_text(json.dumps(data))
    with pytest.raises(RulesetError, match="binding"):
        load_ruleset(PINNED_KEY, root=tmp_path)


def test_cite_returns_code_text():
    r = load_ruleset()
    assert "10,000 sf" in r.cite("8.10.b.1")
    with pytest.raises(RulesetError):
        r.cite("8.99.z.9")


def test_district_keys_from_trace_codes():
    assert district_key_for("D2") == "d2"
    assert district_key_for("SD-Marine") == "sd-marine"
    assert district_key_for("SD-Highway Commercial") == "sd-hwy"
    assert district_key_for("SD-Civic") is None
```

- [ ] **Step 2:** Run — FAIL (no module).
- [ ] **Step 3: Implement** `ruleset.py`. Loading: read `manifest.json`; refuse unless
  `kind == "adopted-czc"`, `status == "active"`, `binding is True`; for each of the six vendored
  logical files (`articles`, `uses`, `use_matrix`, `districts`, `clocks` plus the manifest itself
  unchecked) compare `sha256(file bytes)` with `manifest["content_sha256"][name]` and raise
  `RulesetError(f"{name} does not match the manifest")` on mismatch. `cite()`: read the structure of
  `articles.json` first (the Board app's `ruleset_build/verify_citations.py` resolves the same
  citations — reuse its walking logic by reading it, not by importing it) and return the node's text;
  record how it walks in a ruling. `district_key_for` uses `districts` (`district_key`, `code`, `name`).
- [ ] **Step 4:** Copy the six files (`cp` from `build/permit-review/rulesets/adopted-v1.0/`), run the
  suite — all pass. Commit `portal: pin the adopted ruleset (M3 Task 1)`.

---

## Task 2: The condition language, in Python and TypeScript

**Files:**
- Create: `portal/web/src/forms/expr-fixtures.json` (the one shared fixture file)
- Create: `portal/api/portal_api/forms/__init__.py`, `portal/api/portal_api/forms/expr.py`, `portal/api/tests/test_expr.py`
- Create: `portal/web/src/forms/expr.ts`, `portal/web/src/forms/expr.test.ts`

**The language** (JSON/YAML data, never executed):
- `{"all": [c, …]}`, `{"any": [c, …]}`, `{"not": c}`
- `{"eq": [path, value]}`, `{"ne": [path, value]}`
- `{"has": [path, value]}` — the list at `path` contains `value`
- `{"oneof": [path, [v, …]]}` — the value at `path` is one of the list
- `{"gt"|"gte"|"lt"|"lte": [path, number]}`
- `{"known": path}` — the value at `path` is present and not null
- A `path` is dot-separated (`property.on_state_highway`).

**Three-valued:** a missing or null value makes a comparison **unknown** (`None`/`null`), never
false. `all` → false if any false, else unknown if any unknown, else true. `any` → true if any true,
else unknown if any unknown, else false. `not` unknown → unknown. `known` is never unknown.

- [ ] **Step 1: Write `expr-fixtures.json`** — at least these cases, each `{"name", "expr", "data", "expect"}`:

```json
[
  {"name": "eq true", "expr": {"eq": ["a", 1]}, "data": {"a": 1}, "expect": true},
  {"name": "eq false", "expr": {"eq": ["a", 1]}, "data": {"a": 2}, "expect": false},
  {"name": "eq missing is unknown", "expr": {"eq": ["a", 1]}, "data": {}, "expect": null},
  {"name": "eq null is unknown", "expr": {"eq": ["a", 1]}, "data": {"a": null}, "expect": null},
  {"name": "nested path", "expr": {"eq": ["p.q", "x"]}, "data": {"p": {"q": "x"}}, "expect": true},
  {"name": "has", "expr": {"has": ["project", "build"]}, "data": {"project": ["use", "build"]}, "expect": true},
  {"name": "has absent", "expr": {"has": ["project", "build"]}, "data": {"project": ["use"]}, "expect": false},
  {"name": "oneof", "expr": {"oneof": ["k", ["new", "addition"]]}, "data": {"k": "addition"}, "expect": true},
  {"name": "lte boundary", "expr": {"lte": ["gfa", 10000]}, "data": {"gfa": 10000}, "expect": true},
  {"name": "gt boundary", "expr": {"gt": ["gfa", 10000]}, "data": {"gfa": 10000}, "expect": false},
  {"name": "gt on a string is unknown", "expr": {"gt": ["gfa", 1]}, "data": {"gfa": "big"}, "expect": null},
  {"name": "known", "expr": {"known": "gfa"}, "data": {"gfa": 0}, "expect": true},
  {"name": "known missing", "expr": {"known": "gfa"}, "data": {}, "expect": false},
  {"name": "all false wins", "expr": {"all": [{"eq": ["a", 1]}, {"eq": ["b", 1]}]}, "data": {"a": 2}, "expect": false},
  {"name": "all unknown", "expr": {"all": [{"eq": ["a", 1]}, {"eq": ["b", 1]}]}, "data": {"a": 1}, "expect": null},
  {"name": "any true wins", "expr": {"any": [{"eq": ["a", 1]}, {"eq": ["b", 1]}]}, "data": {"a": 1}, "expect": true},
  {"name": "any unknown", "expr": {"any": [{"eq": ["a", 1]}, {"eq": ["b", 1]}]}, "data": {"a": 2}, "expect": null},
  {"name": "not unknown", "expr": {"not": {"eq": ["a", 1]}}, "data": {}, "expect": null},
  {"name": "empty all is true", "expr": {"all": []}, "data": {}, "expect": true},
  {"name": "empty any is false", "expr": {"any": []}, "data": {}, "expect": false}
]
```

- [ ] **Step 2: Failing tests.** `test_expr.py` loads `Path(__file__).parents[2] / "web/src/forms/expr-fixtures.json"`
  and asserts `evaluate(case["expr"], case["data"]) == case["expect"]` for each (parametrised by
  name), plus `test_unknown_operator_is_refused` (`ValueError`). `expr.test.ts` imports the same JSON
  (`import fixtures from "./expr-fixtures.json"`) and does the same with `it.each`.
- [ ] **Step 3:** Run both — FAIL.
- [ ] **Step 4: Implement** `expr.py`'s `evaluate(expr: dict, data: dict) -> bool | None` and
  `expr.ts`'s `evaluate(expr: Expr, data: Record<string, unknown>): boolean | null`, plus
  `validate(expr)` in Python (raises on an unknown operator or a malformed argument list) used by
  the definitions loader. No `eval`, no regular expressions on user input.
- [ ] **Step 5:** Both suites green. Commit `portal: one condition language, two evaluators (M3 Task 2)`.

---

## Task 3: Definitions — applications, rules, use groups — and the draft guard

**Files:**
- Modify: `portal/api/requirements.txt` (+ `pyyaml==6.0.3`)
- Create: `portal/api/portal_api/forms/definitions/applications.yaml`, `rules.yaml`, `use-groups.yaml`
- Create: `portal/api/portal_api/forms/definitions.py`, `portal/api/tests/test_definitions.py`
- Modify: `portal/api/portal_api/config.py` (`allow_draft_rules: bool = False`)

**Interfaces:**
- `load_definitions(ruleset) -> Definitions` (cached), validating everything below and raising
  `DefinitionError` with the file and entry id.
- `Definitions.applications: dict[key, Application]` — `key`, `code_name` (the Code's own name),
  `plain` (one sentence), `reviewer`, `cite`, `clock_keys: list[str]`, `in_portal: bool`, `status`.
- `Definitions.rules: list[Rule]` — `id`, `when` (condition), `outcome`, `cite`, `status`, `order`.
- `Definitions.groups: list[Group]` — `key`, `plain` (e.g. "A home"), `uses: list[UseEntry]` with
  `use_key`, `definition_key` (key into `uses.json`), `example` (plain line), `status`.
- `Definitions.drafts() -> list[DraftEntry]` (every entry whose `status` is `draft`).

**`applications.yaml`** (all `status: draft`; `in_portal` true only for the three M4 builds):

```yaml
- key: use_permit
  code_name: Use Permit
  plain: Permission to start a new use of land or a building, or to change from one use to another.
  reviewer: Code Enforcement Officer
  cite: "8.15.b.1"
  clock_keys: [use_permit_decision]
  in_portal: true
  status: draft
- key: residential_companion
  code_name: Residential Companion Use Permit
  plain: Permission for a use that goes along with a home on the same lot.
  reviewer: Code Enforcement Officer
  cite: "8.17.b.1"
  clock_keys: []
  in_portal: false
  status: draft
- key: expanded_use
  code_name: Expanded Use Permit
  plain: Permission for a use the Code normally places in busier districts.
  reviewer: Planning Board
  cite: "8.16.b.1"
  clock_keys: [use_permit_decision]
  in_portal: false
  status: draft
- key: special_permit
  code_name: Special Permit
  plain: A Planning Board decision, after a public hearing, on a use the Code allows only case by case.
  reviewer: Planning Board
  cite: "8.18.b.1"
  clock_keys: [special_permit_review_hearing, special_permit_decision]
  in_portal: false
  status: draft
- key: small_project_plan
  code_name: Small Project Plan
  plain: The Code Enforcement Officer's review of a new building, addition or site change up to 10,000 square feet.
  reviewer: Code Enforcement Officer
  cite: "8.10.b.1"
  clock_keys: [small_project_decision]
  in_portal: true
  status: draft
- key: large_project_plan
  code_name: Large Project Plan
  plain: A fuller review of a building over 10,000 square feet, a large parking lot, or a project with big effects on its surroundings.
  reviewer: Code Enforcement Officer
  cite: "8.11.b.2"
  clock_keys: [large_project_ceo_decision]
  in_portal: false
  status: draft
- key: subdivision
  code_name: Subdivision
  plain: The Planning Board's review of dividing land into three or more lots, or building three or more homes.
  reviewer: Planning Board
  cite: "8.12.b.1"
  clock_keys: []
  in_portal: false
  status: draft
- key: entrance_permit
  code_name: Driveway and Entrance Permit
  plain: Permission for a new driveway or entrance onto a street or road, or for moving one.
  reviewer: Code Enforcement Officer
  cite: "3.13.c.1"
  clock_keys: []
  in_portal: true
  status: draft
```

**`rules.yaml`** — evaluated in `order`; each produces outcomes. Outcome kinds:
`application` (`application`, `certainty: needed|may_need`), `use_table` (look up the use in every
district of the lot), `note` (`text`), `town_only`, `contact_town`. A rule with `stop: true` ends
evaluation when its `when` is true. All `status: draft`.

```yaml
- id: civic-land
  order: 10
  when: {eq: [property.civic, true]}
  outcome: {kind: town_only}
  cite: "2.5.b.1"
  stop: true
  status: draft
- id: use-from-table
  order: 20
  when: {all: [{has: [project, use]}, {known: use_key}]}
  outcome: {kind: use_table}
  cite: "8.15.b.1"
  status: draft
- id: use-not-chosen
  order: 21
  when: {all: [{has: [project, use]}, {not: {known: use_key}}]}
  outcome: {kind: note, text: "Choose the use you have in mind to see which permit the Code calls for."}
  cite: "8.15.b.1"
  status: draft
- id: small-project
  order: 30
  when: {all: [{has: [project, build]}, {lte: [building.gross_floor_area_sf, 10000]}]}
  outcome: {kind: application, application: small_project_plan, certainty: needed}
  cite: "8.10.b.1"
  status: draft
- id: large-project
  order: 31
  when: {all: [{has: [project, build]}, {gt: [building.gross_floor_area_sf, 10000]}]}
  outcome: {kind: application, application: large_project_plan, certainty: needed}
  cite: "8.11.b.2"
  status: draft
- id: building-size-unknown
  order: 32
  when: {all: [{has: [project, build]}, {not: {known: building.gross_floor_area_sf}}]}
  outcome: {kind: note, text: "Up to 10,000 square feet of floor area is a Small Project Plan; more is a Large Project Plan. Measure the floor area of every storey you're adding."}
  cite: "8.10.b.1"
  status: draft
- id: three-or-more-homes
  order: 33
  when: {all: [{has: [project, build]}, {gte: [building.dwelling_units, 3]}]}
  outcome: {kind: application, application: subdivision, certainty: needed}
  cite: "8.12.b.3"
  status: draft
- id: divide-three-or-more
  order: 40
  when: {all: [{has: [project, divide]}, {gte: [division.lots_after, 3]}]}
  outcome: {kind: application, application: subdivision, certainty: needed}
  cite: "8.12.b.1"
  status: draft
- id: divide-fewer
  order: 41
  when: {all: [{has: [project, divide]}, {lt: [division.lots_after, 3]}]}
  outcome: {kind: contact_town, text: "Dividing into fewer than three lots isn't a subdivision under the Code, but other rules may still apply. The Code Enforcement Officer can tell you what you need."}
  cite: "8.12.b.1"
  status: draft
- id: driveway
  order: 50
  when: {has: [project, driveway]}
  outcome: {kind: application, application: entrance_permit, certainty: needed}
  cite: "3.7.b.1"
  status: draft
- id: maine-dot
  order: 51
  when: {all: [{has: [project, driveway]}, {eq: [property.on_state_highway, true]}]}
  outcome: {kind: note, text: "Your lot is on a State highway, so the Maine Department of Transportation must also approve the entrance. Bring a copy of their permit to the Town."}
  cite: "3.12.d.1"
  status: draft
- id: something-else
  order: 90
  when: {has: [project, other]}
  outcome: {kind: contact_town, text: "Tell the Code Enforcement Officer what you have in mind; they can say what, if anything, you need."}
  cite: "8.9.c.1"
  status: draft
```

(Before writing, confirm each `cite` resolves with `ruleset.cite()`; if a sub-item number differs
in `articles.json`, correct the citation and record a ruling — never change the Code text.)

**`use-groups.yaml`** — seven groups: `home` "A home", `shop_office` "A shop, office or service",
`food_lodging` "Food, drink or places to stay", `farming` "Farming and land", `making_storing`
"Making, fixing or storing things", `recreation_community` "Recreation, community and culture",
`transport_utilities` "Transport, parking and utilities". Every use-table `use_key` appears in
exactly one group, with its `definition_key` (the `uses.json` name; `paid_parking_lot` → `PARKING LOT`,
`banking_services` → `BANKING & FINANCIAL SERVICES`) and a one-line plain `example` written from the
Code definition (e.g. Dispatch Service: "A taxi, delivery or towing company's base."), all
`status: draft`.

- [ ] **Step 1: Failing tests** — `test_definitions.py`:

```python
import pytest

from portal_api.forms.definitions import DefinitionError, load_definitions, validate_entries
from portal_api.ruleset import load_ruleset

VERDICT_WORDS = ("approved", "denied", "compliant", "meets", "fails", "violates")


@pytest.fixture(scope="module")
def defs():
    return load_definitions(load_ruleset())


def test_every_use_is_in_exactly_one_group(defs):
    seen = [u.use_key for g in defs.groups for u in g.uses]
    assert sorted(seen) == sorted(u["use_key"] for u in load_ruleset().uses)
    assert len(seen) == len(set(seen))


def test_every_use_has_its_code_definition(defs):
    r = load_ruleset()
    for g in defs.groups:
        for u in g.uses:
            assert u.definition_key in r.definitions, u.use_key


def test_every_citation_resolves(defs):
    r = load_ruleset()
    for x in [*defs.applications.values(), *defs.rules]:
        assert r.cite(x.cite)


def test_every_clock_exists_and_applies(defs):
    r = load_ruleset()
    for a in defs.applications.values():
        for k in a.clock_keys:
            assert k in r.clocks


def test_rules_reference_known_applications(defs):
    for rule in defs.rules:
        if rule.outcome.get("kind") == "application":
            assert rule.outcome["application"] in defs.applications


def test_no_verdict_words_in_applicant_text(defs):
    texts = [a.plain for a in defs.applications.values()]
    texts += [r.outcome.get("text", "") for r in defs.rules]
    texts += [u.example for g in defs.groups for u in g.uses] + [g.plain for g in defs.groups]
    for t in texts:
        assert not any(w in t.lower() for w in VERDICT_WORDS), t


def test_drafts_are_listed(defs):
    assert defs.drafts()  # everything starts as a draft


def test_a_bad_condition_names_the_entry():
    with pytest.raises(DefinitionError, match="rules.yaml: bad-rule"):
        validate_entries("rules.yaml", [{"id": "bad-rule", "order": 1, "when": {"between": ["a", 1]},
                                         "outcome": {"kind": "note", "text": "x"}, "cite": "8.10.b.1",
                                         "status": "draft"}], load_ruleset())


def test_approval_needs_who_and_when():
    with pytest.raises(DefinitionError, match="approved_by"):
        validate_entries("rules.yaml", [{"id": "r", "order": 1, "when": {"all": []},
                                         "outcome": {"kind": "note", "text": "x"}, "cite": "8.10.b.1",
                                         "status": "approved"}], load_ruleset())
```

- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement `definitions.py` with dataclasses and
  `validate_entries(file, entries, ruleset)` (checks ids unique, status in `draft|approved`,
  `approved` needs `approved_by` and `approved_on`, conditions pass `expr.validate`, citations
  resolve). Write the three YAML files. **Step 4:** All pass. Commit
  `portal: application, rule and use-group definitions, all drafts (M3 Task 3)`.

---

## Task 4: The screener engine and API

**Files:**
- Create: `portal/api/portal_api/forms/screener.py`, `portal/api/portal_api/routes/screener.py`, `portal/api/tests/test_screener.py`
- Modify: `portal/api/portal_api/main.py`

**Interfaces:**
- `Answers` (pydantic): `project: list[Literal["build","use","driveway","divide","other"]]` (≥1);
  `property: {district_codes: list[str], on_state_highway: bool | None, civic: bool}`;
  `use_key: str | None`; `building: {kind: "new"|"addition"|"renovation"|None, gross_floor_area_sf: float|None, dwelling_units: int|None}`;
  `division: {lots_after: int|None}`.
- `run(answers, ruleset, defs) -> Result`: `{"outcomes": [...], "notes": [...], "not_listed": [...], "drafts_used": [ids]}`.
  - An application outcome: `{"application", "code_name", "plain", "reviewer", "certainty", "days": [{"label","days","basis","cite"}], "why": {"cite","text"}, "in_portal", "district": code|null}`.
  - `use_table`: for each district key of the lot (`district_key_for` over `property.district_codes`),
    the cell for `use_key`: `u`→use_permit, `rc`→residential_companion, `ex`→expanded_use,
    `sp`→special_permit, `rc sp`→both; blank → a `not_listed` entry
    `{"district", "use", "text": "The Code doesn't list this use in the {district name} district. A variance can't be granted for a use (Art. 8 §19.b). The Code Enforcement Officer can talk you through your options.", "cite": "8.19.b.1"}`.
    Districts unknown (empty list) → note "Find your property first so we can check its district."
  - Duplicate applications (same key, same district) merge.
- `POST /api/screener` → `200 Result`; `422` bad answers; `503 {"detail": "screener_not_approved"}` when
  `drafts_used` is not empty and `allow_draft_rules` is false. `GET /api/screener/uses` → the groups with
  each use's Code name, Code definition (verbatim from `uses.json`), example — `503` likewise if any
  is draft. Both use the M2 lookup rate limit; neither logs.

- [ ] **Step 1: Failing tests** — `test_screener.py` (a `client` fixture with `allow_draft_rules = True`
  unless noted):

```python
import pytest
from fastapi.testclient import TestClient

from portal_api.main import create_app


@pytest.fixture
def draft_client(engine, settings, outbox):
    settings.allow_draft_rules = True
    with TestClient(create_app(settings, outbox)) as c:
        yield c


def answers(**kw):
    base = {"project": ["use"], "property": {"district_codes": ["D2"], "on_state_highway": False, "civic": False},
            "use_key": None, "building": {"kind": None, "gross_floor_area_sf": None, "dwelling_units": None},
            "division": {"lots_after": None}}
    base.update(kw)
    return base


def _apps(r):
    return {(o["application"], o["district"]) for o in r.json()["outcomes"]}


def _first_cell(code, district="d2"):
    from portal_api.ruleset import load_ruleset
    r = load_ruleset()
    return next(k[1] for k, c in r.cells.items() if k[0] == district and c["code"] == code)


def test_use_from_the_table(draft_client):
    use = _first_cell("u")
    r = draft_client.post("/api/screener", json=answers(use_key=use))
    assert ("use_permit", "D2") in _apps(r)
    o = next(o for o in r.json()["outcomes"] if o["application"] == "use_permit")
    assert o["reviewer"] == "Code Enforcement Officer" and o["days"][0]["days"] == 30
    assert "8" in o["why"]["cite"] and o["why"]["text"]


def test_use_in_two_districts_shows_both(draft_client):
    from portal_api.ruleset import load_ruleset
    r = load_ruleset()
    use = next(u for (d, u), c in r.cells.items() if d == "d1" and c["code"] == "u" and r.cells[("d6", u)]["code"] == "sp")
    res = draft_client.post("/api/screener", json=answers(
        use_key=use, property={"district_codes": ["D1", "D6"], "on_state_highway": False, "civic": False}))
    assert {("use_permit", "D1"), ("special_permit", "D6")} <= _apps(res)


def test_use_not_listed_in_district(draft_client):
    use = _first_cell("")
    res = draft_client.post("/api/screener", json=answers(use_key=use)).json()
    (nl,) = res["not_listed"]
    assert nl["district"] == "D2" and "variance can't be granted for a use" in nl["text"]


def test_the_two_permit_cell_needs_both(draft_client):
    res = draft_client.post("/api/screener", json=answers(
        use_key="retail_service_general", property={"district_codes": ["D3"], "on_state_highway": False, "civic": False}))
    assert {("residential_companion", "D3"), ("special_permit", "D3")} <= _apps(res)


def test_small_and_large_project_by_floor_area(draft_client):
    small = draft_client.post("/api/screener", json=answers(project=["build"], building={"kind": "new", "gross_floor_area_sf": 10000, "dwelling_units": 1}))
    large = draft_client.post("/api/screener", json=answers(project=["build"], building={"kind": "new", "gross_floor_area_sf": 10001, "dwelling_units": 1}))
    assert {a for a, _ in _apps(small)} == {"small_project_plan"}
    assert {a for a, _ in _apps(large)} == {"large_project_plan"}


def test_unknown_building_size_gives_both_with_the_threshold(draft_client):
    res = draft_client.post("/api/screener", json=answers(project=["build"])).json()
    assert any("10,000 square feet" in n["text"] for n in res["notes"])


def test_three_homes_is_a_subdivision(draft_client):
    res = draft_client.post("/api/screener", json=answers(project=["build"], building={"kind": "new", "gross_floor_area_sf": 3000, "dwelling_units": 3}))
    assert "subdivision" in {a for a, _ in _apps(res)}


def test_driveway_on_a_state_highway_adds_maine_dot(draft_client):
    res = draft_client.post("/api/screener", json=answers(project=["driveway"], property={"district_codes": ["D1"], "on_state_highway": True, "civic": False})).json()
    assert {o["application"] for o in res["outcomes"]} == {"entrance_permit"}
    assert any("Maine Department of Transportation" in n["text"] for n in res["notes"])


def test_civic_land_is_town_only(draft_client):
    res = draft_client.post("/api/screener", json=answers(project=["build", "use"], use_key=_first_cell("u"),
        property={"district_codes": ["SD-Civic"], "on_state_highway": False, "civic": True})).json()
    assert res["outcomes"] == [] and res["town_only"] is True


def test_draft_rules_are_refused_by_default(engine, settings, outbox):
    with TestClient(create_app(settings, outbox)) as c:
        r = c.post("/api/screener", json=answers(use_key=_first_cell("u")))
        assert r.status_code == 503 and r.json() == {"detail": "screener_not_approved"}
        assert c.get("/api/screener/uses").status_code == 503


def test_uses_endpoint_quotes_the_code(draft_client):
    groups = draft_client.get("/api/screener/uses").json()
    u = next(u for g in groups for u in g["uses"] if u["use_key"] == "dispatch_service")
    from portal_api.ruleset import load_ruleset
    assert u["definition"] == load_ruleset().definitions["DISPATCH SERVICE"]["definition"]


def test_bad_answers_are_422(draft_client):
    assert draft_client.post("/api/screener", json=answers(project=["fly"])).status_code == 422
    assert draft_client.post("/api/screener", json=answers(project=[])).status_code == 422
```

- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement (Result also carries `"town_only": bool`).
  **Step 4:** All pass. Commit `portal: the screener engine and API (M3 Task 4)`.

---

## Task 5: The scenario table (spec §7)

**Files:** Create `portal/api/tests/test_screener_scenarios.py`.

- [ ] Generate, from the vendored use table, one case per (district, use) — 819 — and assert the
  screener's use outcomes for a lot wholly in that district equal the cell: `u`→`{use_permit}`,
  `rc`→`{residential_companion}`, `ex`→`{expanded_use}`, `sp`→`{special_permit}`, `rc sp`→both,
  blank→`not_listed`. The engine is called directly (`run(...)`), not over HTTP, so the 819 cases
  stay fast. Name each case `d1/dispatch_service` etc. Commit
  `portal: the screener agrees with every use-table cell (M3 Task 5)`.

---

## Task 6: The "Do I need a permit?" pages

**Files:**
- Create: `portal/web/src/pages/Start.tsx` (what are you planning), `portal/web/src/pages/UsePicker.tsx`,
  `portal/web/src/pages/Results.tsx`, `portal/web/src/screener.ts` (answers kept in `sessionStorage`
  like `property.ts`), tests `Start.test.tsx`, `UsePicker.test.tsx`, `Results.test.tsx`
- Modify: `portal/web/src/api.ts` (`runScreener`, `getUseGroups`; `"not_approved"` on 503
  `screener_not_approved`, `"busy"` on 429, `"unavailable"` otherwise), `App.tsx` (routes `/start`,
  `/start/use`, `/start/results`), `Home.tsx` (link "Do I need a permit?"), `Where.tsx` (after
  saving, go on to `/start/use` or `/start/results` when a screener is in progress)

**Flow:** `/start` asks "What are you planning?" with checkboxes (plain labels from spec §4 step 1:
"Build something new or add on", "Start a business or change how a building is used", "Put in or
move a driveway", "Divide land", "Something else / not sure"); if "build" is ticked, a "How much
floor area will you add?" number field (sq ft) with "I don't know yet", and "How many homes will
there be?"; if "divide", "How many lots will there be afterwards?". Then `/where` (M2). Then, if
"use", `/start/use`: the seven groups as buttons and a search box; each use shows its Code name, a
"What the Code says" disclosure with the definition, and its example. Then `/start/results`:
"Here's what you'll need" — one card per application (Code name, plain line, who reviews it, the
Code's time limit when there is one, "Why: Art. 8 §10.b.1" with the quoted text in a disclosure,
"You can apply here" for `in_portal`, otherwise "Apply through the Town Office"), the notes, any
"not listed" explanation, the fee line ("Set by the Town's fee schedule — the Town Office will tell
you the amount", spec O1), and the closing line "The Code Enforcement Officer confirms this when
you apply." On Civic land: only the Civic explanation.

- [ ] **Step 1: Failing tests** (follow M1/M2 style; mock `api`):
  - `Start.test.tsx`: "asks floor area only when building", "keeps the answers for the next step"
    (`loadAnswers()` after "Next"), "requires at least one choice".
  - `UsePicker.test.tsx`: "shows groups and finds a use by search" (typing "taxi" finds Dispatch
    Service by its example), "shows the Code's definition word for word", "saves the chosen use".
  - `Results.test.tsx`: "lists each application with reviewer, time limit and why" (asserts "30 days",
    "Code Enforcement Officer", "Art. 8 §15.b.1"), "marks the ones you can apply for here",
    "explains a use the Code doesn't list in the district", "shows the fee line", "says when answers
    aren't approved yet" (`not_approved` → "This tool isn't ready yet. Please contact the Town
    Office."), "shows only the Civic explanation on Civic land", and "contains no verdict words"
    (renders a full result and checks the page text against the M1 list).
- [ ] **Step 2–4:** RED, implement, GREEN; `npm run build` clean. Commit
  `portal: the "Do I need a permit?" pages (M3 Task 6)`.

---

## Task 7: The review sheet for the chair

**Files:** Create `portal/api/portal_api/forms/__main__.py` (`python -m portal_api.forms review-sheet`),
`portal/api/tests/test_review_sheet.py`.

- [ ] `review-sheet` writes Markdown listing every draft entry grouped by file: id, what it says to
  applicants, its citation and the **Code text quoted from the ruleset**, and the line to change to
  approve it (`status: approved`, `approved_by: …`, `approved_on: YYYY-MM-DD`). Test: the sheet
  contains every draft id and the Code text for `8.10.b.1`. Render it as a memo with
  `bash build/build-memo.sh` only if the chair asks; commit the generated Markdown at
  `memos/2026-10-15-screener-rules-for-approval.md`. Commit
  `portal: a review sheet of the screener's draft rules (M3 Task 7)`.

---

## Task 8: Wire up, check by hand, document

- [ ] `compose.lan.yml`: `PORTAL_ALLOW_DRAFT_RULES: "true"` (development). README: the draft guard,
  how to approve an entry, the review sheet. Roadmap: M3 status; open item "chair approves screener
  rules".
- [ ] Hands-on through the dev servers: from Home → "Do I need a permit?" → build 2,400 sq ft + new
  use → address 461 Sheepscot → pick a use → results show Small Project Plan and the use-table
  answer for D1 with times and citations; a State-highway lot with a driveway shows the MaineDOT
  note; a Civic lot shows only the Civic explanation; at 375 px; with the production default the
  results page says the tool isn't ready. Commit `portal: M3 wiring and docs (M3 Task 8)`.

## Milestone 3 done when

- API and web suites green on the VM and in CI; the 819-case scenario table passes; the two
  evaluators agree on every shared fixture.
- "Do I need a permit?" works signed out on the dev/LAN stacks; production refuses draft answers.
- The review sheet is in `memos/` for the chair; one fresh-context whole-branch review, findings
  ruled on.
