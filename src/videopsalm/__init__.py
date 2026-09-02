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
    "connect",
    "get_song_sections",
    "import_bible_payload",
    "import_openlyrics_xml",
    "initialize",
    "lookup_verse",
    "upsert_song",
    "LibraryEntry",
    "SetList",
    "SetListItem",
    "SongLibrary",
    "AudioRecording",
    "CorpusLabel",
    "CorpusManifest",
    "validate_manifest",
    "PassageItem",
    "ServicePlan",
]

from .storage import (
    connect,
    get_song_sections,
    import_bible_payload,
    import_openlyrics_xml,
    initialize,
    lookup_verse,
    upsert_song,
)

from .service_plan import PassageItem, ServicePlan

from .corpus import AudioRecording, CorpusLabel, CorpusManifest, validate_manifest
