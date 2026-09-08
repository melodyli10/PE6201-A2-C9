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
| P — model performance | Pass rate, average L1 and all-in cost/task | D4/D5(b) harness | Pending live battery |

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
