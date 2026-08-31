# Best UI interaction contract

Harness OS follows the hackathon UI requirement as a runtime interaction contract, not a screenshot treatment.

The running product must always answer three questions for a new operator:

1. **What is the agent doing?** Show the current evidence gate and TrueForge session state.
2. **What is it waiting on?** Make blocked states explicit, especially human approval and Qodo review.
3. **What did it do?** Show a compact persisted causal trace with links to independent evidence.

Before any irreversible repository mutation, the operator console must display the exact bound GitHub MCP calls and pause the TrueForge session. Approval is intentionally two-step: review scope, then confirm. Reject remains available at the same point.

The certification chain is intentionally narrow:

`TrueForge sandbox -> human approval -> GitHub MCP PR -> Qodo review -> exact replay -> Safety Case`

The UI must never claim a sandbox pass, approval, Qodo review, replay pass, or Safety Case unless the backend has persisted the corresponding evidence.
