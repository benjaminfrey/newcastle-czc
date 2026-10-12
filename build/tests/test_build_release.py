"""build-release.sh end to end: the one-command draft release and its gate.

Each scenario builds a REAL release (real Typst, real leaves) from a copy of the
v1.0 source tree into tmp, so these tests are slow; scenarios that can share a
build do (module-scoped fixtures). Cheap tests (refusals, an existing release dir,
the negative control) reuse an already-built release through stub leaves that copy
finished files -- the gate still inspects real PDFs.
"""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import section_fixtures as fx  # noqa: E402

REPO = fx.REPO
DRIVER = REPO / "build" / "build-release.sh"
VER = "v0.98-draft"
DATE = "January 1, 2027"
MEETING_VER = "v9.0"
EVENT = "May 1, 2027"
MEETING_ENV = {"ADOPTION_MODE": "meeting", "ADOPTION_EVENT_DATE": EVENT}


def drive(args, tree, env_extra=None, version=VER, date=DATE, old="v1.0", unset=()):
    env = dict(os.environ)
    env["SRC_DIR"] = str(tree)
    for k in unset:
        env.pop(k, None)
    env.update(env_extra or {})
    cmd = ["bash", str(DRIVER)]
    if version is not None:
        cmd.append(version)
    if date is not None:
        cmd.append(date)
    if old is not None:
        cmd.append(f"--old-ver={old}")
    cmd += list(args)
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, env=env)


def listing(d):
    return sorted(p.name for p in d.iterdir())


def plan_files(release_dir, *kinds):
    plan = json.loads((release_dir / "release-plan.json").read_text())
    return sorted(f for a in plan["artifacts"] if a["kind"] in kinds for f in a["files"])


def edit_a7(tree):
    f = next(tree.glob("article-07-*.md"))
    f.write_text(f.read_text() + "\nAn added sentence for the test.\n")


def edit_a2_data(tree):
    p = tree / "article-02-data.json"
    data = json.loads(p.read_text())
    entries = data[0]["use_col1"][0]["entries"]
    entries[0][1] = "ex" if entries[0][1] != "ex" else "u"
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False))


def touch_layout(tree):
    with open(tree / "article-02.typ", "a") as f:
        f.write("\n// probe\n")


def calls_file(path, reason):
    path.write_text(json.dumps({"calls": [{"article": 2, "decision": "layout-only",
                                           "reason": reason, "by": "Ben Frey"}]}))
    return path


def built(tmp_path_factory, name, edit=None, args_extra=(), calls_reason=None):
    root = tmp_path_factory.mktemp(name)
    tree = fx.copy_full_source(root / "src")
    if edit:
        edit(tree)
    args = ["--out-dir", str(root / "rel")]
    if calls_reason is not None:
        args += ["--calls", str(calls_file(root / "calls.json", calls_reason))]
    r = drive(args + list(args_extra), tree)
    return r, root / "rel", tree, root


# ---------------------------------------------------------------- scenarios

@pytest.fixture(scope="module")
def a(tmp_path_factory):
    return built(tmp_path_factory, "a")


@pytest.fixture(scope="module")
def b(tmp_path_factory):
    return built(tmp_path_factory, "b", edit_a7)


@pytest.fixture(scope="module")
def c(tmp_path_factory):
    return built(tmp_path_factory, "c", edit_a2_data)


@pytest.fixture(scope="module")
def d_ok(tmp_path_factory):
    return built(tmp_path_factory, "d", touch_layout, calls_reason="only the chrome moved")


def base_files(rel):
    return sorted(plan_files(rel, "integrated", "integrated-redline", "summary", "record"))


def test_a_unchanged_tree_ships_the_minimum(a):
    r, rel, _, _ = a
    assert r.returncode == 0, r.stderr[-2000:]
    names = listing(rel)
    assert len(names) == 7, names
    assert names == base_files(rel)
    assert sum(n.endswith(".pdf") for n in names) == 2 and "release-plan.json" in names and "ships.json" in names
    assert f"Summary of Changes {VER}.md" in names
    assert any("Redline" in n and n.endswith(".md") for n in names)
    summary = (rel / f"Summary of Changes {VER}.md").read_text()
    assert "No Article changed in this release." in summary
    assert "extract" not in summary.lower() and "standalone" not in summary.lower()
    assert f"Release {VER}: 7 file(s)" in r.stdout


