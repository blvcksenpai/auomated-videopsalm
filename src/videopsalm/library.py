"""Song library and service-plan models for set-list matching."""

from dataclasses import dataclass

from .models import Song


@dataclass(frozen=True, slots=True)
class LibraryEntry:
    song_id: str
    licensed: bool = True
    owner: str | None = None


@dataclass(frozen=True, slots=True)
class SetListItem:
    kind: str
    target_id: str
    label: str

    def __post_init__(self) -> None:
        if self.kind not in {"song", "passage", "announcement"}:
            raise ValueError("set-list item kind is not supported")
        if not self.target_id.strip() or not self.label.strip():
            raise ValueError("item target and label are required")


@dataclass(frozen=True, slots=True)
class SetList:
    id: str
    name: str
    items: tuple[SetListItem, ...]

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("set-list id and name are required")
        if not self.items:
            raise ValueError("a set-list must contain at least one item")

    def resolve_song_ids(self) -> tuple[str, ...]:
        return tuple(item.target_id for item in self.items if item.kind == "song")


class SongLibrary:
    """Curated song library used for candidate narrowing and service matching."""

    def __init__(self) -> None:
        self._songs: dict[str, Song] = {}
        self._entries: dict[str, LibraryEntry] = {}

    def add(self, song: Song, *, licensed: bool = True, owner: str | None = None) -> None:
        if song.id in self._songs:
            raise ValueError(f"song already exists in library: {song.id}")
        self._songs[song.id] = song
        self._entries[song.id] = LibraryEntry(song.id, licensed=licensed, owner=owner)

    def get(self, song_id: str) -> Song:
        try:
            return self._songs[song_id]
        except KeyError as exc:
            raise KeyError(f"song not found in library: {song_id}") from exc

    def contains(self, song_id: str) -> bool:
        return song_id in self._songs

    def search(self, query: str) -> tuple[Song, ...]:
        if not query.strip():
            return tuple()
        needle = query.lower()
        results: list[Song] = []
        for song in self._songs.values():
            haystack = song.title.lower()
            for section in song.sections:
                for line in section.lines:
                    haystack += " " + line.lower()
            if needle in haystack:
                results.append(song)
        return tuple(results)

    def items(self) -> tuple[Song, ...]:
        return tuple(self._songs.values())

    def is_licensed(self, song_id: str) -> bool:
        return self._entries.get(song_id, LibraryEntry(song_id, licensed=False)).licensed
