"""The record: decisions written into the library's files, and the Board's ratification (task 6)."""

from datetime import date

import pytest

from portal_api.library import is_live, load_library
from portal_api.library.write import CHAIR_NAME, apply, dump_batch, ratify, read_batch

CHAIR = "chair@example.com"
CEO = "ceo@example.com"
PEOPLE = {CEO: "the Code Enforcement Officer"}
TEXTS = {"overline": "Why · how far from the lot lines", "answer": "Keep back from each lot line.",
         "detail": "Measure from the lot line.", "why": "Room between neighbors."}


def _d(entry_id, action, version=1, by=CHAIR, did=1, body=None, note=None, at="2026-11-20T15:00:00+00:00"):
    return {"id": did, "entry_id": entry_id, "version": version, "action": action, "body": body, "note": note,
            "decided_at": at, "decided_by_email": by}


def _pull(entry_id, version=1, by=CEO, why="The number is wrong"):
    return {"entry_id": entry_id, "version": version, "why": why, "pulled_at": "2026-11-21T15:00:00+00:00",
            "pulled_by_email": by}


def _apply(root, decisions=(), pulls=(), superseded=()):
    return apply(root, {"decisions": list(decisions), "pulls": list(pulls), "superseded": list(superseded)},
                 chair=CHAIR, people=PEOPLE)


def _set(root, entry_id, **fields):
    path = root / "guide.yaml"
    entries, questions = read_batch(path)
    next(e for e in entries if e["id"] == entry_id).update(fields)
    dump_batch(path, entries, questions)


def _draft(root, entry_id):
    path = root / "guide.yaml"
    entries, questions = read_batch(path)
    e = next(e for e in entries if e["id"] == entry_id)
    e["status"] = "draft"
    e.pop("approved_by")
    e.pop("approved_on")
    dump_batch(path, entries, questions)


def test_round_trip_is_byte_stable(lib):
    root = lib("guide", lambda d: None)
    from portal_api.library.load import DIR
    before = (DIR / "guide.yaml").read_bytes()
    entries, questions = read_batch(root / "guide.yaml")
    dump_batch(root / "guide.yaml", entries, questions)
    assert (root / "guide.yaml").read_bytes() == before


def test_apply_approves(lib):
    root = lib("guide", lambda d: None)
    _draft(root, "setbacks")
    r = _apply(root, [_d("setbacks", "approve")])
    assert r["applied"] == ["setbacks"] and r["refused"] == [] and r["exported_decisions"] == [1]
    e = load_library(root).entries["setbacks"]
    assert (e.status, e.approved_by, e.approved_on) == ("approved", CHAIR_NAME, date(2026, 11, 20))
    assert not is_live(e)                       # approved after 2026-11-08: it waits for the Board


def test_only_the_chair_approves(lib):
    root = lib("guide", lambda d: None)
    r = _apply(root, [_d("setbacks", "approve", by=CEO)])
    assert r["refused"] == [["setbacks", "only the chair approves"]]


def test_an_edit_makes_a_new_draft_version(lib):
    root = lib("guide", lambda d: None)
    r = _apply(root, [_d("setbacks", "edit", body=TEXTS, note="Shorter")])
    e = load_library(root).entries["setbacks"]
    assert r["applied"] == ["setbacks"]
    assert (e.version, e.status, e.answer, e.approved_by, e.review_note) == (2, "draft", TEXTS["answer"], None, "Shorter")


def test_two_edits_bump_the_version_once(lib):
    """`decisions` gives the last unexported decision per entry; the earlier one is exported with it."""
    root = lib("guide", lambda d: None)
    later = dict(TEXTS, answer="The second edit.")
    r = _apply(root, [_d("setbacks", "edit", body=later, did=2)], superseded=[1])
    e = load_library(root).entries["setbacks"]
    assert (e.version, e.answer) == (2, "The second edit.")
    assert sorted(r["exported_decisions"]) == [1, 2]


def test_send_back_keeps_the_note(lib):
    root = lib("guide", lambda d: None)
    _apply(root, [_d("use_table", "send_back", note="Say which permit.")])
    e = load_library(root).entries["use_table"]
    assert (e.status, e.review_note, e.approved_on) == ("draft", "Say which permit.", None)


def test_apply_refuses_a_stale_decision(lib):
    root = lib("guide", lambda d: None)
    _set(root, "setbacks", version=2)
    _draft(root, "use_table")
    r = _apply(root, [_d("setbacks", "approve", version=1, did=1), _d("use_table", "approve", did=2)])
    assert r["refused"] == [["setbacks", "stale: the file is at version 2"]] and r["applied"] == ["use_table"]
    assert r["exported_decisions"] == [2]


def test_apply_will_not_approve_a_pulled_entry(lib):
    root = lib("guide", lambda d: None)
    r = _apply(root, [_d("setbacks", "approve")], pulls=[_pull("setbacks")])
    assert r["refused"] == [["setbacks", "pulled at this version: edit it first"]]
    e = load_library(root).entries["setbacks"]
    assert (e.status, e.pulled_by, e.pulled_why) == ("pulled", "the Code Enforcement Officer", "The number is wrong")
    assert r["exported_pulls"] == ["setbacks"]


def test_approving_a_fixed_version_clears_its_pull(lib):
    root = lib("guide", lambda d: None)
    _apply(root, pulls=[_pull("setbacks")])
    _apply(root, [_d("setbacks", "edit", body=TEXTS, did=1)])
    r = _apply(root, [_d("setbacks", "approve", version=2, did=2)])
    assert r["applied"] == ["setbacks"] and r["cleared_pulls"] == ["setbacks"]
    e = load_library(root).entries["setbacks"]
    assert (e.status, e.version, e.pulled_on) == ("approved", 2, None)


def test_a_pull_by_someone_unknown_is_refused(lib):
    root = lib("guide", lambda d: None)
    r = _apply(root, pulls=[_pull("setbacks", by="stranger@example.com")])
    assert r["refused"] == [["setbacks", "unknown person: stranger@example.com"]]


def test_ratify_stamps_the_set(lib):
    root = lib("guide", lambda d: None)
    assert ratify(root, "guide", date(2026, 12, 3)) == ["how_stories_count", "setbacks", "use_table", "use_not_listed"]
    e = load_library(root).entries["setbacks"]
    assert (e.status, e.ratified_on, e.ratified_by) == ("ratified", date(2026, 12, 3), "Planning Board")


def test_ratify_refuses_while_drafts_remain(lib):
    root = lib("guide", lambda d: None)
    _draft(root, "use_table")
    with pytest.raises(ValueError, match="use_table is still a draft"):
        ratify(root, "guide", date(2026, 12, 3))
    assert "use_table" not in ratify(root, "guide", date(2026, 12, 3), partial=True)


def test_a_ratified_entry_is_live(lib):
    root = lib("guide", lambda d: None)
    _draft(root, "setbacks")
    _apply(root, [_d("setbacks", "approve")])
    ratify(root, "guide", date(2026, 12, 3))
    assert is_live(load_library(root).entries["setbacks"])
