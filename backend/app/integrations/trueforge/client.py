from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


class TrueForgeError(RuntimeError):
    pass


def _positive_timeout(value: str | None, default: float = 15.0) -> float:
    if value is None or value.strip() == "":
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("TrueForge request timeout must be numeric") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError("TrueForge request timeout must be a positive finite number")
    return parsed


def _normalize_base_url(raw: str | None, *, mode: str) -> str:
    value = (raw or "").strip().rstrip("/")
    if not value:
        if mode == "live":
            raise ValueError(
                "TRUEFORGE_BASE_URL is required in live mode. Point it to the public TrueForge API base; localhost fallback is disabled."
            )
        return "http://127.0.0.1:8790"

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("TRUEFORGE_BASE_URL must be an absolute http(s) URL")

    hostname = (parsed.hostname or "").lower()
    loopback_hosts = {"127.0.0.1", "localhost", "::1"}
    if mode == "live" and hostname in loopback_hosts:
        raise ValueError(
            "TRUEFORGE_BASE_URL points to localhost while HARNESS_OS_MODE=live. Use the public hosted TrueForge API base instead."
        )
    return value


@dataclass(frozen=True)
class TrueForgeClient:
    base_url: str
    token: str | None = None
    timeout: float = 15

    @classmethod
    def from_env(cls) -> "TrueForgeClient":
        mode = os.getenv("HARNESS_OS_MODE", "demo").strip().lower()
        # TRUEFORGE_API_BASE_URL is accepted as an explicit hosted alias so deployments
        # can distinguish the API origin from any human-facing TrueForge dashboard URL.
        raw_base = os.getenv("TRUEFORGE_API_BASE_URL") or os.getenv("TRUEFORGE_BASE_URL")
        base_url = _normalize_base_url(raw_base, mode=mode)
        timeout = _positive_timeout(
            os.getenv("TRUEFORGE_REQUEST_TIMEOUT_SECONDS", os.getenv("TRUEFORGE_TIMEOUT_SECONDS")),
            15.0,
        )
        return cls(base_url, os.getenv("TRUEFORGE_TOKEN") or None, timeout)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/json", "User-Agent": "HarnessOS/1.0"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        suffix = f"?{urlencode({k: v for k, v in (query or {}).items() if v is not None})}" if query else ""
        request = Request(
            f"{self.base_url}{path}{suffix}",
            method=method,
            headers=headers,
            data=json.dumps(payload).encode() if payload is not None else None,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                body = json.loads(raw or b"{}")
        except HTTPError as exc:
            raw = exc.read().decode(errors="replace")
            if exc.code in {401, 403}:
                raise TrueForgeError(
                    f"TrueForge authentication failed at {self.base_url}: HTTP {exc.code}. Check the server-side TRUEFORGE_TOKEN."
                ) from exc
            if exc.code == 404:
                raise TrueForgeError(
                    f"TrueForge API endpoint was not found at {self.base_url}{path}. Verify TRUEFORGE_BASE_URL/TRUEFORGE_API_BASE_URL points to the API origin, not the dashboard URL."
                ) from exc
            raise TrueForgeError(
                f"TrueForge {method} {path} returned {exc.code}: {raw[:500]}"
            ) from exc
        except URLError as exc:
            raise TrueForgeError(
                f"TrueForge unavailable at {self.base_url}: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise TrueForgeError(
                f"TrueForge request timed out after {self.timeout:g}s at {self.base_url}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise TrueForgeError(
                f"TrueForge returned a non-JSON response from {self.base_url}{path}; verify the configured API base."
            ) from exc
        return body.get("data", body)

    def capabilities(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/capabilities")

    def create_session(self, agent_name: str) -> dict[str, Any]:
        return self._request("POST", "/api/v1/sessions", {"agent": {"name": agent_name}})

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/sessions/{session_id}")

    def submit_input(
        self,
        session_id: str,
        input_messages: list[dict[str, Any]],
        *,
        stream: bool = False,
        previous_turn_id: str = "auto",
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/sessions/{session_id}/turns",
            {
                "input": input_messages,
                "previous_turn_id": previous_turn_id,
                "stream": stream,
            },
        )

    def submit_task(
        self,
        session_id: str,
        task: str,
        *,
        stream: bool = False,
        previous_turn_id: str = "auto",
    ) -> dict[str, Any]:
        return self.submit_input(
            session_id,
            [{"content": task, "type": "user.message"}],
            stream=stream,
            previous_turn_id=previous_turn_id,
        )

    def resume_with_approval(
        self,
        session_id: str,
        *,
        approved: bool,
        thread_id: str,
        tool_call_ids: list[str],
        reason: str,
    ) -> dict[str, Any]:
        if not thread_id:
            raise TrueForgeError("Cannot resolve approval without TrueForge thread_id")
        if not tool_call_ids:
            raise TrueForgeError("Cannot resolve approval without pending tool_call_ids")
        approval = {"status": "allow"} if approved else {"status": "deny", "reason": reason}
        messages = [
            {
                "type": "user.tool_approval",
                "thread_id": thread_id,
                "tool_call_id": tool_call_id,
                "approval": approval,
            }
            for tool_call_id in tool_call_ids
        ]
        return self.submit_input(session_id, messages, stream=False, previous_turn_id="auto")

    def list_session_events(self, session_id: str, limit: int = 100) -> dict[str, Any]:
        return self._request(
            "GET", f"/api/v1/sessions/{session_id}/events", query={"limit": limit}
        )

    def list_turn_events(self, session_id: str, turn_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/sessions/{session_id}/turns/{turn_id}/events")

    def cancel_session(self, session_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/sessions/{session_id}/cancel", {})
