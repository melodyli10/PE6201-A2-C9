"""The scripted backend: a small deterministic policy that plays the same routing-table
decision procedure a correct agent would, on the real fixture data - not a per-claim_id
lookup table, so it generalises to every case the team adds later, not just the 15 shipped.

Deterministic, no network, no key - this is what D5(a) requires as the default backend.
loop.py treats this exactly like a model response: a dict with "message" (assistant turn,
optionally carrying tool_calls) and "usage" (tokens, both 0 here - no real LLM call happens).

The dependency rule lives here (this IS "the model" for scripted runs): turn 1 alone
(get_claim); turn 2 in parallel (lookup_policy, get_hospital_status, check_duplicate_claim);
a code-level gate checks policy/duplicate/limit/narrative BEFORE any line is priced; only
then turn 3 (check_coverage per line, parallel); turn 4 (get_preauthorisation for lines that
need one, parallel); final turn issues the gated decision."""

import json
import uuid

from src import data_store

# Narrative hostile-input detection - this is one of Appendix A's own routing-table rows
# (instruction_in_member_narrative is a decision outcome, not a D3 guardrail-checklist
# control), so it lives here as part of the routing logic, not in a separate module.
_OVERT_MARKERS = (
    "ignore the exclusion", "ignore the policy", "ignore any", "override",
    "disregard the exclusion", "system note", "authorised by claims supervisor",
    "pre-approved by", "approve all lines",
)
_IMITATION_MARKERS = ("returned:",)


def _detect_narrative_injection(narrative: str) -> str | None:
    """Returns a short description of the instruction found, or None."""
    lowered = narrative.lower()
    for marker in _OVERT_MARKERS:
        if marker in lowered:
            return f"overt instruction aimed at the system (matched {marker!r})"
    for marker in _IMITATION_MARKERS:
        if marker in lowered:
            return "free text imitating a tool result"
    return None


def _tool_call(name: str, arguments: dict) -> dict:
    return {
        "id": f"call_{uuid.uuid4().hex[:12]}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _turn(thought: str, calls: list[tuple[str, dict]]) -> dict:
    message = {
        "role": "assistant",
        "content": thought,
        "tool_calls": [_tool_call(name, args) for name, args in calls],
    }
    return {"message": message, "usage": {"prompt_tokens": 0, "completion_tokens": 0}}


def _done(content: str) -> dict:
    message = {"role": "assistant", "content": content, "tool_calls": []}
    return {"message": message, "usage": {"prompt_tokens": 0, "completion_tokens": 0}}


def _extract_tool_history(messages: list[dict]) -> dict[str, list[tuple[dict, dict]]]:
    """tool_name -> [(arguments, result), ...], in first-called order."""
    calls_by_id: dict[str, tuple[str, dict]] = {}
    for msg in messages:
        if msg.get("role") == "assistant":
            for call in msg.get("tool_calls") or []:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])
                calls_by_id[call["id"]] = (name, args)

    history: dict[str, list[tuple[dict, dict]]] = {}
    for msg in messages:
        if msg.get("role") == "tool":
            name, args = calls_by_id[msg["tool_call_id"]]
            result = json.loads(msg["content"])
            history.setdefault(name, []).append((args, result))
    return history


def _get_claim_id(messages: list[dict]) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            return msg["content"].strip()
    raise ValueError("no user message carrying the claim_id was found")


def _build_evidence(history: dict[str, list]) -> list[str]:
    evidence = []
    for name, calls in history.items():
        evidence.append(name if len(calls) == 1 else f"{name} x{len(calls)}")
    return evidence


