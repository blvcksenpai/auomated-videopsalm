from pathlib import Path

from videopsalm.benchmark import compare_provider, load_predictions, run_benchmark
from videopsalm.corpus import CorpusManifest


FIXTURE_ROOT = Path("data/corpus/benchmark-sample")


def test_compare_provider_metrics_shape() -> None:
    manifest = CorpusManifest.load(FIXTURE_ROOT / "manifest.json")
    predictions = load_predictions(FIXTURE_ROOT / "providers/local_whisper.json")
    result = compare_provider(manifest, predictions, "local_whisper")
    assert result["speech_reference"]["precision"] > 0.0
    assert result["speech_reference"]["recall"] > 0.0
    assert result["song_identification"]["top3"] == 1.0
    assert result["latency_ms"]["p95"] is not None


def test_run_benchmark_compares_multiple_providers() -> None:
    result = run_benchmark(
        FIXTURE_ROOT / "manifest.json",
        {
            "local_whisper": FIXTURE_ROOT / "providers/local_whisper.json",
            "hosted_streaming": FIXTURE_ROOT / "providers/hosted_streaming.json",
        },
    )
    assert len(result["providers"]) == 2
    names = {item["provider"] for item in result["providers"]}
    assert names == {"local_whisper", "hosted_streaming"}
