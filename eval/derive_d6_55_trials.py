#!/usr/bin/env python3
"""Derive the teacher-required 55-trial D6 evidence set from a 65-trial battery.

This is deliberately a local transformation: it neither configures a backend
nor calls a model.  It retains the one ordinary trial for every ordinary case
and trials 1--3 for every negative case, excluding only negative trial 4.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from eval import harness


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "eval" / "results" / (
    "20260914T023002Z_live_mistralai-mistral-small-3.2-24b-instruct"
)
DEFAULT_OUTPUT = ROOT / "eval" / "results" / (
    "20260914T023002Z_live_mistralai-mistral-small-3.2-24b-instruct_d6-55-trials"
)


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def keep_row(row: dict) -> bool:
    """Return whether a source result belongs to the teacher's 55-trial plan."""
    if row["case_type"] == "ordinary":
        return row["trial"] == 1
    if row["case_type"] == "negative":
        return row["trial"] in {1, 2, 3}
    raise ValueError(f"unknown case type: {row['case_type']!r}")


def key(row: dict) -> tuple[str, int]:
    return row["case_id"], row["trial"]


def validate_source(rows: list[dict], metadata: dict) -> None:
    if metadata.get("trial_count") != 65 or len(rows) != 65:
        raise ValueError(
            "D6 derivation requires exactly the completed 65-trial source battery "
            f"(metadata={metadata.get('trial_count')}, rows={len(rows)})"
        )
    if len({key(row) for row in rows}) != len(rows):
        raise ValueError("source battery has duplicate case/trial rows")

    negative_trials: dict[str, set[int]] = {}
    ordinary_trials: dict[str, set[int]] = {}
    for row in rows:
        bucket = negative_trials if row["case_type"] == "negative" else ordinary_trials
        bucket.setdefault(row["case_id"], set()).add(row["trial"])
    if len(ordinary_trials) != 25 or any(trials != {1} for trials in ordinary_trials.values()):
        raise ValueError("source does not contain 25 ordinary cases with only trial 1")
    if len(negative_trials) != 10 or any(trials != {1, 2, 3, 4} for trials in negative_trials.values()):
        raise ValueError("source does not contain 10 negative cases with trials 1--4")


def derived_rows(source_rows: list[dict], source_dir: Path, output_dir: Path, run_id: str) -> list[dict]:
    rows = []
    for source_row in source_rows:
        if not keep_row(source_row):
            continue
        row = dict(source_row)
        row["run_id"] = run_id
        source_trace = source_dir / source_row["trace_file"]
        if not source_trace.exists():
            raise ValueError(f"missing source trace: {source_trace}")
        row["trace_file"] = Path(os.path.relpath(source_trace, output_dir)).as_posix()
        rows.append(row)
    if len(rows) != 55:
        raise ValueError(f"expected 55 retained trials, got {len(rows)}")
    if sum(row["case_type"] == "ordinary" for row in rows) != 25:
        raise ValueError("derived result must retain 25 ordinary trials")
    if sum(row["case_type"] == "negative" for row in rows) != 30:
        raise ValueError("derived result must retain 30 negative trials")
    return rows


def filter_keyed_rows(rows: list[dict], kept: set[tuple[str, int]]) -> list[dict]:
    result = []
    for row in rows:
        item = row.get("input", row)
        item_key = key(item)
        if item_key in kept:
            result.append(row)
    return result


def filter_judgement_results(rows: list[dict], kept_hashes: set[str]) -> list[dict]:
    return [row for row in rows if row.get("judge_input_sha256") in kept_hashes]


def build_submission(rows: list[dict], metadata: dict) -> dict:
    fields = (
        "case_id", "case_type", "trial", "expected_decision", "expected_trigger",
        "actual_decision", "actual_trigger", "passed", "turns", "prompt_tokens",
        "completion_tokens", "cost_usd", "stopped_early", "trace_file",
    )
    return {
        "metadata": {
            "owner": "Chai Peiyao",
            "model_id": metadata["model_id"],
            "model_family": "Mistral",
            "price_tier": "cheap",
            "prompt_version": metadata["prompt_version"],
            "eval_set_commit": metadata["git_commit"],
            "run_date": metadata["run_date_utc"][:10],
            "input_usd_per_million": 0.075,
            "output_usd_per_million": 0.2,
            "price_source": "https://openrouter.ai/mistralai/mistral-small-3.2-24b-instruct",
            "reasoning_setting": "not_applicable",
            "trial_count": len(rows),
            "derivation": "Local selection from the 65-trial source: ordinary trial 1 and negative trials 1--3; negative trial 4 excluded.",
        },
        "runs": [{field: row[field] for field in fields} for row in rows],
    }


def derive(source_dir: Path, output_dir: Path) -> Path:
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")

    source_metadata = read_json(source_dir / "metadata.json")
    source_rows = read_jsonl(source_dir / "trials.jsonl")
    validate_source(source_rows, source_metadata)

    run_id = f"{source_metadata['run_id']}_d6-55-trials"
    rows = derived_rows(source_rows, source_dir, output_dir, run_id)
    kept = {key(row) for row in rows}
    output_dir.mkdir(parents=True)

    metadata = dict(source_metadata)
    metadata.update({
        "run_id": run_id,
        "trial_count": len(rows),
        "derived_from": {
            "run_id": source_metadata["run_id"],
            "trial_count": source_metadata["trial_count"],
            "path": source_dir.relative_to(ROOT).as_posix(),
        },
        "derivation": {
            "method": "local row selection; no model execution",
            "ordinary_trials_retained": [1],
            "negative_trials_retained": [1, 2, 3],
            "negative_trials_excluded": [4],
        },
    })
    write_json(output_dir / "metadata.json", metadata)
    write_jsonl(output_dir / "trials.jsonl", rows)
    harness.write_result_tables(output_dir, rows)
    write_json(output_dir / "summary.json", harness.summarise(rows, metadata))

    queue_path = source_dir / "judgement_queue.jsonl"
    if queue_path.exists():
        write_jsonl(output_dir / "judgement_queue.jsonl", filter_keyed_rows(read_jsonl(queue_path), kept))

    judged_path = source_dir / "trials_judged.jsonl"
    if judged_path.exists():
        judged_rows = derived_rows(read_jsonl(judged_path), source_dir, output_dir, run_id)
        write_jsonl(output_dir / "trials_judged.jsonl", judged_rows)
        judged_metadata = dict(metadata)
        source_judged_summary = read_json(source_dir / "summary_judged.json")
        if "judgements_applied_utc" in source_judged_summary.get("metadata", {}):
            judged_metadata["judgements_applied_utc"] = source_judged_summary["metadata"]["judgements_applied_utc"]
        write_json(output_dir / "summary_judged.json", harness.summarise(judged_rows, judged_metadata))

    judge_results_path = source_dir / "judgements_codex_gpt5.jsonl"
    if judge_results_path.exists():
        write_jsonl(output_dir / "judgements_codex_gpt5.jsonl", filter_judgement_results(read_jsonl(judge_results_path), {row["judge_input_sha256"] for row in rows if row.get("judge_input_sha256")}))

    write_json(output_dir / "D6_Chai_Peiyao_Mistral_55_trials.json", build_submission(rows, metadata))
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(derive(args.source, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
