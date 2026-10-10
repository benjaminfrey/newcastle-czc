"""build/use_table_changes.py -- the Use Table Changes document.

Article 2's thirteen district pages are rendered from data; the redline shows
them unmarked. This document is the only place their changes are listed item
by item. Counts come from real tags or from trees materialised from v1.0.
"""
import json
import shutil
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
