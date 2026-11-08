"""The Board's memo for a batch (library plan 1, task 9)."""

from portal_api.library import load_library
from portal_api.library.memo import render_memo


def test_the_memo_lists_every_entry_and_the_open_questions():
    lib = load_library()
    md = render_memo(lib, "article-02", "2026-11-08")
    assert md.startswith("# MEMORANDUM\n") and "**Date:** November 8, 2026" in md
    for e in lib.entries.values():
        if e.batch == "article-02":
            assert f"## {e.overline}" in md, e.id
    for q in lib.open_questions["article-02"]:
        assert q in md
    assert md.count("Draft, not yet approved") == 18


def test_the_memo_fills_each_district_and_marks_the_towns_reading():
    md = render_memo(load_library(), "article-02", "2026-11-08")
    assert "| D1 - Rural | Residential | The building has at most 2 stories. *(the Town's reading)* |" in md
    assert "| D6 - Town Center | — | Your building sits between 0 and 5 ft from each side lot line. *(the Town's reading)* |" in md


def test_the_memo_shows_goes_to_the_town_where_a_value_is_missing():
    md = render_memo(load_library(), "article-02", "2026-11-08")
    assert "| D1 - Rural | Agricultural Use | Goes to the Town |" in md
