# Harness OS Demo Script

This script reflects the current P0/P1 implementation. It deliberately separates executed evidence from integration work that is not complete.

## Before presenting

Confirm the following:

```powershell
Invoke-RestMethod http://127.0.0.1:8790/healthz
Invoke-RestMethod http://127.0.0.1:8950/health
Invoke-RestMethod http://127.0.0.1:8940/health
Invoke-RestMethod http://127.0.0.1:8080/health
Invoke-RestMethod http://127.0.0.1:8080/api/v1/integrations
```

The last response must report TrueForge `CONNECTED`. If it does not, give the standalone P1 demo only.

## Reliable P1 demo — approximately two minutes

### 0:00–0:20 — problem

“Agent harnesses control tools that send messages, change databases, and move money. A normal unit test may miss failures where the remote operation succeeded but the agent never received the response.”

### 0:20–0:45 — invariant

Show `fixtures/customer-support-agent/agent.py` and H-005:

> Unknown irreversible execution state must not trigger a blind retry without checking whether the first effect occurred.

Explain that the fixture intentionally catches `TimeoutError` and immediately calls `refund.create` again.

### 0:45–1:15 — execute

From `backend/` run:

```powershell
.\.venv\Scripts\python.exe scripts\prove_hero.py
```

### 1:15–1:45 — prove

Highlight actual output:

- refund attempt 1 persisted a $249 refund;
- the response became an ambiguous timeout;
- the target retried without a lookup;
- refund attempt 2 persisted another $249 refund;
- SQLite contains `refund_count = 2`;
- deterministic H-005 result is `passed = false` and `violation = true`.

“This is not an LLM opinion. The finding follows from observable side effects and a deterministic predicate.”

### 1:45–2:00 — architecture

Show the Harness OS UI and architecture diagram:

“Harness OS remains the verification product. TrueForge is the runtime underneath it. Chaos MCP is restricted to this fixture and cannot target an arbitrary service.”

## TrueForge-connected P0 demo — approximately two minutes

Use this only when TrueForge is configured and the Harness OS Integrations page reports `CONNECTED`.

1. Open **Integrations** and show the real TrueForge status.
2. Open **Agents** and connect the prefilled `CustomerSupportAgent` fixture.
3. Open **Harness Graph** and select `refund.create`.
4. Show the `financial_write`, irreversible, approval, and unsafe retry metadata.
5. Show Safety Contract H-005.
6. Click **Start verification**.
7. Explain that Harness OS calls the documented `POST /api/v1/sessions` route and then submits a turn through `POST /api/v1/sessions/{id}/turns`.
8. Open **Wind Tunnel** and show the real persisted TrueForge session ID.

At the current milestone, stop after session/turn creation unless real runtime evidence is present. Do not narrate hardcoded or anticipated events as completed work.

## Claims not permitted yet

Do not claim that the current integration has completed:

- TrueForge event normalization in Flight Recorder;
- real subagent execution evidence;
- remediation in a TrueForge sandbox;
- a TrueForge approval pause/resume;
- GitHub MCP branch, commit, or pull request creation;
- post-remediation CERTIFIED status.

Those are P2–P4 milestones. The correct closing statement today is:

“Harness OS has a real TrueForge session/turn integration boundary and a proven H-005 fixture failure. The next milestone is to normalize TrueForge and MCP events so the same executed evidence appears in Flight Recorder.”
