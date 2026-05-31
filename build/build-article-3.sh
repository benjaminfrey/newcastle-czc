#!/usr/bin/env bash
# Build the standalone Article 3 "Streets, Roads & Driveways" deliverable.
#
# The standalone is the new Article rendered for focused review: the prose
# (article-03-streets-roads-driveways.md via pandoc) followed by the ten
# full-page Street/Road Type cross-section plates (S-1..S-5, R-1..R-5) rendered
# natively from source/cross-section-plates.typ. The plate block is appended at
# an EVEN page offset (padding a blank after the prose if it ends on an odd
# page), so the plates' parity-aware chrome (verso/recto badge + mirrored
# running head) matches their physical position and footer numbers stay
# continuous with the prose.
#
# Usage:
#   build-article-3.sh [version-tag]
#
# Example:
#   build-article-3.sh v0.1-draft

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/source/article-03-streets-roads-driveways.md"
PLATES_TYP="$REPO_ROOT/source/cross-section-plates.typ"
VERSION="${1:-v0.0-dev}"
RELEASE_DIR="$REPO_ROOT/releases/$VERSION"
mkdir -p "$RELEASE_DIR"

if [ ! -f "$SOURCE" ]; then
  echo "Article 3 source not yet drafted: $SOURCE" >&2
  exit 1
fi

OUT_NAME="Article 3 Streets Roads & Driveways (Standalone $VERSION)"
OUTPUT_PDF="$RELEASE_DIR/$OUT_NAME.pdf"

TMPDIR_A3="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_A3"' EXIT
PROSE_PDF="$TMPDIR_A3/prose.pdf"

echo "Rendering Article 3 prose"
pandoc "$SOURCE" \
  --from=markdown+fancy_lists+startnum \
  --pdf-engine=typst \
  --pdf-engine-opt=--font-path="$REPO_ROOT/style/fonts" \
  --template="$REPO_ROOT/style/czc-template.typ" \
  --resource-path="$REPO_ROOT/style" \
  -V article-number=3 \
  -V article-name="Streets, Roads & Driveways" \
  -V footer-date="Draft $VERSION" \
  -V page-offset=0 \
  -o "$PROSE_PDF"

PARTS=("$PROSE_PDF")

if [ -f "$PLATES_TYP" ]; then
  PROSE_PAGES=$(python3 - "$PROSE_PDF" <<'PY'
import sys, fitz
print(fitz.open(sys.argv[1]).page_count)
PY
)
  # The plate block's page_offset must be EVEN (parity invariant in
  # cross-section-plates.typ). If the prose ends on an odd page, pad a blank so
  # the first plate opens on a recto and logical == physical for plate chrome.
  PRECEDING=$PROSE_PAGES
  if [ $((PROSE_PAGES % 2)) -eq 1 ]; then
    BLANK_PDF="$TMPDIR_A3/blank.pdf"
    python3 - "$BLANK_PDF" <<'PY'
import sys, fitz
d = fitz.open(); d.new_page(width=612, height=792); d.save(sys.argv[1]); d.close()
PY
    PARTS+=("$BLANK_PDF")
    PRECEDING=$((PROSE_PAGES + 1))
  fi

  PLATES_PDF="$TMPDIR_A3/plates.pdf"
  echo "Rendering 10 Type plates (page offset $PRECEDING)"
  typst compile "$PLATES_TYP" "$PLATES_PDF" \
    --font-path "$REPO_ROOT/style/fonts" \
    --input "page_offset=$PRECEDING" \
    --input "footer_date=Draft $VERSION"
  PARTS+=("$PLATES_PDF")
fi

echo "Assembling: $OUTPUT_PDF"
pdfunite "${PARTS[@]}" "$OUTPUT_PDF"

cp "$SOURCE" "$RELEASE_DIR/$OUT_NAME.md"
echo "Done: $OUTPUT_PDF"
