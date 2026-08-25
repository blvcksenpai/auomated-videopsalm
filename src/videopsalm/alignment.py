"""Deterministic, audio-evidence-driven lyric alignment state machine.

There is deliberately no clock or background task in this module.  A display
transition can only be caused by a qualifying evidence event or an operator
action.
"""

from dataclasses import dataclass, replace
from typing import Optional

from .models import (
    DisplayPosition,
    DisplayState,
    OperatorAction,
    OperatorActionType,
    RecognitionMode,
    RecognitionState,
    Song,
)


@dataclass(frozen=True, slots=True)
class AlignmentConfig:
    confidence_threshold: float = 0.75
    hysteresis: int = 2
    max_skip_ahead: int = 4

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1")
        if self.hysteresis < 1 or self.max_skip_ahead < 1:
            raise ValueError("hysteresis and max_skip_ahead must be positive")


@dataclass(frozen=True, slots=True)
class Evidence:
    """One recognition result. It is the only automatic input to the engine."""

    song_id: str
    position: DisplayPosition
    confidence: float
    skip_ahead: bool = False
    repeat: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


class AlignmentEngine:
    """Align recognition evidence while preserving the last safe display."""

    def __init__(self, song: Song, config: AlignmentConfig | None = None) -> None:
        self.song = song
        self.config = config or AlignmentConfig()
        self.display = DisplayState()
        self.recognition = RecognitionState()
        self._pending_count = 0

    @property
    def state(self) -> DisplayState:
        return self.display

    @property
    def recognition_state(self) -> RecognitionState:
        return self.recognition

    def observe(self, evidence: Evidence) -> DisplayState:
        """Consume evidence; low confidence and invalid jumps hold the display."""
        self.recognition = replace(
            self.recognition,
            confidence=evidence.confidence,
            candidate_song_id=evidence.song_id,
        )
        if self._automation_locked:
            return self.display
        if evidence.song_id != self.song.id or not self.song.contains(evidence.position):
            return self._uncertain("evidence does not match the active song")
        if evidence.confidence < self.config.confidence_threshold:
            return self._uncertain("confidence below threshold")

        current = self.display.position
        if current is not None and evidence.position == current:
            self._pending_count = 0
            if evidence.repeat:
                self.display = replace(
                    self.display, repeat_count=self.display.repeat_count + 1
                )
            self.recognition = replace(self.recognition, mode=RecognitionMode.TRACKING,
                                       pending_position=None, reason="confirmed position")
            return self.display

        if current is not None:
            distance = self._distance(current, evidence.position)
            is_forward = distance > 0
            is_backward = distance < 0
            allowed = (
                (is_forward and (evidence.skip_ahead or distance == 1)
                 and (evidence.skip_ahead is False or distance <= self.config.max_skip_ahead))
                or (is_backward and evidence.repeat)
            )
            if not allowed:
                return self._uncertain("unconfirmed or unbounded position change")

        if self.recognition.pending_position == evidence.position:
            self._pending_count += 1
        else:
            self._pending_count = 1
        self.recognition = replace(
            self.recognition,
            mode=RecognitionMode.UNCERTAIN,
            pending_position=evidence.position,
            reason=f"awaiting hysteresis ({self._pending_count}/{self.config.hysteresis})",
        )
        if self._pending_count < self.config.hysteresis:
            return self.display

        repeat_count = self.display.repeat_count
        if current is not None and self._distance(current, evidence.position) < 0:
            repeat_count += 1
        self.display = replace(
            self.display,
            song_id=evidence.song_id,
            position=evidence.position,
            visible=True,
            repeat_count=repeat_count,
        )
        self._pending_count = 0
        self.recognition = replace(
            self.recognition,
            mode=RecognitionMode.TRACKING,
            pending_position=None,
            reason="position confirmed from live evidence",
        )
        return self.display

    def act(self, action: OperatorAction) -> DisplayState:
        """Apply an operator action. Automated evidence cannot override locks."""
        kind = action.type
        if kind is OperatorActionType.RESUME:
            self.display = replace(
                self.display, visible=True, frozen=False, manual=False, paused=False
            )
            self._pending_count = 0
            self.recognition = replace(
                self.recognition,
                mode=RecognitionMode.TRACKING
                if self.display.position is not None
                else RecognitionMode.SEARCHING,
                reason="automation resumed by operator",
            )
            return self.display
        if kind is OperatorActionType.PAUSE:
            self.display = replace(self.display, paused=True)
            self._pending_count = 0
            self.recognition = replace(self.recognition, mode=RecognitionMode.PAUSED,
                                       reason="paused by operator")
            return self.display
        if kind is OperatorActionType.FREEZE:
            self.display = replace(self.display, frozen=True, manual=True)
            self._pending_count = 0
            self.recognition = replace(self.recognition, mode=RecognitionMode.MANUAL,
                                       reason="frozen by operator")
            return self.display
        if kind is OperatorActionType.BLANK:
            self.display = replace(self.display, visible=False, manual=True)
            self._pending_count = 0
            self.recognition = replace(self.recognition, mode=RecognitionMode.MANUAL,
                                       reason="blanked by operator")
            return self.display
        if kind is OperatorActionType.MANUAL_SELECT:
            if action.song_id != self.song.id or action.position is None \
                    or not self.song.contains(action.position):
                raise ValueError("manual selection must target the active song")
            self.display = replace(
                self.display, song_id=action.song_id, position=action.position,
                visible=True, frozen=False, manual=True, paused=False, repeat_count=0,
            )
            self._pending_count = 0
            self.recognition = replace(self.recognition, mode=RecognitionMode.MANUAL,
                                       candidate_song_id=action.song_id,
                                       reason="manually selected by operator")
            return self.display

        if kind in (OperatorActionType.SKIP_AHEAD, OperatorActionType.REPEAT):
            if self.display.position is None:
                raise ValueError("cannot navigate before a position is selected")
            target = self._navigate(self.display.position, action.amount,
                                    forward=kind is OperatorActionType.SKIP_AHEAD)
            self.display = replace(
                self.display, song_id=self.song.id, position=target, visible=True,
                manual=True, frozen=False, paused=False,
                repeat_count=self.display.repeat_count + (1 if kind is OperatorActionType.REPEAT else 0),
            )
            self._pending_count = 0
            self.recognition = replace(self.recognition, mode=RecognitionMode.MANUAL,
                                       reason=f"{kind.value} by operator")
            return self.display
        raise ValueError(f"unsupported operator action: {kind}")

    def set_recognition_mode(self, mode: RecognitionMode, reason: str = "") -> None:
        """Expose provider disconnect/reconnect states without changing the display."""
        self.recognition = replace(self.recognition, mode=mode, reason=reason)

    @property
    def _automation_locked(self) -> bool:
        return (
            self.display.frozen
            or self.display.manual
            or self.display.paused
            or self.recognition.mode in {
                RecognitionMode.MANUAL,
                RecognitionMode.PAUSED,
                RecognitionMode.DISCONNECTED,
                RecognitionMode.RECONNECTING,
            }
        )

    def _uncertain(self, reason: str) -> DisplayState:
        self._pending_count = 0
        self.recognition = replace(
            self.recognition, mode=RecognitionMode.UNCERTAIN,
            pending_position=None, reason=reason,
        )
        return self.display

    def _distance(self, start: DisplayPosition, end: DisplayPosition) -> int:
        return self._ordinal(end) - self._ordinal(start)

    def _ordinal(self, position: DisplayPosition) -> int:
        return sum(len(section.lines) for section in self.song.sections[:position.section_index]) \
            + position.line_index

    def _navigate(self, position: DisplayPosition, amount: int, *, forward: bool) -> DisplayPosition:
        ordinal = self._ordinal(position) + (amount if forward else -amount)
        if ordinal < 0:
            ordinal = 0
        total = sum(len(section.lines) for section in self.song.sections)
        ordinal = min(ordinal, total - 1)
        for section_index, section in enumerate(self.song.sections):
            if ordinal < len(section.lines):
                return DisplayPosition(section_index, ordinal)
            ordinal -= len(section.lines)
        raise AssertionError("song contains no navigable positions")


# A descriptive alias for callers that prefer the plan's terminology.
LyricAlignmentStateMachine = AlignmentEngine
RecognitionEvidence = Evidence
