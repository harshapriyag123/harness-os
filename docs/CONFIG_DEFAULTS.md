# Harness OS code-owned runtime defaults

Harness OS intentionally keeps demo/judge configuration small. Public project endpoints are defined in code and environment variables are optional overrides.

Defaults:

- TrueForge host: `https://harsha.truefoundry.cloud`
- TrueForge agent: `harness-os`
- Repository: `https://github.com/harshapriyag123/harness-os`
- Refund fixture: `https://harness-os.onrender.com`
- FaultLine MCP: `https://faultline-h005.onrender.com/mcp`

Secrets are never committed. `TRUEFORGE_TOKEN` remains backend-only when authentication is required.
