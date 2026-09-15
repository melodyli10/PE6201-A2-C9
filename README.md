# PE6201-A2-C9

PE6201 A2 Applied AI System - Team C9

## D4 Evaluation Harness

The final D4 evaluation set contains:

- 35 team-written evaluation cases
- 25 ordinary cases
- 10 negative cases

### D4 trial plan

For D4, every case is run three times:

- 35 cases × 3 trials
- 105 total trials

### D5 live-model battery

For D5(b), each live model runs:

- the full 35-case evaluation set once
- plus 3 extra trials for each of the 10 negative cases

This gives:

- 35 baseline trials
- 30 extra negative-case trials
- 65 total trials per live model

Every trial uses a private decision ledger, so no trial depends on another.

## Run the checks

The scripted backend is deterministic and runs without an API key or network access.

```bash
python3 -m unittest eval.test_harness
```

Check the D4 trial count:

```bash
python3 -m eval.harness \
  --suite d4 \
  --backend scripted \
  --trial-mode d4 \
  --dry-run
```

Check the D5 battery trial count:

```bash
python3 -m eval.harness \
  --suite d4 \
  --backend scripted \
  --trial-mode battery \
  --dry-run
```

## Run the D4 scripted evaluation

```bash
python3 -m eval.harness \
  --suite d4 \
  --backend scripted \
  --trial-mode d4
```

Expected trial count: 105

## Run a D5 live-model battery

Before running live, make sure the model and its token price are registered in `src/config.py`.

```bash
python3 -m eval.harness \
  --suite d4 \
  --backend live \
  --trial-mode battery \
  --model <MODEL_ID> \
  --prompt-version v2-final \
  --allow-live
```

Expected trial count per live model: 65

## Grading

The harness uses mixed grading:

- The primary D4/D5 pass rate is outcome-graded: the decision must match the answer key, a document request must name the exact missing item, and an escalation must use the correct trigger.
- Required-record completeness is reported separately for the decision-specific structured fields.
- Strict diagnostics report tool evidence, gated-action and loop behaviour without redefining the outcome pass rate.
- Judgement checks for selected cases where reason and evidence quality require review.

Earlier 55-trial runs are preserved as diagnostic history only.

Final D4 and D5 evidence should use the current 105-trial D4 plan and 65-trial live-model battery.

## Reproduce the D6 cost model

D6 compares one ordinary trial and the first three negative trials per case
from each completed live battery: 25 ordinary + 30 negative = 55 selected
trials per model. The original D5(b) 65-trial records remain available.

The three-layer arithmetic, five-model table, success-rate sensitivity,
break-even and Mistral V1/V2 comparison are offline and stdlib-only:

```bash
python3 -m cost_model.calculate_d6
```

`cost_model/battery_inputs.json` lists the observed trial totals and their D5
sources; `cost_model/d6_results.json` is the calculated output. In a git
checkout with the team branches fetched, verify the input aggregates against
the original trial records with:

```bash
python3 -m cost_model.verify_d6_inputs
```

The B and D ledger token counts use one explicit local tokenizer, rather
than pretending character counts are API usage. To reproduce those two
measurements, install `tiktoken==0.14.0` and run:

```bash
python3 -m cost_model.measure_d6_ledger
```

The saved measurements and method are in `cost_model/ledger_measurements.json`;
the complete interpretation and a report-ready section 4 are in
`supporting_documents/D6_cost_model.md`. The submitted
`cost_model/PE6201_A2_D6_Cost_to_Serve.ipynb` adapts the supplied Class 5
cost-to-serve notebook to the same measured inputs. None of these commands
sends a live request or requires an OpenRouter key.
