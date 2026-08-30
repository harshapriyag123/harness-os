# Harness OS Functional Audit

Audit date: 2026-08-28. Scope: complete repository before this implementation pass.

## Architecture found

- Frontend: one React/Vite component, local state, and a four-function fetch wrapper; no router, forms, query layer, tests, or error handling.
- Backend: three FastAPI modules using process-local dictionaries and a timed scripted campaign; no database, repositories, structured errors, tests, or live/demo boundary.
- Integrations: a generic Chaos MCP tool. TrueForge consists of instruction/skill files; GitHub has no adapter.

## Control matrix

| UI Control | Current Behavior | Required Behavior | Frontend Function | Backend Endpoint | Persistence? | External Integration? | Approval? | Status at audit |
|---|---|---|---|---|---|---|---|---|
| Workspace | dead button | explain fixed workspace | disabled control | — | no | no | no | incomplete |
| Navigation | local view swap | navigate to operational views | `setActive` | view APIs | no | no | no | partial |
| Settings | dead button | integration status | load integrations | `GET /api/v1/integrations` | metadata | all | no | incomplete |
| Search | inert input | filter current view | `setSearch` | list endpoints | no | no | no | incomplete |
| Verify Agent | starts hardcoded timer | connect/discover/contract/campaign workflow | workflow mutations | agent/campaign endpoints | yes | optional TrueForge | no | fake |
| View Architecture | dead button | open graph | navigation | graph endpoint | yes | no | no | incomplete |
| Harness Graph | static cards | discovered nodes/details | `selectNode` | graph endpoint | yes | repo parser | no | fake |
| Safety Contract | static strings | generated persisted invariants | contract mutation | contract endpoints | yes | optional model | no | fake |
| Campaign controls | absent | pause/resume/cancel/trace | campaign mutations | campaign control endpoints | yes | TrueForge | no | missing |
| Flight Recorder | in-memory SSE | persisted trace timeline | load/subscribe | traces/events | yes | Chaos MCP | no | partial |
| Findings | display only | evidence-based finding actions | finding mutations | finding endpoints | yes | sandbox | varies | incomplete |
| Reject | dead button | persist rejection and block write | approval mutation | approval reject | yes | no | human | dead |
| Approve | releases memory event | persist decision then authorized action | approval mutation | approval approve | yes | GitHub adapter | human | partial |
| Safety Case | static computed card | persisted deterministic case | load/download | safety-case endpoints | yes | no | no | fake |

## Prototype debt found

Hardcoded target, graph, contract, metrics, finding, case and success results; `asyncio.sleep` drives fake progress; refresh loses all state; API errors are ignored; SSE cannot resume; TrueForge is always labeled connected; demo/live modes are not separated; Chaos MCP lacks the required fixture-only named tools. README Qodo placeholders are legitimate and remain explicitly unfilled because evidence must not be fabricated.

This is the pre-change audit. Post-change evidence is recorded in `docs/QA_AUDIT.md` and automated tests.
