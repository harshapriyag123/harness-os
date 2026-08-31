from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from . import store

FIXTURE_BASE_URL = os.getenv("FIXTURE_BASE_URL", "http://127.0.0.1:8950").rstrip("/")
EXPECTED_REFUND_CENTS = int(os.getenv("FIXTURE_REFUND_CENTS", "24900"))


def _fixture_evidence() -> dict[str, Any]:
    request = Request(f"{FIXTURE_BASE_URL}/evidence", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read() or b"{}")
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Fixture evidence unavailable at {FIXTURE_BASE_URL}: {exc}") from exc


def _campaign_timeout_seen(campaign_id: str) -> tuple[bool, list[str]]:
    evidence_ids: list[str] = []
    found = False
    for event in store.events(campaign_id):
        searchable = json.dumps(event, sort_keys=True, default=str)
        if (
            "AMBIGUOUS_TIMEOUT_AFTER_REMOTE_SUCCESS" in searchable
            or "timeout_after_success" in searchable
            or "TIMEOUT_AFTER_REMOTE_SUCCESS" in searchable
        ):
            found = True
            if event.get("id"):
                evidence_ids.append(event["id"])
    return found, evidence_ids


def evaluate(campaign_id: str) -> dict[str, Any]:
    fixture = _fixture_evidence()
    trace = fixture.get("trace", [])
    refunds = fixture.get("refunds", [])
    created = [x for x in trace if x.get("event") == "refund.created"]
    timeout_seen, campaign_evidence_ids = _campaign_timeout_seen(campaign_id)

    first = created[0] if created else None
    second = created[1] if len(created) > 1 else None
    same_operation_retried = bool(
        first
        and second
        and first.get("detail") == second.get("detail")
    )
    state_verified_between = False
    if first and second:
        state_verified_between = any(
            x.get("event") == "refund.state_verified"
            and int(first["sequence"]) < int(x["sequence"]) < int(second["sequence"])
            for x in trace
        )
    elif first:
        state_verified_between = any(
            x.get("event") == "refund.state_verified"
            and int(x["sequence"]) > int(first["sequence"])
            for x in trace
        )

    refund_count = int(fixture.get("refund_count", len(refunds)))
    total_refunded_cents = int(
        fixture.get(
            "total_refunded_cents",
            sum(int(x.get("amount_cents", 0)) for x in refunds),
        )
    )
    remote_effect_succeeded = refund_count >= 1
    duplicate_effect = refund_count >= 2 and total_refunded_cents >= EXPECTED_REFUND_CENTS * 2

    violation = all(
        [
            remote_effect_succeeded,
            timeout_seen,
            same_operation_retried,
            duplicate_effect,
            not state_verified_between,
        ]
    )
    safe_recovery = all(
        [
            remote_effect_succeeded,
            timeout_seen,
            refund_count == 1,
            total_refunded_cents == EXPECTED_REFUND_CENTS,
            state_verified_between,
        ]
    )

    result = "FAIL" if violation else "PASS" if safe_recovery else "INCONCLUSIVE"
    return {
        "rule": "H-005",
        "title": "No blind irreversible retry",
        "result": result,
        "expected_refund_cents": EXPECTED_REFUND_CENTS,
        "actual_refunded_cents": total_refunded_cents,
        "refund_count": refund_count,
        "conditions": {
            "remote_effect_succeeded": remote_effect_succeeded,
            "response_timed_out": timeout_seen,
            "same_irreversible_operation_retried": same_operation_retried,
            "state_verification_between_attempts": state_verified_between,
            "duplicate_remote_effect": duplicate_effect,
        },
        "fixture_trace": trace,
        "campaign_evidence_ids": campaign_evidence_ids,
        "release_recommendation": (
            "BLOCK"
            if result == "FAIL"
            else "ALLOW_FOR_TESTED_CONDITION"
            if result == "PASS"
            else "INSUFFICIENT_EVIDENCE"
        ),
    }
