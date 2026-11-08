"""Loading and checking the library's files (library/entries/*.yaml), one batch per file.

A file is `{entries: [...], open_questions: [...]}`. Every key must be one the entry knows (an
unknown key is refused, never dropped), every citation must resolve in the pinned ruleset, and
the statuses carry who approved, ratified, pulled or decided, and when.
"""

import functools
import hashlib
from pathlib import Path

import yaml

from portal_api.forms.definitions import DefinitionError, _check_cite
from portal_api.ruleset import load_ruleset

from .readability import flags
from .terms import article_9_terms
from .model import KINDS, NEVER_WORDS, STATUSES, Library, LibraryEntry, LibraryError, as_date

DIR = Path(__file__).resolve().parent / "entries"
BOARD = "Planning Board"
_KEYS = frozenset(LibraryEntry.__dataclass_fields__) - {"batch"}
_TUPLES = ("cites", "standards", "terms")
_DATES = ("approved_on", "ratified_on", "decided_on", "pulled_on")
_TEXT = ("overline", "answer", "detail", "why", "picture_alt")


def _need(where: str, e: dict, *keys: str) -> None:
    for k in keys:
        if not e.get(k):
            raise LibraryError(f"{where}: needs {k}")


def _date(where: str, e: dict, key: str) -> None:
    try:
        as_date(e.get(key))
    except ValueError:
        raise LibraryError(f"{where}: {key} is not a date") from None


def _check(where: str, e: dict, ruleset) -> None:
    unknown = sorted(set(e) - _KEYS)
    if unknown:
        raise LibraryError(f"{where}: unknown key {', '.join(unknown)}")
    _need(where, e, "id", "kind", "overline", "answer", "detail", "why", "version", "status")
    if e["kind"] not in KINDS:
        raise LibraryError(f"{where}: kind must be one of {', '.join(sorted(KINDS))}")
    if e["status"] not in STATUSES:
        raise LibraryError(f"{where}: status must be one of {', '.join(sorted(STATUSES))}")
    if e["status"] != "draft":
        _need(where, e, "approved_by", "approved_on")
    if e["status"] == "ratified":
        _need(where, e, "ratified_on", "ratified_by")
        if e["ratified_by"] != BOARD:
            raise LibraryError(f"{where}: ratified_by must be {BOARD!r}")
    if e["status"] == "pulled":
        _need(where, e, "pulled_on", "pulled_by", "pulled_why")
    if e["kind"] == "interpretation":
        _need(where, e, "decided_by", "decided_on", "source")
    for k in _DATES:
        _date(where, e, k)
    if e.get("picture") and not e.get("picture_alt"):
        raise LibraryError(f"{where}: a picture needs its picture_alt")
    texts = [e.get(k) or "" for k in _TEXT] + list((e.get("district_notes") or {}).values())
    for t in texts:
        if NEVER_WORDS.search(t):
            raise LibraryError(f"{where}: a never-used word: {NEVER_WORDS.search(t).group(0)!r}")
    for ref in e.get("cites") or []:
        try:
            _check_cite(where, ref, ruleset)
        except DefinitionError as exc:
            raise LibraryError(str(exc)) from None


def _check_slots(where: str, e: dict, keys: frozenset[str]) -> None:
    from .render import PARTS, placeholders
    slots = e.get("slots") or {}
    texts = [e.get(k) or "" for k in ("overline", "answer", "detail", "why")] + list((e.get("district_notes") or {}).values())
    for name in sorted(set().union(*(placeholders(t) for t in texts))):
        if name not in slots:
            raise LibraryError(f"{where}: no slot for {{{name}}}")
    for name, slot in slots.items():
        if not isinstance(slot, dict) or slot.get("part") not in PARTS:
            raise LibraryError(f"{where}: slot {name}: part must be one of {', '.join(sorted(PARTS))}")
        if slot.get("standard") not in keys:
            raise LibraryError(f"{where}: slot {name}: no standard {slot.get('standard')}")
    for key in e.get("standards") or []:
        if key not in keys:
            raise LibraryError(f"{where}: no standard {key}")


@functools.cache
def _load(root: Path) -> Library:
    from .render import all_keys
    keys = all_keys()
    claims: dict[str, str] = {}
    ruleset = load_ruleset()
    files = sorted(root.glob("*.yaml"))
    entries, questions = {}, {}
    for path in files:
        batch = path.stem
        data = yaml.safe_load(path.read_text()) or {}
        questions[batch] = tuple(data.get("open_questions") or ())
        for e in data.get("entries") or []:
            where = f"{batch}: {e.get('id')}"
            _check(where, e, ruleset)
            _check_slots(where, e, keys)
            for key in e.get("standards") or []:
                if key in claims:
                    raise LibraryError(f"{where}: {key} is claimed by both {claims[key]} and {e['id']}")
                claims[key] = e["id"]
            if e["id"] in entries:
                raise LibraryError(f"{where}: duplicate id (also in {entries[e['id']].batch})")
            entries[e["id"]] = LibraryEntry(**{**e, **{k: tuple(e.get(k) or ()) for k in _TUPLES},
                                               "slots": e.get("slots") or {},
                                               "district_notes": e.get("district_notes") or {},
                                               **{k: as_date(e.get(k)) for k in _DATES},
                                               "batch": batch})
    digest = hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()
    terms = article_9_terms()
    found = {i: f for i, e in entries.items() if (f := flags(e, terms))}
    if terms is None:
        found["library"] = ("article 9 terms not available",)
    return Library(entries=entries, open_questions=questions, digest=digest, flags=found)


def load_library(root: Path | None = None) -> Library:
    return _load((root or DIR).resolve())
