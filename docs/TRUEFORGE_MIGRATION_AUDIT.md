# TrueForge Migration Audit

Audit date: 2026-08-28. TrueForge contracts were checked against the official repository, SDK documentation, and API reference before implementation.

| Current component | Current implementation | Keep / Replace / Modify | TrueForge capability used | Migration plan |
|---|---|---|---|---|
| React control plane | Harness OS-specific pages and SSE client | KEEP | none directly | Continue consuming only Harness OS APIs |
| FastAPI gateway | Product API and normalized SSE | KEEP/MODIFY | HTTP API client | Persist TrueForge IDs and normalize real events |
| Campaign orchestration | `engine.run_campaign` emits timed scripted events | REPLACE | session + turn | One campaign maps to one real TrueForge session |
| Session state | fabricated `tf_demo_*` ID | REPLACE | persistent session | Store returned session ID; retrieve after refresh/restart |
| Subagents | hardcoded labels/events | REPLACE | dynamic subagents/threads | Normalize `thread.created` and thread events |
| Sandbox | textual demo event | REPLACE | configured TrueForge sandbox | Require real sandbox events/evidence before VERIFIED |
| Approval | local SQLite decision releases local task | REPLACE in P3 | `tool.approval_required` plus resume turn | UI decision must be submitted as a real resume input |
| Harness discovery | deterministic local JSON parsing | KEEP for fixture; MODIFY for live | GitHub MCP + discovery Skill | Turn output must validate as HarnessIR |
| Chaos MCP | fixture-only MCP, previously in-memory effects | MODIFY | MCP server | Execute the real local fixture side effect and preserve trace |
| Customer fixture | one static JSON file | REPLACE | target/test MCP input | SQLite test service with observable refund effects |
| H-005 evaluator | hardcoded finding sequence | REPLACE | deterministic evidence judge | Evaluate recorded effect/timeout/retry/lookup sequence |
| Findings/Safety Cases | Harness OS SQLite entities | KEEP/MODIFY | TrueForge evidence references | Product state remains in Harness OS; execution IDs come from TrueForge |

## Immediate P0/P1 decision

The old scripted campaign is not evidence of TrueForge execution and must not be shown as connected. Until a reachable/configured TrueForge instance exists, integrations report an actual error/not-configured state. P0 adds the official HTTP adapter. P1 proves the vulnerable fixture and H-005 deterministically without claiming that the unavailable runtime executed it.
