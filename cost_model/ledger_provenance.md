# D6 ledger source map

| Lever | Raw source | Measurement |
|---|---|---|
| B, tool block | `8f8da38:src/tools/__init__.py` before; current `src/tools/__init__.py` after | `python -m cost_model.measure_d6_ledger` serializes and tokenizes both schema lists under the same encoding. Production V2 exposes seven tools; V1 remains callable only for the rewrite experiment. |
| T, turns | `origin/feature/chai-peiyao-d4:supporting_documents/D2c_dependency_rule.md` | The document records a live `CLM-8850` spot check, 6→4 turns and 13,180→9,424 billed prompt tokens, with the same decision. Its 15-case scripted comparison also records 96→58 turns, with unchanged decisions/triggers; scripted input tokens are character-count estimates. |
| D, observation | `experiments/d2b_rewrite.py`; `src/tools/get_preauthorisation.py`; `D2(b)_tool_descriptions.md` | `python -m cost_model.measure_d6_ledger` calls both tool versions on four identical inputs and counts their compact JSON returns with the same tokenizer. The D2(b) document records 15/15 shipped decisions and 3/3 malformed-date guardrails for each version. |
| P, success | D5(b) trial sources in `battery_inputs.json`, including the same 55 Mistral V1/V2 case/trial IDs | `python -m cost_model.verify_d6_inputs` verifies the recorded aggregates; `python -m cost_model.calculate_d6` prices the expected human fallback. |

The B/D local token measurement is separate from API billing. The recorded
D5(b) token counts remain the sole source for baseline layer 1. Source results
and their method are saved in `ledger_measurements.json`, `source_audit.json`
and `d6_results.json` so the submitted folder copy can be inspected without
re-running a live model.
