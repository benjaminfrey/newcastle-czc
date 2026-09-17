"""Builds the binding ruleset for a Code EDITION adopted at Town Meeting, from its
release tag, and marks the Code it replaces superseded.

    python -m ruleset_build.build_edition --tag v1.0 --adopted-on 2026-09-14 \\
        --key adopted-v1.0 --supersedes adopted [--dry-run] [--actor-user-id ID]

First use: CZC v1.0, adopted at the Special Town Meeting of September 14, 2026,
superseding the Code adopted November 3, 2020.

WHY A SEPARATE BUILDER. build_ruleset.py builds the 2020 Code from its PDF and
the working draft from source/. An adopted edition is neither. It is exactly the
text the voters adopted: the release TAG's source/, which is the tree
build/build-adopted.sh renders the adopted edition from and pins against
releases/<tag>/frozen-from.json. Building from the working tree would let
drafting done after the vote leak into a ruleset real decisions cite.

WHAT IT REFUSES, rather than guessing:
  - a tag whose source tree is not the one recorded when the edition was frozen,
    or an edition that build-adopted.sh has not rendered yet;
  - a scheme with no map in app/citation.py SCHEME_TO_DRAFT;
  - deadline clocks, if the set of "within N days" clauses in the new
    Administration article differs from the superseded one, or if a governing
    sentence changed AND its numbers changed with it. (A sentence reworded with
    its numbers intact is carried forward verbatim from the new Code, and every
    such rewording is listed in the manifest.)
  - subdivision criteria, if the 21 standards a-u are not where and what they
    were, or if a judgement word the classification relies on is gone from a
    standard's new text.

NOTHING IS WRITTEN until every artifact has been built. The superseded ruleset's
artifacts are never touched -- only its manifest changes, to say "superseded"
and by what -- because cases decided under it must keep citing exactly it.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))

from app.citation import SCHEME_TO_DRAFT, to_scheme  # noqa: E402
from ruleset_build import build_clocks, build_districts  # noqa: E402
from ruleset_build import build_subdivision_criteria as criteria_build  # noqa: E402
from ruleset_build import crosswalk, parse_articles, parse_definitions  # noqa: E402
from ruleset_build.build_ruleset import (  # noqa: E402
    MANIFEST_SCHEMA,
    _atomic_write_json,
    _existing_or_new_id,
    _register_ruleset,
    _sha256_file,
    _utc_now_iso,
)
from ruleset_build.build_use_matrix import build_use_matrix  # noqa: E402

BUILDER_VERSION = "ruleset_build/2.1.0 (build_edition)"
RULESETS_DIR = APP_ROOT / "rulesets"
OVERRIDES = APP_ROOT / "overrides" / "dimension-qualifiers.json"
SUPERSEDED_SCHEME = "adopted"  # the 2020 Code's numbering; CLOCKS_ADOPTED and the criteria cite it


class EditionBuildError(RuntimeError):
    """The edition cannot be built faithfully. Nothing has been written."""


# --------------------------------------------------------------------------- #
# Provenance and staging
# --------------------------------------------------------------------------- #


def _git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise EditionBuildError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def provenance(tag: str) -> dict[str, Any]:
    """Ties the ruleset to the text the voters adopted, the same way
    build-adopted.sh's provenance gate does."""
    tree = _git("rev-parse", f"{tag}:source")
    frozen = REPO_ROOT / "releases" / tag / "frozen-from.json"
    if not frozen.exists():
        raise EditionBuildError(f"{frozen.relative_to(REPO_ROOT)} not found -- {tag} was never frozen")
    if tree not in frozen.read_text(encoding="utf-8"):
        raise EditionBuildError(
            f"tag {tag}'s source tree {tree} is not the tree recorded in "
            f"{frozen.relative_to(REPO_ROOT)} -- the tag no longer points at what the voters saw"
        )
    md = REPO_ROOT / "releases" / f"{tag}-adopted" / f"Newcastle CZC (Adopted {tag}).md"
    if not md.exists():
        raise EditionBuildError(
            f"{md.relative_to(REPO_ROOT)} not found -- run build/build-adopted.sh {tag} "
            f"\"<adoption date>\" first; a ruleset is built only for an edition that has been adopted"
        )
    return {
        "tag": tag,
        "tag_commit": _git("rev-parse", f"{tag}^{{commit}}"),
        "source_tree": tree,
        "frozen_from": str(frozen.relative_to(REPO_ROOT)),
        "adopted_edition_md": {"path": str(md.relative_to(REPO_ROOT)), "sha256": _sha256_file(md)},
    }


