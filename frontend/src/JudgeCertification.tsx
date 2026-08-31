import React,{useEffect,useMemo,useState}from'react';
import{Activity,CheckCircle2,Clock3,ExternalLink,GitPullRequest,LockKeyhole,RefreshCw,ShieldCheck,TerminalSquare,XCircle}from'lucide-react';
import{api}from'./lib/api';

const labels:any={sandbox:'TrueForge Sandbox',human_approval:'Human Approval',github_pr:'GitHub MCP PR',qodo_review:'Qodo Review',exact_replay:'Exact H-005 Replay',safety_case:'Safety Case'};
const order=['sandbox','human_approval','github_pr','qodo_review','exact_replay','safety_case'];
const waitingCopy:any={sandbox:'TrueForge is executing the candidate remediation in an isolated sandbox.',human_approval:'The agent is paused. Nothing irreversible happens until you decide.',github_pr:'Waiting for the approved GitHub MCP write to finish and return PR evidence.',qodo_review:'Waiting for independent Qodo evidence on the exact remediation PR.',exact_replay:'All review gates passed. The same timeout-after-success attack can now be replayed.',safety_case:'Replay passed. Harness OS is assembling the signed evidence bundle.'};

function compact(value:any,fallback='—'){if(value===undefined||value===null||value==='')return fallback;return String(value)}

