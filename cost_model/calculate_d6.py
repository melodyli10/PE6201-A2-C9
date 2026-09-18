"""Recalculate the D6 cost table from committed live-battery measurements.

Run `python -m cost_model.calculate_d6`. This is stdlib-only and offline. The
source fields in battery_inputs.json identify the raw D5(b) records used for
each 55-trial selection. Monetary values are baseline list-price calculations,
not a model's estimate of its own usage.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "cost_model" / "battery_inputs.json"
OUTPUT = ROOT / "cost_model" / "d6_results.json"


def calculate() -> dict:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    failure_cost = data["failure_cost_usd"]
    volume = data["monthly_claims"]
    fixed_monthly = data["monthly_fixed_provider_fees_usd_measured"]
    results = []

    for row in data["models"]:
        assert row["ordinary_trials"] == 25 and row["negative_trials"] == 30
        assert 0 <= row["ordinary_passed"] <= 25
        assert 0 <= row["negative_passed"] <= 30
        trials = row["ordinary_trials"] + row["negative_trials"]
        passed = row["ordinary_passed"] + row["negative_passed"]
        rate = passed / trials
        token_cost_total = (
            row["prompt_tokens"] * row["input_usd_per_million"]
            + row["completion_tokens"] * row["output_usd_per_million"]
        ) / 1_000_000
        layer_1 = token_cost_total / trials
        layer_2 = (1 - rate) * failure_cost
        task_cost = layer_1 + layer_2
        sensitivity = []
        for shift in (-0.10, 0, 0.10):
            shifted_rate = max(0, min(1, rate + shift))
            shifted_task_cost = layer_1 + (1 - shifted_rate) * failure_cost
            sensitivity.append(
                {
                    "pass_rate": round(shifted_rate, 6),
                    "cost_per_task_usd": round(shifted_task_cost, 6),
                    "monthly_usd": round(shifted_task_cost * volume + fixed_monthly, 2),
                }
            )
        results.append(
            {
                "model_id": row["model_id"],
                "prompt_version": row["prompt_version"],
                "source": row["source"],
                "trials": trials,
                "passed": passed,
                "ordinary_passed": row["ordinary_passed"],
                "negative_passed": row["negative_passed"],
                "pass_rate": round(rate, 6),
                "prompt_tokens": row["prompt_tokens"],
                "completion_tokens": row["completion_tokens"],
                "token_cost_total_usd": round(token_cost_total, 6),
                "layer_1_per_task_usd": round(layer_1, 6),
                "layer_2_per_task_usd": round(layer_2, 6),
                "all_in_per_task_usd": round(task_cost, 6),
                "monthly_usd": round(task_cost * volume + fixed_monthly, 2),
                "sensitivity_plus_minus_10pp": sensitivity,
            }
        )

    def find(model_id: str, prompt_version: str) -> dict:
        return next(
            row for row in results
            if row["model_id"] == model_id and row["prompt_version"] == prompt_version
        )

    mistral_id = "mistralai/mistral-small-3.2-24b-instruct"
    mistral_v2 = find(mistral_id, "v2-final")
    mistral_v1 = find(mistral_id, "v1")
    gpt = find("openai/gpt-4.1-mini", "v2-final")
    cheap_call = mistral_v2["token_cost_total_usd"] / mistral_v2["trials"]
    expensive_all_in = gpt["all_in_per_task_usd"]
    break_even = 1 - (expensive_all_in - cheap_call) / failure_cost

    return {
        "monthly_claims": volume,
        "failure_cost_usd": failure_cost,
        "fixed_monthly_provider_fees_usd_measured": fixed_monthly,
        "manual_monthly_usd": round(failure_cost * volume, 2),
        "models": results,
        "mistral_v1_to_v2": {
            "pass_rate_gain_percentage_points": round(
                100 * (mistral_v2["pass_rate"] - mistral_v1["pass_rate"]), 2
            ),
            "all_in_cost_saved_per_task_usd": round(
                mistral_v1["all_in_per_task_usd"] - mistral_v2["all_in_per_task_usd"], 6
            ),
        },
        "mistral_vs_gpt_break_even": {
            "cheap_token_only_usd": round(cheap_call, 6),
            "expensive_all_in_usd": expensive_all_in,
            "required_cheap_pass_rate": round(break_even, 6),
            "mistral_shortfall_percentage_points": round(
                100 * (break_even - mistral_v2["pass_rate"]), 2
            ),
        },
    }


if __name__ == "__main__":
    result = calculate()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    for row in result["models"]:
        print(
            f"{row['model_id']} {row['prompt_version']}: "
            f"{row['passed']}/{row['trials']} pass, "
            f"USD {row['all_in_per_task_usd']:.6f}/task"
        )
