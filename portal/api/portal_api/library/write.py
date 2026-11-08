"""Writing the review page's decisions into the library's files (design 2, §7), and the Board's
ratification. The files are the Town's record: these functions change them, and the chair commits
the change.

The files are written in one fixed form (keys in a fixed order, no comments), so a decision's diff
is only what changed.
"""

import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from portal_api.ruleset import PINNED_KEY

CHAIR_NAME = "Ben Frey, Planning Board chair"
BOARD = "Planning Board"
ORDER = ("id", "kind", "standards", "overline", "answer", "detail", "why", "slots", "terms", "district_notes",
         "cites", "picture", "picture_alt", "decided_by", "decided_on", "source", "ruleset", "version", "status",
         "approved_by", "approved_on", "ratified_on", "ratified_by", "pulled_on", "pulled_by", "pulled_why",
         "review_note")
_TOWN = ZoneInfo("America/New_York")
_APPROVAL = ("approved_by", "approved_on", "ratified_on", "ratified_by")
_PULL = ("pulled_on", "pulled_by", "pulled_why")
TEXTS = ("overline", "answer", "detail", "why")


def read_batch(path: Path) -> tuple[list[dict], list[str]]:
    data = yaml.safe_load(path.read_text()) or {}
    return list(data.get("entries") or []), list(data.get("open_questions") or [])


def _ordered(e: dict) -> dict:
    return {k: e[k] for k in ORDER if k in e} | {k: v for k, v in e.items() if k not in ORDER}


def dump_batch(path: Path, entries: list[dict], open_questions: list[str]) -> None:
    doc = {"entries": [_ordered(e) for e in entries], "open_questions": list(open_questions)}
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=10_000))
    from .load import _load
    _load.cache_clear()   # a later load in this process reads what was just written


def _day(at: str) -> date:
    return datetime.fromisoformat(at).astimezone(_TOWN).date()


def _drop(e: dict, keys) -> None:
    for k in keys:
        e.pop(k, None)


def apply(root: Path, data: dict, *, chair: str, people: dict[str, str]) -> dict:
    """Write `decisions`' output into the batch files under `root`. Each decision or pull either
    applies or is refused, with its reason; nothing refused is marked exported."""
    from .load import check_edit, load_library
    lib = load_library(root)
    batches = {p.stem: read_batch(p) for p in sorted(root.glob("*.yaml"))}
    where = {e["id"]: (b, e) for b, (es, _) in batches.items() for e in es}
    names = {**people, chair.lower(): CHAIR_NAME}
    applied, refused, cleared, done_d, done_p, touched = [], [], [], list(data.get("superseded") or []), [], set()
    pulls = {p["entry_id"]: p for p in data.get("pulls") or []}

    for p in pulls.values():
        b, e = where.get(p["entry_id"], (None, None))
        who = names.get(p["pulled_by_email"].lower())
        if e is None:
            refused.append([p["entry_id"], "no such entry"])
        elif who is None:
            refused.append([p["entry_id"], f"unknown person: {p['pulled_by_email']}"])
        elif p["version"] != e["version"]:
            refused.append([p["entry_id"], f"stale: the file is at version {e['version']}"])
        elif e["status"] == "draft":
            refused.append([p["entry_id"], "a draft is not shown, so its pull stays on the page only"])
        else:
            e.update(status="pulled", pulled_on=_day(p["pulled_at"]), pulled_by=who, pulled_why=p["why"])
            done_p.append({"entry_id": p["entry_id"], "pulled_at": p["pulled_at"]})
            touched.add(b)

    for d in data.get("decisions") or []:
        b, e = where.get(d["entry_id"], (None, None))
        if e is None:
            refused.append([d["entry_id"], "no such entry"])
            continue
        if d["version"] != e["version"]:
            refused.append([d["entry_id"], f"stale: the file is at version {e['version']}"])
            continue
        if d.get("body") and (bad := check_edit(lib.entries[d["entry_id"]], d["body"])):
            refused.append([d["entry_id"], f"the edit fails its checks: {bad}"])
            continue
        if d["action"] == "approve":
            if d["decided_by_email"].lower() != chair.lower():
                refused.append([d["entry_id"], "only the chair approves"])
                continue
            pull = pulls.get(d["entry_id"])
            if e["status"] == "pulled" or (pull and pull["version"] == e["version"]):
                refused.append([d["entry_id"], "pulled at this version: edit it first"])
                continue
            _drop(e, _APPROVAL + _PULL + ("review_note",))
            if d.get("body"):   # the edited text, approved as a new version
                e.update({k: d["body"][k] for k in TEXTS}, version=e["version"] + 1)
            e.update(status="approved", approved_by=CHAIR_NAME, approved_on=_day(d["decided_at"]), ruleset=PINNED_KEY)
            cleared.append({"entry_id": d["entry_id"], "version": e["version"]})   # pulls of older versions
        else:
            _drop(e, _APPROVAL + _PULL)
            if d["action"] == "edit":
                e.update({k: d["body"][k] for k in TEXTS}, version=e["version"] + 1)
            e["status"] = "draft"
            if d.get("note"):
                e["review_note"] = d["note"]
            else:
                e.pop("review_note", None)
        applied.append(d["entry_id"])
        done_d.append(d["id"])
        touched.add(b)

    for b in touched:
        dump_batch(root / f"{b}.yaml", *batches[b])
    return {"applied": applied, "refused": refused, "cleared_pulls": cleared,
            "exported_decisions": done_d, "exported_pulls": done_p}


_MEMO_LINE = re.compile(r"\(`([^`]+)`, version (\d+)\)")


def memo_versions(memo: Path) -> dict[str, int]:
    """Each entry and the version the Board's memo showed it at."""
    return {m[1]: int(m[2]) for m in _MEMO_LINE.finditer(memo.read_text())}


def ratify(root: Path, batch: str, on: date, *, partial: bool = False, versions: dict[str, int] | None = None) -> list[str]:
    """Stamp the Board's ratification on the approved entries of `batch` that its memo showed, at the
    version it showed (`versions`, from memo_versions); the ids stamped. An entry changed since the
    memo is refused: the Board ratifies what it read (the review, 2026-11-08)."""
    path = root / f"{batch}.yaml"
    entries, questions = read_batch(path)
    drafts = [e["id"] for e in entries if e["status"] == "draft"]
    if drafts and not partial:
        raise ValueError(f"{', '.join(drafts)} {'is' if len(drafts) == 1 else 'are'} still a draft: "
                         "ratify the rest with --partial, or wait")
    changed = [f"{e['id']} is at version {e['version']}; the memo showed version {versions[e['id']]}"
               for e in entries if versions is not None and e["id"] in versions and e["version"] != versions[e["id"]]]
    if changed:
        raise ValueError("; ".join(changed))
    done = []
    for e in entries:
        if e["status"] == "approved" and (versions is None or e["id"] in versions):
            e.update(status="ratified", ratified_on=on, ratified_by=BOARD)
            done.append(e["id"])
    dump_batch(path, entries, questions)
    return done
