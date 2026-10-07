"""The ownership map. The substantive-change determination has to know which
files carry an Article's standards, and nothing recorded that: the manifest's
`data` field is a Typst --input value, not an ownership declaration, and it is
set for exactly one unit. Meanwhile source/article-02.typ reads
article-02-data.json and source/cross-section-plates.typ reads
exhibits/cross-sections/types.json -- both binding content no diff knew about."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST_PY = REPO / "build" / "manifest.py"
MANIFEST_JSON = REPO / "build" / "article-manifest.json"


def run(*args):
    r = subprocess.run([sys.executable, str(MANIFEST_PY), *args],
                       capture_output=True, text=True)
    return r.stdout, r.returncode


def _manifest_module():
    spec = importlib.util.spec_from_file_location("manifest_under_test", MANIFEST_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tracked_source_files():
    tracked = subprocess.run(["git", "ls-files", "source"], cwd=REPO,
                             capture_output=True, text=True, check=True)
    return [p[len("source/"):] for p in tracked.stdout.split("\n") if p]


def test_has_still_exits_1_for_the_pure_prose_articles():
    """The fast path. `has` tests entry.get("units"), not entry, so an entry
    with an empty units list must still select the single-pass build."""
    for n in ("4", "5", "6", "7", "8", "9"):
        _, rc = run("has", n)
        assert rc == 1, f"has {n} returned 0 -- Article {n} lost its pure-prose fast path"
    for n in ("1", "2", "3"):
        _, rc = run("has", n)
        assert rc == 0, f"has {n} returned 1 -- Article {n} lost its splice path"


def test_prose_is_unchanged_for_every_article():
    """Adding entries for 4-9 must not make `prose` start answering for them:
    build-standalone.sh falls back to the article-0N-*.md glob, and ownership of
    prose is that convention, not a manifest field."""
    assert run("prose", "1")[0] == "article-01-general.md\n"
    assert run("prose", "2")[0] == "article-02-prefatory.md\n"
    assert run("prose", "3")[0] == "article-03-streets-roads-driveways.md\n"
    for n in ("4", "5", "6", "7", "8", "9"):
        assert run("prose", n)[0] == "\n", f"prose {n} started answering"


def test_units_3_still_emits_three_pipe_delimited_lines():
    out, _ = run("units", "3")
    lines = [l for l in out.splitlines() if l.strip()]
    assert len(lines) == 3, lines
    for l in lines:
        assert l.count("|") == 5, f"expected 6 pipe-delimited fields: {l!r}"
    assert lines[0].startswith("cross-section-plates.typ|at-marker:TYPE-PAGES|")


def test_articles_lists_all_nine():
    out, rc = run("articles")
    assert rc == 0
    assert out.split() == [str(n) for n in range(1, 10)]


def test_data_is_json_and_declares_a_compare_mode():
    out, rc = run("data", "3")
    assert rc == 0
    entries = json.loads(out)
    assert entries, "Article 3 has data sources"
    for e in entries:
        assert set(e) >= {"path", "compare"}
        assert e["compare"] in ("json-keyed", "binary-hash", "generated-from")
    paths = [e["path"] for e in entries]
    assert "exhibits/street-types/inventory.json" in paths
    assert "exhibits/cross-sections/types.json" in paths


def test_inventory_substantive_fields_match_decision_d7():
    """D7: type, name, termini, ownership, right-of-way and traveled widths.
    Addresses, geometry, present use and districts are derived -- otherwise
    every GIS refresh reads as an amendment to Article 3."""
    entries = json.loads(run("data", "3")[0])
    inv = next(e for e in entries
               if e["path"] == "exhibits/street-types/inventory.json")
    assert inv["compare"] == "json-keyed"
    fields = set(inv["substantive_fields"])
    assert fields == {"type", "name", "termini", "ownership", "row_ft", "traveled_ft"}, fields
    for derived in ("addresses", "geometry", "present_use", "districts",
                    "maindot", "nonconformity"):
        assert derived not in fields, f"{derived} is derived under D7"


def test_owner_resolves_a_unit_a_data_file_and_prose():
    assert run("owner", "article-02.typ")[0].strip() == "2"
    assert run("owner", "article-02-data.json")[0].strip() == "2"
    assert run("owner", "article-07-use-standards.md")[0].strip() == "7"
    assert run("owner", "exhibits/cross-sections/sprites/trees/tree.svg")[0].strip() == "3"
    assert run("owner", "legacy/article-02-districts.md")[0].strip() == "ignored"


def test_owner_refuses_an_unclaimed_path():
    # positive control first: without it this test passes against a manifest.py
    # that has no `owner` subcommand at all (unknown command also exits 1).
    assert run("owner", "article-02.typ") == ("2\n", 0)
    out, rc = run("owner", "no-such-file.json")
    assert rc == 1
    assert out.strip() == ""


def test_every_tracked_source_file_is_claimed_exactly_once():
    """NEGATIVE CONTROL. This is the test that makes "silently uncounted"
    impossible rather than unlikely -- the failure that already shipped.
    Walks git's index, not the filesystem, so local .DS_Store and .bak files
    cannot make it flap. "Exactly once": a path claimed by two Articles would
    otherwise resolve silently to whichever sorts first."""
    rels = _tracked_source_files()
    assert len(rels) > 50, f"only {len(rels)} tracked files -- wrong repo root?"
    unclaimed = [p for p in rels if run("owner", p)[1] != 0]
    assert unclaimed == [], (
        f"{len(unclaimed)} file(s) under source/ are claimed by no Article and "
        f"are not listed in shared/ignored: {unclaimed}\n"
        f"Add each to an Article's data_sources, or to the top-level shared or "
        f"ignored list. An unclaimed file is a file a release can change without "
        f"the substantive-change determination noticing.")
    m = _manifest_module()
    doc = m.load()
    multi = {p: m.claimants(doc, p) for p in rels if len(m.claimants(doc, p)) != 1}
    assert multi == {}, (
        f"file(s) claimed by more than one owner: {multi}\n"
        f"Narrow one of the declarations; overlapping claims make the owner "
        f"depend on sort order.")


def test_a_new_unclaimed_file_fails_the_coverage_check(tmp_path):
    """The control for the control: prove the coverage test can fail. The probe
    is staged with `git add -N` so it genuinely appears in `git ls-files`, which
    is what the coverage test walks."""
    probe = REPO / "source" / "zz-coverage-probe.json"
    assert not probe.exists()
    try:
        probe.write_text("{}\n")
        subprocess.run(["git", "add", "-N", str(probe)], cwd=REPO, check=True)
        # positive control: a real claimed file resolves, so rc 1 below means
        # "unclaimed", not "the subcommand does not exist"
        assert run("owner", "article-02.typ")[1] == 0
        assert "zz-coverage-probe.json" in _tracked_source_files(), \
            "the probe never reached the index the coverage test walks"
        unclaimed = [p for p in _tracked_source_files() if run("owner", p)[1] != 0]
        assert unclaimed == ["zz-coverage-probe.json"], unclaimed
    finally:
        subprocess.run(["git", "rm", "--cached", "-q", "--force", str(probe)],
                       cwd=REPO, check=False)
        probe.unlink(missing_ok=True)
