#!/usr/bin/env bash
# Produce a TEXT redline PDF between two versions of the Code.
#
# LEGACY / text-only — the plain single-column change report. For the formatted
# redline that carries the full integrated layout (chrome + native figures) with
# prose marked inline, use build/build-redline-full.sh instead.
#
# This compares the TEXT of two releases' integrated markdown deliverables and
# renders a compact VECTOR PDF: deleted text struck through, new text in red
# immediately after it. It replaces the old diff-pdf raster overlay (which
# produced 60–110 MB "ghost image" PDFs and flagged every layout/image shift as
# a change). Layout-only and image-only edits live in .typ/.png files, never in
# the markdown, so they are ignored by construction — only real text changes
# appear. Output is typically well under 1 MB.
#
# Usage:
#   build-redline.sh <new-version> <old-version>   # e.g. v0.10-draft v0.9-draft
#   build-redline.sh <old.md> <new.md> <out.pdf>   # explicit file mode
#
# The integrated deliverable for each release must already exist at:
#   releases/<version>/Newcastle CZC (Integrated Draft <version>).md

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REDLINE_PY="$REPO_ROOT/build/redline-text.py"
TEMPLATE="$REPO_ROOT/style/redline-template.typ"
FONTS="$REPO_ROOT/style/fonts"

# render <redlined.md> <out.pdf> <subtitle>
render() {
  pandoc "$1" \
    --from=markdown+raw_attribute+strikeout+fancy_lists+startnum \
    --pdf-engine=typst \
    --pdf-engine-opt=--font-path="$FONTS" \
    --template="$TEMPLATE" \
    --resource-path="$REPO_ROOT/style" \
    -V "redline-title=Redline — Newcastle Core Zoning Code" \
    -V "redline-subtitle=$3" \
    -o "$2"
}

if [ $# -eq 3 ]; then
  # Explicit mode: build-redline.sh old.md new.md out.pdf
  OLD_MD="$1"
  NEW_MD="$2"
  OUTPUT="$3"
  SUBTITLE="Full redline — all changes shown inline"
elif [ $# -eq 2 ]; then
  # Version mode: build-redline.sh <new> <old>
  NEW_V="$1"
  OLD_V="$2"
  OLD_MD="$REPO_ROOT/releases/$OLD_V/Newcastle CZC (Integrated Draft $OLD_V).md"
  NEW_MD="$REPO_ROOT/releases/$NEW_V/Newcastle CZC (Integrated Draft $NEW_V).md"
  OUTPUT="$REPO_ROOT/releases/$NEW_V/Newcastle CZC (Integrated Draft $NEW_V) — Redline.pdf"
  SUBTITLE="Full integrated draft — all changes since $OLD_V shown inline"
else
  echo "usage: build-redline.sh <new-version> <old-version>" >&2
  echo "       build-redline.sh <old.md> <new.md> <out.pdf>" >&2
  exit 1
fi

for f in "$OLD_MD" "$NEW_MD"; do
  if [ ! -f "$f" ]; then
    echo "Integrated markdown not found: $f" >&2
    echo "Run build-full-czc.sh for that version first." >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$OUTPUT")"

echo "Text redline:"
echo "  old:    $OLD_MD"
echo "  new:    $NEW_MD"
echo "  output: $OUTPUT"

TMP_MD="$(mktemp -t redline).md"
trap 'rm -f "$TMP_MD"' EXIT

# Full-document redline: the entire integrated draft with deletions struck and
# additions in red, shown inline in full context (not a changed-passages digest).
python3 "$REDLINE_PY" "$OLD_MD" "$NEW_MD" "$TMP_MD" --full
render "$TMP_MD" "$OUTPUT" "$SUBTITLE"

echo "Redline saved: $OUTPUT"
