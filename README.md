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

### Cross-platform hash note

The Gemini run used the same committed `v2-final` evaluation content, 35-case set and 65-trial battery as the other final live-model runs. Its raw dataset and judge-prompt hashes differed because the run was executed on Windows with CRLF line endings. After normalising CRLF to LF, both hashes matched the reference run. No evaluation content was changed.

## Grading

The harness uses mixed grading:

- Code checks for deterministic requirements such as outcome, trigger, tool behaviour and gated action.
- Judgement checks for selected cases where reason and evidence quality require review.


Final D4 and D5 evidence should use the current 105-trial D4 plan and 65-trial live-model battery.
