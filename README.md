# PE6201-A2-C9

PE6201 A2 Applied AI System - Team C9

## D4 Evaluation Harness

The final D4 evaluation set contains:

- 35 team-written evaluation cases
- 25 ordinary cases
- 10 negative cases
- 55 total trials

Ordinary cases run once. Negative cases run three times.

## Run the scripted backend

The scripted backend is deterministic and runs without an API key or network access.

```bash
python3 -m unittest eval.test_harness
python3 -m eval.harness --suite d4 --backend scripted
```

## Grading

The harness uses mixed grading:

- Code checks for deterministic requirements such as outcome, trigger, tool behaviour and gated action.
- Judgement checks for selected cases where reason and evidence quality require review.

Final judgement outputs are stored in:

```text
eval/final_judgements.jsonl
```

## Final scripted evaluation

Final evidence is stored in:

```text
eval/results/d4_scripted_final/
```

Final scripted result:

- 55/55 trials passed
- 25/25 ordinary trials passed
- 30/30 negative trials passed
- Final pass rate: 100%
- Judgement pending: 0
- Average turns: 3.927
- Total scripted cost: USD 0.00
