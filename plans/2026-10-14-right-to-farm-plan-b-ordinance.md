# Right to Farm — Plan B: the ordinance, the district data, and the v1.2-draft release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draft the Right to Farm amendment into the Code: a new Article 7 §3, the definitions, the
edits to Articles 1, 4 and 5, and the thirteen district tables and buildings matrices. Then proof
it as the v1.2-draft release for Planning Board review.

**Architecture:** Each task changes one Article (or the Article 2 data) and ends with a proof
build of that Article for Ben's review. A new consistency test, `build/tests/test_right_to_farm.py`,
grows task by task. It pins the facts that must agree across Articles: §3's tier table against the
district tables; the statuses that must not move; the Agricultural Building columns; the
single-definition rule. The prose is drafted during execution against the requirement checklists
below. The checklists are the specification; the drafting is the work Ben reviews.

**Tech Stack:** Markdown sources compiled by pandoc → Typst; `source/article-02-data.json`; Python
3.14 + pytest; the release driver `build/build-release.sh` (czc-release skill).

**Spec:** `specs/2026-10-07-right-to-farm-design.md` (approved 2026-10-14) · decisions
`plans/2026-10-14-right-to-farm-decisions.md` R1–R29 · depends on
`plans/2026-10-14-right-to-farm-plan-a-status-code.md` (must be complete: the `br` status exists).

## Global Constraints

- **Never guess a legal value** (rule 9). Every number and status comes from the spec or R1–R29. If drafting needs a value neither gives, stop and ask Ben. Don't invent one, and don't leave a placeholder in `source/`.
- **Match the CZC's form** (rule 7): `## N. TITLE`, `### a. PURPOSE` / `### b. APPLICABILITY` / `### c. GENERAL` …, numbered items `1.` with sub-items `a.` and `i.` at 4-space indents, tables captioned on their own line as `TABLE 7.N TITLE IN CAPS` followed by a pipe table. Defined terms in Article 9 are `**Term:**` on one line, definition on the next, alphabetical.
- **Drafting voice:** plain, mandatory "must"/"may", short sentences, as in Articles 4–8. No "shall" where the surrounding Article uses "must".
- **Prose in `source/` must not trip the residue gate** (CLAUDE.md gotcha): no "draft vote", "not adopted", "draft" as an adjective about the Code, and no HTML comments containing those words.
- **The §154 shield is described as the statute does** (spec §3.7.2): reached only by farm operations under 7 M.R.S. §152(5); conformance determined by the Commissioner (§156), never the CEO; switched on by state law wherever agriculture is permitted.
- **Citations:** statutes as `7 M.R.S. §154`. Code cross-references as the Code writes them, `Article 7 Section 1.h`. Every statute cited is on counsel's cite-check list (spec header); add none the spec does not already cite.
- Stage files by name (rule 2). Commit messages end `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (rule 5). Commit on `right-to-farm`. **No push, PR, tag or release into `releases/` without Ben's explicit go** (rules 1, 6).
- **Ben reviews each Article before the next task starts.** Every drafting task ends with a STOP.
- Version: **v1.2-draft**, redlined against **v1.1-draft**, the previous tag (the driver's `--old-ver`).

## Review Focus

1. **§3's tier table and the district tables disagree.** A voter reading D4's page sees no Medium Stock row ○. §3 must say the same. Pinned by `test_tier_table_matches_the_district_tables` (Tasks 2 and 6).
2. **A status that must not move moves.** Commercial Agriculture (R28), Farm/Vendor Market (R25) and Stables/Riding Center (R20) keep their v1.0 statuses in all thirteen districts. Pinned by `test_unmoved_statuses_match_v1_0` (Task 6).
3. **A carve-out that a co-located non-farm business can still claim.** A landscaping yard on a lot with a token garden gets the storage or fence exemption. Each re-keyed carve-out must name the activity's own footprint and R17's threshold. Checked by the requirement trace in Tasks 3 and 5, and by Ben's read.
4. **A district page that no longer fits.** Six new use rows in column 1, and a sixth buildings-matrix column in D5, SD-Highway Commercial, SD-Rural Highway and SD-Fabrication. A reasonable reader expects every page whole. Checked in Task 6: the Article 2 page count is unchanged and the pages are inspected.
5. **The renumbering breaks a reference.** Inserting §3 moves Article 7 §§3–64 to §§4–65. Any "Section N" that pointed at an old number now points at the wrong use. Pinned by `test_article_7_sections_are_consecutive` and by the reference sweep in Task 2.

---

### Task 1: Article 9 — the definitions

**Files:**
- Modify: `source/article-09-definitions.md`
- Create: `build/tests/test_right_to_farm.py`

**Interfaces:**
- Produces: the defined terms the later tasks use, spelled exactly: **Agriculture**, **Home/Personal Agriculture** (short form **Home Agriculture**, used in the table rows), **Commercial Agriculture**, **Small Stock**, **Medium Stock**, **Large Stock**, **Farm Stand**, **Greenhouse**, **Hoop House**, **High Tunnel**, **Manure Storage**, **Best Management Practices**, **Agritourism**, **On-Farm Processing**, **Agricultural Building**, **Barn**. Task 2 onward uses these spellings verbatim.

- [ ] **Step 1: Write the failing test**

Create `build/tests/test_right_to_farm.py`:

```python
"""Right to Farm (specs/2026-10-07-right-to-farm-design.md; decisions in
plans/2026-10-14-right-to-farm-decisions.md). Facts that must agree across
Articles, pinned so a later edit to one Article cannot silently contradict
another."""
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "source"

NEW_TERMS = [
    "Agriculture", "Home/Personal Agriculture", "Commercial Agriculture",
    "Small Stock", "Medium Stock", "Large Stock", "Farm Stand", "Greenhouse",
    "Hoop House", "High Tunnel", "Manure Storage", "Best Management Practices",
    "Agritourism", "On-Farm Processing", "Agricultural Building", "Barn",
]
RETIRED_TERMS = ["Agricultural Buildings", "Agricultural Use", "Large Animals", "Small Animals"]


