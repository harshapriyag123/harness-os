---
name: remediation
description: Generate minimal, testable harness remediations for verified findings.
---

# Remediation

Prefer the smallest control that prevents the verified failure without breaking the intended workflow. Consider tighter tool schemas, approval gates, idempotency, verify-before-retry, trust labeling, context isolation, permission narrowing and deterministic validators. Test candidate controls in the sandbox, replay the original failure, and run related normal-path regressions. Any repository or external write requires explicit human approval first.
