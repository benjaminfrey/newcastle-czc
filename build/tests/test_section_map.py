"""build/section_map.py -- the derived section-renumbering map.

The map is DERIVED, never authored: a hand-maintained renumbering map is exactly
the failure baseline_selfcheck.py exists to catch (308 phantom lines comparing
v1.0 to itself, exit 0). Every assertion here that something was NOT mapped sits
beside a positive control, because the real tree is identical to v1.0 and a
broken derivation would also map nothing.
"""
import json
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import section_map  # noqa: E402
import section_fixtures as fx  # noqa: E402

REPO = BUILD.parent
ART7 = "article-07-use-standards.md"


def _tree_with(tmp_path, article, transform):
    tree = fx.copy_source(tmp_path / "src")
    p = tree / article
    p.write_text(transform(p.read_text()))
    return tree


def test_against_v1_0_it_examines_every_heading_and_maps_nothing(tmp_path):
    """The tree is v1.0 materialised from the tag, so 'maps nothing' alone proves
    nothing. The positive control is `matched`: the derivation must have found every
    heading again -- 66 in Article 7, 14 in Article 3, 29 in Article 8."""
    doc = section_map.derive("v1.0", fx.copy_source(tmp_path / "src"))
    assert doc["articles"] == {}
    assert doc.get("skipped", []) == []
    assert doc["matched"]["7"] == 66
    assert doc["matched"]["3"] == 14
    assert doc["matched"]["8"] == 29
    assert doc["matched"].get("9", 0) == 0     # Article 9 has no headings


def test_a_section_inserted_at_3_maps_exactly_64(tmp_path):
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    doc = section_map.derive("v1.0", tree)
    assert doc["articles"]["7"] == {str(o): o + 1 for o in range(3, 67)}
    assert len(doc["articles"]["7"]) == 64
    assert doc["matched"]["7"] == 66


def test_a_retitled_section_at_a_shifted_number_is_not_mapped(tmp_path):
    """Old §10 becomes new §11 AND is retitled: not a pure renumbering, so it
    stays visible as a change."""
    def change(t):
        return fx.retitle(fx.insert_section(t, 3, "AGRICULTURE"), 11, "SOMETHING ELSE")
    doc = section_map.derive("v1.0", _tree_with(tmp_path, ART7, change))
    assert "10" not in doc["articles"]["7"]
    assert len(doc["articles"]["7"]) == 63
    assert any(e.startswith("§10 ") for e in doc["unmapped_old"]["7"])


def test_a_deleted_section_maps_the_sections_after_it_but_not_itself(tmp_path):
    """Ruling 6: sections after a deletion keep their titles, so they ARE a
    renumbering. The deleted section's own number is never mapped."""
    doc = section_map.derive("v1.0", _tree_with(tmp_path, ART7, lambda t: fx.delete_section(t, 3)))
    assert doc["articles"]["7"] == {str(o): o - 1 for o in range(4, 67)}
    assert "3" not in doc["articles"]["7"]
    assert any(e.startswith("§3 ") for e in doc["unmapped_old"]["7"])


def test_a_changed_body_at_an_unchanged_number_is_not_mapped(tmp_path):
    def change(t):
        return t.replace("## 5. AMUSEMENT, OUTDOOR\n", "## 5. AMUSEMENT, OUTDOOR\n\nAmended text.\n", 1)
    tree = _tree_with(tmp_path, ART7, change)
    assert "Amended text." in (tree / ART7).read_text()     # the edit really landed
    doc = section_map.derive("v1.0", tree)
    assert doc["articles"] == {}
    assert doc["matched"]["7"] == 66                        # and every heading was examined


def test_a_duplicated_title_is_never_mapped():
    """Two headings with the same title cannot be told apart by title, so the
    alignment could pair the wrong one. Ambiguous titles stay unmapped."""
    old = "## 1. GENERAL\n## 2. GENERAL\n## 3. USE\n"
    new = "## 1. NEW\n## 2. GENERAL\n## 3. GENERAL\n## 4. USE\n"
    mapping, _, old_un, _ = section_map.derive_article(old, new)
    assert mapping == {3: 4}
    assert any("GENERAL" in e for e in old_un)


def test_below_the_similarity_floor_derive_refuses_and_writes_nothing(tmp_path):
    def change(t):
        return fx._H2.sub(lambda m: f"## {m.group(1)}. RENAMED ", t)
    tree = _tree_with(tmp_path, ART7, change)
    out = tmp_path / "map.json"
    r = subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                        "--new-dir", str(tree), "--out", str(out)],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 2, r.stderr
    assert "Article 7" in r.stderr
    assert not out.exists()


def test_the_map_records_its_provenance(tmp_path):
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = tmp_path / "map.json"
    r = subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                        "--new-dir", str(tree), "--out", str(out)],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text())
    assert doc["for_old_ref"] == "v1.0"
    assert doc["for_new_tree"] == section_map.tree_hash(tree)
    assert section_map.load(out) == {7: {o: o + 1 for o in range(3, 67)}}


