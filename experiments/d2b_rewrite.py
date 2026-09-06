import json

from src.tools.get_preauthorisation import (
    get_preauthorisation,
    get_preauthorisation_v2,
)
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

    print(f"\nCASE: {name}")
    print("V1:", json.dumps(v1_result))
    print("V2:", json.dumps(v2_result))
