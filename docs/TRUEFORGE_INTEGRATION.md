# TrueForge Integration

Harness OS uses TrueForge's supported HTTP API rather than copying or modifying its internals.

Official references checked for this implementation:

- https://github.com/truefoundry/trueforge
- https://trueforge.dev/api/overview
- https://trueforge.dev/api-reference/agent-sessions/create-a-session
- https://trueforge.dev/api-reference/agent-sessions/create-and-execute-a-turn-in-a-session
- https://trueforge.dev/api-reference/agent-sessions/subscribe-to-a-running-turn

## Start TrueForge

Local development:

```powershell
npx @truefoundry/trueforge@latest
```

The official local server defaults to port 8790 and uses SQLite. Keep local mode on localhost. The official repository's Docker Compose stack exposes its server on host port 8791 and uses Postgres plus Redis.

## Connection contract

Set `TRUEFORGE_BASE_URL` (for example `http://127.0.0.1:8790`) and, when authentication is configured, `TRUEFORGE_TOKEN`. Harness OS calls only documented routes:

- capabilities: `GET /api/v1/capabilities`
- create session: `POST /api/v1/sessions` with `{ "agent": { "name": "harness-os" } }`
- retrieve session: `GET /api/v1/sessions/{session_id}`
- submit task: `POST /api/v1/sessions/{session_id}/turns` with user-message input, `previous_turn_id: "auto"`, and `stream`
- session events: `GET /api/v1/sessions/{session_id}/events`
- turn events/reconnect: documented turn event and subscription routes
- cancellation: documented session running-turn cancellation route

TrueForge turns may stop with required actions such as `tool.approval_required`. Approval is resumed with a new chained turn containing the required responses; P3 will implement this after a real P0/P1 session is executable.

## Resource setup

Configure the model, the Harness OS Chaos MCP URL, GitHub MCP, required Skills, and a sandbox in TrueForge itself. The Harness OS primary agent lives under `trueforge/agents/harness-os/`; modular Skills remain under `trueforge/skills/`. Harness OS stores product entities and TrueForge associations, while TrueForge owns execution/session persistence.

No server-side credentials are sent to the browser. Harness OS does not silently fall back to the retired scripted runtime.
