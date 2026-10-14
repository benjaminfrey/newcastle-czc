"""Right to Farm (specs/2026-10-07-right-to-farm-design.md; decisions in
plans/2026-10-14-right-to-farm-decisions.md). Facts that must agree across
Articles, pinned so a later edit to one Article cannot silently contradict
another."""
import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "source"

NEW_TERMS = [
    "Agriculture", "Home/Personal Agriculture", "Commercial Agriculture",
    "Small Stock", "Medium Stock", "Large Stock", "Farmstand", "Greenhouse",
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


def test_new_terms_sit_alphabetically_between_their_neighbours():
    """Only the new terms: the adopted Article 9 already has 24 out-of-order
    pairs (e.g. 'Abutting' before 'Abutter'), which this amendment does not
    reorder."""
    terms = _terms()
    for t in NEW_TERMS:
        i = terms.index(t)
        before = terms[i - 1].lower() if i > 0 else ""
        after = terms[i + 1].lower() if i + 1 < len(terms) else "￿"
        assert before <= t.lower() <= after, f"{t!r} sits between {terms[i-1]!r} and {terms[i+1]!r}"


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


def test_the_legend_note_cites_the_right_to_farm_section():
    """Article 2's legend Note sends ○ uses to "Article 7 Section 3" (Plan A,
    R3). That section must be Right to Farm, or the Note points at whatever
    use section sits third (review of Plan A, finding 4)."""
    typ = (SRC / "article-02.typ").read_text(encoding="utf-8")
    assert "must meet the standards of Article 7 Section 3." in typ
    assert re.search(r"^## 3\. RIGHT TO FARM$", _art7(), flags=re.M)


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


def test_nuisance_citations_point_at_1h():
    assert "Section 1.G" not in _art7()
    assert len(re.findall(r"Nuisance Standards in Article 7 Section 1\.H", _art7())) >= 15


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
