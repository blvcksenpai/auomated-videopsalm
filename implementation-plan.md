# Automated VideoPsalm Implementation Plan

## 1. Delivery principles

- Treat the display as a safety-critical user experience: uncertain recognition holds the last confirmed state.
- Keep manual control authoritative over all automated events.
- Separate speech recognition, singing alignment, candidate selection, and display rendering behind stable interfaces.
- Measure speech and singing independently using labeled audio events.
- Keep licensing, privacy, and retention behavior configurable from the beginning.

## 2. Initial system boundaries

### Inputs

- Direct mixer or vocal-channel audio stream.
- Optional service set-list containing songs, passages, and sermon outline items.
- Licensed Bible text and structured, licensed song lyrics.
- Operator commands.

### Processing pipeline

1. Capture and normalize audio.
2. Detect speech, singing, music, silence, and input health.
3. Produce streaming ASR partials and singing/music features.
4. Detect Bible references and generate song candidates.
5. Align live input to the selected reference.
6. Apply confidence thresholds, hysteresis, bounded search, and operator-priority rules.
7. Emit typed display events.
8. Render the congregation display and operator console.
9. Record non-sensitive transition and diagnostic metadata.

## 3. Core components

### Audio gateway

- Accept the supported mixer input format.
- Provide buffering, level monitoring, dropout detection, and reconnect handling.
- Expose timestamps so latency can be measured end to end.

### Recognition adapters

- Define provider-neutral streaming ASR and music/singing feature interfaces.
- Support partial results, confidence, timestamps, errors, and cancellation.
- Make cloud and local providers replaceable without changing alignment logic.

### Reference and content services

- Store Bible books, chapters, verses, translation metadata, and license metadata.
- Store songs as ordered sections and display segments.
- Validate imported content and prevent unlicensed content from being activated.

### Candidate and alignment engine

- Maintain candidates from the active set-list, then the configured library.
- Use fuzzy text matching plus speech/singing activity and acoustic evidence.
- Track reference position and repeat count.
- Implement `searching`, `tracking`, `uncertain`, `manual`, `paused`, `disconnected`, and `reconnecting`.
- Never advance because of elapsed time.

### Control and display layer

- Define typed events for show, advance, hold, blank, freeze, manual select, and resume.
- Enforce operator priority centrally, not separately in each UI.
- Render congregation and operator views from the same confirmed display state.
- Show candidate, position, confidence, mode, latency, and connection health.

## 4. Milestones

### M0 — Feasibility spike

- Build the labeled audio corpus and replay harness.
- Compare ASR and singing-alignment approaches.
- Implement a basic verse parser and lyric matcher.
- Produce baseline latency and accuracy reports.

### M1 — Domain and content foundation

- Implement Bible and song schemas.
- Add translation/licensing metadata and import validation.
- Add set-list and service configuration.
- Create deterministic fixtures for references, songs, repeats, skips, and pauses.

### M2 — Recognition and alignment prototype

- Implement audio gateway and streaming provider adapters.
- Build mode classification and candidate ranking.
- Implement the alignment state machine, hysteresis, confidence thresholds, and bounded recovery.
- Replay labeled audio and emit traceable alignment events.

### M3 — Display and operator console

- Implement congregation renderer and themes.
- Implement operator controls and explicit automation/manual state.
- Add confidence, latency, transcript/reference diff, and reconnect indicators.
- Verify manual actions cannot be overwritten by recognition events.

### M4 — Integrated MVP validation

- Run unit, integration, replay, load, and failure-mode tests.
- Test with live sanctuary recordings and direct mixer feeds.
- Validate acceptance criteria, licensing, privacy, and retention behavior.
- Package deployment and write volunteer setup/runbook documentation.

## 5. Testing strategy

- **Unit tests:** reference parsing, fuzzy matching, confidence transitions, hysteresis, repeat/skip handling, and operator-priority rules.
- **Replay tests:** deterministic processing of labeled speech and singing recordings with measured line accuracy and latency.
- **Integration tests:** audio dropout, provider errors, reconnects, delayed partials, mode changes, and display event ordering.
- **UI tests:** freeze, blank, manual selection, previous/next, resume, and degraded-state visibility.
- **Sanctuary trials:** different singers, keys, tempos, microphones, instruments, pauses, ad-libs, and room acoustics.
- **Security/privacy tests:** transport encryption, access control, retention defaults, and licensing restrictions.

## 6. Operational requirements

- Provide health checks for audio input, recognition providers, content availability, and display output.
- Keep the last confirmed display available during transient failures.
- Log automatic transitions with timestamp, source signals, candidate, position, confidence, and reason.
- Avoid storing live audio or transcripts by default; make any retention explicit and configurable.
- Provide a reset/recovery procedure that does not require database deletion or service restart during worship.

## 7. Principal risks and mitigations

| Risk | Mitigation |
|---|---|
| Singing ASR is unreliable | Combine ASR with singing/music cues; benchmark specialized alignment; require operator confirmation. |
| False lyric or verse jumps | Use bounded search, hysteresis, confidence thresholds, and hold-on-uncertainty behavior. |
| Latency feels distracting | Measure p50/p95 separately; optimize buffering and partial-result handling without timer advances. |
| Room audio is too noisy | Support direct mixer feeds first; evaluate preprocessing and room-mic operation separately. |
| Licensing blocks deployment | Track content licenses and activation rules as first-class data. |
| Cloud outage interrupts recognition | Keep display/control local and provide reconnect status plus manual fallback. |
