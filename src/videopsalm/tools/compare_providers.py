"""CLI helper to generate provider benchmark outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from videopsalm.benchmark import run_benchmark


def _markdown_table(result: dict[str, object]) -> str:
    rows = [
        "| Provider | Ref Precision | Ref Recall | Segment Accuracy | Top-1 | Top-3 | Median Latency (ms) | P95 Latency (ms) | False Triggers/min |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for provider in result["providers"]:
        p = provider
        rows.append(
            "| {name} | {rp:.3f} | {rr:.3f} | {sa:.3f} | {t1:.3f} | {t3:.3f} | {median:.1f} | {p95:.1f} | {ftr:.3f} |".format(
                name=p["provider"],
                rp=p["speech_reference"]["precision"],
                rr=p["speech_reference"]["recall"],
                sa=p["song_segments"]["accuracy"],
                t1=p["song_identification"]["top1"],
                t3=p["song_identification"]["top3"],
                median=(p["latency_ms"]["median"] or 0.0),
                p95=(p["latency_ms"]["p95"] or 0.0),
                ftr=p["false_trigger_rate_per_minute"],
            )
        )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ASR/provider comparison results")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--provider", action="append", default=[], help="name=predictions.json")
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--markdown-output", required=True)
    args = parser.parse_args()

    mappings: dict[str, str] = {}
    for item in args.provider:
        if "=" not in item:
            raise SystemExit(f"invalid --provider value: {item}")
        name, path = item.split("=", 1)
        mappings[name] = path

    result = run_benchmark(args.manifest, mappings)
    json_path = Path(args.json_output)
    md_path = Path(args.markdown_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    md = [
        "# ASR Provider Comparison Results",
        "",
        f"Manifest: `{args.manifest}`",
        "",
        _markdown_table(result),
        "",
        "## Notes",
        "",
        "- Metrics are computed from labeled manifest events and provider prediction files.",
        "- Run this command after updating labels or provider outputs to regenerate both JSON and Markdown results.",
        "- Use real consented sanctuary recordings for production decisions.",
    ]
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
