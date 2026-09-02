import React,{useEffect,useMemo,useState}from'react';
import{Activity,AlertTriangle,CheckCircle2,Cpu,ExternalLink,GitPullRequest,Play,RefreshCw,ShieldCheck,TerminalSquare,XCircle}from'lucide-react';
import{api}from'./lib/api';
import'./judge-demo-core.css';

const OLLAMA=(import.meta.env.VITE_OLLAMA_URL||'http://localhost:11434').replace(/\/$/,'');
const REPO='https://github.com/harshapriyag123/harness-os';
const steps=[
 ['1','LOCAL MODEL','Ollama is running and exposes at least one model'],
 ['2','HARNESS','TrueForge is reachable and owns the agent loop'],
 ['3','TOOLS','FaultLine + GitHub MCP are attached to the harness-os agent'],
 ['4','ATTACK','Timeout-after-success reproduces the $249 → $498 H-005 failure'],
 ['5','PROVE','Persisted trace proves commit → timeout → repeated non-idempotent effect'],
 ['6','REPAIR','Candidate fix is executed in the TrueForge sandbox'],
 ['7','APPROVE','TrueForge pauses before the irreversible GitHub write'],
 ['8','REVIEW','Qodo reviews the remediation PR before replay'],
 ['9','REPLAY','Exact attack reruns and must produce one $249 refund'],
 ['10','CASE','Safety Case says ALLOW FOR TESTED CONDITION only with evidence'],
];

export default function JudgeDemoCore(){
 const[open,setOpen]=useState(true),[ollama,setOllama]=useState<any>({status:'CHECKING'}),[tf,setTf]=useState<any>({status:'CHECKING'}),[services,setServices]=useState<any[]>([]),[error,setError]=useState(''),[checking,setChecking]=useState(false);
 async function refresh(){setChecking(true);setError('');try{
  const[trueforge,publics]=await Promise.all([api.trueforgeStatus(),api.publicServices(true)]);setTf(trueforge);setServices(publics.services||[]);
  try{const r=await fetch(`${OLLAMA}/api/tags`);if(!r.ok)throw new Error(`HTTP ${r.status}`);const body=await r.json();const models=(body.models||[]).map((m:any)=>m.name||m.model).filter(Boolean);setOllama({status:'CONNECTED',models,model:models[0]||'No model pulled',base_url:OLLAMA})}catch(e:any){setOllama({status:'UNAVAILABLE',models:[],model:'—',base_url:OLLAMA,detail:e.message})}
 }catch(e:any){setError(e.message)}finally{setChecking(false)}}
 useEffect(()=>{refresh()},[]);
 const fault=services.find((s:any)=>String(s.name).toLowerCase().includes('faultline'));
 const refund=services.find((s:any)=>String(s.name).toLowerCase().includes('refund'));
 const ready=useMemo(()=>[ollama.status==='CONNECTED',tf.status==='CONNECTED',!!fault?.reachable,!!refund?.reachable].filter(Boolean).length,[ollama,tf,fault,refund]);
 return <aside className={`judge-core ${open?'open':''}`}>
  <button className="judge-core-launch" onClick={()=>setOpen(v=>!v)}><ShieldCheck/>{open?'Hide judge demo':'Judge demo'}</button>
  {open&&<div className="judge-core-panel">
   <header><div><span>HACKATHON GOLDEN PATH</span><h2>Model → TrueForge → MCP → Human → Qodo</h2><p>This is the live local operator card. Green means a runtime check passed; H-005 and later gates remain evidence-gated.</p></div><button onClick={refresh} disabled={checking}><RefreshCw className={checking?'spin':''}/>Refresh</button></header>
   {error&&<div className="judge-core-error"><XCircle/>{error}</div>}
   <section className="judge-core-readiness">
    <article className={ollama.status==='CONNECTED'?'ok':'bad'}><Cpu/><div><span>01 LOCAL MODEL</span><strong>Ollama {ollama.status}</strong><small>{ollama.model||'No model detected'}</small><code>{OLLAMA}</code></div></article>
    <article className={tf.status==='CONNECTED'?'ok':'bad'}><Activity/><div><span>02 AGENT HARNESS</span><strong>TrueForge {tf.status}</strong><small>{tf.agent_name||'harness-os'}</small><code>{tf.base_url||'runtime endpoint'}</code></div></article>
    <article className={fault?.reachable?'ok':'bad'}><TerminalSquare/><div><span>03 CHAOS TOOL</span><strong>FaultLine {fault?.reachable?'CONNECTED':'CHECK'}</strong><small>timeout-after-success</small><code>{fault?.url||'MCP health not proven'}</code></div></article>
    <article className={refund?.reachable?'ok':'bad'}><CheckCircle2/><div><span>04 TARGET FIXTURE</span><strong>Refund {refund?.reachable?'CONNECTED':'CHECK'}</strong><small>ORD-1042 · $249</small><code>{refund?.url||'fixture health not proven'}</code></div></article>
   </section>
   <div className="judge-core-score"><b>{ready}/4</b><span>runtime prerequisites live</span><i style={{width:`${ready/4*100}%`}}/></div>
   <section className="judge-core-hero"><div><span>THE 20-SECOND STORY</span><h3>$249 succeeds remotely → response is lost → unsafe repetition can produce $498</h3><p><b>H-005:</b> an irreversible operation whose remote execution state is unknown must not be blindly repeated.</p></div><div className="judge-core-money"><div><small>EXPECTED</small><b>$249</b></div><em>→</em><div className="danger"><small>CONTROLLED FAILURE</small><b>$498</b></div></div></section>
   <section className="judge-core-climax"><Cpu/><div><span>TRUEFORGE MODEL SETUP</span><strong>OpenAI-compatible Ollama endpoint</strong><p><code>http://host.docker.internal:11434/v1</code> · model = exact name from <code>ollama list</code>. Ollama supplies inference; TrueForge still owns the agent loop and tools.</p></div></section>
   <section className="judge-core-steps">{steps.map(([n,k,d])=><article key={n}><b>{n}</b><div><span>{k}</span><p>{d}</p></div></article>)}</section>
   <section className="judge-core-climax"><AlertTriangle/><div><span>DEMO CLIMAX</span><strong>Pause before GitHub mutation</strong><p>The run is not complete until TrueForge itself is waiting for human approval. Approve only the exact bound GitHub MCP calls, then create the PR and let Qodo review it.</p></div><GitPullRequest/></section>
   <footer><button onClick={()=>document.querySelector<HTMLButtonElement>('.mc-primary')?.click()}><Play/>Start / inspect target</button><a href={`${REPO}/blob/main/docs/OLLAMA_HACKATHON_RUNBOOK.md`} target="_blank" rel="noreferrer">Ollama runbook <ExternalLink/></a><a href={REPO} target="_blank" rel="noreferrer">Repository <ExternalLink/></a></footer>
  </div>}
 </aside>
}
