"""The baseline->current article correspondence.

Without this, build-redline-full.sh resolves the old side of each diff by
filename and finds nothing for 8 of 9 articles -- rendering the entire Code as
newly written in the document that goes to Town Meeting. See ADOPTION-SPEC.md §1.1.
"""
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402


def test_every_renamed_article_resolves_to_its_baseline_path():
    m = adoption_map.load()
    cases = {
        "article-01-general.md": "article-01-general.md",
        "article-04-site-standards.md": "article-03-site-standards.md",
        "article-05-building-standards.md": "article-04-building-standards.md",
        "article-06-design-standards.md": "article-05-design-standards.md",
        "article-07-use-standards.md": "article-06-use-standards.md",
        "article-08-administration.md": "article-07-administration.md",
        "article-09-definitions.md": "article-08-definitions.md",
        "article-02-prefatory.md": "article-02-districts.md",
    }
    for current, baseline in cases.items():
        assert m.baseline_path_for(current) == baseline, current


def test_article_3_is_new_and_says_so_rather_than_erroring():
    m = adoption_map.load()
    assert m.baseline_path_for("article-03-streets-roads-driveways.md") is None


def test_an_unknown_file_raises_rather_than_silently_reading_as_new():
    """The failure that motivated this module: an unmapped file must NOT
    quietly become an empty old-side and render as 100% new."""
    m = adoption_map.load()
    try:
        m.baseline_path_for("article-99-invented.md")
    except KeyError as exc:
        assert "article-99-invented.md" in str(exc)
    else:
        raise AssertionError("an unmapped article must raise, not return None")


def test_renumber_rewrites_cross_references():
    m = adoption_map.load()
    assert m.renumber("See Article 7 and Article 3.") == "See Article 8 and Article 4."
    assert m.renumber("Article 1 and Article 2 are unchanged.") == \
        "Article 1 and Article 2 are unchanged."
