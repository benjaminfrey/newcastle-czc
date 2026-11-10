"""The draft checks: the reading grade and Article 9's defined terms (library plan 1, task 3)."""

import dataclasses
import shutil
from pathlib import Path

import pytest

from portal_api.library import LibraryError, load_library
from portal_api.library.readability import flags, grade
from portal_api.library.terms import TERMS_FILE, article_9_terms


def test_short_plain_text_is_low_grade():
    assert grade("Only floors with full-height outside walls count.") < 8


def test_a_long_legal_sentence_is_flagged():
    legal = ("Notwithstanding any provision hereinabove enumerated, an applicant intending the construction "
             "of an accessory dwelling necessitating extraordinary dimensional accommodation shall additionally "
             "demonstrate conformity with every applicable regulatory determination previously promulgated by "
             "the municipality and its designated administrative authorities.")
    assert grade(legal) > 8
    e = dataclasses.replace(load_library().entries["setbacks"], detail=legal)
    assert any(f.startswith("grade ") for f in flags(e, article_9_terms()))


def test_terms_are_left_out_of_the_grade():
    text = "An Accessory Dwelling Unit counts."
    assert grade(text, frozenset({"Accessory Dwelling Unit"})) < grade(text)


def test_numbers_are_left_out_of_the_grade():
    assert grade("Keep 15 ft back.") == grade("Keep ft back.")


def test_a_known_term_is_not_flagged_and_an_unknown_one_is():
    terms = article_9_terms()
    assert "accessory building" in terms
    e = dataclasses.replace(load_library().entries["setbacks"], terms=("Accessory Building", "Moon Base"))
    assert flags(e, terms) == ("term not in Article 9: Moon Base",)


def test_the_four_entries_carry_their_flags():
    lib = load_library()
    assert set(lib.flags) <= set(lib.entries) | {"library"}


def test_a_changed_definitions_file_is_refused(tmp_path):
    bad = tmp_path / "definitions.json"
    shutil.copy(TERMS_FILE, bad)
    bad.write_bytes(bad.read_bytes().replace(b"Abandoned", b"Abandonee", 1))
    with pytest.raises(LibraryError, match="does not match the pinned ruleset"):
        article_9_terms(bad)


def test_without_the_file_the_terms_check_is_skipped(tmp_path):
    assert article_9_terms(tmp_path / "missing.json") is None


def test_a_shallow_install_has_no_terms_file_and_still_loads():
    """In the API's container the package sits at /app/portal_api: there is no repo above it."""
    from portal_api.library.terms import terms_file
    assert terms_file(Path("/app/portal_api/library/terms.py")) is None
    deep = Path("/home/x/newcastle-czc/portal/api/portal_api/library/terms.py")
    assert terms_file(deep) == Path("/home/x/newcastle-czc/build/permit-review/rulesets/adopted-v1.0/definitions.json")
    assert article_9_terms(None) is None
