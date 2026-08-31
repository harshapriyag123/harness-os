from __future__ import annotations

import math
import os
from typing import Any

from . import store, verification_artifacts
from .integrations.trueforge import TrueForgeClient, TrueForgeError

ACTIVE_STATUSES = ("WAITING_APPROVAL", "RUNNING", "PLANNING", "PAUSED")


def _pick_campaign(campaign_id: str | None = None, agent_id: str | None = None) -> dict[str, Any] | None:
    campaigns = store.list_records("campaigns")
    if campaign_id:
        found = next((c for c in campaigns if c.get("id") == campaign_id), None)
        if found and agent_id and found.get("agent_id") != agent_id:
            return None
        return found
    if agent_id:
        campaigns = [c for c in campaigns if c.get("agent_id") == agent_id]
    for status in ACTIVE_STATUSES:
        found = next((c for c in campaigns if c.get("status") == status), None)
        if found:
            return found
    return campaigns[0] if campaigns else None


def snapshot(campaign_id: str | None = None, refresh_qodo: bool = False, agent_id: str | None = None) -> dict[str, Any]:
    campaign = _pick_campaign(campaign_id, agent_id)
    if not campaign:
        target = store.get("agents", agent_id) if agent_id else None
        return {
            "campaign": None,
            "target": target,
            "certification": None,
            "events": [],
            "approval": None,
            "selection_reason": "NO_CAMPAIGN_FOR_TARGET" if agent_id else "NO_CAMPAIGN",
        }

    cid = campaign["id"]
    target = store.get("agents", campaign.get("agent_id", "")) if campaign.get("agent_id") else None
    approvals = [a for a in store.list_records("approvals") if a.get("campaign_id") == cid]
    approval = next((a for a in approvals if a.get("status") == "PENDING"), approvals[0] if approvals else None)

    if campaign.get("campaign_kind") == "GENERIC_REPOSITORY_INSPECTION":
        certification = {
            "campaign_id": cid,
            "stage": campaign.get("current_stage"),
            "next_gate": "repository_inspection" if campaign.get("status") not in {"COMPLETED","ERROR","CANCELLED"} else "complete",
            "generic": True,
            "gates": {},
            "qodo_blocks_replay": False,
        }
    else:
        try:
            certification = verification_artifacts.certification_status(cid, refresh_qodo=refresh_qodo)
        except Exception as exc:
            certification = {
                "campaign_id": cid,
                "stage": campaign.get("current_stage"),
                "next_gate": "runtime_evidence",
                "gates": {},
                "qodo_blocks_replay": False,
                "status_error": str(exc),
            }

    return {
        "campaign": campaign,
        "target": target,
        "certification": certification,
        "events": store.events(cid)[-25:],
        "approval": approval,
        "selection_reason": "EXPLICIT" if campaign_id else ("WAITING_APPROVAL_PRIORITY" if campaign.get("status") == "WAITING_APPROVAL" else "ACTIVE_PRIORITY" if campaign.get("status") in ACTIVE_STATUSES else "LATEST"),
    }


def _positive_timeout(env_name: str, default: float, minimum: float, maximum: float) -> tuple[float, str | None]:
    raw = os.getenv(env_name)
    if raw is None or raw.strip() == "":
        return default, None
    try:
        value = float(raw)
        if not math.isfinite(value) or value < minimum or value > maximum:
            raise ValueError
        return value, None
    except (TypeError, ValueError):
        return default, f"Invalid {env_name}={raw!r}; using {default:g}s."


def trueforge_status() -> dict[str, Any]:
    try:
        configured = TrueForgeClient.from_env()
    except (TypeError, ValueError) as exc:
        return {
            "base_url": os.getenv("TRUEFORGE_BASE_URL", "http://127.0.0.1:8790").rstrip("/"),
            "agent_name": os.getenv("TRUEFORGE_AGENT_NAME", "harness-os"),
            "status": "CONFIG_ERROR",
            "retryable": True,
            "detail": f"Invalid TrueForge client configuration: {exc}",
            "diagnosis": "Fix the server-side TrueForge timeout/base configuration, then retry. Secrets are not returned to the browser.",
            "capabilities": None,
        }
    probe_timeout, warning = _positive_timeout("TRUEFORGE_PROBE_TIMEOUT_SECONDS", 4.0, 0.25, 30.0)
    effective_timeout = min(configured.timeout, probe_timeout) if configured.timeout > 0 else probe_timeout
    probe = TrueForgeClient(configured.base_url, configured.token, effective_timeout)
    base = {
        "base_url": configured.base_url,
        "agent_name": os.getenv("TRUEFORGE_AGENT_NAME", "harness-os"),
        "request_timeout_seconds": configured.timeout,
        "probe_timeout_seconds": probe.timeout,
        "configuration_warning": warning,
    }
    try:
        capabilities = probe.capabilities()
        return {
            **base,
            "status": "CONNECTED",
            "retryable": False,
            "detail": "TrueForge API responded to the live capability probe.",
            "capabilities": capabilities,
        }
    except TrueForgeError as exc:
        message = str(exc)
        lowered = message.lower()
        timed_out = "timed out" in lowered or "timeout" in lowered
        unavailable = "unavailable" in lowered
        return {
            **base,
            "status": "TIMEOUT" if timed_out else "UNAVAILABLE" if unavailable else "ERROR",
            "retryable": True,
            "detail": message,
            "diagnosis": "The local control plane could not complete a short TrueForge API probe. Verify TRUEFORGE_BASE_URL points to the API base, confirm server-side authentication/network access, then retry." if timed_out or unavailable else "TrueForge returned an unexpected response. Check the configured API base and server-side credentials.",
            "capabilities": None,
        }
