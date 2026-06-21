#!/usr/bin/env bash
# Backward-compatible shim. Article 3's standalone is now produced by the unified
# build-standalone.sh (Article 3 is an entry in build/article-manifest.json), which
# generalizes this script's old split-at-markers + plate/exhibit splice to every
# Article. Kept so existing usage — and CLAUDE.md's build flow — still work:
#
#   build-article-3.sh <version> [date-str]   ==   build-standalone.sh 3 <version> [date-str]
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/build-standalone.sh" 3 "$@"
