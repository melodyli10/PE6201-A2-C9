"""Loads data_A/*.json once and indexes it by id. Every tool reads through this -
none of them touch the filesystem directly."""

import json
import os
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_A")


def _load(name: str) -> list[dict]:
    with open(os.path.join(DATA_DIR, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def _tables() -> dict[str, list[dict]]:
    names = [
        "claims", "members", "policies", "hospitals", "procedures",
        "preauthorisations", "required_documents", "decided_claims",
    ]
    return {name: _load(name) for name in names}


def _index_by(table: str, key: str) -> dict:
    return {row[key]: row for row in _tables()[table]}


def find_claim(claim_id: str) -> dict | None:
    return _index_by("claims", "claim_id").get(claim_id)


def find_member(member_id: str) -> dict | None:
    return _index_by("members", "member_id").get(member_id)


def find_policy(policy_id: str) -> dict | None:
    return _index_by("policies", "policy_id").get(policy_id)


def find_hospital(hospital_id: str) -> dict | None:
    return _index_by("hospitals", "hospital_id").get(hospital_id)


def find_procedure(code: str) -> dict | None:
    return _index_by("procedures", "code").get(code)


def preauthorisations_for(member_id: str, procedure_code: str) -> list[dict]:
    return [
        row for row in _tables()["preauthorisations"]
        if row["member_id"] == member_id and row["procedure_code"] == procedure_code
    ]


def required_document_for(procedure_code: str) -> str | None:
    for row in _tables()["required_documents"]:
        if row["procedure_code"] == procedure_code:
            return row["document"]
    return None


def all_decided_claims() -> list[dict]:
    return _tables()["decided_claims"]