export default function JudgeCertification({campaign}:any){
 const[state,setState]=useState<any>(),[events,setEvents]=useState<any[]>([]),[approval,setApproval]=useState<any>(),[busy,setBusy]=useState(false),[decisionBusy,setDecisionBusy]=useState(false),[confirming,setConfirming]=useState(false),[error,setError]=useState('');
 async function load(refresh=true){if(!campaign?.id)return;setBusy(true);setError('');try{const[cert,trace,approvals]=await Promise.all([api.certification(campaign.id,refresh),api.traces(campaign.id),api.approvals()]);setState(cert);setEvents(Array.isArray(trace)?trace:[]);setApproval((approvals||[]).find((a:any)=>a.campaign_id===campaign.id&&a.status==='PENDING')||(approvals||[]).find((a:any)=>a.campaign_id===campaign.id));}catch(e:any){setError(e.message)}finally{setBusy(false)}}
 useEffect(()=>{if(!campaign?.id){setState(undefined);setEvents([]);setApproval(undefined);return}load(false);const t=setInterval(()=>load(false),3500);return()=>clearInterval(t)},[campaign?.id]);
 const gates=state?.gates||{};const sandbox=gates.sandbox?.detail||{};const qodo=gates.qodo_review?.detail||{};const next=state?.next_gate||'sandbox';
 const lastPassed=useMemo(()=>[...order].reverse().find(key=>gates[key]?.passed),[state]);
 const recent=events.slice(-4).reverse();
 const isWaitingApproval=next==='human_approval'&&approval?.status==='PENDING';
 const runState=campaign?.status==='COMPLETED'?'COMPLETE':isWaitingApproval?'WAITING FOR YOU':campaign?.status==='ERROR'?'ERROR':'AGENT WORKING';
 const targets=approval?.approved_targets||[];
 async function decide(action:'approve'|'reject'){
  if(!approval?.id)return;setDecisionBusy(true);setError('');try{await api.decide(approval.id,action,action==='approve'?'Operator inspected the exact GitHub mutation scope in Harness OS and approved it before execution.':'Operator rejected the proposed irreversible repository mutation.');setConfirming(false);await load(true)}catch(e:any){setError(e.message)}finally{setDecisionBusy(false)}}
 if(!campaign)return <section className="certification-panel certification-empty"><div className="eyebrow"><ShieldCheck/>OPERATOR CONSOLE</div><h3>No verification run yet.</h3><p>Connect the target agent and start one H-005 verification. This console will show what the agent is doing, what it is waiting on, and what it already proved.</p></section>;
 return <section className="certification-panel">
   <div className="operator-head">
    <div><div className="eyebrow"><ShieldCheck/>LIVE AGENT OPERATOR CONSOLE</div><h3>One job. One evidence chain. You stay in control.</h3><p>TrueForge runs the agent. Harness OS makes every consequential transition legible before it happens.</p></div>
    <div className="operator-head-actions"><div className={`run-badge ${runState.toLowerCase().replaceAll(' ','-')}`}><i/>{runState}</div><button className="ghost" onClick={()=>load(true)} disabled={busy}><RefreshCw className={busy?'spin':''}/>{busy?'Checking…':'Refresh'}</button></div>
   </div>
   {error&&<div className="certification-error">{error}</div>}

   <div className="operator-strip">
    <article><span><Activity/>WHAT IT'S DOING</span><strong>{labels[next]||'Verification complete'}</strong><p>{next==='complete'?'The tested condition has reached its final release decision.':waitingCopy[next]}</p></article>
    <article className={isWaitingApproval?'attention':''}><span><Clock3/>WHAT IT'S WAITING ON</span><strong>{isWaitingApproval?'Your approval':next==='qodo_review'?'Independent Qodo review':next==='complete'?'Nothing — complete':labels[next]}</strong><p>{isWaitingApproval?'The GitHub write is paused before execution.':next==='qodo_review'?'Replay stays locked until Qodo reviews the exact PR.':'The next gate must produce evidence before the run advances.'}</p></article>
    <article><span><CheckCircle2/>WHAT IT DID</span><strong>{lastPassed?labels[lastPassed]:'Run started'}</strong><p>{lastPassed?'Evidence is persisted and visible below.':'Waiting for the first evidence-backed gate to pass.'}</p></article>
   </div>

   <div className="session-line"><span>TrueForge session</span><code>{compact(campaign.trueforge_session_id,'session pending')}</code><span>Stage</span><code>{compact(state?.stage,campaign.current_stage||'starting')}</code></div>

   <div className="gate-row">{order.map((key,i)=>{const gate=gates[key];const passed=!!gate?.passed;const active=state?.next_gate===key;return <React.Fragment key={key}><div className={`gate-card ${passed?'passed':active?'active':'locked'}`}><div className="gate-icon">{passed?<CheckCircle2/>:active?<Clock3/>:<LockKeyhole/>}</div><span>{labels[key]}</span><strong>{passed?'VERIFIED':active?'CURRENT':'LOCKED'}</strong></div>{i<order.length-1&&<div className={`gate-arrow ${passed?'passed':''}`}>→</div>}</React.Fragment>})}</div>

   {isWaitingApproval&&<section className="approval-moment">
    <div className="approval-warning"><LockKeyhole/><div><span>IRREVERSIBLE STEP — PAUSED BEFORE EXECUTION</span><h4>{approval.requested_action||'Authorize remediation repository writes'}</h4><p>The agent cannot continue these GitHub MCP writes until you approve the exact scope below.</p></div></div>
    <div className="approval-scope">{targets.length?targets.map((t:any)=><div key={t.tool_call_id||t.tool}><GitPullRequest/><div><strong>{compact(t.tool,'GitHub write')}</strong><small>{compact(t.repository,'repository')} · {compact(t.branch,'branch resolved by tool')}</small></div><code>{compact(t.tool_call_id,'call id pending')}</code></div>):<div><GitPullRequest/><div><strong>{approval.patch_summary||'Verified remediation write'}</strong><small>{approval.requested_action||'Bound by the native TrueForge approval event.'}</small></div></div>}</div>
    {!confirming?<div className="approval-buttons"><button className="reject-action" disabled={decisionBusy} onClick={()=>decide('reject')}><XCircle/>Reject</button><button className="approve-action" disabled={decisionBusy} onClick={()=>setConfirming(true)}><ShieldCheck/>Review & approve</button></div>:<div className="confirm-box"><div><strong>Confirm before TrueForge resumes</strong><p>You are authorizing only the GitHub calls shown above. Harness OS will record this decision and TrueForge will resume the paused tool calls.</p></div><div><button className="ghost" disabled={decisionBusy} onClick={()=>setConfirming(false)}>Go back</button><button className="approve-action" disabled={decisionBusy} onClick={()=>decide('approve')}><ShieldCheck/>{decisionBusy?'Approving…':'Confirm approval'}</button></div></div>}
   </section>}

   <div className="certification-evidence">
    <div><span>TrueForge sandbox proof</span><strong>{sandbox.trueforge_sandbox_id||'Awaiting sandbox artifact'}</strong>{Array.isArray(sandbox.tests)&&<ul>{sandbox.tests.map((t:any)=><li key={t.name}><TerminalSquare/>{t.name}<b>{t.status}</b></li>)}</ul>} {!sandbox.trueforge_sandbox_id&&<p>PASS appears only after an actual sandbox artifact is persisted.</p>}</div>
    <div><span>Independent Qodo gate</span><strong>{qodo.status||'WAITING_FOR_PR'}</strong><p>{qodo.detail||'Qodo is checked against the remediation PR created by this run.'}</p>{qodo.href&&<a href={qodo.href} target="_blank" rel="noreferrer">Open exact review evidence <ExternalLink/></a>}{state?.qodo_blocks_replay&&<small className="blocked-note"><LockKeyhole/>Exact replay is locked until Qodo evidence is found.</small>}</div>
   </div>

   <div className="activity-panel"><div className="activity-title"><div><Activity/><strong>What the agent did</strong></div><span>persisted causal trace</span></div><div className="activity-list">{recent.length?recent.map((e:any)=><article key={e.id||e.sequence}><i/><div><strong>{e.title||e.event_type}</strong><p>{e.detail||e.event_type}</p><small>{e.source||'HARNESS OS'} · {e.timestamp?new Date(e.timestamp).toLocaleTimeString():`#${e.sequence}`}</small></div></article>):<p className="activity-empty">No execution evidence yet. Start a run to populate the trace.</p>}</div></div>
 </section>
}
