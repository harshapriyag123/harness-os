import React,{useEffect,useState}from'react';
import{CheckCircle2,Clock3,ExternalLink,LockKeyhole,RefreshCw,ShieldCheck,TerminalSquare}from'lucide-react';
import{api}from'./lib/api';

const labels:any={sandbox:'TrueForge Sandbox',human_approval:'Human Approval',github_pr:'GitHub MCP PR',qodo_review:'Qodo Review Gate',exact_replay:'Exact H-005 Replay',safety_case:'Safety Case'};

export default function JudgeCertification({campaign}:any){
 const[state,setState]=useState<any>(),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function load(refresh=true){if(!campaign?.id)return;setBusy(true);setError('');try{setState(await api.certification(campaign.id,refresh))}catch(e:any){setError(e.message)}finally{setBusy(false)}}
 useEffect(()=>{if(!campaign?.id){setState(undefined);return}load(false);const t=setInterval(()=>load(false),5000);return()=>clearInterval(t)},[campaign?.id]);
 if(!campaign)return null;
 const gates=state?.gates||{};const order=['sandbox','human_approval','github_pr','qodo_review','exact_replay','safety_case'];
 const sandbox=gates.sandbox?.detail||{};const qodo=gates.qodo_review?.detail||{};
 return <section className="certification-panel">
   <div className="certification-head"><div><div className="eyebrow"><ShieldCheck/>LIVE CERTIFICATION CHAIN</div><h3>Evidence must cross every gate before release.</h3><p>TrueForge executes and sandboxes. A human authorizes repository mutation. GitHub MCP opens the PR. Qodo must review that exact PR before replay can unlock the Safety Case.</p></div><button className="ghost" onClick={()=>load(true)} disabled={busy}><RefreshCw className={busy?'spin':''}/>{busy?'Refreshing':'Refresh evidence'}</button></div>
   {error&&<div className="certification-error">{error}</div>}
   <div className="gate-row">{order.map((key,i)=>{const gate=gates[key];const passed=!!gate?.passed;const active=state?.next_gate===key;return <React.Fragment key={key}><div className={`gate-card ${passed?'passed':active?'active':'locked'}`}><div className="gate-icon">{passed?<CheckCircle2/>:active?<Clock3/>:<LockKeyhole/>}</div><span>{labels[key]}</span><strong>{passed?'VERIFIED':active?'NEXT GATE':'LOCKED'}</strong></div>{i<order.length-1&&<div className={`gate-arrow ${passed?'passed':''}`}>→</div>}</React.Fragment>})}</div>
   <div className="certification-evidence">
    <div><span>Sandbox evidence</span><strong>{sandbox.trueforge_sandbox_id||'Awaiting TrueForge sandbox artifact'}</strong>{Array.isArray(sandbox.tests)&&<ul>{sandbox.tests.map((t:any)=><li key={t.name}><TerminalSquare/>{t.name}<b>{t.status}</b></li>)}</ul>}</div>
    <div><span>Qodo release gate</span><strong>{qodo.status||'WAITING_FOR_PR'}</strong><p>{qodo.detail||'Qodo review is checked only after the approved remediation PR exists.'}</p>{qodo.href&&<a href={qodo.href} target="_blank" rel="noreferrer">Open Qodo evidence <ExternalLink/></a>}{state?.qodo_blocks_replay&&<small className="blocked-note"><LockKeyhole/>Replay is intentionally blocked until Qodo evidence is found.</small>}</div>
   </div>
 </section>
}
