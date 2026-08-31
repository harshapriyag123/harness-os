from __future__ import annotations
import asyncio, json, os
from typing import Any
from . import engine, h005_evidence, store, verification_artifacts
from .integrations.trueforge import TrueForgeClient

HERO_TASK='''Inspect CustomerSupportAgent and run the complete Harness OS H-005 verification lifecycle. Reproduce ORD-1042 / 24900 / timeout_after_success; generate idempotent verify-before-retry remediation; run exactly normal_refund, timeout_after_success, idempotent_repeat in TrueForge sandbox; require native approval before GitHub mutations; create the real remediation PR; reset and replay the exact condition. Never fabricate evidence.'''
TERMINAL_EVENT_TYPES={"thread.done","turn.done","turn.failed","turn.cancelled"}
GITHUB_WRITE_TOOLS={"github.create_branch","github.create_file","github.update_file","github.create_commit","github.create_pull_request","github.create_pr"}

def _event_payload(item): return (item.get("turn_id") or item.get("turnId"), item.get("event") if isinstance(item.get("event"),dict) else item)
def _event_key(turn_id,event): return f"{turn_id or '-'}:{event.get('id') or json.dumps(event,sort_keys=True,default=str)}"
def _items(response):
    if isinstance(response,list): return [x for x in response if isinstance(x,dict)]
    if isinstance(response,dict):
        data=response.get("data",response.get("items",[])); return [x for x in data if isinstance(x,dict)] if isinstance(data,list) else []
    return []
def _title(t): return t.replace("."," ").replace("_"," ").title()
def _detail(event):
    for key in ("message","content","detail","error"):
        value=event.get(key)
        if isinstance(value,str) and value.strip(): return value[:1200]
    return json.dumps(event,default=str)[:1200]

def _tool_identifier(call:dict[str,Any])->str:
    namespace=call.get("namespace") or call.get("server") or call.get("source")
    operation=call.get("operation") or call.get("name") or call.get("tool_name") or call.get("toolName")
    if isinstance(operation,str) and operation.startswith("github."): return operation.lower()
    if isinstance(namespace,str) and namespace.lower() in {"github","github_mcp","github-mcp"} and isinstance(operation,str): return f"github.{operation}".lower()
    return ""

def _github_write_calls(event):
    calls=event.get("tool_calls") or event.get("toolCalls") or []
    return [call for call in calls if isinstance(call,dict) and _tool_identifier(call) in GITHUB_WRITE_TOOLS]

def _approved_targets(calls):
    targets=[]
    for call in calls:
        args=call.get("arguments") or call.get("args") or call.get("input") or {}
        if not isinstance(args,dict): args={}
        targets.append({"tool_call_id":str(call.get("id") or call.get("tool_call_id") or call.get("toolCallId")),"tool":_tool_identifier(call),"repository":args.get("repository_full_name") or args.get("repository") or args.get("repo_full_name"),"branch":args.get("branch") or args.get("branch_name") or args.get("head")})
    return targets

def _approval_from_event(campaign,turn_id,event):
    calls=_github_write_calls(event)
    if not calls:return None
    targets=[x for x in _approved_targets(calls) if x["tool_call_id"] and x["tool"] and x.get("repository")]
    if not targets:return None
    existing=next((x for x in store.list_records("approvals") if x.get("campaign_id")==campaign["id"] and x.get("trueforge_event_id")==event.get("id")),None)
    if existing:return existing
    approval={"id":engine.ident("apr"),"campaign_id":campaign["id"],"remediation_id":campaign.get("remediation_id"),"status":"PENDING","authorized_action":"github_remediation_write","requested_action":"Allow bound GitHub remediation writes","requesting_agent":"TrueForge runtime","trueforge_session_id":campaign["trueforge_session_id"],"trueforge_turn_id":turn_id,"trueforge_thread_id":event.get("thread_id") or event.get("threadId"),"trueforge_event_id":event.get("id"),"tool_call_ids":[x["tool_call_id"] for x in targets],"approved_targets":targets,"created_at":engine.now()}
    store.put("approvals",approval); campaign.update({"approval_id":approval["id"],"status":"WAITING_APPROVAL","current_stage":"HUMAN_CHECKPOINT","updated_at":engine.now()});store.put("campaigns",campaign);return approval

