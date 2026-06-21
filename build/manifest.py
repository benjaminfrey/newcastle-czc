#!/usr/bin/env python3
"""Tiny reader for build/article-manifest.json so build-standalone.sh (bash) need
not parse JSON. The manifest lists native-Typst units only for Articles that have
them (1, 2, 3); any article absent from it is a pure-prose single-pass build.

Subcommands (article-number is 1..9, with or without a leading zero):
  has <NN>      exit 0 if article NN has native units (use the splice path), else 1
  prose <NN>    print the prose markdown filename for NN ("" if no entry)
  markers <NN>  print the split markers, space-separated ("" if none)
  units <NN>    print one line per unit: typ|splice|data|conditional_on|parity|pad_to
"""
import sys
import os
import json

MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "article-manifest.json")


def load():
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: manifest.py <has|prose|markers|units> <article-number>")
    cmd = sys.argv[1]
    nn = str(int(sys.argv[2]))            # normalize "03" -> "3"
    entry = load().get(nn)

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
    sys.exit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
