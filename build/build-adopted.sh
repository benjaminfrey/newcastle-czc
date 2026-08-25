#!/usr/bin/env bash
# Stamp a Town Meeting edition as ADOPTED, after the vote. See ADOPTION-SPEC.md §3.4.
#
# It renders from the TAGGED meeting-edition source, never the working tree, so
# the adopted document structurally cannot contain anything the voters did not
# see. It then asserts the body is byte-identical to what was voted on.
#
# Usage:  build-adopted.sh <version> <adoption-date>
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
ADOPTION_DATE="${2:-}"

if [ -z "$VERSION" ] || [ -z "$ADOPTION_DATE" ]; then
  echo "usage: build-adopted.sh <version> <adoption-date>" >&2
  exit 1
fi

python3 "$REPO_ROOT/build/version_state.py" --require adoption "$VERSION" || exit 1

if ! git -C "$REPO_ROOT" rev-parse -q --verify "refs/tags/$VERSION" >/dev/null; then
  echo "No tag '$VERSION'. The Town Meeting edition must be tagged before it can" >&2
  echo "be adopted — the adopted document is rendered from that tag, not from the" >&2
  echo "working tree, so that it cannot contain anything the voters did not see." >&2
  exit 1
fi

# 1. Check out the tagged source into a staging tree. The working tree is not consulted.
STAGE="$(mktemp -d)"; OUTDIR="$REPO_ROOT/releases/${VERSION}-adopted"
trap 'rm -rf "$STAGE"' EXIT
git -C "$REPO_ROOT" archive "$VERSION" source | tar -x -C "$STAGE"
mkdir -p "$OUTDIR"

# 2. Render with adopted chrome from the tagged source.
SRC_DIR="$STAGE/source" OUT_DIR="$OUTDIR" \
ADOPTION_MODE=adopted ADOPTION_EVENT_DATE="$ADOPTION_DATE" \
  bash "$REPO_ROOT/build/build-full-czc.sh" "$VERSION" "$ADOPTION_DATE"

ADOPTED_MD="$(ls "$OUTDIR"/*.md | head -1)"
ADOPTED_PDF="$(ls "$OUTDIR"/*.pdf | head -1)"
MEETING_MD="$REPO_ROOT/releases/$VERSION/$(basename "$ADOPTED_MD")"

# 3. Content-identity gate. Frontmatter is stripped: it carries footer-date,
#    which is chrome and differs by state BY DESIGN. Comparing the raw file
#    would fail every run for the one reason that does not matter.
python3 - "$MEETING_MD" "$ADOPTED_MD" <<'PYEOF'
import re, sys, hashlib
def body(p):
    t = open(p, encoding="utf-8").read()
    t = re.sub(r"(?ms)^---\n.*?^---\n", "", t)     # YAML frontmatter blocks
    return hashlib.sha256(t.encode()).hexdigest()
a, b = body(sys.argv[1]), body(sys.argv[2])
if a != b:
    print("ADOPTED BODY DIFFERS FROM THE TOWN MEETING EDITION.", file=sys.stderr)
    print(f"  meeting={a}\n  adopted={b}", file=sys.stderr)
    print("The adopted document must contain exactly what was voted on.", file=sys.stderr)
    raise SystemExit(1)
print(f"Content identity verified (body sha256 {a[:16]}…)")
PYEOF

# 4. Draft-residue gate, on the rendered PDF's extracted text.
python3 -c "
import pymupdf, sys
d = pymupdf.open(sys.argv[1])
sys.stdout.write(''.join(p.get_text() for p in d))
" "$ADOPTED_PDF" | python3 "$REPO_ROOT/build/adopted_residue.py"

echo
echo "ADOPTED edition built: $OUTDIR"
echo "Version $VERSION · adopted $ADOPTION_DATE"
