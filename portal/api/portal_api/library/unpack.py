"""Write `apply --emit`'s files into the Mac's checkout, for the chair to review and commit.

The Mac's Python has no PyYAML, so `apply` runs on the VM and sends the files back as JSON; this
script needs only the standard library:

  python3 portal/api/portal_api/library/unpack.py result.json portal/api/portal_api/library/entries
"""

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> list[str]:
    result, out = json.loads(Path(argv[0]).read_text()), Path(argv[1])
    for name, body in sorted(result["files"].items()):
        (out / name).write_text(body)
    for entry_id, why in result["refused"]:
        print(f"refused {entry_id}: {why}", file=sys.stderr)
    return sorted(result["files"])


if __name__ == "__main__":
    print("\n".join(main(sys.argv[1:])))
