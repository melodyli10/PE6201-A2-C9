# D0 - Why an Agent at All?

Problem A sits on rung 7 because the model selects its evidence-gathering sequence at runtime. Steps vary by claim: `CLM-8850` has one line, `CLM-8960` requires four coverage checks, and `CLM-8842` conditionally requires pre-authorisation for one of three lines. `CLM-8910` stops when its lapsed policy is observed. The agent therefore avoids unnecessary tools and exits when authoritative evidence determines an ask or escalation.

Rungs 1-4 provide a single decision, fixed chain, routing or predetermined parallel checks, but not model-selected follow-ups. Rung 5 adds unnecessary multi-agent coordination; rung 6 revises an answer but does not gather evidence or act. Read-only agentic retrieval could collect evidence, but a human would still record the decision. Rung 7 adds flexibility at the cost of variable turns, nondeterminism and a larger attack surface.

The workflow test gives four answers: the model selects the sequence during the run; step count varies by input; trajectories are not fully enumerable, so we grade outcomes; and cost remains variable until stopping. Both agent conditions hold: steps are not known in advance, and each step returns corrective ground truth.

Claim, member, policy, procedure, document, pre-authorisation, hospital and prior-decision files provide objective evidence through same-turn local lookups. If evidence were slow, subjective or absent, we would use a deterministic workflow with human review.

The first irreversible action is issuing the decision letter, simulated by one structured log entry. We choose `confirm` autonomy: the agent investigates and proposes, but an operator approves immediately before `issue_decision_letter` writes.

After D4 and D7, we will report measured pass rate `P = {{P}}`, median turns `T = {{T}}`, and `s = P^(1/T) = {{S}}`. This is diagnostic because steps are dependent and differ in difficulty.

Five pre-build criteria define a good run:

1. It returns the correct outcome and trigger.
2. Every line has a traceable disposition and reconciled totals.
3. Only necessary calls are made, with justified early exits.
4. The gated write occurs at most once, after confirmation.
5. Unsupported cases are requested or escalated; caps hold; cost is below manual handling.
