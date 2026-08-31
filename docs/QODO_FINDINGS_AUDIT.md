# Qodo findings audit

This document is a repository-wide remediation ledger for Qodo feedback across the Harness OS pull-request history. It distinguishes historical fixes from regressions found in the current codebase and from the fixes made on `fix/all-qodo-findings`.

## Evidence pipeline: PRs #3, #4, #5

Qodo's early reviews focused on evidence provenance and certification integrity. The findings included untrusted text being interpreted as artifacts, rejected artifacts being persisted, replay/order mismatches, unrelated approvals authorizing GitHub writes, fabricated/mutable baselines, incomplete evidence hashes, arbitrary sandbox test acceptance, unbound GitHub PR outputs, duplicate Safety Cases, and replay state not being tied to the expected order.

The current pipeline retains the hardening introduced through PR #5: artifacts are accepted only from structured `artifact.output` events; sandbox verification requires exactly the named PASS tests; immutable H-005 baseline evidence is required; GitHub PR evidence is matched against structured outputs from approval-bound GitHub calls; replay is checked against durable fixture evidence; persisted replay evidence is part of the Safety Case hash; and Safety Case creation is idempotent for a replay artifact.

## Documentation/deployment: PRs #6, #7, #8

Qodo identified a stale README state example, public-frontend CORS problems, shell/path portability problems, invalid PowerShell examples, and missing Docker Compose propagation of `HARNESS_OS_CORS_ORIGINS`.

Current audit result:

- The stale `state.status == "completed"` example is no longer present in the current README.
- Cross-platform startup/CORS documentation was already corrected by the earlier follow-up.
- This branch fixes the remaining Compose regression by propagating `HARNESS_OS_CORS_ORIGINS` and the relevant runtime variables into the API container.

## Integration evidence: PR #9

Qodo identified three evidence-presentation risks:

1. static integration labels could be mistaken for live health;
2. Qodo identity was accepted using a substring match, allowing an impostor login containing `qodo`;
3. Qodo author/timestamp provenance returned by the backend was not visible in the product.

This branch fixes all three:

- FaultLine is backed by an actual health probe; GitHub MCP is now labeled `MANAGED_NOT_PROBED` until tool evidence exists rather than being represented as a health assertion.
- certification-grade Qodo evidence accepts only exact configured bot logins (default `qodo-code-review[bot]`);
- Mission Control renders Qodo author/timestamp provenance when available.

## Certification/Qodo gate: PR #10

Qodo identified stale-commit review acceptance, spoofable Qodo identity, GET-triggered state mutation, first-page-only GitHub review retrieval, blank target fallback, parsing failures that could kill sync, stale/cross-PR cache acceptance, and repeated polling/network work.

This branch hardens that path:

- Qodo reviews are bound to repository + PR number + the exact reviewed `commit_id`.
- issue comments can be shown as informational evidence, but only an official Qodo review on the exact remediation commit can unlock certification.
- blank explicit repository/PR inputs fail closed instead of falling back to the global demo target.
- GitHub comments/reviews are paginated with a bounded page count.
- malformed/unexpected GitHub responses return `UNAVAILABLE` rather than escaping into campaign sync.
- cached Qodo evidence is accepted only when its proof matches repository, PR, commit, and review kind.
- a transient retrieval failure never overwrites already verified exact-commit evidence.
- certification reads default to cached/read-only evidence; certification-grade refresh is reserved for explicit workflow transitions.

## Approval-first UI: PR #11

Qodo identified a one-click alternate approval path, stale approval state crossing campaigns, and a pending approval being hidden by a more recently updated completed campaign.

The running application is now a single Mission Control root. Its approval flow validates both `approval.campaign_id == campaign.id` and `campaign.agent_id == selectedTarget.id` immediately before the decision, requires review then confirmation, and displays the exact bound GitHub MCP calls. The atomic operator snapshot prioritizes `WAITING_APPROVAL` before other active/completed campaigns.

## Multi-repository workspace: PR #12

Qodo identified seven issues: generic repositories inheriting H-005 contracts/evaluation, generic inspections not completing correctly, lack of active-target selection, prompt injection through target metadata, unverified repositories being marked READY, and serial public-health probes.

This branch fixes the remaining regressions:

- generic targets receive a separate `GENERIC_REPOSITORY_ASSESSMENT` contract (`G-001..G-003`) and never an H-005 contract;
- generic campaigns skip H-005/artifact certification processing and terminal TrueForge events map to COMPLETED/ERROR/CANCELLED;
- Mission Control has explicit active-target selection;
- branch values are narrowly validated and target metadata is serialized as untrusted JSON data in the TrueForge prompt; display names are not interpolated into privileged instructions;
- a public GitHub repository and branch must be verified and resolve to a commit SHA before the target becomes READY;
- public service probes run concurrently and use a short TTL cache.

## Mission Control: PR #13

Qodo identified four bugs: approval crossing the selected target, polling overwriting a newly started inspection, ES2020-incompatible `.at()`/`replaceAll()`, and an invalid probe-timeout environment value crashing the status endpoint.

This branch fixes all four:

- approval decisions are target + campaign bound;
- selected-target snapshots never fall back to another repository, inspection requests invalidate older polls, and stale responses are ignored with request tokens;
- `.at()` and `replaceAll()` were removed in favor of ES2020-compatible indexing/regex replacement;
- TrueForge probe timeout configuration is validated, bounded, and falls back safely with a visible configuration warning.

## Additional defense in depth in this branch

- generic repository inspection refuses to run unless the target carries server-side repository verification evidence;
- runtime artifact parsing is contained so a malformed structured artifact is emitted as `artifact.rejected` instead of killing the whole TrueForge sync loop;
- `decide_approval` now verifies that the campaign is still `WAITING_APPROVAL` before resuming TrueForge;
- public service timeouts are bounded and invalid timeout configuration falls back safely;
- Docker Compose no longer silently drops public UI CORS configuration.

## Verification status

The branch includes regression tests for exact Qodo bot identity, exact commit binding, stale review rejection, blank target fail-closed behavior, generic target isolation, branch/prompt hardening, target-scoped operator snapshots, WAITING_APPROVAL priority, and invalid TrueForge probe timeout handling.

These tests have been added to the repository. This document does **not** claim they passed until CI or a local test run provides execution evidence.
