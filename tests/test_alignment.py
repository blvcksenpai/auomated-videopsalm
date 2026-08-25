import pytest

from videopsalm import (
    AlignmentConfig,
    AlignmentEngine,
    DisplayPosition,
    Evidence,
    OperatorAction,
    OperatorActionType,
    RecognitionMode,
    SectionKind,
    Song,
    SongSection,
)


@pytest.fixture
def song() -> Song:
    return Song(
        id="amazing-grace",
        title="Amazing Grace",
        sections=(
            SongSection("verse-1", "Verse 1", ("Amazing grace", "How sweet the sound"), SectionKind.VERSE),
            SongSection("chorus", "Chorus", ("I once was lost", "But now am found"), SectionKind.CHORUS),
            SongSection("verse-2", "Verse 2", ("Twas grace that taught", "And grace my fears relieved"), SectionKind.VERSE),
        ),
    )


@pytest.fixture
def engine(song: Song) -> AlignmentEngine:
    return AlignmentEngine(song, AlignmentConfig(confidence_threshold=0.8, hysteresis=2))


def evidence(position: DisplayPosition, confidence: float = 0.95, **kwargs: object) -> Evidence:
    return Evidence("amazing-grace", position, confidence, **kwargs)


def test_normal_advancement_requires_hysteresis(engine: AlignmentEngine) -> None:
    first = DisplayPosition(0, 0)
    second = DisplayPosition(0, 1)
    engine.observe(evidence(first))
    assert engine.display.position is None
    engine.observe(evidence(first))
    assert engine.display.position == first
    engine.observe(evidence(second))
    assert engine.display.position == first
    engine.observe(evidence(second))
    assert engine.display.position == second
    assert engine.recognition.mode is RecognitionMode.TRACKING


def test_uncertainty_holds_last_confirmed_state(engine: AlignmentEngine) -> None:
    first = DisplayPosition(0, 0)
    engine.observe(evidence(first))
    engine.observe(evidence(first))
    engine.observe(evidence(DisplayPosition(0, 1), confidence=0.2))
    assert engine.display.position == first
    assert engine.recognition.mode is RecognitionMode.UNCERTAIN


def test_pause_holds_and_resume_requires_new_evidence(engine: AlignmentEngine) -> None:
    first = DisplayPosition(0, 0)
    second = DisplayPosition(0, 1)
    engine.observe(evidence(first))
    engine.observe(evidence(first))
    engine.act(OperatorAction(OperatorActionType.PAUSE))
    engine.observe(evidence(second))
    assert engine.display.position == first
    assert engine.recognition.mode is RecognitionMode.PAUSED
    engine.act(OperatorAction(OperatorActionType.RESUME))
    engine.observe(evidence(second))
    engine.observe(evidence(second))
    assert engine.display.position == second


def test_skip_ahead_and_repeat_are_hysteresis_protected(engine: AlignmentEngine) -> None:
    first = DisplayPosition(0, 0)
    chorus = DisplayPosition(1, 0)
    verse_two = DisplayPosition(2, 0)
    engine.observe(evidence(first))
    engine.observe(evidence(first))
    engine.observe(evidence(chorus, skip_ahead=True))
    engine.observe(evidence(chorus, skip_ahead=True))
    # Automatic skip/repeat evidence can move to a bounded later section.
    engine.act(OperatorAction(OperatorActionType.RESUME))
    engine.observe(evidence(verse_two, skip_ahead=True))
    engine.observe(evidence(verse_two, skip_ahead=True))
    assert engine.display.position == verse_two
    engine.observe(evidence(chorus, repeat=True))
    engine.observe(evidence(chorus, repeat=True))
    assert engine.display.position == chorus
    assert engine.display.repeat_count == 1


def test_operator_skip_and_repeat_take_control(engine: AlignmentEngine) -> None:
    first = DisplayPosition(0, 0)
    engine.observe(evidence(first))
    engine.observe(evidence(first))

    engine.act(OperatorAction.skip_ahead())
    assert engine.display.position == DisplayPosition(0, 1)
    assert engine.display.manual
    engine.act(OperatorAction.repeat())
    assert engine.display.position == first
    assert engine.display.repeat_count == 1


def test_freeze_blank_manual_select_and_resume_have_operator_priority(
    engine: AlignmentEngine,
) -> None:
    first = DisplayPosition(0, 0)
    second = DisplayPosition(0, 1)
    engine.observe(evidence(first))
    engine.observe(evidence(first))

    engine.act(OperatorAction(OperatorActionType.FREEZE))
    engine.observe(evidence(second))
    assert engine.display.position == first
    assert engine.display.frozen

    engine.act(OperatorAction(OperatorActionType.RESUME))
    engine.act(OperatorAction(OperatorActionType.BLANK))
    assert not engine.display.visible
    engine.observe(evidence(second))
    assert engine.display.position == first

    engine.act(OperatorAction.manual_select("amazing-grace", second))
    assert engine.display.position == second
    assert engine.display.manual
    engine.observe(evidence(first))
    assert engine.display.position == second

    engine.act(OperatorAction(OperatorActionType.RESUME))
    assert engine.display.visible
    engine.observe(evidence(first, repeat=True))
    engine.observe(evidence(first, repeat=True))
    assert engine.display.position == first
