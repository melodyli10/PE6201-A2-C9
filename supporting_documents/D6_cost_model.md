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
| Fixed monthly fee in prototype baseline | USD 0.00 measured | Local JSON storage and scripted evaluation incur no provider fee |
| Illustrative deployment maintenance | USD 152.00/month assumed | Four hours of monthly review at the stated USD 38/hour; not an observed bill and not included in the baseline |

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
input_tokens ≈ B × T + D × T² / 2
L1_i = (prompt_tokens_i / 1,000,000 × input_price)
     + (completion_tokens_i / 1,000,000 × output_price)
     + retrieval_tool_fee_i

success_rate = passed_runs / total_runs
average_L1 = SUM(L1_i) / total_runs
L2 = (1 - success_rate) × 7.60
cost_per_task = average_L1 + L2
monthly_cost = cost_per_task × 8,000 + monthly_fixed_cost
```

Layer 3 is separated from the per-claim costs. The measured local-prototype
baseline has no monthly provider/infrastructure bill, so its layer 3 is USD
0. An explicitly assumed four hours of review per month would add USD 152 to
the monthly figure, making Mistral's illustrative total USD 45,483.20 instead
of USD 45,331.20. This assumption is not represented as a measured charge.
The same fixed amount would add USD 0.019 per claim at 8,000 claims/month and
less per claim at higher volume.

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

With `P = 14/55`, `F = USD 7.60`, and USD 0.00 measured fixed monthly provider fees in the prototype baseline:

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

Even at the upper success-rate point, Mistral remains above GPT-4.1 Mini's
USD 4.424983 per-task expected cost. The economic comparison survives this
range; the human-confirmed pilot recommendation reflects the separate
negative-case evidence, not a claim that Mistral is the cheapest model.

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

All five v2 live batteries were normalised with the same selection rule:
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
| DeepSeek Chat | DeepSeek / cheap | 8/55 | 14.55% | USD 0.003240 | USD 6.497786 | USD 51,982.29 | `feature4/lyf:eval/results/20260915T051830Z_live_deepseek-deepseek-chat/D5b_deepseek_submission.json` |

The sixth member's V1 pass holds the Mistral model fixed on the same 55
case/trial IDs: 3/55 passed (5.45%), L1 USD 0.000842/task, all-in USD
7.186297/task and USD 57,490.37/month in the same prototype baseline. V2
improved the outcome pass rate by 20.00 percentage points and reduced expected
cost by USD 1.519897/task. This is the paired prompt-version comparison, not
an additional V2 model.

Price sources recorded at run time are OpenRouter model pages: Mistral
`mistralai/mistral-small-3.2-24b-instruct` (USD 0.075/0.20 per million input/output
tokens), GPT-4.1 Mini (USD 0.40/1.60), Gemini 2.5 Pro (USD 1.25/10.00), and
Qwen3.6 35B A3B (USD 0.05/0.70). Lai's recorded DeepSeek Chat price is USD
0.2574/1.029 per million input/output tokens. Its selected 55 trials used
600,610 prompt and 22,962 completion tokens; 8 passed (7 ordinary, 1 negative).
The list-price calculation gives USD 0.178225 for the battery, or USD 0.003240
per trial. Monthly figures include the measured token cost and expected human
fallback at 8,000 claims; unpriced deployment fixed costs are excluded.
Recorded price pages: [Mistral](https://openrouter.ai/mistralai/mistral-small-3.2-24b-instruct),
[GPT-4.1 Mini](https://openrouter.ai/openai/gpt-4.1-mini),
[Gemini 2.5 Pro](https://openrouter.ai/google/gemini-2.5-pro),
[Qwen3.6 35B A3B](https://openrouter.ai/qwen/qwen3.6-35b-a3b), and
[DeepSeek Chat](https://openrouter.ai/deepseek/deepseek-chat).

## Break-even comparison

Use Mistral as the cheap model (`C = USD 0.000945` token-only cost/task) and
GPT-4.1 Mini as the more expensive-call model (`E = USD 4.424983` all-in
cost/task), with `F = USD 7.60`:

```text
break_even_success_rate = 1 - (E - C) / F
                        = 41.79%
