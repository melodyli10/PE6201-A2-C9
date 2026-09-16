# D7 - Two reproduced failures

## Reproduce

```bash
python -m failures.run_d7
```

The command uses the production `loop.run_case`, tools, 10-turn cap, USD 0.10
budget ceiling and confirmation gate. It makes zero network calls. `before`
removes exactly one working protection with `unittest.mock.patch`; `after`
restores it. The deterministic token proxy is `ceil(compact JSON UTF-8 bytes /
4)` per turn. Estimated cost applies the recorded Mistral list price to those
proxy counts; actual API cost is USD 0.

## Instrumentation and whole-set distribution

The runner records turns, prompt and completion tokens, estimated cost, stop
reason, ordered tool calls and the written decision. On the full D4 scripted
plan, 105/105 trials passed. Median was 4
turns, worst case 5, and 0 runs hit the
10-turn cap. Distribution: 3 turns = 18, 4 turns = 63, 5 turns = 24.
The scripted set alone would permit a lower cap, but D5 contains completed live
Qwen runs that required 10 turns; retaining 10 avoids truncating observed
legitimate work rather than choosing a round number without evidence.

## Failure 1 - loop control

The deletion removes only the membership check in action de-duplication. The
scripted observation keeps returning the same claim, so the agent re-reads it
until the step cap makes a loud stop. Restoring de-duplication returns
`BLOCKED: duplicate action`; the same agent then uses the evidence it already
has and reaches the correct escalation.

| State | Turns | Prompt tokens | Completion tokens | Estimated cost | Pass rate | Stop |
|---|---:|---:|---:|---:|---:|---|
| Guard deleted | 10 | 25,442 | 460 | USD 0.002000 | 0% | `step cap (10 turns) reached` |
| Guard restored | 3 | 5,753 | 216 | USD 0.000475 | 100% | none |

The step cap caught the runaway, but it did not fix it: no answer was returned.
The budget ceiling did not fire because estimated spend remained below USD
0.10. De-duplication is the causal code-layer fix; a prompt reminder would not
give the loop memory, and a tool-interface change would not track prior calls.

## Failure 2 - tool interface

The deletion removes the five-value `trigger` enum from
`issue_decision_letter`. The deterministic fixture replays the real v1 error:
the plausible synonym `coverage_expired` is written instead of the answer-key
name `outside_policy_dates`. Restoring the enum recovers the exact trigger.

| State | Turns | Prompt tokens | Completion tokens | Estimated cost | Trigger | Pass rate |
|---|---:|---:|---:|---:|---|---:|
| Enum deleted | 1 | 1,747 | 105 | USD 0.000152 | `coverage_expired` | 0% |
| Enum restored | 1 | 1,778 | 106 | USD 0.000155 | `outside_policy_dates` | 100% |

This belongs at the tool boundary: the accepted vocabulary is part of the
function contract. Prompt prose would rely on compliance, while putting
claims-specific trigger names into the generic loop would mix domain policy
with execution control.

## Report section 5 draft (under 250 words)

We reproduced both failures by deleting one protection from the working agent
and running the same scripted fixtures before and after. First, removing action
de-duplication made the loop call `get_claim` repeatedly. Per-run logging made
the failure visible: the agent used 10 turns and 25,902
proxy tokens, cost USD 0.002000, hit the step cap and
returned no decision (0% pass). Restoring the code guard blocked the second
identical call and the agent completed in 3 turns using
5,969 tokens at USD 0.000475 (100%).
The step cap caught the runaway loudly, but only de-duplication removed its
cause; the USD 0.10 budget was not reached, and prompt text cannot give a loop
memory of executed actions. Across all 105 scripted evaluation
trials, median was 4 turns, worst case 5,
and zero runs hit the cap. We retained 10 because completed live Qwen runs
required 10 turns; it preserves observed legitimate work and the
100% scripted pass rate.

Second, deleting the five-value `trigger` enum from the decision-tool schema
reproduced the measured v1 synonym error. The agent wrote
`coverage_expired`, which sounded reasonable but disagreed with the answer key
and failed. Restoring the enum produced `outside_policy_dates` and passed,
without adding turns. The fix belongs in the tool interface because permitted
trigger names are part of its contract. Adding another prompt sentence would
remain advisory; teaching the generic ReAct loop insurance vocabulary would
put domain policy in the wrong layer. Both experiments were deterministic and
their real API cost was USD 0.
