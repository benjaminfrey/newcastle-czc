"""Tests ruleset_build/{legend,build_use_matrix}.py and app/reviews.py against
CONTRACT.md §4.3/§4.4.

Offline, no network, no LLM, no PII — reads only source/article-02*.{json,typ}
and the use-matrix.json this test builds into a throwaway temp directory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))

from ruleset_build.build_use_matrix import UseMatrixBuildError, build_use_matrix  # noqa: E402
from ruleset_build.legend import EXPECTED_LEGEND, LegendParseError, parse_legend  # noqa: E402

SRC = REPO_ROOT / "source" / "article-02-data.json"
LEGEND_TYP = REPO_ROOT / "source" / "article-02.typ"

KNOWN_STATUS_VALUES = {"u", "rc", "sp", "ex", ""}


@pytest.fixture(scope="module")
def legend_typ_text() -> str:
    return LEGEND_TYP.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def matrix() -> dict:
    return build_use_matrix(SRC, LEGEND_TYP, "adopted")


@pytest.fixture(scope="module")
def use_matrix_path(tmp_path_factory, matrix) -> Path:
    """Writes the built matrix to a throwaway dir and points RULESETS_DIR at
    it via the PERMIT_REVIEW-style pattern app.reviews expects: rulesets/
    <key>/use-matrix.json under app.config.RULESETS_DIR. We monkeypatch that
    constant directly rather than touching the real committed file."""
    d = tmp_path_factory.mktemp("rulesets") / "adopted"
    d.mkdir(parents=True)
    path = d / "use-matrix.json"
    path.write_text(json.dumps(matrix), encoding="utf-8")
    return path.parent.parent  # the rulesets/ dir


# --------------------------------------------------------------------------- #
# legend.py
# --------------------------------------------------------------------------- #


def test_legend_parses_from_the_typ_file(legend_typ_text):
    rows = parse_legend(legend_typ_text)
    assert len(rows) == 5  # u, rc, sp, ex, ""
    assert {r["code"] for r in rows} == KNOWN_STATUS_VALUES


def test_legend_matches_the_documented_mapping(legend_typ_text):
    rows = parse_legend(legend_typ_text)
    by_code = {r["code"]: r for r in rows}
    for expected in EXPECTED_LEGEND:
        actual = by_code[expected["code"]]
        for key, value in expected.items():
            assert actual[key] == value, f"{expected['code']!r}.{key}"


def test_legend_raises_loudly_if_heading_is_missing():
    with pytest.raises(LegendParseError):
        parse_legend("this text has no USE TABLE LEGEND anywhere in it")


def test_legend_raises_loudly_if_a_required_code_is_missing():
    broken = """
    #let glyphs = (u: "●", rc: "❶", sp: "❷", ex: "✪")
    USE TABLE LEGEND
    status("u"), [Use Permit Required], [CEO],
    status("rc"), [Residential Companion Permit Required], [CEO],
    status("sp"), [Special Permit Required], [Planning Board],
    Note: Uses without #status("u"), #status("rc"), #status("sp"), or #status("ex") are not allowed in this District]
    """
    with pytest.raises(LegendParseError):
        parse_legend(broken)


# --------------------------------------------------------------------------- #
# build_use_matrix.py
# --------------------------------------------------------------------------- #


def test_cell_count_is_819(matrix):
    assert matrix["counts"]["cells"] == 819
    assert len(matrix["cells"]) == 819
    assert matrix["counts"]["districts"] == 13
    assert matrix["counts"]["uses"] == 63


def test_cell_count_by_code_matches_contract(matrix):
    assert matrix["counts"]["by_code"] == {"u": 218, "rc": 53, "sp": 58, "ex": 40, "": 450}


def test_every_cell_status_is_one_of_the_five_known_values(matrix):
    codes = {cell["code"] for cell in matrix["cells"]}
    assert codes == KNOWN_STATUS_VALUES


def test_cells_are_dense_across_all_districts_and_uses(matrix):
    seen = {(c["district_key"], c["use_key"]) for c in matrix["cells"]}
    expected = {
        (d, u["use_key"]) for d in matrix["district_keys"] for u in matrix["uses"]
    }
    assert seen == expected


def test_d4_soft_hyphen_categories_are_merged(matrix):
    titles = {c["title"] for c in matrix["categories"]}
    assert "TRANSPORTATION & UTILITIES" in titles
    assert not any(t.endswith("\xad") for t in titles)
    assert len(matrix["categories"]) == 7


def test_d1_residence_is_use_permit_ceo(matrix):
    residence = next(u for u in matrix["uses"] if u["use_key"] == "residence")
    cell = next(
        c
        for c in matrix["cells"]
        if c["district_key"] == "d1" and c["use_key"] == residence["use_key"]
    )
    assert cell["code"] == "u"
    assert cell["permit"] == "Use Permit"
    assert cell["authority"] == "CEO"
    assert cell["allowed"] is True


def test_a_prohibited_cell_has_no_authority(matrix):
    prohibited = next(c for c in matrix["cells"] if c["code"] == "")
    assert prohibited["permit"] is None
    assert prohibited["permit_key"] == "prohibited"
    assert prohibited["authority"] is None
    assert prohibited["authority_key"] is None
    assert prohibited["allowed"] is False


def test_build_fails_loudly_on_a_district_count_mismatch(tmp_path):
    bad = tmp_path / "article-02-data.json"
    bad.write_text(json.dumps(json.loads(SRC.read_text())[:5]), encoding="utf-8")
    with pytest.raises(AssertionError):
        build_use_matrix(bad, LEGEND_TYP, "adopted")


def test_build_fails_loudly_on_an_unknown_status_code(tmp_path):
    districts = json.loads(SRC.read_text())
    districts[0]["use_col1"][0]["entries"][0][1] = "zz"  # not a legend code
    bad = tmp_path / "article-02-data.json"
    bad.write_text(json.dumps(districts), encoding="utf-8")
    with pytest.raises(UseMatrixBuildError):
        build_use_matrix(bad, LEGEND_TYP, "adopted")


# --------------------------------------------------------------------------- #
# app/reviews.py
# --------------------------------------------------------------------------- #


@pytest.fixture()
def reviews_module(use_matrix_path, monkeypatch):
    import app.config as config

    monkeypatch.setattr(config, "RULESETS_DIR", use_matrix_path)
    import app.reviews as reviews

    monkeypatch.setattr(reviews, "RULESETS_DIR", use_matrix_path)
    reviews._load_use_matrix.cache_clear()
    yield reviews
    reviews._load_use_matrix.cache_clear()


def test_required_reviews_d1_residence_is_use_permit_ceo(reviews_module):
    rows = reviews_module.required_reviews("d1", "Residence")
    assert len(rows) == 1
    row = rows[0]
    assert row["permit"] == "Use Permit"
    assert row["permitting_authority"] == "CEO"
    assert row["applicability_text"] == (
        "A Residence use in the D1-Rural District requires a Use Permit "
        "which can be issued by the CEO."
    )


def test_required_reviews_matches_by_use_key_and_by_label(reviews_module):
    by_key = reviews_module.required_reviews("d1", "residence")
    by_label = reviews_module.required_reviews("d1", "Residence")
    assert by_key == by_label


def test_required_reviews_prohibited_use_has_no_authority(reviews_module):
    rows = reviews_module.required_reviews("d1", "Paid Parking Lot")
    assert len(rows) == 1
    row = rows[0]
    assert row["permit"] is None
    assert row["permitting_authority"] is None
    assert row["applicability_text"] == "A Paid Parking Lot use is not allowed in the D1-Rural District."


def test_required_reviews_unknown_district_raises(reviews_module):
    with pytest.raises(reviews_module.UnknownDistrict):
        reviews_module.required_reviews("d99", "Residence")


def test_required_reviews_unknown_use_raises(reviews_module):
    with pytest.raises(reviews_module.UnknownUse):
        reviews_module.required_reviews("d1", "Not A Real Use")


# --------------------------------------------------------------------------- #
# Indefinite article ("a Use Permit" vs "an Expanded Use Permit")
# --------------------------------------------------------------------------- #


def test_indefinite_article_is_correct_for_every_label_in_the_adopted_ruleset() -> None:
    """The article is chosen by SOUND, and the vocabulary is closed, so pin all
    of it. Before this was added the worksheet printed "A Adult Establishment
    use ..." and "requires a Expanded Use Permit" on every render.

    If a future ruleset adds a word the rule gets wrong, this test fails rather
    than the error reaching a document in front of the Board.
    """
    from app.citation import indefinite_article

    # The four permit labels in the adopted use matrix.
    assert indefinite_article("Use Permit") == "a"          # yoo-, NOT "an"
    assert indefinite_article("Expanded Use Permit") == "an"
    assert indefinite_article("Special Permit") == "a"
    assert indefinite_article("Residential Companion Permit") == "a"

    # Every vowel-initial use label in the adopted ruleset.
    expect_an = [
        "Adult Establishment", "Amusement, Indoor", "Amusement, Outdoor",
        "Animal Care, Indoor", "Animal Care, Outdoor", "Aquaculture", "Assembly",
        "Industrial, Artisan", "Industrial, General", "Industrial, Heavy",
        "Office, Large", "Office, Medium", "Office, Small", "Outdoor Storage",
    ]
    for label in expect_an:
        assert indefinite_article(label) == "an", label

    # ...except the one that is pronounced "yoo-tilities".
    assert indefinite_article("Utilities & Services") == "a"

    # A consonant-initial sample, and the degenerate input.
    assert indefinite_article("Residence") == "a"
    assert indefinite_article("") == "a"
