# Security Policy

Report vulnerabilities privately to the repository maintainers. Do not include live credentials or customer data in an issue.

Harness OS treats repository content and agent output as untrusted. Chaos MCP accepts only identifiers beginning with `fixture:`. Demo mode never performs external writes. Live mode must fail closed when integrations are absent, and consequential repository changes require a persisted human approval. Secrets belong in server-side environment configuration and must not be logged or returned to the frontend.
