# Harness OS — Live TrueForge Setup

This runbook configures the judge-facing golden path. In `HARNESS_OS_MODE=live`, Harness OS must use real TrueForge sessions, MCP tool calls, sandbox execution and approval state. It must never silently fall back to seeded demo execution.

## 1. Runtime topology

Recommended local topology:

- Harness OS UI/API: host machine
- TrueForge: Docker
- Refund fixture: Docker or host
- FaultLine / Chaos MCP: Docker or host
- GitHub: MCP connector registered in TrueForge
- OpenAI: model provider configured in TrueForge Settings

When TrueForge is containerized, remember that `localhost` inside the TrueForge container is the TrueForge container itself. If FaultLine and the fixture share a Compose network with TrueForge, use service DNS names such as `http://chaos-mcp:8940/mcp` and `http://refund-fixture:8950`.

## 2. Environment

Copy `.env.example` to `.env` and set:

```env
HARNESS_OS_MODE=live
TRUEFORGE_BASE_URL=http://127.0.0.1:<published-port>
TRUEFORGE_TOKEN=<token-if-your-install-requires-one>
TRUEFORGE_AGENT_NAME=harness-os
TRUEFORGE_MODEL_PROVIDER=openai
TRUEFORGE_MODEL=<model-selected-in-trueforge>
HARNESS_CHAOS_MCP_URL=http://chaos-mcp:8940/mcp
FIXTURE_BASE_URL=http://refund-fixture:8950
GITHUB_TARGET_REPOSITORY=harshapriyag123/harness-os
GITHUB_DEFAULT_BRANCH=main
```

Do not commit `.env`, OpenAI keys, GitHub tokens or TrueForge credentials.

## 3. Configure OpenAI in TrueForge

In TrueForge, open Settings → Models → OpenAI and add the API key there. Verify with a trivial agent prompt:

`Reply with exactly: TRUEFORGE_MODEL_OK`

Do not route model calls directly from Harness OS for the golden demo. TrueForge owns the model/agent loop.

## 4. Register the Harness OS agent

Create a named TrueForge agent with the name configured in `TRUEFORGE_AGENT_NAME` (default `harness-os`). Use `trueforge/AGENT_INSTRUCTIONS.md` as its primary instructions and load the skills under `trueforge/skills/`.

Enable the TrueForge capabilities available in your installation for sandboxing, subagents, skills, persistent sessions and human/tool approval.

## 5. Register GitHub MCP

In TrueForge Settings → Connectors / MCP Servers, register the GitHub connector for a repository you are authorized to modify. Confirm the Harness OS agent can use GitHub tools to report the repository's default branch, top-level files, runtime/language and README presence.

The judge-facing trace must show a real TrueForge tool execution rather than a hardcoded backend discovery response.

## 6. Register FaultLine / Chaos MCP

Register the MCP URL from `HARNESS_CHAOS_MCP_URL`. The initial tool contract is deliberately narrow:

- `reset_fixture`
- `inject_timeout_after_success`
- `read_effect_state`
- `get_trace`

`inject_timeout_after_success` must commit the remote refund effect first and then suppress/drop the response so the caller observes an ambiguous timeout.

Expected first-state proof:

```text
Before: refund_count = 0
Remote refund.create: SUCCESS
Caller result: TIMEOUT
After: refund_count = 1
```

## 7. Golden verification contract

Use order `ORD-1042` and refund `24900` cents. The vulnerable target retries `refund.create` after the ambiguous timeout without checking state.

The evidence judge confirms H-005 only when all four conditions are present:

1. remote effect succeeded
2. response timed out / became ambiguous
3. the same irreversible operation was retried
4. no state verification occurred between attempts

Expected vulnerable result:

```text
expected_refund_cents = 24900
actual_refund_cents   = 49800
refund_count          = 2
H-005                 = FAIL
```

## 8. Remediation and approval

The remediation must add an idempotency key and state verification after timeout. Candidate code is verified in the TrueForge sandbox before any GitHub write.

Before branch/commit/PR creation, TrueForge must emit an actual approval-required state/event. The Harness OS UI should display that pending approval and resolve the TrueForge request when the human chooses Approve or Reject. A local UI boolean is not sufficient.

## 9. Replay

After the approved remediation PR is created, replay the exact same test/fault against the candidate code.

Expected result:

```text
expected_refund_cents = 24900
actual_refund_cents   = 24900
refund_count          = 1
H-005                 = PASS
```

## 10. Safety Case

The Safety Case must contain the target, commit, H-005 rule, experiment name, pre-remediation evidence, sandbox test result, human approval evidence, GitHub PR reference, post-remediation replay evidence and `ALLOW_FOR_TESTED_CONDITION` recommendation. Hash the canonical evidence bundle with SHA-256 and display the digest.

## Judge-facing hard checkpoint

Do not call the flow live until all of these are backed by runtime evidence:

- TrueForge session — real
- OpenAI model through TrueForge — real
- GitHub MCP — real
- repository discovery — real
- FaultLine MCP — real
- remote refund success — real
- caller timeout — real
- target retry — real
- refund count = 2 — real
- H-005 failure — evidence-backed
- sandbox remediation verification — real
- TrueForge approval gate — real
- GitHub remediation PR — real
- exact attack replay — real
- Safety Case — generated from normalized evidence
