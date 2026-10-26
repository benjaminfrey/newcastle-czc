"""What a project needs (projects brief §6–§8): the screener's rules run on the project's parts,
priced from the Town's fee schedule, timed by the Code's clocks. Runs the real rules.yaml,
applications.yaml and fees.yaml."""

from datetime import date

import pytest

from portal_api.forms.definitions import load_definitions
from portal_api.forms.fees import load_fees
from portal_api.forms.needs import due_date, needs
from portal_api.forms.parts import load_parts
from portal_api.forms.screener import run
from portal_api.ruleset import load_ruleset

RULESET = load_ruleset()
DEFS = load_definitions(RULESET)
FACTS = {"districts": [{"code": "D2", "name": "Neighborhood Residential"}], "on_state_highway": False}


def project(*parts, answers=None, facts=FACTS, locked_on=None):
    """parts: kinds, or (kind, {field: value}) for a part's own answers; answers: project-level."""
    rows, all_answers = [], {(k, None): v for k, v in (answers or {}).items()}
    for i, p in enumerate(parts):
        kind, own = (p, {}) if isinstance(p, str) else p
        pid = f"{kind}-{i}"
        rows.append({"id": pid, "kind": kind, "position": i})
        for f, v in own.items():
            repeat = load_parts().get(kind).repeats
            all_answers[(f, pid if repeat else None)] = v
    return needs(rows, all_answers, facts, RULESET, DEFS, load_fees(), load_parts(), locked_on=locked_on)


def reviews(n):
    return {(r["review_key"], r.get("use_key"), r["certainty"]) for p in n["permits"] for r in p["reviews"]}


def permit(n, key):
    return next(p for p in n["permits"] if p["key"] == key)


def test_building_and_driveway_is_one_building_permit():
    n = project(("building", {"floor_area": 2400, "dwelling_units": 1}), "driveway",
                answers={"homes_last_5_years": 0})
    assert [p["key"] for p in n["permits"]] == ["use_permit", "building_permit"]  # a home is the Residence use
    b = permit(n, "building_permit")
    assert b["application_fee"] == 30 and b["name"] == "Building Permit"
    assert [(r["name"], r["fee"]) for r in b["reviews"]] == [("Small Project Plan", 0), ("Structure", 30), ("Entrances", 0)]
    assert n["application_fees_total"] == 60


def test_two_new_buildings_two_structures_one_application_fee():
    n = project(("building", {"floor_area": 1200, "dwelling_units": 0}), ("building", {"floor_area": 600, "dwelling_units": 0}))
    b = permit(n, "building_permit")
    assert [r["name"] for r in b["reviews"]] == ["Small Project Plan", "Structure", "Structure"]
    assert sum(r["fee"] for r in b["reviews"]) == 60 and b["application_fee"] == 30
    assert n["application_fees_total"] == 30


def test_one_large_one_small_building():
    n = project(("building", {"floor_area": 12000, "dwelling_units": 0}), ("building", {"floor_area": 800, "dwelling_units": 0}))
    keys = [r["review_key"] for r in permit(n, "building_permit")["reviews"]]
    assert keys.count("small_project_plan") == 1 and keys.count("large_project_plan") == 1


def test_needed_beats_may_need():
    # A building of unknown size may need either plan; a known small one needs the small plan.
    n = project(("building", {"floor_area": {"unknown": True}, "dwelling_units": 0}),
                ("building", {"floor_area": 900, "dwelling_units": 0}))
    assert ("small_project_plan", None, "needed") in reviews(n)
    assert ("small_project_plan", None, "may_need") not in reviews(n)
    assert ("large_project_plan", None, "may_need") in reviews(n)


def test_new_homes_are_summed_across_buildings():
    n = project(("building", {"floor_area": 1500, "dwelling_units": 2}), ("building", {"floor_area": 900, "dwelling_units": 1}),
                answers={"homes_last_5_years": 0})
    assert ("subdivision", None, "needed") in reviews(n)


def test_two_uses_two_use_reviews_one_fee():
    cells = RULESET.cells
    uses = [u for (d, u), c in cells.items() if d == "d2" and c["code"] == "u"][:2]
    n = project(("use", {"proposed_uses": uses}))
    u = permit(n, "use_permit")
    assert [r["use_key"] for r in u["reviews"]] == uses
    assert u["application_fee"] == 30 and n["application_fees_total"] == 30


