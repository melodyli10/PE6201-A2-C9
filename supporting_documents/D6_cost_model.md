# D6 — Cost model, ledger and sensitivity

## Purpose and scope

This working paper converts one completed D5(b) live-model battery into a
reproducible cost-to-serve estimate for the Problem A first-response agent. It
uses measured tokens and completion outcomes, not estimated usage. The final
report should cite the resulting values and the evidence paths recorded below.

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

## Model-by-model 55-trial cost table

All four live batteries were normalised locally with the same selection rule:
ordinary trial 1 plus negative trials 1--3, with negative trial 4 excluded.
This does not execute a model. `L1` is recomputed from the recorded token totals
and the recorded OpenRouter list prices; it is therefore not distorted by
provider-side rounding in per-trial `cost_usd` fields.

| Model | Family / tier | Passes | Pass rate | L1/task | All-in cost/task | Monthly cost | Evidence |
|---|---|---:|---:|---:|---:|---:|---|
| Mistral Small 3.2 24B | Mistral / cheap | 14/55 | 25.45% | USD 0.000945 | USD 5.666400 | USD 45,331.20 | `eval/results/20260914T023002Z_live_mistralai-mistral-small-3.2-24b-instruct_d6-55-trials/` |
| GPT-4.1 Mini | OpenAI / mid | 23/55 | 41.82% | USD 0.003165 | USD 4.424983 | USD 35,399.86 | historical run `2a07d6e1:eval/results/20260914T070612Z_live_openai-gpt-4.1-mini/trials_judged.jsonl` |
| Gemini 2.5 Pro | Google / expensive | 8/55 | 14.55% | USD 0.031866 | USD 6.526412 | USD 52,211.29 | historical run `8cf78814:eval/results/20260914T154843Z_live_google-gemini-2.5-pro/trials_judged.jsonl` |
| Qwen3.6 35B A3B | Qwen / cheap | 14/55 | 25.45% | USD 0.001861 | USD 5.667316 | USD 45,338.53 | historical run `a892594b:eval/results/20260915T012109Z_live_qwen-qwen3.6-35b-a3b/trials_judged.jsonl` |

Price sources recorded at run time are OpenRouter model pages: Mistral
`mistralai/mistral-small-3.2-24b-instruct` (USD 0.075/0.20 per million input/output
tokens), GPT-4.1 Mini (USD 0.40/1.60), Gemini 2.5 Pro (USD 1.25/10.00), and
Qwen3.6 35B A3B (USD 0.05/0.70). The GPT and Qwen batteries have dataset hash
`f735…`, while Mistral and Gemini have `0aca…`; all are 35-case/10-negative
batteries, but this hash difference means the table is a cost comparison and
not a controlled causal ranking of model quality.

## Break-even comparison

Use Mistral as the cheap model (`C = USD 0.000945` token-only cost/task) and
GPT-4.1 Mini as the more expensive-call model (`E = USD 4.424983` all-in
cost/task), with `F = USD 7.60`:

```text
break_even_success_rate = 1 - (E - C) / F
                        = 41.79%
```

GPT-4.1 Mini's selected-battery outcome rate is 41.82%, only 0.03 percentage
points above that break-even. Its 0/30 negative-case passes make that narrow
cost advantage unsuitable as an autonomous-decision recommendation; the
break-even is an economic threshold, not a safety clearance.

## Cost ledger

| Lever | Before | After | Change | Evidence and interpretation |
|---|---:|---:|---:|---|
| B — tool block size | 1,054 estimated tokens (eight exposed schemas) | 939 (V2-only seven-schema selection) | -115 (-10.9%) | Static compact-JSON estimate from `src/tools/__init__.py`; retain `check_duplicate_claim`, remove the superseded V1 pre-authorisation schema from production exposure. D2(b) shows V2 preserves 15/15 decisions. |
| T — dependency order | 96 turns; ~105,044 input tokens | 58 turns; ~59,878 input tokens | -38 turns (-39.6%); -45,166 tokens (-43.0%) | `supporting_documents/D2c_dependency_rule.md`, 15-case scripted paired comparison; every outcome/trigger was unchanged. |
| D — descriptor return | 30.25 estimated tokens/call | 10.00 | -20.25 (-66.9%) | `D2(b)_tool_descriptions.md`, valid/expired/missing/malformed four-case comparison; 15/15 evaluation and 3/3 guardrails in both versions. |
| P — operating result | Manual handling: USD 7.60/task | Mistral: 25.45% outcome pass; USD 5.666400/task | USD 1.933600/task lower before fixed costs | 55-trial Mistral evidence above. Mistral and Qwen tie on outcome rate, but Mistral has lower L1; Mistral is also the only listed model with negative-case passes (6/30). |

## Operational caps and recommendation

| Control | Final value | Evidence / rationale |
|---|---:|---|
| Step cap | 10 turns | `src/config.py` sets 10; the selected Mistral and Qwen batteries reached but never exceeded 10, so this is a proven hard stop rather than an untested lower value. |
| Per-claim API budget | USD 1.00 | `src/config.py` and D3 guardrail test. The highest observed selected-trial provider charge was Gemini's USD 0.058585, leaving a 17.1× margin; the budget test blocks an over-budget write. |
| Monthly per-user API budget | USD 1.00 | Deployment policy cap. It is intentionally on API spend, not human fallback allocation, and covers at least 17 runs at the observed worst API charge. Enforce it before starting a new user run. |

Recommendation: use the Mistral V2 tool design only as a human-confirmed first-response
pilot, with the V2-only schema block, parallel dependency rule, 10-turn cap,
USD 1.00 per-claim API cap and USD 1.00 monthly per-user API cap. It is the
lower-L1 cheap model and the only tested option with non-zero negative-case
outcomes. Do not automate the irreversible decision write: strict process
passes remain 0/55, so the existing `confirm` gate stays mandatory. GPT-4.1
Mini may be re-evaluated after the evaluation-set hash is aligned and its
negative-case failure is corrected; Gemini and Qwen are not cost-preferred on
these measurements.

## Final D6 outputs

1. The four-model, 55-trial cost table and recorded price sources are above.
2. The Mistral three-point success-rate sensitivity is above.
3. The Mistral-versus-GPT break-even calculation is above.
4. The B/T/D/P evidence ledger is complete above.
5. The selected operating model and all three caps are stated above.