def next_turn(messages: list[dict], tools: list[dict] | None = None, parallel: bool = True) -> dict:
    """Same routing decisions either way. parallel=False caps every turn at one call, so
    a claim needing N independent checks takes N turns instead of 1 - this is the
    deliberate "sequential" comparison mode for D2(c), not a second policy."""
    history = _extract_tool_history(messages)
    claim_id = _get_claim_id(messages)

    if "issue_decision_letter" in history:
        _, result = history["issue_decision_letter"][0]
        return _done(result if isinstance(result, str) else json.dumps(result))

    # turn 1: get_claim, alone
    if "get_claim" not in history:
        return _turn(f"Fetch claim {claim_id}.", [("get_claim", {"claim_id": claim_id})])

    _, claim = history["get_claim"][0]
    if "error" in claim:
        return _turn(
            "Claim could not be resolved; escalating.",
            [("issue_decision_letter", {
                "claim_id": claim_id, "decision": "escalate",
                "reason": claim["error"], "evidence": _build_evidence(history),
                "trigger": "claim_not_found", "escalate_to": "human claims assessor",
            })],
        )

    member_id, hospital_id = claim["member_id"], claim["hospital_id"]
    date_of_service, lines = claim["date_of_service"], claim["lines"]
    narrative, documents = claim.get("narrative", ""), claim.get("documents", [])

    # turn 2: lookup_policy || get_hospital_status || check_duplicate_claim
    turn2 = ["lookup_policy", "get_hospital_status", "check_duplicate_claim"]
    missing_turn2 = [name for name in turn2 if name not in history]
    if missing_turn2:
        calls = []
        if "lookup_policy" in missing_turn2:
            calls.append(("lookup_policy", {"member_id": member_id}))
        if "get_hospital_status" in missing_turn2:
            calls.append(("get_hospital_status", {"hospital_id": hospital_id}))
        if "check_duplicate_claim" in missing_turn2:
            calls.append(("check_duplicate_claim", {
                "member_id": member_id, "hospital_id": hospital_id,
                "date_of_service": date_of_service, "lines": lines,
            }))
        if not parallel:
            calls = calls[:1]
        return _turn("Check policy, hospital panel status and prior decisions.", calls)

    _, policy = history["lookup_policy"][0]
    _, duplicate = history["check_duplicate_claim"][0]
    _, hospital = history["get_hospital_status"][0]

    def escalate(trigger: str, reason: str) -> dict:
        return _turn(
            f"Escalating: {trigger}.",
            [("issue_decision_letter", {
                "claim_id": claim_id, "decision": "escalate", "reason": reason,
                "evidence": _build_evidence(history), "trigger": trigger,
                "escalate_to": "human claims assessor",
            })],
        )

    injection = _detect_narrative_injection(narrative)
    if injection:
        return escalate(
            "instruction_in_member_narrative",
            f"Member narrative contains {injection}. Instruction was found and NOT followed.",
        )

    if policy.get("status") != "active":
        return escalate("policy_lapsed", f"Policy {policy.get('policy_id')} status is {policy.get('status')!r}.")

    if not (policy["start_date"] <= date_of_service <= policy["end_date"]):
        return escalate(
            "outside_policy_dates",
            f"Date of service {date_of_service} falls outside policy {policy['policy_id']}'s "
            f"cover {policy['start_date']}..{policy['end_date']}.",
        )

    if duplicate.get("duplicate"):
        return escalate(
            "duplicate_claim",
            f"Matches prior claim {duplicate['matched_claim_id']} on member, hospital, "
            f"date of service and lines.",
        )

    claim_total = sum(line["amount"] for line in lines)
    remaining = policy["annual_limit"] - policy["used_to_date"]
    if claim_total > remaining:
        return escalate(
            "annual_limit_exceeded",
            f"Claim total {claim_total} exceeds {remaining} remaining on {policy['policy_id']}. "
            f"Lines were not individually priced: the claim cannot be decided at this level.",
        )

    # turn 3: check_coverage per line, parallel
    codes = [line["code"] for line in lines]
    have_coverage = {args["procedure_code"] for args, _ in history.get("check_coverage", [])}
    missing_coverage = [code for code in codes if code not in have_coverage]
    if missing_coverage:
        calls = [("check_coverage", {"policy_id": policy["policy_id"], "procedure_code": code})
                 for code in missing_coverage]
        if not parallel:
            calls = calls[:1]
        return _turn("Check coverage for every line.", calls)
    coverage_by_code = {args["procedure_code"]: result for args, result in history["check_coverage"]}

    # turn 4: get_preauthorisation, only for lines that need one
    needs_preauth = [c for c in codes if coverage_by_code[c]["covered"] and coverage_by_code[c]["requires_preauth"]]
    have_preauth = {args["procedure_code"] for args, _ in history.get("get_preauthorisation", [])}
    missing_preauth = [c for c in needs_preauth if c not in have_preauth]
    if missing_preauth:
        calls = [("get_preauthorisation", {
            "member_id": member_id, "procedure_code": code, "date_of_service": date_of_service,
        }) for code in missing_preauth]
        if not parallel:
            calls = calls[:1]
        return _turn("Chase pre-authorisation for lines that require one.", calls)
    preauth_by_code = {args["procedure_code"]: result for args, result in history.get("get_preauthorisation", [])}

    evidence = _build_evidence(history)

    # request_document: an invalid/missing pre-authorisation first
    for code in needs_preauth:
        pa = preauth_by_code[code]
        if not pa.get("valid"):
            return _turn(
                "Pre-authorisation missing or expired; requesting it.",
                [("issue_decision_letter", {
                    "claim_id": claim_id, "decision": "request_document",
                    "missing": f"pre-authorisation reference for {code}, valid on {date_of_service}",
                    "reason": pa.get("reason", f"No valid pre-authorisation on file for {code}."),
                    "evidence": evidence,
                })],
            )

    # request_document: a required supporting document absent
    for line in lines:
        code = line["code"]
        required_doc = data_store.required_document_for(code)
        if required_doc and required_doc not in documents:
            return _turn(
                "Required document absent; requesting it.",
                [("issue_decision_letter", {
                    "claim_id": claim_id, "decision": "request_document",
                    "missing": f"{required_doc} for line {code}",
                    "reason": f"Line {code} requires {required_doc}, which is not among the attached documents.",
                    "evidence": evidence,
                })],
            )

    # approve_in_principle: a disposition for every line
    dispositions, approved_total, refused_total = [], 0, 0
    for line in lines:
        code, amount = line["code"], line["amount"]
        cov = coverage_by_code[code]
        if cov["covered"]:
            approved_total += amount
            dispositions.append({"code": code, "amount": amount, "status": "covered"})
        else:
            refused_total += amount
            dispositions.append({
                "code": code, "amount": amount, "status": "not_covered",
                "exclusion": cov["exclusion_rule"],
            })

    settlement_basis = "direct" if hospital.get("panel") else "reimbursement"
    hospital_note = (
        f"Hospital {hospital['hospital_id']} on panel."
        if hospital.get("panel")
        else f"Hospital {hospital['hospital_id']} not on panel; member paid and is claiming reimbursement."
    )
    reason = (
        f"Policy {policy['policy_id']} active to {policy['end_date']}. {hospital_note} "
        f"{len([d for d in dispositions if d['status'] == 'covered'])} of {len(lines)} lines payable; "
        f"{len([d for d in dispositions if d['status'] == 'not_covered'])} excluded. "
        f"Approved total {approved_total} against {remaining} remaining on the annual limit."
    )
    return _turn(
        "Every line resolved; approving in principle.",
        [("issue_decision_letter", {
            "claim_id": claim_id, "decision": "approve_in_principle", "reason": reason,
            "evidence": evidence, "lines": dispositions,
            "approved_total": approved_total, "refused_total": refused_total,
            "settlement_basis": settlement_basis,
        })],
    )
