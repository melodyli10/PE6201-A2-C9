"""The tool registry: every tool the loop may call, plus the OpenAI-compatible schema
each one is described by for native tool-calling. Flat, no sub-grouping, per the brief."""

from src.tools.check_coverage import check_coverage
from src.tools.check_duplicate_claim import check_duplicate_claim
from src.tools.get_claim import get_claim
from src.tools.get_hospital_status import get_hospital_status
from src.tools.get_preauthorisation import get_preauthorisation
from src.tools.issue_decision_letter import issue_decision_letter
from src.tools.lookup_policy import lookup_policy

TOOL_FUNCTIONS = {
    "get_claim": get_claim,
    "lookup_policy": lookup_policy,
    "check_coverage": check_coverage,
    "get_preauthorisation": get_preauthorisation,
    "get_hospital_status": get_hospital_status,
    "check_duplicate_claim": check_duplicate_claim,
    "issue_decision_letter": issue_decision_letter,
}

# OpenAI-compatible tool schemas - full six-field descriptor writeups (D2b) live in docs/,
# this is only the JSON shape the model/API actually needs to call a tool.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_claim",
            "description": "Fetch a claim and its line items by claim_id. Entry point - call this first, alone.",
            "parameters": {
                "type": "object",
                "properties": {"claim_id": {"type": "string"}},
                "required": ["claim_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_policy",
            "description": "Member -> policy join. Returns status, dates, annual_limit, used_to_date, exclusions.",
            "parameters": {
                "type": "object",
                "properties": {"member_id": {"type": "string"}},
                "required": ["member_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_coverage",
            "description": "Per-line coverage/exclusion check for one procedure code under one policy. Returns requires_preauth.",
            "parameters": {
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string"},
                    "procedure_code": {"type": "string"},
                },
                "required": ["policy_id", "procedure_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_preauthorisation",
            "description": "Call ONLY when check_coverage reported requires_preauth=true for that line. An expired match is not a valid one.",
            "parameters": {
                "type": "object",
                "properties": {
                    "member_id": {"type": "string"},
                    "procedure_code": {"type": "string"},
                    "date_of_service": {"type": "string"},
                },
                "required": ["member_id", "procedure_code", "date_of_service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hospital_status",
            "description": "Panel lookup against the insurer's own hospital table.",
            "parameters": {
                "type": "object",
                "properties": {"hospital_id": {"type": "string"}},
                "required": ["hospital_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_duplicate_claim",
            "description": "Checks whether this claim is a resubmission of an already-decided claim. Matches on member_id, hospital_id, date_of_service AND lines - all four, never claim_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "member_id": {"type": "string"},
                    "hospital_id": {"type": "string"},
                    "date_of_service": {"type": "string"},
                    "lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "amount": {"type": "number"},
                            },
                        },
                    },
                },
                "required": ["member_id", "hospital_id", "date_of_service", "lines"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_decision_letter",
            "description": "The gated action. Records the first-response decision on a claim. Call at most once, only after the facts are established.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "decision": {
                        "type": "string",
                        "enum": ["approve_in_principle", "request_document", "escalate"],
                    },
                    "reason": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "The tool names you actually called, in the order you called them - "
                            "not a narrative. Repeat a name with a count if called more than once. "
                            "Example: [\"get_claim\", \"lookup_policy\", \"check_coverage x3\", "
                            "\"get_preauthorisation\", \"get_hospital_status\"]. Do not describe "
                            "what each call found here - that belongs in `reason`."
                        ),
                    },
                    "trigger": {
                        "type": "string",
                        "enum": [
                            "policy_lapsed",
                            "outside_policy_dates",
                            "annual_limit_exceeded",
                            "duplicate_claim",
                            "instruction_in_member_narrative",
                        ],
                        "description": "escalate only - the one reason, exactly one of these five names.",
                    },
                    "missing": {"type": "string", "description": "request_document only - the one named thing"},
                    "escalate_to": {"type": "string"},
                    "lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "amount": {"type": "number"},
                                "status": {"type": "string"},
                                "exclusion": {"type": ["string", "null"]},
                            },
                        },
                    },
                    "approved_total": {"type": "number"},
                    "refused_total": {"type": "number"},
                    "settlement_basis": {
                        "type": "string",
                        "enum": ["direct", "reimbursement"],
                        "description": "approve_in_principle only - direct if the hospital is on panel, reimbursement if not.",
                    },
                },
                "required": ["claim_id", "decision", "reason", "evidence"],
            },
        },
    },
]
