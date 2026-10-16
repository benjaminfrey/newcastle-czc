"""Tools for the screener's definitions.

  python -m portal_api.forms review-sheet > memos/<date>-screener-rules-for-approval.md

The review sheet lists every draft entry with what applicants would read, the Code
section it rests on and that section's text quoted from the pinned ruleset, so the
chair can approve entries one by one.
"""

import argparse
from datetime import date

from portal_api.forms.definitions import Definitions, load_definitions
from portal_api.forms.screener import APP_FOR_CODE
from portal_api.ruleset import Ruleset, load_ruleset

# Questions that came up while drafting; they need the chair's answer, not a guess.
DRAFTING_QUESTIONS = [
    "**An owner's own home.** The use table has no use for a home the owner lives in: *Residence* is "
    "defined as a dwelling \"rented, leased, let, or hired out\". So someone building their own house "
    "is told only about the Small Project Plan, and has no use to choose. Is that right, or does an "
    "owner-occupied home need something more?",
    "**Residential Companion permits have no time limit in the Code's clocks.** §17.c.1 says the "
    "procedure follows §15.D, but the clock for §15.d.1 lists only Use and Expanded Use permits. The "
    "screener therefore shows no time limit for a Residential Companion permit. Should it show 30 days?",
    "**Dividing into fewer than three lots** is not a subdivision (§12.b.1). The draft tells the person "
    "to ask the Code Enforcement Officer rather than guessing what else applies.",
    "**A Large Project Plan is the Code Enforcement Officer's** (§11.c.1), though §11.d.4 also gives "
    "the Planning Board a hearing and decision in some cases. The draft names the CEO as reviewer.",
    "**Use-table codes become applications** as follows: "
    + ", ".join(f"`{c}` → {a.replace('_', ' ')}" for c, a in APP_FOR_CODE.items())
    + "; a blank cell means the Code doesn't list the use in that district.",
]


def _approve_lines() -> str:
    return (f"To approve, change `status: draft` to\n\n```yaml\nstatus: approved\napproved_by: <name>\n"
            f"approved_on: {date.today().isoformat()}\n```\n")


def review_sheet(ruleset: Ruleset, defs: Definitions) -> str:
    draft_ids = {(d.file, d.id) for d in defs.drafts()}
    out = [f"# Screener rules for approval ({ruleset.key})", "",
           "Every entry below is a **draft**. Production will not show applicants any answer that rests on "
           "a draft. Each entry shows what applicants would read, the Code section it rests on, and that "
           "section quoted from the adopted ruleset.", "", _approve_lines(),
           "## Questions from drafting", "", *[f"{i}. {q}" for i, q in enumerate(DRAFTING_QUESTIONS, 1)], ""]
    out += ["## Applications (`applications.yaml`)", ""]
    for a in defs.applications.values():
        if ("applications.yaml", a.key) not in draft_ids:
            continue
        clocks = ", ".join(f"{ruleset.clocks[k]['days']} {ruleset.clocks[k]['basis']} days" for k in a.clock_keys) or "none"
        out += [f"### `{a.key}` — {a.code_name}", "", f"- Applicants read: {a.plain}",
                f"- Reviewer: {a.reviewer}", f"- Time limits shown: {clocks}",
                f"- Apply on this site: {'yes' if a.in_portal else 'no (Town Office)'}",
                f"- Rests on Art. {a.cite.split('.')[0]} §{'.'.join(a.cite.split('.')[1:])}:", "",
                *[f"  > {line}" for line in ruleset.cite(a.cite).splitlines()], ""]
    out += ["## Rules (`rules.yaml`)", ""]
    for r in defs.rules:
        if ("rules.yaml", r.id) not in draft_ids:
            continue
        what = r.outcome.get("text") or (f"names the {r.outcome['application'].replace('_', ' ')}"
                                         if r.outcome["kind"] == "application" else r.outcome["kind"].replace("_", " "))
        out += [f"### `{r.id}`", "", f"- When: `{r.when}`", f"- Then: {what}",
                f"- Rests on Art. {r.cite.split('.')[0]} §{'.'.join(r.cite.split('.')[1:])}:", "",
                *[f"  > {line}" for line in ruleset.cite(r.cite).splitlines()], ""]
    out += ["## Plain examples for each use (`use-groups.yaml`)", "",
            "Each use is shown to applicants with its Code name, the Code's definition word for word, and "
            "the plain example below.", ""]
    labels = {u["use_key"]: u["label"] for u in ruleset.uses}
    for g in defs.groups:
        out += [f"### {g.plain}", ""]
        for u in g.uses:
            if ("use-groups.yaml", u.use_key) not in draft_ids:
                continue
            out += [f"- `{u.use_key}` — **{labels[u.use_key]}**: {u.example}",
                    f"  - Code: {ruleset.definitions[u.definition_key]['definition']}"]
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m portal_api.forms")
    p.add_argument("command", choices=["review-sheet"])
    p.parse_args(argv)
    r = load_ruleset()
    print(review_sheet(r, load_definitions(r)))


if __name__ == "__main__":
    main()
