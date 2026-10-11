#!/usr/bin/env python3
"""release_plan.py -- what a draft release must contain.

Turns czc_diff's per-Article verdicts, plus a person's WRITTEN calls where a
machine cannot decide, into release-plan.json: the list of artifacts the release
driver must produce. It decides what ships to the Town, so it fails closed -- a
missing or improper call stops the release, naming the Article.

  release_plan.py --old REF --new-dir DIR --version V --date D --out PLAN.json
                  --ships SHIPS.json [--section-map P] [--calls FILE]

Exit 0: both files written.  Exit 1: refused (`release_plan: refusing -- ...` on
stderr), and neither file exists afterwards.

Calls (--calls FILE): {"calls": [{"article": N, "decision": "layout-only" |
"substantive", "reason": "...", "by": "..."}]}. Every NEEDS-CALL Article needs
exactly one. layout-only is allowed only for a NEEDS-CALL Article; substantive may
upgrade any verdict except SUBSTANTIVE (redundant). A call can make a release
ship more, never less. The calls are copied into the plan.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BUILD = Path(__file__).resolve().parent
REPO = BUILD.parent

CALL_KEYS = {"article", "decision", "reason", "by"}
DECISIONS = ("layout-only", "substantive")
VERDICTS = ("SUBSTANTIVE", "NEEDS-CALL", "RENUMBER-ONLY", "UNCHANGED")


class Refusal(Exception):
    pass


def _run(cmd):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)


def _name_via_bash(func_args):
    """Call a function from adoption-name.sh -- the one definition of a name."""
    r = subprocess.run(
        ["bash", "-c", 'source build/adoption-name.sh; "$@"', "_", *func_args],
        cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip("\n"):
        raise Refusal(f"could not name an artifact ({' '.join(func_args)}): {r.stderr.strip()}")
    return r.stdout.rstrip("\n")


def _article_name(new_dir: Path, num: int) -> str:
    """The prose file's frontmatter `article-name` (as article-meta.sh reads it)."""
    pro = _run([sys.executable, str(BUILD / "manifest.py"), "prose", str(num)]).stdout.strip()
    f = new_dir / pro if pro else None
    if f is None or not f.is_file():
        f = next(iter(sorted(new_dir.glob(f"article-0{num}-*.md"))), None)
    if f is None:
        raise Refusal(f"Article {num}: no prose file in {new_dir}")
    m = re.match(r"^---\n(.*?)\n---", f.read_text(encoding="utf-8"), re.S)
    val = ""
    if m:
        for ln in m.group(1).split("\n"):
            if ln.startswith("article-name:"):
                val = ln.split(":", 1)[1].strip().strip('"')
                break
    if not val:
        raise Refusal(f"Article {num}: {f.name} has no frontmatter article-name")
    return val


def _no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        raise Refusal(f"duplicate key {', '.join(repr(k) for k in dup)} in the calls file")
    return dict(pairs)


