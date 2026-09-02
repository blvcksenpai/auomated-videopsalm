# ASR Provider Comparison Results

Manifest: `data/corpus/benchmark-sample/manifest.json`

| Provider | Ref Precision | Ref Recall | Segment Accuracy | Top-1 | Top-3 | Median Latency (ms) | P95 Latency (ms) | False Triggers/min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| local_whisper | 0.667 | 1.000 | 1.000 | 1.000 | 1.000 | 200.0 | 400.0 | 0.250 |
| hosted_streaming | 1.000 | 1.000 | 0.750 | 0.000 | 1.000 | 600.0 | 800.0 | 0.250 |

## Notes

- Metrics are computed from labeled manifest events and provider prediction files.
- Run this command after updating labels or provider outputs to regenerate both JSON and Markdown results.
- Use real consented sanctuary recordings for production decisions.
