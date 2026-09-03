# D0_why_an_agent.md




## D0(c) — What Good Looks Like

1. Correct outcome and trigger.  
   The run returns exactly one permitted outcome — `approve_in_principle`, `request_document`, or `escalate` — and its trigger agrees with the answer key rather than reaching the correct outcome by accident.

2. Necessary work only.  
   The agent performs all required checks, executes independent checks together where permitted, makes conditional calls only when their prerequisite is satisfied, and stops early after a decisive escalation trigger.

3. Per-case processing cost is lower than human manual handling.

4. Explicitly request missing information instead of fabricating data.

5. Takes the gated action at most once, and only after the facts are established.
