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
`/evidence`, with live JSON snapshots on `/ws`.

## No-timer rule

Automatic display changes are driven only by recognized reference evidence.
There is no elapsed-time or background timer that advances lyrics; uncertainty,
silence, and pauses hold the last confirmed display. Operator freeze, blank,
pause, and manual selection always take priority until `resume`.
