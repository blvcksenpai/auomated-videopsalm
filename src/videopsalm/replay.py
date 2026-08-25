"""Deterministic, timestamp-driven replay utilities for alignment experiments."""

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .alignment import AlignmentEngine, Evidence
from .models import DisplayPosition


@dataclass(frozen=True, slots=True)
class ReplayEvent:
    timestamp: datetime
    evidence: Evidence


@dataclass(frozen=True, slots=True)
class AlignmentTrace:
    timestamp: datetime
    position: DisplayPosition | None
    confidence: float
    mode: str
    reason: str


def replay(
    engine: AlignmentEngine, events: Iterable[ReplayEvent]
) -> tuple[AlignmentTrace, ...]:
    """Process events in supplied timestamp order; never use wall-clock time."""
    traces: list[AlignmentTrace] = []
    previous: datetime | None = None
    for event in events:
        if previous is not None and event.timestamp < previous:
            raise ValueError("replay events must be ordered by timestamp")
        previous = event.timestamp
        state = engine.observe(event.evidence)
        recognition = engine.recognition_state
        traces.append(
            AlignmentTrace(
                timestamp=event.timestamp,
                position=state.position,
                confidence=recognition.confidence,
                mode=recognition.mode.value,
                reason=recognition.reason,
            )
        )
    return tuple(traces)
