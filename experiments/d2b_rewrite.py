import json

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
