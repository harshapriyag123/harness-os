# Harness OS — Ollama + TrueForge Hackathon Runbook

This is the shortest reproducible path for the **Agent Harness Hackathon** when the model runs locally through **Ollama**.

> The architecture must remain: **Ollama = model, TrueForge = harness/runtime, MCP = tools, Harness OS = operator UI, Qodo = code-review gate.** Do not bypass TrueForge by calling Ollama directly for the golden agent run.

## 0. Final architecture

```text
Judge browser
  -> Harness OS UI (localhost:5173)
      -> Harness OS API (localhost:8080)
      -> Judge Demo Core (live readiness card)

TrueForge (localhost:8791)
  -> OpenAI-compatible model endpoint
      -> Ollama on host (localhost:11434 / host.docker.internal:11434)
  -> GitHub MCP
  -> FaultLine MCP (mcp-chaos:8940/mcp)
  -> sandbox
  -> human approval

FaultLine MCP
  -> refund fixture (customer-fixture:8950)

Approved remediation
  -> GitHub PR
  -> Qodo review
  -> exact replay
  -> Safety Case
```

## 1. Install and start Ollama

Install Ollama for your OS, then verify:

```powershell
ollama --version
ollama serve
```

If Ollama is already running as a background service, `ollama serve` may report that the port is in use; that is fine.

Verify the API:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags
```

## 2. Pull a local model

Use a model that supports the reasoning/tool behavior you need and that fits your machine.

```powershell
ollama list
ollama pull <your-model>
```

Test it directly once:

```powershell
ollama run <your-model> "Reply with exactly OLLAMA_OK"
```

Expected:

```text
OLLAMA_OK
```

Do not spend demo time benchmarking models. Pick one model that is fast enough on the laptop and keep it loaded.

## 3. Make Ollama reachable from the local UI / Docker

Harness OS Judge Demo Core checks:

```text
http://localhost:11434/api/tags
```

TrueForge runs in Docker in the local stack, so the OpenAI-compatible model endpoint should normally use:

```text
http://host.docker.internal:11434/v1
```

If the browser blocks the Ollama readiness check because of origin policy, start Ollama with a localhost origin allowance for the Harness OS UI. Example environment intent:

```text
OLLAMA_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Restart Ollama after changing its environment.

## 4. Start Harness OS + TrueForge + fixtures

From the repository root:

```powershell
docker compose up --build
```

Open:

| Service | URL |
|---|---|
| Harness OS | http://localhost:5173 |
| Harness OS API | http://localhost:8080 |
| TrueForge | http://localhost:8791 |
| FaultLine MCP | http://localhost:8940/mcp |
| Refund fixture | http://localhost:8950 |
| Ollama | http://localhost:11434 |

Check all local services:

```powershell
Invoke-RestMethod http://localhost:8791/healthz
Invoke-RestMethod http://localhost:8080/health
Invoke-RestMethod http://localhost:8940/health
Invoke-RestMethod http://localhost:8950/health
Invoke-RestMethod http://localhost:11434/api/tags
```

## 5. Configure Ollama as the model inside TrueForge

Open TrueForge:

```text
http://localhost:8791
```

Go to **Settings → Models** and add an **OpenAI-compatible** provider/model.

Use:

```text
Provider name: ollama-local
Base URL: http://host.docker.internal:11434/v1
API key: ollama
Model: <exact name shown by `ollama list`>
```

Why `/v1`? Ollama exposes an OpenAI-compatible API there, and TrueForge supports OpenAI-compatible model endpoints.

Save the model and test it in TrueForge with:

```text
Reply with exactly: TRUEFORGE_OLLAMA_OK
```

Expected:

```text
TRUEFORGE_OLLAMA_OK
```

If this fails, fix this before touching GitHub MCP.

### Fast diagnostics

Host works but TrueForge cannot reach Ollama:

```text
Use http://host.docker.internal:11434/v1, not http://localhost:11434/v1.
```

Model not found:

```powershell
ollama list
```

Use the exact model identifier from that output.

## 6. Configure GitHub MCP

In **TrueForge → Settings → Connectors / MCP Servers**, connect GitHub.

For the Harness OS repository:

```text
https://github.com/harshapriyag123/harness-os
```

Recommended minimum permissions for the final flow:

```text
Contents: read + write
Pull requests: read + write
Metadata: read-only
```

Attach GitHub MCP to the **harness-os agent**.

Start a new TrueForge session and verify read access first:

```text
Use GitHub MCP get_me.
Return only my GitHub username.
Do not perform any write operation.
```

Then:

```text
Use GitHub MCP to inspect the harness-os repository.
Get the default branch and read the top-level files.
READ ONLY.
Report the GitHub MCP tools actually called.
```

If GitHub tools do not appear in the session, reopen the agent, attach the connector, save, and start a fresh session.

## 7. Configure FaultLine MCP

For TrueForge inside Docker use:

```text
http://mcp-chaos:8940/mcp
```

If the UI validates from the browser instead of the container, use:

```text
http://host.docker.internal:8940/mcp
```

Required tools:

```text
reset_fixture
inject_timeout_after_success
read_effect_state
get_trace
```

The required failure semantics are:

```text
REMOTE EFFECT COMMITTED
-> SUCCESS RESPONSE LOST
-> CALLER SEES TIMEOUT
```

Never replace this with a timeout where no remote effect occurred.

## 8. Create / update the `harness-os` agent

Create an agent named exactly:

```text
harness-os
```

Attach:

```text
Model: ollama-local/<your-model>
GitHub MCP
FaultLine MCP
Sandbox: enabled
Human/tool approval: enabled
Ask-user questions: enabled
```

