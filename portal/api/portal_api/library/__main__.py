"""The explanation library's commands (design 2, §7). They run on the VM, where the database and
PyYAML are; `unpack.py` brings the changed files back to the Mac's checkout.

  python -m portal_api.library role <email> <applicant|staff|admin>
  python -m portal_api.library decisions                 > decided.json
  python -m portal_api.library apply decided.json --chair <email> [--person <email>=<name>]... --emit > result.json
  python3 portal/api/portal_api/library/unpack.py result.json portal/api/portal_api/library/entries   (on the Mac)
  python -m portal_api.library mark-exported result.json  (after the chair commits the files)
  python -m portal_api.library ratify <batch> <YYYY-MM-DD> [--partial] --emit > result.json
  python -m portal_api.library flag --old <ruleset dir> --new <ruleset dir> [--apply --emit]
      (--apply only when the new ruleset is the adopted one being pinned)
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine

from portal_api import auth
from portal_api.config import Settings

from . import records
from .changes import flag
from .load import DIR
from .write import apply, ratify

ROLES = ("applicant", "staff", "admin")


def _engine():
    return create_engine(Settings().database_url)


def _read(arg: str) -> dict:
    return json.loads(sys.stdin.read() if arg == "-" else Path(arg).read_text())


def _files(root: Path) -> dict:
    return {p.name: p.read_text() for p in sorted(root.glob("*.yaml"))}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m portal_api.library")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("role", help="give an account a role (the chair and the CEO need staff)")
    r.add_argument("email")
    r.add_argument("role", choices=ROLES)
    sub.add_parser("decisions", help="print the review page's pending decisions and pulls, as JSON")
    a = sub.add_parser("apply", help="write decisions into the library's files")
    a.add_argument("decisions", help="the JSON `decisions` printed, or - for stdin")
    a.add_argument("--root", type=Path, default=DIR)
    a.add_argument("--chair", required=True, help="the chair's sign-in email: only he approves")
    a.add_argument("--person", action="append", default=[], help="email=name, for who pulled an entry")
    a.add_argument("--emit", action="store_true", help="also print the changed files, for unpack.py")
    m = sub.add_parser("mark-exported", help="after the commit: the decisions are on the record")
    m.add_argument("result")
    t = sub.add_parser("ratify", help="stamp the Board's ratification on a batch")
    t.add_argument("batch")
    t.add_argument("on", type=date.fromisoformat)
    t.add_argument("--partial", action="store_true")
    t.add_argument("--root", type=Path, default=DIR)
    t.add_argument("--emit", action="store_true")
    f = sub.add_parser("flag", help="list the entries citing what an amendment changed")
    f.add_argument("--old", type=Path, required=True)
    f.add_argument("--new", type=Path, required=True)
    f.add_argument("--apply", action="store_true", help="pull them: only when the amendment is adopted")
    f.add_argument("--root", type=Path, default=DIR)
    f.add_argument("--emit", action="store_true")
    args = p.parse_args(argv)

    if args.command == "role":
        with _engine().begin() as conn:
            changed = auth.set_role(conn, args.email, args.role)
        if changed is None:
            print(f"No account for {args.email}: they sign in once first.", file=sys.stderr)
            return 1
        print(f"{args.email}: {changed[0]} -> {changed[1]}")
    elif args.command == "decisions":
        with _engine().begin() as conn:
            out = {"decisions": records.pending(conn), "superseded": records.superseded(conn),
                   "pulls": records.pulls(conn, unexported=True)}
        print(json.dumps(out, default=str, indent=2))
    elif args.command == "apply":
        people = dict(x.split("=", 1) for x in args.person)
        result = apply(args.root, _read(args.decisions), chair=args.chair, people={k.lower(): v for k, v in people.items()})
        if args.emit:
            result["files"] = _files(args.root)
        print(json.dumps(result, default=str, indent=2))
    elif args.command == "mark-exported":
        result = _read(args.result)
        with _engine().begin() as conn:
            records.mark_exported(conn, result["exported_decisions"], result["exported_pulls"])
            records.clear_pulls(conn, result["cleared_pulls"])
        print(f"{len(result['exported_decisions'])} decisions and {len(result['exported_pulls'])} pulls on the record")
    elif args.command == "ratify":
        try:
            done = ratify(args.root, args.batch, args.on, partial=args.partial)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        out = {"ratified": done, "refused": [], "files": _files(args.root) if args.emit else {}}
        print(json.dumps(out, indent=2))
    elif args.command == "flag":
        hits = flag(args.root, args.old, args.new, apply=args.apply)
        out = {"flagged": hits, "applied": args.apply, "files": _files(args.root) if args.emit and args.apply else {}}
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
