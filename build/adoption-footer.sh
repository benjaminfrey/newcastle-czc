# Shared adoption-mode resolution. Sourced by build-full-czc.sh and
# build-standalone.sh (both `set -euo pipefail`, both define REPO_ROOT and
# VERSION before sourcing this). Reads ADOPTION_MODE (default 'draft', so a
# plain invocation is unchanged) and ADOPTION_EVENT_DATE from the environment,
# sets FOOTER_TEXT, and enforces the version-state rule in BOTH directions.
# See build/ADOPTION-SPEC.md §4 / §4.1 / §6.1.
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

# The version-state gate, BOTH directions (ADOPTION-SPEC.md §2.1 / §6.1):
#
#   draft mode              must NOT carry a whole number
#   meeting / adopted mode  MUST carry a whole number
#
# Only the first half existed until the final whole-branch review. With the
# second half missing, `ADOPTION_MODE=adopted ADOPTION_EVENT_DATE=…
# build-full-czc.sh v0.24-draft` built happily — cover "v0.24-draft · Adopted
# March 15, 2027", footer "Adopted: March 15, 2027" — rendered from the WORKING
# TREE, with neither the content-identity gate nor the draft-residue gate,
# because both of those live in build-adopted.sh. That is a document claiming
# adoption produced by one environment variable: the 11pm bypass around every
# safeguard this feature exists to provide. Adoption chrome now requires an
# adoption version number, which in turn only ever comes from build-adoption.sh
# / build-adopted.sh and their gates.
#
# It lives HERE, in the file both builders already source, so the two cannot
# drift apart again (the same reasoning that moved footer resolution here).
if [ "$ADOPTION_MODE" = "draft" ]; then
  python3 "$REPO_ROOT/build/version_state.py" --require draft "$VERSION" || exit 1
else
  python3 "$REPO_ROOT/build/version_state.py" --require adoption "$VERSION" || exit 1
fi

# Shared artifact naming, so the mode and the filename can never disagree.
source "$REPO_ROOT/build/adoption-name.sh"
