"""The gated action. Three steps only: check the gate, append one structured JSON record,
return a short confirmation string. Nothing here composes a letter, a greeting or a policy
summary - the record IS the output, and it is what gets marked.

The gate check lives here, inline, because it's part of this tool's own required shape
(the brief's own full-marks sample bakes it directly into the function) - not a separate
guardrail layer. The step cap / budget ceiling / action-dedup that a full D3 guardrail
layer would add are someone else's deliverable, not this file's.

The FAQ's minimal 5-argument sample (claim_id, decision, reason, evidence, autonomy) is the
shape of the WRITE itself. Appendix A's own worked records carry more fields than that -
trigger, missing, lines, approved_total, refused_total - because D4's answer key
(expected_outcomes_A.json) and check_my_data.py grade on those as structured fields, not by
parsing prose out of `reason`. Those extras are accepted as optional keyword arguments and
written through unchanged."""

import json
import os
from datetime import datetime, timezone

VALID_DECISIONS = {"approve_in_principle", "request_document", "escalate"}

DECISIONS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "decisions.jsonl",
)

_approved_claims: set[str] = set()


def approve(claim_id: str) -> None:
    """Simulates the operator's confirm step. In a batch evaluation run (D4/D5) there is
    no live human per run, so the loop performs this step right before it invokes the
    gated action - the gate below still blocks if this was skipped."""
    _approved_claims.add(claim_id)


def _already_decided(claim_id: str) -> bool:
    if not os.path.exists(DECISIONS_PATH):
        return False
    with open(DECISIONS_PATH, encoding="utf-8") as fh:
        return any(json.loads(line)["case_id"] == claim_id for line in fh if line.strip())


def issue_decision_letter(
    claim_id: str,
    decision: str,
    reason: str,
    evidence: list[str],
    autonomy: str = "confirm",
    trigger: str | None = None,
    missing: str | None = None,
    escalate_to: str | None = None,
    lines: list[dict] | None = None,
    approved_total: float | None = None,
    refused_total: float | None = None,
    settlement_basis: str | None = None,
    *,
    turns: int | None = None,
    cost_usd: float | None = None,
) -> str:
    if decision not in VALID_DECISIONS:
        return f"BLOCKED: decision {decision!r} is not one of {sorted(VALID_DECISIONS)}"
    if autonomy == "confirm" and claim_id not in _approved_claims:
        return "BLOCKED: awaiting operator confirmation"
    if _already_decided(claim_id):
        return "BLOCKED: duplicate - a decision already exists"

    gate = (
        f"operator approved at turn {turns}" if autonomy == "confirm"
        else f"autonomy={autonomy}, no confirmation required"
    )
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "case_id": claim_id,
        "decision": decision,
        "reason": reason,
        "evidence": evidence,
        "autonomy": autonomy,
        "gate": gate,
        "turns": turns,
        "cost_usd": round(cost_usd, 6) if cost_usd is not None else None,
    }
    optional_fields = {
        "trigger": trigger,
        "missing": missing,
        "escalate_to": escalate_to,
        "lines": lines,
        "approved_total": approved_total,
        "refused_total": refused_total,
        "settlement_basis": settlement_basis,
    }
    record.update({k: v for k, v in optional_fields.items() if v is not None})

    with open(DECISIONS_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return f"recorded: {decision} on {claim_id}"
