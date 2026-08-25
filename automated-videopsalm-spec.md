# Automated VideoPsalm — Product & Technical Specification

**Version:** 0.2 (Draft)
**Prepared:** August 25, 2026
**Status:** Revised for technical review

---

## 1. Overview

Automated VideoPsalm is a live worship-display system for churches. It listens to what is happening on stage — singing or speaking — and automatically drives the congregation-facing screen: showing the right song lyrics or the right Bible verse, at the right line, at the moment it's actually said or sung.

The defining constraint: **the display must be paced by the live audio, never by a clock.** No fixed-duration timers, no "advance every N seconds" logic. If the singer holds a note, the display holds. If the preacher pauses, the display waits. If someone skips a verse or repeats a chorus, the display follows.

### 1.1 Problem statement
Traditional setups need a human operator clicking through slides in sync with the service. Mistakes (wrong slide, late advance, missed verse) are common and distracting. This app removes the manual-clicking bottleneck while staying accurate to what's actually being said/sung.

### 1.2 Goals
- Automatically detect when a spoken Bible reference occurs and display the correct verse.
- Automatically detect which song is being sung and display its lyrics.
- Advance the displayed line/verse in sync with the live singer or speaker — driven by recognition of actual speech/singing progress, not elapsed time.
- Reduce or eliminate the need for a manual slide operator, while still allowing manual override.
- Operate safely when recognition is uncertain, delayed, unavailable, or disconnected.

### 1.3 Non-goals (for v1)
- Fully automated multi-camera video production.
- Real-time translation/subtitling into other languages (could be a future extension).
- Music transcription or chord-chart generation.

---

## 2. Core Functional Requirements

| ID | Requirement | Notes |
|----|-------------|-------|
| FR-1 | **Verse reference detection** — detect a spoken Bible reference (e.g. "John 3:16", "Romans chapter 8 verse 1") in near-real time from the live mic feed. | Must handle spoken variations: "chapter," "verse," ranges ("verses 1 through 4"), abbreviated book names, multiple translations. |
| FR-2 | **Verse display** | Pull the correct verse text from a Bible database (configurable translation/language) and render it on the congregation screen. |
| FR-3 | **Song detection** — identify which song is currently being sung, from a known song library, using the live audio/mic feed. | Must work despite instruments, key transposition, tempo variation, and a live singer's voice (not studio-clean audio). |
| FR-4 | **Song lyric sync** — display the correct lyric line, advancing as the singer actually reaches each line/section. | No fixed timing. Must handle repeats (chorus x2/x3), skipped verses, bridges, ad-libs. |
| FR-5 | **Speech-paced advance (non-song content)** — for preaching, prayer, announcements, or any spoken (non-sung) content tied to a script/outline/verse sequence, advance the display in step with the speaker's actual pace. | No fixed timing here either. Must tolerate pauses, filler words, tangents, paraphrasing. |
| FR-6 | **Manual override** | Operator can pause auto-mode, jump to any verse/line, freeze the screen, or blank it, at any time without fighting the automatic system. |
| FR-7 | **Confidence-based fallback** | If the system is not confident what's being said/sung, it should hold the last correct state rather than guess wrong and flash an incorrect line. |
| FR-8 | **Multi-translation / multi-language Bible support** | Displayed translation should be configurable per service or per verse. |
| FR-9 | **Song library management** | Add/edit/import songs (lyrics, structure: verse/chorus/bridge, optional audio fingerprint reference). |
| FR-10 | **Service/set-list mode** | Pre-load an order of service (songs + sermon outline + expected passages) so detection has a shortlist to match against, improving accuracy and speed — while still supporting off-script moments. |
| FR-11 | **Operator priority** | Manual actions always take precedence over automation. Auto-mode must not overwrite a freeze, blank, manual selection, or paused state until the operator explicitly resumes automation. |
| FR-12 | **Recognition state and recovery** | Expose recognition mode, candidate, position, confidence, latency, and degraded/reconnecting status to the operator console; recover by holding the last confirmed display rather than guessing. |

---

## 3. The "No Timer" Requirement — What It Actually Means

This is the core technical differentiator, so it's worth spelling out precisely.

**Forbidden approach:** "Show line 1 for 4 seconds, then line 2 for 4 seconds…" — this breaks the moment a singer holds a note, a preacher pauses for effect, or the pace varies at all (which live speech and singing always do).

