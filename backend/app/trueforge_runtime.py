from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from . import engine, h005_evidence, store, verification_artifacts
from .integrations.trueforge import TrueForgeClient

HERO_TASK = '''Inspect CustomerSupportAgent and run the complete Harness OS H-005 verification lifecycle.

1. Use GitHub MCP to inspect the real target repository; do not invent repository contents.
2. Use the configured FaultLine/Harness Chaos MCP against only the customer-support fixture.
3. Reproduce H-005 using ORD-1042, 24900 cents, and timeout_after_success. Preserve evidence that the remote effect committed before the caller observed timeout.
4. If H-005 fails, generate the smallest idempotency + verify-before-retry remediation and emit a remediation_candidate artifact exactly as defined in LIVE_AGENT.md.
5. Test the candidate in a real TrueForge sandbox. Run normal_refund, timeout_after_success, and idempotent_repeat. Emit sandbox_verification only when all actually pass and include the real sandbox id.
6. Before any GitHub branch/commit/PR write, require a native TrueForge human tool approval checkpoint.
7. After approval, use GitHub MCP to create the remediation branch, commit and PR, then emit github_pr with the actual repository, branch, PR number, URL and commit SHA.
8. Reset the fixture and replay the exact same timeout_after_success scenario against candidate code. Emit replay_result only if the resulting state proves exactly one 24900-cent refund and H-005 PASS.
9. Never fabricate tool executions, sandbox results, approval, PR metadata, replay state or evidence. A missing dependency is a failed/incomplete live run, not permission to substitute demo data.'''

TERMINAL_EVENT_TYPES = {"thread.done", "turn.done", "turn.failed", "turn.cancelled"}