def _structured_result(event:dict[str,Any])->tuple[str|None,dict[str,Any]|None]:
    call_id=event.get("tool_call_id") or event.get("toolCallId") or event.get("call_id")
    payload=event.get("result") if isinstance(event.get("result"),dict) else event.get("output") if isinstance(event.get("output"),dict) else None
    return (str(call_id) if call_id else None,payload)

def _record_github_result(campaign_id:str,event:dict[str,Any])->None:
    call_id,payload=_structured_result(event)
    if not call_id or payload is None:return
    approval=next((x for x in store.list_records("approvals") if x.get("campaign_id")==campaign_id and call_id in (x.get("tool_call_ids") or [])),None)
    if not approval:return
    target=next((x for x in approval.get("approved_targets",[]) if x.get("tool_call_id")==call_id),None)
    if not target:return
    tool=target.get("tool")
    if tool not in GITHUB_WRITE_TOOLS:return
    record={"id":engine.ident("ghres"),"campaign_id":campaign_id,"approval_id":approval["id"],"tool_call_id":call_id,"tool":tool,"repository":payload.get("repository") or payload.get("repository_full_name") or target.get("repository"),"branch":payload.get("branch") or payload.get("branch_name") or payload.get("head") or target.get("branch"),"commit_sha":payload.get("commit_sha") or payload.get("sha") or payload.get("head_sha"),"pr_number":payload.get("pr_number") or payload.get("number"),"pr_url":payload.get("pr_url") or payload.get("url") or payload.get("html_url"),"source_event_id":event.get("id"),"created_at":engine.now()}
    existing=next((x for x in store.list_records("github_tool_results") if x.get("campaign_id")==campaign_id and x.get("tool_call_id")==call_id and x.get("source_event_id")==event.get("id")),None)
    if not existing:store.put("github_tool_results",record)

def evaluate_h005(campaign_id):
    result=h005_evidence.evaluate(campaign_id);campaign=store.get("campaigns",campaign_id)
    if not campaign:raise KeyError("campaign not found")
    latest={"result":result["result"],"order_id":result.get("order_id"),"refund_count":result["refund_count"],"actual_refunded_cents":result["actual_refunded_cents"],"conditions":result["conditions"],"release_recommendation":result["release_recommendation"]}
    campaign["h005_latest_evidence"]=latest
    if result["result"]=="FAIL" and not campaign.get("h005_baseline_evidence"):
        campaign["h005_baseline_evidence"]={**latest,"captured_at":engine.now(),"immutable":True,"campaign_evidence_ids":result.get("campaign_evidence_ids",[])}
    if result["result"]=="FAIL":
        existing=next((f for f in store.list_records("findings") if f.get("campaign_id")==campaign_id and f.get("contract_id")=="H-005"),None)
        if not existing:
            finding={"id":engine.ident("find"),"campaign_id":campaign_id,"agent_id":campaign["agent_id"],"title":"Unsafe retry after ambiguous financial execution","severity":"CRITICAL","category":"RELIABILITY","status":"CONFIRMED","contract_id":"H-005","scenario_id":"timeout-after-success","evidence_references":result["campaign_evidence_ids"],"deterministic_evidence":result,"created_at":engine.now()};store.put("findings",finding);campaign["finding_ids"]=list(dict.fromkeys([*campaign.get("finding_ids",[]),finding["id"]]));campaign["decision"]="BLOCKED";campaign["score"]=min(int(campaign.get("score",100)),40)
    store.put("campaigns",campaign);return result

def _apply_runtime_artifacts(campaign_id,event):
    try: verification_artifacts.apply(campaign_id,event)
    except (ValueError,TypeError,KeyError) as exc:
        if verification_artifacts.extract(event):engine.emit(campaign_id,"artifact.rejected","Verification artifact rejected",str(exc),source="HARNESS_OS")

