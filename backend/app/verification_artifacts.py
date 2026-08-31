from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from . import engine, store

ARTIFACT_TYPES = {
    "remediation_candidate",
    "sandbox_verification",
    "github_pr",
    "replay_result",
}


def _walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _json_objects_from_text(text: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            objects.append(parsed)
    return objects


def extract(event: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in _walk(event):
        candidates: list[dict[str, Any]] = []
        if isinstance(value, dict):
            candidates.append(value)
        elif isinstance(value, str) and "artifact_type" in value:
            candidates.extend(_json_objects_from_text(value))
        for candidate in candidates:
            if candidate.get("artifact_type") not in ARTIFACT_TYPES:
                continue
            key = json.dumps(candidate, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                found.append(candidate)
    return found


def _latest_finding(campaign: dict[str, Any]) -> dict[str, Any] | None:
    ids = campaign.get("finding_ids", [])
    return store.get("findings", ids[-1]) if ids else None


def _put_artifact(campaign_id: str, artifact: dict[str, Any], event_id: str | None) -> dict[str, Any]:
    digest = hashlib.sha256(json.dumps(artifact, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    existing = next(
        (
            item
            for item in store.list_records("verification_artifacts")
            if item.get("campaign_id") == campaign_id and item.get("sha256") == digest
        ),
        None,
    )
    if existing:
        return existing
    record = {
        "id": engine.ident("artifact"),
        "campaign_id": campaign_id,
        "artifact_type": artifact["artifact_type"],
        "payload": artifact,
        "source_event_id": event_id,
        "sha256": digest,
        "created_at": engine.now(),
    }
    return store.put("verification_artifacts", record)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def apply(campaign_id: str, event: dict[str, Any]) -> list[dict[str, Any]]:
    campaign = store.get("campaigns", campaign_id)
    if not campaign:
        raise KeyError("campaign not found")
    applied: list[dict[str, Any]] = []
    for artifact in extract(event):
        record = _put_artifact(campaign_id, artifact, event.get("id"))
        kind = artifact["artifact_type"]
        if kind == "remediation_candidate":
            _require(bool(artifact.get("patch")), "remediation_candidate.patch is required")
            _require(bool(artifact.get("idempotency_key_strategy")), "idempotency key strategy is required")
            _require(bool(artifact.get("state_verification_strategy")), "state verification strategy is required")
            finding = _latest_finding(campaign)
            remediation = next(
                (
                    item
                    for item in store.list_records("remediations")
                    if item.get("campaign_id") == campaign_id and item.get("source_artifact_id") == record["id"]
                ),
                None,
            )
            if not remediation:
                remediation = store.put(
                    "remediations",
                    {
                        "id": engine.ident("rem"),
                        "campaign_id": campaign_id,
                        "finding_id": finding.get("id") if finding else None,
                        "status": "CANDIDATE",
                        "patch_summary": artifact.get("summary", "Idempotent verify-before-retry remediation"),
                        "candidate_patch": artifact["patch"],
                        "idempotency_key_strategy": artifact["idempotency_key_strategy"],
                        "state_verification_strategy": artifact["state_verification_strategy"],
                        "source_artifact_id": record["id"],
                        "created_at": engine.now(),
                    },
                )
            campaign.update({"remediation_id": remediation["id"], "current_stage": "REMEDIATION_CANDIDATE", "updated_at": engine.now()})
            engine.emit(campaign_id, "remediation.generated", "Candidate remediation generated", remediation["patch_summary"], source="TRUEFORGE", remediation_id=remediation["id"], artifact_id=record["id"])
        elif kind == "sandbox_verification":
            tests = artifact.get("tests") or []
            passed = sum(1 for test in tests if isinstance(test, dict) and test.get("status") == "PASS")
            failed = sum(1 for test in tests if isinstance(test, dict) and test.get("status") == "FAIL")
            _require(len(tests) >= 3, "sandbox_verification must include at least three tests")
            _require(passed >= 3 and failed == 0, "sandbox verification requires 3+ PASS and 0 FAIL")
            _require(bool(artifact.get("trueforge_sandbox_id")), "trueforge_sandbox_id is required")
            remediation = store.get("remediations", campaign.get("remediation_id", ""))
            _require(remediation is not None, "sandbox verification requires a remediation candidate")
            remediation.update({"status": "SANDBOX_VERIFIED", "sandbox_results": {"passed": passed, "failed": failed, "tests": tests, "trueforge_sandbox_id": artifact["trueforge_sandbox_id"]}, "sandbox_artifact_id": record["id"], "updated_at": engine.now()})
            store.put("remediations", remediation)
            campaign.update({"current_stage": "SANDBOX_VERIFIED", "sandbox_verified": True, "updated_at": engine.now()})
            engine.emit(campaign_id, "sandbox.passed", "TrueForge sandbox verification passed", f"{passed}/{len(tests)} tests passed with no failures.", source="SANDBOX", remediation_id=remediation["id"], artifact_id=record["id"])
        elif kind == "github_pr":
            _require(campaign.get("sandbox_verified") is True, "GitHub PR evidence cannot precede sandbox verification")
            approval = store.get("approvals", campaign.get("approval_id", ""))
            _require(approval is not None and approval.get("status") == "APPROVED", "GitHub PR evidence requires approved TrueForge checkpoint")
            for field in ("repository", "branch", "pr_number", "pr_url", "commit_sha"):
                _require(bool(artifact.get(field)), f"github_pr.{field} is required")
            campaign.update({"github_pr": {key: artifact[key] for key in ("repository", "branch", "pr_number", "pr_url", "commit_sha")}, "current_stage": "REMEDIATION_PR_CREATED", "updated_at": engine.now()})
            engine.emit(campaign_id, "github.pr.created", "Remediation PR created", str(artifact["pr_url"]), source="GITHUB MCP", artifact_id=record["id"], pr_number=artifact["pr_number"], commit_sha=artifact["commit_sha"])
        elif kind == "replay_result":
            _require(bool(campaign.get("github_pr")), "replay_result requires GitHub PR evidence")
            _require(artifact.get("scenario") == "timeout_after_success", "replay must use timeout_after_success")
            _require(int(artifact.get("expected_refund_cents", 0)) == 24900, "replay expected refund must be 24900 cents")
            _require(int(artifact.get("actual_refund_cents", 0)) == 24900, "replay must prove exactly one 24900-cent refund")
            _require(int(artifact.get("refund_count", 0)) == 1, "replay must prove refund_count=1")
            _require(artifact.get("h005") == "PASS", "replay must explicitly pass H-005")
            campaign.update({"replay": artifact, "current_stage": "REPLAY_PASSED", "decision": "ALLOW_FOR_TESTED_CONDITION", "score": max(int(campaign.get("score", 0)), 98), "updated_at": engine.now()})
            engine.emit(campaign_id, "replay.passed", "Exact fault replay passed", "Same timeout-after-success condition produced exactly one $249 refund and H-005 PASS.", source="EVIDENCE_JUDGE", artifact_id=record["id"])
            case = engine.create_safety_case(campaign_id)
            campaign = store.get("campaigns", campaign_id) or campaign
            campaign.update({"status": "COMPLETED", "progress": 100, "safety_case_id": case["id"], "updated_at": engine.now()})
            store.put("campaigns", campaign)
        store.put("campaigns", campaign)
        applied.append(record)
    return applied
