#!/usr/bin/env python3
"""summary_skeleton.py -- the Summary of Changes skeleton, generated from a release plan.

  summary_skeleton.py PLAN.json OUT.md

Names every Article by what happened to it and states what the redline cannot
show. Everything comes from the plan, the manifest's page labels and the adoption
map's baseline; the prose is left for a person. Exit 0: written. Exit 1: refused
(`summary_skeleton: refusing -- ...`), nothing written -- OUT exists, or the plan
is malformed. The write is atomic and never replaces an existing file.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402
import manifest  # noqa: E402

STATUSES = ("SUBSTANTIVE", "RENUMBER-ONLY", "LAYOUT-ONLY", "UNCHANGED")
COUNT_KEYS = ("prose", "heading", "table", "data", "suppressed")
COUNT_WORDS = (("prose", "its text"), ("heading", "its headings"),
               ("table", "its tables"), ("data", "its district or inventory data"))
PLACEHOLDER = ("<!-- Write this in plain words, for residents. Name sections, tables "
               "and roads; do not mention files, paths or scripts. -->")


class Refusal(Exception):
    pass


def validate(plan):
    if not isinstance(plan, dict):
        raise Refusal("the plan is not an object")
    for k in ("version", "date", "old", "articles"):
        if not isinstance(plan.get(k), (str if k != "articles" else dict)):
            raise Refusal(f"the plan has no usable '{k}'")
    arts = plan["articles"]
    for n in map(str, range(1, 10)):
        a = arts.get(n)
        if not isinstance(a, dict):
            raise Refusal(f"Article {n} is missing from the plan")
        if a.get("status") not in STATUSES:
            raise Refusal(f"Article {n} has an unknown status {a.get('status')!r}")
        if not isinstance(a.get("name"), str):
            raise Refusal(f"Article {n} has no name")
        c = a.get("counts")
        if not isinstance(c, dict) or any(not isinstance(c.get(k), int) for k in COUNT_KEYS):
            raise Refusal(f"Article {n} has no usable counts")
        call = a.get("call")
        if a["status"] == "LAYOUT-ONLY" and not (
                isinstance(call, dict) and call.get("reason") and call.get("by")):
            raise Refusal(f"Article {n} is layout-only but carries no call with reason and name")
        if call is not None and not isinstance(call, dict):
            raise Refusal(f"Article {n} has a malformed call")
    sm = plan.get("section_map")
    if sm is not None and not (isinstance(sm, dict) and isinstance(sm.get("renumbered"), int)):
        raise Refusal("the plan's section_map is malformed")
    if not isinstance(plan.get("artifacts", []), list):
        raise Refusal("the plan's artifacts are malformed")


def _join(words):
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def _unit_labels(num):
    units = (manifest.load().get(num) or {}).get("units") or []
    return [u["label"] for u in units if u.get("label")]


def _heading(n, a):
    return f"Article {n}, {a['name']}"


def render(plan):
    validate(plan)
    arts = plan["articles"]
    nums = [str(i) for i in range(1, 10)]
    old = plan["old"]
    base = adoption_map.load().baseline_version
    out = [f"# Summary of Changes — {plan['version']}", "",
           f"{plan['version']}, {plan['date']}. Changes are stated against {old}"
           + (", the Code as most recently adopted." if old == base else "."), ""]

    subst = [n for n in nums if arts[n]["status"] == "SUBSTANTIVE"]
    renum = [n for n in nums if arts[n]["status"] == "RENUMBER-ONLY"]
    layout = [n for n in nums if arts[n]["status"] == "LAYOUT-ONLY"]

    if not (subst or renum or layout):
        out += ["No Article changed in this release.", ""]
    if subst:
        out += ["## Articles with their own extract and redline", ""]
        for n in subst:
            a = arts[n]
            words = [w for k, w in COUNT_WORDS if a["counts"][k] > 0]
            if not words and a.get("call"):
                words = ["its content, by a person's decision"]
            line = f"- {_heading(n, a)}"
            if a.get("new"):
                line += " (added in this release)"
            if words:
                line += f": {_join(words)}"
            out.append(line)
        out.append("")
    if renum:
        out += ["## Articles changed only by renumbering or cross-reference updates", ""]
        out += [f"- {_heading(n, arts[n])}" for n in renum]
        out.append("")
    if layout:
        out += ["## Layout-only changes (a person's call)", ""]
        for n in layout:
            c = arts[n]["call"]
            out.append(f"- {_heading(n, arts[n])}: {c['reason']} (decided by {c['by']})")
        out.append("")

    out += ["## What is new", "", PLACEHOLDER, "", "## What changed", "", PLACEHOLDER, ""]

    cannot = []
    if any(arts[n]["counts"]["table"] > 0 for n in nums):
        cannot.append("Tables are shown unmarked: the redline prints them as they now "
                      "read, without marking what changed in them.")
    for n in nums:
        a = arts[n]
        call = a.get("call") or {}
        applies = (a["counts"]["data"] > 0 or a["status"] == "LAYOUT-ONLY"
                   or call.get("decision") == "substantive")
        labels = _unit_labels(n) if applies else []
        if labels:
            cannot.append(f"In Article {n}, {_join(labels)} are generated pages. "
                          "The redline shows them as they now read, unmarked.")
    renumbered = (plan.get("section_map") or {}).get("renumbered", 0)
    if renumbered > 0:
        s = "" if renumbered == 1 else "s"
        cannot.append(f"{renumbered} section renumbering{s} suppressed as mechanical.")
    if any(x.get("kind") == "use-table-changes" for x in plan.get("artifacts", [])):
        cannot.append("Changes to the use tables are listed in the separate Use Table Changes "
                      "document, not marked in the redline.")
    if cannot:
        out += ["## What the redline cannot show", ""] + [f"- {c}" for c in cannot] + [""]
    return "\n".join(out).rstrip("\n") + "\n"


def write_new(path: Path, text: str):
    """Atomic, and never replaces: write a temp file, then link it into place."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".summary-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise Refusal(f"{path} already exists; it is never overwritten")
    finally:
        os.unlink(tmp)


def main(argv):
    if len(argv) != 3:
        print("usage: summary_skeleton.py PLAN.json OUT.md", file=sys.stderr)
        return 2
    try:
        out = Path(argv[2])
        if out.exists():
            raise Refusal(f"{out} already exists; it is never overwritten")
        try:
            plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise Refusal(f"cannot read the plan: {e}")
        write_new(out, render(plan))
    except Refusal as e:
        print(f"summary_skeleton: refusing -- {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
