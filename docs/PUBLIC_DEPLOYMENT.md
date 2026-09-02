# Public deployment runbook

Harness OS intentionally separates the **public judge view** from the **full operator runtime**.

- The public judge view is a read-only static site. It is safe to expose because it contains no secrets and performs no consequential actions.
- The full operator runtime includes TrueForge, GitHub MCP, FaultLine MCP, the controlled refund fixture, the Harness OS API, optional local Ollama, sandbox execution and human approval. Run it locally for the complete hackathon demonstration.

This split prevents the public demo from pretending that a GitHub write, sandbox run or approval occurred when the private runtime is not actually connected.

## Public URLs

After GitHub Pages is enabled for this repository and the `Deploy public judge view` workflow succeeds, the canonical public UI URL is:

```text
https://harshapriyag123.github.io/harness-os/
```

Already-public controlled services used by the project:

```text
Refund fixture health  https://harness-os.onrender.com/health
FaultLine health       https://faultline-h005.onrender.com/health
Repository             https://github.com/harshapriyag123/harness-os
```

The Pages UI is read-only by design. It explains the architecture, current evidence boundary, H-005 reproduction, public service links, Qodo evidence and exact local startup commands.

## Deploy the public UI for free with GitHub Pages

The repository includes `.github/workflows/pages.yml` and `frontend/vite.config.mjs`.

One-time GitHub setting:

1. Open the repository on GitHub.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, select **GitHub Actions** as the source.
4. Merge the deployment workflow to `main`, or manually run **Deploy public judge view** from the Actions tab.
5. Wait for the `github-pages` environment deployment to finish.
6. Open `https://harshapriyag123.github.io/harness-os/`.

The workflow builds with:

```text
VITE_PUBLIC_READ_ONLY=true
```

That environment flag renders `PublicJudgeLanding` instead of Mission Control. The local build remains unchanged and still renders the complete Mission Control / Demo Mode / Judge Demo Core experience.

## Local full runtime

```powershell
git clone https://github.com/harshapriyag123/harness-os.git
cd harness-os
docker compose up --build
```

Local endpoints:

```text
Harness OS UI      http://localhost:5173
Harness OS API     http://localhost:8080
TrueForge          http://localhost:8791
FaultLine MCP      http://localhost:8940/mcp
Refund fixture     http://localhost:8950
Ollama             http://localhost:11434
```

## Optional free Render hosting

Render currently offers free static sites and free web services suitable for prototypes/hackathon demos. Free web services spin down after inactivity and use ephemeral local filesystems, so do not rely on local SQLite state as durable evidence. Persist important evidence in GitHub artifacts, external storage, or a database if you move the full runtime to the cloud.

For this hackathon, the recommended deployment split is:

```text
GitHub Pages  -> read-only judge-facing UI
Render        -> controlled public fixture / FaultLine health endpoints
Local machine -> TrueForge + Ollama + approval-gated GitHub MCP workflow
```

This architecture keeps the public URL reliable while preserving the security and evidence integrity of the consequential runtime.

## Why the public page does not create PRs

A public static site must not carry a GitHub PAT, model key or TrueForge credential. The consequential path remains:

```text
TrueForge runtime
  -> GitHub MCP
  -> candidate remediation
  -> sandbox evidence
  -> explicit human approval
  -> branch / file update / pull request
  -> Qodo review
  -> exact replay
  -> Safety Case
```

If a judge wants to see that flow, run the local operator demo and screen-share the real approval boundary. Do not replace it with a fake client-side modal on the public site.
