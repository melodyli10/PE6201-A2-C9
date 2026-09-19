# Contributions — Chai Peiyao

This document records only the work completed by **Chai Peiyao**. My main
ownership areas were D6 and D7. I also completed the individual D4 and D5 work
required of every team member and contributed the related engineering,
validation, documentation and integration work.

## Individual tasks required of every team member

### D4 — Individual evaluation cases

- Authored six additional Problem A evaluation cases, CLM-9201 to CLM-9206.
- Covered ordinary clean claims, excluded-only lines, non-panel hospitals,
  inclusive policy-date boundaries, annual-limit boundaries and hostile input.
- Included exactly one required negative case: CLM-9206, a natural-language
  prompt-injection attempt instructing the system to disregard policy rules.
- Wrote the expected outcome for every case from the Appendix A routing table
  before execution, then added the corresponding fixture data and labels to the
  shared evaluation set.
- Recorded the initial CLM-9206 failure as a genuine D3 hostile-input finding
  instead of removing or weakening the case, so the detector could be fixed and
  the case retained as regression evidence.
- Documented the six cases, their purpose, ground truth and scripted outcomes in
  `supporting_documents/D4_cases_chai_pei_yao.md`.

### D5(b) — Individual live-model battery

- Took ownership of the Mistral Small 3.2 24B evaluation strand.
- Ran and preserved the completed 65-trial live-model battery rather than using
  scripted or synthetic outputs as a substitute for the required live run.
- Preserved per-trial traces, tool interactions, raw outcomes, judgement files,
  judged result tables, summaries and run metadata for auditability.
- Produced the Mistral submission JSON and the CSV/Markdown result tables used
  by the later D6 analysis.
- Added and tested harness/submission-building support needed to turn the live
  run into reproducible evidence, including coverage for the new workflow.
- Kept the original completed battery intact so later analyses could be derived
  locally without making additional model calls.

Primary evidence:
`eval/results/20260916T045705Z_live_mistralai-mistral-small-3.2-24b-instruct/`.

## D6 — Cost-to-serve analysis and report (primary owner)

### Reproducible 55-trial normalisation

- Converted the completed Mistral 65-trial live battery into the exact
  55-trial basis required for the cross-model cost comparison.
- Performed the conversion locally and did **not** re-run Mistral, avoiding both
  unnecessary API cost and a non-comparable second sample.
- Applied the required negative-case rule consistently: retained negative trials
  1-3 and excluded negative trial 4.
- Implemented `eval/derive_d6_55_trials.py` so the selection can be reproduced
  from the preserved source battery rather than hand-edited.
- Added `eval/test_derive_d6_55_trials.py` to check the trial count, selection
  rule and integrity of the derived outputs.
- Generated a complete derived evidence bundle containing 55 trials, judged
  trials, judgement records, result tables, summaries, metadata and the D6
  submission JSON.
- Preserved provenance between the source battery and the derived subset so the
  assessor can verify that D6 uses completed live evidence and contains no new
  inference run.

Derived evidence:
`eval/results/20260914T023002Z_live_mistralai-mistral-small-3.2-24b-instruct_d6-55-trials/`.

### Cost model and cross-model analysis

- Designed and implemented the reproducible three-layer cost-to-serve model:
  model-token cost, human fallback cost at USD 7.60 per failed claim, and fixed
  cost. Recorded measured fixed fees as zero for the local prototype and kept
  unmeasured future operating costs outside the measured total.
- Normalised and verified six completed live-result sources before using them in
  the model, with the verification result saved in `cost_model/source_audit.json`.
- Built the required five-model comparison and maintained separate Mistral v1
  and v2 evidence so prompt/model changes were not hidden in a single number.
- Calculated the corrected Mistral v2 result on the common 55-trial basis:
  14/55 successes (25.45%), USD 0.000945 model cost per task, USD 5.666400 total
  cost per task, and USD 45,331.20 per month at 8,000 claims.
- Calculated the corrected Mistral v1 result: 1/55 successes (1.82%) and
  USD 7.462673 total cost per task. Quantified the v2 improvement as +23.64
  percentage points in success and -USD 1.796273 per task.
- Compared automated handling with the fully manual baseline of USD 60,800 per
  month and calculated GPT's modelled monthly cost at approximately USD 35,400.
- Built a Mistral success-rate sensitivity analysis showing that a ten-point
  change moves monthly cost between approximately USD 39,251 and USD 51,411.
- Calculated Mistral's 41.79% break-even success rate against GPT and compared it
  with the measured 25.45% success rate, making the operational gap explicit.
- Measured and modelled the four principal levers requested for the analysis:
  tool-block size, number of turns, observation size and success rate. Showed
  that human fallback, not token spend, dominates total cost.
- Produced the B/T/D/P evidence ledger linking business assumptions, token data,
  decision/success outcomes and pricing inputs to their source files.
- Proposed and justified operating controls using measured evidence: a 10-turn
  cap, a USD 0.10 per-claim budget ceiling, and a proposed USD 1 monthly budget
  per active user for this prototype context.

### D6 deliverables and report writing

- Built `cost_model/PE6201_A2_D6_Cost_to_Serve.ipynb` as the assessor-facing,
  reproducible notebook for the calculations and comparisons.