def _cli(args):
    return subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", *args],
                          capture_output=True, text=True, cwd=REPO)


def test_a_bad_old_ref_is_refused_and_writes_nothing(tmp_path):
    out = tmp_path / "map.json"
    r = _cli(["no-such-ref-xyz", "--new-dir", str(fx.copy_source(tmp_path / "src")),
              "--out", str(out)])
    assert r.returncode == 1, r.stderr
    assert "refusing to derive" in r.stderr
    assert "no-such-ref-xyz" in r.stderr
    assert not out.exists()


def test_a_tree_with_no_matching_articles_is_refused(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    out = tmp_path / "map.json"
    r = _cli(["v1.0", "--new-dir", str(empty), "--out", str(out)])
    assert r.returncode == 1, r.stderr
    assert "nothing was compared" in r.stderr
    assert not out.exists()


# --- check: is this map for this comparison? ----------------------------------

def _derived(tmp_path, tree):
    out = tmp_path / "map.json"
    r = subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                        "--new-dir", str(tree), "--out", str(out)],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    return out


def _run_cli(*args):
    return subprocess.run([sys.executable, str(BUILD / "section_map.py"), *args],
                          capture_output=True, text=True, cwd=REPO)


def test_check_accepts_the_comparison_a_map_was_derived_for(tmp_path):
    """The positive control for the two refusals below."""
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = _derived(tmp_path, tree)
    r = _run_cli("check", str(out), "--old-ref", "v1.0", "--new-dir", str(tree))
    assert r.returncode == 0, r.stderr


def test_check_refuses_a_map_for_a_different_old_ref(tmp_path):
    """Nothing today validates the old ref against a map; this closes it."""
    out = _derived(tmp_path, _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "X")))
    r = _run_cli("check", str(out), "--old-ref", "v0.24-draft")
    assert r.returncode == 1
    assert "v1.0" in r.stderr and "v0.24-draft" in r.stderr


def test_check_refuses_a_map_applied_to_a_different_tree(tmp_path):
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = _derived(tmp_path, tree)
    (tree / ART7).write_text((tree / ART7).read_text() + "\nLater edit.\n")
    r = _run_cli("check", str(out), "--old-ref", "v1.0", "--new-dir", str(tree))
    assert r.returncode == 1
    assert "different tree" in r.stderr


# --- selfcheck: is this map right? ---------------------------------------------

def test_selfcheck_passes_a_correct_non_empty_map(tmp_path):
    """The positive control, and deliberately NOT the empty map against the real
    tree: that passes whether or not the gate works. This map has 64 entries,
    every one of which the gate must examine and accept."""
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = _derived(tmp_path, tree)
    assert len(json.loads(out.read_text())["articles"]["7"]) == 64
    r = _run_cli("selfcheck", str(out), "--old-ref", "v1.0", "--new-dir", str(tree))
    assert r.returncode == 0, r.stderr


def test_selfcheck_refuses_an_off_by_one_map(tmp_path):
    """The control the gate exists for: shift every target by one and every
    entry now pairs two different sections. It must be able to fail, or it
    is decoration."""
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = _derived(tmp_path, tree)
    doc = json.loads(out.read_text())
    doc["articles"]["7"] = {o: n + 1 for o, n in doc["articles"]["7"].items()}
    out.write_text(json.dumps(doc))
    r = _run_cli("selfcheck", str(out), "--old-ref", "v1.0", "--new-dir", str(tree))
    assert r.returncode == 1
    assert "Article 7" in r.stderr


def test_selfcheck_refuses_a_single_wrong_entry(tmp_path):
    tree = _tree_with(tmp_path, ART7, lambda t: fx.insert_section(t, 3, "AGRICULTURE"))
    out = _derived(tmp_path, tree)
    doc = json.loads(out.read_text())
    doc["articles"]["7"]["10"] = 40          # old §10 is not new §40
    out.write_text(json.dumps(doc))
    r = _run_cli("selfcheck", str(out), "--old-ref", "v1.0", "--new-dir", str(tree))
    assert r.returncode == 1
    assert "§10 -> §40" in r.stderr


def test_section_map_does_not_reach_into_the_adoption_map():
    """The invariant behind deriving the map. It reads the Code only through
    git_show; a later edit importing the adoption map or its self-check would
    make the next amendment's map collide with the rollover guard.

    Checked on the parsed module, not its text: the docstrings deliberately
    NAME those files to say they are not touched, so a text search fails on
    the documentation of their absence."""
    import ast
    tree = ast.parse((BUILD / "section_map.py").read_text())
    imported = {a.name.split(".")[0] for n in ast.walk(tree)
                if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.module}
    assert not imported & {"adoption_map", "baseline_selfcheck"}, imported
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
                  and n.body and isinstance(n.body[0], ast.Expr)
                  and isinstance(n.body[0].value, ast.Constant)}
    literals = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and id(n) not in docstrings]
    assert not [s for s in literals if "adoption-map" in s or "adoption_map" in s
                or "baseline_selfcheck" in s]
