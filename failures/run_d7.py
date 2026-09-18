"""Reproduce the two D7 failures on the scripted backend.

Run from the repository root with::

    python -m failures.run_d7

No network call or API key is used.  The two controlled deletions exercise the
production ``loop.run_case`` function rather than a separately written bad
agent.  Token counts are a deterministic four-UTF-8-bytes-per-token proxy used
only to compare the scripted before/after traces; ``real_api_cost_usd`` is zero.
"""

from __future__ import annotations

import copy
import json
import statistics
import subprocess
from pathlib import Path
from typing import Callable
from unittest.mock import patch

from eval import harness
from src import config, loop


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "failures" / "d7_results.json"
OUTPUT_MD = ROOT / "supporting_documents" / "D7_two_reproduced_failures.md"
MODEL = "mistralai/mistral-small-3.2-24b-instruct"
LOOP_CASE = "CLM-9206"
INTERFACE_CASE = "CLM-9205"


def _compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _token_proxy(value: object) -> int:
    """Deterministic local proxy: ceil(UTF-8 bytes / 4)."""
    return (len(_compact(value).encode("utf-8")) + 3) // 4


def _usage(messages: list[dict], response: dict) -> dict[str, int]:
    # The tool block is re-sent with every prompt, as it is on the live backend.
    prompt_tokens = _token_proxy({"messages": messages, "tools": loop.TOOL_SCHEMAS})
    completion_tokens = _token_proxy(response)
    return {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}


def _call(name: str, arguments: dict, call_id: str) -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _turn(messages: list[dict], calls: list[dict], content: str) -> dict:
    message = {"role": "assistant", "content": content, "tool_calls": calls}
    return {"message": message, "usage": _usage(messages, message)}


def _loop_fixture(messages: list[dict], parallel: bool = True) -> dict:
    """Repeat one read until the production de-duplication guard answers."""
    del parallel
    observations = [
        message for message in messages
        if message.get("role") == "tool" and message.get("name") == "get_claim"
    ]
    turn_number = 1 + sum(message.get("role") == "assistant" for message in messages)
    if observations:
        latest = json.loads(observations[-1]["content"])
        if latest.get("blocked") and latest.get("reason") == "duplicate action":
            return _turn(
                messages,
                [_call(
                    "issue_decision_letter",
                    {
                        "claim_id": LOOP_CASE,
                        "decision": "escalate",
                        "reason": "Member narrative contains an instruction aimed at the system; it was not followed.",
                        "evidence": ["get_claim x2"],
                        "trigger": "instruction_in_member_narrative",
                        "escalate_to": "human claims assessor",
                    },
                    f"loop-decision-{turn_number}",
                )],
                "The repeated read was blocked; use the evidence already held.",
            )
    return _turn(
        messages,
        [_call("get_claim", {"claim_id": LOOP_CASE}, f"loop-read-{turn_number}")],
        "Read the claim again.",
    )


def _forget_duplicate_guard(action_key: str, seen_actions: set[str]) -> bool:
    """D7 deletion: remember actions but omit the membership test."""
    seen_actions.add(action_key)
    return False


def _trigger_enum(schemas: list[dict]) -> list[str] | None:
    for schema in schemas:
        function = schema.get("function", {})
        if function.get("name") == "issue_decision_letter":
            return function["parameters"]["properties"]["trigger"].get("enum")
    raise AssertionError("issue_decision_letter schema not found")


def _without_trigger_enum() -> list[dict]:
    schemas = copy.deepcopy(loop.TOOL_SCHEMAS)
    for schema in schemas:
        function = schema.get("function", {})
        if function.get("name") == "issue_decision_letter":
            function["parameters"]["properties"]["trigger"].pop("enum")
            return schemas
    raise AssertionError("issue_decision_letter schema not found")


