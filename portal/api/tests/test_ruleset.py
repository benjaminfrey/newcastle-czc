import json
import shutil
from pathlib import Path

import pytest

from portal_api.ruleset import PINNED_KEY, RulesetError, district_key_for, load_ruleset

VENDORED = Path(__file__).resolve().parents[1] / "portal_api" / "rulesets" / PINNED_KEY
SOURCE = Path(__file__).resolve().parents[3] / "build" / "permit-review" / "rulesets" / PINNED_KEY


def test_loads_the_adopted_ruleset():
    r = load_ruleset()
    assert r.key == "adopted-v1.0" and str(r.adopted_on) == "2026-09-14"
    assert len(r.uses) == 63 and len(r.cells) == 819 and len(r.districts) == 13


def test_vendored_files_match_the_board_apps_ruleset():
    files = sorted(VENDORED.iterdir())
    assert len(files) == 6
    for f in files:
        assert f.read_bytes() == (SOURCE / f.name).read_bytes(), f.name


def test_a_tampered_file_is_refused(tmp_path):
    shutil.copytree(VENDORED, tmp_path / PINNED_KEY)
    p = tmp_path / PINNED_KEY / "use-matrix.json"
    p.write_text(p.read_text().replace('"Use Permit"', '"Use Permit!"', 1))
    with pytest.raises(RulesetError, match="use_matrix"):
        load_ruleset(PINNED_KEY, root=tmp_path)


def test_a_non_binding_ruleset_is_refused(tmp_path):
    shutil.copytree(VENDORED, tmp_path / PINNED_KEY)
    m = tmp_path / PINNED_KEY / "manifest.json"
    data = json.loads(m.read_text())
    data["binding"] = False
    m.write_text(json.dumps(data))
    with pytest.raises(RulesetError, match="binding"):
        load_ruleset(PINNED_KEY, root=tmp_path)


def test_cite_returns_code_text():
    r = load_ruleset()
    assert "10,000 sf" in r.cite("8.10.b.1")
    with pytest.raises(RulesetError):
        r.cite("8.99.z.9")


def test_cite_includes_a_lead_ins_items():
    text = load_ruleset().cite("3.13.c.1")
    assert text.startswith("The Code Enforcement Officer reviews and approves:")
    assert "Entrance permits." in text


def test_district_keys_from_trace_codes():
    assert district_key_for("D2") == "d2"
    assert district_key_for("SD-Marine") == "sd-marine"
    assert district_key_for("SD-Highway Commercial") == "sd-hwy"
    assert district_key_for("SD-Civic") is None