def _terms() -> list[str]:
    text = (SRC / "article-09-definitions.md").read_text(encoding="utf-8")
    return re.findall(r"^\*\*(.+?):\*\*\s*$", text, flags=re.M)


def test_each_new_term_is_defined_exactly_once():
    terms = _terms()
    for t in NEW_TERMS:
        assert terms.count(t) == 1, f"{t!r} defined {terms.count(t)} times"


def test_retired_terms_are_gone_and_unused():
    assert not set(RETIRED_TERMS) & set(_terms())
    for f in SRC.glob("article-0*.md"):
        body = f.read_text(encoding="utf-8")
        for t in ("Large Animals", "Small Animals", "Agricultural Use"):
            assert t not in body, f"{f.name} still uses {t!r}"


def test_definitions_stay_alphabetical():
    terms = _terms()
    keys = [t.lower() for t in terms]
    assert keys == sorted(keys), "Article 9 terms out of alphabetical order"
```

Run: `python3 -m pytest build/tests/test_right_to_farm.py -q`
Expected: FAIL. Terms are missing, and the retired ones are present. If `test_definitions_stay_alphabetical` fails on **v1.0's own** ordering before any edit, run it on the unedited file first. If it does, restrict the test to the new terms' neighbours (assert each new term sorts between the entries before and after it) and note the pre-existing disorder in the commit message. Do not reorder the adopted Code.

- [ ] **Step 2: Find every use of the terms being retired or redefined**

```bash
grep -n -E "Agricultural Use|Agricultural Buildings?|Large Animals|Small Animals|agricultural activit|agricultural uses|commercial agricultural uses|active agricultural use|Commercial Agricultural uses|\bbarn" source/*.md source/article-02-data.json
```
Keep the list. Tasks 3 and 5 re-point each hit, and the column rename in Task 6 removes the "Agricultural Use" hit in the data. For now, Step 1's `test_retired_terms_are_gone_and_unused` is expected to stay red until Task 5. Mark it `@pytest.mark.xfail(strict=True, reason="re-pointed in Tasks 3, 5 and 6")` now. Task 6 removes the marker.

- [ ] **Step 3: Draft the definitions**

Requirements. Each must be traceable to one entry:
1. **Agriculture**: spec §3.1, verbatim in substance: the umbrella over Home/Personal and Commercial, "regulated separately because they differ in scale and impact".
2. **Home/Personal Agriculture**: spec §3.1, plus "(also Home Agriculture)". It includes the sale from the lot of products grown or made on that lot, including from a Farm Stand (D7, R19). It points to Article 7 Section 3 for the tiers.
3. **Commercial Agriculture**: spec §3.1. It tracks 7 M.R.S. §152(5)–(6). It includes production for wholesale and the sale of products not grown or made on the lot (D7). It excludes the boarding of others' horses, lessons, shows and events, which are Stables / Riding Center (R20).
4. **Small Stock**: up to six hens or hens and ducks, no roosters or drakes, plus up to six rabbits (spec §3.3). A seventh bird makes a flock Medium Stock (R6).
5. **Medium Stock**: goats, sheep, miniature breeds, alpacas, miniature horses and miniature donkeys (R26); roosters, drakes, turkeys, geese and guinea fowl (R7); a flock of more than six birds (R6); and "other animals of similar size".
6. **Large Stock**: cattle, horses, pigs, llamas, emus, standard donkeys and mules (spec §3.3, R26), and "other animals of similar or greater size".
7. **Agricultural Building**: one definition replacing both existing entries (spec §3.1). Barns, equipment sheds, stables, greenhouses and similar enclosed buildings used for agriculture. It expressly **excludes** hoop houses, high tunnels and other seasonal or unenclosed structures (R16), and Small Stock housing and hives, which are additional structures (R29).
8. **Barn**: an Agricultural Building for housing animals, equipment, feed or crops (the word is used operatively six times and defined nowhere — spec §3.6).
9. **Farm Stand, Greenhouse, Hoop House, High Tunnel, Manure Storage, Best Management Practices, Agritourism, On-Farm Processing**: one each. **Best Management Practices** is keyed to the statutory phrase "as determined by the Commissioner" under 7 M.R.S. §§154 and 156, naming no DACF publication (counsel's open question in spec §7). **Agritourism** is events and visits on a farm open to the public, so the §3.4 trigger (more than 50 attendees, or more than 12 events a year) has a subject.
10. **Retire** "Agricultural Buildings", "Agricultural Use", "Large Animals" and "Small Animals". The equine sentence moves to Article 7 §62 Stables in Task 4 (R20). Small and Large Animals give way to the three stock classes.

Insert each term alphabetically. Wording must not conflict with Article 7 §16's existing definition text; Task 4 reconciles §16 to point here.

- [ ] **Step 4: Run the tests and build the proof**

Run: `python3 -m pytest build/tests/test_right_to_farm.py -q` → the two non-xfail tests pass, and the xfail test xfails.
Run: `OUT_DIR="$TMPDIR/rtf-b1" bash build/build-standalone.sh 9 v1.2-draft` → exit 0.

- [ ] **Step 5: Commit, then STOP for Ben**

```bash
git add source/article-09-definitions.md build/tests/test_right_to_farm.py
git commit -m "Article 9: Right to Farm definitions (spec §3.1; R6, R7, R16, R19, R20, R26, R29)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Send Ben the standalone PDF (`SendUserFile`). With it, send a trace table: requirement number → the defined term that satisfies it. **Wait for his approval or edits before Task 2.**

---

### Task 2: Article 7 §3 "Right to Farm", part 1 — permission, tiers, separation, Board triggers

**Files:**
- Modify: `source/article-07-use-standards.md` (insert the new `## 3. RIGHT TO FARM` after `## 2. EXPANDED USE STANDARDS`; renumber `## 3.`…`## 64.` to `## 4.`…`## 65.`)
- Modify: `build/tests/test_right_to_farm.py` (append)

**Interfaces:**
- Consumes: Task 1's terms.
- Produces: `TABLE 7.1 AGRICULTURE TIERS BY DISTRICT`, `TABLE 7.2 SEPARATION DISTANCES`, `TABLE 7.3 PLANNING BOARD REVIEW`, in the exact format below. The test parses Table 7.1; Task 6 makes the data agree with it. Subsections a–f of §3; Task 3 adds g–j.

- [ ] **Step 1: Write the failing tests**

Append to `build/tests/test_right_to_farm.py`:

```python
DISTRICT_ORDER = ["D1", "D2", "D3", "D4", "D5", "D6", "SD-Historic", "SD-Conservation",
                  "SD-Highway Commercial", "SD-Rural Highway", "SD-Campus", "SD-Marine",
                  "SD-Fabrication"]          # article-02-data.json order
TIERS = ["Cultivation", "Beekeeping", "Small Stock", "Medium Stock", "Large Stock"]


def _art7() -> str:
    return (SRC / "article-07-use-standards.md").read_text(encoding="utf-8")


def tier_table() -> dict[str, set[str]]:
    """TABLE 7.1 → {tier: set of district labels}. 'All districts' → all 13."""
    text = _art7()
    block = text.split("TABLE 7.1 AGRICULTURE TIERS BY DISTRICT", 1)[1].split("\n\n", 2)[1]
    out = {}
    for line in block.splitlines()[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        where = cells[-1]
        out[cells[0]] = (set(DISTRICT_ORDER) if where == "All districts"
                         else {d.strip() for d in where.split(",")})
    return out


def test_tier_table_follows_the_spec():
    t = tier_table()
    assert list(t) == TIERS
    assert t["Cultivation"] == t["Beekeeping"] == t["Small Stock"] == set(DISTRICT_ORDER)
    assert t["Medium Stock"] == {"D1", "D2", "D3", "SD-Rural Highway", "SD-Conservation", "SD-Campus"}
    assert t["Large Stock"] == {"D1", "D2", "SD-Rural Highway", "SD-Conservation", "SD-Campus"}


def test_article_7_sections_are_consecutive():
    nums = [int(n) for n in re.findall(r"^## (\d+)\. ", _art7(), flags=re.M)]
    assert nums == list(range(1, len(nums) + 1))
    assert re.search(r"^## 3\. RIGHT TO FARM$", _art7(), flags=re.M)


def test_separation_and_board_tables_are_present():
    text = _art7()
    for caption in ("TABLE 7.2 SEPARATION DISTANCES", "TABLE 7.3 PLANNING BOARD REVIEW"):
        assert caption in text
```

Run: `python3 -m pytest build/tests/test_right_to_farm.py -q` → the three new tests FAIL.

- [ ] **Step 2: Insert the section and renumber**

Renumber mechanically before drafting, so the diff of the prose stays readable:

```bash
python3 - <<'EOF'
import re, pathlib
p = pathlib.Path("source/article-07-use-standards.md")
t = p.read_text(encoding="utf-8")
head, sep, rest = t.partition("\n## 3. ADULT ESTABLISHMENT")
assert sep, "anchor moved"
rest = re.sub(r"^## (\d+)\. ", lambda m: f"## {int(m.group(1)) + 1}. ", "## 3. ADULT ESTABLISHMENT" + rest, flags=re.M)
p.write_text(head + "\n## 3. RIGHT TO FARM\n\n" + rest, encoding="utf-8")
EOF
grep -n "^## [1-5]\. " source/article-07-use-standards.md
```
Expected: `## 1. USE STANDARDS`, `## 2. EXPANDED USE STANDARDS`, `## 3. RIGHT TO FARM`, `## 4. ADULT ESTABLISHMENT`, `## 5. AMUSEMENT, INDOOR`.

- [ ] **Step 3: Sweep references to renumbered sections**

```bash
grep -n -E "Section ([3-9]|[1-5][0-9]|6[0-4])\b|§ ?([3-9]|[1-5][0-9]|6[0-4])\b|Sections? [0-9]+ (through|to|and) [0-9]+" source/article-07-use-standards.md
grep -n -E "Article 7,? (Section|§) ?[0-9]+|Art\. 7" source/*.md source/article-02-data.json
```
Each hit that names an old §3–§64 of Article 7 moves up by one. Section 1 and 2 references don't move. Record the hits and their fixes in the task report. Note that `Article 7 §3.b.1.a` (the adult-establishment measuring rule, spec §3.5 item 3) is now **§4.b.1.a**.

- [ ] **Step 4: Draft §3.a–§3.f**

Requirements, each traceable to a clause:
- **a. PURPOSE**: farming as a spectrum from a garden in any district to full-scale farming in D1 (spec §1), and the permissive bias.
- **b. APPLICABILITY**: all Agriculture in every district. Home/Personal Agriculture is governed by this Section. Commercial Agriculture is governed by this Section and Article 7 Section 17 (the renumbered Commercial Agriculture section; confirm the number after Step 2).
- **c. PERMISSION**:
  1. Home/Personal Agriculture within Table 7.1 needs **no permit**. Article 1 Section 2.b.8 does not apply to it. The general standards of this Code still apply (spec §3.2, D1).
  2. Moving between tiers is not a change of use under Article 7 Section 1.g (spec §3.2).
  3. Commercial Agriculture keeps its Use Permit, and reaches the Planning Board only under Table 7.3 (spec §3.2).
  4. For any agricultural activity or building within this Section's by-right limits, the CEO's power to send a project to the Planning Board does not apply. That covers the district pages' "The CEO may determine…" sentence and Article 8 Sections 10.c.3 and 11.c.3 (R18).
  5. Nuisance: Article 7 Section 1.h applies to every tier, subject to the safe harbour in §3.h (R12). Reference it, don't restate it.
- **d. TIERS**: Table 7.1, in exactly this form:

```markdown
TABLE 7.1 AGRICULTURE TIERS BY DISTRICT

| Tier | Covers | Districts |
| :--- | :--- | :--- |
| Cultivation | Growing plants at any scale, and selling from the lot what is grown or made there | All districts |
| Beekeeping | Hives, registered as state law requires | All districts |
| Small Stock | As defined in Article 9 | All districts |
| Medium Stock | As defined in Article 9 | D1, D2, D3, SD-Conservation, SD-Rural Highway, SD-Campus |
| Large Stock | As defined in Article 9 | D1, D2, SD-Conservation, SD-Rural Highway, SD-Campus |
```

  Plus: no head-count cap on Medium or Large Stock (R8). The tiers are a floor, not a ceiling, for what already exists (see §3.i; spec §3.3).
- **e. SEPARATION**: Table 7.2, with the spec §3.5 rows (Cultivation · Beekeeping · Small Stock housing · Medium Stock housing · Large Stock housing · Manure Storage) and columns (From a property line · From a dwelling on another lot · By right where lot width is). Values verbatim from spec §3.5. Then the rules:
  1. Greater-of: the distance is the greater of Table 7.2 and the district's Accessory Building Placement setback.
  2. Pens, runs and paddocks take their tier's housing distance from a property line; open pasture and grazing take none (R9).
  3. Front: animal housing and manure storage meet the district's Accessory Building Placement front setback, and may not sit forward of the primary building's front façade, except in D1 and the districts mapped to it (R10).
  4. Lot-width gate for Medium and Large Stock only. Below the gate they are not prohibited: the Planning Board may approve a reduced separation of no less than half the Table 7.2 distances, on the three findings of R11. Small Stock takes no gate. On a lot too narrow for 10 ft, the district accessory setback governs. The 25 ft dwelling separation applies only where the lot is at least 50 ft wide (spec §3.5).
  5. Measuring: to a dwelling, measured to the nearest boundary of the lot containing it, as Article 7 Section 4.b.1.a measures (spec §3.5 item 3).
- **f. PLANNING BOARD REVIEW**: Table 7.3 with the six spec §3.4 triggers and thresholds, verbatim. The farm-building row reads per R13: D1 and the districts mapped to it (SD-Rural Highway, SD-Conservation) uncapped; over 5,000 sq ft in D2 and SD-Campus; 3,000 in D3; 2,000 in D4, D5, D6 and the districts mapped to D5 (SD-Historic, SD-Fabrication, SD-Highway Commercial, SD-Marine). Add a seventh row for **seasonal and unenclosed structures** (R16): over the same floor area in D3–D6 and the districts mapped to D5; no limit elsewhere. One sentence closes it: the Planning Board applies Article 8 Section 18.e to these, plus any finding this Section names.

- [ ] **Step 5: Run the tests and build the proof**

Run: `python3 -m pytest build/tests/test_right_to_farm.py -q` → Task 2's tests pass.
Run: `OUT_DIR="$TMPDIR/rtf-b2" bash build/build-standalone.sh 7 v1.2-draft` → exit 0. Check that the three tables render as tables (open the PDF at §3).

- [ ] **Step 6: Commit, then STOP for Ben**

```bash
git add source/article-07-use-standards.md build/tests/test_right_to_farm.py
git commit -m "Article 7 §3 Right to Farm, part 1: permission, tiers, separation, Board review

Inserts §3; §§3-64 renumbered to §§4-65 (<n> references updated).
Spec §§3.2-3.5; R6-R13, R16, R18.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Send Ben the Article 7 standalone PDF and the requirement trace. **Wait for approval before Task 3.**

---

### Task 3: Article 7 §3, part 2 — buildings, protection, savings, carve-outs

**Files:**
- Modify: `source/article-07-use-standards.md` (§3.g–§3.j)
- Modify: `build/tests/test_right_to_farm.py` (append)

**Interfaces:**
- Consumes: Task 2's §3.a–f; Task 1's terms.
- Produces: §3.j's activity-footprint rule and the R17 threshold. Task 5 points Articles 4 and 5's carve-outs at **Article 7 Section 3.j**.

- [ ] **Step 1: Write the failing test**

```python
SAVINGS = ("An agricultural activity lawfully conducted on the effective date of this Section may "
           "continue at its then-existing scale and location, without a permit and without becoming "
           "a nonconforming use; such an operation may enter a tier voluntarily; and nothing in this "
           "Section requires any existing building, fence, structure or manure facility to be altered.")


def test_the_savings_clause_is_verbatim():
    assert SAVINGS in " ".join(_art7().split())


def test_part_two_subsections_exist():
    sec3 = _art7().split("## 3. RIGHT TO FARM", 1)[1].split("\n## 4. ", 1)[0]
    for h in ("### g. BUILDINGS AND STRUCTURES", "### h. PROTECTION",
              "### i. EXISTING AGRICULTURE", "### j. AGRICULTURAL AREA"):
        assert h in sec3, h
```

Run → FAIL.

- [ ] **Step 2: Draft §3.g–§3.j**

- **g. BUILDINGS AND STRUCTURES**:
  1. Agricultural Buildings follow the Agricultural Building column of the district's Permitted Buildings matrix (Article 2; R13). SD-Conservation, SD-Campus and SD-Marine have no matrix. Each follows the column of its mapped district: D1, D2 and D5 respectively (R15). D6 has no Agricultural Building column; farm buildings there use its Commercial Accessory column (R14).
  2. Reconcile with the Connected Farm building group, Article 5 Section 18.b: §3 adds to it and does not limit it (spec §3.6).
  3. Hoop houses, high tunnels, trellising, fencing, temporary animal shelters and field-season equipment covers are not buildings. They are exempt from Table 5.2's area cap and from Article 5 Section 10's three-month removal rule, subject to the R16 footprint cap in D3–D6 and the districts mapped to D5, with Planning Board review above it (Table 7.3). Accessory setbacks apply everywhere.
  4. Small Stock housing and hives: permitted in every district notwithstanding Table 5.2. Limited to 100 sq ft in total per lot where Table 5.2 reads "Not Permitted" or "n/a". They count toward Table 5.2 elsewhere (R29).
- **h. PROTECTION**: spec §3.7, three numbered provisions:
  1. The declaration.
  2. The state shield, described accurately: 7 M.R.S. §154; town-wide by force of state law where agriculture is permitted; farm operations under §152(5) only; conformance determined by the Commissioner under §156. Burden per R24: the operator bears it; a written §156 determination is the showing; when conformance is disputed the CEO requests one, and enforcement on that question waits for it.
  3. The safe harbour: an activity meeting this Section's numeric standards is not a violation of Article 7 Section 1.h, Article 8 Section 18.e or Article 4 Section 12.h. It is keyed to those provisions, never to the bare word "nuisance" (spec §3.7).
- **i. EXISTING AGRICULTURE**: the savings clause **verbatim** (test above). It sits here, not in Article 8 §25 (spec §3.8).
- **j. AGRICULTURAL AREA**: the re-keying rule (spec §3.9, R17):
  1. Where this Code exempts or relaxes a standard for agriculture, it applies only to the agricultural activity and its own footprint, under Article 1 Section 2.b.6, never to a non-agricultural use on the same lot.
  2. Fence materials and crossings (Article 4 Section 8) qualify for any tier, for fencing that encloses the agricultural area itself.
  3. The field-review exemption (Article 4 Section 7), the accessory-building allowances (Article 5 Section 2.c.2.b and 2.c.3.a), and the storage and work-yard screening exemptions (Article 5 Section 18) apply only to Commercial Agriculture, Medium or Large Stock, or at least ½ acre in cultivation.

- [ ] **Step 3: Run the tests, build the proof, commit, STOP for Ben**

Run: `python3 -m pytest build/tests/test_right_to_farm.py -q` → pass (the xfail still xfails).
Run: `OUT_DIR="$TMPDIR/rtf-b3" bash build/build-standalone.sh 7 v1.2-draft` → exit 0.

```bash
git add source/article-07-use-standards.md build/tests/test_right_to_farm.py
git commit -m "Article 7 §3 Right to Farm, part 2: buildings, protection, savings, carve-outs

Spec §§3.6-3.9; R12, R14-R17, R24, R29.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Send Ben the PDF and the trace. **Wait for approval before Task 4.**

---

### Task 4: Article 7 — the existing use sections and housekeeping

**Files:**
- Modify: `source/article-07-use-standards.md` (the renumbered Commercial Agriculture, Farmstand, Farm/Vendor Market, Outdoor Storage and Stables sections, and the 15 `Section 1.G` citations)
- Modify: `build/tests/test_right_to_farm.py` (append)

- [ ] **Step 1: Write the failing test**

```python
def test_nuisance_citations_point_at_1h():
    assert "Section 1.G" not in _art7()
    assert len(re.findall(r"Nuisance Standards in Article 7 Section 1\.H", _art7())) >= 15
```

Run → FAIL. (The baseline has 15 `Article 7 Section 1.G`; verified 2026-10-13.)

- [ ] **Step 2: Edit**

1. **Commercial Agriculture**: keep the definition, and point it at Article 9's term. Replace §b.1 (the private non-commercial sentence, now governed by §3) with a pointer to Section 3. Replace §b.2 ("Mainie State Agriculture Protection Act") with a reference to §3.h's description of 7 M.R.S. §154.
2. **Farmstand**: keep the definition. Add that it is Home/Personal Agriculture (D7) and needs no permit (R19). The stand must meet Accessory Building Placement setbacks.
3. **Farm/Vendor Market**: unchanged (R25).
4. **Outdoor Storage**: add the R23 carve-out. Equipment, vehicles and materials in active agricultural use on the lot (implements in season, hay, bedding, feed, harvest bins) are not Outdoor Storage. Unused or inoperable equipment remains storage. It applies only within the agricultural area (§3.j).
5. **Stables / Riding Center**: add the equine sentence moved from Article 9 (boarding of others' horses, lessons, rides, breeding, veterinary care, races, events and shows). Add that keeping one's own horses is Large Stock under Section 3 (R20).
6. All 15 `Section 1.G` → `Section 1.H` (spec §4 housekeeping).

- [ ] **Step 3: Test, proof, commit, STOP**

Run: `python3 -m pytest build/tests/test_right_to_farm.py -q` and `OUT_DIR="$TMPDIR/rtf-b4" bash build/build-standalone.sh 7 v1.2-draft`.

```bash
git add source/article-07-use-standards.md build/tests/test_right_to_farm.py
git commit -m "Article 7: Commercial Agriculture, Farmstand, Outdoor Storage, Stables reconciled; §1.G -> §1.H

Spec §4; R19, R20, R23, R25.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Send Ben the PDF. **Wait for approval before Task 5.**

---

### Task 5: Articles 1, 4 and 5 — the consequential edits

**Files:**
- Modify: `source/article-01-general.md` (§2.b.8)
- Modify: `source/article-04-site-standards.md` (§5.b, §7.b, §8.c, §12.b)
- Modify: `source/article-05-building-standards.md` (§1.c, §2.c, §9, §10, §18)
- Modify: `build/tests/test_right_to_farm.py` (append)

- [ ] **Step 1: Write the failing test**

```python
VARIANT_PHRASES = ["agricultural activities", "agricultural uses", "commercial agricultural uses",
                   "active agricultural use", "new Commercial Agricultural uses"]


def test_the_five_variant_trigger_phrases_are_resolved():
    for f in ("article-04-site-standards.md", "article-05-building-standards.md"):
        body = (SRC / f).read_text(encoding="utf-8")
        for v in VARIANT_PHRASES:
            assert v not in body, f"{f}: {v!r}"


def test_article_1_permit_rule_carves_out_home_agriculture():
    a1 = " ".join((SRC / "article-01-general.md").read_text(encoding="utf-8").split())
    assert "except as provided in Article 7 Section 3" in a1
```

Run → FAIL.

- [ ] **Step 2: Edit**

- **Article 1 §2.b.8**: append ", except as provided in Article 7 Section 3" to the sentence "Acquisition of a permit is mandatory prior to enacting anything noted as "Permitted" in this Code" (spec §3.2).
- **Article 4 §5.b (Natural Screening)**: item 2 does not apply to agriculture meeting Article 7 Section 3 (R23).
- **Article 4 §7.b.2 (Fields)**: re-key "new Commercial Agricultural uses" to the §3.j agricultural area (R17).
- **Article 4 §8.c.6 and §8.c.7.b (Fences)**: re-key "used for agricultural activities" to fencing enclosing an agricultural area under Article 7 Section 3.j (R17).
- **Article 4 §12.b (Lighting)**: add an exemption, agricultural task lighting used only while work is underway. Permanent fixtures still meet §12.c.5 (colour temperature) and §12.g (shielding) (R22).
- **Article 5 §1.c.1.c.ii**: keep "Agricultural Building" in the list (it is now defined in Article 9).
- **Article 5 §2.c.2.b and §2.c.3.a**: re-key to Article 7 Section 3.j (R17).
- **Article 5 §9 (Additional Structures)**: add the R29 rule for Small Stock housing and hives, and the R16 seasonal-structure exemption, each by reference to Article 7 Section 3.g.
- **Article 5 §10 (Temporary Structures)**: exempt the seasonal and unenclosed structures of Article 7 Section 3.g.3 from the 3-month removal rule (R16).
- **Article 5 §18 (Building Groups)**: re-key "active agricultural use" in the outdoor-storage and work-yard screening items to Article 7 Section 3.j (R17).
- Then remove the `xfail` marker from `test_retired_terms_are_gone_and_unused` **only if** Step 2 of Task 1's grep list shows no remaining hits outside `article-02-data.json`. Task 6 handles the data's "Agricultural Use" column.

- [ ] **Step 3: Test, proofs, commit, STOP**

Run: `python3 -m pytest build/tests/test_right_to_farm.py -q`.
Run: `for n in 1 4 5; do OUT_DIR="$TMPDIR/rtf-b5" bash build/build-standalone.sh $n v1.2-draft || break; done` → all exit 0.

```bash
git add source/article-01-general.md source/article-04-site-standards.md source/article-05-building-standards.md build/tests/test_right_to_farm.py
git commit -m "Articles 1, 4, 5: Right to Farm consequential edits

Permit rule carve-out; fences, fields, screening, lighting; building count,
additional and temporary structures, building groups re-keyed to Art. 7 §3.j.
Spec §§3.2, 3.6, 3.9, 4; R16, R17, R22, R23, R29.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Send Ben the three PDFs. **Wait for approval before Task 6.**

---

### Task 6: Article 2 — the district use tables and buildings matrices

**Files:**
- Modify: `source/article-02-data.json`
- Modify: `build/tests/test_right_to_farm.py` (append; remove the remaining `xfail`)
- Modify: `build/permit-review/DECISIONS-NEEDED.md` (extend D-0035)

**Interfaces:**
- Consumes: Task 2's Table 7.1 (`tier_table()`); Plan A's `br` status.

- [ ] **Step 1: Write the failing tests**

```python
NAME_TO_LABEL = {"RURAL": "D1", "NEIGHBORHOOD RESIDENTIAL": "D2", "NEIGHBORHOOD BUSINESS": "D3",
                 "VILLAGE RESIDENTIAL": "D4", "VILLAGE BUSINESS": "D5", "TOWN CENTER": "D6",
                 "HISTORIC": "SD-Historic", "CONSERVATION": "SD-Conservation",
                 "HIGHWAY COMMERCIAL": "SD-Highway Commercial", "RURAL HIGHWAY": "SD-Rural Highway",
                 "CAMPUS": "SD-Campus", "MARINE": "SD-Marine", "FABRICATION": "SD-Fabrication"}


def _statuses(data: list) -> dict[str, dict[str, str]]:
    out = {}
    for d in data:
        cells = {}
        for col in ("use_col1", "use_col2"):
            for cat in d[col]:
                for use, status in cat["entries"]:
                    cells[use] = status
        out[NAME_TO_LABEL[d["name"]]] = cells
    return out


def _data(ref: str | None = None) -> list:
    if ref is None:
        return json.loads((SRC / "article-02-data.json").read_text(encoding="utf-8"))
    return json.loads(subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:source/article-02-data.json"],
                                     capture_output=True, text=True, check=True).stdout)


def test_tier_table_matches_the_district_tables():
    st, tiers = _statuses(_data()), tier_table()
    for tier in TIERS:
        row = f"Home Agriculture: {tier}"
        for district in DISTRICT_ORDER:
            want = "br" if district in tiers[tier] else ""
            assert st[district][row] == want, f"{district} {row}"


def test_farmstand_needs_no_permit_anywhere():
    st = _statuses(_data())
    assert {st[d]["Farmstand"] for d in DISTRICT_ORDER} == {"br"}


def test_unmoved_statuses_match_v1_0():
    now, then = _statuses(_data()), _statuses(_data("v1.0"))
    for use in ("Commercial Agriculture", "Farm/Vendor Market", "Stables/Riding Center"):
        for d in DISTRICT_ORDER:
            assert now[d][use] == then[d][use], f"{d} {use}"


def test_only_the_six_new_rows_were_added():
    now, then = _statuses(_data()), _statuses(_data("v1.0"))
    added = set(now["D1"]) - set(then["D1"])
    assert added == {"Farmstand"} | {f"Home Agriculture: {t}" for t in TIERS}
    assert all(set(now[d]) == set(now["D1"]) for d in DISTRICT_ORDER)


AG_COL = {"D1": ("CEO", "-"), "D2": ("CEO", "5,000 sf"), "D3": ("CEO", "3,000 sf"),
          "D4": ("CEO", "2,000 sf"), "D5": ("CEO", "2,000 sf"), "SD-Historic": ("CEO", "2,000 sf"),
          "SD-Highway Commercial": ("CEO", "2,000 sf"), "SD-Rural Highway": ("CEO", "-"),
          "SD-Fabrication": ("CEO", "2,000 sf")}


def test_agricultural_building_columns():
    for d in _data():
        label = NAME_TO_LABEL[d["name"]]
        m = d.get("matrix")
        cols = m["cols"] if m else []
        if label in AG_COL:
            assert "Agricultural Building" in cols, label
            i = cols.index("Agricultural Building") + 1
            rows = {r[0]: r[i] for r in m["rows"]}
            authority, floor = AG_COL[label]
            assert rows["Permitting Authority"] == authority and rows["Building Floor Area"] == floor, label
            if floor != "-":
                assert (rows["Total Stories"], rows["First Floor Height"], rows["Upper Floor Height"]) == ("2", "16 ft", "10 ft"), label
        else:
            assert "Agricultural Building" not in cols, label     # D6 (R14); no-matrix SDs (R15)
        assert "Agricultural Use" not in cols, label
```

Run → FAIL.

- [ ] **Step 2: Record the "before" Article 2 page count**

```bash
OUT_DIR="$TMPDIR/rtf-b6-before" bash build/build-standalone.sh 2 v1.2-draft >/dev/null && python3 -c "import pymupdf,glob; print(pymupdf.open(glob.glob('$TMPDIR/rtf-b6-before/*.pdf')[0]).page_count)" | tee "$TMPDIR/rtf-b6-before.count"
```

- [ ] **Step 3: Edit the data with a script, keyed by title, never by index**

`AGRICULTURAL` is in `use_col1` in all 13 districts (verified 2026-10-14). D4's `TRANSPORTATION & UTIL\xad` / `ITIES` split means category **indexes** differ in D4. Match on `title == "AGRICULTURAL"`.

```bash
python3 - <<'EOF'
import json, pathlib
p = pathlib.Path("source/article-02-data.json")
data = json.loads(p.read_text(encoding="utf-8"))
MEDIUM = {"RURAL", "NEIGHBORHOOD RESIDENTIAL", "NEIGHBORHOOD BUSINESS", "CONSERVATION", "RURAL HIGHWAY", "CAMPUS"}
LARGE = {"RURAL", "NEIGHBORHOOD RESIDENTIAL", "CONSERVATION", "RURAL HIGHWAY", "CAMPUS"}
def tier_status(tier, name):
    if tier in ("Cultivation", "Beekeeping", "Small Stock"): return "br"
    return "br" if name in (MEDIUM if tier == "Medium Stock" else LARGE) else ""
D5_COL = ["CEO", "-", "-", "2,000 sf", "2", "16 ft", "10 ft", "-"]
AG = {"NEIGHBORHOOD RESIDENTIAL": ["CEO", "-", "-", "5,000 sf", "2", "16 ft", "10 ft", "-"],
      "NEIGHBORHOOD BUSINESS":    ["CEO", "-", "-", "3,000 sf", "2", "16 ft", "10 ft", "-"],
      "VILLAGE RESIDENTIAL": D5_COL, "VILLAGE BUSINESS": D5_COL, "HISTORIC": D5_COL,
      "HIGHWAY COMMERCIAL": D5_COL, "FABRICATION": D5_COL,
      "RURAL HIGHWAY": ["CEO", "-", "-", "-", "-", "-", "-", "-"]}
for d in data:
    cats = [c for c in d["use_col1"] if c["title"] == "AGRICULTURAL"]
    assert len(cats) == 1, d["name"]
    e = cats[0]["entries"]
    e.append(["Farmstand", "br"])
    for t in ("Cultivation", "Beekeeping", "Small Stock", "Medium Stock", "Large Stock"):
        e.append([f"Home Agriculture: {t}", tier_status(t, d["name"])])
    # Appended in this order on purpose: Farmstand sorts after Farm/Vendor Market
    # (the last existing row), and the tiers stay in tier order, not alphabetical (R27).
    m = d.get("matrix")
    if m and "Agricultural Use" in m["cols"]:
        m["cols"][m["cols"].index("Agricultural Use")] = "Agricultural Building"
    elif m and d["name"] in AG:
        m["cols"].append("Agricultural Building")
        assert [r[0] for r in m["rows"]] == ["Permitting Authority", "Building Width", "Building Depth",
            "Building Floor Area", "Total Stories", "First Floor Height", "Upper Floor Height", "Number of Units"], d["name"]
        for r, v in zip(m["rows"], AG[d["name"]]): r.append(v)
p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")   # the file's own format, no trailing newline (verified 2026-10-14)
EOF
git diff --stat source/article-02-data.json
```

The dump arguments reproduce the file byte for byte (checked 2026-10-14: `indent=1`, `ensure_ascii=False`, no trailing newline). If `git diff --stat` shows a whole-file rewrite, the format has changed since: restore with `git checkout source/article-02-data.json`, find the arguments that round-trip the file unchanged, and rerun.

Remove the `xfail` marker from `test_retired_terms_are_gone_and_unused`.

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest build/tests/test_right_to_farm.py build/tests/test_status_br_typst.py build/tests/test_use_table_changes.py -q` → all pass.

- [ ] **Step 5: Check that every district page fits**

```bash
OUT_DIR="$TMPDIR/rtf-b6-after" bash build/build-standalone.sh 2 v1.2-draft >/dev/null && python3 -c "import pymupdf,glob; print(pymupdf.open(glob.glob('$TMPDIR/rtf-b6-after/*.pdf')[0]).page_count)" > "$TMPDIR/rtf-b6-after.count"; diff "$TMPDIR/rtf-b6-before.count" "$TMPDIR/rtf-b6-after.count" && echo SAME
python3 -c "
import pymupdf,glob
d=pymupdf.open(glob.glob('$TMPDIR/rtf-b6-after/*.pdf')[0])
for i,p in enumerate(d):
    t=p.get_text()
    if 'USE TABLE LEGEND' in t or 'PERMITTED BUILDINGS' in t: p.get_pixmap(dpi=80).save(f'$TMPDIR/rtf-b6-p{i+1:03}.png')
"
```
Expected: `SAME`. Open every PNG. In each, the six new rows show in column 1 with ○ where Table 7.1 says, and the use row labels are not clipped. The matrices of D5, SD-Highway Commercial, SD-Rural Highway and SD-Fabrication show six columns, legible and inside the margins. **If anything overflows, clips or wraps badly, stop and report** with the page images. Rebalancing columns or narrowing a matrix is a layout call for Ben.

- [ ] **Step 6: The permit app — record, don't re-pin**

Run: `(cd build/permit-review && .venv/bin/python -m pytest -q 2>&1 | tail -15)`.
Expected failures, by design: `build_use_matrix` refuses the `br` cells (D-0035) and the use count of 69 (it requires 63). Some tests read the working tree's counts (release spec P17: `test_use_matrix.py`, `test_parse_definitions.py`, `test_edition_rollover.py`). **Do not re-pin or loosen them** (release spec P17, "Breaks loudly"). Append to D-0035 in `build/permit-review/DECISIONS-NEEDED.md` a dated paragraph: the failing test names, quoted from the run. State that they are owed to the app plan, which must (a) model `br`, (b) accept 69 uses, and (c) decide whether its tests read the binding ruleset's source (v1.0) or the working tree.

- [ ] **Step 7: Run the full build suite**

Run: `python3 -m pytest build/tests -q` (15–20 min; a subagent may run it and return the summary line and any failure output).
Expected: all pass. Any failure: read it. A test asserting a v1.0 fact from the tag is untouched by this plan and must still pass. A test asserting the **working tree's** Article 2 or Article 7 shape needs a decision: convert it to an invariant, per release spec P17. Report it to Ben before changing it.

- [ ] **Step 8: Commit, then STOP for Ben**

```bash
git add source/article-02-data.json build/tests/test_right_to_farm.py build/permit-review/DECISIONS-NEEDED.md
git commit -m "Article 2: Right to Farm rows and Agricultural Building columns in the 13 districts

Six AGRICULTURAL rows (Farmstand; Home Agriculture tiers) per Table 7.1;
Agricultural Building column in D2-D5 and the mapped SDs; D1's column renamed.
Commercial Agriculture, Farm/Vendor Market, Stables unchanged. Page count
unchanged: <n>. App tests owed to the app plan, recorded in D-0035.
R13-R15, R19, R25, R27, R28.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Send Ben the Article 2 standalone PDF. **Wait for approval before Task 7.**

---

### Task 7: The v1.2-draft proof release

Uses the **czc-release skill** procedure. Builds into a scratch directory, never `releases/`, until Ben says go.

**Files:**
- Create: `$TMPDIR/rtf-calls.json` (not committed until the real release)
- Create (scratch): the proof release under `$TMPDIR/rtf-release/`

- [ ] **Step 1: Plan only**

```bash
bash build/build-release.sh v1.2-draft "<today, Month D, YYYY>" --old-ver=v1.1-draft --plan-only
```
Expected: substantive Articles **1, 2, 4, 5, 7, 9**, the Use Table Changes document, and Article 2 listed as **NEEDS-CALL** (`article-02.typ` changed in Plan A). Any other Article listed as substantive (e.g. 8 or 3): stop and report what changed in it. It should be untouched.

- [ ] **Step 2: Write the call for Article 2**

`$TMPDIR/rtf-calls.json` (the reason is printed in the Summary: write it for residents):

```json
{"calls": [{"article": 2, "decision": "substantive",
  "reason": "The use-table legend gains a fifth symbol, an open circle meaning no permit is required, and the district tables gain rows for farm stands and home agriculture.",
  "by": "Ben Frey, Planning Board Chair"}]}
```

- [ ] **Step 3: Build the proof release**

```bash
bash build/build-release.sh v1.2-draft "<date>" --old-ver=v1.1-draft --calls "$TMPDIR/rtf-calls.json" --out-dir "$TMPDIR/rtf-release"
```
Expected: exit 0; `release_gate.py` passes. Note the integrated page count and the redline's.

- [ ] **Step 4: Hand-write the Summary of Changes**

Replace the generated skeleton `Summary of Changes v1.2-draft.md` in the proof directory. Plain language, no file names (czc-release skill). It must include:
1. What Right to Farm does, by tier and district (from Table 7.1).
2. **The §154 trade, in plain words** (spec §3.7.2, mandatory): permitting agriculture switches on the state's shield for farm operations that follow best management practices. Example: a cattle farm following those practices may use barbed wire, which Article 4 otherwise bans.
3. The new ○ symbol and what it means.
4. What reaches the Planning Board (Table 7.3).
5. The savings clause, in one sentence.
6. Renumbering: Article 7 §§3–64 are now §§4–65.
7. Not in this amendment: seasonal farm-worker housing, a planned follow-up (R21).
8. Before adoption: the Town must send the proposed ordinance to the Maine Department of Agriculture at least 90 days before the hearing or meeting that considers it (7 M.R.S. §155; spec §6). Open questions are with Town counsel.

Render: `bash build/build-memo.sh "<…Summary….md>" "<…Summary….pdf>" "Summary of Changes — v1.2-draft" "Newcastle Core Zoning Code · <date>"`.

- [ ] **Step 5: Read the proof, then STOP for Ben**

Check, and report each with evidence:
- The integrated PDF opens; Article 7 §3 is in the table of contents; the redline marks §3 as added and shows the 63 renumbered headings as renumbering, not change (spec §5.1).
- The Use Table Changes document lists the legend change first, then the six rows × 13 districts and the matrix columns, in words, no glyphs.
- No page claims adoption; the cover reads draft.

Send Ben the integrated PDF, the redline, the Summary and the Use Table Changes (`SendUserFile`). **Stop.** Committing `releases/v1.2-draft/`, merging to `main`, tagging and pushing are Ben's call. They follow the whole-branch review in "After Plan B".

---

## After Plan B

1. **One fresh-context review of the whole `right-to-farm` branch** (Plans A and B) against the spec and R1–R29, before anything merges (CLAUDE.md "Review").
2. On Ben's go: PR `right-to-farm` → `main`; after the merge, cut the real release on `main` with the czc-release skill (same calls file), commit `releases/v1.2-draft/` records, tag `v1.2-draft` (annotated), and push `main` and the tag as **separate commands** (rule 6).
3. Not in this plan: the permit-review app's handling of `br` and 69 uses (D-0035); counsel's questions (spec §7); the DACF submission (a clerk's act, 7 M.R.S. §155).
