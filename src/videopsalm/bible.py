"""Bible reference parsing and licensed verse lookup primitives."""

from dataclasses import dataclass
import re
from typing import Mapping


@dataclass(frozen=True, slots=True)
class BibleReference:
    book: str
    chapter: int
    verse_start: int
    verse_end: int | None = None

    def __post_init__(self) -> None:
        if self.chapter < 1 or self.verse_start < 1:
            raise ValueError("Bible references must use positive chapter and verse numbers")
        if self.verse_end is not None and self.verse_end < self.verse_start:
            raise ValueError("verse range must be ordered")


_BOOK_ALIASES: Mapping[str, str] = {
    "genesis": "Genesis", "gen": "Genesis",
    "exodus": "Exodus", "ex": "Exodus",
    "psalm": "Psalms", "psalms": "Psalms", "ps": "Psalms",
    "proverbs": "Proverbs", "prov": "Proverbs",
    "isaiah": "Isaiah", "isa": "Isaiah",
    "matthew": "Matthew", "matt": "Matthew",
    "mark": "Mark", "mk": "Mark",
    "luke": "Luke", "lk": "Luke",
    "john": "John", "jn": "John",
    "acts": "Acts",
    "romans": "Romans", "rom": "Romans",
    "corinthians": "Corinthians", "cor": "Corinthians",
    "galatians": "Galatians", "gal": "Galatians",
    "ephesians": "Ephesians", "eph": "Ephesians",
    "philippians": "Philippians", "phil": "Philippians",
    "colossians": "Colossians", "col": "Colossians",
    "hebrews": "Hebrews", "heb": "Hebrews",
    "james": "James", "jas": "James",
    "peter": "Peter",
    "jude": "Jude",
    "revelation": "Revelation", "revelations": "Revelation", "rev": "Revelation",
}

_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50}


def _number(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    words = value.replace("-", " ").split()
    if len(words) == 1:
        return _ONES.get(words[0]) or _TENS.get(words[0])
    if len(words) == 2 and words[0] in _TENS and words[1] in _ONES:
        return _TENS[words[0]] + _ONES[words[1]]
    return None


_NUMBER = r"(\d+|[a-z]+(?:[- ][a-z]+)?)"
_BOOK = r"(?P<book>(?:\d\s*)?[a-z]+)"


def parse_reference(text: str, *, context: BibleReference | None = None) -> BibleReference | None:
    """Parse common written/spoken references, optionally using prior context."""
    normalized = re.sub(r"[^a-z0-9:\- ]", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    book_match = re.search(_BOOK, normalized)
    book: str | None = None
    if book_match:
        candidate = book_match.group("book").strip()
        parts = candidate.split()
        prefix = f"{parts[0]} " if parts and parts[0].isdigit() else ""
        name = " ".join(parts[1:] if prefix else parts)
        if name in _BOOK_ALIASES:
            book = prefix + _BOOK_ALIASES[name]
    if book is None and context is not None:
        book = context.book
    if book is None:
        return _parse_continuation(normalized, context)

    remainder = normalized[book_match.end():].strip()
    match = re.search(
        rf"(?:chapter\s+)?{_NUMBER}(?:\s*:\s*|\s+(?:verse|verses)\s+){_NUMBER}"
        rf"(?:\s+(?:through|to|-)\s+{_NUMBER})?",
        remainder,
    )
    if not match:
        return _parse_continuation(normalized, context) if context else None
    chapter = _number(match.group(1))
    verse_start = _number(match.group(2))
    verse_end = _number(match.group(3)) if match.group(3) else None
    if chapter is None or verse_start is None:
        return None
    return BibleReference(book, chapter, verse_start, verse_end)


def _parse_continuation(text: str, context: BibleReference | None) -> BibleReference | None:
    if context is None:
        return None
    match = re.search(rf"(?:verses?|and)\s+{_NUMBER}", text)
    if not match:
        return None
    verse = _number(match.group(1))
    return BibleReference(context.book, context.chapter, verse) if verse else None


@dataclass(frozen=True, slots=True)
class BibleTranslation:
    id: str
    language: str
    name: str
    licensed: bool = False


class BibleCatalog:
    """In-memory catalog boundary; persistence and provider licensing come later."""

    def __init__(self, translation: BibleTranslation, verses: Mapping[BibleReference, str]):
        self.translation = translation
        self._verses = dict(verses)

    def lookup(self, reference: BibleReference) -> str:
        if not self.translation.licensed:
            raise PermissionError("translation is not licensed for display")
        try:
            return self._verses[reference]
        except KeyError as exc:
            raise KeyError(f"verse not found: {reference}") from exc
