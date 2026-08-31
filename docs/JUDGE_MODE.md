# Harness OS Live Judge Mode

Harness OS is designed so judges do not have to inspect five disconnected tools to understand the project. The local React UI now exposes the assurance chain directly:

```text
TrueForge -> FaultLine MCP -> GitHub MCP -> Qodo Review -> Safety Case
```

## What the UI proves

### 1. TrueForge

The Harness OS control-plane API calls the configured TrueForge runtime capability endpoint. The UI only displays `CONNECTED` when the runtime is actually reachable. Campaign execution still uses native TrueForge sessions, runtime events, MCP calls and approval handling.

### 2. FaultLine H-005

FaultLine is the Streamable HTTP MCP used to inject the deterministic `timeout_after_success` failure. Its job is to make an irreversible refund succeed remotely while the caller receives an ambiguous timeout.

### 3. GitHub MCP

Repository inspection and approval-gated repository mutations are performed through the GitHub MCP attached to the Harness OS TrueForge agent. Harness OS does not silently substitute a local fake GitHub mutation in live mode.

### 4. Qodo Review

`backend/app/integrations/qodo.py` retrieves review/comment evidence from the public GitHub API and looks specifically for Qodo bot activity. The UI displays:

- whether Qodo evidence was found;
- the configured PR number;
- number of detected Qodo review/comment events;
- timestamp/author metadata from the latest event;
- a direct evidence link.

If Qodo evidence cannot be found, the UI reports `NO REVIEW FOUND` or `UNAVAILABLE`; it never fabricates a successful Qodo review.

Defaults:

```text
QODO_REPOSITORY=harshapriyag123/harness-os
QODO_PR_NUMBER=7
```

Both can be overridden in the backend environment. `GITHUB_TOKEN` is optional for this public repository but can be supplied server-side to reduce GitHub API rate-limit pressure. Never expose it to the frontend.

### 5. Safety Case

Harness OS owns the normalized verification evidence and release decision. The UI shows how many Safety Cases are currently persisted. Final verdict language remains intentionally narrow: `ALLOW_FOR_TESTED_CONDITION`, `BLOCK`, or `INCONCLUSIVE`.

## Local judging setup

Run the Harness OS control-plane API with TrueForge configured, then start the frontend against it.

macOS/Linux:

```bash
cd backend
source .venv/bin/activate
HARNESS_OS_MODE=live \
TRUEFORGE_BASE_URL=<your TrueForge runtime origin> \
TRUEFORGE_AGENT_NAME=harness-os \
HARNESS_CHAOS_MCP_URL=https://faultline-h005.onrender.com/mcp \
QODO_REPOSITORY=harshapriyag123/harness-os \
QODO_PR_NUMBER=7 \
uvicorn app.main:app --reload --port 8080
```

In a second terminal:

```bash
cd frontend
VITE_API_URL=http://127.0.0.1:8080 npm run dev
```

Windows PowerShell:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:HARNESS_OS_MODE = "live"
$env:TRUEFORGE_BASE_URL = "<your TrueForge runtime origin>"
$env:TRUEFORGE_AGENT_NAME = "harness-os"
$env:HARNESS_CHAOS_MCP_URL = "https://faultline-h005.onrender.com/mcp"
$env:QODO_REPOSITORY = "harshapriyag123/harness-os"
$env:QODO_PR_NUMBER = "7"
uvicorn app.main:app --reload --port 8080
```

In a second PowerShell window:

```powershell
cd frontend
$env:VITE_API_URL = "http://127.0.0.1:8080"
npm run dev
```

Open `http://127.0.0.1:5173`.

The top of the application displays **LIVE JUDGE MODE** and refreshes the integration evidence through `/api/v1/integrations`.

## Best two-minute judging flow

1. Open Harness OS and point at the Live Judge Mode rail.
2. Show TrueForge as the execution runtime rather than claiming the UI itself is the agent harness.
3. Run the H-005 campaign and show the real `$249 -> $498` baseline evidence in Wind Tunnel / Flight Recorder.
4. Open the GitHub evidence from the UI.
5. Open the Qodo evidence from the Qodo card and show that the verifier's own code was independently reviewed.
6. Return to Harness OS and show the human approval and Safety Case surfaces.

The key judging message is:

> **Harness OS does not replace TrueForge or Qodo. It orchestrates them into one evidence-backed pre-deployment safety gate.**
