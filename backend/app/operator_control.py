from __future__ import annotations

import math
import os
import threading
import time
from typing import Any
from urllib.parse import urlparse

from . import store, verification_artifacts
from .integrations.trueforge import TrueForgeClient, TrueForgeError
from .integrations.trueforge.client import DEFAULT_TRUEFORGE_BASE_URL, DEFAULT_TRUEFORGE_AGENT_NAME

ACTIVE_STATUSES = ("WAITING_APPROVAL", "RUNNING", "PLANNING", "PAUSED")
_TRUEFORGE_STATUS_LOCK = threading.Lock()
_TRUEFORGE_STATUS_CACHE: dict[str, Any] = {"value": None, "expires_at": 0.0}

def _status_cache_seconds() -> float:
    value, _ = _positive_timeout("TRUEFORGE_STATUS_CACHE_SECONDS", 60.0, 5.0, 600.0)
    return value

def _rate_limit_cache_seconds() -> float:
    value, _ = _positive_timeout("TRUEFORGE_RATE_LIMIT_CACHE_SECONDS", 60.0, 10.0, 900.0)
    return value

def _cached_trueforge_status() -> dict[str, Any] | None:
    now = time.monotonic()
    with _TRUEFORGE_STATUS_LOCK:
        value = _TRUEFORGE_STATUS_CACHE.get("value")
        expires_at = float(_TRUEFORGE_STATUS_CACHE.get("expires_at") or 0.0)
        if not isinstance(value, dict) or expires_at <= now:
            return None
        remaining = max(0, int(math.ceil(expires_at - now)))
        return {**value, "cached": True, "retry_after_seconds": remaining if value.get("status") == "RATE_LIMITED" else value.get("retry_after_seconds", 0)}

def _store_trueforge_status(value: dict[str, Any], ttl: float) -> dict[str, Any]:
    expires_at = time.monotonic() + ttl
    with _TRUEFORGE_STATUS_LOCK:
        _TRUEFORGE_STATUS_CACHE["value"] = dict(value)
        _TRUEFORGE_STATUS_CACHE["expires_at"] = expires_at
    return {**value, "cached": False, "retry_after_seconds": int(math.ceil(ttl)) if value.get("status") == "RATE_LIMITED" else value.get("retry_after_seconds", 0)}

def _pick_campaign(campaign_id: str | None = None, agent_id: str | None = None) -> dict[str, Any] | None:
    campaigns = store.list_records("campaigns")
    if campaign_id:
        found = next((c for c in campaigns if c.get("id") == campaign_id), None)
        if found and agent_id and found.get("agent_id") != agent_id:return None
        return found
    if agent_id:campaigns = [c for c in campaigns if c.get("agent_id") == agent_id]
    for status in ACTIVE_STATUSES:
        found = next((c for c in campaigns if c.get("status") == status), None)
        if found:return found
    return campaigns[0] if campaigns else None

def snapshot(campaign_id: str | None = None, refresh_qodo: bool = False, agent_id: str | None = None) -> dict[str, Any]:
    campaign = _pick_campaign(campaign_id, agent_id)
    if not campaign:
        target = store.get("agents", agent_id) if agent_id else None
        return {"campaign": None,"target": target,"certification": None,"events": [],"approval": None,"selection_reason": "NO_CAMPAIGN_FOR_TARGET" if agent_id else "NO_CAMPAIGN"}
    cid = campaign["id"];target = store.get("agents", campaign.get("agent_id", "")) if campaign.get("agent_id") else None
    approvals = [a for a in store.list_records("approvals") if a.get("campaign_id") == cid]
    approval = next((a for a in approvals if a.get("status") == "PENDING"), approvals[0] if approvals else None)
    if campaign.get("campaign_kind") == "GENERIC_REPOSITORY_INSPECTION":
        certification = {"campaign_id": cid,"stage": campaign.get("current_stage"),"next_gate": "repository_inspection" if campaign.get("status") not in {"COMPLETED", "ERROR", "CANCELLED"} else "complete","generic": True,"gates": {},"qodo_blocks_replay": False}
    else:
        try:certification = verification_artifacts.certification_status(cid, refresh_qodo=refresh_qodo)
        except Exception as exc:certification = {"campaign_id": cid,"stage": campaign.get("current_stage"),"next_gate": "runtime_evidence","gates": {},"qodo_blocks_replay": False,"status_error": str(exc)}
    return {"campaign": campaign,"target": target,"certification": certification,"events": store.events(cid)[-25:],"approval": approval,"selection_reason": "EXPLICIT" if campaign_id else ("WAITING_APPROVAL_PRIORITY" if campaign.get("status") == "WAITING_APPROVAL" else "ACTIVE_PRIORITY" if campaign.get("status") in ACTIVE_STATUSES else "LATEST")}

