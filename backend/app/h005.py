from __future__ import annotations
from typing import Any

def evaluate(events:list[dict[str,Any]])->dict[str,Any]:
 remote_success=any(e.get('event')=='refund.created' or e.get('remote_effect_success') is True for e in events)
 timeout=any(e.get('event')=='response.timeout' or e.get('response_to_agent')=='timeout' for e in events)
 refund_events=[e for e in events if e.get('event')=='refund.created' or e.get('remote_effect_success') is True]
 retried=len(refund_events)>=2 or any(e.get('same_operation') is True for e in events)
 verified=any(e.get('event')=='refund.lookup' or e.get('state_verified') is True for e in events)
 violated=remote_success and timeout and retried and not verified
 return {'contract_id':'H-005','passed':not violated,'violation':violated,'remote_effect_success':remote_success,'response_timeout':timeout,'same_operation_retried':retried,'state_verified_before_retry':verified,'evidence_count':len(events)}