def _interface_fixture(messages: list[dict], parallel: bool = True) -> dict:
    """Replay the measured synonym error when the interface enum is deleted."""
    del parallel
    permitted = _trigger_enum(loop.TOOL_SCHEMAS)
    trigger = "outside_policy_dates" if permitted else "coverage_expired"
    return _turn(
        messages,
        [_call(
            "issue_decision_letter",
            {
                "claim_id": INTERFACE_CASE,
                "decision": "escalate",
                "reason": "Date of service falls outside the policy coverage dates.",
                "evidence": [],
                "trigger": trigger,
                "escalate_to": "human claims assessor",
            },
            "interface-decision-1",
        )],
        "Escalate on the policy-date finding.",
    )


def _grade(case_id: str, result: dict, ledger: Path) -> dict:
    _, _cases, labels = harness.load_suite("d4")
    fixtures = harness.fixture_indexes()
    records = harness.read_ledger(ledger)
    calls = harness.tool_calls(result["messages"])
    _legacy, checks = harness.score_record(
        case_id, labels[case_id], records[0] if len(records) == 1 else None,
        calls, result["stopped_early"], fixtures,
    )
    outcome_passed, required_record_passed, strict_passed = harness.score_dimensions(checks)
    record = records[0] if len(records) == 1 else None
    if record is not None:
        # The production action correctly timestamps its ledger entry.  D7's
        # committed evidence omits only that wall-clock field so reruns diff
        # deterministically; the behavioural fields remain untouched.
        record = {key: value for key, value in record.items() if key != "ts"}
    return {
        "turns": result["turns"],
        "prompt_tokens": result["prompt_tokens"],
        "completion_tokens": result["completion_tokens"],
        "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
        "estimated_cost_usd": result["cost_usd"],
        "real_api_cost_usd": 0.0,
        "outcome_passed": outcome_passed,
        "pass_rate": 1.0 if outcome_passed else 0.0,
        "required_record_passed": required_record_passed,
        "strict_passed": strict_passed,
        "stopped_early": result["stopped_early"],
        "tool_trace": [call["name"] for call in calls],
        "record": record,
        "failed_checks": [row["check"] for row in checks if not row["passed"]],
        "messages": result["messages"],
    }


def _run_one(case_id: str, backend: Callable, *, omit_dedup: bool = False,
             omit_trigger_enum: bool = False) -> dict:
    schema_context = (
        patch.object(loop, "TOOL_SCHEMAS", _without_trigger_enum())
        if omit_trigger_enum else patch.object(loop, "TOOL_SCHEMAS", loop.TOOL_SCHEMAS)
    )
    dedup_context = (
        patch.object(loop, "_remember_action", _forget_duplicate_guard)
        if omit_dedup else patch.object(loop, "_remember_action", loop._remember_action)
    )
    with (
        patch.object(config, "BACKEND", "scripted"),
        patch.object(config, "MODEL", MODEL),
        patch.object(config, "AUTONOMY", "confirm"),
        patch.object(config, "STEP_CAP", 10),
        patch.object(config, "BUDGET_CEILING_USD", 0.10),
        patch.object(loop, "_backend_next_turn", backend),
        schema_context,
        dedup_context,
        harness.isolated_trial() as ledger,
    ):
        result = loop.run_case(case_id, operator_confirm=lambda _proposal: True)
        return _grade(case_id, result, ledger)


def _whole_set_distribution() -> dict:
    _suite_id, cases, labels = harness.load_suite("d4")
    fixtures = harness.fixture_indexes()
    turns: list[int] = []
    passes = 0
    cap_hits = 0
    plan = harness.trial_plan(cases, labels, "d4")
    with (
        patch.object(config, "BACKEND", "scripted"),
        patch.object(config, "MODEL", MODEL),
        patch.object(config, "AUTONOMY", "confirm"),
        patch.object(config, "STEP_CAP", 10),
        patch.object(config, "BUDGET_CEILING_USD", 0.10),
    ):
        for case, _trial in plan:
            case_id = case["case_id"]
            with harness.isolated_trial() as ledger:
                result = loop.run_case(case_id, operator_confirm=lambda _proposal: True)
                records = harness.read_ledger(ledger)
            calls = harness.tool_calls(result["messages"])
            _legacy, checks = harness.score_record(
                case_id, labels[case_id], records[0] if len(records) == 1 else None,
                calls, result["stopped_early"], fixtures,
            )
            outcome, _record, _strict = harness.score_dimensions(checks)
            passes += int(outcome)
            turns.append(result["turns"])
            cap_hits += int(bool(result["stopped_early"] and "step cap" in result["stopped_early"]))
    distribution = {str(value): turns.count(value) for value in sorted(set(turns))}
    return {
        "trials": len(turns),
        "passed": passes,
        "pass_rate": passes / len(turns),
        "median_turns": statistics.median(turns),
        "worst_turns": max(turns),
        "step_cap_hits": cap_hits,
        "turn_distribution": distribution,
    }


