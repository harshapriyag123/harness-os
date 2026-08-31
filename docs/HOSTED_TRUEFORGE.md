# Hosted TrueForge runtime setup

Harness OS live mode is designed to talk to a **hosted TrueForge API**, not a local fallback.

## Required server-side environment

```text
HARNESS_OS_MODE=live
TRUEFORGE_API_BASE_URL=https://<your-trueforge-api-origin>
TRUEFORGE_TOKEN=<server-side-token>
TRUEFORGE_AGENT_NAME=harness-os
TRUEFORGE_REQUEST_TIMEOUT_SECONDS=60
TRUEFORGE_PROBE_TIMEOUT_SECONDS=4
```

`TRUEFORGE_BASE_URL` remains supported as a compatibility alias, but `TRUEFORGE_API_BASE_URL` is preferred for hosted deployments because it makes the distinction from a human-facing dashboard URL explicit.

The configured origin must expose TrueForge API routes such as:

```text
GET  /api/v1/capabilities
POST /api/v1/sessions
GET  /api/v1/sessions/{session_id}/events
```

Do **not** use a dashboard URL unless those API routes are actually served from the same origin.

## Live-mode safety behavior

When `HARNESS_OS_MODE=live`:

- missing TrueForge API configuration returns `NOT_CONFIGURED`;
- `localhost`, `127.0.0.1`, and `::1` are rejected for the TrueForge API base;
- Harness OS does not silently fall back to a local/demo TrueForge server;
- authentication errors are reported as `AUTH_ERROR`;
- dashboard/wrong-route responses are reported as `WRONG_API_BASE`;
- connectivity failures are reported as `UNAVAILABLE` or `TIMEOUT`;
- the TrueForge token is never returned to the browser.

## Windows PowerShell example

```powershell
$env:HARNESS_OS_MODE="live"
$env:TRUEFORGE_API_BASE_URL="https://<your-trueforge-api-origin>"
$env:TRUEFORGE_TOKEN="<your-server-side-token>"
$env:TRUEFORGE_AGENT_NAME="harness-os"
$env:TRUEFORGE_REQUEST_TIMEOUT_SECONDS="60"
$env:TRUEFORGE_PROBE_TIMEOUT_SECONDS="4"

cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Then open Mission Control and use **Retry connection**. The expected status is `CONNECTED TrueForge`.

## Public deployment architecture

```text
Public React UI
      |
      v
Public Harness OS control-plane API
      |
      v
Hosted TrueForge API
      |-- GitHub MCP
      |-- FaultLine MCP
      |-- Sandbox
      `-- Native approval checkpoints
```

Keep `TRUEFORGE_TOKEN` only on the Harness OS backend/control-plane service. Never expose it through a `VITE_*` frontend environment variable.
