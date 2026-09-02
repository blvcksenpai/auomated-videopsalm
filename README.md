# Automated VideoPsalm

The initial backend slice contains typed song/display/recognition models and a
deterministic lyric alignment state machine with conservative operator controls.

## Tests

From the repository root:

```bash
python3.12 -m pip install -e '.[test]'
python3.12 -m pytest
```

## Local API

Install the optional API dependencies and run the local demo API on loopback:

```bash
.venv/bin/pip install -e '.[api]'
.venv/bin/uvicorn videopsalm.api:demo_app --factory --host 127.0.0.1 --port 8000
```

Applications should use `videopsalm.api.create_app(engine)` to inject their
own `AlignmentEngine` instance. The API exposes `/status`, `/actions`, and
`/evidence`, with live JSON snapshots on `/ws`. Service-planning metadata is
available via `/library` and `/setlists` so the local app can narrow
candidate songs and pre-load an order of service.

## No-timer rule

Automatic display changes are driven only by recognized reference evidence.
There is no elapsed-time or background timer that advances lyrics; uncertainty,
silence, and pauses hold the last confirmed display. Operator freeze, blank,
pause, and manual selection always take priority until `resume`.

## Data layer

The project includes a local SQLite data layer for Bible text and song library content. You can import a thiagobodruk-style JSON payload for Bible verses or a minimal OpenLyrics XML document for worship songs.

- Bible source candidates: https://github.com/thiagobodruk/bible (local import) and https://bible-api.com/ (prototype lookup).
- Song source candidates: https://openlyrics.org/ and the OpenLyrics XML format for local, legally cleared worship songs.
- Licensing: protect public display rights for any lyrics or Bible translations used in worship; the code supports licensing metadata and local content controls.

## Real sanctuary corpus

Use the private corpus workflow in `data/corpus/README.md` for consented recordings and timestamped labels. The repository includes only a manifest example, never raw audio. Validate a local manifest with `validate_manifest` before replay or benchmark work.
