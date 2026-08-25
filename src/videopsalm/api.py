"""Local HTTP and WebSocket API for an alignment engine.

The API has no engine singleton: callers create an application with the
engine instance that should receive evidence and operator actions.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .alignment import AlignmentEngine, Evidence
from .models import (
    DisplayPosition,
    DisplayState,
    OperatorAction,
    OperatorActionType,
    RecognitionState,
    SectionKind,
    Song,
    SongSection,
)


class PositionPayload(BaseModel):
    """JSON representation of a display position."""

    section_index: int = Field(ge=0)
    line_index: int = Field(ge=0)

    def to_domain(self) -> DisplayPosition:
        return DisplayPosition(self.section_index, self.line_index)


class EvidencePayload(BaseModel):
    """Validated recognition evidence accepted by the API."""

    song_id: str = Field(min_length=1)
    position: PositionPayload
    confidence: float = Field(ge=0.0, le=1.0)
    skip_ahead: bool = False
    repeat: bool = False

    def to_domain(self) -> Evidence:
        return Evidence(
            song_id=self.song_id,
            position=self.position.to_domain(),
            confidence=self.confidence,
            skip_ahead=self.skip_ahead,
            repeat=self.repeat,
        )


class ActionPayload(BaseModel):
    """Validated operator action accepted by the API."""

    type: OperatorActionType
    song_id: str | None = Field(default=None, min_length=1)
    position: PositionPayload | None = None
    amount: int = Field(default=1, ge=1)

    def to_domain(self) -> OperatorAction:
        if self.type is OperatorActionType.MANUAL_SELECT:
            if self.song_id is None or self.position is None:
                raise ValueError(
                    "manual_select requires song_id and position"
                )
        return OperatorAction(
            type=self.type,
            song_id=self.song_id,
            position=self.position.to_domain() if self.position else None,
            amount=self.amount,
        )


def _position_json(position: DisplayPosition | None) -> dict[str, int] | None:
    if position is None:
        return None
    return {
        "section_index": position.section_index,
        "line_index": position.line_index,
    }


def _display_json(state: DisplayState) -> dict[str, object]:
    return {
        "song_id": state.song_id,
        "position": _position_json(state.position),
        "visible": state.visible,
        "frozen": state.frozen,
        "manual": state.manual,
        "paused": state.paused,
        "repeat_count": state.repeat_count,
    }


def _recognition_json(state: RecognitionState) -> dict[str, object]:
    return {
        "mode": state.mode.value,
        "confidence": state.confidence,
        "candidate_song_id": state.candidate_song_id,
        "pending_position": _position_json(state.pending_position),
        "reason": state.reason,
    }


def serialize_state(engine: AlignmentEngine) -> dict[str, object]:
    """Return a JSON-safe snapshot of display and recognition state."""

    return {
        "display": _display_json(engine.state),
        "recognition": _recognition_json(engine.recognition_state),
    }


class _ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, object]) -> None:
        disconnected: list[WebSocket] = []
        for websocket in tuple(self._connections):
            try:
                await websocket.send_json(message)
            except (WebSocketDisconnect, RuntimeError):
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket)


def create_app(engine: AlignmentEngine) -> FastAPI:
    """Create a local API bound to *engine*.

    Each application owns its WebSocket connection manager and engine
    reference, which keeps tests and multiple local services isolated.
    """

    api = FastAPI(title="VideoPsalm local API")
    api.state.engine = engine
    api.state.connections = _ConnectionManager()

    def get_engine(request: Request) -> AlignmentEngine:
        return request.app.state.engine

    @api.get("/status")
    async def status(
        current_engine: AlignmentEngine = Depends(get_engine),
    ) -> dict[str, object]:
        return serialize_state(current_engine)

    @api.post("/actions")
    @api.post("/action", include_in_schema=False)
    async def action(
        payload: ActionPayload,
        current_engine: AlignmentEngine = Depends(get_engine),
    ) -> dict[str, object]:
        try:
            current_engine.act(payload.to_domain())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        await api.state.connections.broadcast(serialize_state(current_engine))
        return serialize_state(current_engine)

    @api.post("/evidence")
    @api.post("/recognition/evidence", include_in_schema=False)
    async def evidence(
        payload: EvidencePayload,
        current_engine: AlignmentEngine = Depends(get_engine),
    ) -> dict[str, object]:
        try:
            current_engine.observe(payload.to_domain())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        await api.state.connections.broadcast(serialize_state(current_engine))
        return serialize_state(current_engine)

    @api.websocket("/ws")
    async def websocket(websocket: WebSocket) -> None:
        manager: _ConnectionManager = api.state.connections
        await manager.connect(websocket)
        try:
            await websocket.send_json(serialize_state(api.state.engine))
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    return api


def demo_app() -> FastAPI:
    """Build a small local demo app for the documented Uvicorn command."""

    song = Song(
        id="demo",
        title="Demo",
        sections=(
            SongSection("verse", "Verse", ("First line", "Second line"), SectionKind.VERSE),
        ),
    )
    return create_app(AlignmentEngine(song))
