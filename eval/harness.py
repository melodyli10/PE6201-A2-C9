#!/usr/bin/env python3
"""D4 outcome-evaluation harness for Problem A.

Default (deterministic, offline and free):
    python -m eval.harness --suite d4 --backend scripted

Ordinary cases run once; negative cases (ASK or ESCALATE) run three times.
Every trial uses a private decision ledger, so no trial depends on another.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"
DATA_DIR = ROOT / "data_A"
LABELS_PATH = ROOT / "expected_outcomes_A.json"
MANIFEST_PATH = EVAL_DIR / "cases_d4.json"
JUDGE_PROMPT_PATH = EVAL_DIR / "judge_prompt.md"
SHIPPED_CASE_COUNT = 15

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config, data_store, loop  # noqa: E402


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


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


def write_result_tables(run_dir: Path, rows: list[dict]) -> None:
    """Write compact CSV/Markdown tables; detailed checks remain in traces."""
    fields = [
        "model_id", "case_id", "case_type", "trial", "check_type",
        "expected_decision", "actual_decision", "code_passed",
        "judgement_status", "passed", "turns", "prompt_tokens",
        "completion_tokens", "cost_usd", "stopped_early", "trace_file",
    ]
    with (run_dir / "results_table.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with (run_dir / "results_table.md").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("| Case | Type | Trial | Check | Expected | Actual | Code | Judgement | Final | Turns |\n")
        stream.write("|---|---|---:|---|---|---|---|---|---|---:|\n")
        for row in rows:
            final = "pending" if row["passed"] is None else ("PASS" if row["passed"] else "FAIL")
            stream.write(
                f"| {row['case_id']} | {row['case_type']} | {row['trial']} | "
                f"{row['check_type']} | {row['expected_decision']} | "
                f"{row['actual_decision']} | {'PASS' if row['code_passed'] else 'FAIL'} | "
                f"{row['judgement_status']} | {final} | {row['turns']} |\n"
            )


def hash_json(value: Any) -> str:
    packed = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def dataset_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(DATA_DIR.glob("*.json")) + [LABELS_PATH, MANIFEST_PATH]:
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def git_commit() -> str | None:
    git = shutil.which("git")
    if not git:
        return None
    try:
        result = subprocess.run(
            [git, "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT),
             "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def load_suite(name: str) -> tuple[str, list[dict], dict[str, dict]]:
    all_labels = read_json(LABELS_PATH)
    labels: dict[str, dict] = {}
    for label in all_labels:
        case_id = label.get("case_id")
        if not case_id or case_id in labels:
            raise ValueError(f"missing or duplicate answer-key case_id: {case_id!r}")
        labels[case_id] = label

    claim_ids = {row["claim_id"] for row in read_json(DATA_DIR / "claims.json")}
    if name == "d4":
        manifest = read_json(MANIFEST_PATH)
        suite_id, cases = manifest["suite_id"], manifest["cases"]
    else:
        suite_id = "teacher-shipped-regression-v1"
        cases = [{"case_id": row["case_id"], "author": "teacher fixture",
                  "judgement_check": False}
                 for row in all_labels[:SHIPPED_CASE_COUNT]]

    ids = [row.get("case_id") for row in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"suite {suite_id!r} has duplicate case ids")
    missing_claims = sorted(set(ids) - claim_ids)
    missing_labels = sorted(set(ids) - set(labels))
    if missing_claims or missing_labels:
        raise ValueError(
            f"suite integrity failure: missing claims={missing_claims}; "
            f"missing labels={missing_labels}"
        )

    negative_count = sum(labels[cid]["expected_decision"] != "approve_in_principle"
                         for cid in ids)
    if name == "d4" and not (30 <= len(cases) <= 50 and 6 <= negative_count <= 10):
        raise ValueError(
            f"D4 needs 30-50 cases and 6-10 negatives; "
            f"found {len(cases)} cases and {negative_count} negatives"
        )
    return suite_id, cases, labels


def trial_plan(
    cases: list[dict],
    labels: dict[str, dict],
    mode: str,
) -> list[tuple[dict, int]]:
    plan = []

    for case in cases:
        is_negative = (
            labels[case["case_id"]]["expected_decision"]
            != "approve_in_principle"
        )

        if mode == "d4":
            # D4: several trials per case; use 3 for every case.
            trial_count = 3
        elif mode == "battery":
            # D5: full set once, plus 3 EXTRA trials on negative cases.
            trial_count = 4 if is_negative else 1
        else:
            raise ValueError(f"unknown trial mode: {mode!r}")

        for trial in range(1, trial_count + 1):
            plan.append((case, trial))

    return plan


@contextmanager
def isolated_trial() -> Iterator[Path]:
    """Redirect the gated write to a new ledger and clear mutable state."""
    decision_module = importlib.import_module("src.tools.issue_decision_letter")
    original_path = decision_module.DECISIONS_PATH
    with tempfile.TemporaryDirectory(prefix="pe6201-d4-") as temp_dir:
        ledger = Path(temp_dir) / "decisions.jsonl"
        decision_module.DECISIONS_PATH = str(ledger)
        decision_module._approved_claims.clear()
        data_store._tables.cache_clear()
        try:
            yield ledger
        finally:
            decision_module._approved_claims.clear()
            data_store._tables.cache_clear()
            decision_module.DECISIONS_PATH = original_path


def read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def tool_calls(messages: list[dict]) -> list[dict]:
    calls = []
    for message_index, message in enumerate(messages, 1):
        if message.get("role") != "assistant":
            continue
        for call in message.get("tool_calls") or []:
            function = call.get("function", {})
            try:
                arguments = json.loads(function.get("arguments", "{}"))
            except (TypeError, json.JSONDecodeError):
                arguments = {"_unparseable": function.get("arguments")}
            calls.append({"message_index": message_index, "call_id": call.get("id"),
                          "name": function.get("name"), "arguments": arguments})
    return calls


def tool_observations(messages: list[dict]) -> list[dict]:
    observations = []
    for message in messages:
        if message.get("role") != "tool":
            continue
        try:
            result = json.loads(message.get("content", "null"))
        except (TypeError, json.JSONDecodeError):
            result = message.get("content")
        observations.append({"call_id": message.get("tool_call_id"),
                             "name": message.get("name"), "result": result})
    return observations


def compressed_evidence(calls: list[dict]) -> list[str]:
    names = [call["name"] for call in calls if call["name"] != "issue_decision_letter"]
    result, seen = [], set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        count = names.count(name)
        result.append(name if count == 1 else f"{name} x{count}")
    return result


def canonical_missing(value: Any) -> dict[str, str | None]:
    """Compare the named item semantically, without fragile substring scoring."""
    text = re.sub(r"\s+", " ", str(value or "").replace("_", " ").strip().lower())
    line = re.search(r"(?:line|for|procedure(?: code)?)\s+(\d{5})", text)
    valid_on = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if "pre-authorisation" in text or "preauthorisation" in text:
        item = "pre-authorisation"
    elif "itemised bill" in text:
        item = "itemised_bill"
    elif "discharge summary" in text:
        item = "discharge_summary"
    else:
        item = text or None
    return {"item": item, "for_line": line.group(1) if line else None,
            "valid_on": valid_on.group(0) if valid_on else None}


def fixture_indexes() -> dict[str, dict]:
    def index(file_name: str, key: str) -> dict:
        return {row[key]: row for row in read_json(DATA_DIR / file_name)}
    return {
        "claims": index("claims.json", "claim_id"),
        "members": index("members.json", "member_id"),
        "policies": index("policies.json", "policy_id"),
        "hospitals": index("hospitals.json", "hospital_id"),
    }


def expected_approval(case_id: str, fixtures: dict[str, dict]) -> dict:
    claim = fixtures["claims"][case_id]
    member = fixtures["members"][claim["member_id"]]
    policy = fixtures["policies"][member["policy_id"]]
    hospital = fixtures["hospitals"][claim["hospital_id"]]
    exclusions = {row["code"]: row["rule"] for row in policy.get("exclusions", [])}
    lines, approved, refused = [], 0, 0
    for source in claim["lines"]:
        line = {"code": source["code"], "amount": source["amount"]}
        if source["code"] in exclusions:
            line.update(status="not_covered", exclusion=exclusions[source["code"]])
            refused += source["amount"]
        else:
            line.update(status="covered")
            approved += source["amount"]
        lines.append(line)
    return {"lines": lines, "approved_total": approved, "refused_total": refused,
            "settlement_basis": "direct" if hospital["panel"] else "reimbursement"}


def normalise_lines(lines: Any) -> list[dict]:
    result = []

    status_aliases = {
        "covered": "covered",
        "approved": "covered",
        "approved with valid preauth": "covered",
        "approved with valid pre-authorisation": "covered",
        "approved with valid preauthorization": "covered",
        "not covered": "not_covered",
        "excluded": "not_covered",
        "refused": "not_covered",
    }

    for line in lines or []:
        row = {
            key: line.get(key)
            for key in ("code", "amount", "status", "exclusion")
            if line.get(key) is not None
        }

        if isinstance(row.get("status"), str):
            status_key = re.sub(
                r"[\s_-]+",
                " ",
                row["status"].strip().lower(),
            )
            row["status"] = status_aliases.get(status_key, row["status"])

        result.append(row)

    return sorted(
        result,
        key=lambda row: (
            str(row.get("code")),
            float(row.get("amount", 0)),
        ),
    )


def score_record(case_id: str, expected: dict, actual: dict | None,
                 calls: list[dict], stopped: str | None,
                 fixtures: dict[str, dict]) -> tuple[bool, list[dict]]:
    checks = []

    def check(name: str, passed: bool, wanted: Any, observed: Any) -> None:
        checks.append({"check": name, "passed": bool(passed),
                       "expected": wanted, "actual": observed})

    action_count = sum(call["name"] == "issue_decision_letter" for call in calls)
    check("gated_action_called_once", action_count == 1, 1, action_count)
    check("decision_record_written_once", actual is not None, 1, 1 if actual else 0)
    check("run_not_stopped_early", stopped is None, None, stopped)
    if actual is None:
        return False, checks

    check("case_id", actual.get("case_id") == case_id, case_id, actual.get("case_id"))
    check("decision", actual.get("decision") == expected["expected_decision"],
          expected["expected_decision"], actual.get("decision"))
    wanted_evidence = compressed_evidence(calls)
    check("evidence_matches_trace", actual.get("evidence") == wanted_evidence,
          wanted_evidence, actual.get("evidence"))

    decision = expected["expected_decision"]
    if decision == "escalate":
        check("trigger", actual.get("trigger") == expected.get("trigger"),
              expected.get("trigger"), actual.get("trigger"))
        check("escalate_to", actual.get("escalate_to") == "human claims assessor",
              "human claims assessor", actual.get("escalate_to"))
    elif decision == "request_document":
        wanted = canonical_missing(expected.get("missing"))
        observed = canonical_missing(actual.get("missing"))
        check("missing_item", observed == wanted, wanted, observed)
    else:
        wanted = expected_approval(case_id, fixtures)
        check("line_dispositions", normalise_lines(actual.get("lines")) == normalise_lines(wanted["lines"]),
              normalise_lines(wanted["lines"]), normalise_lines(actual.get("lines")))
        for field in ("approved_total", "refused_total", "settlement_basis"):
            check(field, actual.get(field) == wanted[field], wanted[field], actual.get(field))
    return all(row["passed"] for row in checks), checks


def supporting_fixtures(case_id: str, fixtures: dict[str, dict]) -> dict:
    claim = fixtures["claims"][case_id]
    member = fixtures["members"][claim["member_id"]]
    return {"member": member, "policy": fixtures["policies"][member["policy_id"]],
            "hospital": fixtures["hospitals"][claim["hospital_id"]]}


def summarise(rows: list[dict], metadata: dict) -> dict:
    def group(case_type: str | None) -> dict:
        selected = [row for row in rows if case_type is None or row["case_type"] == case_type]
        graded = [row for row in selected if row["passed"] is not None]
        code_passes = sum(row["code_passed"] for row in selected)
        final_passes = sum(row["passed"] is True for row in graded)
        pending = sum(row["passed"] is None for row in selected)
        return {
            "trials": len(selected),
            "code_passed": code_passes,
            "code_pass_rate": round(code_passes / len(selected), 4) if selected else None,
            "final_graded": len(graded),
            "final_passed": final_passes,
            # A submission-level pass rate is not a measurement until every
            # required judgement is present. Keep the partial figure explicit.
            "graded_only_pass_rate": round(final_passes / len(graded), 4) if graded else None,
            "final_pass_rate": (
                round(final_passes / len(selected), 4) if selected and pending == 0 else None
            ),
            "judgement_pending": pending,
        }
    return {
        "metadata": metadata,
        "cases": len({row["case_id"] for row in rows}),
        "negative_cases": len({row["case_id"] for row in rows if row["case_type"] == "negative"}),
        "overall": group(None), "ordinary": group("ordinary"), "negative": group("negative"),
        "average_turns": round(sum(row["turns"] for row in rows) / len(rows), 3),
        "total_prompt_tokens": sum(row["prompt_tokens"] for row in rows),
        "total_completion_tokens": sum(row["completion_tokens"] for row in rows),
        "total_cost_usd": round(sum(row["cost_usd"] for row in rows), 6),
    }


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "unknown"


def run(args: argparse.Namespace) -> Path:
    suite_id, cases, labels = load_suite(args.suite)
    plan = trial_plan(cases, labels, args.trial_mode)
    negatives = sum(labels[row["case_id"]]["expected_decision"] != "approve_in_principle"
                    for row in cases)
    print(f"Suite: {suite_id}; cases={len(cases)}, negatives={negatives}, trials={len(plan)}")
    if args.dry_run:
        return EVAL_DIR
    if args.backend == "live" and not args.allow_live:
        raise SystemExit("Live execution requires --allow-live after checking expected spend.")
    if args.backend == "live" and not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY is required for --backend live")

    config.BACKEND = args.backend
    if args.model:
        config.MODEL = args.model
    config.price_for(config.MODEL)  # Reject unknown prices before the first request.
    evaluated_model = config.MODEL if args.backend == "live" else "scripted-policy-v1"

    started = datetime.now(timezone.utc)
    run_id = f"{started.strftime('%Y%m%dT%H%M%SZ')}_{safe_name(args.backend)}_{safe_name(evaluated_model)}"
    run_dir = Path(args.output_dir).resolve() / run_id
    traces_dir = run_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=False)
    metadata = {
        "run_id": run_id, "suite_id": suite_id, "backend": args.backend,
        "model_id": evaluated_model, "configured_model": config.MODEL,
        "prompt_version": args.prompt_version,
        "run_date_utc": started.isoformat(), "git_commit": git_commit(),
        "dataset_sha256": dataset_hash(),
        "system_prompt_sha256": hashlib.sha256(loop.SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "judge_prompt": JUDGE_PROMPT_PATH.relative_to(ROOT).as_posix(),
        "judge_prompt_sha256": hashlib.sha256(JUDGE_PROMPT_PATH.read_bytes()).hexdigest(),
        "trial_count": len(plan),
    }
    write_json(run_dir / "metadata.json", metadata)

    fixtures = fixture_indexes()
    rows, queue = [], []
    for index, (case, trial) in enumerate(plan, 1):
        case_id, expected = case["case_id"], labels[case["case_id"]]
        negative = expected["expected_decision"] != "approve_in_principle"
        print(f"[{index:02d}/{len(plan)}] {case_id} trial {trial}", flush=True)
        with isolated_trial() as ledger:
            result = loop.run_case(case_id, operator_confirm=lambda _proposal: True)
            records = read_ledger(ledger)

        calls = tool_calls(result["messages"])
        observations = tool_observations(result["messages"])
        actual = records[0] if len(records) == 1 else None
        code_passed, checks = score_record(
            case_id, expected, actual, calls, result["stopped_early"], fixtures
        )
        trace_name = f"{case_id}_trial-{trial}.json"
        write_json(traces_dir / trace_name, {
            "metadata": metadata, "case": case, "trial": trial,
            "expected_label": expected, "decision_records": records,
            "code_checks": checks, "run_result": result,
        })

        judgement_required = bool(case.get("judgement_check"))
        judge_input = {
            "case_id": case_id, "trial": trial, "model_id": evaluated_model,
            "expected_label": expected, "claim_fixture": fixtures["claims"][case_id],
            "supporting_fixtures": supporting_fixtures(case_id, fixtures),
            "actual_record": actual, "tool_observations": observations,
        }
        judge_hash = hash_json(judge_input) if judgement_required else None
        if judgement_required:
            queue.append({"judge_input_sha256": judge_hash,
                          "prompt_file": JUDGE_PROMPT_PATH.relative_to(ROOT).as_posix(),
                          "input": judge_input})

        rows.append({
            "run_id": run_id, "model_id": evaluated_model, "case_id": case_id,
            "author": case["author"], "family": expected.get("family"),
            "case_type": "negative" if negative else "ordinary", "trial": trial,
            "check_type": "code+llm_judgement" if judgement_required else "code",
            "expected_decision": expected["expected_decision"],
            "actual_decision": actual.get("decision") if actual else None,
            "expected_trigger": expected.get("trigger"),
            "actual_trigger": actual.get("trigger") if actual else None,
            "expected_missing": expected.get("missing"),
            "actual_missing": actual.get("missing") if actual else None,
            "code_passed": code_passed,
            "code_failures": [item["check"] for item in checks if not item["passed"]],
            "judgement_required": judgement_required,
            "judgement_status": "pending" if judgement_required else "not_required",
            "judge_input_sha256": judge_hash,
            "passed": None if judgement_required else code_passed,
            "turns": result["turns"], "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"], "cost_usd": result["cost_usd"],
            "stopped_early": result["stopped_early"],
            "tool_trace": [call["name"] for call in calls],
            "trace_file": f"traces/{trace_name}",
        })

    write_jsonl(run_dir / "trials.jsonl", rows)
    write_jsonl(run_dir / "judgement_queue.jsonl", queue)
    write_result_tables(run_dir, rows)
    summary = summarise(rows, metadata)
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Results: {run_dir}")
    return run_dir


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--suite", choices=("d4", "shipped"), default="d4")
    result.add_argument("--backend", choices=("scripted", "live"), default="scripted")
    result.add_argument(
    "--trial-mode",
    choices=("d4", "battery"),
    default="battery",
    help="d4 = 3 trials per case; battery = full set once plus 3 extra negative trials",
)
    result.add_argument("--model", help="Model id; register its price in src/config.py")
    result.add_argument("--prompt-version", default="v2-final")
    result.add_argument("--output-dir", default=str(EVAL_DIR / "results"))
    result.add_argument("--dry-run", action="store_true", help="Validate and print counts only")
    result.add_argument("--allow-live", action="store_true",
                        help="Explicit confirmation that a paid live battery may run")
    return result


def main() -> int:
    try:
        run(parser().parse_args())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
