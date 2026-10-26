"""fees.yaml is the Town's Planning Fee Schedule as of 2025.08.25, line for line (projects brief §7)."""

from portal_api.forms.definitions import load_definitions
from portal_api.forms.fees import load_fees
from portal_api.ruleset import load_ruleset

# The brief's §7 table, as printed on the schedule.
SCHEDULE = {
    "USE PERMIT": (30, {"Basic Use": 0, "Residential Companion Use": 0, "Expanded Use": 60, "Special": 60,
                        "Shoreland Use (CEO rev)": 0, "Shoreland Use (PB rev)": 60}),
    "BUILDING PERMIT": (30, {"Small Project Plan": 0, "Small Project Plan Revisions": 0, "Large Project Plan": 240,
                             "Large Project Plan Revisions": 100, "Structure": 30, "Entrances": 0,
                             "Demolition of Historic Assets": 0, "Floodplain Management": 60, "Mobile Home Park": 60,
                             "Tower": 500, "Power Generation": {"per_sf": 0.10}, "Erosion & Sediment Control": 60}),
    "SUBDIVISION (PERMIT)": (300, {"Subdivision (Major)": 0, "Master Plan": 1000}),
    "SIGN PERMIT": (30, {"Sign": 0, "Shoreland Sign": 30}),
    "PLUMBING PERMIT": ("varies", {"Plumbing (interior)": "varies", "Subsurface Wastewater": "varies",
                                   "Tank Only": "varies"}),
    "ACTIVITY PERMIT": (30, {"Tourist Rentals Annual Registration": 70, "Temporary Structure": 0,
                             "Shoreland Vegetation Removal": 60}),
    "OTHER": (None, {"Zoning Variance": 300, "Administrative Appeal": 300}),
}


def test_fees_yaml_matches_the_schedule():
    fees = load_fees()
    got = {p.schedule_name: (p.application_fee, {r.name: r.fee for r in p.reviews}) for p in fees.permits}
    assert got == SCHEDULE
    assert fees.source["as_of"] == "2025-08-25" and fees.source["read_on"] == "2026-10-25"
    assert fees.source["url"] == "https://drive.google.com/file/d/1f2ZNZcp0ESJU3uDRK7aEFEooCpzGo5uB/view"
    assert fees.status == "approved" and fees.approved_on == "2026-10-25"


def test_every_review_maps_to_a_fee_line():
    fees = load_fees()
    keys = set(load_definitions(load_ruleset()).applications) | {"structure"}
    assert set(fees.review_map) == keys
    for key in keys:
        permit, review = fees.line(key)
        assert review in permit.reviews


def test_the_briefs_mapping():
    fees = load_fees()
    named = {k: (fees.line(k)[0].schedule_name, fees.line(k)[1].name) for k in fees.review_map}
    assert named == {
        "small_project_plan": ("BUILDING PERMIT", "Small Project Plan"),
        "large_project_plan": ("BUILDING PERMIT", "Large Project Plan"),
        "use_permit": ("USE PERMIT", "Basic Use"),
        "residential_companion": ("USE PERMIT", "Residential Companion Use"),
        "expanded_use": ("USE PERMIT", "Expanded Use"),
        "special_permit": ("USE PERMIT", "Special"),
        "subdivision": ("SUBDIVISION (PERMIT)", "Subdivision (Major)"),
        "entrance_permit": ("BUILDING PERMIT", "Entrances"),
        "structure": ("BUILDING PERMIT", "Structure"),
    }