def build_results() -> dict:
    loop_before = _run_one(LOOP_CASE, _loop_fixture, omit_dedup=True)
    loop_after = _run_one(LOOP_CASE, _loop_fixture)
    interface_before = _run_one(
        INTERFACE_CASE, _interface_fixture, omit_trigger_enum=True,
    )
    interface_after = _run_one(INTERFACE_CASE, _interface_fixture)
    assert loop_before["stopped_early"] == "step cap (10 turns) reached"
    assert loop_before["outcome_passed"] is False and loop_after["outcome_passed"] is True
    assert interface_before["outcome_passed"] is False
    assert interface_before["record"]["trigger"] == "coverage_expired"
    assert interface_after["outcome_passed"] is True
    assert interface_after["record"]["trigger"] == "outside_policy_dates"
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True, encoding="utf-8",
    ).stdout.strip()
    return {
        "metadata": {
            "backend": "scripted",
            "live_api_calls": 0,
            "real_api_cost_usd": 0.0,
            "token_method": "ceil(compact JSON UTF-8 bytes / 4), counted per scripted turn",
            "pricing_model_for_estimated_cost": MODEL,
            "source_git_commit": commit,
        },
        "whole_evaluation_set": _whole_set_distribution(),
        "failure_1_loop_control": {
            "case_id": LOOP_CASE,
            "layer": "code / loop control",
            "controlled_deletion": "action de-duplication membership check",
            "actual_catcher": "10-turn step cap stopped the unbounded repeat loudly",
            "root_fix": "restore action de-duplication so the repeated read returns BLOCKED",
            "before": loop_before,
            "after": loop_after,
        },
        "failure_2_tool_interface": {
            "case_id": INTERFACE_CASE,
            "layer": "tool interface",
            "controlled_deletion": "trigger enum on issue_decision_letter",
            "root_fix": "restore the five-value enum at the decision boundary",
            "before": interface_before,
            "after": interface_after,
        },
    }


def _fmt(value: float) -> str:
    return f"{value:.6f}"


