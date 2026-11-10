"""Slots, filled from the standards (library plan 1, task 2)."""

import dataclasses

import pytest
import yaml

from portal_api.library import LibraryError, load_library
from portal_api.library.render import entry_for, render, standard_key, number
from portal_api.standards import standards_for

STORIES = {"stories": {"standard": "building:total_stories", "part": "max"}}


def _stories(**k):
    e = load_library().entries["how_stories_count"]
    return dataclasses.replace(e, answer="At most {stories}.", slots=STORIES, standards=("building:total_stories",), **k)


def test_standard_keys():
    by = {s.key: standard_key(s) for s in standards_for("d1")}
    assert by["d1/building/Residential/total_stories"] == "building:total_stories"
    assert by["d1/dimension/primary_building_placement.side_setback"] == "dimension:primary_building_placement.side_setback"


def test_numbers_read_as_people_say_them():
    assert number(2.0, "stories") == "2 stories" and number(1.0, "stories") == "1 story"
    assert number(8000.0, "sf") == "8,000 sq ft" and number(15.0, "ft") == "15 ft"
    assert number(1.0, "units") == "1 unit" and number(2.5, "ft") == "2.5 ft"


def test_total_stories_fills_from_the_district():
    r = render(_stories(), "d1", "Residential")
    assert r.answer == "At most 2 stories."
    assert r.detail == load_library().entries["how_stories_count"].detail


def test_an_unestablished_value_does_not_render():
    assert render(_stories(), "d1", "Agricultural Use") is None      # Total Stories is "-" there
    assert render(_stories(), "d1", "No Such Building") is None


def test_an_override_value_carries_its_note():
    e = dataclasses.replace(load_library().entries["setbacks"], answer="At least {side}.",
                            slots={"side": {"standard": "dimension:primary_building_placement.side_setback", "part": "min"}})
    r = render(e, "d6", None)
    assert r.answer == "At least 0 ft."
    assert len(r.interpretations) == 1 and r.interpretations[0].startswith("Decided by Ben Frey, Planning Board chair on 2026-11-02")
    assert render(e, "d1", None).interpretations == ()               # D1's 15 ft is the Code's own


def test_raw_fills_the_text():
    e = dataclasses.replace(load_library().entries["use_table"], answer="Reviewed by the {who}.",
                            slots={"who": {"standard": "building:permitting_authority", "part": "raw"}})
    assert render(e, "d1", "Residential").answer == "Reviewed by the CEO."


def test_a_district_note_joins_the_detail():
    e = dataclasses.replace(_stories(), district_notes={"d1": "In D1 a barn may be taller."})
    assert render(e, "d1", "Residential").detail.endswith(" In D1 a barn may be taller.")
    assert "barn" not in render(e, "d2", "Residential").detail


def _add(data, **e):
    base = {k: v for k, v in data["entries"][0].items() if k not in ("picture", "picture_alt")}
    data["entries"].append({**base, "id": "extra", **e})


def test_a_placeholder_without_a_slot_is_refused(lib):
    with pytest.raises(LibraryError, match="extra: no slot for {stories}"):
        load_library(lib("guide", lambda d: _add(d, answer="At most {stories}.")))


def test_a_slot_naming_no_standard_is_refused(lib):
    root = lib("guide", lambda d: _add(d, answer="At most {s}.", slots={"s": {"standard": "building:wings", "part": "max"}}))
    with pytest.raises(LibraryError, match="extra: slot s: no standard building:wings"):
        load_library(root)


def test_a_slot_part_must_be_known(lib):
    root = lib("guide", lambda d: _add(d, answer="At most {s}.", slots={"s": {"standard": "building:total_stories", "part": "most"}}))
    with pytest.raises(LibraryError, match="part"):
        load_library(root)


def test_a_claimed_standard_must_exist(lib):
    with pytest.raises(LibraryError, match="no standard building:wings"):
        load_library(lib("guide", lambda d: _add(d, standards=["building:wings"])))


def test_two_entries_cannot_claim_one_standard(lib):
    def both(d):
        _add(d, standards=["building:total_stories"])
        next(e for e in d["entries"] if e["id"] == "setbacks")["standards"] = ["building:total_stories"]
    with pytest.raises(LibraryError, match="building:total_stories is claimed by both"):
        load_library(lib("guide", both))


def test_entry_for_finds_the_claim(lib):
    root = lib("guide", lambda d: _add(d, standards=["building:total_stories"]))
    assert entry_for(load_library(root), "building:total_stories").id == "extra"
    assert entry_for(load_library(root), "building:building_width") is None


def _range(**slot):
    e = load_library().entries["setbacks"]
    return dataclasses.replace(e, answer="Keep {side} from the side.", slots={"side": slot})


def test_a_range_reads_as_people_say_it():
    side = {"standard": "dimension:primary_building_placement.side_setback", "part": "range"}
    assert render(_range(**side), "d1", None).answer == "Keep at least 15 ft from the side."
    assert render(_range(**side), "d6", None).answer == "Keep between 0 and 5 ft from the side."
    stories = {"standard": "building:total_stories", "part": "range"}
    assert render(_range(**stories), "d1", "Residential").answer == "Keep at most 2 stories from the side."


def test_a_slot_may_name_the_same_standard_under_another_key():
    keys = ["dimension:primary_building_placement.side_setback", "dimension:building_placement.side_setback"]
    districts = {s.district_key for s in standards_for_all() if s.field == "building_placement.side_setback"}
    assert districts, "some district names its placement fields building_placement.*"
    d = sorted(districts)[0]
    assert render(_range(standard=keys, part="range"), d, None) is not None
    assert render(_range(standard=keys[:1], part="range"), d, None) is None


def standards_for_all():
    from portal_api.standards import load_standards
    return load_standards()
