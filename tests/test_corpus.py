import json
from pathlib import Path

import pytest

from videopsalm import AudioRecording, CorpusLabel, CorpusManifest, validate_manifest


def make_manifest() -> CorpusManifest:
    return CorpusManifest(
        version=1,
        corpus_id="sanctuary-v1",
        privacy_notice="Consented recordings; no public redistribution.",
        recordings=(
            AudioRecording(
                id="service-001",
                path="service-001.wav",
                split="test",
                source_type="mixer",
                sample_rate=48000,
                channels=2,
                duration_seconds=30.0,
                consent_id="consent-001",
                labels=(
                    CorpusLabel(0.0, 4.0, "song_start", song_id="demo"),
                    CorpusLabel(4.0, 8.0, "song_segment", song_id="demo", section_index=0, line_index=0),
                ),
            ),
        ),
    )


def test_manifest_round_trip_and_path_validation(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    make_manifest().save(manifest_path)
    assert validate_manifest(manifest_path, audio_root=tmp_path) == ["recording audio file not found: service-001"]
    (tmp_path / "service-001.wav").write_bytes(b"placeholder")
    loaded = CorpusManifest.load(manifest_path)
    assert validate_manifest(manifest_path, audio_root=tmp_path) == []
    assert loaded.by_split("test")[0].labels[1].line_index == 0


def test_manifest_rejects_overlapping_or_invalid_labels() -> None:
    with pytest.raises(ValueError):
        AudioRecording(
            "bad", "bad.wav", "train", "room", 16000, 1, 4.0, "consent",
            labels=(CorpusLabel(0.0, 2.0, "pause"), CorpusLabel(1.0, 3.0, "dropout")),
        )


def test_validator_reports_empty_manifest(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"version": 1, "corpus_id": "x", "privacy_notice": "notice", "recordings": []}), encoding="utf-8")
    assert validate_manifest(path) == ["manifest contains no recordings"]