**Required approach:** The system continuously listens, transcribes/recognizes in real time, and **aligns what it hears to a known reference text** (the song's lyrics or the sermon's expected passage/outline). The display advances only when the system detects, from the actual audio, that the speaker/singer has reached the next segment.

This requires:
1. **Streaming recognition** — audio is processed continuously and incrementally, not in fixed batches.
2. **Reference alignment** — the recognized words are matched against a known reference (lyrics, verse text, or outline) to determine *where in the reference* the live audio currently is. This is conceptually similar to forced alignment / karaoke-style lyric sync, but running live rather than on a pre-recorded track.
3. **Position tracking with hysteresis** — the system tracks a "current position" in the reference and only moves forward (or, rarely, backward) when new recognized audio gives sufficient confidence, avoiding flicker from noisy/partial matches.
4. **Graceful handling of divergence** — if the live audio stops matching the reference well (ad-lib, skipped section, off-script moment), the system should either widen its search window across the known set-list or hold the last confident position, rather than jumping erratically.
5. **Multi-signal state machine** — position decisions combine partial ASR tokens, singing/music cues, lyric/reference candidates, confidence, and operator actions. No single transcript fragment or acoustic cue may independently force an unsafe display jump.

### 3.1 Recognition states and fallback behavior

The alignment engine must expose at least these states: `searching`, `tracking`, `uncertain`, `manual`, `paused`, `disconnected`, and `reconnecting`.

- In `tracking`, advance only after the next configured display segment has sufficient cumulative evidence and hysteresis.
- In `uncertain`, hold the last confirmed segment; do not display a low-confidence guess. Continue searching within the current candidate and then the active set-list before widening to the full library.
- During silence, pauses, false starts, audio dropouts, or processing latency spikes, hold the display. There are no timeout-driven advances or automatic end-of-song transitions.
- Manual freeze, blank, pause, and selection take priority over all automated events. Automation resumes only after an explicit operator action.
- When confidence recovers, require a stable match before resuming automatic advancement; log the confidence and reason for each automatic transition.

---

## 4. System Architecture (proposed)

```
[Stage mic / mixer line-out]
        │
        ▼
  Audio Capture ──► Noise/Instrument Separation (for song mode)
        │
        ▼
  Streaming Speech Recognition (ASR)
        │
        ▼
 ┌───────────────────────────────┐
 │      Mode Classifier          │  → is this singing or speaking?
 └───────────────────────────────┘
        │                    │
        ▼                    ▼
  Song Path            Speech/Verse Path
  - Song ID match      - Verse reference NER
    (fingerprint or      (detect "Book Ch:Vs" patterns)
    lyric match)        - Passage alignment (if a
  - Lyric alignment       sermon outline/passage
    engine (live)         is pre-loaded)
        │                    │
        ▼                    ▼
   Position Tracker (current line / verse, confidence score)
        │
        ▼
   Display Renderer (congregation screen output)
        │
        ▼
   Operator Console (override, monitor confidence, manual jump)
```

