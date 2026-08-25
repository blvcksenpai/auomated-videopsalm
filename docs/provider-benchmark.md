# Recognition Provider Benchmark

This benchmark is the M0 feasibility gate. It must compare speech and singing
separately using the same labeled recordings and direct mixer input where
available. Do not select a production provider based on transcript quality
alone.

## Test corpus

Create consented, locally stored recordings with event labels for:

- Spoken Bible references, including chapter/verse variants, ranges,
  abbreviations, and implied continuations.
- Singing with different voices, keys, tempos, held notes, melisma, repeats,
  skipped sections, bridges, and ad-libs.
- Speech and singing over instruments, silence, pauses, false starts, and
  simulated audio dropouts.

Record the source type, sample rate, language, translation, song/reference,
and exact event boundaries. Keep raw audio and transcripts out of telemetry by
default.

## Candidate configurations

Evaluate at least:

1. Local streaming ASR using `faster-whisper` or an equivalent model.
2. One hosted streaming ASR provider through `StreamingSpeechProvider`.
3. A local audio-feature provider for speech/singing/music activity.
4. A combined ASR plus audio-feature alignment pipeline.

The hosted provider is optional when privacy or network constraints prohibit
it, but the adapter boundary must still be exercised with a test double.

## Measurements

For each configuration, report:

- Verse-reference precision, recall, and false-trigger rate.
- Song identification top-1 and top-3 accuracy, with and without a set-list.
- Display segment accuracy and drift for singing and speech separately.
- Median and p95 end-to-display latency from labeled event boundary.
- Recovery time after dropout and behavior during uncertainty.
- CPU, memory, GPU, bandwidth, and estimated per-service cost.

## Decision rules

- No configuration may advance the display on low-confidence or missing
  evidence.
- A provider is not acceptable if its p95 latency exceeds 1.5 seconds for the
  target environment or if it causes unsafe false jumps.
- Singing alignment must be evaluated with live performances; studio-only
  results are insufficient.
- Select the simplest configuration that meets the acceptance criteria while
  preserving a local fallback and provider replacement path.

## Reproducibility

The replay harness should consume a manifest of audio files and labels, emit
machine-readable metrics, and retain per-event traces containing timestamps,
candidate, position, confidence, and decision reason. Never use fixed timers
to make a replay pass; replay timing must derive from audio timestamps.
