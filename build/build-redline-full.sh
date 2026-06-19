#!/usr/bin/env bash
# Formatted full-CZC redline — the integrated draft in its full publication
# layout (two-column body, Article openers, rotated fore-edge tab, running
# heads, footers, and all native figures) with PROSE changes marked inline:
# additions in red, deletions struck through.
#
# A redline is a TEXT diff, so only prose can be marked. The native-Typst
# figures (Type plates, Article-2 district spreads, district maps, Exhibit 3.1
# inventory, Exhibit 3.2 map) and inline raw-Typst tables render at their
# CURRENT (new) state, UNMARKED — figure/data changes are narrated in the
# hand-written Summary of Changes. This replaces the plain single-column text
# redline (build/build-redline.sh, now legacy/text-only).
#
# How it works: copy the working-tree source/ into a staging tree (so the native
# .typ units render the current figures), rewrite each article-*.md in place with
# redline-text.py --source (vs the OLD version's file from git), then run the
# normal integrated build (build-full-czc.sh) against the stage. The build's
# data-driven page-offset/parity machinery handles the longer marked document
# automatically — no special parity handling here.
#
# Usage:
#   build-redline-full.sh <new-ver> [old-ver] [date-str]
#     <new-ver>   labels the output + cover banner; the NEW content compared is
#                 the current working tree (source/ as it stands).
#     [old-ver]   git ref to compare against (default: the tag preceding
#                 <new-ver>'s commit).
#     [date-str]  cover date (default: today; pass explicitly for reproducible
#                 rebuilds, per build-full-czc.sh).
#
# Output: releases/<new-ver>/Newcastle CZC (Integrated Draft <new-ver>) — Redline.pdf
#   Override the destination with REDLINE_OUT=/path/out.pdf — e.g. a /tmp
#   dry-run that must not overwrite a shipped release deliverable.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REDLINE_PY="$REPO_ROOT/build/redline-text.py"
SRC="$REPO_ROOT/source"

NEW_V="${1:-}"
OLD_V="${2:-}"
DATE_STR="${3:-$(date +"%B %-d, %Y")}"

if [ -z "$NEW_V" ]; then
  echo "usage: build-redline-full.sh <new-ver> [old-ver] [date-str]" >&2
  exit 1
fi

if [ -z "$OLD_V" ]; then
  OLD_V="$(git -C "$REPO_ROOT" describe --tags --abbrev=0 "${NEW_V}^" 2>/dev/null || true)"
  if [ -z "$OLD_V" ]; then
    echo "Could not auto-detect the prior version for '$NEW_V'; pass <old-ver> explicitly." >&2
    exit 1
  fi
fi

echo "Formatted redline:  NEW = working tree (labeled $NEW_V)   vs   OLD = $OLD_V"

# 1. Stage the NEW source (working tree). The native .typ/json/svg are copied
#    verbatim, so every figure renders at its CURRENT state.
STAGE="$(mktemp -d)"
OUTDIR="$(mktemp -d)"
trap 'rm -rf "$STAGE" "$OUTDIR"' EXIT
cp -R "$SRC/." "$STAGE/"

# 2. Rewrite each article markdown in place: OLD = that file at <old-ver> (from
#    git), NEW = the staged working-tree file. --source preserves frontmatter +
#    split markers, marks prose, and emits figures/tables/headings unmarked.
OLDTMP="$OUTDIR/old.md"
shopt -s nullglob
n=0
for nf in "$STAGE"/article-*.md; do
  base="$(basename "$nf")"
  if ! git -C "$REPO_ROOT" show "$OLD_V:source/$base" > "$OLDTMP" 2>/dev/null; then
    : > "$OLDTMP"   # file is new since OLD: empty OLD -> whole body marked added
    echo "  ($base is new since $OLD_V — whole body marked as added)"
  fi
  python3 "$REDLINE_PY" "$OLDTMP" "$nf" "$nf" --source
  n=$((n + 1))
done
rm -f "$OLDTMP"
echo "Marked $n article markdown file(s) (vs $OLD_V)."

# 3. Build the integrated draft against the staged (marked) source. SRC_DIR
#    redirects the build's content; OUT_DIR keeps its output out of releases/;
#    REDLINE_CAVEAT stamps the cover. Neither source/ nor releases/ is touched.
CAVEAT="REDLINE vs $OLD_V  ·  additions in red, deletions struck  ·  figures & tables shown at current state (see the Summary of Changes)"
SRC_DIR="$STAGE" OUT_DIR="$OUTDIR" REDLINE_CAVEAT="$CAVEAT" \
  bash "$REPO_ROOT/build/build-full-czc.sh" "$NEW_V" "$DATE_STR"

BUILT="$OUTDIR/Newcastle CZC (Integrated Draft $NEW_V).pdf"
if [ ! -f "$BUILT" ]; then
  echo "Build did not produce the expected PDF: $BUILT" >&2
  exit 1
fi

# 4. Place the result (default: the release dir; override with REDLINE_OUT).
DEST="${REDLINE_OUT:-$REPO_ROOT/releases/$NEW_V/Newcastle CZC (Integrated Draft $NEW_V) — Redline.pdf}"
mkdir -p "$(dirname "$DEST")"
cp "$BUILT" "$DEST"
PAGES=$(python3 - "$DEST" <<'PY'
import sys, fitz
print(fitz.open(sys.argv[1]).page_count)
PY
)
echo "Formatted redline saved ($PAGES pages): $DEST"