def test_driveway_only_pays_the_building_permit():
    n = project("driveway")
    assert [(p["key"], p["application_fee"], [(r["name"], r["fee"]) for r in p["reviews"]]) for p in n["permits"]] == \
        [("building_permit", 30, [("Entrances", 0)])]
    assert n["application_fees_total"] == 30


def test_varies_never_shows_a_number():
    from portal_api.forms.needs import fee_words
    assert fee_words("varies") == "Set by the Town Office"
    assert fee_words(0) == "No permit fee" and fee_words(30) == "$30" and fee_words({"per_sf": 0.10}) == "$0.10 a square foot"


def test_civic_land_is_town_only():
    n = project("driveway", facts={"districts": [{"code": "SD-Civic"}], "on_state_highway": False})
    assert n["town_only"] is True and n["permits"] == [] and n["application_fees_total"] == 0


def test_off_portal_reviews_say_so():
    n = project(("divide", {"lots_after": 4, "divided_last_5_years": "no"}))
    (r,) = permit(n, "subdivision")["reviews"]
    assert r["in_portal"] is False and r["reviewer"] == "Planning Board"


def test_clocks_read_plainly_and_date_only_after_the_lock():
    n = project(("building", {"floor_area": 900, "dwelling_units": 0}))
    spp = next(r for r in permit(n, "building_permit")["reviews"] if r["review_key"] == "small_project_plan")
    (clock,) = spp["clocks"]
    assert clock["plain"] == "The Code Enforcement Officer decides within 10 days of accepting your project."
    assert "due" not in clock
    n = project(("building", {"floor_area": 900, "dwelling_units": 0}), locked_on=date(2026, 10, 28))
    spp = next(r for r in permit(n, "building_permit")["reviews"] if r["review_key"] == "small_project_plan")
    assert spp["clocks"][0]["due"] == "2026-11-07" and spp["clocks"][0]["due_words"] == "Decision due by November 7"


def test_every_clock_sentence_states_the_rulesets_days():
    for app in DEFS.applications.values():
        assert set(app.clock_plain) == set(app.clock_keys), app.key
        for k, entry in app.clock_plain.items():
            assert f" {RULESET.clocks[k]['days']} " in entry["text"], (app.key, k)
            assert entry["status"] in ("draft", "approved")


@pytest.mark.parametrize("start,days,basis,want", [
    (date(2026, 10, 28), 10, "calendar", (date(2026, 11, 7), False)),     # across a month end
    (date(2026, 12, 20), 30, "calendar", (date(2027, 1, 19), False)),     # across a year end
    (date(2026, 10, 30), 7, "business", (date(2026, 11, 10), True)),      # Fri + 7 business days, "about"
    (date(2026, 8, 31), 6, "months", (date(2027, 2, 28), False)),         # month end clamps
])
def test_due_dates(start, days, basis, want):
    got = due_date(start, days, basis)
    assert got == want and got[0] > start