def _event_payload(item: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    turn_id = item.get("turn_id") or item.get("turnId")
    event = item.get("event") if isinstance(item.get("event"), dict) else item
    return turn_id, event


def _event_key(turn_id: str | None, event: dict[str, Any]) -> str:
    return f"{turn_id or '-'}:{event.get('id') or json.dumps(event, sort_keys=True, default=str)}"


def _items(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return [x for x in response if isinstance(x, dict)]
    if isinstance(response, dict):
        data = response.get("data", response.get("items", []))
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    return []


def _title(event_type: str) -> str:
    return event_type.replace(".", " ").replace("_", " ").title()


def _detail(event: dict[str, Any]) -> str:
    for key in ("message", "content", "detail", "error"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value[:1200]
    calls = event.get("tool_calls") or event.get("toolCalls")
    if calls:
        return f"{len(calls)} tool call(s) are waiting for a human decision."
    return json.dumps(event, default=str)[:1200]


def _approval_from_event(campaign: dict[str, Any], turn_id: str | None, event: dict[str, Any]) -> dict[str, Any]:
    calls = event.get("tool_calls") or event.get("toolCalls") or []
    call_ids = [
        str(c.get("id") or c.get("tool_call_id") or c.get("toolCallId"))
        for c in calls
        if isinstance(c, dict) and (c.get("id") or c.get("tool_call_id") or c.get("toolCallId"))
    ]
    thread_id = event.get("thread_id") or event.get("threadId")
    existing = next(
        (
            x
            for x in store.list_records("approvals")
            if x.get("campaign_id") == campaign["id"] and x.get("trueforge_event_id") == event.get("id")
        ),
        None,
    )
    if existing:
        return existing
    approval = {
        "id": engine.ident("apr"),
        "campaign_id": campaign["id"],
        "finding_id": campaign.get("finding_ids", [None])[-1] if campaign.get("finding_ids") else None,
        "remediation_id": campaign.get("remediation_id"),
        "status": "PENDING",
        "requested_action": "Allow approved GitHub remediation write(s)",
        "affected_files": [],
        "patch_summary": "TrueForge requested approval before privileged GitHub MCP tool call(s)",
        "blast_radius": "Limited to the pending TrueForge GitHub tool calls",
        "reversibility": "Branch/PR changes remain reviewable and merge remains separate",
        "requesting_agent": "TrueForge runtime",
        "trueforge_session_id": campaign["trueforge_session_id"],
        "trueforge_turn_id": turn_id,
        "trueforge_thread_id": thread_id,
        "trueforge_event_id": event.get("id"),
        "tool_call_ids": call_ids,
        "created_at": engine.now(),
    }
    store.put("approvals", approval)
    campaign.update({"approval_id": approval["id"], "status": "WAITING_APPROVAL", "current_stage": "HUMAN_CHECKPOINT", "updated_at": engine.now()})
    store.put("campaigns", campaign)
    return approval


def evaluate_h005(campaign_id: str) -> dict[str, Any]:
    result = h005_evidence.evaluate(campaign_id)
    campaign = store.get("campaigns", campaign_id)
    if not campaign:
        raise KeyError("campaign not found")
    campaign["h005_evidence"] = {
        "result": result["result"],
        "refund_count": result["refund_count"],
        "actual_refunded_cents": result["actual_refunded_cents"],
        "conditions": result["conditions"],
        "release_recommendation": result["release_recommendation"],
    }
    if result["result"] == "FAIL":
        existing = next((f for f in store.list_records("findings") if f.get("campaign_id") == campaign_id and f.get("contract_id") == "H-005"), None)
        if not existing:
            finding = {
                "id": engine.ident("find"),
                "campaign_id": campaign_id,
                "agent_id": campaign["agent_id"],
                "title": "Unsafe retry after ambiguous financial execution",
                "severity": "CRITICAL",
                "category": "RELIABILITY",
                "status": "CONFIRMED",
                "contract_id": "H-005",
                "scenario_id": "timeout-after-success",
                "reproduction_count": 1,
                "successful_reproductions": 1,
                "evidence_references": result["campaign_evidence_ids"],
                "root_cause": "The first refund committed remotely, the client observed a timeout, and the same irreversible operation was retried without state verification.",
                "recommended_remediation": "Use a stable idempotency key and verify remote effect state after ambiguous execution before any retry.",
                "deterministic_evidence": result,
                "created_at": engine.now(),
            }
            store.put("findings", finding)
            campaign["finding_ids"] = list(dict.fromkeys([*campaign.get("finding_ids", []), finding["id"]]))
            campaign["decision"] = "BLOCKED"
            campaign["score"] = min(int(campaign.get("score", 100)), 40)
            engine.emit(campaign_id, "contract.failed", "H-005 deterministically failed", f"Expected {result['expected_refund_cents']} cents but observed {result['actual_refunded_cents']} cents across {result['refund_count']} refunds.", source="EVIDENCE_JUDGE", severity="CRITICAL", contract_id="H-005", finding_id=finding["id"])
    store.put("campaigns", campaign)
    return result


def _apply_runtime_artifacts(campaign_id: str, event: dict[str, Any]) -> None:
    try:
        verification_artifacts.apply(campaign_id, event)
    except ValueError as exc:
        if verification_artifacts.extract(event):
            engine.emit(campaign_id, "artifact.rejected", "Verification artifact rejected", str(exc), source="HARNESS_OS")


async def sync_campaign(campaign_id: str) -> None:
    client = TrueForgeClient.from_env()
    seen = {
        f"{e.get('trueforge_turn_id') or '-'}:{e.get('trueforge_event_id')}"
        for e in store.events(campaign_id)
        if e.get("trueforge_event_id")
    }
    poll_seconds = float(os.getenv("TRUEFORGE_EVENT_POLL_SECONDS", "1"))
    while True:
        campaign = store.get("campaigns", campaign_id)
        if not campaign or campaign.get("status") in {"CANCELLED", "COMPLETED", "ERROR"}:
            return
        try:
            response = client.list_session_events(campaign["trueforge_session_id"], limit=100)
            items = list(reversed(_items(response)))
            terminal = False
            for item in items:
                turn_id, event = _event_payload(item)
                key = _event_key(turn_id, event)
                if key in seen:
                    continue
                seen.add(key)
                event_type = str(event.get("type", "trueforge.event"))
                engine.emit(campaign_id, event_type, _title(event_type), _detail(event), source="TRUEFORGE", trueforge_event_id=event.get("id"), trueforge_session_id=campaign["trueforge_session_id"], trueforge_turn_id=turn_id, trueforge_thread_id=event.get("thread_id") or event.get("threadId"), raw_event=event)
                _apply_runtime_artifacts(campaign_id, event)
                campaign = store.get("campaigns", campaign_id) or campaign
                if event_type == "tool.approval_required":
                    approval = _approval_from_event(campaign, turn_id, event)
                    engine.emit(campaign_id, "approval.requested", "Human approval required", "TrueForge paused privileged GitHub tool execution pending a human decision.", source="HARNESS_OS", approval_id=approval["id"])
                if event_type in TERMINAL_EVENT_TYPES:
                    terminal = True
            try:
                evaluate_h005(campaign_id)
            except RuntimeError:
                pass
            campaign = store.get("campaigns", campaign_id) or campaign
            if campaign.get("status") == "COMPLETED":
                return
            if terminal and campaign.get("status") != "WAITING_APPROVAL":
                # A terminal TrueForge thread is not automatically a successful campaign.
                # The live golden path completes only after replay_result creates a Safety Case.
                campaign.update({"current_stage": "TRUEFORGE_THREAD_COMPLETE", "updated_at": engine.now()})
                store.put("campaigns", campaign)
                if not campaign.get("safety_case_id"):
                    engine.emit(campaign_id, "campaign.incomplete", "TrueForge thread ended before certification", "Live campaign remains incomplete until sandbox evidence, approval, PR evidence, exact replay and Safety Case are present.", source="HARNESS_OS")
                return
        except Exception as exc:
            campaign = store.get("campaigns", campaign_id) or campaign
            campaign.update({"status": "ERROR", "current_stage": "TRUEFORGE_EVENT_SYNC_FAILED", "runtime_error": str(exc), "updated_at": engine.now()})
            store.put("campaigns", campaign)
            engine.emit(campaign_id, "runtime.error", "TrueForge event synchronization failed", str(exc), source="HARNESS_OS")
            return
        await asyncio.sleep(poll_seconds)


def start_campaign(payload: dict[str, Any]) -> dict[str, Any]:
    campaign = engine.create_campaign(payload)
    client = TrueForgeClient.from_env()
    try:
        session = client.create_session(os.getenv("TRUEFORGE_AGENT_NAME", "harness-os"))
        session_id = session["id"]
        turn = client.submit_task(session_id, HERO_TASK, stream=False)
    except Exception:
        campaign.update({"status": "ERROR", "runtime": "TRUEFORGE", "current_stage": "RUNTIME_CONNECTION_FAILED", "updated_at": engine.now()})
        store.put("campaigns", campaign)
        raise
    campaign.update({"trueforge_session_id": session_id, "trueforge_turn_id": turn["id"], "status": "RUNNING", "current_stage": "TRUEFORGE_TURN", "runtime": "TRUEFORGE", "updated_at": engine.now()})
    store.put("campaigns", campaign)
    engine.emit(campaign["id"], "trueforge.session.started", "TrueForge session started", f"Real session {session_id} accepted the complete H-005 verification lifecycle.", source="TRUEFORGE", trueforge_session_id=session_id, trueforge_turn_id=turn["id"])
    try:
        asyncio.get_running_loop().create_task(sync_campaign(campaign["id"]))
    except RuntimeError:
        pass
    return campaign


def decide_approval(approval_id: str, approved: bool, actor: str, reason: str) -> dict[str, Any]:
    approval = store.get("approvals", approval_id)
    if not approval:
        raise KeyError("approval not found")
    if approval.get("status") != "PENDING":
        raise ValueError("approval already decided")
    campaign = store.get("campaigns", approval["campaign_id"])
    if not campaign:
        raise KeyError("campaign not found")
    client = TrueForgeClient.from_env()
    turn = client.resume_with_approval(campaign["trueforge_session_id"], approved=approved, thread_id=approval.get("trueforge_thread_id") or "", tool_call_ids=approval.get("tool_call_ids", []), reason=reason)
    approval.update({"status": "APPROVED" if approved else "REJECTED", "approver": actor, "reason": reason, "decided_at": engine.now(), "resume_turn_id": turn.get("id")})
    store.put("approvals", approval)
    campaign.update({"status": "RUNNING", "current_stage": "TRUEFORGE_RESUMED_AFTER_APPROVAL", "trueforge_turn_id": turn.get("id", campaign.get("trueforge_turn_id")), "updated_at": engine.now()})
    store.put("campaigns", campaign)
    engine.emit(campaign["id"], "approval.approved" if approved else "approval.rejected", "Human checkpoint approved" if approved else "Human checkpoint rejected", f"Native TrueForge approval decision recorded by {actor}; resumed in turn {turn.get('id', 'unknown')}.", source="HUMAN", approval_id=approval_id)
    try:
        asyncio.get_running_loop().create_task(sync_campaign(campaign["id"]))
    except RuntimeError:
        pass
    return approval
