#!/usr/bin/env python3
"""Resume an interrupted D5 live run by reusing completed trace files."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from eval import harness
from src import config, loop


def trace_path(run_dir: Path, case_id: str, trial: int) -> Path:
    return run_dir / "traces" / f"{case_id}_trial-{trial}.json"


def row_from_trace(
    run_dir: Path,
    metadata: dict,
    trace: dict,
    fixtures: dict[str, dict],
) -> tuple[dict, dict | None]:
    case = trace["case"]
    case_id = case["case_id"]
    trial = trace["trial"]
    expected = trace["expected_label"]
    result = trace["run_result"]
    records = trace["decision_records"]
    calls = harness.tool_calls(result["messages"])
    observations = harness.tool_observations(result["messages"])
    actual = records[0] if len(records) == 1 else None
    code_checks = trace["code_checks"]
    code_passed = all(item["passed"] for item in code_checks)
    judgement_required = bool(case.get("judgement_check"))
    negative = expected["expected_decision"] != "approve_in_principle"

    judge_input = {
        "case_id": case_id,
        "trial": trial,
        "model_id": metadata["model_id"],
        "expected_label": expected,
        "claim_fixture": fixtures["claims"][case_id],
        "supporting_fixtures": harness.supporting_fixtures(case_id, fixtures),
        "actual_record": actual,
        "tool_observations": observations,
    }
    judge_hash = harness.hash_json(judge_input) if judgement_required else None

    row = {
        "run_id": metadata["run_id"],
        "model_id": metadata["model_id"],
        "case_id": case_id,
        "author": case["author"],
        "family": expected.get("family"),
        "case_type": "negative" if negative else "ordinary",
        "trial": trial,
        "check_type": "code+llm_judgement" if judgement_required else "code",
        "expected_decision": expected["expected_decision"],
        "actual_decision": actual.get("decision") if actual else None,
        "expected_trigger": expected.get("trigger"),
        "actual_trigger": actual.get("trigger") if actual else None,
        "expected_missing": expected.get("missing"),
        "actual_missing": actual.get("missing") if actual else None,
        "code_passed": code_passed,
        "code_failures": [item["check"] for item in code_checks if not item["passed"]],
        "judgement_required": judgement_required,
        "judgement_status": "pending" if judgement_required else "not_required",
        "judge_input_sha256": judge_hash,
        "passed": None if judgement_required else code_passed,
        "turns": result["turns"],
        "prompt_tokens": result["prompt_tokens"],
        "completion_tokens": result["completion_tokens"],
        "cost_usd": result["cost_usd"],
        "stopped_early": result["stopped_early"],
        "tool_trace": [call["name"] for call in calls],
        "trace_file": f"traces/{case_id}_trial-{trial}.json",
    }
    queue_item = None
    if judgement_required:
        queue_item = {
            "judge_input_sha256": judge_hash,
            "prompt_file": harness.JUDGE_PROMPT_PATH.relative_to(harness.ROOT).as_posix(),
            "input": judge_input,
        }
    return row, queue_item


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--suite", choices=("d4", "shipped"), default="d4")
    parser.add_argument("--trial-mode", choices=("d4", "battery"), default="battery")
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-retries", type=int, default=10)
    parser.add_argument("--retry-delay-seconds", type=int, default=180)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    metadata = harness.read_json(run_dir / "metadata.json")
    suite_id, cases, labels = harness.load_suite(args.suite)
    plan = harness.trial_plan(cases, labels, args.trial_mode)
    fixtures = harness.fixture_indexes()

    config.BACKEND = "live"
    config.MODEL = args.model
    harness.config.BACKEND = "live"
    harness.config.MODEL = args.model
    harness.config.price_for(args.model)

    rows, queue = [], []
    for index, (case, trial) in enumerate(plan, 1):
        case_id = case["case_id"]
        path = trace_path(run_dir, case_id, trial)
        if path.exists():
            print(f"[{index:02d}/{len(plan)}] {case_id} trial {trial} already complete")
            trace = harness.read_json(path)
        else:
            print(f"[{index:02d}/{len(plan)}] {case_id} trial {trial}", flush=True)
            expected = labels[case_id]
            for attempt in range(1, args.max_retries + 1):
                try:
                    with harness.isolated_trial() as ledger:
                        result = loop.run_case(case_id, operator_confirm=lambda _proposal: True)
                        records = harness.read_ledger(ledger)
                    break
                except RuntimeError as exc:
                    message = str(exc)
                    retryable = (
                        "429" in message
                        or "engine_overloaded" in message
                        or "Connection reset" in message
                        or "urlopen error" in message
                    )
                    if not retryable or attempt == args.max_retries:
                        raise
                    wait = args.retry_delay_seconds * attempt
                    print(
                        f"OpenRouter rate limit on {case_id} trial {trial}; "
                        f"retry {attempt}/{args.max_retries - 1} in {wait}s",
                        flush=True,
                    )
                    time.sleep(wait)
            calls = harness.tool_calls(result["messages"])
            actual = records[0] if len(records) == 1 else None
            code_passed, checks = harness.score_record(
                case_id, expected, actual, calls, result["stopped_early"], fixtures
            )
            trace = {
                "metadata": metadata,
                "case": case,
                "trial": trial,
                "expected_label": expected,
                "decision_records": records,
                "code_checks": checks,
                "run_result": result,
            }
            harness.write_json(path, trace)

        row, queue_item = row_from_trace(run_dir, metadata, trace, fixtures)
        rows.append(row)
        if queue_item:
            queue.append(queue_item)

    metadata = dict(metadata)
    metadata["suite_id"] = suite_id
    metadata["trial_count"] = len(plan)
    metadata["dataset_sha256"] = harness.dataset_hash()
    metadata["system_prompt_sha256"] = hashlib.sha256(loop.SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    metadata["judge_prompt_sha256"] = hashlib.sha256(harness.JUDGE_PROMPT_PATH.read_bytes()).hexdigest()

    harness.write_jsonl(run_dir / "trials.jsonl", rows)
    harness.write_jsonl(run_dir / "judgement_queue.jsonl", queue)
    harness.write_result_tables(run_dir, rows)
    summary = harness.summarise(rows, metadata)
    harness.write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Results: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
