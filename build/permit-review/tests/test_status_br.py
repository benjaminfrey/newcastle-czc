"""The fifth use-table status, `br` / ○ "No Permit Required" (Right to Farm,
plans/2026-10-14-right-to-farm-plan-a-status-code.md; decisions R1-R5).

The app reads the legend row but does not yet model a permit-free cell: its
citation sentence would print a `br` cell as "not allowed". Until the app plan
teaches it, building a ruleset that contains a `br` cell is refused
(DECISIONS-NEEDED.md D-0035). `br` combined with another code is refused for
good (release-machinery spec D3).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))

from ruleset_build.build_use_matrix import UseMatrixBuildError, build_use_matrix  # noqa: E402
from ruleset_build.legend import (  # noqa: E402
    EXPECTED_BR_ROW, NOTE_WITH_BR, LegendParseError, parse_legend,
)

SRC = REPO_ROOT / "source" / "article-02-data.json"

LEGEND_WITH_BR = """
#let glyphs = (u: "●", rc: "❶", sp: "❷", ex: "✪", br: "○")
USE TABLE LEGEND
status("u"), [Use Permit Required], [CEO],
status("rc"), [Residential Companion Permit Required], [CEO],
status("sp"), [Special Permit Required], [Planning Board],
status("ex"), [Expanded Use Permit Required], [Planning Board],
status("br"), [No Permit Required], [—],
)
text(size: 8pt)[Note: Uses without #status("u"), #status("rc"), #status("sp"), #status("ex"), or #status("br") are not allowed in this District. Uses marked #status("br") require no permit but must meet the standards of Article 7 Section 3.]
"""


def _v10_typ() -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", "v1.0:source/article-02.typ"],
        capture_output=True, text=True, check=True).stdout


def test_the_br_row_is_read():
    rows = parse_legend(LEGEND_WITH_BR)
    assert [r["code"] for r in rows] == ["u", "rc", "sp", "ex", "br", ""]
    br = next(r for r in rows if r["code"] == "br")
    assert br == EXPECTED_BR_ROW
    assert br["permit"] + " Required" == "No Permit Required"
    assert br["authority"] == "—" and br["authority_key"] is None


def test_the_two_sentence_note_is_read_whole():
    rows = parse_legend(LEGEND_WITH_BR)
    assert rows[-1]["note"] == NOTE_WITH_BR
    assert NOTE_WITH_BR == ("Uses without u, rc, sp, ex, or br are not allowed in this District. "
                            "Uses marked br require no permit but must meet the standards of "
                            "Article 7 Section 3.")


def test_the_v10_four_code_legend_still_parses():
    rows = parse_legend(_v10_typ())
    assert [r["code"] for r in rows] == ["u", "rc", "sp", "ex", ""]
    assert rows[-1]["note"] == "Uses without u, rc, sp, or ex are not allowed in this District."


def test_an_unknown_legend_code_is_refused():
    bad = LEGEND_WITH_BR.replace('br: "○")', 'br: "○", zz: "◆")').replace(
        'status("br"), [No Permit Required], [—],',
        'status("br"), [No Permit Required], [—],\nstatus("zz"), [Odd Permit Required], [CEO],')
    with pytest.raises(LegendParseError, match="zz"):
        parse_legend(bad)


def test_a_br_row_with_the_wrong_symbol_is_refused():
    with pytest.raises(LegendParseError, match="br"):
        parse_legend(LEGEND_WITH_BR.replace('br: "○"', 'br: "◎"'))


def _data_with(code: str, tmp_path: Path) -> tuple[Path, Path]:
    districts = json.loads(SRC.read_text(encoding="utf-8"))
    districts[0]["use_col1"][0]["entries"][0][1] = code
    data = tmp_path / "article-02-data.json"
    data.write_text(json.dumps(districts), encoding="utf-8")
    typ = tmp_path / "article-02.typ"
    typ.write_text(LEGEND_WITH_BR, encoding="utf-8")
    return data, typ


def test_a_br_cell_is_refused_not_misread(tmp_path):
    data, typ = _data_with("br", tmp_path)
    with pytest.raises(UseMatrixBuildError, match=r"br.*D-0035"):
        build_use_matrix(data, typ, "adopted")


@pytest.mark.parametrize("combo", ["br u", "u br", "rc br"])
def test_br_combined_with_another_code_is_refused(tmp_path, combo):
    data, typ = _data_with(combo, tmp_path)
    with pytest.raises(UseMatrixBuildError, match="br"):
        build_use_matrix(data, typ, "adopted")


def test_the_refusal_states_the_real_risk(tmp_path):
    """Review of Plan A, finding 3: citation.py would not print a br cell as a
    prohibition -- the br row's permit, "No Permit", is truthy -- it would print
    'requires a No Permit which must be issued by the —'. Say that."""
    data, typ = _data_with("br", tmp_path)
    with pytest.raises(UseMatrixBuildError) as e:
        build_use_matrix(data, typ, "adopted")
    assert "prohibition" not in str(e.value)
    assert "requires a No Permit" in str(e.value)
