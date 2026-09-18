"""Audit D6's committed aggregates against the original D5 trial records.

Run `python -m cost_model.verify_d6_inputs` in a git checkout after fetching
the team branches. The arithmetic itself can always be reproduced offline
from battery_inputs.json with calculate_d6.py, including in a folder copy
without git metadata.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "cost_model" / "battery_inputs.json"
OUTPUT = ROOT / "cost_model" / "source_audit.json"


def read_source(location: str) -> list[dict]:
    if ":" in location:
        revision, path = location.split(":", 1)
        content = subprocess.run(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "show", f"{revision}:{path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout
    else:
        content = (ROOT / location).read_text(encoding="utf-8")
    return [json.loads(line) for line in content.splitlines() if line.strip()]


def audit() -> dict:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    audited = []
    mistral_pairs = {}
    for expected in data["models"]:
        rows = [row for row in read_source(expected["source"]) if row["trial"] <= 3]
        ordinary = [row for row in rows if row["case_type"] == "ordinary"]
        negative = [row for row in rows if row["case_type"] == "negative"]
        measured = {
            "ordinary_trials": len(ordinary),
            "negative_trials": len(negative),
            "ordinary_passed": sum(row["passed"] is True for row in ordinary),
            "negative_passed": sum(row["passed"] is True for row in negative),
            "prompt_tokens": sum(row["prompt_tokens"] for row in rows),
            "completion_tokens": sum(row["completion_tokens"] for row in rows),
        }
        for field, value in measured.items():
            assert expected[field] == value, (expected["model_id"], field, value)
        assert len(rows) == 55 and len({row["case_id"] for row in rows}) == 35
        pairs = {(row["case_id"], row["trial"]) for row in rows}
        assert len(pairs) == len(rows)
        if expected["family"] == "Mistral":
            mistral_pairs[expected["prompt_version"]] = pairs
        audited.append(
            {
                "model_id": expected["model_id"],
                "prompt_version": expected["prompt_version"],
                "source": expected["source"],
                "case_count": 35,
                "trial_count": 55,
                "aggregates_match": True,
            }
        )
    assert mistral_pairs["v1"] == mistral_pairs["v2-final"]
    return {"sources": audited, "mistral_v1_v2_case_trial_pairs_match": True}


if __name__ == "__main__":
    result = audit()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(result['sources'])} live sources; wrote {OUTPUT}")
