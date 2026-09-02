# Public deployment runbook

Harness OS now supports two public surfaces plus the complete local runtime:

```text
GitHub Pages / docs/index.html  -> judge-facing website
Render                         -> public TrueForge + Harness OS API blueprint
Existing Render services       -> refund fixture + FaultLine H-005
Local Docker Compose           -> full Ollama + TrueForge + MCP + approval demo
```

## Public judge URL

Canonical project site:

```text
https://harshapriyag123.github.io/harness-os/
```

The repository contains **both** deployment paths so GitHub Pages cannot fall back to rendering Markdown as the website:

- `docs/index.html` — static, zero-build judge site for branch `/docs` Pages mode.
- `.github/workflows/pages.yml` — Vite/React judge-site deployment for GitHub Actions Pages mode.

Either Pages configuration now has a real `index.html` project website instead of a README-only experience.

## Already-public evidence services

```text
Refund fixture health  https://harness-os.onrender.com/health
FaultLine health       https://faultline-h005.onrender.com/health
Repository             https://github.com/harshapriyag123/harness-os
```

## Free cloud TrueForge + API blueprint

The repository root now contains `render.yaml` and the missing `mcp-chaos/Dockerfile`.

The Blueprint declares:

```text
harness-os-trueforge  -> docker/trueforge/Dockerfile
harness-os-api-cloud  -> backend/Dockerfile
```

TrueForge is therefore deployable as the same containerized harness used locally rather than being replaced by a fake hosted UI. The cloud API is configured to use the public FaultLine and refund fixture endpoints.

One-click Blueprint entry point:

```text
https://render.com/deploy?repo=https://github.com/harshapriyag123/harness-os
```

Render requires the account owner to approve the Blueprint because it creates services in that Render workspace. No GitHub or model secrets are embedded in this repository.

Expected service URLs after the Blueprint is created with the declared names are typically:

```text
https://harness-os-trueforge.onrender.com
https://harness-os-api-cloud.onrender.com
```

Treat those as expected names until Render reports each service as Live. The stable public URLs already verified by this project remain the fixture and FaultLine URLs above.

## Render free-tier caveat

The Blueprint uses `plan: free`. Free web services are suitable for a hackathon but can sleep after inactivity and have ephemeral local filesystems. TrueForge standalone SQLite is therefore configured under `/tmp` for the public demonstration runtime; do not treat that cloud SQLite file as durable certification evidence.

The authoritative H-005 evidence in the submission remains the persisted controlled fixture/trace evidence and repository history.

## Complete local runtime

```powershell
git clone https://github.com/harshapriyag123/harness-os.git
cd harness-os
docker compose up --build
```

```text
Harness OS UI      http://localhost:5173
Harness OS API     http://localhost:8080
TrueForge          http://localhost:8791
FaultLine MCP      http://localhost:8940/mcp
Refund fixture     http://localhost:8950
Ollama             http://localhost:11434
```

The local surface is the consequential-action demo: GitHub MCP writes, TrueForge sandbox execution and human approval remain here unless the hosted TrueForge instance is explicitly configured with equivalent credentials and approval policies.

## Security boundary

The public judge website never contains:

- GitHub PATs
- model API keys
- OAuth tokens
- TrueForge credentials
- simulated approvals
- fabricated sandbox or Qodo PASS state

Public deployment is for inspectability. Consequential actions remain evidence-gated.
