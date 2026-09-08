# D2(b) Tool Descriptor Contracts

## 1. get_claim

**NAME + SIGNATURE**  
`get_claim(claim_id: str) -> dict`

**WHAT**  
Fetches a claim and all of its line items using the claim ID. It is the entry-point tool and must be called first.

**INPUT**  
`claim_id`: a string identifying the claim to retrieve.

**RETURNS**  
A dictionary containing the claim record and its line items. If the claim does not exist, it returns an error dictionary.

**FAILS WHEN**  
The supplied `claim_id` cannot be found in the claim data.

**IRREVERSIBLE?**  
No. It is a read-only lookup and does not modify any data.


## 2. lookup_policy

**NAME + SIGNATURE**  
`lookup_policy(member_id: str) -> dict`

**WHAT**  
Retrieves the insurance policy associated with a member. It provides the policy status, coverage dates, annual limit, used amount, and exclusions needed for policy-related checks.

**INPUT**  
`member_id`: a string identifying the member whose policy should be retrieved.

**RETURNS**  
A dictionary containing the member's policy record, including policy status, dates, annual limit, used-to-date amount, and exclusions.

**FAILS WHEN**  
The supplied `member_id` cannot be found, or the member refers to a `policy_id` that does not exist in the policy data.

**IRREVERSIBLE?**  
No. It is a read-only lookup and does not modify any data.


## 3. check_coverage

**NAME + SIGNATURE**  
`check_coverage(policy_id: str, procedure_code: str) -> dict`

**WHAT**  
Checks whether a specific procedure is covered under a policy, whether an exclusion applies, and whether the procedure requires pre-authorisation.

**INPUT**  
`policy_id`: a string identifying the policy to check.  
`procedure_code`: a string identifying the procedure being assessed.

**RETURNS**  
A dictionary containing the procedure code, whether it is covered, any applicable exclusion rule, and whether pre-authorisation is required.

**FAILS WHEN**  
The supplied `policy_id` cannot be found, or the supplied `procedure_code` does not exist in the procedure data.

**IRREVERSIBLE?**  
No. It performs a read-only coverage check and does not modify any data.


## 4. get_preauthorisation

**NAME + SIGNATURE**  
`get_preauthorisation(member_id: str, procedure_code: str, date_of_service: str) -> dict`

**WHAT**  
Checks whether a valid pre-authorisation exists for a member and procedure on the specified date of service. It should only be called when `check_coverage` has returned `requires_preauth = true` for that procedure.

**INPUT**  
`member_id`: a string identifying the member.  
`procedure_code`: a string identifying the procedure requiring pre-authorisation.  
`date_of_service`: the date on which the procedure was performed.

**RETURNS**  
A dictionary indicating whether a pre-authorisation was found and whether it was valid on the date of service. If valid, it also returns the pre-authorisation ID and validity dates. If invalid or absent, it returns a reason.

**FAILS WHEN**  
No matching pre-authorisation exists for the member and procedure, or a matching pre-authorisation exists but its validity period does not cover the date of service.

**IRREVERSIBLE?**  
No. It is a read-only lookup and does not modify any data.


## 5. get_hospital_status

**NAME + SIGNATURE**  
`get_hospital_status(hospital_id: str) -> dict`

**WHAT**  
Looks up a hospital in the insurer's hospital data and determines whether it is a panel hospital. Panel status affects the settlement basis of an approved claim.

**INPUT**  
`hospital_id`: a string identifying the hospital.

**RETURNS**  
A dictionary containing the hospital ID, hospital name, and its panel status.

**FAILS WHEN**  
The supplied `hospital_id` cannot be found in the hospital data.

**IRREVERSIBLE?**  
No. It is a read-only lookup and does not modify any data.


## 6. check_duplicate_claim

**NAME + SIGNATURE**  
`check_duplicate_claim(member_id: str, hospital_id: str, date_of_service: str, lines: list[dict]) -> dict`

**WHAT**  
Checks whether the current claim is a resubmission of an already-decided claim. A duplicate is identified by matching the member, hospital, date of service, and all claim line items rather than by claim ID.

**INPUT**  
`member_id`: a string identifying the member.  
`hospital_id`: a string identifying the hospital.  
`date_of_service`: the date of service for the claim.  
`lines`: a list of claim line items containing procedure codes and amounts.

**RETURNS**  
A dictionary indicating whether the claim is a duplicate. If a duplicate is found, it also returns the matched claim ID, matched facts, prior decision, and decision date.

