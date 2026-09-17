"""The v1.0 adoption rollover (Town Meeting, September 14, 2026).

After the vote the app holds two adopted Codes: the one adopted November 3, 2020
(`rulesets/adopted`, eight articles, now superseded) and CZC v1.0
(`rulesets/adopted-v1.0`, nine articles, current). These tests pin what that
has to mean: new work is held to v1.0, the 2020 Code's citations do not move,
and v1.0's ruleset is exactly the text the voters adopted.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from app import citation, rulesets
from app.citation import Citation, NoCounterpart

APP = Path(__file__).resolve().parent.parent
REPO = APP.parent.parent
RULESETS = APP / "rulesets"


def _manifest(key: str) -> dict:
    return json.loads((RULESETS / key / "manifest.json").read_text(encoding="utf-8"))


# --- which Code governs ------------------------------------------------------

def test_new_work_is_held_to_v1_0():
    assert rulesets.current_binding_key() == "adopted-v1.0"


def test_the_2020_code_is_superseded_not_removed():
    old = _manifest("adopted")
    assert old["binding"] is True
    assert old["status"] == "superseded"
    assert old["superseded_by"]["ruleset_key"] == "adopted-v1.0"
    assert old["superseded_by"]["on"] == "2026-09-14"
    assert old["adopted_on"] == "2020-11-03"
    for name in ("articles.json", "use-matrix.json", "districts.json", "clocks.json", "criteria-subdivision.json"):
        assert (RULESETS / "adopted" / name).exists(), name


def test_two_active_codes_refuse_rather_than_guess(tmp_path, monkeypatch):
    for key in ("a", "b"):
        (tmp_path / key).mkdir()
        (tmp_path / key / "manifest.json").write_text(json.dumps({"binding": True, "status": "active"}))
    monkeypatch.setattr(rulesets, "RULESETS_DIR", tmp_path)
    with pytest.raises(rulesets.RulesetNotFound):
        rulesets.current_binding_key()


# --- v1.0 is the text the voters adopted -------------------------------------

def test_v1_0_manifest_records_the_adoption_and_its_provenance():
    m = _manifest("adopted-v1.0")
    assert (m["binding"], m["status"], m["article_scheme"], m["adopted_on"]) == (True, "active", "adopted-v1.0", "2026-09-14")
    assert m["supersedes"]["ruleset_key"] == "adopted"
    tree = subprocess.run(["git", "-C", str(REPO), "rev-parse", "v1.0:source"],
                          capture_output=True, text=True, check=True).stdout.strip()
    assert m["provenance"]["tag"] == "v1.0"
    assert m["provenance"]["source_tree"] == tree


def test_v1_0_has_every_artifact_the_app_loads():
    for name in ("manifest.json", "articles.json", "definitions.json", "uses.json", "use-matrix.json",
                 "districts.json", "clocks.json", "criteria-subdivision.json"):
        assert (RULESETS / "adopted-v1.0" / name).exists(), name
    rs = rulesets.load_ruleset("adopted-v1.0")
    assert (len(rs.districts_by_key), len(rs.uses_by_key), len(rs.cells_by_pair)) == (13, 63, 819)


def test_v1_0_use_matrix_requires_both_permits_in_d3():
    cell = rulesets.load_ruleset("adopted-v1.0").cells_by_pair[("d3", "retail_service_general")]
    assert [(r["permit"], r["authority"]) for r in cell["reviews"]] == [
        ("Residential Companion Permit", "CEO"), ("Special Permit", "Planning Board")]


def test_v1_0_clocks_and_criteria_cite_article_8():
    clocks = json.loads((RULESETS / "adopted-v1.0" / "clocks.json").read_text())
    assert clocks["article_scheme"] == "adopted-v1.0"
    assert {c["citation"]["article"] for c in clocks["clocks"]} == {8}
    crit = json.loads((RULESETS / "adopted-v1.0" / "criteria-subdivision.json").read_text())
    assert crit["criteria_set"]["citation"]["article"] == 8
    rules = {r["standard_letter"]: r for r in crit["rules"]}
    assert len(rules) == 21
    assert rules["b"]["source_text"] == "The standards of Article 3 Thoroughfares."
    assert {r["citation"]["scheme"] for r in crit["rules"]} == {"adopted-v1.0"}


def test_v1_0_quotes_its_own_text_even_where_it_differs_from_2020():
    """Standard s reads "phosphorous" in the adopted v1.0 text where the 2020
    Code read "phosphorus". The ruleset quotes the Code as adopted; correcting
    adopted text is the Board's call, not the builder's."""
    crit = json.loads((RULESETS / "adopted-v1.0" / "criteria-subdivision.json").read_text())
    s = next(r for r in crit["rules"] if r["standard_letter"] == "s")
    assert "phosphorous concentration" in s["source_text"]


# --- the 2020 Code's citations do not move -----------------------------------

def test_a_2020_citation_renders_exactly_as_before():
    c = Citation("adopted", "adopted", 7, section="12", standard_letter="n", standard_title="Flood Areas")
    assert citation.render_citation(c, scheme="adopted") == "Article 7, Section 12, Standard n. (Flood Areas)"
    assert citation.article_name("adopted", 3) == "Site Standards"


def test_v1_0_numbering_and_names():
    assert citation.to_scheme(7, frm="adopted", to="adopted-v1.0") == 8
    assert citation.to_scheme(8, frm="adopted-v1.0", to="draft") == 8
    assert citation.article_name("adopted-v1.0", 3) == "Thoroughfares"
    assert citation.article_name("adopted-v1.0", 9) == "Definitions"
    with pytest.raises(NoCounterpart):
        citation.to_scheme(3, frm="adopted-v1.0", to="adopted")
    assert citation.scheme_for_ruleset("adopted-v1.0") == "adopted-v1.0"
    assert citation.scheme_for_ruleset("adopted") == "adopted"


# --- the DB accepts the new numbering ----------------------------------------

def test_migrations_admit_an_adopted_edition_scheme_and_nothing_else(tmp_path):
    from app.config import MIGRATIONS_DIR
    from app.db import connect, migrate

    conn = connect(tmp_path / "t.db")
    migrate(conn, MIGRATIONS_DIR)
    row = ("x", "k1", "l", 1, "adopted-v1.0", "2026-09-14", "t", "b", "m", "{}", 0, None, "t", None)
    conn.execute("INSERT INTO rulesets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?);", row)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO rulesets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?);",
                     ("y", "k2", "l", 1, "bogus", None, "t", "b", "m", "{}", 0, None, "t", None))
    conn.close()


# --- the builder refuses what it cannot build faithfully ---------------------

def test_build_edition_refuses_a_scheme_with_no_map():
    from ruleset_build import build_edition

    with pytest.raises(build_edition.EditionBuildError, match="no numbering map"):
        build_edition.build(tag="v1.0", adopted_on="2026-09-14", key="adopted-v9.9", supersedes="adopted-v1.0")
