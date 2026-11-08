"""The explanation library's commands (design 2, §7).

  python -m portal_api.library role <email> <applicant|staff|admin>
"""

import argparse
import sys

from sqlalchemy import create_engine

from portal_api import auth
from portal_api.config import Settings

ROLES = ("applicant", "staff", "admin")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m portal_api.library")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("role", help="give an account a role (the chair and the CEO need staff)")
    r.add_argument("email")
    r.add_argument("role", choices=ROLES)
    args = p.parse_args(argv)

    if args.command == "role":
        with create_engine(Settings().database_url).begin() as conn:
            changed = auth.set_role(conn, args.email, args.role)
        if changed is None:
            print(f"No account for {args.email}: they sign in once first.", file=sys.stderr)
            return 1
        print(f"{args.email}: {changed[0]} -> {changed[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