**FAILS WHEN**  
No previously decided claim matches all four required facts: member, hospital, date of service, and line items. In that case, the tool returns `duplicate = false`.

**IRREVERSIBLE?**  
No. It only compares the claim against existing decided claims and does not modify any data.


## 7. issue_decision_letter

**NAME + SIGNATURE**  
`issue_decision_letter(claim_id: str, decision: str, reason: str, evidence: list[str], autonomy: str = "confirm", ...) -> str`

**WHAT**  
Performs the gated action for the agent. After the required facts and approval conditions have been established, it records the claim decision as one structured JSON record. Despite its name, it does not generate or send an actual letter.

**INPUT**  
`claim_id`: the claim being decided.  
`decision`: one of `approve_in_principle`, `request_document`, or `escalate`.  
`reason`: a short explanation supporting the decision.  
`evidence`: the tools actually called to establish the decision.  
`autonomy`: the approval mode, which defaults to `confirm`.  
Optional fields record structured decision details such as trigger, missing document, escalation destination, line-level outcomes, approved/refused totals, and settlement basis.

**RETURNS**  
A short confirmation string when the decision is successfully recorded, or a `BLOCKED` message when the gated action is not permitted.

**FAILS WHEN**  
The decision is outside the permitted decision set, required operator confirmation has not been obtained under `confirm` autonomy, or a decision for the same claim has already been recorded.

**IRREVERSIBLE?**  
Yes. This is the agent's gated write action: it appends a structured decision record to the local decision log. It must therefore be called at most once and only after the required facts and gate conditions have been established.


# Poka-Yoke Design Changes

The following two design changes move error prevention into the tool interface or code layer rather than relying on the model to follow instructions.

| Before | After | What it makes impossible |
| --- | --- | --- |
| Each item in `lines[]` could omit `code` or `amount` in the `check_duplicate_claim` schema. | Each line item now requires both `code` and `amount`. | An incomplete line item entering duplicate-claim matching. |
| `date_of_service` could be any string passed to `get_preauthorisation`. | The schema specifies ISO `YYYY-MM-DD`, and the tool validates the value using `date.fromisoformat()`. | A malformed or ambiguous service date silently entering the pre-authorisation validity check. |


# Descriptor Rewrite Experiment

**Tool chosen:** `get_preauthorisation`

**V1:** current instruction-heavy descriptor.

**V2:** shorter descriptor with date validity enforced by the interface and code layer.

**Metrics to compare:**
- tokens returned per call
- evaluation pass rate
- guardrail cases passed

## Token-return comparison

A small four-case comparison was run against valid, expired, missing, and malformed-date inputs. Token counts were estimated using `len(json.dumps(output)) // 4`.

| Case | V1 estimated tokens | V2 estimated tokens |
| --- | ---: | ---: |
| Valid pre-authorisation | 27 | 11 |
| Expired pre-authorisation | 48 | 18 |
| Missing pre-authorisation | 28 | 5 |
| Invalid service date | 18 | 6 |
| **Average** | **30.25** | **10.00** |

The V2 output reduced estimated tokens returned per call from 30.25 to 10.00 on average, a reduction of approximately **66.9%**. The shorter output retains the decision-relevant fields needed to distinguish valid, expired, missing, and malformed-date cases.

## Evaluation pass-rate comparison

The same 15-case Problem A evaluation set was run once with the V1 pre-authorisation tool and once with the V2 tool.

| Version | Cases passed | Pass rate |
| --- | ---: | ---: |
| V1 | 15 / 15 | 100% |
| V2 | 15 / 15 | 100% |

The V2 rewrite preserved the baseline decision accuracy while substantially reducing the size of the tool return.

## Guardrail-case comparison

Three malformed service-date guardrail cases were defined for this rewrite experiment to verify that invalid date inputs do not silently enter the pre-authorisation validity check.

| Version | Guardrail cases passed |
| --- | ---: |
| V1 | 3 / 3 |
| V2 | 3 / 3 |

Both versions rejected all three malformed-date inputs: an incorrect separator (`2026/09/01`), an impossible date (`2026-02-30`), and a free-text date (`September 1 2026`).

Overall, V2 reduced the average estimated return size from 30.25 to 10.00 tokens (approximately 66.9%) while preserving a 100% evaluation pass rate and a 3/3 guardrail pass result.
