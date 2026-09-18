# Report sections -- Chai Peiyao

## 4. What it costs

We modelled cost using the same reproducible 55-trial subset of the completed Mistral live battery: all 25 ordinary trials and trials 1--3 for each of ten negative cases. Negative trial 4 was excluded and no model was rerun. Mistral passed 14/55 trials (25.45%): 8/25 ordinary trials and 6/30 negative trials. The average run took four turns.

At 8,000 claims per month, our model separates three layers: model-token cost, human fallback, and fixed cost. Measured token cost was only USD 0.000945 per task. However, each failed claim is escalated to a claims assessor at USD 7.60, producing expected fallback cost of USD 5.665455 per task. Fixed fees are zero for this local prototype; future infrastructure, monitoring and maintenance are excluded. The expected total is therefore USD 5.666400 per claim, or USD 45,331.20 per month, against USD 60,800 for fully manual handling. This gives expected monthly savings of USD 15,468.80 before fixed operating costs.

Human fallback dominates: it is more than 99.98% of Mistral's all-in expected cost. A ten-percentage-point success-rate change shifts monthly cost from USD 51,411.20 at 15.45% success to USD 39,251.20 at 35.45%. We measured four levers: a 10.9% smaller tool block, 39.6% fewer dependency turns, 66.9% fewer descriptor-return tokens, and end-to-end success rate. The final lever matters most because it determines the human fallback layer directly.

Mistral needs a 41.79% success rate to break even against GPT-4.1 Mini; its measured rate is 25.45%. We therefore recommend it only as a human-confirmed first-response pilot, with a ten-turn cap and a USD 1 API cap per claim. Its strict process pass rate remains 0/55, so the confirmation gate must remain mandatory.

## 5. The two failures

We reproduced both failures on the scripted backend by deleting one control from the production agent, rather than writing a separate bad agent. First, deleting action de-duplication made the runner request the same claim ten times. It reached the ten-turn cap without a decision or a write: 10,000 prompt tokens, 1,000 completion tokens and a synthetic, Mistral-priced cost of USD 0.000950. Restoring de-duplication stopped the repeat at turn two, with one real read and one blocked repeat: 2,000 prompt tokens, 200 completion tokens and USD 0.000190. This is an 80% reduction in turns, tokens and cost. The correct repair belongs in loop-control code because only the loop sees the complete action history; a prompt request is not enforcement, and a single tool cannot detect repetition across calls. The 35-case scripted evaluation remained 35/35 before and after, so legitimate outcomes were not truncated.

Second, we deleted the member-to-policy recovery adapter in `check_coverage`. The failure replay uses CLM-9105 and supplies member ID M-5502, which `get_claim` exposes before policy ID. Without the adapter, coverage failed and the agent wrote an incorrect escalation. Restoring the adapter resolved the member's policy and produced the required `request_document` decision, naming `itemised_bill for line 45378`. Both variants used four turns, 4,000 prompt tokens, 400 completion tokens and USD 0.000380; the repair improves correctness, not cost. This belongs in the tool interface: the defect is a recoverable identifier mismatch. Rewording the prompt would leave the contract fragile, while a loop guard can stop a run but cannot resolve the missing join.

## Evidence paths

- D6 cost model and 55-trial selection: `supporting_documents/D6_cost_model.md`
- D7 runner: `eval/run_d7_failures.py`
- D7 generated results: `eval/results/d7_scripted_failures/summary.json`