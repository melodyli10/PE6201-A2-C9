"""Member -> policy join. Returns status, dates, annual_limit, used_to_date, exclusions -
everything needed for the policy_lapsed / outside_policy_dates / annual_limit_exceeded gates."""

from src import data_store


def lookup_policy(member_id: str) -> dict:
    member = data_store.find_member(member_id)
    if member is None:
        return {"error": f"no member found for member_id={member_id!r}"}
    policy = data_store.find_policy(member["policy_id"])
    if policy is None:
        return {"error": f"member {member_id!r} points at policy_id={member['policy_id']!r}, which does not exist"}
    return dict(policy)
