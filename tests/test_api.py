import pytest

pytest.importorskip("fastapi")

try:
    from fastapi.testclient import TestClient
except (ImportError, RuntimeError):
    pytest.skip("FastAPI TestClient transport is unavailable", allow_module_level=True)

from videopsalm import (
    AlignmentConfig,
    AlignmentEngine,
    SectionKind,
    Song,
    SongSection,
)
from videopsalm.api import create_app


@pytest.fixture
def client() -> TestClient:
    song = Song(
        "demo",
        "Demo",
        (SongSection("verse", "Verse", ("one", "two"), SectionKind.VERSE),),
    )
    engine = AlignmentEngine(song, AlignmentConfig(hysteresis=2))
    return TestClient(create_app(engine))


def evidence(line_index: int = 0) -> dict[str, object]:
    return {
        "song_id": "demo",
        "position": {"section_index": 0, "line_index": line_index},
        "confidence": 0.95,
    }


def test_status_serializes_position_and_recognition(client: TestClient) -> None:
    response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {
        "display": {
            "song_id": None,
            "position": None,
            "visible": True,
            "frozen": False,
            "manual": False,
            "paused": False,
            "repeat_count": 0,
        },
        "recognition": {
            "mode": "searching",
            "confidence": 0.0,
            "candidate_song_id": None,
            "pending_position": None,
            "reason": "",
        },
    }


def test_evidence_endpoint_preserves_hysteresis(client: TestClient) -> None:
    first = client.post("/evidence", json=evidence())
    second = client.post("/evidence", json=evidence())

    assert first.status_code == second.status_code == 200
    assert first.json()["display"]["position"] is None
    assert first.json()["recognition"]["mode"] == "uncertain"
    assert second.json()["display"]["position"] == {
        "section_index": 0,
        "line_index": 0,
    }
    assert second.json()["recognition"]["mode"] == "tracking"


def test_manual_freeze_has_priority_over_evidence(client: TestClient) -> None:
    client.post("/evidence", json=evidence())
    client.post("/evidence", json=evidence())
    frozen = client.post("/actions", json={"type": "freeze"})
    updated = client.post("/evidence", json=evidence(1))

    assert frozen.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["display"]["position"] == {
        "section_index": 0,
        "line_index": 0,
    }
    assert updated.json()["display"]["frozen"] is True


def test_invalid_action_payload_is_rejected(client: TestClient) -> None:
    response = client.post("/actions", json={"type": "manual_select"})

    assert response.status_code == 422


def test_websocket_receives_state_updates(client: TestClient) -> None:
    with client.websocket_connect("/ws") as websocket:
        initial = websocket.receive_json()
        assert initial["recognition"]["mode"] == "searching"

        client.post("/actions", json={"type": "freeze"})
        update = websocket.receive_json()

    assert update["display"]["frozen"] is True
    assert update["recognition"]["mode"] == "manual"