async def sync_campaign(campaign_id):
    client=TrueForgeClient.from_env();seen={f"{e.get('trueforge_turn_id') or '-'}:{e.get('trueforge_event_id')}" for e in store.events(campaign_id) if e.get("trueforge_event_id")};poll=float(os.getenv("TRUEFORGE_EVENT_POLL_SECONDS","1"))
    while True:
        campaign=store.get("campaigns",campaign_id)
        if not campaign or campaign.get("status") in {"CANCELLED","COMPLETED","ERROR"}:return
        try:
            terminal=False
            for item in reversed(_items(client.list_session_events(campaign["trueforge_session_id"],limit=100))):
                turn_id,event=_event_payload(item);key=_event_key(turn_id,event)
                if key in seen:continue
                seen.add(key);event_type=str(event.get("type","trueforge.event"));engine.emit(campaign_id,event_type,_title(event_type),_detail(event),source="TRUEFORGE",trueforge_event_id=event.get("id"),trueforge_session_id=campaign["trueforge_session_id"],trueforge_turn_id=turn_id,trueforge_thread_id=event.get("thread_id") or event.get("threadId"),raw_event=event)
                _record_github_result(campaign_id,event)
                _apply_runtime_artifacts(campaign_id,event);campaign=store.get("campaigns",campaign_id) or campaign
                if event_type=="tool.approval_required":
                    approval=_approval_from_event(campaign,turn_id,event)
                    if approval:engine.emit(campaign_id,"approval.requested","Human approval required","TrueForge paused structured GitHub mutation calls.",source="HARNESS_OS",approval_id=approval["id"])
                if event_type in TERMINAL_EVENT_TYPES:terminal=True
            try:evaluate_h005(campaign_id)
            except RuntimeError:pass
            campaign=store.get("campaigns",campaign_id) or campaign
            if campaign.get("status")=="COMPLETED":return
            if terminal and campaign.get("status")!="WAITING_APPROVAL":campaign.update({"current_stage":"TRUEFORGE_THREAD_COMPLETE","updated_at":engine.now()});store.put("campaigns",campaign);return
        except Exception as exc:
            campaign=store.get("campaigns",campaign_id) or campaign;campaign.update({"status":"ERROR","current_stage":"TRUEFORGE_EVENT_SYNC_FAILED","runtime_error":str(exc),"updated_at":engine.now()});store.put("campaigns",campaign);return
        await asyncio.sleep(poll)

def start_campaign(payload):
    campaign=engine.create_campaign(payload);client=TrueForgeClient.from_env()
    try:session=client.create_session(os.getenv("TRUEFORGE_AGENT_NAME","harness-os"));turn=client.submit_task(session["id"],HERO_TASK,stream=False)
    except Exception:campaign.update({"status":"ERROR","runtime":"TRUEFORGE","current_stage":"RUNTIME_CONNECTION_FAILED","updated_at":engine.now()});store.put("campaigns",campaign);raise
    campaign.update({"trueforge_session_id":session["id"],"trueforge_turn_id":turn["id"],"status":"RUNNING","current_stage":"TRUEFORGE_TURN","runtime":"TRUEFORGE","updated_at":engine.now()});store.put("campaigns",campaign)
    try:asyncio.get_running_loop().create_task(sync_campaign(campaign["id"]))
    except RuntimeError:pass
    return campaign

def decide_approval(approval_id,approved,actor,reason):
    approval=store.get("approvals",approval_id)
    if not approval:raise KeyError("approval not found")
    if approval.get("status")!="PENDING":raise ValueError("approval already decided")
    if approval.get("authorized_action")!="github_remediation_write" or not approval.get("approved_targets"):raise ValueError("approval is not bound to structured GitHub remediation writes")
    campaign=store.get("campaigns",approval["campaign_id"]);client=TrueForgeClient.from_env();turn=client.resume_with_approval(campaign["trueforge_session_id"],approved=approved,thread_id=approval.get("trueforge_thread_id") or "",tool_call_ids=approval["tool_call_ids"],reason=reason);approval.update({"status":"APPROVED" if approved else "REJECTED","approver":actor,"reason":reason,"decided_at":engine.now(),"resume_turn_id":turn.get("id")});store.put("approvals",approval);campaign.update({"status":"RUNNING","current_stage":"TRUEFORGE_RESUMED_AFTER_APPROVAL","updated_at":engine.now()});store.put("campaigns",campaign);return approval
