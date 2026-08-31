# Hosted TrueForge runtime setup

Harness OS now uses the project's known hosted services directly in code. A large `.env` is not required for the demo.

## Code-owned defaults

```text
TrueForge host: https://harsha.truefoundry.cloud
TrueForge agent: harness-os
Repository: https://github.com/harshapriyag123/harness-os
Refund fixture: https://harness-os.onrender.com
FaultLine MCP: https://faultline-h005.onrender.com/mcp
```

Harness OS probes the known TrueForge host using `/api/v1/capabilities`. There is no localhost fallback in the hosted path.

## Minimal environment

Normally the only TrueForge value that may need to be supplied is the server-side authentication token:

```powershell
$env:TRUEFORGE_TOKEN="<server-side-token>"
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

If the hosted service does not require a bearer token, even `TRUEFORGE_TOKEN` can remain unset.

## Only override the API URL when needed

The currently known TrueForge URL is `https://harsha.truefoundry.cloud`. If that host is only the human-facing dashboard and TrueForge exposes its API from another origin, set just this one override:

```powershell
$env:TRUEFORGE_API_BASE_URL="https://<actual-api-origin>"
```

The API origin must expose routes such as:

```text
GET  /api/v1/capabilities
POST /api/v1/sessions
GET  /api/v1/sessions/{session_id}/events
```

Mission Control reports:

- `CONNECTED` when the capability endpoint succeeds;
- `AUTH_ERROR` when the service is reachable but rejects authentication;
- `WRONG_API_BASE` when the known host is a dashboard/wrong route;
- `TIMEOUT` or `UNAVAILABLE` for connectivity failures.

## Public deployment architecture

```text
Public React UI
      |
      v
Public Harness OS control-plane API
      |
      v
Hosted TrueForge
      |-- GitHub MCP
      |-- FaultLine MCP
      |-- Sandbox
      `-- Native approval checkpoints
```

Secrets remain backend-only. Never place `TRUEFORGE_TOKEN` in a `VITE_*` frontend variable.
