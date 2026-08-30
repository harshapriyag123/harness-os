# Harness OS Architecture

Harness OS separates **reasoning** from **proof**.

- LLM/subagents: discover architecture, synthesize scenarios, investigate root causes, propose candidate controls.
- Deterministic engine: evaluates invariants, stores traces, computes pass/fail, controls release blockers.
- TrueForge boundary: production campaign creation uses the documented TrueForge HTTP session/turn API and persists returned identifiers. Demo mode changes the target to a local fixture but still requires real TrueForge execution. Without a reachable configured runtime, campaign start fails honestly.
- Chaos MCP: controlled failure injection and trace inspection.
- UI: makes state, evidence and approval waits visible.

## Production evolution

Hackathon MVP -> continuous pre-merge assurance -> runtime assurance -> incident replay -> enterprise policy registry.

The local control plane uses SQLite records plus an append-only campaign-event table. Safety Cases hash canonical evidence with SHA-256. A future production deployment can add Postgres/Redis, OIDC/RBAC, signed attestations, OpenTelemetry export, policy-as-code, multiple target adapters and signed evidence manifests.