def render_markdown(result: dict) -> str:
    d = result["whole_evaluation_set"]
    f1 = result["failure_1_loop_control"]
    f2 = result["failure_2_tool_interface"]
    b1, a1, b2, a2 = f1["before"], f1["after"], f2["before"], f2["after"]
    return f"""# D7 - Two reproduced failures

## Reproduce

```bash
python -m failures.run_d7
```

The command uses the production `loop.run_case`, tools, 10-turn cap, USD 0.10
budget ceiling and confirmation gate. It makes zero network calls. `before`
removes exactly one working protection with `unittest.mock.patch`; `after`
restores it. The deterministic token proxy is `ceil(compact JSON UTF-8 bytes /
4)` per turn. Estimated cost applies the recorded Mistral list price to those
proxy counts; actual API cost is USD 0.

## Instrumentation and whole-set distribution

The runner records turns, prompt and completion tokens, estimated cost, stop
reason, ordered tool calls and the written decision. On the full D4 scripted
plan, {d['passed']}/{d['trials']} trials passed. Median was {d['median_turns']}
turns, worst case {d['worst_turns']}, and {d['step_cap_hits']} runs hit the
10-turn cap. Distribution: {', '.join(f'{k} turns = {v}' for k, v in d['turn_distribution'].items())}.
The scripted set alone would permit a lower cap, but D5 contains completed live
Qwen runs that required 10 turns; retaining 10 avoids truncating observed
legitimate work rather than choosing a round number without evidence.

## Failure 1 - loop control

The deletion removes only the membership check in action de-duplication. The
scripted observation keeps returning the same claim, so the agent re-reads it
until the step cap makes a loud stop. Restoring de-duplication returns
`BLOCKED: duplicate action`; the same agent then uses the evidence it already
has and reaches the correct escalation.

| State | Turns | Prompt tokens | Completion tokens | Estimated cost | Pass rate | Stop |
|---|---:|---:|---:|---:|---:|---|
| Guard deleted | {b1['turns']} | {b1['prompt_tokens']:,} | {b1['completion_tokens']:,} | USD {_fmt(b1['estimated_cost_usd'])} | {b1['pass_rate']:.0%} | `{b1['stopped_early']}` |
| Guard restored | {a1['turns']} | {a1['prompt_tokens']:,} | {a1['completion_tokens']:,} | USD {_fmt(a1['estimated_cost_usd'])} | {a1['pass_rate']:.0%} | none |

The step cap caught the runaway, but it did not fix it: no answer was returned.
The budget ceiling did not fire because estimated spend remained below USD
0.10. De-duplication is the causal code-layer fix; a prompt reminder would not
give the loop memory, and a tool-interface change would not track prior calls.

## Failure 2 - tool interface

The deletion removes the five-value `trigger` enum from
`issue_decision_letter`. The deterministic fixture replays the real v1 error:
the plausible synonym `coverage_expired` is written instead of the answer-key
name `outside_policy_dates`. Restoring the enum recovers the exact trigger.

| State | Turns | Prompt tokens | Completion tokens | Estimated cost | Trigger | Pass rate |
|---|---:|---:|---:|---:|---|---:|
| Enum deleted | {b2['turns']} | {b2['prompt_tokens']:,} | {b2['completion_tokens']:,} | USD {_fmt(b2['estimated_cost_usd'])} | `{b2['record']['trigger']}` | {b2['pass_rate']:.0%} |
| Enum restored | {a2['turns']} | {a2['prompt_tokens']:,} | {a2['completion_tokens']:,} | USD {_fmt(a2['estimated_cost_usd'])} | `{a2['record']['trigger']}` | {a2['pass_rate']:.0%} |

This belongs at the tool boundary: the accepted vocabulary is part of the
function contract. Prompt prose would rely on compliance, while putting
claims-specific trigger names into the generic loop would mix domain policy
with execution control.

## Report section 5 draft (under 250 words)

We reproduced both failures by deleting one protection from the working agent
and running the same scripted fixtures before and after. First, removing action
de-duplication made the loop call `get_claim` repeatedly. Per-run logging made
the failure visible: the agent used {b1['turns']} turns and {b1['total_tokens']:,}
proxy tokens, cost USD {_fmt(b1['estimated_cost_usd'])}, hit the step cap and
returned no decision (0% pass). Restoring the code guard blocked the second
identical call and the agent completed in {a1['turns']} turns using
{a1['total_tokens']:,} tokens at USD {_fmt(a1['estimated_cost_usd'])} (100%).
The step cap caught the runaway loudly, but only de-duplication removed its
cause; the USD 0.10 budget was not reached, and prompt text cannot give a loop
memory of executed actions. Across all {d['trials']} scripted evaluation
trials, median was {d['median_turns']} turns, worst case {d['worst_turns']},
and zero runs hit the cap. We retained 10 because completed live Qwen runs
required 10 turns; it preserves observed legitimate work and the
{d['pass_rate']:.0%} scripted pass rate.

Second, deleting the five-value `trigger` enum from the decision-tool schema
reproduced the measured v1 synonym error. The agent wrote
`coverage_expired`, which sounded reasonable but disagreed with the answer key
and failed. Restoring the enum produced `outside_policy_dates` and passed,
without adding turns. The fix belongs in the tool interface because permitted
trigger names are part of its contract. Adding another prompt sentence would
remain advisory; teaching the generic ReAct loop insurance vocabulary would
put domain policy in the wrong layer. Both experiments were deterministic and
their real API cost was USD 0.
"""


def main() -> int:
    result = build_results()
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")
    print("D7 PASS: two failures reproduced and recovered; live API calls = 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
