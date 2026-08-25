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
]