def load_calls(path):
    """Parse and shape-check a calls file -> list of dicts. Raises Refusal."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"),
                         object_pairs_hook=_no_duplicate_keys)
    except (OSError, ValueError) as e:
        raise Refusal(f"calls file {path} unreadable: {e}")
    if not isinstance(doc, dict) or set(doc) != {"calls"} or not isinstance(doc["calls"], list):
        raise Refusal('calls file must be {"calls": [...]} and nothing else')
    seen = set()
    for i, c in enumerate(doc["calls"]):
        where = f"call #{i + 1}"
        if not isinstance(c, dict):
            raise Refusal(f"{where} is not an object")
        extra = set(c) - CALL_KEYS
        if extra:
            raise Refusal(f"{where} has unknown key(s): {', '.join(sorted(extra))}")
        missing = CALL_KEYS - set(c)
        if missing:
            raise Refusal(f"{where} is missing key(s): {', '.join(sorted(missing))}")
        a = c["article"]
        if isinstance(a, bool) or not isinstance(a, int) or not 1 <= a <= 9:
            raise Refusal(f"{where}: article must be an integer 1-9, got {a!r}")
        if c["decision"] not in DECISIONS:
            raise Refusal(f"Article {a}: decision must be one of {', '.join(DECISIONS)}, got {c['decision']!r}")
        for k in ("reason", "by"):
            if not isinstance(c[k], str) or not c[k].strip():
                raise Refusal(f"Article {a}: call has an empty {k!r}")
        if a in seen:
            raise Refusal(f"Article {a}: more than one call")
        seen.add(a)
    return doc["calls"]


def build(old, new_dir, version, date, section_map=None, calls_path=None):
    """-> (plan dict, ships dict). Raises Refusal; writes nothing."""
    new_dir = Path(new_dir)
    calls = load_calls(calls_path) if calls_path else []
    by_art = {c["article"]: c for c in calls}

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ships_path = td / "ships.json"
        cmd = [sys.executable, str(BUILD / "czc_diff.py"), "--old", old,
               "--new-dir", str(new_dir), "--json", str(ships_path)]
        if section_map:
            cmd += ["--section-map", str(section_map)]
        r = _run(cmd)
        if r.returncode != 0 or not ships_path.is_file():
            msg = (r.stderr.strip() or r.stdout.strip() or "czc_diff failed")
            raise Refusal(f"the change determination was refused: {msg}")
        ships = json.loads(ships_path.read_text(encoding="utf-8"))
        ships["new"] = version      # czc_diff records the --new-dir path; keep no local path

        for n in range(1, 10):          # improper calls are named before missing ones
            rec = ships.get("articles", {}).get(str(n)) or {}
            call, v = by_art.get(n), rec.get("verdict")
            if call is None:
                continue
            if call["decision"] == "layout-only" and v != "NEEDS-CALL":
                raise Refusal(f"Article {n}: layout-only is allowed only for a NEEDS-CALL "
                              f"Article; its verdict is {v}")
            if call["decision"] == "substantive" and v == "SUBSTANTIVE":
                raise Refusal(f"Article {n}: a substantive call is redundant; "
                              "its verdict is already SUBSTANTIVE")

        missing = []
        for n in range(1, 10):
            rec = ships.get("articles", {}).get(str(n))
            if rec is not None and rec.get("verdict") == "NEEDS-CALL" and n not in by_art:
                lines = "\n".join(f"    {s}" for s in rec.get("needs_call", []))
                missing.append(f"Article {n} is NEEDS-CALL and has no call:\n{lines}")
        if missing:
            raise Refusal("a person must decide, in writing (--calls), whether each of these is "
                          "layout-only or substantive.\n" + "\n".join(missing))

        arts = {}
        for n in range(1, 10):
            rec = ships.get("articles", {}).get(str(n))
            if rec is None or rec.get("verdict") not in VERDICTS:
                raise Refusal(f"Article {n}: czc_diff gave no usable verdict")
            v = rec["verdict"]
            call = by_art.get(n)
            status = v
            if call is not None:
                status = "LAYOUT-ONLY" if call["decision"] == "layout-only" else "SUBSTANTIVE"
            arts[n] = {
                "name": _article_name(new_dir, n), "verdict": v, "status": status,
                "new": bool(rec.get("new", False)),
                "counts": {k: rec.get(k, 0) for k in ("prose", "heading", "table", "data", "suppressed")},
                "needs_call": list(rec.get("needs_call", [])),
                "call": call,
            }
        # Calls for an Article the determination does not call for are caught above
        # (layout-only) or are upgrades; an Article outside 1-9 was refused on load.

        # Use Table Changes: decided by running the tool itself.
        utc_out = td / "utc.md"
        r = _run([sys.executable, str(BUILD / "use_table_changes.py"), old, str(utc_out),
                  "--new-dir", str(new_dir)])
        if r.returncode == 0:
            utc = True
        elif r.returncode == 2:
            utc = False
        else:
            raise Refusal("the Use Table Changes could not be determined: "
                          f"{(r.stderr.strip() or r.stdout.strip())}")

    renumbered = None
    if section_map:
        try:
            sm = json.loads(Path(section_map).read_text(encoding="utf-8"))
            renumbered = sum(len(v) for v in sm.get("articles", {}).values())
        except (OSError, ValueError, AttributeError) as e:
            raise Refusal(f"section map {section_map} unreadable: {e}")

    def nm(*a):
        return _name_via_bash(list(a))

    integ = nm("czc_integrated_name", "draft", version)
    artifacts = [
        {"kind": "integrated", "article": None, "files": [f"{integ}.pdf", f"{integ}.md"]},
        {"kind": "integrated-redline", "article": None,
         "files": [f"{integ} — Redline.pdf", f"{integ} — Redline.md"]},
    ]
    for n in range(1, 10):
        if arts[n]["status"] != "SUBSTANTIVE":
            continue
        s = nm("czc_standalone_name", "draft", str(n), arts[n]["name"], version)
        sr = nm("czc_standalone_name", "draft", str(n), arts[n]["name"], version, "redline")
        artifacts.append({"kind": "standalone", "article": n, "files": [f"{s}.pdf", f"{s}.md"]})
        artifacts.append({"kind": "standalone-redline", "article": n, "files": [f"{sr}.pdf", f"{sr}.md"]})
    if utc:
        artifacts.append({"kind": "use-table-changes", "article": 2,
                          "files": [f"Use Table Changes {version}.md", f"Use Table Changes {version}.pdf"]})
    artifacts.append({"kind": "summary", "article": None, "files": [f"Summary of Changes {version}.md"]})
    artifacts.append({"kind": "record", "article": None, "files": ["release-plan.json", "ships.json"]})

    plan = {
        "schema": 1, "version": version, "date": date, "mode": "draft", "old": old,
        "section_map": None if renumbered is None else {"renumbered": renumbered},
        "articles": {str(n): arts[n] for n in range(1, 10)},
        "artifacts": artifacts,
    }
    return plan, ships


def _atomic_write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--old", required=True)
    ap.add_argument("--new-dir", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ships", required=True)
    ap.add_argument("--section-map")
    ap.add_argument("--calls")
    a = ap.parse_args(argv)
    out, ships_out = Path(a.out), Path(a.ships)
    # A refusal must never leave an earlier run's plan looking current.
    for p in (out, ships_out):
        if p.exists():
            p.unlink()
    try:
        if subprocess.run([sys.executable, str(BUILD / "version_state.py"), "--require", "draft",
                           a.version], cwd=REPO, capture_output=True).returncode != 0:
            raise Refusal(f"{a.version} is not a draft version")
        plan, ships = build(a.old, a.new_dir, a.version, a.date, a.section_map, a.calls)
        _atomic_write(ships_out, ships)
        _atomic_write(out, plan)
    except Refusal as e:
        for p in (out, ships_out):
            if p.exists():
                p.unlink()
        print(f"release_plan: refusing -- {e}", file=sys.stderr)
        return 1
    print(f"release_plan: {len(plan['artifacts'])} artifact group(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
