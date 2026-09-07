# D2(a) — The tool set, chosen not collected

Seven tools. Six come from Problem A's minimum tool set; one (`check_duplicate_claim`) was
added because nothing in the minimum set can query `decided_claims.json`, and the routing
table requires catching a resubmission on it.

Each tool is scored against three questions: does a task actually fail without it, could
the model confuse it with a neighbour, and what does it cost when it's never called.

## Testing necessity instead of arguing it

We pulled each tool out one at a time, swapped in a stand-in that either errors or quietly
returns "everything's fine," left the other six real, and reran all 15 shipped claims to
see which ones actually broke.

| Tool ablated | Stand-in used | Cases affected | What broke |
|---|---|---|---|
| `get_claim` | always "no claim found" | **15 / 15** | Total failure, as expected — but the system degrades safely: every case falls through to `escalate/claim_not_found` rather than crashing. |
| `lookup_policy` | always active, unlimited, no exclusions | **3 / 15** | Exactly the three cases that depend on policy status/dates/limit — `CLM-8910` (lapsed), `CLM-8917` (outside dates), `CLM-8925` (over limit) — all silently approved instead. Nothing else moved. |
| `check_coverage` | always covered, never needs pre-auth | **2 / 15** | `CLM-8888`, `CLM-8894` wrongly approved — without it, `requires_preauth` is never known, so the system doesn't even think to check for a pre-authorisation. |
| `get_preauthorisation` | always valid, never actually checked | **2 / 15** | The same two cases, different mechanism — coverage correctly flags "needs pre-auth," but nothing verifies one exists and is current. |
| `check_duplicate_claim` | always "not a duplicate" | **1 / 15** | `CLM-8933`, the one true duplicate, wrongly approved. |
| `get_hospital_status` | panel status always unknown | **0 / 15 decisions**, but content silently wrong | The decision never moves — but `CLM-8842` (a panel hospital) gets recorded as `"not on panel; reimbursement"`, the opposite of the truth. Fails the record, not the decision. |
| `issue_decision_letter` | not tested | — | Not the same kind of tool — it's the output mechanism, not an information source. "Removing" it means no case can ever be decided, for every case, which isn't a comparable test to the other six. |

## The scoring table

| Tool | 1 · Does a task actually fail without it? | 2 · Could the model confuse it with a neighbour? | 3 · Cost when never called |
|---|---|---|---|
| `get_claim` | **Yes — tested.** 15/15 cases fail when it's removed. It is the only entry point into the claim. | No. | Its schema rides in the prompt on every turn of every run, same as the other six. It's only actually invoked once, turn 1 — every later turn pays for it and gets nothing back. |
| `lookup_policy` | **Yes — tested.** 3/15 cases fail when it's removed (all three policy-status/date/limit escalations). | No — one-line distinction from `check_coverage`: this answers account-level questions, `check_coverage` answers per-procedure questions. | Schema rides in the prompt every turn regardless. It is actually invoked once, on every single run — no case skips it, so the "never called" cost never applies here. |
| `check_coverage` | **Yes — tested.** 2/15 cases fail when it's removed. | No — distinct from `get_preauthorisation` ("is it covered" vs. "does a valid approval exist"). | Schema rides in the prompt every turn regardless. On the six escalation cases it's never invoked at all — the schema is paid for on every one of their turns and used by none of them. |
| `get_preauthorisation` | **Yes — tested.** Same 2/15 cases fail when it's removed, for a different reason than `check_coverage`'s removal. | No. | Schema rides in the prompt every turn regardless. Only invoked on lines flagged `requires_preauth=true` — 11 of the 15 shipped runs never call it once, and still pay for it on every turn. |
| `get_hospital_status` | **Tested and confirmed debatable.** 0/15 decisions change, but the record's content becomes factually wrong on a panel-hospital approval. Fails the record, not the outcome. | No — unambiguous single boolean, not confusable with anything. | Schema rides in the prompt every turn regardless. Invoked on every run, but its answer is only ever used on an approval — on the six escalations it's paid for, fetched, and then thrown away. Cheapest schema of the six read tools. |
| `check_duplicate_claim` | **Yes — tested.** 1/15 cases fail when it's removed (the one true duplicate). | No — unique join logic against `decided_claims.json`, not overlapping any other tool. | Schema rides in the prompt every turn regardless. Invoked on every run, but its answer only ever matters on the one claim that's actually a duplicate — the other 14 runs pay for it and use nothing. |
| `issue_decision_letter` | **Yes — not tested the same way (see above).** It is the entire deliverable — the one write, the whole point of the exercise. | No. | Schema rides in the prompt every turn regardless, same as the rest. This is the one tool that's never truly "never called" — a run isn't finished until it is. |

## Why `check_duplicate_claim` is a new tool and not tacked onto something else

We don't have a tool that touches `decided_claims.json`, so widening an existing one
wasn't an option — there was nothing to widen.

We did think about folding the check into `get_claim`, since `get_claim` already has the
member/hospital/date/lines the match needs. Dropped that idea: it would mean our own code
decides whether a claim is a duplicate before the agent ever gets a say, which defeats the
point of building an agent in the first place. Same reason we didn't just do the check in
plain code outside the loop — it's a judgement call, and judgement calls belong to the
agent, not to us.

So it's a new tool. It earns its keep — the ablation above shows exactly one case
(`CLM-8933`) silently goes wrong without it, and there's nothing else in the set it could
be confused with.

## `get_hospital_status` is the shakiest tool in the set

Pulling it out doesn't change a single decision. It does quietly wreck the record on a
panel hospital, though — `CLM-8842` came back saying "not on panel" when it plainly is.

Cost-wise it's cheap: roughly 63 tokens of schema, and across an average 4-turn run at
Problem A's volume (8,000 claims/month, cheap-tier pricing of US$0.10/1M input tokens)
that's about:

```
8,000 claims × 4 turns × 63 tokens ≈ 2,016,000 tokens/month ≈ US$0.20/month
```

A real live call (`nvidia/nemotron-3-super-120b-a12b:free`, `CLM-8850`) came in around
10,800 input tokens for the whole 4-turn run once the tool calls were batched properly,
which lines up with the estimate once you separate out the tool-definition share from the
rest of the conversation.

We're keeping it where it is. `CLM-8874`'s answer key needs the record to say the hospital
is non-panel, and there's no other way to know that. Fetching it later — only once the run
looks headed for an approval — would save the cost on escalations, but it costs a turn back
on the ordinary case for one boolean, and US$0.20/month doesn't justify that. Nothing got
cut here; this was the closest we came.

## The bug this turned up

Digging into `get_hospital_status`'s cost turned up something worse than a cost question:
we were calling it every run and then never using the answer. `CLM-8874` was getting the
right decision (`approve_in_principle`) but the record never said the hospital was
non-panel, which its answer key requires. Fixed it in `backend_scripted.py` (reads the
result back now) and added a `settlement_basis` field to `issue_decision_letter.py` so it's
carried through. Reran all 15 — still 15/15, and `CLM-8842`/`CLM-8874` now say what the
answer key expects.
