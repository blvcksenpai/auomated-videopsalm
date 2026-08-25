# Automated VideoPsalm Feature Roadmap

## Product direction

Build a reliable live-display assistant that follows recognized speech and singing, never a clock. Automation should be conservative: uncertainty holds the last confirmed display and gives the operator control.

## Phase 0 — Discovery and feasibility

**Objective:** Prove that the core recognition and alignment approach works in real sanctuary conditions.

- Collect representative mixer feeds and labeled service recordings.
- Benchmark streaming speech ASR and singing/lyric alignment options.
- Prototype verse-reference parsing and fuzzy lyric matching.
- Measure latency, accuracy, drift, and behavior during pauses, repeats, skips, and ad-libs.
- Confirm Bible and lyric licensing requirements.

**Exit criteria:** A documented model/library choice, a test corpus, baseline metrics, and a validated audio-input setup.

## Phase 1 — MVP: assisted live display

**Objective:** Deliver a safe, usable system for one church and a constrained configuration.

- One language and one licensed Bible translation.
- Verse-reference detection and verse display.
- Curated, licensed song library with structured sections.
- Pre-loaded set-list candidate narrowing.
- Song detection with explicit operator confirmation.
- Audio-paced lyric advancement using multi-signal alignment.
- Recognition states: tracking, uncertain, paused, manual, disconnected, reconnecting.
- Operator console: freeze, blank, pause, manual selection, previous/next, resume.
- Congregation display with configurable line grouping and theme.
- Conservative fallback and transition audit log.
- Clean mixer/vocal input as the supported source.

**Exit criteria:** MVP acceptance criteria in the specification pass on labeled recordings and live sanctuary trials.

## Phase 2 — Service workflow expansion

- Pre-loaded sermon-outline alignment.
- Multiple Bible translations and languages.
- Confidence visualization and drift-correction workflows.
- Song import/edit tools and set-list templates.
- Local/on-device recognition fallback.
- Better room-mic robustness and configurable audio preprocessing.

## Phase 3 — Scale and advanced operations

- Multi-mic and multi-speaker handling.
- Call-and-response and duet support.
- Multi-tenant church administration.
- Service analytics and alignment-quality reports.
- Hardware/input health monitoring.
- Advanced offline operation and deployment packaging.

## Deferred or explicitly out of scope

- Fully automated multi-camera production.
- Real-time translation or subtitling.
- Music transcription and chord-chart generation.
- Timer-based slide advancement.
