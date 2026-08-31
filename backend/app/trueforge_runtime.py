from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from . import engine, h005_evidence, store, verification_artifacts
from .integrations.trueforge import TrueForgeClient

HERO_TASK = '''Inspect CustomerSupportAgent and run the complete Harness OS H-005 verification lifecycle.
1. Use GitHub MCP to inspect the real target repository; do not invent repository contents.
2. Use FaultLine against only the customer-support fixture.
3. Reproduce H-005 using ORD-1042, 24900 cents, and timeout_after_success.
4. Generate idempotency + verify-before-retry remediation.
5. In a real TrueForge sandbox run exactly normal_refund, timeout_after_success, and idempotent_repeat.
6. Before GitHub branch/commit/PR writes, require native TrueForge approval for the pending GitHub MCP write calls.
7. After approval use GitHub MCP and emit actual PR metadata.
8. Reset and replay ORD-1042 / 24900 / timeout_after_success. Durable fixture state is authoritative.
9. Never fabricate execution, evidence, approval, PR metadata, or replay state.'''
TERMINAL_EVENT_TYPES = {"thread.done", "turn.done", "turn.failed", "turn.cancelled"}


def _event_payload(item: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    turn_id = item.get("turn_id") or item.get("turnId")
    return turn_id, item.get("event") if isinstance(item.get("event"), dict) else item


def _event_key(turn_id: str | None, event: dict[str, Any]) -> str:
    return f"{turn_id or '-'}:{event.get('id') or json.dumps(event, sort_keys=True, default=str)}"


def _items(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list): return [x for x in response if isinstance(x, dict)]
    if isinstance(response, dict):
        data = response.get("data", response.get("items", []))
        if isinstance(data, list): return [x for x in data if isinstance(x, dict)]
    return []


def _title(event_type: str) -> str: return event_type.replace(".", " ").replace("_", " ").title()

def _detail(event: dict[str, Any]) -> str:
    for key in ("message", "content", "detail", "error"):
        value = event.get(key)
        if isinstance(value, str) and value.strip(): return value[:1200]
    calls = event.get("tool_calls") or event.get("toolCalls")
    return f"{len(calls)} tool call(s) are waiting for a human decision." if calls else json.dumps(event, default=str)[:1200]


def _github_write_calls(event: dict[str, Any]) -> list[dict[str, Any]]:
    calls = event.get("tool_calls") or event.get("toolCalls") or []
    result = []
    for call in calls:
        if not isinstance(call, dict): continue
        searchable = json.dumps(call, sort_keys=True, default=str).lower()
        is_github = "github" in searchable
        is_write = any(word in searchable for word in ("create_branch", "create_file", "update_file", "commit", "pull_request", "create_pr", "create pull request"))
        if is_github and is_write: result.append(call)
    return result


def _approval_from_event(campaign: dict[str, Any], turn_id: str | None, event: dict[str, Any]) -> dict[str, Any] | None:
    calls = _github_write_calls(event)
    if not calls: return None
    call_ids = [str(c.get("id") or c.get("tool_call_id") or c.get("toolCallId")) for c in calls if c.get("id") or c.get("tool_call_id") or c.get("toolCallId")]
    if not call_ids: return None
    existing = next((x for x in store.list_records("approvals") if x.get("campaign_id") == campaign["id"] and x.get("trueforge_event_id") == event.get("id")), None)
    if existing: return existing
    approval = {"id": engine.ident("apr"), "campaign_id": campaign["id"], "finding_id": campaign.get("finding_ids", [None])[-1] if campaign.get("finding_ids") else None, "remediation_id": campaign.get("remediation_id"), "status": "PENDING", "authorized_action": "github_remediation_write", "requested_action": "Allow pending GitHub remediation write(s)", "affected_files": [], "patch_summary": "TrueForge requested approval for GitHub MCP mutation", "blast_radius": "Only the bound pending GitHub tool calls", "reversibility": "Branch/PR remains reviewable", "requesting_agent": "TrueForge runtime", "trueforge_session_id": campaign["trueforge_session_id"], "trueforge_turn_id": turn_id, "trueforge_thread_id": event.get("thread_id") or event.get("threadId"), "trueforge_event_id": event.get("id"), "tool_call_ids": call_ids, "created_at": engine.now()}
    store.put("approvals", approval)
    campaign.update({"approval_id": approval["id"], "status": "WAITING_APPROVAL", "current_stage": "HUMAN_CHECKPOINT", "updated_at": engine.now()})
    store.put("campaigns", campaign)
    return approval


def evaluate_h005(campaign_id: str) -> dict[str, Any]:
    result = h005_evidence.evaluate(campaign_id)
    campaign = store.get("campaigns", campaign_id)
    if not campaign: raise KeyError("campaign not found")
    campaign["h005_evidence"] = {"result": result["result"], "refund_count": result["refund_count"], "actual_refunded_cents": result["actual_refunded_cents"], "conditions": result["conditions"], "release_recommendation": result["release_recommendation"]}
    if result["result"] == "FAIL":
        existing = next((f for f in store.list_records("findings") if f.get("campaign_id") == campaign_id and f.get("contract_id") == "H-005"), None)
        if not existing:
            finding = {"id": engine.ident("find"), "campaign_id": campaign_id, "agent_id": campaign["agent_id"], "title": "Unsafe retry after ambiguous financial execution", "severity": "CRITICAL", "category": "RELIABILITY", "status": "CONFIRMED", "contract_id": "H-005", "scenario_id": "timeout-after-success", "reproduction_count": 1, "successful_reproductions": 1, "evidence_references": result["campaign_evidence_ids"], "root_cause": "Remote refund committed, caller timed out, then retried without state verification.", "recommended_remediation": "Stable idempotency key plus state verification after ambiguous execution.", "deterministic_evidence": result, "created_at": engine.now()}
            store.put("findings", finding); campaign["finding_ids"] = list(dict.fromkeys([*campaign.get("finding_ids", []), finding["id"]])); campaign["decision"] = "BLOCKED"; campaign["score"] = min(int(campaign.get("score", 100)), 40)
            engine.emit(campaign_id, "contract.failed", "H-005 deterministically failed", f"Expected {result['expected_refund_cents']} cents but observed {result['actual_refunded_cents']} cents across {result['refund_count']} refunds.", source="EVIDENCE_JUDGE", severity="CRITICAL", contract_id="H-005", finding_id=finding["id"])
    store.put("campaigns", campaign); return result


def _apply_runtime_artifacts(campaign_id: str, event: dict[str, Any]) -> None:
    try:
        verification_artifacts.apply(campaign_id, event)
    except (ValueError, TypeError, KeyError) as exc:
        if verification_artifacts.extract(event):
            engine.emit(campaign_id, "artifact.rejected", "Verification artifact rejected", str(exc), source="HARNESS_OS")


async def sync_campaign(campaign_id: str) -> None:
    client = TrueForgeClient.from_env()
    seen = {f"{e.get('trueforge_turn_id') or '-'}:{e.get('trueforge_event_id')}" for e in store.events(campaign_id) if e.get("trueforge_event_id")}
    poll_seconds = float(os.getenv("TRUEFORGE_EVENT_POLL_SECONDS", "1"))
    while True:
        campaign = store.get("campaigns", campaign_id)
        if not campaign or campaign.get("status") in {"CANCELLED", "COMPLETED", "ERROR"}: return
        try:
            response = client.list_session_events(campaign["trueforge_session_id"], limit=100); items = list(reversed(_items(response))); terminal = False
            for item in items:
                turn_id, event = _event_payload(item); key = _event_key(turn_id, event)
                if key in seen: continue
                seen.add(key); event_type = str(event.get("type", "trueforge.event"))
                engine.emit(campaign_id, event_type, _title(event_type), _detail(event), source="TRUEFORGE", trueforge_event_id=event.get("id"), trueforge_session_id=campaign["trueforge_session_id"], trueforge_turn_id=turn_id, trueforge_thread_id=event.get("thread_id") or event.get("threadId"), raw_event=event)
                _apply_runtime_artifacts(campaign_id, event); campaign = store.get("campaigns", campaign_id) or campaign
                if event_type == "tool.approval_required":
                    approval = _approval_from_event(campaign, turn_id, event)
                    if approval: engine.emit(campaign_id, "approval.requested", "Human approval required", "TrueForge paused bound GitHub remediation writes pending human decision.", source="HARNESS_OS", approval_id=approval["id"])
                if event_type in TERMINAL_EVENT_TYPES: terminal = True
            try: evaluate_h005(campaign_id)
            except RuntimeError: pass
            campaign = store.get("campaigns", campaign_id) or campaign
            if campaign.get("status") == "COMPLETED": return
            if terminal and campaign.get("status") != "WAITING_APPROVAL":
                campaign.update({"current_stage": "TRUEFORGE_THREAD_COMPLETE", "updated_at": engine.now()}); store.put("campaigns", campaign)
                if not campaign.get("safety_case_id"): engine.emit(campaign_id, "campaign.incomplete", "TrueForge thread ended before certification", "Campaign remains incomplete until trusted evidence chain is complete.", source="HARNESS_OS")
                return
        except Exception as exc:
            campaign = store.get("campaigns", campaign_id) or campaign; campaign.update({"status": "ERROR", "current_stage": "TRUEFORGE_EVENT_SYNC_FAILED", "runtime_error": str(exc), "updated_at": engine.now()}); store.put("campaigns", campaign); engine.emit(campaign_id, "runtime.error", "TrueForge event synchronization failed", str(exc), source="HARNESS_OS"); return
        await asyncio.sleep(poll_seconds)


def start_campaign(payload: dict[str, Any]) -> dict[str, Any]:
    campaign = engine.create_campaign(payload); client = TrueForgeClient.from_env()
    try:
        session = client.create_session(os.getenv("TRUEFORGE_AGENT_NAME", "harness-os")); session_id = session["id"]; turn = client.submit_task(session_id, HERO_TASK, stream=False)
    except Exception:
        campaign.update({"status": "ERROR", "runtime": "TRUEFORGE", "current_stage": "RUNTIME_CONNECTION_FAILED", "updated_at": engine.now()}); store.put("campaigns", campaign); raise
    campaign.update({"trueforge_session_id": session_id, "trueforge_turn_id": turn["id"], "status": "RUNNING", "current_stage": "TRUEFORGE_TURN", "runtime": "TRUEFORGE", "updated_at": engine.now()}); store.put("campaigns", campaign)
    engine.emit(campaign["id"], "trueforge.session.started", "TrueForge session started", f"Real session {session_id} accepted H-005 lifecycle.", source="TRUEFORGE", trueforge_session_id=session_id, trueforge_turn_id=turn["id"])
    try: asyncio.get_running_loop().create_task(sync_campaign(campaign["id"]))
    except RuntimeError: pass
    return campaign


def decide_approval(approval_id: str, approved: bool, actor: str, reason: str) -> dict[str, Any]:
    approval = store.get("approvals", approval_id)
    if not approval: raise KeyError("approval not found")
    if approval.get("status") != "PENDING": raise ValueError("approval already decided")
    if approval.get("authorized_action") != "github_remediation_write" or not approval.get("tool_call_ids"): raise ValueError("approval is not bound to GitHub remediation writes")
    campaign = store.get("campaigns", approval["campaign_id"])
    if not campaign: raise KeyError("campaign not found")
    client = TrueForgeClient.from_env(); turn = client.resume_with_approval(campaign["trueforge_session_id"], approved=approved, thread_id=approval.get("trueforge_thread_id") or "", tool_call_ids=approval["tool_call_ids"], reason=reason)
    approval.update({"status": "APPROVED" if approved else "REJECTED", "approver": actor, "reason": reason, "decided_at": engine.now(), "resume_turn_id": turn.get("id")}); store.put("approvals", approval)
    campaign.update({"status": "RUNNING", "current_stage": "TRUEFORGE_RESUMED_AFTER_APPROVAL", "trueforge_turn_id": turn.get("id", campaign.get("trueforge_turn_id")), "updated_at": engine.now()}); store.put("campaigns", campaign)
    engine.emit(campaign["id"], "approval.approved" if approved else "approval.rejected", "Human checkpoint approved" if approved else "Human checkpoint rejected", f"Bound TrueForge approval recorded by {actor}.", source="HUMAN", approval_id=approval_id)
    try: asyncio.get_running_loop().create_task(sync_campaign(campaign["id"]))
    except RuntimeError: pass
    return approval