def _positive_timeout(env_name: str, default: float, minimum: float, maximum: float) -> tuple[float, str | None]:
    raw = os.getenv(env_name)
    if raw is None or raw.strip() == "":return default, None
    try:
        value = float(raw)
        if not math.isfinite(value) or value < minimum or value > maximum:raise ValueError
        return value, None
    except (TypeError, ValueError):return default, f"Invalid {env_name}={raw!r}; using {default:g}s."

def _effective_agent_name()->str:
    return os.getenv("TRUEFORGE_AGENT_NAME",DEFAULT_TRUEFORGE_AGENT_NAME).strip() or DEFAULT_TRUEFORGE_AGENT_NAME

def _configured_base_safe() -> str:
    raw=(os.getenv("TRUEFORGE_API_BASE_URL") or os.getenv("TRUEFORGE_BASE_URL") or DEFAULT_TRUEFORGE_BASE_URL).strip()
    try:
        parsed=urlparse(raw);host=parsed.hostname or ''
        if not parsed.scheme or not host:return "INVALID_TRUEFORGE_ORIGIN"
        if ':' in host and not host.startswith('['):host=f'[{host}]'
        port=f':{parsed.port}' if parsed.port else ''
        return f'{parsed.scheme}://{host}{port}'
    except (TypeError,ValueError):return "INVALID_TRUEFORGE_ORIGIN"

def trueforge_status(force: bool = False) -> dict[str, Any]:
    cached = _cached_trueforge_status()
    # A 429 cooldown is intentionally non-bypassable. A judge pressing Retry
    # should never turn into another burst against the hosted TrueForge API.
    if cached and (not force or cached.get("status") == "RATE_LIMITED"):
        return cached

    configured_base = _configured_base_safe();agent_name=_effective_agent_name()
    try:configured = TrueForgeClient.from_env()
    except (TypeError, ValueError) as exc:
        result = {"base_url": configured_base,"agent_name": agent_name,"status": "CONFIG_ERROR","retryable": True,"detail": str(exc),"diagnosis": "The configured TrueForge API origin is invalid or unsafe. Use a clean http(s) origin without credentials, query tokens, or loopback addresses in live mode.","configuration_required": True,"capabilities": None}
        return _store_trueforge_status(result, _status_cache_seconds())

    probe_timeout, warning = _positive_timeout("TRUEFORGE_PROBE_TIMEOUT_SECONDS", 4.0, 0.25, 30.0)
    effective_timeout = min(configured.timeout, probe_timeout) if configured.timeout > 0 else probe_timeout
    probe = TrueForgeClient(configured.base_url, configured.token, effective_timeout)
    base = {"base_url": configured.base_url,"agent_name": agent_name,"request_timeout_seconds": configured.timeout,"probe_timeout_seconds": probe.timeout,"configuration_warning": warning,"hosted": configured.base_url.startswith("https://"),"uses_code_default": not bool(os.getenv("TRUEFORGE_API_BASE_URL") or os.getenv("TRUEFORGE_BASE_URL"))}
    try:
        capabilities = probe.capabilities()
        result = {**base,"status": "CONNECTED","retryable": False,"detail": "TrueForge API responded to the live capability probe.","diagnosis": "Hosted TrueForge is online.","capabilities": capabilities}
        return _store_trueforge_status(result, _status_cache_seconds())
    except TrueForgeError as exc:
        message = str(exc);lowered = message.lower();timed_out = "timed out" in lowered or "timeout" in lowered;unavailable = "unavailable" in lowered;auth_failed = "authentication failed" in lowered;wrong_base = "endpoint was not found" in lowered or "non-json response" in lowered;rate_limited = "returned 429" in lowered or "too many requests" in lowered
        if rate_limited:
            result = {**base,"status": "RATE_LIMITED","retryable": True,"detail": "Hosted TrueForge is online but temporarily rate limiting capability checks.","diagnosis": "Harness OS paused automatic TrueForge probes to avoid amplifying the rate limit. Existing persisted evidence remains available.","capabilities": None}
            return _store_trueforge_status(result, _rate_limit_cache_seconds())
        if auth_failed:status = "AUTH_ERROR";diagnosis = "The TrueForge service requires authentication. Configure backend credentials/OIDC; never place secrets in the browser URL."
        elif wrong_base:status = "WRONG_API_BASE";diagnosis = "The configured TrueForge origin did not expose the expected API route."
        else:status = "TIMEOUT" if timed_out else "UNAVAILABLE" if unavailable else "ERROR";diagnosis = "Harness OS could not reach TrueForge." if timed_out or unavailable else "TrueForge returned an unexpected response."
        result = {**base,"status": status,"retryable": True,"detail": message,"diagnosis": diagnosis,"capabilities": None}
        return _store_trueforge_status(result, _status_cache_seconds())