# Every rule family: the screener's answers and an equivalent project name the same applications.
SAME = [
    ({"project": ["build"], "building": {"kind": "new", "gross_floor_area_sf": 800, "new_dwelling_units": 0}},
     [("building", {"floor_area": 800, "dwelling_units": 0})], {}),
    ({"project": ["build"], "building": {"kind": "new", "gross_floor_area_sf": 20000, "new_dwelling_units": 0}},
     [("building", {"floor_area": 20000, "dwelling_units": 0})], {}),
    ({"project": ["build"], "building": {"kind": "new", "new_dwelling_units": 0}},
     [("building", {"floor_area": {"unknown": True}, "dwelling_units": 0})], {}),
    ({"project": ["build"], "building": {"kind": "addition", "gross_floor_area_sf": 400}},
     [("addition", {"added_floor_area": 400})], {}),
    ({"project": ["build"], "building": {"kind": "addition", "gross_floor_area_sf": 14000}},
     [("addition", {"added_floor_area": 14000})], {}),
    ({"project": ["build"], "building": {"kind": "addition"}}, [("addition", {})], {}),
    ({"project": ["build"], "building": {"kind": "renovation", "total_floor_area_sf": 4000}},
     [("renovation", {"renovation_total_floor_area": 4000})], {}),
    ({"project": ["build"], "building": {"kind": "renovation", "total_floor_area_sf": 15000}},
     [("renovation", {"renovation_total_floor_area": 15000})], {}),
    ({"project": ["build"], "building": {"kind": "site", "parking_spaces": 10}}, [("site", {"parking_spaces": 10})], {}),
    ({"project": ["build"], "building": {"kind": "site", "parking_spaces": 60}}, [("site", {"parking_spaces": 60})], {}),
    ({"project": ["build"], "building": {"kind": "site"}}, [("site", {})], {}),
    ({"project": ["build"], "building": {"kind": "new", "gross_floor_area_sf": 3000, "new_dwelling_units": 3}},
     [("building", {"floor_area": 3000, "dwelling_units": 3})], {"homes_last_5_years": 0}),
    ({"project": ["build"], "building": {"kind": "new", "gross_floor_area_sf": 3000, "new_dwelling_units": 1,
                                         "homes_added_last_5_years": 2}},
     [("building", {"floor_area": 3000, "dwelling_units": 1})], {"homes_last_5_years": 2}),
    ({"project": ["build"], "building": {"kind": "new", "gross_floor_area_sf": 3000, "new_dwelling_units": 1}},
     [("building", {"floor_area": 3000, "dwelling_units": 1})], {}),
    ({"project": ["divide"], "division": {"lots_after": 4}}, [("divide", {"lots_after": 4})], {}),
    ({"project": ["divide"], "division": {"lots_after": 2, "divided_last_5_years": False}},
     [("divide", {"lots_after": 2, "divided_last_5_years": "no"})], {}),
    ({"project": ["divide"], "division": {"lots_after": 2, "divided_last_5_years": True}},
     [("divide", {"lots_after": 2, "divided_last_5_years": "yes"})], {}),
    ({"project": ["divide"], "division": {"lots_after": 2}}, [("divide", {"lots_after": 2, "divided_last_5_years": "unsure"})], {}),
    ({"project": ["divide"]}, [("divide", {})], {}),
    ({"project": ["driveway"]}, ["driveway"], {}),
    ({"project": ["other"]}, ["other"], {}),
    ({"project": ["use"], "use_key": "residence"}, [("use", {"proposed_uses": ["residence"]})], {}),
    ({"project": ["use"]}, ["use"], {}),
]


@pytest.mark.parametrize("screener,parts,answers", SAME)
def test_same_outcomes_as_the_screener(screener, parts, answers):
    s = {"property": {"district_codes": ["D2"], "on_state_highway": False, "civic": False}, **screener}
    s.setdefault("building", {})
    s.setdefault("division", {})
    old = run(s, RULESET, DEFS)
    want = {(o["application"], o["certainty"]) for o in old["outcomes"]}
    n = project(*parts, answers=answers)
    got = {(k, c) for k, _, c in reviews(n) if k != "structure"}
    assert got == want
    assert {x["text"] for x in n["notes"]} == {x["text"] for x in old["notes"]}


def test_needs_are_refused_while_any_rule_is_a_draft():
    from portal_api.forms.needs import drafts
    assert drafts(DEFS, load_fees()) == [d for d in drafts(DEFS, load_fees())]  # callable, lists entries
    import dataclasses
    rules = [dataclasses.replace(DEFS.rules[0], status="draft"), *DEFS.rules[1:]]
    with_draft = dataclasses.replace(DEFS, rules=rules)
    assert any("rules.yaml" in d for d in drafts(with_draft, load_fees()))


def test_fees_due_at_send_leave_out_what_may_not_apply():
    # Lots after unknown: Subdivision may be needed, and the Town Office takes it. Its $300 isn't
    # "payable when you send" (the whole-branch review, finding 5).
    n = project(("divide", {"lots_after": {"unknown": True}}))
    (sub,) = n["permits"]
    assert sub["key"] == "subdivision" and sub["due_at_send"] is False
    assert n["application_fees_total"] == 0
    n = project("driveway")
    assert n["permits"][0]["due_at_send"] is True and n["application_fees_total"] == 30
