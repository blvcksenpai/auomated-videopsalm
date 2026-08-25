"""Provider-neutral interfaces for live audio recognition.

Adapters implement these protocols for local or hosted providers. The
alignment engine consumes timestamped evidence and remains provider-agnostic.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Protocol


@dataclass(frozen=True, slots=True)
class AudioChunk:
    """A timestamped PCM audio chunk supplied by the audio gateway."""

    samples: bytes
    sample_rate: int
    channels: int
    started_at: datetime

    def __post_init__(self) -> None:
        if not self.samples:
            raise ValueError("audio chunks must contain samples")
        if self.sample_rate < 1 or self.channels < 1:
            raise ValueError("audio format must have positive rate and channels")


@dataclass(frozen=True, slots=True)
class TranscriptToken:
    text: str
    confidence: float
    started_at: datetime
    ended_at: datetime
    is_final: bool = False

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("transcript tokens must contain text")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.ended_at < self.started_at:
            raise ValueError("token end cannot precede token start")


@dataclass(frozen=True, slots=True)
class AudioEvidence:
    """Non-transcript cues used alongside ASR for singing alignment."""

    started_at: datetime
    ended_at: datetime
    speech_activity: float
    singing_activity: float
    music_activity: float

    def __post_init__(self) -> None:
        if self.ended_at < self.started_at:
            raise ValueError("evidence end cannot precede evidence start")
        for value in (
            self.speech_activity,
            self.singing_activity,
            self.music_activity,
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError("activity values must be between 0 and 1")


class StreamingSpeechProvider(Protocol):
    async def transcribe(
        self, chunks: AsyncIterator[AudioChunk]
    ) -> AsyncIterator[TranscriptToken]:
        """Yield partial and final timestamped transcript tokens."""


class AudioFeatureProvider(Protocol):
    async def analyze(
        self, chunks: AsyncIterator[AudioChunk]
    ) -> AsyncIterator[AudioEvidence]:
        """Yield speech, singing, and music activity evidence."""
