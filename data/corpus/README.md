# Real Sanctuary Audio Corpus

This directory is intentionally empty of audio. Add only consented recordings
from a church or test session, and keep the files local/private. Do not commit
raw audio, transcripts containing personal information, or copyrighted service
recordings to the repository.

## Layout

```text
data/corpus/
  manifest.json
  audio/
    service-001.wav
```

`manifest.json` records anonymized IDs, audio metadata, dataset split, consent
reference, and timestamped labels. Audio paths are relative to the corpus root.

## Collection checklist

1. Obtain written consent covering recording, transcription, model evaluation,
   local storage, retention, and deletion.
2. Prefer a direct mixer/vocal feed; also capture room-mic examples as a
   separately labeled source type.
3. Label Bible references, song starts, lyric segments, repeats, skips, pauses,
   dropouts, and speech/singing mode changes using the event types in the
   manifest schema.
4. Remove names and unrelated conversation from labels; use anonymized IDs.
5. Keep train, validation, and test services separated by service/session, not
   by randomly splitting adjacent clips.
6. Validate before replay:

```bash
.venv/bin/python -c "from videopsalm import validate_manifest; print(validate_manifest('data/corpus/manifest.json', audio_root='data/corpus'))"
```

The validator must report `[]` before a corpus is used for benchmark results.
