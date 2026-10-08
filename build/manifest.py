#!/usr/bin/env python3
"""Tiny reader for build/article-manifest.json so build-standalone.sh (bash) need
not parse JSON. The manifest has an entry for every Article 1-9; an Article with
an empty ``units`` list (4-9) is a pure-prose single-pass build.

Subcommands (article-number is 1..9, with or without a leading zero):
  has <NN>      exit 0 if article NN has native units (use the splice path), else 1
  prose <NN>    print the prose markdown filename for NN ("" if no entry)
  markers <NN>  print the split markers, space-separated ("" if none)
  units <NN>    print one line per unit: typ|splice|data|conditional_on|parity|pad_to
  data <NN>     print the article's data_sources as JSON ("[]" if none).
                NON-PROSE FILES ONLY: an Article's prose is NOT in data_sources
                (it is the article-0N-*.md convention, see claimants()), so
                "[]" -- as for Articles 4-9 -- does NOT mean "no binding
                content". Article 7's binding content is entirely its prose.
                To ask what governs an Article, use `owner <path>` per file.
  articles      print every article number the manifest knows, one per line
  owner <path>  print the owning article number for a path under source/
                ("shared"/"ignored" for the top-level lists); exit 1 if unclaimed
"""
import sys
import os
import json
import re

MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "article-manifest.json")


def load():
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


PROSE_RE = re.compile(r"^article-0(\d)-[^/]*\.md$")


def _claims(path, decl):
    """True if a data_sources path declaration claims `path`. A declaration
    ending in "/" claims everything beneath it."""
    return path.startswith(decl) if decl.endswith("/") else path == decl


def claimants(doc, path):
    """Every owner that claims `path` (relative to source/): an article number,
    "shared" or "ignored" (both terminal -- see below). A well-formed map yields
    exactly one; the coverage
    test asserts that, so an overlapping declaration cannot silently resolve to
    whichever Article happens to sort first.

    Prose is claimed by the article-0N-*.md convention rather than by a
    manifest field: build-standalone.sh already falls back to that glob, and
    declaring prose here would change `manifest.py prose`'s output for
    Articles 4-9.
    """
    # The two top-level lists are TERMINAL: a path named in one has exactly that
    # claimant even if it also falls under a data_sources "/" prefix. That is
    # how a file inside a claimed directory (e.g. sprites/NOTICE.md) is carved out.
    if path in doc.get("ignored", []):
        return ["ignored"]
    if path in doc.get("shared", []):
        return ["shared"]
    found = []
    m = PROSE_RE.match(path)
    if m:
        found.append(str(int(m.group(1))))
    for nn in sorted((k for k in doc if k.isdigit()), key=int):
        entry = doc[nn]
        if (any(u.get("typ") == path for u in entry.get("units", []))
                or any(_claims(path, d.get("path", ""))
                       for d in entry.get("data_sources", []))):
            found.append(nn)
    return found


def owner_of(doc, path):
    """Return the owner of `path`, or None if nothing claims it."""
    found = claimants(doc, path)
    return found[0] if found else None


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: manifest.py <has|prose|markers|units|data> <article-number>\n"
                 "       manifest.py articles\n"
                 "       manifest.py owner <path-under-source>")
    cmd = sys.argv[1]
    doc = load()

    if cmd == "articles":
        for n in sorted((k for k in doc if k.isdigit()), key=int):
            print(n)
        return
    if cmd == "owner":
        if len(sys.argv) < 3:
            sys.exit("usage: manifest.py owner <path-under-source>")
        who = owner_of(doc, sys.argv[2])
        if who is None:
            sys.exit(1)
        print(who)
        return

    if len(sys.argv) < 3:
        sys.exit("usage: manifest.py <has|prose|markers|units|data> <article-number>")
    nn = str(int(sys.argv[2]))            # normalize "03" -> "3"
    entry = doc.get(nn)

    if cmd == "has":
        sys.exit(0 if (entry and entry.get("units")) else 1)
    if cmd == "prose":
        print(entry.get("prose", "") if entry else "")
        return
    if cmd == "markers":
        print(" ".join(entry.get("split_markers", [])) if entry else "")
        return
    if cmd == "units":
        if not entry:
            return
        for u in entry.get("units", []):
            print("|".join([
                u.get("typ", ""), u.get("splice", ""), u.get("data", ""),
                u.get("conditional_on", ""), u.get("parity", ""), u.get("pad_to", ""),
            ]))
        return
    if cmd == "data":
        print(json.dumps(entry.get("data_sources", []) if entry else [], indent=2))
        return
    sys.exit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
