# Harness OS Certification Chain

Harness OS deliberately makes sponsor tooling part of the release decision rather than decoration.

```text
TrueForge sandbox PASS
        ↓
TrueForge human approval
        ↓
GitHub MCP remediation PR
        ↓
Qodo review evidence on that exact PR
        ↓
Exact H-005 replay
        ↓
Harness OS Safety Case
```

## Why this is different

A normal demo can say that TrueForge executed an agent and Qodo reviewed the repository. Harness OS makes both independently observable dependencies of certification.

- **TrueForge sandbox** must provide the three required PASS results and a real sandbox identifier.
- **Human approval** must be a native TrueForge approval bound to the GitHub mutation tool calls.
- **GitHub MCP** must create the remediation PR with structured result evidence.
- **Qodo** is queried independently from GitHub and must have review evidence on the exact repository + PR number. Agent-authored text cannot satisfy this gate.
- **Exact replay** is rejected until the Qodo gate is satisfied.
- **Safety Case** includes the Qodo proof alongside the sandbox, approval, PR and replay evidence in its evidence digest.

## Local judge UI

The local React experience exposes two layers above the dashboard:

1. **Live Integration Rail** — TrueForge, FaultLine MCP, GitHub MCP, Qodo Review and Safety Case availability.
2. **Live Certification Chain** — campaign-specific gates showing what has actually passed and what is blocking release.

The campaign-specific panel displays the real TrueForge sandbox ID and named test results when available, and it displays the exact Qodo review evidence link once found.

The most important state for the demo is `QODO_REVIEW_PENDING`: the remediation PR exists, but Harness OS intentionally keeps replay locked until independent review evidence arrives.

## Evidence integrity

Harness OS never treats a model statement such as “Qodo reviewed this PR” as proof. The backend retrieves Qodo bot comments/reviews from GitHub and binds them to the campaign's `github_pr.repository` and `github_pr.pr_number` before replay can proceed.