def stage_source(tag: str, dest: Path) -> Path:
    """Extracts the tag's source/ (and nothing else) into `dest`."""
    r = subprocess.run(["git", "-C", str(REPO_ROOT), "archive", tag, "source"], capture_output=True)
    if r.returncode != 0:
        raise EditionBuildError(f"git archive {tag} source failed: {r.stderr.decode().strip()}")
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as t:
        t.extractall(dest, filter="data")
    return dest / "source"


# --------------------------------------------------------------------------- #
# Carrying a superseded Code's reviewed artifacts forward
# --------------------------------------------------------------------------- #


def _norm(s: str | None) -> str:
    return " ".join((s or "").strip().casefold().split())


def _flat(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"article": n["article"], "section": n.get("section"), "subsection": n.get("subsection"),
             "path": n.get("path") or [], "text": n.get("text") or ""} for n in nodes]


def _renumber_citations(obj: Any, *, key: str, scheme: str, old_key: str) -> Any:
    """Every {ruleset_key, scheme, article} citation of the superseded Code,
    re-pointed at the new Code (article renumbered through the scheme maps)."""
    if isinstance(obj, list):
        return [_renumber_citations(v, key=key, scheme=scheme, old_key=old_key) for v in obj]
    if not isinstance(obj, dict):
        return obj
    out = {k: _renumber_citations(v, key=key, scheme=scheme, old_key=old_key) for k, v in obj.items()}
    if out.get("ruleset_key") == old_key and out.get("scheme") == SUPERSEDED_SCHEME and isinstance(out.get("article"), int):
        out["ruleset_key"] = key
        out["scheme"] = scheme
        out["article"] = to_scheme(out["article"], frm=SUPERSEDED_SCHEME, to=scheme)
    return out


