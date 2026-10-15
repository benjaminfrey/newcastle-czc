#!/usr/bin/env bash
# Development happens on a VM, not the Mac: the Mac holds the git checkout and
# the editor; the VM runs Docker, the API, the web dev server and the tests.
#
#   portal/vm.sh sync            copy portal/ to the VM
#   portal/vm.sh run <command>   sync, then run <command> on the VM from the repo root there
#   portal/vm.sh tunnel          forward the dev ports to this Mac (web 5173, API 8000, Mailpit 8025)
#   portal/vm.sh lan             sync, then rebuild and restart the LAN stack (https://<VM>, Mailpit on :8026)
#
# Everything on the VM binds 127.0.0.1 only; the tunnel is how a browser on the
# Mac reaches it. Override the VM with PORTAL_DEV_VM (default ben@192.168.1.6).
set -euo pipefail

VM="${PORTAL_DEV_VM:-ben@192.168.1.6}"
REMOTE_ROOT="newcastle-czc"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sync() {
  ssh "$VM" "mkdir -p $REMOTE_ROOT/portal"
  # Excluded paths are VM-local (built there) and survive --delete.
  rsync -az --delete \
    --exclude '.venv/' --exclude 'node_modules/' --exclude 'dist/' \
    --exclude '__pycache__/' --exclude '.pytest_cache/' --exclude '.env' \
    --exclude 'web/public/basemap/' \
    "$HERE/" "$VM:$REMOTE_ROOT/portal/"
  # Reference data the GIS loaders read, kept at the same repo-relative paths on the VM.
  (cd "$HERE/.." && rsync -azR \
    data/street-types/districts.geojson \
    source/exhibits/street-types/inventory.json \
    source/exhibits/cross-sections/types.json \
    build/permit-review/rulesets/adopted-v1.0/districts.json \
    "$VM:$REMOTE_ROOT/")
}

case "${1:-}" in
  sync)
    sync
    ;;
  run)
    shift
    [ $# -gt 0 ] || { echo "usage: portal/vm.sh run <command>" >&2; exit 2; }
    sync
    ssh "$VM" "cd $REMOTE_ROOT && export PATH=\$HOME/.local/bin:\$PATH && $*"
    ;;
  lan)
    sync
    ssh "$VM" "cd $REMOTE_ROOT/portal/deploy && sudo docker compose -f compose.yml -f compose.lan.yml --env-file .env up -d --build --wait --remove-orphans"
    ;;
  tunnel)
    echo "Forwarding 5173 (web), 8000 (API), 8025 (Mailpit) from $VM. Ctrl-C to stop."
    ssh -N -L 5173:127.0.0.1:5173 -L 8000:127.0.0.1:8000 -L 8025:127.0.0.1:8025 "$VM"
    ;;
  *)
    sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
