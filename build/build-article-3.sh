#!/usr/bin/env bash
# Build the standalone Article 3 "Streets, Roads & Driveways" deliverable.
#
# Usage:
#   build-article-3.sh [version-tag]
#
# Example:
#   build-article-3.sh v0.1-draft

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/source/article-03-streets-roads-driveways.md"
VERSION="${1:-v0.0-dev}"
RELEASE_DIR="$REPO_ROOT/releases/$VERSION"
mkdir -p "$RELEASE_DIR"

if [ ! -f "$SOURCE" ]; then
  echo "Article 3 source not yet drafted: $SOURCE" >&2
  exit 1
fi

OUT_NAME="Article 3 Streets Roads & Driveways (Standalone $VERSION)"
OUTPUT_PDF="$RELEASE_DIR/$OUT_NAME.pdf"

echo "Rendering: $OUTPUT_PDF"
pandoc "$SOURCE" \
  --from=markdown+fancy_lists+startnum \
  --pdf-engine=typst \
  --pdf-engine-opt=--font-path="$REPO_ROOT/style/fonts" \
  --template="$REPO_ROOT/style/czc-template.typ" \
  --resource-path="$REPO_ROOT/style" \
  -V article-number=3 \
  -V article-name="Streets, Roads & Driveways" \
  -V footer-date="Draft $VERSION" \
  -o "$OUTPUT_PDF"

cp "$SOURCE" "$RELEASE_DIR/$OUT_NAME.md"
echo "Done: $OUTPUT_PDF"
