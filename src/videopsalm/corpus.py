"""Manifest and validation tools for consented sanctuary audio corpora."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


EVENT_TYPES = frozenset({
    "speech_reference",
    "speech_passage",
    "song_start",
    "song_segment",
    "song_repeat",
    "song_skip",
    "pause",
    "dropout",
    "mode_change",
})
SPLITS = frozenset({"train", "validation", "test"})


@dataclass(frozen=True, slots=True)
class CorpusLabel:
    start_seconds: float
    end_seconds: float
    event_type: str
    text: str | None = None
    reference: str | None = None
    song_id: str | None = None
    section_index: int | None = None
    line_index: int | None = None

    def __post_init__(self) -> None:
        if self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise ValueError("label timestamps must be non-negative and ordered")
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported corpus event type: {self.event_type}")
        if self.section_index is not None and self.section_index < 0:
            raise ValueError("section_index must be non-negative")
        if self.line_index is not None and self.line_index < 0:
            raise ValueError("line_index must be non-negative")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CorpusLabel":
        return cls(
            start_seconds=float(value["start_seconds"]),
            end_seconds=float(value["end_seconds"]),
            event_type=str(value["event_type"]),
            text=value.get("text"),
            reference=value.get("reference"),
            song_id=value.get("song_id"),
            section_index=value.get("section_index"),
            line_index=value.get("line_index"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "event_type": self.event_type,
            "text": self.text,
            "reference": self.reference,
            "song_id": self.song_id,
            "section_index": self.section_index,
            "line_index": self.line_index,
        }


@dataclass(frozen=True, slots=True)
class AudioRecording:
    id: str
    path: str
    split: str
    source_type: str
    sample_rate: int
    channels: int
    duration_seconds: float
    consent_id: str
    labels: tuple[CorpusLabel, ...] = ()
    language: str = "en"
    retained_until: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.path.strip() or not self.consent_id.strip():
            raise ValueError("recording id, path, and consent_id are required")
        if self.split not in SPLITS:
            raise ValueError(f"split must be one of {sorted(SPLITS)}")
        if self.sample_rate < 1 or self.channels < 1 or self.duration_seconds <= 0:
            raise ValueError("audio format and duration must be positive")
        previous_end = 0.0
        for label in self.labels:
            if label.end_seconds > self.duration_seconds:
                raise ValueError("label exceeds recording duration")
            if label.start_seconds < previous_end:
                raise ValueError("labels must be ordered and non-overlapping")
            previous_end = label.end_seconds

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AudioRecording":
        labels = tuple(CorpusLabel.from_dict(label) for label in value.get("labels", []))
        return cls(
            id=str(value["id"]),
            path=str(value["path"]),
            split=str(value["split"]),
            source_type=str(value.get("source_type", "mixer")),
            sample_rate=int(value["sample_rate"]),
            channels=int(value["channels"]),
            duration_seconds=float(value["duration_seconds"]),
            consent_id=str(value["consent_id"]),
            labels=labels,
            language=str(value.get("language", "en")),
            retained_until=value.get("retained_until"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "split": self.split,
            "source_type": self.source_type,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration_seconds": self.duration_seconds,
            "consent_id": self.consent_id,
            "language": self.language,
            "retained_until": self.retained_until,
            "labels": [label.to_dict() for label in self.labels],
        }


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    version: int
    corpus_id: str
    recordings: tuple[AudioRecording, ...]
    privacy_notice: str

    def __post_init__(self) -> None:
        if self.version != 1:
            raise ValueError("unsupported corpus manifest version")
        if not self.corpus_id.strip() or not self.privacy_notice.strip():
            raise ValueError("corpus_id and privacy_notice are required")
        ids = [recording.id for recording in self.recordings]
        if len(ids) != len(set(ids)):
            raise ValueError("recording ids must be unique")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CorpusManifest":
        return cls(
            version=int(value["version"]),
            corpus_id=str(value["corpus_id"]),
            privacy_notice=str(value["privacy_notice"]),
            recordings=tuple(AudioRecording.from_dict(item) for item in value.get("recordings", [])),
        )

    @classmethod
    def load(cls, path: str | Path) -> "CorpusManifest":
        with Path(path).open(encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def save(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8") as handle:
            json.dump({
                "version": self.version,
                "corpus_id": self.corpus_id,
                "privacy_notice": self.privacy_notice,
                "recordings": [recording.to_dict() for recording in self.recordings],
            }, handle, indent=2)
            handle.write("\n")

    def validate_paths(self, root: str | Path) -> tuple[str, ...]:
        base = Path(root)
        return tuple(recording.id for recording in self.recordings if not (base / recording.path).is_file())

    def by_split(self, split: str) -> tuple[AudioRecording, ...]:
        if split not in SPLITS:
            raise ValueError(f"split must be one of {sorted(SPLITS)}")
        return tuple(recording for recording in self.recordings if recording.split == split)


def validate_manifest(path: str | Path, *, audio_root: str | Path | None = None) -> list[str]:
    """Return actionable validation errors; successful manifests return []."""
    errors: list[str] = []
    try:
        manifest = CorpusManifest.load(path)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return [str(exc)]
    if not manifest.recordings:
        errors.append("manifest contains no recordings")
    if audio_root is not None:
        for recording_id in manifest.validate_paths(audio_root):
            errors.append(f"recording audio file not found: {recording_id}")
    return errors