```

Mistral's measured 25.45% is 16.33 percentage points below the 41.79%
break-even needed to match GPT-4.1 Mini's expected cost. GPT is therefore the
lower-cost option under this fallback model. Its 0/30 negative-case passes make
that cost advantage unsuitable as an autonomous-decision recommendation; the
break-even is an economic threshold, not a safety clearance.

## Cost ledger

| Lever | Before | After | Change | Evidence and interpretation |
|---|---:|---:|---:|---|
| B — tool block size | 943 tokens, eight exposed schemas | 841 tokens, seven V2-only schemas | -102 tokens/turn (-10.82%) | `cost_model/ledger_measurements.json`; tiktoken 0.14.0 `o200k_base` counts the compact serialized schema block before (`8f8da38`) and after the code cut. The old function remains for experiments but is no longer exposed to the final V2 model. |
| T — dependency order | 6 turns, 13,180 billed prompt tokens | 4 turns, 9,424 billed prompt tokens | -2 turns (-33.3%); -3,756 tokens (-28.5%) | D2(c) live spot check on `CLM-8850`: same decision. The broader 15-case scripted paired comparison gives 96→58 turns and ~105,044→59,878 *estimated* input tokens, with all outcomes/triggers unchanged. |
| D — pre-authorisation observation | 38.25 tokens/call, V1 average | 12.25 tokens/call, V2 average | -26.00 tokens/call (-67.97%) | `cost_model/ledger_measurements.json`, same tokenizer/serialization on four valid, expired, missing and invalid-date outputs. Both versions retained 15/15 shipped decisions and 3/3 malformed-date guardrails. |
| P — measured success | Mistral V1: 3/55 (5.45%); USD 7.186297/task | Mistral V2: 14/55 (25.45%); USD 5.666400/task | +20.00 percentage points; -USD 1.519897/task | `cost_model/d6_results.json`; same model and 55 case/trial IDs, with ordinary trial 1 and negative trials 1--3. V2 passed 6/30 negative trials; V1 passed 0/30. |

The tokenizer counts in B and D are local measurements of exactly the payloads
sent/returned under one explicit encoding, not provider-billed usage. The B
schema cut was made after the recorded D5 live battery, so its savings are a
separate before/after design measurement and are not silently subtracted from
the measured L1 baseline. Among token levers, T has the largest measured
whole-run effect. In the all-in bill, P dominates because each failure adds
USD 7.60 of human handling. Both cost scripts and their saved outputs live in
`cost_model/`; the arithmetic script runs offline with the Python standard
library.

## Operational caps and recommendation

| Control | Final value | Evidence / rationale |
|---|---:|---|
| Step cap | 10 turns | Selected Mistral median was 4 turns; 1/55 reached the cap and stopped without a decision (`CLM-9219`). Other completed selected runs reached 10 turns (Qwen), so a lower cap would truncate observed work. The scripted D3 test verifies a cap stops a repeated-action loop without writing. |
| Per-claim API budget | USD 0.10 | `src/config.py` now sets 0.10, about 1.7× the highest selected-trial provider charge (Gemini, USD 0.058585). The scripted D3 budget test verifies that an over-budget response cannot write a decision. The sent request can still exceed the remaining budget before its usage is returned. |
| Monthly per-user API budget | USD 1.00 proposed | Deployment policy for API spend, not human fallback allocation; it covers at least 17 runs at the observed worst API charge. The single-user prototype does not yet enforce cumulative monthly usage. |

Recommendation: use the Mistral V2 tool design only as a human-confirmed first-response
pilot, with the V2-only schema block, parallel dependency rule, 10-turn cap,
USD 0.10 per-claim API cap and a proposed USD 1.00 monthly per-user API policy.
Mistral is the lower-L1 cheap model with the highest measured negative-trial
pass count (6/30). Do not automate the irreversible decision write: strict
process passes remain 0/55, so the existing `confirm` gate stays mandatory.
GPT-4.1 Mini had the lowest expected cost but no negative-trial passes;
Gemini, Qwen and DeepSeek do not improve the cost and negative-case combination
for this human-confirmed pilot.

## Final D6 outputs

1. The five-model, 55-trial cost table, separate Mistral V1 pair, and recorded
   price sources are above.
2. The three-point sensitivity, layer-3 assumption and Mistral-versus-GPT
   break-even calculation are above.
3. The B/T/D/P before/after evidence ledger and its counting method are above.
4. The selected operating model and all three caps are stated above.
5. `cost_model/battery_inputs.json`, `d6_results.json`,
   `ledger_measurements.json` and `source_audit.json` preserve the inputs,
   calculations, local token counts and raw-source verification. The scripts
   that regenerate them are in the same directory. The Class 5 notebook
   adaptation is `cost_model/PE6201_A2_D6_Cost_to_Serve.ipynb`.

## Report section 4 draft (under 400 words)

At 8,000 claims per month, a failed automated response returns to a claims
assessor. Twelve minutes at USD 38/hour makes fallback USD 7.60 per claim.
Our three-layer baseline adds measured input/output token charges, expected
fallback `(1 - pass rate) x USD 7.60`, and USD 0 measured fixed monthly
provider fees for this local prototype. An explicitly assumed four hours of
monthly review would add USD 152; it is not an observed charge.

Mistral V2 passed 14/55 selected trials (25.45%). Its token charge averaged
USD 0.000945 per trial, but expected fallback raised cost to USD 5.666400 per
claim, or USD 45,331.20/month before deployment costs. Fallback dominates
the bill. Across success rate ±10 percentage points, monthly cost ranges
from USD 51,411.20 to USD 39,251.20. Even at the upper point, it remains
costlier than GPT-4.1 Mini's USD 4.424983 per claim.

The four-lever ledger measures the design changes. Removing the unused V1
pre-authorisation schema reduced the serialized tool block from 943 to 841
locally counted tokens per turn (B). In a live spot check, batching independent
tools reduced turns 6→4 and billed prompt tokens 13,180→9,424 (T); the
15-case scripted comparison preserved every outcome. The V2 pre-authorisation
observation averaged 12.25 locally counted tokens against V1's 38.25 (D).
On the same Mistral and 55 case/trial IDs, V1 passed 3/55 and cost USD
7.186297 per task, versus V2's 14/55 and USD 5.666400 (P). Success-rate
improvement outweighed token savings because a failure costs USD 7.60.

Five V2 models were costed. GPT-4.1 Mini had the lowest expected cost. For
cheap Mistral to match it, break-even success is 41.79%; measured Mistral
falls 16.33 points short. GPT passed 0/30 negative trials, while Mistral
passed 6/30. We recommend Mistral only for a human-confirmed pilot, with a
10-turn step cap, USD 0.10 per-claim API ceiling and a proposed USD 1.00
monthly per-user API policy. The monthly policy needs enforcement before
multi-user deployment; the decision-letter gate stays at `confirm`.
