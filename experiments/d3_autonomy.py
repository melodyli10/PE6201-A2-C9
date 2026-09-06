import os
import tempfile

from src.tools import issue_decision_letter as decision_tool


# Use a temporary file so this test does not write into the real decisions.jsonl.
temp_dir = tempfile.mkdtemp()
decision_tool.DECISIONS_PATH = os.path.join(temp_dir, "decisions.jsonl")

claim_id = "TEST-AUTONOMY-001"

base_args = {
    "claim_id": claim_id,
    "decision": "escalate",
    "reason": "Autonomy guardrail test",
    "evidence": ["test"],
    "autonomy": "confirm",
}

# Case 1: no operator approval -> must be blocked.
blocked_result = decision_tool.issue_decision_letter(**base_args)

# Case 2: operator approval exists -> write is allowed.
decision_tool.approve(claim_id)
approved_result = decision_tool.issue_decision_letter(**base_args)

print("Without approval:", blocked_result)
print("After approval:", approved_result)
