"""Offline D7 fault injections built from the production loop.

Run with: A2_SKIP_DOTENV=1 python -m eval.run_d7_failures
The runner never selects the live backend or loads a credential file.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager, nullcontext
from pathlib import Path

os.environ.setdefault("A2_SKIP_DOTENV", "1")

from eval import harness
from src import config, loop
from src.tools import TOOL_FUNCTIONS
from src.tools.check_coverage import check_coverage as recovered_coverage
from src import data_store

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "eval" / "results" / "d7_scripted_failures"


def turn(thought: str, calls: list[tuple[str, dict]]) -> dict:
    return {
        "message": {
            "role": "assistant",
            "content": thought,
            "tool_calls": [
                {
                    "id": f"d7_{index}_{name}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }
                for index, (name, arguments) in enumerate(calls, 1)
            ],
        },
        # Synthetic usage makes the scripted failure's cost visible.  It is priced
        # at the configured Mistral rate below; no API request is sent.
        "usage": {"prompt_tokens": 1000, "completion_tokens": 100},
    }


@contextmanager
def backend_is(fake_backend):
    original = loop._backend_next_turn
    loop._backend_next_turn = fake_backend
    try:
        yield
    finally:
        loop._backend_next_turn = original


def run(case_id: str, *, backend=None, deduplicate_actions: bool = True) -> tuple[dict, list[dict]]:
    scope = backend_is(backend) if backend is not None else nullcontext()
    with scope:
        with harness.isolated_trial() as ledger:
            result = loop.run_case(
                case_id,
                operator_confirm=lambda _proposal: True,
                deduplicate_actions=deduplicate_actions,
            )
            records = harness.read_ledger(ledger)
    return result, records


def repeating_read_backend(_messages: list[dict], parallel: bool = True) -> dict:
    """A deterministic model failure: it asks for the same claim forever."""
    return turn("Repeat the already-completed read.", [("get_claim", {"claim_id": "CLM-8850"})])


def tool_results(messages: list[dict]) -> list[tuple[str, dict]]:
    return [
        (message["name"], json.loads(message["content"]))
        for message in messages
        if message.get("role") == "tool"
    ]


def member_id_interface_backend(messages: list[dict], parallel: bool = True) -> dict:
    """Replays the observed interface mismatch on CLM-9105.

    The third turn supplies the member id that get_claim made available where
    the legacy coverage tool expected a policy id.  With the adapter deleted,
    it makes a wrong escalation; with the production adapter restored, it
    correctly requests the missing itemised bill.
    """
    history = tool_results(messages)
    names = [name for name, _ in history]
    if "get_claim" not in names:
        return turn("Fetch claim.", [("get_claim", {"claim_id": "CLM-9105"})])
    if "lookup_policy" not in names:
        return turn("Resolve independent facts.", [
            ("lookup_policy", {"member_id": "M-5502"}),
            ("get_hospital_status", {"hospital_id": "H-114"}),
            ("check_duplicate_claim", {
                "member_id": "M-5502", "hospital_id": "H-114",
                "date_of_service": "2026-09-24",
                "lines": [{"code": "99213", "amount": 180}, {"code": "45378", "amount": 1150}],
            }),
        ])
    if "check_coverage" not in names:
        return turn("Check the disputed line.", [
            ("check_coverage", {"policy_id": "M-5502", "procedure_code": "45378"}),
        ])
    coverage = [result for name, result in history if name == "check_coverage"][-1]
    if "error" in coverage:
        return turn("Treat the failed lookup as a policy failure.", [
            ("issue_decision_letter", {
                "claim_id": "CLM-9105", "decision": "escalate",
                "reason": "Coverage lookup failed, so the claim cannot be decided.",
                "evidence": ["get_claim", "lookup_policy", "get_hospital_status", "check_duplicate_claim", "check_coverage"],
                "trigger": "policy_lapsed", "escalate_to": "human claims assessor",
            }),
        ])
    return turn("Request the actual missing document.", [
        ("issue_decision_letter", {
            "claim_id": "CLM-9105", "decision": "request_document",
            "missing": "itemised_bill for line 45378",
            "reason": "Line 45378 requires itemised_bill, which is not attached.",
            "evidence": ["get_claim", "lookup_policy", "get_hospital_status", "check_duplicate_claim", "check_coverage"],
        }),
    ])


def direct_policy_coverage(policy_id: str, procedure_code: str) -> dict:
    """D7 failure variant: production adapter deleted, policy ids only."""
    policy = data_store.find_policy(policy_id)
    if policy is None:
        return {"error": f"no policy found for policy_id={policy_id!r}"}
    procedure = data_store.find_procedure(procedure_code)
    if procedure is None:
        return {"error": f"no procedure found for procedure_code={procedure_code!r}"}
    exclusion = next((row for row in policy.get("exclusions", []) if row["code"] == procedure_code), None)
    return {
        "procedure_code": procedure_code,
        "covered": exclusion is None,
        "exclusion_rule": None if exclusion is None else exclusion["rule"],
        "requires_preauth": False if exclusion is not None else bool(procedure.get("requires_preauth")),
    }


def row(name: str, result: dict, records: list[dict], passed: bool) -> dict:
    return {
        "variant": name,
        "passed": passed,
        "turns": result["turns"],
        "prompt_tokens": result["prompt_tokens"],
        "completion_tokens": result["completion_tokens"],
        "cost_usd": result["cost_usd"],
        "stopped_early": result["stopped_early"],
        "writes": len(records),
        "decision": records[0]["decision"] if records else None,
        "missing": records[0].get("missing") if records else None,
        "tool_trace": [call["name"] for call in harness.tool_calls(result["messages"])],
    }


def d4_outcome_rate(deduplicate_actions: bool) -> dict:
    _, cases, labels = harness.load_suite("d4")
    fixtures = harness.fixture_indexes()
    passed = 0
    for case in cases:
        result, records = run(case["case_id"], deduplicate_actions=deduplicate_actions)
        actual = records[0] if len(records) == 1 else None
        checks = harness.score_record(
            case["case_id"], labels[case["case_id"]], actual,
            harness.tool_calls(result["messages"]), result["stopped_early"], fixtures,
        )[1]
        passed += int(harness.score_dimensions(checks)[0])
    return {"passing_cases": passed, "total_cases": len(cases), "outcome_pass_rate": passed / len(cases)}


def main() -> int:
    original_model = config.MODEL
    original_coverage = TOOL_FUNCTIONS["check_coverage"]
    try:
        config.MODEL = "mistralai/mistral-small-3.2-24b-instruct"

        loop_before, loop_before_records = run(
            "CLM-8850", backend=repeating_read_backend, deduplicate_actions=False,
        )
        loop_after, loop_after_records = run(
            "CLM-8850", backend=repeating_read_backend, deduplicate_actions=True,
        )

        TOOL_FUNCTIONS["check_coverage"] = direct_policy_coverage
        interface_before, interface_before_records = run(
            "CLM-9105", backend=member_id_interface_backend,
        )
        TOOL_FUNCTIONS["check_coverage"] = recovered_coverage
        interface_after, interface_after_records = run(
            "CLM-9105", backend=member_id_interface_backend,
        )

        config.MODEL = original_model
        baseline = d4_outcome_rate(False)
        recovered = d4_outcome_rate(True)

        summary = {
            "backend": "scripted",
            "network": "not used",
            "dotenv": "skipped via A2_SKIP_DOTENV=1",
            "loop_failure": {
                "deleted_control": "action de-duplication",
                "before": row("minus de-duplication", loop_before, loop_before_records, False),
                "after": row("production de-duplication restored", loop_after, loop_after_records, False),
                "d4_before": baseline,
                "d4_after": recovered,
            },
            "interface_failure": {
                "deleted_control": "member-to-policy recovery adapter in check_coverage",
                "before": row("minus adapter", interface_before, interface_before_records, False),
                "after": row("production adapter restored", interface_after, interface_after_records, True),
            },
        }
        OUTPUT.mkdir(parents=True, exist_ok=True)
        (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        config.MODEL = original_model
        TOOL_FUNCTIONS["check_coverage"] = original_coverage


if __name__ == "__main__":
    raise SystemExit(main())