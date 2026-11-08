"""The memo for a batch (design 2, §7): the chair's reading copy, and the Board's for ratification.

Built from the library's files, so it shows exactly what residents would read: every entry, filled
in for each district and building, with its citations, its status and the batch's open questions.
Render it with `build/build-memo.sh`.
"""

from datetime import date

from portal_api.ruleset import load_ruleset

from .model import Library, LibraryEntry
from .render import render

TOWN = "Goes to the Town"
MARK = " *(the Town's reading)*"


def _when(d) -> str:
    d = d if isinstance(d, date) else date.fromisoformat(str(d))
    return f"{d:%B} {d.day}, {d.year}"


def _status(e: LibraryEntry) -> str:
    if e.status == "ratified":
        return f"Ratified by the Planning Board on {_when(e.ratified_on)}."
    if e.status == "approved":
        return f"Approved by {e.approved_by} on {_when(e.approved_on)}; waiting for the Board."
    if e.status == "pulled":
        return f"Pulled on {_when(e.pulled_on)}: {e.pulled_why}"
    return "Draft, not yet approved."


def _rows(e: LibraryEntry, districts: list[dict]) -> tuple[list[str], list[str]]:
    rows, notes = [], []
    by_building = any(k.startswith("building:") for k in e.standards)
    for d in districts:
        cols = (d.get("building_matrix") or {}).get("cols") or []
        for b in (cols or [None]) if by_building else [None]:
            r = render(e, d["district_key"], b)
            shown = TOWN if r is None else r.answer + (MARK if r.interpretations else "")
            rows.append(f"| {d['display_name']} | {b or '—'} | {shown} |")
            for n in (r.interpretations if r else ()):
                if n not in notes:
                    notes.append(n)
    return rows, notes


def render_memo(lib: Library, batch: str, today: str) -> str:
    districts = load_ruleset().districts
    entries = [e for e in lib.entries.values() if e.batch == batch]
    out: list[str] = []
    w = out.append
    w("# MEMORANDUM\n")
    w("**To:** Ben Frey, Planning Board chair, and the Planning Board")
    w("**From:** Applicant Portal build (explanation library)")
    w(f"**Date:** {_when(today)}")
    w(f"**Re:** The explanation library, {batch}: {len(entries)} entries, for review and ratification")
    w(f"**Status:** *Generated {today} from the library's files by `python -m portal_api.library memo {batch}`.*\n")
    w("---\n")
    w("Each entry explains one of the Code's standards in plain words, the way a resident reads it in the "
      "guide. Numbers are never typed into an entry: they are filled in from the Code's tables for each "
      "district and building, as the tables below show. Where the Code gives no value, the standard goes "
      "to the Town. A number marked *(the Town's reading)* rests on the chair's recorded reading where the "
      "Code is silent. Every entry carries the line \"The adopted Code governs if anything here differs "
      "from it.\"\n")
    for e in entries:
        rows, notes = _rows(e, districts)
        w(f"## {e.overline}\n")
        w(f"> {e.answer}\n")
        w(f"{e.detail}\n")
        w(f"**Why the rule exists:** {e.why}\n")
        w(f"**The Code:** {', '.join(e.cites)}" + (f" · **Defined terms:** {', '.join(e.terms)}" if e.terms else "") + "\n")
        w("| District | Building | What a resident reads |")
        w("|:---|:---|:---|")
        out.extend(rows)
        w("")
        for n in notes:
            w(f"*The Town's reading:* {n}\n")
        w(f"**Status:** {_status(e)} (`{e.id}`, version {e.version})\n")
    questions = lib.open_questions.get(batch) or ()
    if questions:
        w("## Questions for the chair\n")
        out.extend(f"{i}. {q}" for i, q in enumerate(questions, 1))
        w("")
    return "\n".join(out)