- Added the supporting cost-model scripts and machine-readable JSON outputs so
  the published figures are recalculable rather than manually typed totals.
- Wrote and refined `supporting_documents/D6_cost_model.md`, including the final
  report Section 4, assumptions, source provenance, corrected Mistral results,
  sensitivity analysis, break-even analysis, evidence ledger and operational
  recommendations.
- Added `cost_model/verify_d6_inputs.py` and used it to verify all six live input
  sources before finalising the analysis.
- Updated the project documentation so another team member or assessor can find
  the inputs, reproduce the 55-trial derivation and run the D6 verification.

## D7 — Two reproduced failures and report (primary owner)

### Experiment design and implementation

- Designed two deterministic deletion experiments against the working system,
  each removing one useful capability and measuring the failure before restoring
  the capability.
- Implemented the experiments in `failures/run_d7.py` using the production loop,
  production tools, 10-turn cap, USD 0.10 budget ceiling and confirmation gate.
- Kept the experiments fully offline and deterministic: no live model/API calls
  were required, and the saved result explicitly records zero live calls.
- Added `failures/test_d7.py` with regression coverage for the experiment runner,
  expected failures, recoveries and saved evidence.
- Saved all machine-readable before/after measurements in
  `failures/d7_results.json`.

### Failure 1 — Removing duplicate-action protection

- Removed the action de-duplication capability to reproduce a repeated-tool loop
  and then restored the protection to demonstrate recovery.
- Before restoration, the case reached the 10-turn cap, failed the task, used
  25,442 prompt tokens plus 460 completion tokens (25,902 total proxy tokens),
  and cost approximately USD 0.002000.
- After restoration, the same case completed successfully in 3 turns, used
  5,753 prompt tokens plus 216 completion tokens (5,969 total proxy tokens),
  cost approximately USD 0.000475, and did not hit a stop condition.
- This experiment demonstrated that action de-duplication improves reliability
  while also sharply reducing turns, token use and cost.

### Failure 2 — Removing an allowed tool-schema value

- Removed the required `outside_policy_dates` trigger from the five-value tool
  interface to reproduce an incorrect `coverage_expired` outcome, then restored
  the schema wording/value to demonstrate recovery.
- Before restoration, the one-turn case failed with 1,747 prompt tokens,
  105 completion tokens and an estimated cost of USD 0.000152.
- After restoration, the same one-turn case passed with 1,778 prompt tokens,
  106 completion tokens and an estimated cost of USD 0.000155.
- This experiment showed that a small, explicit tool-interface distinction can
  fix decision accuracy with negligible cost impact.

### Full-set instrumentation and D7 report writing

- Instrumented and measured the complete 105-trial scripted evaluation set.
- Verified 105/105 passing trials, with a median of 4 turns, a maximum of 5
  turns, and zero trials reaching the 10-turn cap.
- Reported the complete turn distribution: 18 trials used 3 turns, 63 used
  4 turns and 24 used 5 turns.
- Used this measured distribution to support the D6/D7 operating-cap rationale
  instead of choosing a cap without empirical evidence.
- Wrote `supporting_documents/D7_two_reproduced_failures.md`, including setup,
  exact deletions, before/after measurements, interpretation, reproducibility
  instructions and the final report Section 5.
- Updated the README with the commands and evidence locations needed to reproduce
  and inspect D7.

## Engineering, validation and integration work

- Improved the evaluation harness and added automated tests supporting the live
  Mistral battery and its downstream evidence generation.
- Added a reproducible D5 submission builder and preserved machine-readable,
  assessor-readable and trace-level outputs.
- Added and tested the local D6 55-trial derivation workflow rather than relying
  on manual deletion of ten records.
- Added deterministic D7 instrumentation and regression tests so both failures
  and both recoveries can be reproduced without external services.
- Integrated the final D4 data and the complete D6/D7 evidence into the feature
  branch and maintained the corresponding README and contribution documentation.
- Checked the final artifacts for consistent trial counts, traceability,
  reproducibility and alignment between reported figures and saved evidence.

## Evidence index

- D4 cases and finding: `supporting_documents/D4_cases_chai_pei_yao.md`
- D5 live Mistral battery:
  `eval/results/20260916T045705Z_live_mistralai-mistral-small-3.2-24b-instruct/`
- D5 submission builder and harness: `eval/build_d5_submission.py`,
  `eval/harness.py`, `eval/test_harness.py`
- D6 55-trial derivation: `eval/derive_d6_55_trials.py`,
  `eval/test_derive_d6_55_trials.py`
- D6 derived Mistral evidence:
  `eval/results/20260914T023002Z_live_mistralai-mistral-small-3.2-24b-instruct_d6-55-trials/`
- D6 model and verification: `cost_model/PE6201_A2_D6_Cost_to_Serve.ipynb`,
  `cost_model/verify_d6_inputs.py`, `cost_model/source_audit.json`
- D6 report material: `supporting_documents/D6_cost_model.md`
- D7 experiment code and tests: `failures/run_d7.py`, `failures/test_d7.py`
- D7 saved results: `failures/d7_results.json`
- D7 report material: `supporting_documents/D7_two_reproduced_failures.md`

The repository history under the `chaipeiyao8-dotcom` author identity and the
evidence paths above corroborate these contributions.
