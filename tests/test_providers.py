from datetime import datetime, timedelta, timezone

import pytest

from videopsalm import AudioChunk, AudioEvidence, TranscriptToken


START = datetime(2026, 8, 25, tzinfo=timezone.utc)


def test_audio_chunk_requires_valid_audio_format() -> None:
    chunk = AudioChunk(b"\x00\x01", 16_000, 1, START)
    assert chunk.sample_rate == 16_000

    with pytest.raises(ValueError):
        AudioChunk(b"", 16_000, 1, START)


def test_transcript_token_validates_confidence_and_timestamps() -> None:
    token = TranscriptToken("John", 0.9, START, START + timedelta(milliseconds=100))
    assert not token.is_final

    with pytest.raises(ValueError):
        TranscriptToken("3:16", 1.1, START, START)


def test_audio_evidence_validates_activity_ranges() -> None:
    evidence = AudioEvidence(START, START + timedelta(seconds=1), 0.8, 0.2, 0.9)
    assert evidence.music_activity == 0.9

    with pytest.raises(ValueError):
        AudioEvidence(START, START, -0.1, 0.0, 0.0)
