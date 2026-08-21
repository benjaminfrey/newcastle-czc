"""Offline builders: repo source (source/article-02*.{json,typ}) -> rulesets/.

See ../CONTRACT.md §4 for the normative schemas these builders produce.
Runtime code (app/) never imports from here and never re-parses repo source
directly — it only reads the committed rulesets/<key>/*.json build output.
"""
