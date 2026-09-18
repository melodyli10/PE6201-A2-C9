"""Per-line coverage/exclusion check. Surfaces requires_preauth so the loop knows whether
to chase a pre-authorisation next - this is the single flag that varies turn count."""

from src import data_store


def check_coverage(policy_id: str, procedure_code: str) -> dict:
    policy = data_store.find_policy(policy_id)
    if policy is None:
        return {"error": f"no policy found for policy_id={policy_id!r}"}
    procedure = data_store.find_procedure(procedure_code)
    if procedure is None:
        return {"error": f"no procedure found for procedure_code={procedure_code!r}"}

    exclusion = next(
        (ex for ex in policy.get("exclusions", []) if ex["code"] == procedure_code), None
    )
    if exclusion is not None:
        return {
            "procedure_code": procedure_code,
            "covered": False,
            "exclusion_rule": exclusion["rule"],
            "requires_preauth": False,
        }
    return {
        "procedure_code": procedure_code,
        "covered": True,
        "exclusion_rule": None,
        "requires_preauth": bool(procedure.get("requires_preauth")),
    }
