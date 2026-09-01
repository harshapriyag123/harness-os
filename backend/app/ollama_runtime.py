from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


def _base_url() -> str:
    return (os.getenv("OLLAMA_BASE_URL") or "http://host.docker.internal:11434").strip().rstrip("/")


def _timeout() -> float:
    try:
        value = float(os.getenv("OLLAMA_PROBE_TIMEOUT_SECONDS", "3"))
        return value if 0.25 <= value <= 20 else 3.0
    except ValueError:
        return 3.0


def status() -> dict[str, Any]:
    base = _base_url()
    started = time.perf_counter()
    req = urllib.request.Request(f"{base}/api/tags", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_timeout()) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = [m.get("name") or m.get("model") for m in payload.get("models", []) if (m.get("name") or m.get("model"))]
        preferred = os.getenv("OLLAMA_MODEL", "").strip()
        return {
            "status": "CONNECTED",
            "base_url": base,
            "openai_base_url": f"{base}/v1",
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "models": models,
            "model": preferred or (models[0] if models else None),
            "preferred_model_available": (preferred in models) if preferred else None,
            "detail": f"Ollama responded with {len(models)} local model(s).",
            "trueforge_hint": "Configure TrueForge with an OpenAI-compatible endpoint pointing to the Ollama /v1 URL.",
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            "status": "UNAVAILABLE",
            "base_url": base,
            "openai_base_url": f"{base}/v1",
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "models": [],
            "model": os.getenv("OLLAMA_MODEL", "").strip() or None,
            "preferred_model_available": False,
            "detail": str(exc),
            "diagnosis": "Start Ollama on the host and make sure Docker can reach it through host.docker.internal. On a host-only backend, set OLLAMA_BASE_URL=http://127.0.0.1:11434.",
        }