def test_b_article_7_edit_adds_its_standalone_pair(b):
    r, rel, _, _ = b
    assert r.returncode == 0, r.stderr[-2000:]
    names = listing(rel)
    extra = [n for n in names if n not in base_files(rel)]
    assert len(extra) == 4, names
    assert extra == sorted(plan_files(rel, "standalone", "standalone-redline"))
    assert all("Article 7" in n for n in extra)
    assert sorted(n.rsplit(".", 1)[1] for n in extra) == ["md", "md", "pdf", "pdf"]
    assert sum("Redline" in n for n in extra) == 2


def test_c_district_data_edit_ships_article_2_and_the_use_table_memo(c):
    r, rel, _, _ = c
    assert r.returncode == 0, r.stderr[-2000:]
    names = listing(rel)
    extra = [n for n in names if n not in base_files(rel)]
    a2 = [n for n in extra if "Article 2" in n]
    assert len(a2) == 4, names
    assert sorted(n for n in extra if n not in a2) == [
        f"Use Table Changes {VER}.md", f"Use Table Changes {VER}.pdf"]
    redline_md = next(n for n in a2 if "Redline" in n and n.endswith(".md"))
    assert "the thirteen district pages" in (rel / redline_md).read_text()


def test_d_layout_unit_edit_without_a_reason_is_refused_and_leaves_nothing(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    touch_layout(tree)
    rel = tmp_path / "rel"
    r = drive(["--out-dir", str(rel), "--calls", str(calls_file(tmp_path / "c.json", ""))], tree)
    assert r.returncode == 1, r.stderr[-1500:]
    assert "release_plan: refusing" in r.stderr and not rel.exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".staging-")]
    r = drive(["--out-dir", str(rel)], tree)   # no calls file at all
    assert r.returncode == 1 and not rel.exists()


def test_d_layout_unit_edit_with_a_written_call_releases_and_quotes_the_reason(d_ok):
    r, rel, _, _ = d_ok
    assert r.returncode == 0, r.stderr[-2000:]
    assert "only the chrome moved" in (rel / f"Summary of Changes {VER}.md").read_text()
    assert listing(rel) == base_files(rel)


def test_e_plan_only_prints_the_plan_and_builds_nothing(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    edit_a7(tree)
    rel = tmp_path / "out" / "rel"
    r = drive(["--plan-only", "--out-dir", str(rel)], tree)
    assert r.returncode == 0, r.stderr[-1500:]
    plan = json.loads(r.stdout)
    assert plan["version"] == VER and plan["articles"]["7"]["verdict"] == "SUBSTANTIVE"
    assert not rel.exists()
    assert not (tmp_path / "out").exists() or listing(tmp_path / "out") == []


# ----------------------------------------------------------- stubbed leaves

def write_stub(path, body):
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
    return path


def copy_stubs(tmp_path, src_rel, skip=(), sub="stubs"):
    """Stub leaves that 'build' by copying finished files from `src_rel`, named by its plan."""
    d = tmp_path / sub
    d.mkdir()
    s = str(src_rel)

    def cp_each(names, dest):
        return "".join(f'cp "{s}/{n}" "{dest}"\n' for n in names)

    integ = [n for n in plan_files(src_rel, "integrated")]
    rl = plan_files(src_rel, "integrated-redline")
    rl_pdf = next(n for n in rl if n.endswith(".pdf"))
    rl_md = next(n for n in rl if n.endswith(".md"))
    env = {}
    env["CZC_LEAF_FULL"] = str(write_stub(d / "full.sh", cp_each(integ, '$OUT_DIR/')))
    env["CZC_LEAF_REDLINE_FULL"] = str(write_stub(
        d / "rfull.sh", f'cp "{s}/{rl_pdf}" "$REDLINE_OUT"\ncp "{s}/{rl_md}" "$REDLINE_MD_OUT"\n'))
    sa = plan_files(src_rel, "standalone")
    env["CZC_LEAF_STANDALONE"] = str(write_stub(d / "sa.sh", cp_each(sa, '$OUT_DIR/')))
    sr = plan_files(src_rel, "standalone-redline")
    env["CZC_LEAF_REDLINE_STANDALONE"] = str(write_stub(d / "sr.sh", cp_each(sr, '$REDLINE_OUT/')))
    for k in skip:
        env[k] = str(write_stub(d / f"{k}.sh", "exit 0\n"))
    return env


def test_negative_control_a_leaf_that_writes_nothing_is_caught_by_the_gate(b, tmp_path):
    _, b_rel, _, _ = b
    tree = fx.copy_full_source(tmp_path / "src")
    edit_a7(tree)
    env = copy_stubs(tmp_path, b_rel, skip=("CZC_LEAF_STANDALONE",))
    rel = tmp_path / "rel"
    r = drive(["--out-dir", str(rel)], tree, env_extra=env)
    assert r.returncode == 1, (r.stdout, r.stderr[-2000:])
    missing = [n for n in plan_files(b_rel, "standalone")]
    assert any(n in r.stderr and "Article 7" in r.stderr for n in missing), r.stderr
    assert "release_gate:" in r.stderr
    assert not rel.exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".staging-")]
    # positive control: the same stubs without the sabotage release cleanly
    env = copy_stubs(tmp_path, b_rel, sub="stubs-ok")
    r = drive(["--out-dir", str(rel)], tree, env_extra=env)
    assert r.returncode == 0, r.stderr[-2000:]
    assert listing(rel) == listing(b_rel)


