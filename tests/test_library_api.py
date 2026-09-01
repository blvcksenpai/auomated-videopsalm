from fastapi.testclient import TestClient

from videopsalm import (
    AlignmentConfig,
    AlignmentEngine,
    SectionKind,
    Song,
    SongLibrary,
    SongSection,
)
from videopsalm.api import create_app


def make_app():
    library = SongLibrary()
    library.add(
        Song(
            "demo",
            "Demo",
            (SongSection("verse", "Verse", ("one", "two"), SectionKind.VERSE),),
        )
    )
    return create_app(AlignmentEngine(Song("demo", "Demo", (SongSection("verse", "Verse", ("one", "two"), SectionKind.VERSE),)), AlignmentConfig()), library=library, setlists={})


def test_library_endpoint_lists_curated_songs():
    app = make_app()
    with TestClient(app) as client:
        response = client.get('/library')
        assert response.status_code == 200
        assert response.json()['count'] == 1
        assert response.json()['songs'][0]['id'] == 'demo'


def test_setlist_endpoint_accepts_service_order():
    app = make_app()
    payload = {
        'id': 'sunday',
        'name': 'Sunday service',
        'items': [
            {'kind': 'song', 'target_id': 'demo', 'label': 'Demo'},
            {'kind': 'passage', 'target_id': 'john-3-16', 'label': 'John 3:16'},
        ],
    }
    with TestClient(app) as client:
        response = client.post('/setlists', json=payload)
        assert response.status_code == 200
        assert response.json()['setlist']['id'] == 'sunday'
        assert response.json()['setlist']['items'][0]['kind'] == 'song'
