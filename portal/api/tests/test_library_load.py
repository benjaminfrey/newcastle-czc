"""The explanation library's files, their statuses and the live rule (library plan 1, task 1)."""

import dataclasses
import shutil
from datetime import date
from pathlib import Path

import pytest
import yaml

import portal_api.library.load as ll
from portal_api.guide.content import load_content
from portal_api.library import LibraryError, is_live, load_library


@pytest.fixture
def lib(tmp_path):
    """A writable copy of the library, and a way to change one batch."""
    for f in ll.DIR.glob("*.yaml"):
        shutil.copy(f, tmp_path / f.name)

    def edit(batch: str, change) -> Path:
        path = tmp_path / f"{batch}.yaml"
        data = yaml.safe_load(path.read_text())
        change(data)
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        return tmp_path
    return edit


def _entry(data: dict, entry_id: str) -> dict:
    return next(e for e in data["entries"] if e["id"] == entry_id)


def test_the_four_entries_load_from_the_library():
    lib = load_library()
    assert set(lib.entries) == {"how_stories_count", "setbacks", "use_table", "use_not_listed"}
    e = lib.entries["how_stories_count"]
    assert e.answer == "Only floors with full-height outside walls count."
    assert e.kind == "standard" and e.batch == "guide" and e.picture == "stories"
    assert e.status == "approved" and e.approved_by == "Ben Frey, Planning Board chair"
    assert str(e.approved_on) == "2026-11-06"
    assert load_content().entries["setbacks"].cites == ("2.3.c.3",)
    assert len(lib.digest) == 64


def test_an_unknown_key_is_refused(lib):
    root = lib("guide", lambda d: _entry(d, "setbacks").update(colour="red"))
    with pytest.raises(LibraryError, match="guide: setbacks: unknown key colour"):
        load_library(root)


def test_every_cite_resolves(lib):
    root = lib("guide", lambda d: _entry(d, "setbacks")["cites"].append("99.1.a"))
    with pytest.raises(LibraryError, match="guide: setbacks"):
        load_library(root)


def test_a_picture_needs_its_description(lib):
    root = lib("guide", lambda d: _entry(d, "how_stories_count").pop("picture_alt"))
    with pytest.raises(LibraryError, match="picture_alt"):
        load_library(root)


def test_ids_are_unique_across_batches(lib, tmp_path):
    (tmp_path / "other.yaml").write_text(yaml.safe_dump({"entries": [
        yaml.safe_load((ll.DIR / "guide.yaml").read_text())["entries"][0]], "open_questions": []}))
    with pytest.raises(LibraryError, match="duplicate id"):
        load_library(tmp_path)


@pytest.mark.parametrize("missing", ["approved_by", "approved_on", "ratified_on", "ratified_by"])
def test_ratified_needs_approval_and_a_date(lib, missing):
    def ratify(d):
        _entry(d, "setbacks").update(status="ratified", ratified_on="2026-12-01", ratified_by="Planning Board")
        _entry(d, "setbacks").pop(missing)
    with pytest.raises(LibraryError, match=missing):
        load_library(lib("guide", ratify))


def test_ratified_by_is_the_board(lib):
    root = lib("guide", lambda d: _entry(d, "setbacks").update(
        status="ratified", ratified_on="2026-12-01", ratified_by="the chair"))
    with pytest.raises(LibraryError, match="Planning Board"):
        load_library(root)


@pytest.mark.parametrize("missing", ["pulled_on", "pulled_by", "pulled_why"])
def test_pulled_needs_who_when_and_why(lib, missing):
    def pull(d):
        _entry(d, "setbacks").update(status="pulled", pulled_on="2026-12-01", pulled_by="Ben Frey",
                                     pulled_why="The number is wrong")
        _entry(d, "setbacks").pop(missing)
    with pytest.raises(LibraryError, match=missing):
        load_library(lib("guide", pull))


@pytest.mark.parametrize("missing", ["decided_by", "decided_on", "source"])
def test_interpretation_needs_who_decided_when_and_source(lib, missing):
    def interpret(d):
        _entry(d, "use_table").update(kind="interpretation", decided_by="Code Enforcement Officer",
                                      decided_on="2026-05-01", source="CEO determination, May 2026")
        _entry(d, "use_table").pop(missing)
    with pytest.raises(LibraryError, match=missing):
        load_library(lib("guide", interpret))


@pytest.mark.parametrize("key,value", [("kind", "essay"), ("status", "live")])
def test_an_unknown_kind_or_status_is_refused(lib, key, value):
    with pytest.raises(LibraryError, match=f"{key} must be one of"):
        load_library(lib("guide", lambda d: _entry(d, "setbacks").update({key: value})))


@pytest.mark.parametrize("field", ["overline", "answer", "detail", "why", "picture_alt"])
def test_never_words_are_refused_in_every_field(lib, field):
    root = lib("guide", lambda d: _entry(d, "how_stories_count").update({field: "Your house is approved."}))
    with pytest.raises(LibraryError, match="never-used word"):
        load_library(root)


def test_live_rule():
    e = load_library().entries["setbacks"]          # approved 2026-11-06: before the library's design
    r = lambda **k: dataclasses.replace(e, **k)     # noqa: E731
    assert not is_live(r(status="draft"))
    assert is_live(e)
    assert not is_live(r(approved_on=date(2026, 11, 8)))
    assert is_live(r(status="ratified", ratified_on=date(2026, 12, 1), ratified_by="Planning Board"))
    assert not is_live(r(status="ratified"), pulled=frozenset({"setbacks"}))
    assert not is_live(e, pulled=frozenset({"setbacks"}))
    assert not is_live(r(status="pulled"))


def test_a_file_may_list_open_questions(lib):
    root = lib("guide", lambda d: d.update(open_questions=["D3: the Code gives no rear setback."]))
    assert load_library(root).open_questions["guide"] == ("D3: the Code gives no rear setback.",)


def test_the_guide_reads_its_entries_from_a_given_library(lib):
    root = lib("guide", lambda d: _entry(d, "setbacks").update(answer="Changed for the test."))
    assert load_content(library_root=root).entries["setbacks"].answer == "Changed for the test."
