"""Reproduce D6's tool-block and observation-size token measurements.

Run from the repository root with `python -m cost_model.measure_d6_ledger` after
installing tiktoken 0.14.0. This does not use an API key or make a model call.
The same explicit tokenizer and compact JSON serialization are used for both
sides of each comparison. These counts are local measurements of the payload,
not claims about a provider's billed token count.
"""

from __future__ import annotations

import ast
import importlib.metadata
import json
import subprocess
from pathlib import Path

import tiktoken

from src.tools import TOOL_SCHEMAS
from src.tools.get_preauthorisation import (
    get_preauthorisation,
    get_preauthorisation_v2,
)


ROOT = Path(__file__).resolve().parents[1]
BEFORE_COMMIT = "8f8da38"
ENCODING = "o200k_base"
CASES = (
    ("valid", "M-2214", "62480", "2026-09-01"),
    ("expired", "M-6118", "29881", "2026-09-01"),
    ("missing", "M-9999", "99999", "2026-09-01"),
    ("invalid_date", "M-2214", "62480", "not-a-date"),
)


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def old_schemas() -> list[dict]:
    source = subprocess.run(
        ["git", "show", f"{BEFORE_COMMIT}:src/tools/__init__.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "TOOL_SCHEMAS"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise RuntimeError("TOOL_SCHEMAS missing from before commit")


def measure() -> dict:
    encoder = tiktoken.get_encoding(ENCODING)
    count = lambda value: len(encoder.encode(compact_json(value)))
    before = old_schemas()
    after = TOOL_SCHEMAS
    before_names = [item["function"]["name"] for item in before]
    after_names = [item["function"]["name"] for item in after]
    assert len(before) == 8 and len(after) == 7
    assert [name for name in before_names if name != "get_preauthorisation"] == after_names

    observations = []
    for name, member_id, procedure_code, date_of_service in CASES:
        arguments = dict(
            member_id=member_id,
            procedure_code=procedure_code,
            date_of_service=date_of_service,
        )
        old_result = get_preauthorisation(**arguments)
        new_result = get_preauthorisation_v2(**arguments)
        observations.append(
            {
                "case": name,
                "v1_tokens": count(old_result),
                "v2_tokens": count(new_result),
                "v1_payload": old_result,
                "v2_payload": new_result,
            }
        )

    block_before = count(before)
    block_after = count(after)
    return {
        "method": {
            "tokenizer": f"tiktoken {importlib.metadata.version('tiktoken')} / {ENCODING}",
            "serialization": "json.dumps(ensure_ascii=False, separators=(',', ':'))",
            "scope": "local token count of serialized schemas/observations; not API billing",
        },
        "B_tool_block": {
            "before_commit": BEFORE_COMMIT,
            "before_tools": before_names,
            "after_tools": after_names,
            "before_tokens": block_before,
            "after_tokens": block_after,
            "saved_tokens_per_turn": block_before - block_after,
            "saved_percent": round(100 * (block_before - block_after) / block_before, 2),
        },
        "D_preauthorisation_observation": {
            "cases": observations,
            "v1_total_tokens": sum(row["v1_tokens"] for row in observations),
            "v2_total_tokens": sum(row["v2_tokens"] for row in observations),
            "v1_average_tokens": sum(row["v1_tokens"] for row in observations) / len(observations),
            "v2_average_tokens": sum(row["v2_tokens"] for row in observations) / len(observations),
        },
    }


if __name__ == "__main__":
    result = measure()
    output = ROOT / "cost_model" / "ledger_measurements.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(compact_json({"B": result["B_tool_block"], "D": result["D_preauthorisation_observation"]}))
