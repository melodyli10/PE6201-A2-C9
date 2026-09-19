# Contributions

## Chai Peiyao

- Contributed six D4 evaluation cases, including the required negative cases.
- Ran and preserved the Mistral Small 3.2 24B D5(b) live battery.
- Built D6's reproducible three-layer cost model, five-model comparison,
  sensitivity analysis, break-even calculation and B/T/D/P cost ledger.
- Built D7's two deterministic deletion experiments, scripted instrumentation,
  105-trial turn distribution, before/after evidence and report section draft.

## Zhao Zixuan

- Handled testing and validation for the D2(b)/D3 guardrail work, including the reproducible D3 test runner, test checklist, saved results, and related guardrail and configuration fixes.
- Prepared the initial D4 evaluation implementation, including the evaluation-related code, evaluation cases, and their associated test data and expected outcomes. The initial work was then handed over to Li Jiakun for further review, refinement, and integration.
- Ran and preserved the complete 65-trial Gemini 2.5 Pro D5(b) live-model battery, including execution traces, judged results, summary tables, and cross-platform hash verification.


The commit history and the evidence paths in `supporting_documents/` corroborate
these items. Other team members should append their own entries before the team
submission is assembled.

## Wang Xiyue

- Implemented the D2(b) tool-description and poka-yoke work, including the V1/V2 pre-authorisation interface rewrite and structured return shapes; the rewrite reduced estimated return tokens while preserving the 15/15 scripted baseline.
- Implemented D3(a)’s code-layer guardrails, including the step cap, budget ceiling, duplicate-action blocking, and the host-configured confirm-mode gate for irreversible decision writes, together with reproducible guardrail experiments.
- Contributed six D4 evaluation cases with matching fixture data and expected outcomes, including the required negative case, and validated them against the integrated scripted system.
- Ran and preserved the complete 65-trial Qwen D5(b) live-model battery, including model pricing/configuration, execution traces, independent GPT-4.1-mini judgements, judged results, and submission artifacts.
  
## Lai Yangfei

- Contributed six D4 evaluation cases with matching fixture data and expected outcomes, including the required negative case.
- Ran and preserved the complete 65-trial DeepSeek Chat D5(b) live-model battery, including pricing/configuration, traces, judged results, summary outputs, and the final submission JSON. Completed the DeepSeek judgement workflow and verified that all pending judgements were resolved.
- Contributed to the loop-and-tool design discussion, especially the rationale for an agentic loop, dynamic tool selection, a gated irreversible decision write.
- Drafted and refined report.
- Coordinated report and demo assembly, including integrating the final report, checking A2 requirement alignment, preparing the demo script and slide guidance, and editing the final video.

## Aravindh

- Built D1: the single-agent ReAct loop (`src/loop.py`), the scripted and live backends, the seven-tool registry, and the gated decision write with its autonomy check.
- Built D2(a): justified the seven-tool set by removing each tool in turn and rerunning the evaluation set, and fixed the defect this exposed (the hospital-status result was fetched but never written into the record, so a panel hospital was recorded as non-panel).
- Built D2(c): defined the dependency rule for which calls may share a turn, implemented parallel execution, and measured sequential against parallel runs on the same cases (39.6% fewer turns and 43.0% fewer input tokens, identical decisions).
- Contributed five D4 evaluation cases (`CLM-9107` to `CLM-9111`) covering an annual-limit breach by exactly one dollar, both inclusive edges of a pre-authorisation window, an expiry missed by one day, and a claim needing two pre-authorisation lookups; labels were written from the routing table before any agent run.
- Ran and preserved the D5(b) v1 pass on Mistral Small 3.2 24B (65 trials, judged independently by GPT-4.1 Mini, US$0.052962): only the v1 pre-authorisation tool was exposed, verified by zero v2 calls across all traces, and the system prompt was left unchanged. Result 1/65 (1.54%) against the v2 run's 16/65 on the same model. An earlier attempt that varied the system prompt instead of the tool descriptor was identified as incorrect and replaced.
- Checked the other teams' live runs for mixed tool versions by counting actual tool calls in their traces (two single-version, one with a single stray v1 call).
- Evaluated multi-agent and retrieval alternatives as a side experiment outside the graded build (`alt_architecture_multiagent_rag/`, kept local); the comparison and the reasons for not adopting them, or fine-tuning, are written up separately for the report's limits section.
