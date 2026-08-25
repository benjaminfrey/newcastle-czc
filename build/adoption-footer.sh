# Shared adoption-mode footer resolution. Sourced by build-full-czc.sh and
# build-standalone.sh (both `set -euo pipefail`, both define VERSION before
# sourcing this). Reads ADOPTION_MODE (default 'draft', so a plain invocation
# is unchanged) and ADOPTION_EVENT_DATE from the environment, and sets
# FOOTER_TEXT. See build/ADOPTION-SPEC.md §4 / §4.1.
ADOPTION_MODE="${ADOPTION_MODE:-draft}"
ADOPTION_EVENT_DATE="${ADOPTION_EVENT_DATE:-}"
case "$ADOPTION_MODE" in
  draft)    FOOTER_TEXT="Draft $VERSION" ;;
  meeting)  FOOTER_TEXT="Town Meeting Edition $VERSION" ;;
  adopted)  FOOTER_TEXT="Adopted: $ADOPTION_EVENT_DATE" ;;
  *) echo "unknown ADOPTION_MODE '$ADOPTION_MODE'" >&2; exit 1 ;;
esac
if [ "$ADOPTION_MODE" != "draft" ] && [ -z "$ADOPTION_EVENT_DATE" ]; then
  echo "ADOPTION_MODE=$ADOPTION_MODE requires ADOPTION_EVENT_DATE" >&2; exit 1
fi