Use `trueforge/AGENT_INSTRUCTIONS.md` as the primary mission instructions.

The agent's critical rule is:

```text
H-005 — An irreversible operation whose remote execution state is unknown must not be blindly repeated.
```

## 9. Open the Harness OS Judge Demo Core

Open:

```text
http://localhost:5173
```

Use the floating **Judge demo** control in the lower-right corner.

The readiness cards should show:

```text
01 LOCAL MODEL      Ollama CONNECTED
02 AGENT HARNESS    TrueForge CONNECTED
03 CHAOS TOOL       FaultLine CONNECTED
04 TARGET FIXTURE   Refund CONNECTED
```

Do not start the golden demo until all four prerequisites are green.

The same drawer gives the judge the complete 10-step story and keeps the key H-005 failure visible:

```text
EXPECTED $249 -> VULNERABLE $498
```

## 10. Connect the repository in Harness OS

In Mission Control choose **Connect repo**:

```text
Repository URL: https://github.com/harshapriyag123/harness-os
Branch: main
Display name: Harness OS
```

Then choose **Inspect with TrueForge**.

## 11. Run the H-005 attack

Golden fixture:

```text
Order: ORD-1042
Expected refund: 24900 cents
```

Required vulnerable sequence:

```text
refund.create($249)
-> remote effect succeeds
-> response is intentionally lost
-> target observes timeout
-> target blindly retries
-> second refund succeeds
```

Required evidence:

```text
Expected refund  = $249
Actual refund    = $498
Effects          = 2
H-005            = FAIL
```

The Flight Recorder must show the causal chain. A model explanation alone is not proof.

## 12. Generate the remediation

The smallest valid remediation is:

```text
idempotency key
+ state verification after timeout
+ no blind retry while execution state is unknown
```

The model can propose code, but the claim is not complete until TrueForge executes the regression in its sandbox.

## 13. TrueForge sandbox gate

Show:

```text
BEFORE
refund_count = 2
H-005 = FAIL

AFTER CANDIDATE FIX
refund_count = 1
H-005 = PASS
```

Only display PASS when an actual sandbox/replay artifact exists.

## 14. Human approval — the demo climax

Before GitHub write, TrueForge must actually pause.

Harness OS should show the exact bound action:

```text
GitHub MCP tool
repository
branch
tool-call ID
```

Say to the judge:

> "The agent has produced and tested a fix, but it still cannot change the repository until a human approves this exact external action."

Approve only after showing this pause on screen.

## 15. Create the remediation PR

After approval:

```text
TrueForge
-> GitHub MCP
-> branch
-> file update / commit
-> pull request
```

Do not create the PR manually for the golden run if you are claiming the harness performed the external write.

## 16. Qodo gate

Every substantive hackathon PR should follow:

```text
branch
-> PR
-> Qodo review
-> inspect findings
-> fix or dismiss with explicit reason
-> follow-up review
-> human merge
```

Keep the public PR URL as evidence.

## 17. Exact replay

Run the exact same timeout-after-success attack after remediation.

Expected:

```text
Expected refund  = $249
Actual refund    = $249
Effects          = 1
H-005            = PASS
```

## 18. Safety Case

The final Safety Case should include:

```text
target + commit
H-005 invariant
attack/fault
pre-fix causal trace
sandbox proof
human approval
GitHub PR
Qodo evidence
post-fix exact replay
evidence hash
release recommendation
```

Use:

```text
ALLOW FOR TESTED CONDITION
```

Do not say universally certified safe.

## 19. Three-minute judge script

```text
00:00-00:15  Open Judge Demo Core: Ollama + TrueForge + FaultLine + fixture are green
00:15-00:30  Explain H-005 and the $249 refund
00:30-01:00  Run attack: remote success -> timeout -> retry -> $498
01:00-01:20  Flight Recorder: prove the causal chain
01:20-01:40  Show remediation: idempotency + state verification
01:40-02:00  Show TrueForge sandbox: before FAIL / after PASS
02:00-02:25  TrueForge pauses before GitHub mutation; show exact scope
02:25-02:35  Human approves
02:35-02:45  GitHub PR + Qodo gate
02:45-02:55  Exact replay: one refund, H-005 PASS
02:55-03:00  Safety Case: ALLOW FOR TESTED CONDITION
```

Final line:

> **CI proves your code works. Harness OS proves your agent can be trusted to act when the real world behaves unexpectedly.**

## 20. Screenshot checklist

Capture sanitized screenshots for:

```text
01 Mission Control + Judge Demo Core (4/4 green)
02 TrueForge harness-os agent showing Ollama model + MCP attachments
03 GitHub MCP real read call
04 H-005 $249 -> $498 FAIL
05 Flight Recorder causal trace
06 sandbox before/after proof
07 TrueForge approval pause
08 remediation PR + Qodo review
09 exact replay PASS
10 Safety Case
```

Never show API keys, PATs, OAuth tokens, `.env`, or password-manager UI.

## 21. Pre-demo checklist

```text
[ ] ollama list shows the chosen model
[ ] http://localhost:11434/api/tags responds
[ ] TrueForge model test says TRUEFORGE_OLLAMA_OK
[ ] GitHub MCP read test succeeds
[ ] FaultLine MCP tools are listed
[ ] refund fixture health succeeds
[ ] Harness OS Judge Demo Core shows 4/4
[ ] repository target is connected
[ ] H-005 attack can be reproduced deterministically
[ ] sandbox is available
[ ] approval is native TrueForge state
[ ] Qodo is active on the PR
[ ] exact replay uses the same fault
[ ] Safety Case only uses persisted evidence
[ ] all screenshots hide secrets
```
