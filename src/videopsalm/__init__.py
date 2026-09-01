"""Core domain models and deterministic alignment for Automated VideoPsalm."""

from .alignment import (
    AlignmentConfig,
    AlignmentEngine,
    Evidence,
    LyricAlignmentStateMachine,
    RecognitionEvidence,
)
from .models import (
    DisplayPosition,
    DisplayState,
    OperatorAction,
    OperatorActionType,
    RecognitionMode,
    RecognitionState,
    SectionKind,
    Song,
    SongSection,
)
from .providers import (
    AudioChunk,
    AudioEvidence,
    AudioFeatureProvider,
    StreamingSpeechProvider,
    TranscriptToken,
)
from .audio_gateway import AudioGateway, AudioHealth, AudioStatus
from .replay import AlignmentTrace, ReplayEvent, replay
from .bible import BibleCatalog, BibleReference, BibleTranslation, parse_reference
from .library import LibraryEntry, SetList, SetListItem, SongLibrary

__all__ = [
    "AlignmentConfig",
    "AlignmentEngine",
    "DisplayPosition",
    "DisplayState",
    "Evidence",
    "LyricAlignmentStateMachine",
    "OperatorAction",
    "OperatorActionType",
    "RecognitionMode",
    "RecognitionEvidence",
    "RecognitionState",
    "SectionKind",
    "Song",
    "SongSection",
    "AudioChunk",
    "AudioEvidence",
    "AudioFeatureProvider",
    "StreamingSpeechProvider",
    "TranscriptToken",
    "AudioGateway",
    "AudioHealth",
    "AudioStatus",
    "AlignmentTrace",
    "ReplayEvent",
    "replay",
    "BibleCatalog",
    "BibleReference",
    "BibleTranslation",
    "parse_reference",
    "LibraryEntry",
    "SetList",
    "SetListItem",
    "SongLibrary",
]
