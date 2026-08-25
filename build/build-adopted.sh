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

# The Town Meeting edition to verify against. Named explicitly (build-full-czc.sh's
# name for meeting mode, unchanged) rather than discovered by globbing — see the
# ADOPTED_MD/ADOPTED_PDF comment below for why glob discovery is the wrong tool here.
MEETING_MD="$REPO_ROOT/releases/$VERSION/Newcastle CZC (Integrated Draft $VERSION).md"

# Fail fast, and with a legible message, before spending a build on a release
# that has no meeting edition to verify against. Worth calling out because the
# repo prunes old release PDFs from disk (markdown/Summaries stay tracked, but
# a pruned or never-built meeting edition would otherwise surface here as a
# bare FileNotFoundError from the Python identity-gate script, far from this
# script's actual usage error).
if [ ! -f "$MEETING_MD" ]; then
  echo "The Town Meeting edition markdown was not found:" >&2
  echo "  $MEETING_MD" >&2
  echo "It must be built (build-adoption.sh $VERSION <meeting-date>) and present" >&2
  echo "before the adopted edition can be verified against it. If it once existed" >&2
  echo "but was pruned from disk, rebuild it from the '$VERSION' tag first." >&2
  exit 1
fi

# 1. Check out the tagged source into a staging tree. The working tree is not consulted.
STAGE="$(mktemp -d)"
# Build into a SCRATCH output dir, not releases/<version>-adopted/ directly. Both
# gates below run AFTER the build, and a refused run must not leave a complete,
# shipped-looking release directory behind — the hazard is worse here than an
# ordinary build failure, because the artifact would look adopted without having
# been verified. (Same "build to scratch, place only on success" discipline as
# build-redline-full.sh; see also build-adoption.sh's --dry-run flag-validation
# comment, which guards the same class of hazard for the pre-vote freeze.)
SCRATCH_OUT="$(mktemp -d)"
FINAL_OUTDIR="$REPO_ROOT/releases/${VERSION}-adopted"
trap 'rm -rf "$STAGE" "$SCRATCH_OUT"' EXIT
git -C "$REPO_ROOT" archive "$VERSION" source | tar -x -C "$STAGE"

# 2. Render with adopted chrome from the tagged source.
SRC_DIR="$STAGE/source" OUT_DIR="$SCRATCH_OUT" \
ADOPTION_MODE=adopted ADOPTION_EVENT_DATE="$ADOPTION_DATE" \
  bash "$REPO_ROOT/build/build-full-czc.sh" "$VERSION" "$ADOPTION_DATE"

# Named explicitly, not discovered with `ls *.md | head -1`: the adoption
# packet also produces a standalone Article 3 whose filename ("Article 3
# Thoroughfares...") sorts before "Newcastle CZC..." — a glob would silently
# compare the wrong document while the actual integrated adopted edition went
# unverified. build-full-czc.sh names the adopted-mode output "Adopted
# $VERSION" (not "Integrated Draft $VERSION") precisely so the filename itself
# carries no draft chrome (see build-full-czc.sh's OUT_NAME).
ADOPTED_MD="$SCRATCH_OUT/Newcastle CZC (Adopted $VERSION).md"
ADOPTED_PDF="$SCRATCH_OUT/Newcastle CZC (Adopted $VERSION).pdf"

# 3. Content-identity gate. Frontmatter is stripped: it carries footer-date,
#    which is chrome and differs by state by design. Comparing the raw file
#    would fail every run for the one reason that does not matter.
python3 - "$MEETING_MD" "$ADOPTED_MD" <<'PYEOF'
import re, sys, hashlib

# Anchored to the THREE known frontmatter keys (article-number / article-name
# / footer-date), not a bare "next --- line wins". The bare version matches
# any two "---" lines, including a markdown thematic break inside an article
# body -- harmless today (the 9 blocks are always tightly paired, 18 lines
# total) but a silent trap: one added "---" divider would pair a real
# frontmatter open with an unrelated later line and swallow real body text
# from the hash unnoticed. Belt-and-suspenders: also assert the number of
# blocks actually stripped equals the number of "article-number:" lines
# present, and refuse loudly on any mismatch rather than hashing the wrong span.
FRONTMATTER_RE = re.compile(
    r"(?m)^---\n(?:(?:article-number|article-name|footer-date):[^\n]*\n)+---\n"
)

def body(p):
    t = open(p, encoding="utf-8").read()
    expected = len(re.findall(r"(?m)^article-number:", t))
    stripped, n = FRONTMATTER_RE.subn("", t)
    if n != expected:
        print(f"frontmatter-strip mismatch in {p}: stripped {n} block(s), "
              f"expected {expected} (one per 'article-number:' line). Refusing "
              f"rather than hashing the wrong span.", file=sys.stderr)
        raise SystemExit(1)
    return hashlib.sha256(stripped.encode()).hexdigest()

a, b = body(sys.argv[1]), body(sys.argv[2])
if a != b:
    print("ADOPTED BODY DIFFERS FROM THE TOWN MEETING EDITION.", file=sys.stderr)
    print(f"  meeting={a}\n  adopted={b}", file=sys.stderr)
    print("The adopted document must contain exactly what was voted on.", file=sys.stderr)
    raise SystemExit(1)
print(f"Content identity verified (body sha256 {a[:16]}…)")
PYEOF

# 4. Draft-residue gate, on the rendered PDF's extracted text AND on the
#    artifact filenames themselves — a chrome string in the FILENAME is
#    exactly what a page-text-only scan cannot see (Task 8 review, Important 1).
python3 -c "
import pymupdf, sys
d = pymupdf.open(sys.argv[1])
sys.stdout.write(''.join(p.get_text() for p in d))
" "$ADOPTED_PDF" | python3 "$REPO_ROOT/build/adopted_residue.py" "$ADOPTED_PDF" "$ADOPTED_MD"

# 5. Both gates passed. ONLY NOW place the result where it will be found and
#    filed — see the SCRATCH_OUT comment above for why this happens last.
mkdir -p "$FINAL_OUTDIR"
cp "$ADOPTED_MD" "$ADOPTED_PDF" "$FINAL_OUTDIR/"
FINAL_PDF="$FINAL_OUTDIR/$(basename "$ADOPTED_PDF")"

# --- Layout recap (ADOPTION-SPEC.md §6.5: page + blank counts per artifact). -
echo
python3 "$REPO_ROOT/build/pdf_recap.py" "Adopted edition=$FINAL_PDF"

echo
echo "ADOPTED edition built: $FINAL_OUTDIR"
echo "Version $VERSION · adopted $ADOPTION_DATE"
