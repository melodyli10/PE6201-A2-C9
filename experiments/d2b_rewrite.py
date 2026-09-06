import json

from src.tools.get_preauthorisation import (
    get_preauthorisation,
    get_preauthorisation_v2,
)
case = {
    "member_id": "M-2214",
    "procedure_code": "62480",
    "date_of_service": "2026-09-01",
}

v1_result = get_preauthorisation(**case)
v2_result = get_preauthorisation_v2(**case)

print("V1:", json.dumps(v1_result))
print("V2:", json.dumps(v2_result))
