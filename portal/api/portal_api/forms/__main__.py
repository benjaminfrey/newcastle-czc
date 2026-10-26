"""Tools for the screener's definitions and the application forms.

  python -m portal_api.forms review-sheet > memos/<date>-screener-rules-for-approval.md
  python -m portal_api.forms forms-sheet > memos/<date>-application-forms-for-approval.md

The review sheet lists every entry with what applicants would read, the Code section
it rests on (quoted from the pinned ruleset), any ruling, and whether the chair has
approved it — a standing record, and the worklist when entries are drafts.
"""

import argparse
from datetime import date

from portal_api.forms.definitions import Definitions, load_definitions
from portal_api.forms.screener import APP_FOR_CODE
from portal_api.ruleset import Ruleset, load_ruleset

# The nine questions from drafting, as the chair answered them on 2026-10-18.
RULINGS_ON = "2026-10-18"
RULINGS = [
    ("An owner's own home", "Any home, whether the owner lives in it or rents it out, is the Residence use, "
     "so the use table's Residence column decides. Building or placing new homes also runs Residence through the use table."),
    ("Residential Companion time limit", "§17.c.1 sends the procedure to §15.D, so §15.d.1's 30 days are shown."),
    ("Dividing into fewer than three lots", "The screener asks whether the land was divided in the last five years. "
     "No earlier division: not a subdivision under §12.b.1. An earlier division: 'you may need' a Subdivision and the "
     "Code Enforcement Officer confirms how the lots count. Unknown: the cautious wording."),
    ("Large additions", "Additions over 10,000 sf of floor area are a Large Project Plan. §11.b does not list "
     "additions, so this rests on §11.b.1 and the ruling (open item: add additions to §11.b)."),
    ("Renovations", "The 10,000 sf line measures the whole building's floor area."),
    ("MaineDOT entrance permits", "The note applies to any State-owned road, S1 State routes included "
     "(open item: §8.c.1's '(R4 or R5)')."),
    ("Subdivision by homes", "Homes added on the lot within five years count together toward §12.b.3's three "
     "(open item for counsel: confirm 30-A M.R.S. §4401(4))."),
    ("Who reviews a Large Project Plan", "The Code Enforcement Officer, who may send it to the Planning Board "
     "for a public hearing (§11.c.3; §10.c.3 for the Small Project Plan); the Board's 30 + 30 days are shown "
     "'if sent to the Planning Board'."),
    ("Use-table codes", "Confirmed: " + ", ".join(f"`{c}` → {a.replace('_', ' ')}" for c, a in APP_FOR_CODE.items())
     + "; the D3 `rc sp` cell needs both; a blank cell means the Code doesn't list the use in that district."),
]


def _status_line(entry) -> list[str]:
    if entry.status == "approved":
        return [f"- Approved by {entry.approved_by}, on {entry.approved_on}."]
    return ["- **Draft — awaiting the chair's approval.**"]


def _ruling_line(entry) -> list[str]:
    r = getattr(entry, "ruling", None)
    return [f"- Ruling ({r['by']}, {r['on']}): {r['text']}"] if r else []


def _approve_lines() -> str:
    return (f"To approve a draft, change `status: draft` to\n\n```yaml\nstatus: approved\napproved_by: <name>\n"
            f"approved_on: {date.today().isoformat()}\n```\n")


def review_sheet(ruleset: Ruleset, defs: Definitions) -> str:
    drafts = defs.drafts()
    out = [f"# Screener rules: approval record ({ruleset.key})", "",
           "Each entry shows what applicants read, the Code section it rests on (quoted from the adopted "
           "ruleset), any ruling, and its approval. Production refuses the screener while any entry is a draft.",
           "", (f"**{len(drafts)} entries await approval.**" if drafts else
                "**Every entry is approved.** A new or changed entry goes back to draft until the chair approves it."),
           "", _approve_lines(),
           f"## The chair's rulings ({RULINGS_ON})", "",
           *[f"{i}. **{title}.** {text}" for i, (title, text) in enumerate(RULINGS, 1)], "",
           "Entries that rest on a ruling say so below.", ""]
    out += ["## Applications (`applications.yaml`)", ""]
    for a in defs.applications.values():
        clocks = ", ".join(f"{ruleset.clocks[k]['days']} {ruleset.clocks[k]['basis']} days" for k in a.clock_keys) or "none"
        out += [f"### `{a.key}` — {a.code_name}", "", f"- Applicants read: {a.plain}",
                f"- Reviewer: {a.reviewer}", f"- Time limits shown: {clocks}",
                f"- Apply on this site: {'yes' if a.in_portal else 'no (Town Office)'}",
                *_ruling_line(a), *_status_line(a),
                f"- Rests on Art. {a.cite.split('.')[0]} §{'.'.join(a.cite.split('.')[1:])}:", "",
                *[f"  > {line}" for line in ruleset.cite(a.cite).splitlines()], ""]
    out += ["## Rules (`rules.yaml`)", ""]
    for r in defs.rules:
        what = r.outcome.get("text") or (f"names the {r.outcome['application'].replace('_', ' ')}"
                                         if r.outcome["kind"] == "application" else r.outcome["kind"].replace("_", " "))
        out += [f"### `{r.id}`", "", f"- When: `{r.when}`", f"- Then: {what}", *_ruling_line(r), *_status_line(r),
                f"- Rests on Art. {r.cite.split('.')[0]} §{'.'.join(r.cite.split('.')[1:])}:", "",
                *[f"  > {line}" for line in ruleset.cite(r.cite).splitlines()], ""]
    out += ["## Plain examples for each use (`use-groups.yaml`)", "",
            "Each use is shown to applicants with its Code name, the Code's definition word for word, and "
            "the plain example below.", ""]
    labels = {u["use_key"]: u["label"] for u in ruleset.uses}
    for g in defs.groups:
        out += [f"### {g.plain}", ""]
        for u in g.uses:
            out += [f"- `{u.use_key}` — **{labels[u.use_key]}**: {u.example}",
                    f"  - Code: {ruleset.definitions[u.definition_key]['definition']}",
                    f"  {_status_line(u)[0]}"]
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m portal_api.forms")
    p.add_argument("command", choices=["review-sheet", "forms-sheet"])
    args = p.parse_args(argv)
    r = load_ruleset()
    if args.command == "forms-sheet":
        from portal_api.forms.formdefs import FORM_KEYS, latest_version, load_form
        from portal_api.forms.forms_sheet import forms_sheet
        from portal_api.forms.parts import QUESTIONS, load_parts
        print(forms_sheet(r, [load_form(k, latest_version(k), r) for k in (*FORM_KEYS, QUESTIONS)], load_parts()))
    else:
        print(review_sheet(r, load_definitions(r)))


if __name__ == "__main__":
    main()
