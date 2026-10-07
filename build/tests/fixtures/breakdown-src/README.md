# breakdown-src

A minimal source tree for `build/adoption_breakdown.py` tests. It exists so the
breakdown's output can be asserted against a known, frozen input rather than
against the live `source/` tree, which moves with every amendment.

## article-01-general.md

The `v0.1-baseline` copy of Article 1 as the breakdown sees it (that tag's
`source/article-01-general.md` passed through `normalize_old_side` with
`adoption-map-v0.1-baseline.json`), with **exactly one line changed**: PURPOSE
item 1, which has a clause appended. Measured against that same baseline the
breakdown reports **2 lines** -- one deleted, one added -- and an unedited copy
reports 0. The live `source/` tree reports 0 for Article 1 under the same map,
so a "2" can only have come from this directory.

It starts from the normalised baseline, not a raw copy, because the baseline
uses upper-case headings and the current Code lower-case ones; a raw copy
reports ~30 lines of heading-case noise before the edit is even counted.

The tree holds only Article 1, but the map names every article, so the
breakdown reports Article 1 and then refuses (exit 1) naming the first missing
file. That refusal is part of what the test asserts: it proves the breakdown
read *this* directory. Both ends are frozen: the `v0.1-baseline` tag is
immutable and this file is never edited, so the number is stable by
construction, not by re-pinning.

Keep it small. If a test needs a second article, add the smallest file that
exercises the rule under test, and say here what it is for. If the normaliser's
rules legitimately change the count, understand why before updating the test.
