# Best UI interaction contract

Harness OS treats the hackathon UI requirement as a runtime interaction contract, not a screenshot treatment.

The running product must always answer three questions for a new operator:

1. **What is the agent doing?** Show the current evidence gate and TrueForge session state.
2. **What is it waiting on?** Make blocked states explicit, especially human approval and Qodo review.
3. **What did it do?** Show a compact persisted causal trace with links to independent evidence.

Before any irreversible repository mutation, the operator console displays the exact bound GitHub MCP calls and keeps the TrueForge session paused. Approval is intentionally two-step: review the scope, then confirm. Reject is available at the same point.

The certification chain stays narrow and understandable:

`TrueForge sandbox -> human approval -> GitHub MCP PR -> Qodo review -> exact replay -> Safety Case`

The UI must never claim a sandbox pass, approval, Qodo review, replay pass, or Safety Case unless the backend has persisted the corresponding evidence.
