"""The rules coverage memo: what the guided builder can check today, and what it can't.

Every count and list here is computed from the pinned ruleset, the standards layer and the
portal's own code. Nothing is typed in by hand, so the memo can be regenerated at any time.
"""

import ast
from collections import Counter, defaultdict
from pathlib import Path

from .ruleset import load_ruleset
from .standards import Standard, load_standards, missing_buildings_table

_STATUS_WORDS = {
    "checkable": "can be checked",
    "needs_qualifier": "no minimum or maximum stated",
    "needs_unit": "no unit stated",
    "not_established": "not set for this district",
    "unresolved": "unresolved in the ruleset",
    "not_a_number": "not a number (who decides)",
}
_GIS_LOAD = Path(__file__).resolve().parent / "gis" / "load.py"


def _bounds(s: Standard) -> str:
    if s.status != "checkable":
        return ""
    parts = []
    if s.min is not None:
        parts.append(f"at least {s.min:g} {s.unit}")
    if s.max is not None:
        parts.append(f"at most {s.max:g} {s.unit}")
    return ", ".join(parts)


def _gis_layers() -> list[str]:
    """The layers the portal loads, read from gis/load.py's insert table (not imported, so this
    works without the GIS libraries)."""
    tree = ast.parse(_GIS_LOAD.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign | ast.Assign):
            targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
            if any(getattr(t, "id", None) == "_INSERT" for t in targets):
                return [k.value for k in node.value.keys]
    return []


def render_audit(today: str) -> str:
    r = load_ruleset()
    standards = load_standards()
    names = {d["district_key"]: d["display_name"] for d in r.districts}
    out: list[str] = []
    w = out.append

    w("# Rules coverage for the guided builder")
    w("")
    w(f"*Generated {today} from the pinned ruleset `{r.key}` by "
      "`python -m portal_api.standards audit`.*")
    w("")
    w("This memo says which of the Code's district standards the guided builder can check today, "
      "which it can't and why, and the questions only the chair can answer. It never fills in a "
      "value the Code doesn't state.")
    w("")

    # 1. Summary
    w("## 1. Summary")
    w("")
    by_status = Counter(s.status for s in standards)
    dims = [s for s in standards if s.source == "dimension"]
    cells = [s for s in standards if s.source == "building_matrix"]
    w(f"{len(standards)} standards across {len(names)} districts: {len(dims)} from the district "
      f"pages' dimension panels and {len(cells)} from the Permitted Buildings tables.")
    w("")
    w("| Status | Count |")
    w("|---|---|")
    for status, words in _STATUS_WORDS.items():
        w(f"| {words} (`{status}`) | {by_status.get(status, 0)} |")
    w("")

    # 2. District by district
    w("## 2. District by district")
    w("")
    for key, name in names.items():
        w(f"### {name}")
        w("")
        w("| Building | Field | Raw | Status | Bounds |")
        w("|---|---|---|---|---|")
        for s in standards:
            if s.district_key == key:
                w(f"| {s.building or ''} | {s.label} | {s.raw} | {s.status} | {_bounds(s)} |")
        w("")

    # 3. Questions for the chair
    w("## 3. Questions only the chair can answer")
    w("")
    w("The Code gives these numbers without a minimum or maximum, without a unit, or with a "
      "footnote whose text is missing. Until the chair answers, the builder can't check them and "
      "never treats them as a \"no\".")
    w("")
    w("Article 5 says what the Permitted Buildings dimensions apply to:")
    w("")
    w("> " + r.cite("5.3.c.4").replace("\n", "\n> "))
    w("")
    n = 0
    bare: dict[str, list[Standard]] = defaultdict(list)
    for s in cells:
        if s.status == "needs_qualifier":
            bare[s.label].append(s)
    for label, group in bare.items():
        n += 1
        w(f"**Q{n}. Is {label} in the Permitted Buildings tables a maximum?** "
          "If not, is it a minimum?")
        w("")
        for s in group:
            w(f"- {names[s.district_key]}, {s.building}: {s.raw}")
        w("")
    for s in standards:
        if s.status == "needs_unit":
            n += 1
            w(f"**Q{n}. What unit is the {s.label} of {s.raw} for {s.building} in "
              f"{names[s.district_key]}?** {s.note}")
            w("")
    for s in standards:
        if s.status == "unresolved":
            n += 1
            where = f"{s.building}, " if s.building else ""
            w(f"**Q{n}. {names[s.district_key]}, {where}{s.label} ({s.raw}).** {s.note}")
            w("")
    for key, name in names.items():
        q = missing_buildings_table(key)
        if q:
            n += 1
            w(f"**Q{n}. {name} has no Permitted Buildings table.** {q}")
            w("")

    # 4. Prose
    w("## 4. What the Code says in prose, not yet checkable")
    w("")
    w("These sections are written as sentences, not as numbers in a table. Each needs either a "
      "rule the builder can check or an approved plain-language entry in the explanation library. "
      "This is the work list later plans are sized from.")
    w("")
    sections: dict[tuple[int, str], dict] = {}
    for node in r._nodes.values():
        if node["article"] in (2, 9):
            continue
        k = (node["article"], node["section"])
        entry = sections.setdefault(k, {"name": node["section_name"],
                                        "article_name": node["article_name"], "nodes": 0})
        entry["nodes"] += 1
    w("| Article | Section | Name | Provisions | Status |")
    w("|---|---|---|---|---|")
    for (art, sec), e in sorted(sections.items(), key=lambda kv: (kv[0][0], int(kv[0][1]))):
        w(f"| {art} ({e['article_name']}) | {sec} | {e['name'].title()} | {e['nodes']} | "
          "prose — needs a rule or a library entry |")
    w("")

    # 5. Shoreland
    w("## 5. Shoreland")
    w("")
    hits = [nd for nd in r._nodes.values() if "shoreland" in nd["text"].lower()]
    w(f"{len(hits)} provisions of the Code mention shoreland. They are quoted here as written, "
      "without interpretation.")
    w("")
    for nd in hits:
        ref = nd["id"].split(":", 1)[1]
        w(f"- `{ref}` ({nd['article_name']}, {nd['section_name'].title()}): {nd['text']}")
    w("")
    layers = _gis_layers()
    if any("shore" in L for L in layers):
        w(f"The portal loads these map layers: {', '.join(layers)}.")
    else:
        w(f"The portal loads these map layers: {', '.join(layers)}. None of them maps a "
          "shoreland zone, so the builder can't yet tell whether a lot is in one.")
    w("")
    w("**Question for the chair:** do the shoreland standards sit in the Core Zoning Code, or "
      "in a separate shoreland ordinance? And where can the portal get a map of the shoreland "
      "zone?")
    w("")

    # 6. Existing permits
    w("## 6. Existing permits and established uses on record")
    w("")
    if not any("permit" in L for L in layers):
        w("No portal data source carries the permits or established uses already on record for a "
          "lot. The builder needs them to tell someone \"you're already covered\".")
    w("")
    w("**Question for the chair:** does the Town keep a record of permits and established uses "
      "by map and lot, and in what form (a spreadsheet, a database, paper files)?")
    w("")
    return "\n".join(out)
