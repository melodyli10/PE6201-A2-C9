import json
import os
import sys

# Let this run either as `python experiments/d2b_rewrite.py` or as
# `python -m experiments.d2b_rewrite` - both need the repo root on sys.path
# for `from src...` to resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.get_preauthorisation import (
    get_preauthorisation,
    get_preauthorisation_v2,
)


def est_tokens(value):
    return max(1, len(json.dumps(value)) // 4)


cases = [
    {
        "name": "valid",
        "member_id": "M-2214",
        "procedure_code": "62480",
        "date_of_service": "2026-09-01",
    },
    {
        "name": "expired",
        "member_id": "M-6118",
        "procedure_code": "29881",
        "date_of_service": "2026-09-01",
    },
    {
        "name": "missing",
        "member_id": "M-9999",
        "procedure_code": "99999",
        "date_of_service": "2026-09-01",
    },
    {
        "name": "invalid_date",
        "member_id": "M-2214",
        "procedure_code": "62480",
        "date_of_service": "not-a-date",
    },
]

guardrail_cases = [
    {
        "name": "wrong_separator",
        "member_id": "M-2214",
        "procedure_code": "62480",
        "date_of_service": "2026/09/01",
    },
    {
        "name": "impossible_date",
        "member_id": "M-2214",
        "procedure_code": "62480",
        "date_of_service": "2026-02-30",
    },
    {
        "name": "free_text_date",
        "member_id": "M-2214",
        "procedure_code": "62480",
        "date_of_service": "September 1 2026",
    },
]

for case in cases:
    name = case.pop("name")

    v1_result = get_preauthorisation(**case)
    v2_result = get_preauthorisation_v2(**case)
    
    v1_tokens = est_tokens(v1_result)
    v2_tokens = est_tokens(v2_result)

    print(f"\nCASE: {name}")
    print("V1:", json.dumps(v1_result))
    print("V1 tokens:", v1_tokens)
    print("V2:", json.dumps(v2_result))
    print("V2 tokens:", v2_tokens)

print("\nGUARDRAIL CASES")

v1_guardrail_passed = 0
v2_guardrail_passed = 0

for case in guardrail_cases:
    name = case["name"]
    args = {k: v for k, v in case.items() if k != "name"}

    v1_result = get_preauthorisation(**args)
    v2_result = get_preauthorisation_v2(**args)

    v1_pass = "error" in v1_result
    v2_pass = v2_result.get("status") == "invalid_date"

    v1_guardrail_passed += int(v1_pass)
    v2_guardrail_passed += int(v2_pass)

    print(f"{name}: V1={'PASS' if v1_pass else 'FAIL'}, V2={'PASS' if v2_pass else 'FAIL'}")

print(f"V1 guardrail cases passed: {v1_guardrail_passed}/{len(guardrail_cases)}")
print(f"V2 guardrail cases passed: {v2_guardrail_passed}/{len(guardrail_cases)}")
