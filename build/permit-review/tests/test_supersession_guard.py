"""A superseded ruleset's content may not be rewritten.

The hazard these tests pin: `build_ruleset.py` rebuilds `rulesets/adopted/` from the
working tree, and `rulesets/adopted` is the Code adopted November 3, 2020, superseded
by CZC v1.0 on September 14, 2026. Nine sample decisions cite it and
`--verify-citations` resolves 157 citations against it. A rebuild would succeed
quietly and move the ground under decided cases.

Every test here has a negative control: the guard must also NOT fire where writing is
legitimate, or it would block `build_edition.py` from recording supersession and block
every rebuild of the current Code.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

from ruleset_build import supersession  # noqa: E402
from ruleset_build.supersession import (  # noqa: E402
    SupersededRuleset,
    refuse_if_superseded,
    refuse_if_superseded_path,
)


@pytest.fixture()
def rulesets(tmp_path, monkeypatch):
    """A rulesets/ dir with one superseded and one active ruleset."""
    for key, status in (("old-code", "superseded"), ("current-code", "active")):
        d = tmp_path / key
        d.mkdir()
        manifest = {"ruleset_key": key, "binding": True, "status": status}
        if status == "superseded":
            manifest["superseded_by"] = {"ruleset_key": "current-code", "on": "2026-09-14"}
        (d / "manifest.json").write_text(json.dumps(manifest))
        (d / "use-matrix.json").write_text('{"cells": []}')
    monkeypatch.setattr(supersession, "RULESETS_DIR", tmp_path)
    return tmp_path


# --- the guard fires ---------------------------------------------------------

def test_content_of_a_superseded_ruleset_is_refused(rulesets):
    with pytest.raises(SupersededRuleset) as exc:
        refuse_if_superseded_path(rulesets / "old-code" / "use-matrix.json")
    msg = str(exc.value)
    assert "nothing was written" in msg.lower()
    assert "current-code" in msg and "2026-09-14" in msg
    assert "build_edition" in msg, "the message must name the supported route"


def test_the_key_form_fires_too(rulesets):
    with pytest.raises(SupersededRuleset):
        refuse_if_superseded("old-code")


def test_nothing_is_written_when_it_fires(rulesets):
    before = (rulesets / "old-code" / "use-matrix.json").read_text()
    with pytest.raises(SupersededRuleset):
        refuse_if_superseded_path(rulesets / "old-code" / "use-matrix.json")
    assert (rulesets / "old-code" / "use-matrix.json").read_text() == before


# --- the negative controls: it must NOT fire here ----------------------------

def test_the_manifest_itself_is_always_writable(rulesets):
    """build_edition.py records supersession by writing this file. If the guard
    caught it, a Code could never be superseded at all."""
    refuse_if_superseded_path(rulesets / "old-code" / "manifest.json")


def test_an_active_ruleset_is_not_guarded(rulesets):
    refuse_if_superseded_path(rulesets / "current-code" / "use-matrix.json")
    refuse_if_superseded("current-code")


def test_a_path_outside_rulesets_is_not_guarded(rulesets, tmp_path):
    refuse_if_superseded_path(tmp_path / "exports" / "something.json")


def test_an_unknown_ruleset_is_not_guarded(rulesets):
    refuse_if_superseded("never-built")


# --- the real repository state -----------------------------------------------

def test_the_2020_ruleset_really_is_marked_superseded():
    """Pins the premise of the wiring tests below. If this fails, either the
    rollover was undone or the manifest moved."""
    manifest = json.loads((APP_ROOT / "rulesets" / "adopted" / "manifest.json").read_text())
    assert manifest["status"] == "superseded"
    assert manifest["superseded_by"]["ruleset_key"] == "adopted-v1.0"


def test_the_current_code_is_not_guarded():
    """The guard must leave the Code in force fully rebuildable."""
    refuse_if_superseded("adopted-v1.0")


# --- wiring: the guard is actually invoked where the hazard lives -------------

@pytest.mark.parametrize("module_name, hook", [
    ("ruleset_build.build_ruleset", "step_extract_adopted"),
    ("ruleset_build.lift_use_matrix", "main"),
    ("ruleset_build.extract_adopted", "main"),
    ("ruleset_build.lift_districts", "main"),
    ("ruleset_build.build_clocks", "build_clocks"),
    ("ruleset_build.build_subdivision_criteria", "build"),
])
def test_every_writer_invokes_the_guard(module_name, hook):
    """Source-level check: each entry point that writes into rulesets/<key>/ names
    the guard. A test that only exercised one path would let the others regress."""
    import importlib
    import inspect

    mod = importlib.import_module(module_name)
    src = inspect.getsource(getattr(mod, hook))
    assert "refuse_if_superseded" in src, f"{module_name}.{hook} does not call the guard"


def test_lift_use_matrix_refuses_the_superseded_ruleset_without_writing():
    """End to end on the real repository: the committed 2020 use-matrix is
    untouched by an attempt to rebuild it."""
    from ruleset_build import lift_use_matrix

    target = APP_ROOT / "rulesets" / "adopted" / "use-matrix.json"
    before = target.read_bytes()
    with pytest.raises(SupersededRuleset):
        lift_use_matrix.main(["--ruleset-key", "adopted"])
    assert target.read_bytes() == before
