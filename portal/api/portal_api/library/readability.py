"""The reading grade of a draft, and the warnings it carries (design 2, §6; decision 14).

Flesch–Kincaid grade level, aiming at about grade 8. An entry's defined terms and its numbers
are left out, since the Code's own words can't be made shorter. Syllables come from vowel groups,
with a silent final "e"; no dictionary. A high grade flags a draft for the chair and never
refuses it.
"""

import re

from .model import LibraryEntry

AIM = 8.0
_WORD = re.compile(r"[A-Za-z']+")
_SENTENCE = re.compile(r"[.!?]+(?:\s|$)")


def _syllables(word: str) -> int:
    w = word.lower().strip("'")
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith("le") and n > 1:
        n -= 1
    return max(n, 1)


def grade(text: str, skip: frozenset[str] = frozenset()) -> float:
    for term in sorted(skip, key=len, reverse=True):
        text = re.sub(re.escape(term), " ", text, flags=re.IGNORECASE)
    words = _WORD.findall(text)
    if not words:
        return 0.0
    sentences = max(len(_SENTENCE.findall(text)), 1)
    syllables = sum(_syllables(w) for w in words)
    return 0.39 * len(words) / sentences + 11.8 * syllables / len(words) - 15.59


def flags(e: LibraryEntry, terms: frozenset[str] | None) -> tuple[str, ...]:
    out = []
    g = grade(" ".join((e.answer, e.detail, e.why)), frozenset(e.terms))
    if g > AIM:
        out.append(f"grade {g:.1f}")
    if terms is not None:
        out += [f"term not in Article 9: {t}" for t in e.terms if t.lower() not in terms]
    return tuple(out)