def test_an_existing_summary_only_release_dir_is_filled_and_the_summary_kept(a, tmp_path):
    _, a_rel, _, _ = a
    tree = fx.copy_full_source(tmp_path / "src")
    rel = tmp_path / "rel"
    rel.mkdir()
    summary = rel / f"Summary of Changes {VER}.md"
    summary.write_bytes(b"# Hand-written\n\nPlain words, not a skeleton.\n")
    before = summary.read_bytes()
    r = drive(["--out-dir", str(rel)], tree, env_extra=copy_stubs(tmp_path, a_rel))
    assert r.returncode == 0, r.stderr[-2000:]
    assert summary.read_bytes() == before
    assert listing(rel) == listing(a_rel)
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".staging-")]


def test_an_existing_release_dir_with_anything_else_is_refused_untouched(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    rel = tmp_path / "rel"
    rel.mkdir()
    (rel / f"Summary of Changes {VER}.md").write_text("mine\n")
    (rel / "stray.txt").write_text("x\n")
    r = drive(["--out-dir", str(rel)], tree)
    assert r.returncode == 1 and r.stderr.startswith("build-release: ")
    assert listing(rel) == ["Summary of Changes v0.98-draft.md", "stray.txt"]
    assert (rel / "stray.txt").read_text() == "x\n"


# ------------------------------------------------------------------ refusals

def test_missing_old_ver_is_refused(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    r = drive(["--out-dir", str(tmp_path / "rel")], tree, old=None)
    assert r.returncode == 1 and r.stderr.startswith("build-release: ") and "--old-ver" in r.stderr
    assert not (tmp_path / "rel").exists()


def test_an_old_ver_that_is_not_a_commit_is_refused(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    r = drive(["--out-dir", str(tmp_path / "rel")], tree, old="v9.9-nonesuch")
    assert r.returncode == 1 and "not a git commit" in r.stderr


def test_a_whole_number_version_is_refused(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    r = drive(["--out-dir", str(tmp_path / "rel")], tree, version="v1.0")
    assert r.returncode == 1 and r.stderr.startswith("build-release: ")
    assert not (tmp_path / "rel").exists()


def test_meeting_mode_with_a_draft_version_is_refused(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    r = drive(["--out-dir", str(tmp_path / "rel")], tree,
              env_extra={"ADOPTION_MODE": "meeting", "ADOPTION_EVENT_DATE": "March 1, 2027"})
    assert r.returncode == 1 and "adoption version" in r.stderr
    assert not (tmp_path / "rel").exists()


def test_adopted_mode_is_refused(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    r = drive(["--out-dir", str(tmp_path / "rel")], tree, version=MEETING_VER,
              env_extra={"ADOPTION_MODE": "adopted", "ADOPTION_EVENT_DATE": EVENT})
    assert r.returncode == 1 and "ADOPTION_MODE=adopted" in r.stderr
    assert not (tmp_path / "rel").exists()


def test_meeting_mode_needs_an_event_date(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    r = drive(["--out-dir", str(tmp_path / "rel")], tree, version=MEETING_VER,
              env_extra={"ADOPTION_MODE": "meeting"}, unset=("ADOPTION_EVENT_DATE",))
    assert r.returncode == 1 and "ADOPTION_EVENT_DATE" in r.stderr
    assert not (tmp_path / "rel").exists()


def test_meeting_mode_refuses_an_old_ver_that_is_not_the_baseline(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    old = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                         text=True, check=True).stdout.strip()
    r = drive(["--out-dir", str(tmp_path / "rel")], tree, version=MEETING_VER, old=old,
              env_extra=MEETING_ENV)
    assert r.returncode == 1 and "adopted baseline" in r.stderr
    assert not (tmp_path / "rel").exists()


def test_a_draft_run_refuses_an_inherited_adoption_baseline(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    r = drive(["--out-dir", str(tmp_path / "rel")], tree, env_extra={"ADOPTION_BASELINE": "1"})
    assert r.returncode == 1 and "ADOPTION_BASELINE" in r.stderr
    assert not (tmp_path / "rel").exists()


def test_a_draft_run_refuses_an_inherited_event_date(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    r = drive(["--out-dir", str(tmp_path / "rel")], tree, env_extra={"ADOPTION_EVENT_DATE": EVENT})
    assert r.returncode == 1 and "ADOPTION_EVENT_DATE" in r.stderr
    assert not (tmp_path / "rel").exists()


def _env_spy(path, out, rc=0):
    keys = "ADOPTION_MODE ADOPTION_EVENT_DATE ADOPTION_BASELINE"
    body = "".join(f'echo "{k}=${{{k}-unset}}" >> "{out}"\n' for k in keys.split())
    return write_stub(path, body + f"exit {rc}\n")


def _spy_env(tmp_path):
    seen = {n: tmp_path / f"seen-{n}.txt" for n in ("full", "rfull", "sa", "sr")}
    d = tmp_path / "spies"
    d.mkdir()
    env = {
        "CZC_LEAF_FULL": str(_env_spy(d / "full.sh", seen["full"])),
        "CZC_LEAF_REDLINE_FULL": str(_env_spy(d / "rfull.sh", seen["rfull"])),
        "CZC_LEAF_STANDALONE": str(_env_spy(d / "sa.sh", seen["sa"])),
        "CZC_LEAF_REDLINE_STANDALONE": str(_env_spy(d / "sr.sh", seen["sr"], rc=1)),
    }
    return env, seen


def test_meeting_mode_hands_every_leaf_the_mode_and_the_redlines_the_baseline(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    edit_a7(tree)
    env, seen = _spy_env(tmp_path)
    env.update(MEETING_ENV)
    r = drive(["--out-dir", str(tmp_path / "rel")], tree, version=MEETING_VER, env_extra=env)
    assert r.returncode == 1 and "standalone redline build failed" in r.stderr, r.stderr[-1500:]
    for n, f in seen.items():
        got = f.read_text().split("\n")
        assert "ADOPTION_MODE=meeting" in got and f"ADOPTION_EVENT_DATE={EVENT}" in got, (n, got)
        want = "ADOPTION_BASELINE=1" if n in ("rfull", "sr") else "ADOPTION_BASELINE=unset"
        assert want in got, (n, got)


def test_draft_mode_hands_the_leaves_no_adoption_variables(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    edit_a7(tree)
    env, seen = _spy_env(tmp_path)
    r = drive(["--out-dir", str(tmp_path / "rel")], tree, env_extra=env,
              unset=("ADOPTION_MODE", "ADOPTION_EVENT_DATE", "ADOPTION_BASELINE"))
    assert r.returncode == 1 and "standalone redline build failed" in r.stderr, r.stderr[-1500:]
    for n, f in seen.items():
        assert f.read_text().split("\n")[:3] == [
            "ADOPTION_MODE=unset", "ADOPTION_EVENT_DATE=unset", "ADOPTION_BASELINE=unset"], n


# ------------------------------------------------- one real Town Meeting packet

@pytest.fixture(scope="module")
def meeting(tmp_path_factory):
    root = tmp_path_factory.mktemp("meeting")
    tree = fx.copy_full_source(root / "src")
    edit_a7(tree)
    r = drive(["--out-dir", str(root / "rel")], tree, version=MEETING_VER, date=EVENT,
              env_extra=MEETING_ENV)
    return r, root / "rel", root


def test_meeting_release_passes_the_gate_and_never_claims_adoption(meeting):
    import pymupdf
    r, rel, _ = meeting
    assert r.returncode == 0, r.stderr[-3000:]
    names = listing(rel)
    plan = json.loads((rel / "release-plan.json").read_text())
    assert plan["mode"] == "meeting" and plan["event_date"] == EVENT
    assert sorted(n for n in names) == sorted(f for a in plan["artifacts"] for f in a["files"])
    assert any("Standalone Town Meeting Edition" in n for n in names)
    for n in names:
        assert "Adopted" not in n and "Draft" not in n, n
        if n.endswith(".md"):
            body = (rel / n).read_text()
            assert "Adopted v9.0" not in body and "ADOPTED" not in body.replace("NOT YET ADOPTED", ""), n
    edition = next(n for n in names if n.startswith("Newcastle CZC (Town Meeting Edition")
                   and n.endswith(".pdf") and "Redline" not in n)
    cover = " ".join(pymupdf.open(rel / edition)[0].get_text().split())
    assert "TOWN MEETING EDITION \u2014 NOT YET ADOPTED" in cover, cover
    summary = (rel / f"Summary of Changes {MEETING_VER}.md").read_text()
    assert f"**For adoption at Town Meeting, {EVENT}.**" in summary
def test_an_existing_empty_release_dir_gets_the_generated_summary(a, tmp_path):
    _, a_rel, _, _ = a
    tree = fx.copy_full_source(tmp_path / "src")
    rel = tmp_path / "rel"
    rel.mkdir()
    r = drive(["--out-dir", str(rel)], tree, env_extra=copy_stubs(tmp_path, a_rel))
    assert r.returncode == 0, r.stderr[-2000:]
    assert listing(rel) == listing(a_rel)
    assert "No Article changed" in (rel / f"Summary of Changes {VER}.md").read_text()


def test_a_release_dir_holding_only_the_summary_pdf_is_refused_untouched(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    rel = tmp_path / "rel"
    rel.mkdir()
    (rel / f"Summary of Changes {VER}.pdf").write_bytes(b"%PDF-1.4 stray\n")
    r = drive(["--out-dir", str(rel)], tree)
    assert r.returncode == 1 and r.stderr.startswith("build-release: ")
    assert listing(rel) == [f"Summary of Changes {VER}.pdf"]


def test_a_failing_leaf_is_a_build_release_refusal(a, tmp_path):
    _, a_rel, _, _ = a
    tree = fx.copy_full_source(tmp_path / "src")
    env = copy_stubs(tmp_path, a_rel)
    env["CZC_LEAF_REDLINE_FULL"] = str(write_stub(tmp_path / "boom.sh", "exit 3\n"))
    rel = tmp_path / "rel"
    r = drive(["--out-dir", str(rel)], tree, env_extra=env)
    assert r.returncode == 1 and "build-release: the integrated redline build failed (exit 3)" in r.stderr
    assert not rel.exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".staging-")]


def test_an_inherited_section_map_never_reaches_the_leaves(a, tmp_path):
    _, a_rel, _, _ = a
    tree = fx.copy_full_source(tmp_path / "src")
    env = copy_stubs(tmp_path, a_rel)
    seen = tmp_path / "seen.txt"
    env["CZC_LEAF_REDLINE_FULL"] = str(write_stub(
        tmp_path / "spy.sh",
        f'echo "${{SECTION_MAP-unset}}" > "{seen}"\n'
        + next(l for l in open(env["CZC_LEAF_REDLINE_FULL"]).read().splitlines()[2:3]) + "\n"
        + open(env["CZC_LEAF_REDLINE_FULL"]).read().splitlines()[3] + "\n"))
    env["SECTION_MAP"] = "/nonexistent/bogus-map.json"
    rel = tmp_path / "rel"
    r = drive(["--out-dir", str(rel)], tree, env_extra=env)
    assert r.returncode == 0, r.stderr[-2000:]
    got = seen.read_text().strip()
    assert got != "/nonexistent/bogus-map.json"


def test_a_leaf_that_leaves_a_hidden_file_is_refused(a, tmp_path):
    _, a_rel, _, _ = a
    tree = fx.copy_full_source(tmp_path / "src")
    env = copy_stubs(tmp_path, a_rel)
    full = open(env["CZC_LEAF_FULL"]).read()
    env["CZC_LEAF_FULL"] = str(write_stub(tmp_path / "dirty.sh", full.split("\n", 2)[2] + 'touch "$OUT_DIR/.leaf-scratch"\n'))
    rel = tmp_path / "rel"
    r = drive(["--out-dir", str(rel)], tree, env_extra=env)
    assert r.returncode == 1 and "release_gate: .leaf-scratch: file is not in the release plan" in r.stderr
    assert not rel.exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".staging-")]


def test_an_existing_release_dir_with_a_hidden_file_is_refused_untouched(tmp_path):
    tree = fx.copy_full_source(tmp_path / "src")
    rel = tmp_path / "rel"
    rel.mkdir()
    (rel / ".DS_Store").write_text("x")
    r = drive(["--out-dir", str(rel)], tree)
    assert r.returncode == 1 and r.stderr.startswith("build-release: ")
    assert [p.name for p in rel.iterdir()] == [".DS_Store"]


def test_placed_release_is_world_readable(a):
    _, rel, _, _ = a
    assert (rel.stat().st_mode & 0o777) == 0o755
    assert {(p.stat().st_mode & 0o777) for p in rel.iterdir()} == {0o644}
