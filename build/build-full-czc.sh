#!/usr/bin/env bash
# Build the full integrated CZC (all articles concatenated) for a release.
#
# Usage:
#   build-full-czc.sh [version-tag]
#
# Example:
#   build-full-czc.sh v0.1-draft

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/source"
VERSION="${1:-v0.0-dev}"
RELEASE_DIR="$REPO_ROOT/releases/$VERSION"
mkdir -p "$RELEASE_DIR"

# Collect all article markdown files in lexical order (article-01, article-02, …)
mapfile -t ARTICLES < <(ls "$SOURCE_DIR"/article-*.md 2>/dev/null | sort)

if [ ${#ARTICLES[@]} -eq 0 ]; then
  echo "No article markdown files found in $SOURCE_DIR" >&2
  exit 1
fi

OUT_NAME="Newcastle CZC (Integrated Draft $VERSION)"
COMBINED_MD="$RELEASE_DIR/$OUT_NAME.md"
OUTPUT_PDF="$RELEASE_DIR/$OUT_NAME.pdf"

echo "Concatenating ${#ARTICLES[@]} article files into: $COMBINED_MD"
cat "${ARTICLES[@]}" > "$COMBINED_MD"

echo "Rendering: $OUTPUT_PDF"
pandoc "$COMBINED_MD" \
  --from=markdown+fancy_lists+startnum \
  --pdf-engine=typst \
  --template="$REPO_ROOT/style/czc-template.typ" \
  --resource-path="$REPO_ROOT/style" \
  -V footer-date="Draft $VERSION" \
  -o "$OUTPUT_PDF"

echo "Done: $OUTPUT_PDF"
