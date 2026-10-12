"""build/release_plan.py -- what a draft release must contain.

Trees are materialised from the v1.0 tag (never the live source/) and edited, so
every expectation can fail. Names are compared against adoption-name.sh itself.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import section_fixtures as fx  # noqa: E402

REPO = BUILD.parent
VER = "v0.98-draft"
DATE = "January 1, 2027"


def bash_name(*args):
    r = subprocess.run(["bash", "-c", 'source build/adoption-name.sh; "$@"', "_", *args],
                       cwd=REPO, capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


@pytest.fixture
def tree(tmp_path):
    return fx.copy_full_source(tmp_path / "src")


def run(tmp_path, tree, calls=None, extra=(), old="v1.0"):
    out, ships = tmp_path / "o" / "release-plan.json", tmp_path / "o" / "ships.json"
    cmd = [sys.executable, str(BUILD / "release_plan.py"), "--old", old, "--new-dir", str(tree),
           "--version", VER, "--date", DATE, "--out", str(out), "--ships", str(ships), *extra]
    if calls is not None:
        cf = tmp_path / "calls.json"
        cf.write_text(json.dumps(calls))
        cmd += ["--calls", str(cf)]
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return r, out, ships


def ok(tmp_path, tree, calls=None, **kw):
    r, out, ships = run(tmp_path, tree, calls, **kw)
    assert r.returncode == 0, r.stderr
    return json.loads(out.read_text()), json.loads(ships.read_text())


def refused(tmp_path, tree, calls=None, **kw):
    r, out, ships = run(tmp_path, tree, calls, **kw)
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
    assert r.stderr.startswith("release_plan: refusing -- ")
    assert not out.exists() and not ships.exists()
    return r.stderr


def kinds(plan):
    return [(a["kind"], a["article"]) for a in plan["artifacts"]]


def call(n, decision="layout-only", reason="only the chrome moved", by="Ben Frey"):
    return {"article": n, "decision": decision, "reason": reason, "by": by}


def edit_a7(tree):
    f = next(tree.glob("article-07-*.md"))
    f.write_text(f.read_text() + "\nAn added sentence for the test.\n")


def touch_layout(tree):
    with open(tree / "article-02.typ", "a") as f:
        f.write("\n// a layout comment\n")


def test_unchanged_tree_ships_the_minimum(tmp_path, tree):
    plan, ships = ok(tmp_path, tree)
    assert {k: v["verdict"] for k, v in plan["articles"].items()} == {str(n): "UNCHANGED" for n in range(1, 10)}
    assert list(plan["articles"]) == [str(n) for n in range(1, 10)]
    assert kinds(plan) == [("integrated", None), ("integrated-redline", None),
                           ("summary", None), ("record", None)]
    assert plan["section_map"] is None and plan["mode"] == "draft" and plan["old"] == "v1.0"
    assert plan["schema"] == 1 and plan["version"] == VER and plan["date"] == DATE
    assert ships["old"] == "v1.0" and set(ships["articles"]) == {str(n) for n in range(1, 10)}


def test_article_7_edit_ships_its_standalone_pair_with_the_real_names(tmp_path, tree):
    edit_a7(tree)
    plan, _ = ok(tmp_path, tree)
    a7 = plan["articles"]["7"]
    assert a7["verdict"] == a7["status"] == "SUBSTANTIVE" and a7["counts"]["prose"] >= 1
    assert a7["call"] is None and a7["needs_call"] == []
    assert kinds(plan) == [("integrated", None), ("integrated-redline", None),
                           ("standalone", 7), ("standalone-redline", 7),
                           ("summary", None), ("record", None)]
    integ = bash_name("czc_integrated_name", "draft", VER)
    s = bash_name("czc_standalone_name", "draft", "7", a7["name"], VER)
    sr = bash_name("czc_standalone_name", "draft", "7", a7["name"], VER, "redline")
    assert a7["name"] == "Use Standards"
    files = {(a["kind"]): a["files"] for a in plan["artifacts"]}
    assert files["integrated"] == [f"{integ}.pdf", f"{integ}.md"]
    assert files["integrated-redline"] == [f"{integ} — Redline.pdf", f"{integ} — Redline.md"]
    assert files["standalone"] == [f"{s}.pdf", f"{s}.md"]
    assert files["standalone-redline"] == [f"{sr}.pdf", f"{sr}.md"]
    assert files["summary"] == [f"Summary of Changes {VER}.md"]
    assert files["record"] == ["release-plan.json", "ships.json"]


def test_a_use_status_edit_ships_article_2_and_the_use_table_changes(tmp_path, tree):
    p = tree / "article-02-data.json"
    data = json.loads(p.read_text())
    rec = next(r for r in data if (r["code"], r["name"]) == ("D3", "NEIGHBORHOOD BUSINESS"))
    cat = next(c for c in rec["use_col2"] if c["title"] == "COMMERCIAL GOODS")
    e = next(e for e in cat["entries"] if e[0] == "Retail & Service, General")
    e[1] = "rc"
    p.write_text(json.dumps(data, indent=2))
    plan, _ = ok(tmp_path, tree)
    assert plan["articles"]["2"]["status"] == "SUBSTANTIVE"
    assert plan["articles"]["2"]["counts"]["data"] == 1
    assert ("standalone", 2) in kinds(plan) and ("use-table-changes", 2) in kinds(plan)
    utc = next(a for a in plan["artifacts"] if a["kind"] == "use-table-changes")
    assert utc["files"] == [f"Use Table Changes {VER}.md", f"Use Table Changes {VER}.pdf"]
    order = [k for k, _ in kinds(plan)]
    assert order.index("use-table-changes") == order.index("summary") - 1


def test_layout_unit_change_without_a_call_is_refused_naming_the_article(tmp_path, tree):
    touch_layout(tree)
    err = refused(tmp_path, tree)
    assert "Article 2" in err and "NEEDS-CALL" in err
    assert "article-02.typ: a layout unit changed" in err   # its needs_call line, quoted


def test_layout_only_call_is_recorded_and_ships_no_standalone(tmp_path, tree):
    touch_layout(tree)
    c = call(2)
    plan, _ = ok(tmp_path, tree, {"calls": [c]})
    a2 = plan["articles"]["2"]
    assert a2["verdict"] == "NEEDS-CALL" and a2["status"] == "LAYOUT-ONLY"
    assert a2["call"] == c and a2["needs_call"]
    assert ("standalone", 2) not in kinds(plan)
    assert ("use-table-changes", 2) not in kinds(plan)


def test_substantive_call_on_a_needs_call_article_ships_it(tmp_path, tree):
    touch_layout(tree)
    plan, _ = ok(tmp_path, tree, {"calls": [call(2, "substantive", "legend wording moved")]})
    assert plan["articles"]["2"]["status"] == "SUBSTANTIVE"
    assert ("standalone-redline", 2) in kinds(plan)


def test_substantive_call_on_an_unchanged_article_ships_its_pair(tmp_path, tree):
    plan, _ = ok(tmp_path, tree, {"calls": [call(5, "substantive", "counsel says so")]})
    a5 = plan["articles"]["5"]
    assert a5["verdict"] == "UNCHANGED" and a5["status"] == "SUBSTANTIVE" and a5["call"]
    assert ("standalone", 5) in kinds(plan) and ("standalone-redline", 5) in kinds(plan)


@pytest.mark.parametrize("calls, needle", [
    ([call(2, reason="")], "reason"),
    ([call(2, reason="   ")], "reason"),
    ([call(2, by="")], "by"),
    ([call(2), call(2)], "more than one"),
    ([call(10)], "1-9"),
    ([call(0)], "1-9"),
    ([{**call(2), "extra": 1}], "unknown key"),
    ([{"article": 2, "decision": "layout-only", "reason": "r"}], "missing"),
    ([call(2, "maybe")], "decision"),
    ([call(3)], "layout-only is allowed only for a NEEDS-CALL"),            # UNCHANGED
    ([call(2), call(7, "substantive")], "redundant"),                       # 7 is SUBSTANTIVE
])
def test_improper_calls_are_refused_and_write_nothing(tmp_path, tree, calls, needle):
    touch_layout(tree)
    edit_a7(tree)
    err = refused(tmp_path, tree, {"calls": calls})
    assert needle in err


def test_a_malformed_calls_file_is_refused(tmp_path, tree):
    refused(tmp_path, tree, {"calls": [], "extra": 1})
    refused(tmp_path, tree, [])


def test_layout_only_cannot_downgrade_a_substantive_article(tmp_path, tree):
    edit_a7(tree)
    err = refused(tmp_path, tree, {"calls": [call(7)]})
    assert "Article 7" in err


def test_a_refused_czc_diff_is_refused_and_writes_nothing(tmp_path, tree):
    err = refused(tmp_path, tree, old="no-such-ref-xyz")
    assert "change determination" in err


def test_a_stale_plan_is_removed_by_a_refusing_run(tmp_path, tree):
    ok(tmp_path, tree)
    touch_layout(tree)
    refused(tmp_path, tree)     # refused() asserts both earlier outputs are gone


def test_the_section_map_is_counted_not_shipped(tmp_path, tree):
    d = tmp_path / "derived.json"   # a real map: czc_diff selfchecks it
    subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                    "--new-dir", str(tree), "--out", str(d)], cwd=REPO, check=True, capture_output=True)
    plan, _ = ok(tmp_path, tree, extra=("--section-map", str(d)))
    assert plan["section_map"] == {"renumbered": 0}
    assert not any("map" in f.lower() for a in plan["artifacts"] for f in a["files"])


def test_the_date_is_required(tmp_path, tree):
    r = subprocess.run([sys.executable, str(BUILD / "release_plan.py"), "--old", "v1.0",
                        "--new-dir", str(tree), "--version", VER, "--out", str(tmp_path / "p"),
                        "--ships", str(tmp_path / "s")], cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0 and not (tmp_path / "p").exists()


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)


def test_the_release_record_holds_no_local_path(tmp_path, tree):
    plan, ships = ok(tmp_path, tree)
    assert ships["new"] == VER
    for doc in (plan, ships):
        assert [s for s in _strings(doc) if s.startswith("/")] == []


def test_every_needs_call_article_is_named_in_one_refusal(tmp_path, tree):
    touch_layout(tree)
    with open(tree / "street-type-map.typ", "a") as f:
        f.write("\n// probe\n")
    err = refused(tmp_path, tree)
    assert "Article 2" in err and "Article 3" in err


def test_a_duplicate_key_in_a_call_is_refused(tmp_path, tree):
    touch_layout(tree)
    cf = tmp_path / "calls.json"
    cf.write_text('{"calls": [{"article": 2, "decision": "layout-only", '
                  '"decision": "substantive", "reason": "r", "by": "b"}]}')
    out, ships = tmp_path / "o" / "release-plan.json", tmp_path / "o" / "ships.json"
    r = subprocess.run([sys.executable, str(BUILD / "release_plan.py"), "--old", "v1.0",
                        "--new-dir", str(tree), "--version", VER, "--date", DATE,
                        "--out", str(out), "--ships", str(ships), "--calls", str(cf)],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 1 and "duplicate key" in r.stderr
    assert not out.exists() and not ships.exists()


# ---------------------------------------------------------------- meeting mode

MEETING_VER = "v9.0"
EVENT = "May 1, 2027"


def run_meeting(tmp_path, tree, version=MEETING_VER, old="v1.0", event=EVENT):
    out, ships = tmp_path / "o" / "release-plan.json", tmp_path / "o" / "ships.json"
    cmd = [sys.executable, str(BUILD / "release_plan.py"), "--old", old, "--new-dir", str(tree),
           "--version", version, "--date", DATE, "--out", str(out), "--ships", str(ships),
           "--mode", "meeting"]
    if event is not None:
        cmd += ["--event-date", event]
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return r, out, ships


def test_meeting_plan_is_named_by_the_meeting_forms_and_records_its_mode(tmp_path, tree):
    edit_a7(tree)
    r, out, _ = run_meeting(tmp_path, tree)
    assert r.returncode == 0, r.stderr
    plan = json.loads(out.read_text())
    assert plan["mode"] == "meeting" and plan["event_date"] == EVENT
    integ = bash_name("czc_integrated_name", "meeting", MEETING_VER)
    assert integ == f"Newcastle CZC (Town Meeting Edition {MEETING_VER})"
    by = {a["kind"]: a for a in plan["artifacts"]}
    assert by["integrated"]["files"] == [f"{integ}.pdf", f"{integ}.md"]
    assert by["integrated-redline"]["files"] == [f"{integ} \u2014 Redline.pdf", f"{integ} \u2014 Redline.md"]
    name7 = plan["articles"]["7"]["name"]
    s = bash_name("czc_standalone_name", "meeting", "7", name7, MEETING_VER)
    sr = bash_name("czc_standalone_name", "meeting", "7", name7, MEETING_VER, "redline")
    assert "Standalone Town Meeting Edition" in s
    assert by["standalone"]["files"] == [f"{s}.pdf", f"{s}.md"]
    assert by["standalone-redline"]["files"] == [f"{sr}.pdf", f"{sr}.md"]
    assert not any("Adopted" in f or "Draft" in f for a in plan["artifacts"] for f in a["files"])


def test_draft_plan_records_no_event_date(tmp_path, tree):
    plan, _ = ok(tmp_path, tree)
    assert plan["mode"] == "draft" and plan["event_date"] is None


def _meeting_refused(tmp_path, tree, needle, **kw):
    r, out, ships = run_meeting(tmp_path, tree, **kw)
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
    assert r.stderr.startswith("release_plan: refusing -- ") and needle in r.stderr, r.stderr
    assert not out.exists() and not ships.exists()


def test_meeting_mode_refuses_a_decimal_version(tmp_path, tree):
    _meeting_refused(tmp_path, tree, "adoption version", version="v9.0-draft")


def test_meeting_mode_needs_an_event_date(tmp_path, tree):
    _meeting_refused(tmp_path, tree, "--event-date", event=None)


def test_meeting_mode_must_compare_against_the_adopted_baseline(tmp_path, tree):
    _meeting_refused(tmp_path, tree, "adopted baseline", old="v0.24-draft")


def test_draft_mode_refuses_an_event_date(tmp_path, tree):
    r, out, ships = run(tmp_path, tree, extra=["--event-date", EVENT])
    assert r.returncode == 1 and "meeting mode only" in r.stderr
    assert not out.exists() and not ships.exists()
