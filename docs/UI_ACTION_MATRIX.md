# UI Action Matrix — TrueForge Migration

This matrix distinguishes implemented product controls from TrueForge actions that cannot pass until a configured runtime is executed. P0/P1 does not claim P2–P4 controls complete.

| Control | Harness OS endpoint | TrueForge action | Expected result | Status |
|---|---|---|---|---|
| Connect Agent | `POST /api/v1/agents` | none | product target persisted | PASS |
| Discover | `POST /api/v1/agents/{id}/discover` | future discovery turn/GitHub MCP read | fixture HarnessIR persisted | PASS fixture; live pending |
| Generate Safety Contract | `POST .../contracts/generate` | future safety-contract Skill | H-005 available | PASS fixture; live pending |
| Start Verification | `POST /api/v1/campaigns` | create session then non-streaming turn | real session/turn IDs persisted | IMPLEMENTED; execution blocked until TrueForge is configured |
| Pause/Resume | campaign actions | TrueForge has cancel/reconnect, not generic pause | must reflect real supported semantics | FAIL; disabled-state refinement pending |
| Cancel | campaign cancel | documented running-turn cancel | cancel real turn | adapter method implemented; UI mapping pending |
| View Trace | traces endpoint | session/turn events | normalized evidence | P2 pending |
| Reproduce / Investigate / Generate Fix | findings | new chained turns/Skills | evidence-bound actions | P2/P3 pending |
| Run Sandbox Retest | remediation | real TrueForge sandbox | before=2, after=1 | P3 pending |
| Reject / Approve | approval endpoints | required-action resume turn | real runtime resumes or ends | P3 pending; local legacy action is not TrueForge approval |
| Open PR | not exposed | approval-gated GitHub MCP | real branch/commit/PR | P3 pending |
| Generate / Download Safety Case | safety-case endpoints | evidence references only | scoped case/export | existing product control; real evidence P4 pending |
| Filters / Navigation | frontend | none | local view/filter | PASS |
| Refresh/reconnect | dashboard/SSE | get session/list or subscribe events | same session recovered | association persists; event reconnect P2 pending |
