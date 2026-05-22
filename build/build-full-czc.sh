#!/usr/bin/env bash
# Build the full integrated CZC for a release.
#
# Each article is rendered to its own PDF (so per-article metadata — Article
# number, Article name, opener page — is honored), then all article PDFs are
# concatenated with pdfunite into a single deliverable.
#
# Usage:
#   build-full-czc.sh [version-tag]
#
# Example:
#   build-full-czc.sh v0.1-baseline

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/source"
VERSION="${1:-v0.0-dev}"
RELEASE_DIR="$REPO_ROOT/releases/$VERSION"
mkdir -p "$RELEASE_DIR"

# Collect article markdown files in lexical order (bash-3 compatible).
ARTICLES=()
while IFS= read -r f; do
  ARTICLES+=("$f")
done < <(ls "$SOURCE_DIR"/article-*.md 2>/dev/null | sort)

if [ ${#ARTICLES[@]} -eq 0 ]; then
  echo "No article markdown files found in $SOURCE_DIR" >&2
  exit 1
fi

OUT_NAME="Newcastle CZC (Integrated Draft $VERSION)"
OUTPUT_PDF="$RELEASE_DIR/$OUT_NAME.pdf"
COMBINED_MD="$RELEASE_DIR/$OUT_NAME.md"

# Render each article to its own PDF.
TMPDIR_PDFS="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_PDFS"' EXIT

INDEX=0
PDF_LIST=()
for ART in "${ARTICLES[@]}"; do
  INDEX=$((INDEX + 1))
  PART="$TMPDIR_PDFS/$(printf "%02d" "$INDEX").pdf"
  echo "Rendering article $INDEX: $(basename "$ART")"
  bash "$REPO_ROOT/build/build-article.sh" "$ART" "$PART" \
    -V "footer-date=Draft $VERSION" >/dev/null
  PDF_LIST+=("$PART")
done

echo "Concatenating ${#PDF_LIST[@]} article PDFs into: $OUTPUT_PDF"
pdfunite "${PDF_LIST[@]}" "$OUTPUT_PDF"

# Also emit the concatenated markdown source for reference (frontmatter intact;
# read by humans, not re-rendered through pandoc as one input).
echo "Writing combined markdown: $COMBINED_MD"
cat "${ARTICLES[@]}" > "$COMBINED_MD"

echo "Done: $OUTPUT_PDF"
