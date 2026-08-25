from datetime import datetime, timedelta, timezone

import pytest

from videopsalm import (
    AlignmentEngine,
    AudioHealth,
    AudioStatus,
    DisplayPosition,
    Evidence,
    ReplayEvent,
    SectionKind,
    Song,
    SongSection,
    replay,
)


START = datetime(2026, 8, 25, tzinfo=timezone.utc)


def make_engine() -> AlignmentEngine:
    return AlignmentEngine(
        Song(
            "demo",
            "Demo",
            (SongSection("verse", "Verse", ("one", "two"), SectionKind.VERSE),),
        )
    )


def test_replay_uses_event_timestamps_and_emits_trace() -> None:
    first = Evidence("demo", DisplayPosition(0, 0), 0.9)
    traces = replay(
        make_engine(),
        (
            ReplayEvent(START, first),
            ReplayEvent(START + timedelta(seconds=1), first),
        ),
    )
    assert len(traces) == 2
    assert traces[-1].position == DisplayPosition(0, 0)
    assert traces[-1].mode == "tracking"


def test_replay_rejects_out_of_order_events() -> None:
    event = ReplayEvent(
        START,
        Evidence("demo", DisplayPosition(0, 0), 0.9),
    )
    with pytest.raises(ValueError, match="ordered"):
        replay(make_engine(), (event, ReplayEvent(START - timedelta(seconds=1), event.evidence)))


def test_audio_status_has_explicit_degraded_states() -> None:
    status = AudioStatus(AudioHealth.RECONNECTING, "usb-mixer", START, "input lost")
    assert status.health is AudioHealth.RECONNECTING
