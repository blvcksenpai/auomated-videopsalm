# Automated VideoPsalm

The initial backend slice contains typed song/display/recognition models and a
deterministic lyric alignment state machine with conservative operator controls.

## Tests

From the repository root:

```bash
python3.12 -m pip install -e '.[test]'
python3.12 -m pytest
```

## No-timer rule

Automatic display changes are driven only by recognized reference evidence.
There is no elapsed-time or background timer that advances lyrics; uncertainty,
silence, and pauses hold the last confirmed display. Operator freeze, blank,
pause, and manual selection always take priority until `resume`.
