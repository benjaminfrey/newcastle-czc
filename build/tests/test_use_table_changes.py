"""build/use_table_changes.py -- the Use Table Changes document.

Article 2's thirteen district pages are rendered from data; the redline shows
them unmarked. This document is the only place their changes are listed item
by item. Counts come from real tags or from trees materialised from v1.0.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import use_table_changes as utc  # noqa: E402

REPO = BUILD.parent
TYP = "article-02.typ"


def _typ(ref: str = "v1.0") -> str:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:source/{TYP}"],
                          capture_output=True, text=True, check=True).stdout


def test_the_legend_is_read():
    leg = utc.parse_legend(_typ())
    assert leg["rows"] == {
        "u": ("Use Permit Required", "CEO"),
        "rc": ("Residential Companion Permit Required", "CEO"),
        "sp": ("Special Permit Required", "Planning Board"),
        "ex": ("Expanded Use Permit Required", "Planning Board"),
    }
    assert leg["glyphs"] == {"u": "●", "rc": "❶", "sp": "❷", "ex": "✪"}
    assert leg["note"] == "Note: Uses without u, rc, sp, or ex are not allowed in this District"


def test_this_reader_agrees_with_the_permit_review_apps():
    """Two readers of one legend block (ruling 12). This test is the only thing
    that keeps them together: never skip or xfail it."""
    sys.path.insert(0, str(REPO / "build" / "permit-review"))
    from ruleset_build.legend import parse_legend as app_parse_legend
    text = _typ()
    ours, app = utc.parse_legend(text), app_parse_legend(text)
    app_rows = {r["code"]: r for r in app if r["code"]}
    assert set(ours["rows"]) == set(app_rows) == {"u", "rc", "sp", "ex"}
    for code, (label, authority) in ours["rows"].items():
        assert label == app_rows[code]["permit"] + " Required"
        assert authority == app_rows[code]["authority"]
        assert ours["glyphs"][code] == app_rows[code]["glyph"]
    app_note = next(r["note"] for r in app if not r["code"])
    assert ours["note"].removeprefix("Note: ").rstrip(".") == app_note.rstrip(".")


def test_an_unchanged_legend_has_no_delta_and_a_changed_one_does():
    old = utc.parse_legend(_typ())
    assert utc.legend_delta(old, utc.parse_legend(_typ())) == []
    new = utc.parse_legend(_typ().replace("[Special Permit Required], [Planning Board]",
                                          "[Special Exception Required], [Board of Appeals]", 1))
    delta = utc.legend_delta(old, new)
    assert any("Special Exception Required" in s for s in delta)
    assert any("Board of Appeals" in s for s in delta)


def test_a_missing_legend_is_refused():
    with pytest.raises(utc.LegendError):
        utc.parse_legend("#let x = 1\n")


def test_status_words():
    leg = utc.parse_legend(_typ())
    assert utc.status_words("", leg) == "Not allowed"
    assert utc.status_words("rc sp", leg) == \
        "Residential Companion Permit (CEO) + Special Permit (Planning Board)"
    assert utc.status_words("zz", leg) == "`zz` (not in the legend)"


# --- fix round 1: a legend change is never silent -------------------------------

ROW_U = 'status("u"), [Use Permit Required], [CEO],'
NOTE_END = 'are not allowed in this District]'


def _rewrapped(text: str, note: bool = True) -> str:
    """Every run of spaces inside the legend rows (and the Note, if asked) becomes
    a newline plus indentation: the same legend, laid out differently."""
    head = text.index("USE TABLE LEGEND")
    end = text.index(NOTE_END) + len(NOTE_END)
    seg = "\n".join(re.sub(r"(?<=\S) +(?=\S)", "\n          ", ln)
                    if (("Note:" in ln and note) or ("Note:" not in ln and 'status("' in ln)) else ln
                    for ln in text[head:end].split("\n"))
    return text[:head] + seg + text[end:]


def _delta_or_refusal(old_text: str, new_text: str) -> list[str]:
    """A change must surface either as a non-empty delta or as a refusal."""
    try:
        new = utc.parse_legend(new_text)
    except utc.LegendError as e:
        return [f"refused: {e}"]
    return utc.legend_delta(utc.parse_legend(old_text), new)


def test_a_fifth_row_in_another_form_is_never_silent():
    text = _typ()
    ex_row = 'status("ex"), [Expanded Use Permit Required], [Planning Board],'
    assert ex_row in text
    edited = text.replace(ex_row, ex_row + '\n        status("zz"), [Zoning Permit Required], [CEO]', 1)
    edited = edited.replace('ex: "✪")', 'ex: "✪", zz: "◆")', 1)
    assert edited != text
    assert _delta_or_refusal(text, edited)


def test_a_clause_added_to_the_note_is_reported():
    text = _typ()
    assert NOTE_END in text
    edited = text.replace(NOTE_END, NOTE_END[:-1] + " except as provided in Section 3]", 1)
    delta = utc.legend_delta(utc.parse_legend(text), utc.parse_legend(edited))
    assert delta and any("except as provided in Section 3" in s for s in delta)


def test_a_rewrap_is_not_a_change():
    text = _typ()
    wrapped = _rewrapped(text)
    assert wrapped != text and "\n          " in wrapped
    old, new = utc.parse_legend(text), utc.parse_legend(wrapped)
    assert utc.legend_delta(old, new) == []
    assert not utc.legend_block_changed(old, new)
    # the agreement test, again, on rewrapped rows. (The app's Note regex needs
    # single spaces in "Uses without", so the Note is left unwrapped here: the app
    # refuses a rewrapped Note loudly, which is a difference but not a silent one.)
    rows_only = _rewrapped(text, note=False)
    assert rows_only != text
    sys.path.insert(0, str(REPO / "build" / "permit-review"))
    from ruleset_build.legend import parse_legend as app_parse_legend
    app_rows = {r["code"]: r for r in app_parse_legend(rows_only) if r["code"]}
    assert utc.parse_legend(rows_only)["rows"] == new["rows"]
    assert set(new["rows"]) == set(app_rows)
    for code, (label, authority) in new["rows"].items():
        assert label == " ".join(app_rows[code]["permit"].split()) + " Required"
        assert authority == " ".join(app_rows[code]["authority"].split())


def test_glyphs_and_rows_must_name_the_same_codes():
    edited = _typ().replace(', ex: "✪"', "", 1)
    assert edited != _typ()
    with pytest.raises(utc.LegendError, match="ex"):
        utc.parse_legend(edited)


def test_a_duplicate_code_is_refused():
    text = _typ()
    dup = text.replace(ROW_U, ROW_U + "\n        " + ROW_U, 1)
    assert dup != text
    with pytest.raises(utc.LegendError, match="`u`"):
        utc.parse_legend(dup)


def test_added_removed_and_glyph_changes_are_itemised():
    old = utc.parse_legend(_typ())
    no_ex = _typ().replace(', ex: "✪"', "", 1)
    no_ex = re.sub(r'\n[ \t]*status\("ex"\)[^\n]*', "", no_ex, count=1)
    assert 'status("ex")' not in no_ex.split("USE TABLE LEGEND")[1].split("Note:")[0]
    gone = utc.parse_legend(no_ex)
    assert any("`ex` removed" in s for s in utc.legend_delta(old, gone))
    assert any("`ex` added" in s for s in utc.legend_delta(gone, old))
    glyph = utc.legend_delta(old, utc.parse_legend(_typ().replace('u: "●"', 'u: "○"', 1)))
    assert any("symbol for `u` changed" in s and "●" in s and "○" in s for s in glyph)


def test_an_unitemisable_change_falls_back_to_the_block():
    """A change in the legend table's layout that no field captures still surfaces."""
    text = _typ()
    old = utc.parse_legend(text)
    marker = "columns: (auto, 1fr, auto), stroke: none,"
    assert marker in text
    new = utc.parse_legend(text.replace(marker, "columns: (auto, 2fr, auto), stroke: none,", 1))
    assert old["block"] != new["block"]
    delta = utc.legend_delta(old, new)
    assert len(delta) == 1 and "cannot itemise" in delta[0]
    assert utc.legend_block_changed(old, new)
