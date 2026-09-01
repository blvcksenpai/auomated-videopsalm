"""Local HTTP and WebSocket API for an alignment engine.

The API has no engine singleton: callers create an application with the
engine instance that should receive evidence and operator actions.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .alignment import AlignmentEngine, Evidence
from .library import SetList, SetListItem, SongLibrary
from .service_plan import PassageItem, ServicePlan
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


def _operator_console_html() -> str:
    return """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>VideoPsalm Operator Console</title>
      <style>
        body { font-family: sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
        .shell { max-width: 1100px; margin: 32px auto; padding: 24px; }
        .grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 24px; }
        .panel { background: #111827; border: 1px solid #334155; border-radius: 12px; padding: 18px; }
        button { background: #2563eb; color: white; border: 0; border-radius: 8px; padding: 10px 14px; cursor: pointer; margin: 6px 6px 0 0; }
        button.secondary { background: #374151; }
        button.warn { background: #b45309; }
        button.danger { background: #b91c1c; }
        .display-box { min-height: 200px; display: flex; align-items: center; justify-content: center; text-align: center; background: #020617; border-radius: 12px; border: 1px solid #475569; font-size: clamp(1.8rem, 4vw, 3rem); padding: 18px; }
        .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 12px; }
        .kpi { background: #0b1220; border-radius: 10px; border: 1px solid #334155; padding: 12px; }
        code { background: #0b1220; border-radius: 6px; padding: 2px 6px; }
      </style>
    </head>
    <body>
      <div class="shell">
        <h1>VideoPsalm Operator Console</h1>
        <div class="grid">
          <div class="panel">
            <div id="display" class="display-box">Waiting for service…</div>
            <div class="kpis">
              <div class="kpi"><strong>Mode</strong><br /><span id="mode">searching</span></div>
              <div class="kpi"><strong>Song</strong><br /><span id="song">—</span></div>
              <div class="kpi"><strong>Position</strong><br /><span id="position">—</span></div>
              <div class="kpi"><strong>Confidence</strong><br /><span id="confidence">0.0</span></div>
            </div>
          </div>
          <div class="panel">
            <h3>Controls</h3>
            <div>
              <button id="resume">Resume</button>
              <button class="secondary" id="pause">Pause</button>
              <button class="secondary" id="freeze">Freeze</button>
              <button class="warn" id="blank">Blank</button>
              <button class="danger" id="next">Next</button>
              <button class="danger" id="prev">Previous</button>
            </div>
            <h3>Service</h3>
            <div id="setlist"></div>
            <h3>State</h3>
            <pre id="state"></pre>
          </div>
        </div>
      </div>
      <script>
        const stateEl = document.getElementById('state');
        const modeEl = document.getElementById('mode');
        const songEl = document.getElementById('song');
        const positionEl = document.getElementById('position');
        const confidenceEl = document.getElementById('confidence');
        const displayEl = document.getElementById('display');
        const setlistEl = document.getElementById('setlist');

        function renderStatus(data) {
          const display = data.display || {};
          const recognition = data.recognition || {};
          const songId = display.song_id || '—';
          const position = display.position ? (display.position.section_index + ':' + display.position.line_index) : '—';
          modeEl.textContent = recognition.mode || 'searching';
          songEl.textContent = songId;
          positionEl.textContent = position;
          confidenceEl.textContent = Number(recognition.confidence || 0).toFixed(2);
          let text = '—';
          if (display.position && display.song_id) {
            text = display.song_id + ' / ' + position;
          }
          if (display.visible === false) {
            text = 'BLANK';
          }
          displayEl.textContent = text;
          stateEl.textContent = JSON.stringify(data, null, 2);
        }

        async function fetchJson(url, options) {
          const response = await fetch(url, options);
          if (!response.ok) {
            throw new Error('Request failed: ' + response.status);
          }
          return response.json();
        }

        async function refresh() {
          const status = await fetchJson('/status');
          renderStatus(status);
          const setlists = await fetchJson('/setlists');
          setlistEl.innerHTML = setlists.setlists.map((item) => '<div><strong>' + item.name + '</strong><ul>' + item.items.map((entry) => '<li>' + entry.label + '</li>').join('') + '</ul></div>').join('');
        }

        async function action(type) {
          await fetchJson('/actions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type }) });
          await refresh();
        }

        document.getElementById('resume').addEventListener('click', () => action('resume'));
        document.getElementById('pause').addEventListener('click', () => action('pause'));
        document.getElementById('freeze').addEventListener('click', () => action('freeze'));
        document.getElementById('blank').addEventListener('click', () => action('blank'));
        document.getElementById('next').addEventListener('click', () => action('skip_ahead'));
        document.getElementById('prev').addEventListener('click', () => action('repeat'));

        refresh();
        const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
        ws.onmessage = (event) => { renderStatus(JSON.parse(event.data)); };
      </script>
    </body>
    </html>
    """


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



class SongSectionPayload(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    kind: str = "verse"
    lines: list[str] = Field(min_length=1)

    def to_domain(self) -> SongSection:
        return SongSection(
            id=self.id,
            label=self.label,
            lines=tuple(self.lines),
            kind=SectionKind(self.kind),
        )


class SongPayload(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    sections: list[SongSectionPayload] = Field(min_length=1)

    def to_domain(self) -> Song:
        return Song(
            id=self.id,
            title=self.title,
            sections=tuple(section.to_domain() for section in self.sections),
        )


class SetListItemPayload(BaseModel):
    kind: str
    target_id: str = Field(min_length=1)
    label: str = Field(min_length=1)

    def to_domain(self) -> SetListItem:
        return SetListItem(kind=self.kind, target_id=self.target_id, label=self.label)


class SetListPayload(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    items: list[SetListItemPayload] = Field(min_length=1)

    def to_domain(self) -> SetList:
        return SetList(
            id=self.id,
            name=self.name,
            items=tuple(item.to_domain() for item in self.items),
        )


def _song_json(song: Song) -> dict[str, object]:
    return {
        "id": song.id,
        "title": song.title,
        "sections": [
            {
                "id": section.id,
                "label": section.label,
                "kind": section.kind.value,
                "lines": list(section.lines),
            }
            for section in song.sections
        ],
    }


def _setlist_json(setlist: SetList) -> dict[str, object]:
    return {
        "id": setlist.id,
        "name": setlist.name,
        "items": [
            {"kind": item.kind, "target_id": item.target_id, "label": item.label}
            for item in setlist.items
        ],
    }



class ServicePlanPayload(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    translation_id: str = "web"
    language: str = "en"
    items: list[dict[str, str]] = Field(default_factory=list)

    def to_domain(self) -> ServicePlan:
        normalized: list[object] = []
        for item in self.items:
            kind = item.get('kind')
            if kind == 'passage':
                normalized.append(
                    PassageItem(
                        reference=item.get('reference', ''),
                        label=item.get('label', ''),
                        translation_id=item.get('translation_id', self.translation_id),
                        language=item.get('language', self.language),
                    )
                )
            elif kind == 'song':
                normalized.append(SetListItem('song', item.get('target_id', ''), item.get('label', '')))
            else:
                normalized.append(SetListItem(item.get('kind', 'announcement'), item.get('target_id', ''), item.get('label', '')))
        return ServicePlan(
            id=self.id,
            name=self.name,
            translation_id=self.translation_id,
            language=self.language,
            items=tuple(normalized),
        )


def _service_plan_json(plan: ServicePlan) -> dict[str, object]:
    return {
        'id': plan.id,
        'name': plan.name,
        'translation_id': plan.translation_id,
        'language': plan.language,
        'items': [
            {'kind': 'song', 'target_id': item.target_id, 'label': item.label} if getattr(item, 'kind', None) == 'song' else {
                'kind': 'passage',
                'reference': item.reference,
                'label': item.label,
                'translation_id': item.translation_id,
                'language': item.language,
            }
            for item in plan.items
        ],
    }


def create_app(
    engine: AlignmentEngine,
    *,
    library: SongLibrary | None = None,
    setlists: dict[str, SetList] | None = None,
) -> FastAPI:
    """Create a local API bound to *engine*.

    Each application owns its WebSocket connection manager and engine
    reference, which keeps tests and multiple local services isolated.
    """

    api = FastAPI(title="VideoPsalm local API")
    api.state.engine = engine
    api.state.connections = _ConnectionManager()
    api.state.library = library or SongLibrary()
    api.state.setlists = setlists or {}
    api.state.service_plans = {}

    def get_engine(request: Request) -> AlignmentEngine:
        return request.app.state.engine

    def get_library(request: Request) -> SongLibrary:
        return request.app.state.library

    def get_setlists(request: Request) -> dict[str, SetList]:
        return request.app.state.setlists

    def get_service_plans(request: Request) -> dict[str, ServicePlan]:
        return request.app.state.service_plans

    @api.get("/")
    async def root() -> HTMLResponse:
        return HTMLResponse(_operator_console_html())

    @api.get("/status")
    async def status(
        current_engine: AlignmentEngine = Depends(get_engine),
    ) -> dict[str, object]:
        return serialize_state(current_engine)

    @api.get("/library")
    async def library_status(
        current_library: SongLibrary = Depends(get_library),
    ) -> dict[str, object]:
        return {"songs": [_song_json(song) for song in current_library.items()], "count": len(current_library.items())}

    @api.post("/library")
    async def add_song_to_library(
        payload: SongPayload,
        current_library: SongLibrary = Depends(get_library),
    ) -> dict[str, object]:
        try:
            current_library.add(payload.to_domain())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"song": _song_json(current_library.get(payload.id))}

    @api.get("/setlists")
    async def list_setlists(
        current_setlists: dict[str, SetList] = Depends(get_setlists),
    ) -> dict[str, object]:
        return {"setlists": [_setlist_json(value) for value in current_setlists.values()] }

    @api.get("/service-plans")
    async def list_service_plans(
        current_service_plans: dict[str, ServicePlan] = Depends(get_service_plans),
    ) -> dict[str, object]:
        return {"service_plans": [_service_plan_json(value) for value in current_service_plans.values()] }

    @api.post("/service-plans")
    async def create_service_plan(
        payload: ServicePlanPayload,
        current_service_plans: dict[str, ServicePlan] = Depends(get_service_plans),
    ) -> dict[str, object]:
        try:
            plan = payload.to_domain()
            current_service_plans[plan.id] = plan
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"service_plan": _service_plan_json(current_service_plans[payload.id])}

    @api.post("/setlists")
    async def create_setlist(
        payload: SetListPayload,
        current_setlists: dict[str, SetList] = Depends(get_setlists),
    ) -> dict[str, object]:
        try:
            setlist = payload.to_domain()
            current_setlists[setlist.id] = setlist
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"setlist": _setlist_json(current_setlists[payload.id])}

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

    library = SongLibrary()
    song = Song(
        id="demo",
        title="Demo",
        sections=(
            SongSection("verse", "Verse", ("First line", "Second line"), SectionKind.VERSE),
        ),
    )
    library.add(song)
    setlists = {
        "sunday": SetList(
            id="sunday",
            name="Sunday service",
            items=(
                SetListItem("song", "demo", "Demo"),
                SetListItem("passage", "john-3-16", "John 3:16"),
            ),
        )
    }
    return create_app(AlignmentEngine(song), library=library, setlists=setlists)
