"""Trees in which something DID move, for the section-map tests.

Every source/article-*.md is byte-identical to v1.0 (measured 2026-10-08), so a
test that derives v1.0 against the real tree can only ever see "nothing moved",
and passes whether or not the code works. These helpers build trees where a
section was inserted, deleted or retitled, so the assertions can fail.
"""
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_H2 = re.compile(r"^## (\d+)\. ", re.MULTILINE)


def copy_source(dest: Path) -> Path:
    shutil.copytree(REPO / "source", dest)
    return dest


def shift_headings(text: str, start: int, by: int) -> str:
    """Renumber every `## N.` heading with N >= start by `by`. Headings only."""
    return _H2.sub(
        lambda m: f"## {int(m.group(1)) + by}. " if int(m.group(1)) >= start else m.group(0),
        text)


def insert_section(text: str, at: int, title: str, body: str = "New text.") -> str:
    """Insert `## at. TITLE` before the existing `## at.`, shifting it and every
    later heading up by one."""
    shifted = shift_headings(text, at, 1)
    i = shifted.index(f"## {at + 1}. ")
    return shifted[:i] + f"## {at}. {title}\n\n{body}\n\n" + shifted[i:]


def delete_section(text: str, n: int) -> str:
    """Remove `## n.` and its body up to the next `## ` heading, shifting every
    later heading down by one."""
    start = text.index(f"## {n}. ")
    nxt = text.find("\n## ", start + 1)
    out = text[:start] + (text[nxt + 1:] if nxt != -1 else "")
    return shift_headings(out, n + 1, -1)


def retitle(text: str, n: int, new_title: str) -> str:
    return re.sub(rf"^## {n}\. .*$", f"## {n}. {new_title}", text, count=1, flags=re.MULTILINE)
