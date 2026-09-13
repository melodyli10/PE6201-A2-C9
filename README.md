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