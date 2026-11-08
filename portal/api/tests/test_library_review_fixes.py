"""The whole-branch review's Important findings (library plan 1), each pinned by a test."""

import json
from datetime import date

from sqlalchemy import text

from portal_api.guide.content import load_content
from portal_api.guide.engine import Action, Lot, _Build, replay
from portal_api.library import load_library
from portal_api.library.__main__ import main as cli
from portal_api.library.load import check_edit
from portal_api.library.view import View, using
from portal_api.library.write import apply, memo_versions, ratify
from portal_api.ruleset import PINNED_KEY
from tests.test_library_record import CHAIR, PEOPLE, _d, _draft
from tests.test_library_routes import staff  # noqa: F401  (fixture)
from tests.test_projects import alice, app  # noqa: F401  (fixtures)
from tests.test_property import layers  # noqa: F401  (fixture)

TEXTS = {"overline": "Why · how far from the front", "answer": "Your building sits {front} from the front lot line.",
         "detail": "Measure to the closest wall.", "why": "Streets keep their line."}


def _lot(*codes):
    return Lot(map_lot="004-036", district_codes=codes, district_names=codes, acres=2.0, frontage_ft=300)


# 1. A lot in two districts never shows one district's number on the card.
def test_a_two_district_lot_shows_no_card_when_the_districts_differ():
    c = load_content()
    side = c.turn("setback_side_1")
    assert _Build(c, "new_house", _lot("D1")).why_for(side)["answer"].startswith("Your building sits at least 15 ft")
    assert _Build(c, "new_house", _lot("D1", "D2")).why_for(side) is None          # 15 ft and 12 ft


def test_two_districts_that_agree_show_the_card():
    c = load_content()
    stories = c.turn("full_stories")
    assert _Build(c, "new_house", _lot("D1", "D2")).why_for(stories)["answer"] == "The building has at most 2 stories."


# 2. An edit is checked before it is recorded, and again when it is applied.
def test_an_edit_is_checked():
    e = load_library().entries["front_setback"]
    assert check_edit(e, TEXTS) is None
    assert check_edit(e, {**TEXTS, "why": "Once approved by the Board."}) == "never_word"
    assert check_edit(e, {**TEXTS, "answer": "Your building sits {back} from the line."}) == "unknown_slot"
    assert check_edit(e, {**TEXTS, "answer": "Your building sits 20 ft from the front lot line."}) == "drops_slot"


def test_the_route_refuses_a_bad_edit(staff):  # noqa: F811
    url = "/api/library/entries/front_setback/decision"
    r = staff.post(url, json={"version": 1, "action": "edit", "body": {**TEXTS, "why": "It is approved."}})
    assert (r.status_code, r.json()["detail"]) == (422, "never_word")


def test_apply_refuses_a_bad_edit(lib):
    root = lib("guide", lambda d: None)
    body = {"overline": "o", "answer": "Granted.", "detail": "d", "why": "w"}
    r = apply(root, {"decisions": [_d("setbacks", "edit", body=body)], "pulls": [], "superseded": []}, chair=CHAIR, people=PEOPLE)
    assert r["refused"] == [["setbacks", "the edit fails its checks: never_word"]]
    load_library(root)


# 4. Pulls are exported and cleared one by one, never by entry alone.
def test_a_pull_made_after_the_dump_survives_mark_exported(staff, engine, monkeypatch, capsys, tmp_path):  # noqa: F811
    monkeypatch.setenv("PORTAL_DATABASE_URL", str(engine.url.render_as_string(hide_password=False)))
    staff.post("/api/library/entries/setbacks/pull", json={"version": 1, "why": "First"})
    assert cli(["decisions"]) == 0
    dump = json.loads(capsys.readouterr().out)
    with engine.begin() as conn:      # a second pull of the same entry, after the dump
        conn.execute(text("UPDATE library_pull SET why = 'Second', pulled_at = now() + interval '1 minute'"))
    result = tmp_path / "r.json"
    result.write_text(json.dumps({"exported_decisions": [], "cleared_pulls": [{"entry_id": "setbacks", "version": 1}],
                                  "exported_pulls": [{"entry_id": p["entry_id"], "pulled_at": p["pulled_at"]} for p in dump["pulls"]]}))
    assert cli(["mark-exported", str(result)]) == 0
    with engine.begin() as conn:
        row = conn.execute(text("SELECT why, exported_at FROM library_pull")).one()
    assert (row.why, row.exported_at) == ("Second", None)


def test_approving_a_fix_clears_only_older_pulls(lib):
    root = lib("guide", lambda d: None)
    edit = _d("setbacks", "approve", body={"overline": "o", "answer": "a", "detail": "d", "why": "w"})
    pull = {"entry_id": "setbacks", "version": 1, "why": "x", "pulled_at": "2026-11-21T15:00:00+00:00",
            "pulled_by_email": "ceo@example.com"}
    r = apply(root, {"decisions": [edit], "pulls": [pull], "superseded": []}, chair=CHAIR, people=PEOPLE)
    assert r["cleared_pulls"] == [] and r["refused"]                       # pulled at v1: not approved
    _draft(root, "use_table")
    r = apply(root, {"decisions": [_d("use_table", "approve", did=5)], "pulls": [], "superseded": []}, chair=CHAIR, people=PEOPLE)
    assert r["cleared_pulls"] == [{"entry_id": "use_table", "version": 1}]


# 5. The Board ratifies the versions its memo showed, and only those.
def test_ratify_stamps_only_the_memos_versions(lib, tmp_path):
    root = lib("guide", lambda d: None)
    memo = tmp_path / "memo.md"
    memo.write_text("**Status:** Approved (`setbacks`, version 1)\n**Status:** Approved (`use_table`, version 1)\n")
    versions = memo_versions(memo)
    assert versions == {"setbacks": 1, "use_table": 1}
    assert ratify(root, "guide", date(2026, 12, 3), versions=versions, partial=True) == ["setbacks", "use_table"]


def test_ratify_refuses_an_entry_changed_since_the_memo(lib, tmp_path):
    root = lib("guide", lambda d: None)
    apply(root, {"decisions": [_d("setbacks", "approve", body={"overline": "o", "answer": "a", "detail": "d", "why": "w"})],
                 "pulls": [], "superseded": []}, chair=CHAIR, people=PEOPLE)
    import pytest
    with pytest.raises(ValueError, match="setbacks is at version 2; the memo showed version 1"):
        ratify(root, "guide", date(2026, 12, 3), versions={"setbacks": 1})


# 6. An approval records the ruleset it was approved against.
def test_an_approval_records_the_pinned_ruleset(lib):
    root = lib("guide", lambda d: d["entries"][1].update(ruleset="adopted-v0.9"))
    apply(root, {"decisions": [_d("setbacks", "approve", body={"overline": "o", "answer": "a", "detail": "d", "why": "w"})],
                 "pulls": [], "superseded": []}, chair=CHAIR, people=PEOPLE)
    assert load_library(root).entries["setbacks"].ruleset == PINNED_KEY


# 10. The interpretation mark is the guide's own word, and a draft until the chair approves it.
def test_the_interpretation_mark_is_a_draft_word_the_guide_records():
    c = load_content()
    with using(View()):
        s = replay(c, "new_house", _lot("D1"), [Action("answer", "lot", "yes"), Action("answer", "confirm", "yes")])
    assert s.current.why["mark"] == c.wording["interpretation_mark"]["text"]
    assert "wording.yaml: interpretation_mark" in s.drafts
