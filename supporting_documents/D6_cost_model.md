# D6 — Cost model, ledger and sensitivity

## Purpose and scope

This working paper converts one completed D5(b) live-model battery into a
reproducible cost-to-serve estimate for the Problem A first-response agent. It
uses measured tokens and completion outcomes, not estimated usage. The final
report should cite the resulting values and link to the filled D6 workbook.

## Static assumptions

| Input | Value | Basis |
|---|---:|---|
| Monthly claim volume | 8,000 claims | Assignment brief |
| Manual handling time if automation fails | 12 minutes | Assignment brief |
| Assessor wage | USD 38/hour | Assignment brief |
| Failure cost `F` | USD 7.60 | `12/60 × 38` |
| Retrieval/tool fee | USD 0.00 | Current tools read local JSON only; revise if a paid retrieval service is introduced |

## Required live-run inputs

One row is required per `case_id × trial` in the D5(b) JSON. The harness must
write: `model_id`, `case_id`, `case_type`, `trial`, `actual_decision`,
`actual_trigger`, `passed`, `turns`, `prompt_tokens`, `completion_tokens`,
`cost_usd`, `stopped_early`, and `trace_file`.

For each model, also record its official input and output list prices per
million tokens, the pricing-source URL, prompt version, evaluation-set commit,
and reasoning setting. A run passes only when its decision and required
trigger/missing field agree with the answer key.

## Core calculations

For each run `i`:

```text
L1_i = (prompt_tokens_i / 1,000,000 × input_price)
     + (completion_tokens_i / 1,000,000 × output_price)
     + retrieval_tool_fee_i

success_rate = passed_runs / total_runs
average_L1 = SUM(L1_i) / total_runs
L2 = (1 - success_rate) × 7.60
cost_per_task = average_L1 + L2
monthly_cost = cost_per_task × 8,000 + monthly_fixed_cost
```

`cost_usd` returned by the provider is retained as a reconciliation check. If
it differs materially from calculated L1, report both and use the documented
official list-price calculation in the cross-model comparison.

## Measured result — Chai Peiyao / Mistral Small 3.2 24B

Source battery: `eval/results/20260914T023002Z_live_mistralai-mistral-small-3.2-24b-instruct/`.
The D6 evidence set is the local, reproducible selection at
`eval/results/20260914T023002Z_live_mistralai-mistral-small-3.2-24b-instruct_d6-55-trials/`:
all 25 ordinary trial 1 rows plus negative trials 1--3 for each of 10 negative
cases; negative trial 4 is excluded. No model was rerun. The source battery
used commit `ba145f25512b753d0c7bc8210a7d6a23adaeef36`, the locked `v2-final`
prompt, and 35 cases. OpenRouter's model page lists USD 0.075 per million
input tokens and USD 0.20 per million output tokens.

| Measured item | Result |
|---|---:|
| Trials | 55 |
| Outcome passes | 14 |
| Outcome pass rate | 25.45% |
| Ordinary pass rate | 32.00% (8/25) |
| Negative pass rate | 20.00% (6/30) |
| Required-record completeness | 7.27% (4/55) |
| Strict record/process pass rate | 0.00% (0/55) |
| Average turns | 4.000 |
| Prompt tokens | 506,046 total; 9,200.84 per trial |
| Completion tokens | 70,241 total; 1,277.11 per trial |
| Measured token cost | USD 0.051997 total; USD 0.000945 per trial |

The headline success rate is outcome-graded as required by D4: the decision
must match, a document request must name the correct missing item, and an
escalation must carry the correct trigger. Required-record and strict process
rates remain visible as diagnostics rather than being silently folded into the
headline measure.

With `P = 14/55`, `F = USD 7.60`, and no fixed monthly cost entered yet:

```text
average_L1 = 0.051997 / 55 = USD 0.000945
L2 = (1 - 14/55) x 7.60 = USD 5.665455
cost_per_task = 0.000945 + 5.665455 = USD 5.666400
monthly_cost = 5.666400 x 8,000 = USD 45,331.20
manual_baseline = 7.60 x 8,000 = USD 60,800.00
expected saving before fixed costs = USD 15,468.80/month
```

This model is cheap to call, but its expected human fallback cost dominates:
more than 99.98% of its all-in expected cost is layer 2, not tokens.

### Mistral success-rate sensitivity

| Outcome success rate | Average L1 | Expected fallback L2 | Cost/task | Monthly at 8,000 |
|---:|---:|---:|---:|---:|
| 15.45% | USD 0.000945 | USD 6.425455 | USD 6.426400 | USD 51,411.20 |
| 25.45% measured | USD 0.000945 | USD 5.665455 | USD 5.666400 | USD 45,331.20 |
| 35.45% | USD 0.000945 | USD 4.905455 | USD 4.906400 | USD 39,251.20 |

### Dominant observed failure

All 55 selected traces (and all 65 source traces) contain at least one `check_coverage` call made with a fabricated
policy id before the real `lookup_policy` result was used. The interface takes
`policy_id`, but the preceding claim record only supplies `member_id`. This is
evidence of a dependency/interface mismatch, not a token-price problem. Keep
the locked D5 result unchanged for the model comparison; use this reproduced
failure in D7 or a post-battery improvement, where the correct fix is either to
make coverage accept an available identifier or to enforce the lookup-before-
coverage dependency.

## Sensitivity

Hold measured `average_L1` fixed and calculate the cost per task at:

```text
lower success rate = MAX(0, measured success_rate - 0.10)
base success rate  = measured success_rate
upper success rate = MIN(1, measured success_rate + 0.10)
```

For each point, recompute `L2`, cost per task and monthly cost. This tests the
economic impact of reliability uncertainty rather than inventing a different
token profile.

## Break-even comparison

For a cheap model token-only cost `C`, an expensive model all-in cost per task
`E`, and failure cost `F = 7.60`:

```text
break_even_success_rate = 1 - (E - C) / F
```

Interpretation: the expensive model is justified only if it achieves at least
this success rate relative to the cheap model under the stated comparison.
Clip impossible values below 0 or above 1, and state that no practical
break-even exists in that direction.

## Cost ledger: evidence still required

| Lever | Metric to record | Owner/source | Status |
|---|---|---|---|
| B — tool definitions | Entire tool-schema prompt tokens before vs after D2(a) | D2(a) owner | Pending |
| T — dependency order | Parallel vs sequential turns and prompt tokens | D2(c) experiment | Available; copy final figures |
| D — descriptors | Returned tokens per descriptor call v1 vs v2 | D2(b) experiment | Available; copy final figures |
| P — model performance | Pass rate, average L1 and all-in cost/task | D4/D5(b) harness | Mistral complete: 25.45%, USD 0.000945 L1, USD 5.666400 all-in; other models pending |

## Operational caps to state in the report

Document the final, evidenced values for the step cap, per-claim budget cap,
and monthly per-user cap. Do not claim the placeholder configuration value is a
financially justified control. State the test or distribution that supports
each final limit.

## Final D6 outputs

1. Model-by-model measured cost table with pricing source and trial count.
2. Three-point success-rate sensitivity table.
3. Cheap-versus-expensive break-even statement.
4. Four-lever ledger with before/after evidence.
5. One recommendation that names the selected operating model and all caps.
