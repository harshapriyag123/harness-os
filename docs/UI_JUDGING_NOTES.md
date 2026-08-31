# Best UI interaction contract

Harness OS is an operator console, not a static hackathon dashboard.

A stranger should be able to answer four questions without reading the README:

1. **What target am I operating on?**
2. **What is the agent doing now?**
3. **What is it waiting on?**
4. **What did it already do?**

## Repository workspace

The local UI accepts any public GitHub repository URL. Repository names are derived from the URL by default, and every target is registered independently with branch, status and risk state. A generic repository is not mislabeled as `CustomerSupportAgent` and does not inherit the H-005 refund scenario.

Generic targets are inspected by TrueForge through GitHub MCP. Harness OS asks TrueForge to identify actual agent surfaces, MCP tools, generated-code execution, retries, data boundaries and irreversible actions. If a repository is not an AI agent, the run must say `NOT_APPLICABLE`/`INCONCLUSIVE` rather than forcing the refund scenario.

## Public runtime bridge

The local control plane probes the hosted services used by the live demo and exposes them inside the product:

- Refund Fixture health
- FaultLine H-005 health

The UI shows reachability and observed latency. These states come from backend probes, not static green badges.

## Approval-before-action rule

When TrueForge emits a native pending approval for consequential GitHub writes, the operator surface must show the exact tool, repository, branch and tool-call ID before execution. The user must explicitly review and confirm approval. Reject remains available. The frontend never simulates approval; the final action calls the Harness OS backend, which resumes the native TrueForge approval.

## Certification chain

`TrueForge sandbox -> human approval -> GitHub MCP PR -> Qodo review -> exact replay -> Safety Case`

## Evidence integrity

UI status is derived from persisted Harness OS/TrueForge/Qodo evidence. No sandbox, approval, Qodo, replay, public-service or Safety Case state may be manufactured to make the demo appear complete.
