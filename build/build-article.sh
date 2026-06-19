#!/usr/bin/env bash
# Build a single article markdown file to PDF using the CZC Typst template.
#
# Usage:
#   build-article.sh <source.md> <output.pdf> [pandoc -V variables...]
#
# Example:
#   build-article.sh source/article-01-general.md /tmp/art1.pdf \
#     -V article-number=1 -V article-name="General Standards"

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <source.md> <output.pdf> [pandoc -V variables...]" >&2
  exit 1
fi

SOURCE_MD="$1"
OUTPUT_PDF="$2"
shift 2

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$REPO_ROOT/style/czc-template.typ"

if [ ! -f "$SOURCE_MD" ]; then
  echo "Source file not found: $SOURCE_MD" >&2
  exit 1
fi

if [ ! -f "$TEMPLATE" ]; then
  echo "Template not found: $TEMPLATE" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_PDF")"

pandoc "$SOURCE_MD" \
  --from=markdown+raw_attribute+strikeout+fancy_lists+startnum \
  --pdf-engine=typst \
  --pdf-engine-opt=--font-path="$REPO_ROOT/style/fonts" \
  --template="$TEMPLATE" \
  --resource-path="$REPO_ROOT/style" \
  "$@" \
  -o "$OUTPUT_PDF"

echo "Built: $OUTPUT_PDF"
