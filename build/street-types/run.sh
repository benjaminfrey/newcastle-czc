#!/usr/bin/env bash
# Run the Street & Road Type pipeline, stages 01 -> 05, in order.
#
#   bash build/street-types/run.sh            # all stages
#   bash build/street-types/run.sh --from 3   # resume at stage 3 (join)
#
# Stage 00 (district digitizing) is run separately — it needs a georeferenced
# raster you produce in QGIS (see README + 00_digitize_districts.py).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$HERE/.venv/bin/python"
[ -x "$PY" ] || { echo "geo venv missing — create it: see build/street-types/README.md" >&2; exit 1; }

FROM=1
if [ "${1:-}" = "--from" ]; then FROM="${2:?--from needs a stage number}"; fi

cd "$HERE"
STAGES=(01_fetch 02_prepare 03_join 04_classify 05_export)
for i in "${!STAGES[@]}"; do
  n=$((i + 1))
  if [ "$n" -lt "$FROM" ]; then continue; fi
  echo "=== stage $n — ${STAGES[$i]} ==="
  "$PY" "${STAGES[$i]}.py"
done
echo "Pipeline complete. Working outputs in data/street-types/work/ (inventory.json, review.csv)."
