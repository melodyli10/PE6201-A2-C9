"""Called ONLY when check_coverage said requires_preauth=true for that line. Matches on
member_id + procedure_code, then the date of service must fall inside valid_from..valid_to -
an authorisation that exists but expired before treatment is not a valid one."""

from src import data_store
from datetime import date


def get_preauthorisation(member_id: str, procedure_code: str, date_of_service: str) -> dict:
        try:
        date.fromisoformat(date_of_service)
    except (TypeError, ValueError):
        return {
            "error": "date_of_service must be a valid ISO date in YYYY-MM-DD format"
        }    
        candidates = data_store.preauthorisations_for(member_id, procedure_code)
    if not candidates:
        return {
            "found": False,
            "valid": False,
            "reason": f"no pre-authorisation on file for member {member_id!r}, procedure {procedure_code!r}",
        }

    for pa in candidates:
        if pa["valid_from"] <= date_of_service <= pa["valid_to"]:
            return {
                "found": True,
                "valid": True,
                "preauth_id": pa["preauth_id"],
                "valid_from": pa["valid_from"],
                "valid_to": pa["valid_to"],
            }

    # Found one or more, but none cover this date of service - report the closest miss.
    pa = candidates[0]
    if date_of_service > pa["valid_to"]:
        reason = f"{pa['preauth_id']} validity ended {pa['valid_to']}, before date of service {date_of_service}"
    else:
        reason = f"{pa['preauth_id']} validity starts {pa['valid_from']}, after date of service {date_of_service}"
    return {
        "found": True,
        "valid": False,
        "preauth_id": pa["preauth_id"],
        "valid_from": pa["valid_from"],
        "valid_to": pa["valid_to"],
        "reason": reason,
    }

def get_preauthorisation_v2(
    member_id: str,
    procedure_code: str,
    date_of_service: str,
) -> dict:
    try:
        date.fromisoformat(date_of_service)
    except (TypeError, ValueError):
        return {"status": "invalid_date"}

    candidates = data_store.preauthorisations_for(member_id, procedure_code)

    if not candidates:
        return {"status": "missing"}

    for pa in candidates:
        if pa["valid_from"] <= date_of_service <= pa["valid_to"]:
            return {
                "status": "valid",
                "preauth_id": pa["preauth_id"],
            }

    return {"status": "invalid"}
