# D2(c) — Calling more than one tool in a turn

## The mechanism

This agent uses native tool-calling (the OpenAI-compatible `tool_calls` array) rather than
parsing an `Action:` line out of free text — a model can return several tool calls in one
response, and the loop executes all of them together before asking again. `src/loop.py` is
domain-agnostic: it sends the conversation to whichever backend `config.BACKEND` names,
executes every tool call the response contains, appends all the observations, and repeats.
It never decides *what* to batch — that's the backend's job (the scripted policy, or the
live model reading the system prompt), which keeps this an agent rather than a hardcoded
workflow: the loop doesn't choose the sequence, the decision-maker behind it does.

## The dependency rule

**Turn 1 — alone.** `get_claim(claim_id)`. Nothing else has `member_id`, `hospital_id`,
`date_of_service` or `lines[]` until this returns.

**Turn 2 — parallel.** `lookup_policy || get_hospital_status || check_duplicate_claim`.
None of these three prices a line, and none needs another's result — they only need facts
`get_claim` already returned.

**Decision gate, evaluated after turn 2's three results are in** (see
`backend_scripted.py` for the scripted policy's version of this; the live model is guided
to the same gate by the system prompt in `loop.py`):
- policy lapsed / outside dates → escalate (`policy_lapsed` / `outside_policy_dates`)
- duplicate found → escalate (`duplicate_claim`)
- `sum(line.amount) > policy.annual_limit - policy.used_to_date` → escalate
  (`annual_limit_exceeded`) — computed from `get_claim`'s own data, **no** `check_coverage`
  call needed to reach this trigger
- narrative flagged as hostile → escalate (`instruction_in_member_narrative`)
- otherwise, continue

**Turn 3 — parallel, only if turn 2 passed every gate.** `check_coverage`, once per line.

**Turn 4 — parallel, conditional.** `get_preauthorisation`, once per line where coverage
said `requires_preauth=true`.

**Final turn.** `issue_decision_letter`, behind the `confirm` autonomy gate.

## Why turn 2 doesn't include `check_coverage`

An alternative grouping bundles `lookup_policy` together with `check_coverage` in turn 2,
which is faster for the ordinary case — but it means a lapsed or over-limit claim still
burns `check_coverage` calls it never uses, and its decision record would then say "lines
were not individually priced" while the evidence trail shows `check_coverage` was called
anyway, which is a contradiction, not just a cost trade-off.

This rule checks every escalation gate **before** touching `check_coverage` at all, so
"stop before pricing individual lines" is actually true of the system rather than merely
claimed in the decision text.

## The measurement

We built a second mode into the scripted backend — same routing decisions, but capped at
one tool call per turn instead of batching independent ones together — and ran all 15
shipped claims through both. Same fixture data, same routing logic, only the grouping
changed.

| Claim | Expected | Parallel | Sequential |
|---|---|---|---|
| `CLM-8842` | approve | 5 turns, ~6,052 tok | 9 turns, ~11,437 tok |
| `CLM-8850` | approve | 4 turns, ~3,946 tok | 6 turns, ~6,108 tok |
| `CLM-8861` | approve | 5 turns, ~5,618 tok | 8 turns, ~9,249 tok |
| `CLM-8874` | approve | 4 turns, ~4,025 tok | 6 turns, ~6,263 tok |
| `CLM-8888` | request_document | 5 turns, ~5,973 tok | 9 turns, ~11,264 tok |
| `CLM-8894` | request_document | 5 turns, ~5,463 tok | 7 turns, ~7,739 tok |
| `CLM-8901` | request_document | 4 turns, ~3,927 tok | 6 turns, ~6,077 tok |
| `CLM-8910` | escalate/policy_lapsed | 3 turns, ~2,754 tok | 5 turns, ~4,911 tok |
| `CLM-8917` | escalate/outside_policy_dates | 3 turns, ~2,677 tok | 5 turns, ~4,776 tok |
| `CLM-8925` | escalate/annual_limit_exceeded | 3 turns, ~2,802 tok | 5 turns, ~5,039 tok |
| `CLM-8933` | escalate/duplicate_claim | 3 turns, ~2,797 tok | 5 turns, ~5,000 tok |
| `CLM-8941` | escalate/instruction_in_member_narrative | 3 turns, ~2,752 tok | 5 turns, ~4,944 tok |
| `CLM-8952` | escalate/instruction_in_member_narrative | 3 turns, ~2,747 tok | 5 turns, ~4,950 tok |
| `CLM-8960` | approve | 4 turns, ~4,378 tok | 9 turns, ~11,133 tok |
| `CLM-8971` | approve | 4 turns, ~3,967 tok | 6 turns, ~6,154 tok |
| **Total** | | **58 turns, ~59,878 tok** | **96 turns, ~105,044 tok** |

**39.6% fewer turns, 43.0% fewer input tokens with parallel batching.** Every case landed
on the same decision (and the same trigger, where one applies) in both modes — nothing
about correctness moved, only how many turns it took to get there.

The six escalations are the cleanest read: all land at exactly 3 turns under parallel,
regardless of which trigger fires, and exactly 5 under sequential — the minimum the
dependency rule allows either way. Nothing surprising in the turn counts anywhere in the
set; every number is explained by how many lines a claim has and whether one of them needs
a pre-authorisation chased.

One caveat on the token figures: the scripted backend makes no real API call, so there's no
real token usage to read off. What's reported is a character-count estimate of what would
actually be re-sent at each turn (everything before that turn, summed across every turn of
the run) — the right shape for comparing the two modes against each other, but not billed
API usage.

## Two honest limits

1. **Parallel calls can raise cost when a call turns out unnecessary.** Bundling
   `get_hospital_status` into turn 2 means it's fetched on every escalation too, even
   though its result is never used there (see `supporting_documents/D2a_tool_set.md`'s
   cost discussion).
2. **They remove a decision point the agent would otherwise have used.** By hard-coding
   the turn-2 trio as always-parallel, the model never gets the chance to skip
   `get_hospital_status` or `check_duplicate_claim` early based on its own judgement — the
   code decided that grouping, not the agent.

## A live-model spot check, separately

The comparison above runs on the scripted backend, which is free, deterministic, and the
right instrument for isolating "does batching help" from "did the model just behave
differently this time." A live model was checked too, on `CLM-8850`, as a smaller
supplement rather than a replacement for the above:

| Version | Turns | Prompt tokens | Completion tokens | Total |
|---|---|---|---|---|
| Before (prompt didn't insist on batching — model called one tool per turn) | 6 | 13,180 | 1,431 | 14,611 |
| After (prompt insists independent calls go in one response) | 4 | 9,424 | 956 | 10,380 |

Same decision both times, ~29% fewer tokens after the prompt was tightened. Turn counts on
the live model aren't fully stable run to run the way the scripted backend is — `CLM-8925`
ran anywhere from 3 to 5 turns across separate attempts, all landing on the correct
decision — which is itself worth noting as a real difference between the two backends.
