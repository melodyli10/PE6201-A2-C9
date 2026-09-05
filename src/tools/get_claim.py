"""Entry point. Pulls the claim and every line item. The only tool callable on turn 1 -
nothing else has a member_id, hospital_id or lines[] until this returns."""

from src import data_store


def get_claim(claim_id: str) -> dict:
    claim = data_store.find_claim(claim_id)
    if claim is None:
        return {"error": f"no claim found for claim_id={claim_id!r}"}
    return dict(claim)