def edition_clocks(nodes: list[dict[str, Any]], *, scheme: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """CLOCKS_ADOPTED (reviewed against the 2020 Administration article),
    re-validated against the new Code. Returns (clocks, reworded)."""
    old_nodes = build_clocks._load_adopted_nodes()
    art = to_scheme(7, frm=SUPERSEDED_SCHEME, to=scheme)
    new_nodes = _flat(nodes)

    def within_days(ns: list[dict[str, Any]], article: int) -> set[tuple[str, str]]:
        as_seven = [dict(n, article=7 if n["article"] == article else 0) for n in ns]
        return {(s, sub) for (_, s, sub) in build_clocks._duty_citations_in_text(as_seven)}

    old_found, new_found = within_days(old_nodes, 7), within_days(new_nodes, art)
    if not old_found:
        raise EditionBuildError(
            "found no 'within ... days' clauses in the superseded Administration article -- the "
            "coverage comparison below would pass vacuously, so it refuses instead")
    if old_found != new_found:
        raise EditionBuildError(
            "the 'within ... days' clauses of the Administration article changed -- "
            f"new: {sorted(new_found - old_found)}, gone: {sorted(old_found - new_found)}. "
            "A person must review CLOCKS_ADOPTED against the adopted text before a binding "
            "clock set can be built."
        )

    clocks, reworded = [], []
    for c in build_clocks.CLOCKS_ADOPTED:
        cit = c["citation"]
        old_text = build_clocks._find_text(old_nodes, 7, cit["section"], cit["subsection"])
        new_text = build_clocks._find_text(new_nodes, art, cit["section"], cit["subsection"])
        if new_text is None:
            raise EditionBuildError(
                f"{c['clock_key']}: Article {art} §{cit['section']}.{cit['subsection']} does not exist "
                f"in the adopted Code"
            )
        c2 = json.loads(json.dumps(c))
        c2["citation"]["article"] = art
        if c["source_text"].strip() not in new_text:
            nums_old, nums_new = re.findall(r"\d+", old_text or ""), re.findall(r"\d+", new_text)
            if nums_old != nums_new or str(c["days"]) not in nums_new:
                raise EditionBuildError(
                    f"{c['clock_key']}: the governing sentence changed and its numbers changed with it "
                    f"({nums_old} -> {nums_new}). A person must decide the new clock.\n"
                    f"  superseded: {old_text!r}\n  adopted:    {new_text!r}"
                )
            c2["source_text"] = new_text
            reworded.append({"clock_key": c["clock_key"], "citation": c2["citation"],
                             "superseded_text": c["source_text"], "adopted_text": new_text})
        clocks.append(c2)
    return clocks, reworded


def edition_criteria(nodes: list[dict[str, Any]], *, key: str, scheme: str, old_key: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The 21 Subdivision Plan approval standards, verbatim from the new Code,
    classified by the same reviewed table. Returns (artifact, changed)."""
    art = to_scheme(7, frm=SUPERSEDED_SCHEME, to=scheme)
    group = [n for n in nodes if n["article"] == art and n.get("section") == "12" and n.get("subsection") == "f"]
    if not group or any(_norm(n.get("section_name")) != "subdivision"
                        or _norm(n.get("subsection_name")) != "approval standards" for n in group):
        raise EditionBuildError(
            f"Article {art} §12.f is not SUBDIVISION / APPROVAL STANDARDS in the adopted Code")
    letters = [n["path"][1] for n in group if len(n["path"]) == 2 and n["path"][0] == "1"]
    if letters != criteria_build.EXPECTED_LETTERS:
        raise EditionBuildError(f"Article {art} §12.f.1 standards are {letters}, expected a-u")

    standards = []
    for letter in letters:
        node = next(n for n in group if n["path"] == ["1", letter])
        kids = [{"number": k["path"][2], "text": k["text"]}
                for k in group if len(k["path"]) == 3 and k["path"][:2] == ["1", letter]]
        standards.append({"number": letter, "text": node["text"], "children": kids,
                          "source_ref": node.get("source_ref")})

    superseded = json.loads((RULESETS_DIR / old_key / "criteria-subdivision.json").read_text(encoding="utf-8"))
    old_text = {r["standard_letter"]: r["source_text"] for r in superseded["rules"]}

    rows = criteria_build.build_rule_rows(standards)
    for row in rows:
        # Tells are the reviewer's category labels ("adverse effect" also names
        # "adversely affect"), so they are not all literal. What must not happen
        # is a word that WAS literally in the reviewed 2020 text vanishing from
        # the adopted text while its classification silently carries over.
        before, after = old_text[row["standard_letter"]].casefold(), row["source_text"].casefold()
        gone = [t for t in row["judgement_tells"] if t.casefold() in before and t.casefold() not in after]
        if gone:
            raise EditionBuildError(
                f"standard {row['standard_letter']}: classified 'judgement' on {gone}, which appeared in "
                f"the superseded text but not in the adopted text -- the classification must be re-reviewed")
        row["rule_key"] = f"art{art}.12.f.1.{row['standard_letter']}"
    rows = _renumber_citations(rows, key=key, scheme=scheme, old_key=old_key)
    criteria_set = _renumber_citations(criteria_build.build_criteria_set(), key=key, scheme=scheme, old_key=old_key)
    criteria_set["label"] = f"Subdivision — Article {art} §12.f.1 Approval Standards"

    def _straight(t: str) -> str:
        return t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"').strip()

    changed = [{"standard_letter": r["standard_letter"],
                "quotation_marks_only": _straight(old_text[r["standard_letter"]]) == _straight(r["source_text"]),
                "superseded_text": old_text[r["standard_letter"]], "adopted_text": r["source_text"]}
               for r in rows if old_text.get(r["standard_letter"]) != r["source_text"]]

    by_kind: dict[str, int] = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    artifact = {
        "schema": "newcastle.criteria-subdivision/1.0.0",
        "ruleset_key": key,
        "generated_at": _utc_now_iso(),
        "source": {"path": f"rulesets/{key}/articles.json"},
        "node_id": f"{key}:a{art}.s12.f.1",
        "criteria_set": criteria_set,
        "rules": rows,
        "counts": {"rules": len(rows), "by_kind": by_kind,
                   "judgement_letters": sorted(r["standard_letter"] for r in rows if r["kind"] == "judgement")},
        "text_changed_from_superseded": [c["standard_letter"] for c in changed],
    }
    return artifact, changed


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #


def build(*, tag: str, adopted_on: str, key: str, supersedes: str) -> dict[str, Any]:
    """Builds everything in memory. Writes nothing."""
    scheme = key
    if scheme not in SCHEME_TO_DRAFT or scheme in (SUPERSEDED_SCHEME, "draft"):
        raise EditionBuildError(
            f"no numbering map for {scheme!r} -- add it to app/citation.py SCHEME_TO_DRAFT "
            f"(identity if the adopted Code keeps the draft's numbering) before building its ruleset")
    date.fromisoformat(adopted_on)
    old_manifest_path = RULESETS_DIR / supersedes / "manifest.json"
    old_manifest = json.loads(old_manifest_path.read_text(encoding="utf-8"))
    if not old_manifest.get("binding"):
        raise EditionBuildError(f"{supersedes!r} is not a binding ruleset; only an adopted Code is superseded")
    if old_manifest.get("status") == "superseded" and (old_manifest.get("superseded_by") or {}).get("ruleset_key") != key:
        raise EditionBuildError(f"{supersedes!r} was already superseded by {old_manifest['superseded_by']}")

    prov = provenance(tag)
    with tempfile.TemporaryDirectory() as tmp:
        src = stage_source(tag, Path(tmp))
        tagged = lambda name: f"{tag}:source/{name}"  # noqa: E731

        articles = parse_articles.build_articles(key, src)
        articles["source_dir"] = f"{tag}:source/"
        articles["article_scheme"] = scheme
        uses = parse_articles.build_uses_map(articles["nodes"], key)
        definitions = parse_definitions.build_definitions(key, src / "article-09-definitions.md")

        use_matrix = build_use_matrix(src / "article-02-data.json", src / "article-02.typ", key)
        use_matrix["source"]["data_path"] = tagged("article-02-data.json")
        use_matrix["source"]["legend_path"] = tagged("article-02.typ")

        districts = build_districts.build_districts(src / "article-02-data.json", OVERRIDES, key)
        districts["source"]["path"] = tagged("article-02-data.json")

        source_sha256 = {tagged(p.name): _sha256_file(p) for p in sorted(src.iterdir())
                         if p.is_file() and p.name.startswith("article-")}

    clocks, reworded = edition_clocks(articles["nodes"], scheme=scheme)
    clocks_doc = {
        "schema": build_clocks.SCHEMA,
        "ruleset_key": key,
        "article_scheme": scheme,
        "generated_at": _utc_now_iso(),
        "source": {
            "path": f"rulesets/{key}/articles.json",
            "derived_from": f"rulesets/{supersedes}/clocks.json (CLOCKS_ADOPTED, re-validated against {tag})",
            "renumbering": f"{SUPERSEDED_SCHEME} Article 7 -> {scheme} Article {to_scheme(7, frm=SUPERSEDED_SCHEME, to=scheme)}",
            "source_text_reworded": [r["clock_key"] for r in reworded],
        },
        "counts": {"clocks": len(clocks)},
        "clocks": clocks,
    }
    criteria, criteria_changed = edition_criteria(articles["nodes"], key=key, scheme=scheme, old_key=supersedes)

    old_um = json.loads((RULESETS_DIR / supersedes / "use-matrix.json").read_text(encoding="utf-8"))
    old_cells = {(c["district_key"], c["use_key"]): c for c in old_um["cells"]}
    cells_changed = [
        {"district_key": c["district_key"], "use_key": c["use_key"],
         "superseded_code": old_cells[(c["district_key"], c["use_key"])]["code"], "adopted_code": c["code"]}
        for c in use_matrix["cells"]
        if old_cells.get((c["district_key"], c["use_key"]), {}).get("code") != c["code"]
    ]
    old_d = {d["district_key"]: d for d in json.loads((RULESETS_DIR / supersedes / "districts.json").read_text())["districts"]}
    dims_changed = [d["district_key"] for d in districts["districts"]
                    if json.dumps(d.get("dimensions"), sort_keys=True) != json.dumps(old_d.get(d["district_key"], {}).get("dimensions"), sort_keys=True)]

    human = date.fromisoformat(adopted_on)
    title = f"Newcastle Core Zoning Code (Adopted {human:%B} {human.day}, {human.year} — {tag})"
    return {
        "key": key, "scheme": scheme, "supersedes": supersedes, "adopted_on": adopted_on, "title": title,
        "docs": {
            "articles": ("articles.json", articles),
            "definitions": ("definitions.json", definitions),
            "uses": ("uses.json", uses),
            "use_matrix": ("use-matrix.json", use_matrix),
            "districts": ("districts.json", districts),
            "clocks": ("clocks.json", clocks_doc),
            "criteria_subdivision": ("criteria-subdivision.json", criteria),
        },
        "old_manifest": old_manifest,
        "provenance": prov,
        "source_sha256": source_sha256,
        "changes": {
            "clock_source_text_reworded": reworded,
            "subdivision_criteria_text_changed": criteria_changed,
            "use_matrix_cells_changed": cells_changed,
            "district_dimensions_changed": dims_changed,
        },
    }


def write(built: dict[str, Any], *, actor_user_id: str | None) -> dict[str, Any]:
    key, supersedes = built["key"], built["supersedes"]
    out_dir = RULESETS_DIR / key
    out_dir.mkdir(parents=True, exist_ok=True)

    articles_file = out_dir / "articles.json"
    _atomic_write_json(articles_file, built["docs"]["articles"][1])
    articles_sha = _sha256_file(articles_file)
    for logical in ("clocks", "criteria_subdivision"):
        built["docs"][logical][1]["source"]["sha256"] = articles_sha
    for logical, (filename, doc) in built["docs"].items():
        if logical != "articles":
            _atomic_write_json(out_dir / filename, doc)

    old = built["old_manifest"]
    new_id = _existing_or_new_id(key)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "id": new_id,
        "ruleset_key": key,
        "kind": "adopted-czc",
        "title": built["title"],
        "label": built["title"],
        "status": "active",
        "binding": True,
        "article_scheme": built["scheme"],
        "adopted_date": built["adopted_on"],
        "adopted_on": built["adopted_on"],
        "built_at": _utc_now_iso(),
        "builder_version": BUILDER_VERSION,
        "files": {logical: filename for logical, (filename, _) in built["docs"].items()},
        "content_sha256": {logical: _sha256_file(out_dir / filename) for logical, (filename, _) in built["docs"].items()},
        "counts": {logical: doc.get("counts") for logical, (_, doc) in built["docs"].items()},
        "source_sha256": built["source_sha256"],
        "provenance": built["provenance"],
        "supersedes": {"ruleset_key": supersedes, "id": old.get("id"), "adopted_on": old.get("adopted_on")},
        "changes_from_superseded": built["changes"],
    }
    _atomic_write_json(out_dir / "manifest.json", manifest)

    old["status"] = "superseded"
    old["superseded_by"] = {"ruleset_key": key, "id": new_id, "on": built["adopted_on"]}
    _atomic_write_json(RULESETS_DIR / supersedes / "manifest.json", old)

    _atomic_write_json(RULESETS_DIR / "article-map.json", crosswalk.build_article_map())
    register(manifest, old, key=key, supersedes=supersedes, actor_user_id=actor_user_id)
    return manifest


def register(new_manifest: dict[str, Any], old_manifest: dict[str, Any], *, key: str, supersedes: str,
             actor_user_id: str | None) -> None:
    """One transaction: the superseded Code stops being current, the new Code
    becomes current, and the supersession is on the audit chain."""
    from app.audit import append_event
    from app.config import DB_PATH, MIGRATIONS_DIR
    from app.db import connect, migrate

    conn = connect(DB_PATH)
    try:
        migrate(conn, MIGRATIONS_DIR)
        conn.execute("BEGIN;")
        try:
            old_id = _register_ruleset(conn, old_manifest, manifest_path_rel=f"rulesets/{supersedes}/manifest.json",
                                       is_current=False, actor_user_id=actor_user_id)
            new_id = _register_ruleset(conn, new_manifest, manifest_path_rel=f"rulesets/{key}/manifest.json",
                                       is_current=True, actor_user_id=actor_user_id)
            conn.execute("UPDATE rulesets SET superseded_by = ? WHERE id = ?;", (new_id, old_id))
            append_event(
                conn,
                actor_user_id=actor_user_id,
                kind="ruleset.updated",
                payload={"ruleset_key": supersedes, "superseded_by": key, "on": new_manifest["adopted_on"],
                         "reason": f"Town Meeting adopted {new_manifest['provenance']['tag']} on {new_manifest['adopted_on']}"},
                entity_table="rulesets",
                entity_id=old_id,
            )
            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            raise
        print(f"  {supersedes:<14} -> rulesets.id={old_id}  binding=1  is_current=0  superseded_by={new_id}")
        print(f"  {key:<14} -> rulesets.id={new_id}  binding=1  is_current=1")
    finally:
        conn.close()


def _summary(built: dict[str, Any]) -> None:
    ch = built["changes"]
    print(f"{built['title']}")
    print(f"  from tag {built['provenance']['tag']} (source tree {built['provenance']['source_tree'][:12]}), "
          f"supersedes {built['supersedes']!r}")
    for logical, (filename, doc) in built["docs"].items():
        print(f"  {filename:<27} {json.dumps(doc.get('counts'), ensure_ascii=False)}")
    print(f"  use-matrix cells changed from the superseded Code: {len(ch['use_matrix_cells_changed'])} "
          f"{[(c['district_key'], c['use_key'], c['superseded_code'], c['adopted_code']) for c in ch['use_matrix_cells_changed']]}")
    print(f"  district dimensions changed: {ch['district_dimensions_changed'] or 'none'}")
    print(f"  clock sentences reworded (numbers unchanged): {[r['clock_key'] for r in ch['clock_source_text_reworded']] or 'none'}")
    crit = ch["subdivision_criteria_text_changed"]
    print(f"  subdivision standards reworded: {[c['standard_letter'] for c in crit if not c['quotation_marks_only']] or 'none'}"
          f"; quotation marks only (PDF curly vs markdown straight): {[c['standard_letter'] for c in crit if c['quotation_marks_only']] or 'none'}")
    for c in crit:
        if not c["quotation_marks_only"]:
            print(f"    {c['standard_letter']}: {c['superseded_text'][:110]!r}\n       -> {c['adopted_text'][:110]!r}")
    for r in ch["clock_source_text_reworded"]:
        print(f"    clock {r['clock_key']}: {r['superseded_text'][-60:]!r}\n       -> {r['adopted_text'][-60:]!r}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tag", required=True)
    ap.add_argument("--adopted-on", required=True, help="Town Meeting date, ISO (YYYY-MM-DD)")
    ap.add_argument("--key", required=True, help="new ruleset key, also its article scheme (e.g. adopted-v1.0)")
    ap.add_argument("--supersedes", required=True, help="ruleset key of the Code this one replaces")
    ap.add_argument("--actor-user-id", default=None)
    ap.add_argument("--dry-run", action="store_true", help="build and report; write nothing")
    args = ap.parse_args(argv)
    try:
        built = build(tag=args.tag, adopted_on=args.adopted_on, key=args.key, supersedes=args.supersedes)
    except EditionBuildError as exc:
        print(f"build_edition: refusing -- {exc}", file=sys.stderr)
        return 1
    _summary(built)
    if args.dry_run:
        print("(dry run — nothing written)")
        return 0
    write(built, actor_user_id=args.actor_user_id)
    print(f"wrote rulesets/{args.key}/ and marked rulesets/{args.supersedes} superseded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
