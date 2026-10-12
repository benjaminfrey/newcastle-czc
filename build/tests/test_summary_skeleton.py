"""build/summary_skeleton.py -- the Summary of Changes skeleton from a release plan."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402
import summary_skeleton as ss  # noqa: E402

NAMES = {"1": "General Standards", "2": "District Standards", "3": "Thoroughfares",
         "4": "Site Standards", "5": "Building Standards", "6": "Design Standards",
         "7": "Use Standards", "8": "Administration", "9": "Definitions"}


def art(n, status="UNCHANGED", **counts):
    c = {"prose": 0, "heading": 0, "table": 0, "data": 0, "suppressed": 0}
    c.update(counts)
    return {"name": NAMES[n], "verdict": status, "status": status, "new": False,
            "counts": c, "needs_call": [], "call": None}


def plan(**over):
    p = {"schema": 1, "version": "v0.98-draft", "date": "January 1, 2027", "mode": "draft",
         "old": "v1.0", "section_map": None,
         "articles": {n: art(n) for n in NAMES}, "artifacts": []}
    p.update(over)
    return p


def mixed():
    p = plan()
    p["articles"]["7"] = art("7", "SUBSTANTIVE", prose=3, heading=1)
    p["articles"]["5"] = art("5", "RENUMBER-ONLY")
    a2 = art("2", "LAYOUT-ONLY")
    a2["call"] = {"article": 2, "decision": "layout-only",
                  "reason": "page furniture only", "by": "Ben Frey"}
    p["articles"]["2"] = a2
    return p


def test_substantive_named_with_words():
    t = ss.render(mixed())
    sec = t.split("## Articles with their own extract and redline")[1].split("\n## ")[0]
    assert "Article 7" in sec and "Use Standards" in sec
    assert "its text" in sec and "its headings" in sec
    assert "its tables" not in sec and "its district" not in sec


def test_all_four_count_words():
    p = plan()
    p["articles"]["3"] = art("3", "SUBSTANTIVE", prose=1, heading=1, table=1, data=1)
    t = ss.render(p)
    for w in ("its text", "its headings", "its tables", "its district or inventory data"):
        assert w in t


def test_renumber_only_named():
    t = ss.render(mixed())
    sec = t.split("## Articles changed only by renumbering or cross-reference updates")[1].split("\n## ")[0]
    assert "Article 5" in sec and "Building Standards" in sec


def test_layout_only_with_reason_and_who():
    t = ss.render(mixed())
    sec = t.split("## Layout-only changes (a person's call)")[1].split("\n## ")[0]
    assert "Article 2" in sec and "page furniture only" in sec and "Ben Frey" in sec


def test_cannot_show_labels_and_tables():
    p = mixed()
    p["articles"]["3"] = art("3", "SUBSTANTIVE", table=2, data=1)
    t = ss.render(p)
    sec = t.split("## What the redline cannot show")[1].split("\n## ")[0]
    assert "unmarked" in sec and "table" in sec
    assert "the ten Thoroughfare Type pages" in sec           # data > 0
    assert "Exhibit 3.1, the Thoroughfare Inventory" in sec
    assert "the thirteen district pages (district standards and use tables)" in sec  # layout call


def test_cannot_show_omits_unaffected_article():
    p = plan()
    p["articles"]["7"] = art("7", "SUBSTANTIVE", prose=1)
    t = ss.render(p)
    assert "cannot show" not in t or "district pages" not in t
    assert "Thoroughfare Type pages" not in t


def test_substantive_call_with_units_listed():
    p = plan()
    a = art("1", "SUBSTANTIVE")
    a["call"] = {"article": 1, "decision": "substantive", "reason": "maps redrawn", "by": "Ben"}
    p["articles"]["1"] = a
    assert "the District Maps" in ss.render(p)


def test_section_renumbering_and_use_table():
    p = mixed()
    p["section_map"] = {"renumbered": 12}
    p["artifacts"] = [{"kind": "use-table-changes", "article": None, "files": ["x.md"]}]
    t = ss.render(p)
    assert "12 sections were renumbered; the redline does not mark the new numbers as changes." in t
    assert "Use Table Changes" in t
    p["section_map"] = {"renumbered": 1}
    assert "1 section was renumbered; the redline does not mark the new numbers as changes." in ss.render(p)
    p["section_map"] = {"renumbered": 0}
    assert "suppressed as mechanical" not in ss.render(p)


def test_opening_line():
    base = adoption_map.load().baseline_version
    t = ss.render(plan(old=base))
    first = t.split("\n")[0:4]
    joined = "\n".join(first)
    assert "v0.98-draft" in joined and "January 1, 2027" in joined
    assert f"Changes are stated against {base}, the Code as most recently adopted" in joined
    t2 = ss.render(plan(old="v0.5-draft"))
    assert "Changes are stated against v0.5-draft" in t2
    assert "most recently adopted" not in t2


def test_prose_placeholders():
    t = ss.render(mixed())
    assert "## What is new" in t and "## What changed" in t
    assert "<!--" in t and "plain words" in t


def test_no_stale_cycle_facts():
    for p in (plan(), mixed()):
        t = ss.render(p)
        for bad in ("November 3, 2020", "March 24, 2025", "3-8 become 4-9", "entirely new"):
            assert bad not in t


def test_all_unchanged_one_sentence():
    t = ss.render(plan())
    assert "No Article changed in this release." in t
    assert "## Articles with their own extract" not in t


def test_no_file_or_script_names():
    t = ss.render(mixed())
    body = t.replace("<!--", "").split("-->")
    for bad in (".md", ".py", ".typ", ".json", "build/"):
        assert bad not in "".join(body[1:]) and bad not in t.split("<!--")[0]


def cli(*a):
    return subprocess.run([sys.executable, str(BUILD / "summary_skeleton.py"), *map(str, a)],
                          capture_output=True, text=True)


def test_cli_writes(tmp_path):
    pj, out = tmp_path / "p.json", tmp_path / "s.md"
    pj.write_text(json.dumps(mixed()))
    r = cli(pj, out)
    assert r.returncode == 0, r.stderr
    assert out.read_text() == ss.render(mixed())
    assert [f.name for f in tmp_path.iterdir()].count("s.md") == 1 and len(list(tmp_path.iterdir())) == 2


def test_cli_refuses_existing(tmp_path):
    pj, out = tmp_path / "p.json", tmp_path / "s.md"
    pj.write_text(json.dumps(mixed()))
    out.write_text("hand written")
    r = cli(pj, out)
    assert r.returncode == 1 and "summary_skeleton: refusing --" in r.stderr
    assert out.read_text() == "hand written"


@pytest.mark.parametrize("mut", [
    lambda p: p.pop("version"),
    lambda p: p["articles"].pop("4"),
    lambda p: p["articles"]["4"].update(status="WEIRD"),
    lambda p: p["articles"]["4"].pop("counts"),
    lambda p: p["articles"]["4"]["counts"].pop("data"),
    lambda p: p["articles"]["2"].update(status="LAYOUT-ONLY", call=None),
])
def test_cli_refuses_malformed(tmp_path, mut):
    p = mixed()
    mut(p)
    pj, out = tmp_path / "p.json", tmp_path / "s.md"
    pj.write_text(json.dumps(p))
    r = cli(pj, out)
    assert r.returncode == 1 and "summary_skeleton: refusing --" in r.stderr
    assert not out.exists()


def test_cli_refuses_bad_json(tmp_path):
    pj, out = tmp_path / "p.json", tmp_path / "s.md"
    pj.write_text("{nope")
    r = cli(pj, out)
    assert r.returncode == 1 and not out.exists()


def test_meeting_summary_says_for_adoption_and_never_adopted_about_the_new_version():
    base = adoption_map.load().baseline_version
    p = mixed()
    p.update(mode="meeting", event_date="May 1, 2027", version="v9.0", old=base)
    t = ss.render(p)
    assert t.split("\n")[2] == "**For adoption at Town Meeting, May 1, 2027.**"
    assert f"Changes are stated against the Code as most recently adopted ({base})." in t
    # the only use of "adopted" is the baseline sentence
    assert t.lower().count("adopted") == 1
    assert "draft" not in t.lower()


def test_meeting_summary_requires_an_event_date():
    p = plan(mode="meeting", event_date=None, version="v9.0")
    with pytest.raises(ss.Refusal):
        ss.render(p)
