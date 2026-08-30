# Adversarial QA Audit

> Superseded for runtime claims by `docs/TRUEFORGE_MIGRATION_AUDIT.md`: the earlier demo golden-path test exercised a local scripted engine, not TrueForge. It remains historical evidence for Harness OS product persistence only.

Date: 2026-08-28. This records controls exercised by build/API tests in this pass. Browser automation is not installed, so controls marked source/build verified were not represented as pointer-click E2E evidence.

| CONTROL | PAGE | EXPECTED ACTION | ACTUAL ACTION | API CALLED | PERSISTED? | ERROR HANDLED? | RESULT |
|---|---|---|---|---|---|---|---|
| Navigation (10 items) | shell | open named view | React state opens operational view | view-dependent | n/a | n/a | PASS (build/source) |
| Workspace | shell | no unavailable mutation | disabled with explanation | — | n/a | n/a | PASS |
| Search | shell | filter trace/activity | filters event title/detail | — | no | n/a | PASS |
| Connect Agent | Agents/Command | four-step validated connection | creates, discovers, generates contract | agents/discover/contracts | yes | visible error bar | PASS (API test) |
| Discover Harness | Agents | deterministic discovery | parses fixture into HarnessIR | agent discover | yes | visible error bar | PASS (API test) |
| Graph node | Graph | inspect evidence | opens details drawer | graph | yes | empty state | PASS |
| Start verification | Command | create/run campaign | persisted campaign and task | campaigns | yes | duplicate disabled | PASS (API test) |
| Pause/Resume/Cancel | Wind Tunnel | lifecycle transition | guarded backend transition | campaign action | yes | visible error | PASS (source/API contract) |
| View Trace | Wind/Findings | open trace | opens persisted Recorder | campaign traces | yes | empty state | PASS |
| Reject | Approvals | persist reject/no write | records rejection and BLOCKED case | approval reject | yes | duplicate disabled | PASS (source/API contract) |
| Approve | Approvals | authorize remediation/reverify | persisted decision, demo apply, replay | approval approve | yes | duplicate disabled | PASS (API test) |
| Download JSON | Safety Cases | download complete case | Blob download of API entity | safety cases | yes | empty state | PASS (build/source) |
| Integrations | Integrations | show honest state | demo/live statuses from server | integrations | metadata | load failure does not fake connection | PASS |

## Golden-path execution result

`python -m unittest discover -s tests -v` executed Connect → Discover → Contract → Campaign → timeout-after-success → H-005 failure → 3/3 reproduction → remediation verification → approval → reverification → hashed Safety Case → CERTIFIED. Result: **PASS**.

Frontend `npm run build`: **PASS**. Backend import/route check: **PASS**, 29 FastAPI routes.

## Remaining limitations / honest failures

- TrueForge, GitHub, and model-provider live adapters are not implemented; live mode reports NOT CONFIGURED and never falls back to fixtures.
- Browser pointer-level E2E, accessibility automation, mobile viewport snapshots, SSE reconnect/resume browser testing, finding reproduction/dismiss buttons, editable contract UI, and printable HTML report remain incomplete.
- The repository has no authentication/RBAC. SQLite is suitable for the local demo, not a horizontally scaled control plane.
- The secondary indirect-injection fixture and advanced graph zoom/pan/edge filters were intentionally deferred behind the complete hero path.