### 4.1 Key modules
- **Audio capture** — dedicated input from the church sound board (not room mic), to minimize noise and get the clean vocal channel where possible.
- **Mode classifier** — determines whether current audio is song or speech using music activity, singing-voice, and speech-activity signals; it must support an `uncertain` mode.
- **ASR engine** — streaming speech-to-text, tuned for low latency and partial results. ASR is one alignment signal and is not assumed to transcribe sustained or ornamented singing accurately.
- **Song identification** — either audio fingerprinting (Shazam-style, if using reference recordings) or lyric-matching against the live ASR transcript (more robust for live worship where the performance won't match a studio track exactly). Lyric-matching against a known song library is likely the more reliable approach for *live* worship.
- **Verse reference NER (Named Entity Recognition)** — a language model or rule-based parser trained to catch spoken Bible references in natural speech, including partial/implied references ("verse 16" after "John 3" was said earlier).
- **Alignment/position engine** — the heart of the "no timer" requirement; combines ASR, acoustic/music cues, reference candidates, and hysteresis in a state machine that keeps track of where the live audio is within the known reference text and emits advance events.
- **Renderer** — the actual on-screen display, plus a lower-third or full-screen mode, theming, transitions.
- **Operator console** — human-in-the-loop monitor and override, not required for normal operation but always available.

---

## 5. Detection Details

### 5.1 Verse reference detection
- Parse spoken patterns: `[Book] [Chapter]:[Verse]`, `[Book] Chapter [N] Verse [N]`, ranges, "the following verses," implied continuations ("...verse 17, 18...").
- Handle common spoken book-name variants and abbreviations, and mispronunciations.
- Disambiguate books with similar names (e.g. 1/2 Samuel, 1/2/3 John) using context.
- Confidence threshold before triggering a display change, to avoid false positives from casual mentions ("like it says in John...").

### 5.2 Song detection
- Primary: combine live ASR transcript fragments with singing/music activity and match against a lyrics database (fuzzy match tolerant of missed words, instrument bleed, sustained notes, ornamentation, and ad-libbed repeats). Standard speech ASR alone is insufficient for singing alignment.
- Secondary/optional: audio fingerprinting against reference recordings, useful for instrumental intros before lyrics start.
- Should narrow candidates fast using the pre-loaded set-list if available (FR-10), falling back to full-library search if not.

### 5.3 Pace-following (songs)
- Track current line/section (verse, pre-chorus, chorus, bridge) and repeat count.
- Must detect repeats of the same chorus without getting "stuck" thinking it's already shown that line.
- Should tolerate ornamentation, ad-libs, and vocal runs that don't match lyrics word-for-word.

### 5.4 Pace-following (speech/preaching)
- When a passage or outline is pre-loaded, align live speech against it the same way as song lyrics.
- When nothing is pre-loaded (free-form preaching), the system's job is narrower: just catch verse references as they're spoken (FR-1/FR-2) rather than trying to track an outline that doesn't exist yet.

---

## 6. Edge Cases to Handle

- Singer/speaker skips ahead or back.
- Chorus/refrain repeated an unpredictable number of times.
- Preacher paraphrases a verse instead of quoting it, but still references it.
- Multiple mics / multiple speakers (call-and-response, duet, panel).
- Background instruments bleeding into the vocal mic.
- Silence or long pauses (should not cause false "end of song" or timeout-driven jumps).
- Key change or tempo change mid-song.
- False starts (song starts, stops, restarts).
- No pre-loaded set-list / fully improvised service.
- Network or processing latency spikes — system should degrade gracefully (hold last state) rather than glitch the screen.
- Recognition remains uncertain for an extended period — show the operator a clear intervention prompt without changing the congregation display.

---

## 7. Data Requirements

| Data set | Purpose | Notes |
|---|---|---|
| Bible text database | Verse lookup/display | Multiple translations and languages; needs correct licensing for each translation used. |
| Song lyrics library | Lyric display + matching | Structured by section (verse/chorus/bridge); needs licensing (CCLI or equivalent) for public display. |
| Optional song audio references | Fingerprinting | Only needed if fingerprinting approach is used. |
| Service/set-list templates | Improve detection accuracy | Song order, expected sermon passages, per-service config. |

---

## 8. UI/UX

- **Congregation display**: clean, theme-able, large-type output — verse text + reference, or song lyric lines, with smooth (not jarring) transitions.
- **Operator console** (separate view, e.g. on a laptop/tablet backstage):
  - Live status: current detected mode (song/speech), current song or passage, confidence indicator.
  - One-tap override: freeze, blank, jump to next/previous line, manual song/verse select.
  - Visual diff between "what the system thinks is being said" and "what's on screen," so the operator can catch drift early.
- **Config/admin panel**: manage song library, Bible translations, set-lists, themes.

---

## 9. Non-Functional Requirements

- **Latency**: sub-second from spoken/sung word to display update is the target; anything over ~1.5s will feel laggy to a congregation.
- **Latency measurement**: report median and p95 end-to-display latency separately for speech and singing, measured from labeled audio events. The initial target is median <=1.0s and p95 <=1.5s; the display must never advance solely to meet a latency target.
- **Reliability**: must not crash mid-service; auto-reconnect on audio dropout.
- **Offline capability**: local network operation should not depend on internet if possible (at least for playback/display; cloud ASR may require connectivity — a local/on-device ASR fallback is worth evaluating for reliability).
- **Accuracy under noise**: must remain usable with typical sanctuary acoustics, not just studio conditions.
- **Ease of setup**: sound-booth volunteers, not engineers, will operate this day to day.
- **Privacy and security**: clearly indicate when audio or transcripts leave the venue; encrypt transport and stored data; make retention configurable with a no-retention default for live audio and transcripts unless explicitly enabled.
- **Operator safety**: manual state and automation state must be visually distinct, and every automatic display transition must be auditable with timestamp, source signal, candidate, and confidence.

---

## 10. Suggested Technical Approaches (for evaluation, not final decisions)

- **Streaming ASR**: real-time speech-to-text engines capable of low-latency partial transcripts (cloud-based or on-device, evaluate both for latency/reliability/cost/licensing). Benchmark speech and singing separately.
- **Text alignment**: techniques from forced alignment / karaoke-sync systems, adapted to run incrementally on a live stream rather than a fixed recording.
- **Song/verse matching**: fuzzy string matching (edit distance / phonetic matching) tolerant of ASR errors, rather than exact string matching.
- **Audio routing**: direct feed from the sound board's vocal channel(s) where possible, rather than relying on a room mic.
- **Decision engine**: an explicit state machine with confidence thresholds, hysteresis, bounded search windows, and operator-priority rules; avoid timer-based advancement.

These should be validated with prototyping/spikes before committing — actual model/library choice depends on latency testing in a real sanctuary environment.

---

## 11. MVP Scope vs. Later Phases

**MVP (Phase 1)**
- Verse reference detection + display for one language and one licensed translation (FR-1, FR-2).
- Song detection + lyric-paced display for a curated, licensed song library and pre-loaded set-list (FR-3, FR-4, FR-10).
- Clean mixer/vocal input as the supported audio source; room-mic operation is an evaluation case, not an MVP guarantee.
- Manual override console with operator-priority state handling (FR-6, FR-7, FR-11, FR-12).
- Conservative fallback: hold the last confirmed state whenever confidence is insufficient.
- Manual confirmation of the detected song before automatic lyric advancement.

**Phase 2**
- Pace-following for pre-loaded sermon outlines (FR-5, FR-10 full version).
- Multi-translation/multi-language support.
- Confidence visualization and drift-correction UI for operators.

**Phase 3 (future)**
- Multi-mic/multi-speaker handling.
- Offline/on-device recognition option.
- Analytics (which verses/songs used, service length trends).

---

## 12. Open Questions for Stakeholders

- Which Bible translations and licensing arrangements are needed?
- Is there an existing song library with licensing (e.g. CCLI) already in place, or does that need to be built?
- What's the sound board setup at target churches — is a clean vocal feed realistically available, or will this mostly run off a room mic?
- Is cloud-based processing acceptable, or is fully offline/on-prem a hard requirement (data privacy, internet reliability in the venue)?
- Single-church deployment or multi-tenant product for many churches?

## 12.1 MVP acceptance criteria

Before expanding beyond the MVP, validate the system with labeled recordings and live sanctuary trials:

- Verse references: measure precision and recall for supported books, spoken variants, ranges, and implied continuations; false positives must be reviewed separately from missed references.
- Song identification: measure top-1 and top-3 accuracy using live singers, transposed keys, tempo changes, instrument bleed, and set-list/no-set-list conditions.
- Alignment: measure line/segment accuracy, median and p95 latency, and drift during held notes, pauses, repeats, skips, bridges, ad-libs, and false starts.
- Safety: verify that uncertainty, silence, audio loss, reconnects, and latency spikes hold the last confirmed display and never trigger a timer-based transition.
- Operator control: verify that freeze, blank, manual selection, previous/next, and resume actions cannot be overwritten by automated events.
- Licensing and privacy: verify that only configured/licensed Bible and lyric content is displayed and that retention/network behavior matches service configuration.

---

## 13. Glossary

- **ASR** — Automatic Speech Recognition (speech-to-text).
- **Forced alignment** — technique for matching audio to a known reference text, timestamp by timestamp.
- **Fingerprinting** — identifying audio by matching an acoustic "fingerprint" against a reference database (how apps like Shazam work).
- **Set-list** — the planned order of songs/elements for a service.
- **CCLI** — Christian Copyright Licensing International, common licensing body for displaying song lyrics in churches.
