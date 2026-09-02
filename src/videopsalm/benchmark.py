"""Provider comparison metrics over labeled sanctuary-corpus manifests."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from .corpus import AudioRecording, CorpusLabel, CorpusManifest


@dataclass(frozen=True, slots=True)
class ProviderPrediction:
    recording_id: str
    start_seconds: float
    end_seconds: float
    event_type: str
    confidence: float
    reference: str | None = None
    song_id: str | None = None
    section_index: int | None = None
    line_index: int | None = None
    candidate_song_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProviderPrediction":
        return cls(
            recording_id=str(value["recording_id"]),
            start_seconds=float(value["start_seconds"]),
            end_seconds=float(value["end_seconds"]),
            event_type=str(value["event_type"]),
            confidence=float(value.get("confidence", 0.0)),
            reference=value.get("reference"),
            song_id=value.get("song_id"),
            section_index=value.get("section_index"),
            line_index=value.get("line_index"),
            candidate_song_ids=tuple(value.get("candidate_song_ids", [])),
        )


def load_predictions(path: str | Path) -> tuple[ProviderPrediction, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("predictions", [])
    return tuple(ProviderPrediction.from_dict(item) for item in rows)


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _is_match(label: CorpusLabel, prediction: ProviderPrediction) -> bool:
    if prediction.event_type != label.event_type:
        return False
    if _overlap(label.start_seconds, label.end_seconds, prediction.start_seconds, prediction.end_seconds) <= 0:
        return False
    if label.event_type == "speech_reference":
        return (label.reference or "").lower() == (prediction.reference or "").lower()
    if label.event_type == "song_start":
        return (label.song_id or "") == (prediction.song_id or "")
    if label.event_type == "song_segment":
        return (
            (label.song_id or "") == (prediction.song_id or "")
            and label.section_index == prediction.section_index
            and label.line_index == prediction.line_index
        )
    return True


def _percentile95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def _match_labels(
    labels: list[tuple[str, CorpusLabel]],
    predictions: list[ProviderPrediction],
) -> tuple[int, int, int, list[float]]:
    used: set[int] = set()
    true_positives = 0
    false_negatives = 0
    latencies_ms: list[float] = []
    for recording_id, label in labels:
        match_index = -1
        for index, candidate in enumerate(predictions):
            if index in used or candidate.recording_id != recording_id:
                continue
            if _is_match(label, candidate):
                match_index = index
                break
        if match_index >= 0:
            used.add(match_index)
            true_positives += 1
            latencies_ms.append((predictions[match_index].start_seconds - label.start_seconds) * 1000.0)
        else:
            false_negatives += 1
    false_positives = len([1 for i in range(len(predictions)) if i not in used])
    return true_positives, false_positives, false_negatives, latencies_ms


def compare_provider(
    manifest: CorpusManifest,
    predictions: tuple[ProviderPrediction, ...],
    provider_name: str,
) -> dict[str, Any]:
    labels = [(recording.id, label) for recording in manifest.recordings for label in recording.labels]
    references = [(rec, label) for rec, label in labels if label.event_type == "speech_reference"]
    segments = [(rec, label) for rec, label in labels if label.event_type == "song_segment"]
    song_starts = [(rec, label) for rec, label in labels if label.event_type == "song_start"]

    ref_predictions = [p for p in predictions if p.event_type == "speech_reference"]
    seg_predictions = [p for p in predictions if p.event_type == "song_segment"]

    ref_tp, ref_fp, ref_fn, ref_lat = _match_labels(references, ref_predictions)
    seg_tp, seg_fp, seg_fn, seg_lat = _match_labels(segments, seg_predictions)

    total_duration_minutes = sum(recording.duration_seconds for recording in manifest.recordings) / 60.0
    false_triggers = ref_fp + seg_fp

    top1 = 0
    top3 = 0
    start_predictions = [p for p in predictions if p.event_type == "song_start"]
    for recording_id, label in song_starts:
        related = [
            p for p in start_predictions
            if p.recording_id == recording_id
            and _overlap(label.start_seconds, label.end_seconds, p.start_seconds, p.end_seconds) > 0
        ]
        if not related:
            continue
        ranked = related[0].candidate_song_ids or ((related[0].song_id,) if related[0].song_id else tuple())
        if ranked and ranked[0] == label.song_id:
            top1 += 1
        if label.song_id in ranked[:3]:
            top3 += 1

    latencies = ref_lat + seg_lat
    result = {
        "provider": provider_name,
        "recordings": len(manifest.recordings),
        "speech_reference": {
            "tp": ref_tp,
            "fp": ref_fp,
            "fn": ref_fn,
            "precision": 0.0 if (ref_tp + ref_fp) == 0 else ref_tp / (ref_tp + ref_fp),
            "recall": 0.0 if (ref_tp + ref_fn) == 0 else ref_tp / (ref_tp + ref_fn),
        },
        "song_segments": {
            "tp": seg_tp,
            "fp": seg_fp,
            "fn": seg_fn,
            "accuracy": 0.0 if (seg_tp + seg_fn) == 0 else seg_tp / (seg_tp + seg_fn),
        },
        "song_identification": {
            "samples": len(song_starts),
            "top1": 0.0 if len(song_starts) == 0 else top1 / len(song_starts),
            "top3": 0.0 if len(song_starts) == 0 else top3 / len(song_starts),
        },
        "latency_ms": {
            "median": None if not latencies else median(latencies),
            "p95": _percentile95(latencies),
        },
        "false_trigger_rate_per_minute": 0.0 if total_duration_minutes <= 0 else false_triggers / total_duration_minutes,
    }
    return result


def run_benchmark(
    manifest_path: str | Path,
    provider_prediction_files: dict[str, str | Path],
) -> dict[str, Any]:
    manifest = CorpusManifest.load(manifest_path)
    providers = []
    for name, file_path in provider_prediction_files.items():
        providers.append(compare_provider(manifest, load_predictions(file_path), name))
    return {
        "manifest": str(manifest_path),
        "corpus_id": manifest.corpus_id,
        "providers": providers,
    }
