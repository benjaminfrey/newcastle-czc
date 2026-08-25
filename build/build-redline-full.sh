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

# 2. Rewrite each article markdown in place: OLD = that file at <old-ver>, NEW
#    = the staged working-tree file. --source preserves frontmatter + split
#    markers, marks prose, and emits figures/tables/headings unmarked.
#
#    Old-side resolution goes through build/redline_resolve.py, which knows
#    two things a plain `git show <old>:source/<same-name>` does not:
#      - ADOPTION_BASELINE=1 (an adoption-release redline against the
#        previously adopted Code): articles were renamed/renumbered at the
#        Article-3 insertion, so the old side must be looked up via
#        adoption-map.json, not by filename (build/redline_resolve.py, exit 0).
#        It also normalises the old side it writes (heading case + cross-ref
#        renumbering ONLY, via normalize_old_side -- see normalize_for_diff.py)
#        so cosmetic drift doesn't bury real changes under invisible ones.
#      - An article whose content moved out of markdown into a native-Typst
#        unit since the baseline (Article 2's district standards) cannot be
#        text-diffed without reporting a phantom mass deletion; it must render
#        UNMARKED instead (exit 4 — see below).
#    Without ADOPTION_BASELINE=1 this resolves by filename exactly as before
#    (exit 3 on a genuinely new file), so an ordinary draft-to-draft redline
#    is untouched.
#
#    The NEW side ($nf) is NEVER normalised or otherwise rewritten here: it is
#    the staged working-tree file that build-full-czc.sh typesets verbatim
#    into the published PDF. redline-text.py's --source mode is line-based and
#    emits the lines it is given, so anything done to a side that gets
#    rendered reaches the document, not just the comparison. (A prior version
#    of this loop normalised the new side too "for equal terms" -- that
#    silently flattened indented sub-clauses into run-on prose. Fixed
#    2026-08-24 after review; see normalize_for_diff.py.)
OLDTMP="$OUTDIR/old.md"
BASELINE_FLAG=""
if [ "${ADOPTION_BASELINE:-0}" = "1" ]; then BASELINE_FLAG="--baseline"; fi

shopt -s nullglob
n=0
for nf in "$STAGE"/article-*.md; do
  base="$(basename "$nf")"
  # Every branch of the case below must (re)create OLDTMP. Removing it first
  # means a branch that fails to do so is caught by the existence check right
  # after the case, rather than silently reusing the previous article's old
  # side (OLDTMP is one file, reused every iteration).
  rm -f "$OLDTMP"
  set +e
  python3 "$REPO_ROOT/build/redline_resolve.py" "$base" "$OLD_V" "$OLDTMP" $BASELINE_FLAG
  rc=$?
  set -e
  case "$rc" in
    0) ;;
    3) : > "$OLDTMP"   # new since OLD: empty OLD -> whole body marked added
       echo "  ($base is new since $OLD_V — whole body marked as added)" ;;
    4) cp "$nf" "$OLDTMP"   # not text-comparable: force old == new -> unmarked
       echo "  ($base is not text-comparable against $OLD_V — rendered unmarked)" ;;
    *) echo "redline: could not resolve the old side for $base (exit $rc)." >&2
       exit 1 ;;
  esac
  if [ ! -e "$OLDTMP" ]; then
    echo "redline: internal error — no old side was produced for $base (exit $rc)." >&2
    exit 1
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
