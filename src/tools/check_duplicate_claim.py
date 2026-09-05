"""Resubmission check against decided_claims.json. Matching is on facts, never claim_id -
a resubmission arrives with a new id - and it matches on ALL FOUR: member, hospital, date
of service and lines. Three of the shipped decided_claims rows are near-misses that differ
on exactly one fact, specifically to punish a shortcut match."""

from src import data_store


def _line_signature(lines: list[dict]) -> frozenset:
    return frozenset((line["code"], line["amount"]) for line in lines)


def check_duplicate_claim(member_id: str, hospital_id: str, date_of_service: str, lines: list[dict]) -> dict:
    signature = _line_signature(lines)
    for decided in data_store.all_decided_claims():
        if (
            decided["member_id"] == member_id
            and decided["hospital_id"] == hospital_id
            and decided["date_of_service"] == date_of_service
            and _line_signature(decided["lines"]) == signature
        ):
            return {
                "duplicate": True,
                "matched_claim_id": decided["claim_id"],
                "matched_facts": ["member_id", "hospital_id", "date_of_service", "lines"],
                "prior_decision": decided["decision"],
                "decided_on": decided["decided_on"],
            }
    return {"duplicate": False}
