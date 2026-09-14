#!/usr/bin/env python3
"""Build the agreed D5(b) hand-in JSON from a completed harness run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import PRICE_PER_MILLION


def read_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--model-family", required=True)
    parser.add_argument("--price-tier", required=True)
    parser.add_argument("--price-source", required=True)
    parser.add_argument("--reasoning-setting", default="not_applicable")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    metadata = read_json(run_dir / "metadata.json")
    rows_path = run_dir / "trials_judged.jsonl"
    if not rows_path.exists():
        raise SystemExit("trials_judged.jsonl is required; finish all judgements first")
    rows = read_jsonl(rows_path)
    if len(rows) != metadata["trial_count"]:
        raise SystemExit(
            f"trial count mismatch: metadata={metadata['trial_count']}, rows={len(rows)}"
        )

    model_id = metadata["model_id"]
    if model_id not in PRICE_PER_MILLION:
        raise SystemExit(f"price not registered for {model_id}")
    input_price, output_price = PRICE_PER_MILLION[model_id]

    result = {
        "metadata": {
            "owner": args.owner,
            "model_id": model_id,
            "model_family": args.model_family,
            "price_tier": args.price_tier,
            "prompt_version": metadata["prompt_version"],
            "eval_set_commit": metadata["git_commit"],
            "run_date": metadata["run_date_utc"][:10],
            "input_usd_per_million": input_price,
            "output_usd_per_million": output_price,
            "price_source": args.price_source,
            "reasoning_setting": args.reasoning_setting,
        },
        "runs": [
            {
                "case_id": row["case_id"],
                "case_type": row["case_type"],
                "trial": row["trial"],
                "expected_decision": row["expected_decision"],
                "expected_trigger": row["expected_trigger"],
                "actual_decision": row["actual_decision"],
                "actual_trigger": row["actual_trigger"],
                "passed": row["passed"],
                "turns": row["turns"],
                "prompt_tokens": row["prompt_tokens"],
                "completion_tokens": row["completion_tokens"],
                "cost_usd": row["cost_usd"],
                "stopped_early": row["stopped_early"],
                "trace_file": row["trace_file"],
            }
            for row in rows
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
