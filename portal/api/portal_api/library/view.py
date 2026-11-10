"""Which entries this request may show (design 2, §5).

Public: live entries only, whatever any setting says. The LAN copy: every entry not pulled, with
what isn't live marked as a draft. A pull hides an entry in both, at once. The view is set once
per request (main.py) and read wherever the guide loads its content.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from .model import LibraryEntry, is_live


@dataclass(frozen=True)
class View:
    public: bool = False
    pulled: frozenset[str] = frozenset()
    # Every standard the guide checks needs an entry, or it goes to the Town (decision 12). Only a
    # test of the checks themselves turns this off.
    covers_standards: bool = True


_current: ContextVar[View] = ContextVar("library_view", default=View())


def current() -> View:
    return _current.get()


def set_view(view: View) -> None:
    _current.set(view)


@contextmanager
def using(view: View) -> Iterator[None]:
    token = _current.set(view)
    try:
        yield
    finally:
        _current.reset(token)


def visible(e: LibraryEntry, *, public: bool, pulled: frozenset[str]) -> bool:
    return is_live(e, pulled) if public else e.id not in pulled and e.status != "pulled"
