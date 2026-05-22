#!/usr/bin/env bash
# Produce a redline PDF comparing two documents.
#
# Default behavior: compare a release's Full CZC PDF against the baseline CZC PDF.
#
# Usage:
#   build-redline.sh [version-tag]                # release vs baseline
#   build-redline.sh <pdf-a> <pdf-b> <output>     # explicit two-file diff

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ $# -eq 3 ]; then
  # Explicit mode: build-redline.sh A.pdf B.pdf out.pdf
  PDF_A="$1"
  PDF_B="$2"
  OUTPUT="$3"
else
  VERSION="${1:-v0.0-dev}"
  RELEASE_DIR="$REPO_ROOT/releases/$VERSION"
  PDF_A="$REPO_ROOT/docs/Newcastle Core Zoning Code.pdf"
  PDF_B="$RELEASE_DIR/Newcastle CZC (Integrated Draft $VERSION).pdf"
  OUTPUT="$RELEASE_DIR/Redline — Full CZC $VERSION vs Baseline.pdf"

  if [ ! -f "$PDF_B" ]; then
    echo "Release PDF not found; run build-full-czc.sh $VERSION first." >&2
    echo "  expected: $PDF_B" >&2
    exit 1
  fi
fi

mkdir -p "$(dirname "$OUTPUT")"

echo "Comparing:"
echo "  baseline: $PDF_A"
echo "  draft:    $PDF_B"
echo "  output:   $OUTPUT"

# diff-pdf exits non-zero when files differ — that is expected and not an error here.
diff-pdf --output-diff="$OUTPUT" --mark-differences "$PDF_A" "$PDF_B" || true

if [ -f "$OUTPUT" ]; then
  echo "Redline saved: $OUTPUT"
else
  echo "Warning: diff-pdf did not produce an output file." >&2
  exit 1
fi
