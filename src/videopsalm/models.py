"""Small, dependency-free domain model layer."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SectionKind(str, Enum):
    VERSE = "verse"
    PRE_CHORUS = "pre_chorus"
    CHORUS = "chorus"
    BRIDGE = "bridge"
    INTRO = "intro"
    OUTRO = "outro"
    TAG = "tag"
    CUSTOM = "custom"


class RecognitionMode(str, Enum):
    SEARCHING = "searching"
    TRACKING = "tracking"
    UNCERTAIN = "uncertain"
    MANUAL = "manual"
    PAUSED = "paused"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"


class OperatorActionType(str, Enum):
    PAUSE = "pause"
    RESUME = "resume"
    FREEZE = "freeze"
    BLANK = "blank"
    MANUAL_SELECT = "manual_select"
    SKIP_AHEAD = "skip_ahead"
    REPEAT = "repeat"


@dataclass(frozen=True, slots=True)
class DisplayPosition:
    """A zero-based location in a song's ordered display segments."""

    section_index: int
    line_index: int

    def __post_init__(self) -> None:
        if self.section_index < 0 or self.line_index < 0:
            raise ValueError("display positions must be non-negative")


@dataclass(frozen=True, slots=True)
class SongSection:
    id: str
    label: str
    lines: tuple[str, ...]
    kind: SectionKind = SectionKind.CUSTOM

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.label.strip():
            raise ValueError("section id and label are required")
        if not self.lines or any(not line.strip() for line in self.lines):
            raise ValueError("a section must contain non-empty lyric lines")
        object.__setattr__(self, "lines", tuple(self.lines))


@dataclass(frozen=True, slots=True)
class Song:
    id: str
    title: str
    sections: tuple[SongSection, ...]

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.title.strip():
            raise ValueError("song id and title are required")
        if not self.sections:
            raise ValueError("a song must contain at least one section")
        object.__setattr__(self, "sections", tuple(self.sections))

    def contains(self, position: DisplayPosition) -> bool:
        return (
            position.section_index < len(self.sections)
            and position.line_index < len(self.sections[position.section_index].lines)
        )


@dataclass(frozen=True, slots=True)
class DisplayState:
    song_id: Optional[str] = None
    position: Optional[DisplayPosition] = None
    visible: bool = True
    frozen: bool = False
    manual: bool = False
    paused: bool = False
    repeat_count: int = 0


@dataclass(frozen=True, slots=True)
class RecognitionState:
    mode: RecognitionMode = RecognitionMode.SEARCHING
    confidence: float = 0.0
    candidate_song_id: Optional[str] = None
    pending_position: Optional[DisplayPosition] = None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class OperatorAction:
    type: OperatorActionType
    song_id: Optional[str] = None
    position: Optional[DisplayPosition] = None
    amount: int = 1

    def __post_init__(self) -> None:
        if self.amount < 1:
            raise ValueError("action amount must be positive")

    @classmethod
    def manual_select(cls, song_id: str, position: DisplayPosition) -> "OperatorAction":
        return cls(OperatorActionType.MANUAL_SELECT, song_id, position)

    @classmethod
    def skip_ahead(cls, amount: int = 1) -> "OperatorAction":
        return cls(OperatorActionType.SKIP_AHEAD, amount=amount)

    @classmethod
    def repeat(cls, amount: int = 1) -> "OperatorAction":
        return cls(OperatorActionType.REPEAT, amount=amount)
