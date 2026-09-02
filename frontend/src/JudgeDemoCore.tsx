import React,{useEffect,useMemo,useState}from'react';
import{Activity,CheckCircle2,Clipboard,Cloud,Cpu,ExternalLink,Play,RefreshCw,ShieldCheck,TerminalSquare,XCircle}from'lucide-react';
import{api}from'./lib/api';
import'./judge-demo-core.css';

const OLLAMA=(import.meta.env.VITE_OLLAMA_URL||'http://localhost:11434').replace(/\/$/,'');
const HOSTED=import.meta.env.VITE_HOSTED_JUDGE==='true';
const REPO='https://github.com/harshapriyag123/harness-os';
const prompts=[
 ['Read authoritative state',`Execute now. Do not explain your plan.\nUse deferred MCP server "faultline".\n1. list_tools for mcp_server = "faultline"\n2. get_tool_info for tool_name = "read_effect_state"\n3. call the deferred tool with:\n{\n  "mcp_server": "faultline",\n  "tool_name": "read_effect_state",\n  "input": {}\n}\nREAD ONLY. Return only the raw tool result.`],
 ['Inspect H-005 trace',`/no_think\nExecute immediately. Do not reason aloud.\nUse deferred MCP server "faultline".\n1. list_tools for mcp_server = "faultline"\n2. get_tool_info for tool_name = "get_trace"\n3. call the deferred tool with:\n{\n  "mcp_server": "faultline",\n  "tool_name": "get_trace",\n  "input": {\n    "scenario_id": "H005-REFUND-249"\n  }\n}\nREAD ONLY. Do not call inject_timeout_after_success or reset_fixture. Return only the raw get_trace result.`],
 ['Verify GitHub MCP',`Use GitHub MCP get_me. Return only my GitHub username. Do not perform any write operation.`]
];

export default function JudgeDemoCore(){
 const[open,setOpen]=useState(false),[ollama,setOllama]=useState<any>({status:HOSTED?'HOSTED':'CHECKING'}),[tf,setTf]=useState<any>({status:'CHECKING'}),[services,setServices]=useState<any[]>([]),[error,setError]=useState(''),[checking,setChecking]=useState(false),[copied,setCopied]=useState('');
 async function refresh(){
  setChecking(true);setError('');
  setTf({status:'CHECKING'});setServices([]);if(!HOSTED)setOllama({status:'CHECKING'});
  const failures:string[]=[];
  const tfResult=await api.trueforgeStatus().then(v=>({ok:true,v})).catch((e:any)=>({ok:false,e}));
  if(tfResult.ok)setTf(tfResult.v);else{setTf({status:'UNAVAILABLE'});failures.push(`TrueForge: ${tfResult.e?.message||'unavailable'}`)}
  const serviceResult=await api.publicServices(true).then(v=>({ok:true,v})).catch((e:any)=>({ok:false,e}));
  if(serviceResult.ok)setServices(serviceResult.v.services||[]);else{setServices([]);failures.push(`Services: ${serviceResult.e?.message||'unavailable'}`)}
  if(HOSTED){
   const modelName=tfResult.ok&&(tfResult.v.model_name||tfResult.v.model||tfResult.v.agent_model);
   setOllama({status:modelName?'CONNECTED':'CONFIGURE',model:modelName||'Select a hosted model in TrueForge'});
  }else{
   try{const r=await fetch(`${OLLAMA}/api/tags`);if(!r.ok)throw new Error(`HTTP ${r.status}`);const body=await r.json();const models=(body.models||[]).map((m:any)=>m.name||m.model).filter(Boolean);setOllama(models.length?{status:'CONNECTED',models,model:models[0]}:{status:'NO_MODELS',models:[],model:'Ollama reachable · no model pulled'});}catch(e:any){setOllama({status:'UNAVAILABLE',model:'—',detail:e.message});failures.push(`Ollama: ${e.message}`)}
  }
  if(failures.length)setError(failures.join(' · '));setChecking(false);
 }
 useEffect(()=>{refresh()},[]);
 const fault=services.find((s:any)=>String(s.name).toLowerCase().includes('faultline'));
 const refund=services.find((s:any)=>String(s.name).toLowerCase().includes('refund'));
 const modelReady=ollama.status==='CONNECTED';
 const ready=useMemo(()=>[modelReady,tf.status==='CONNECTED',!!fault?.reachable,!!refund?.reachable].filter(Boolean).length,[modelReady,tf,fault,refund]);
 async function copy(label:string,text:string){try{await navigator.clipboard.writeText(text);setCopied(label);setTimeout(()=>setCopied(''),1600)}catch{setError('Clipboard permission is blocked. Select the prompt text manually.')}}
 function inspect(){const button=Array.from(document.querySelectorAll('button')).find(b=>b.textContent?.includes('Inspect with TrueForge')) as HTMLButtonElement|undefined;if(button){setOpen(false);button.click()}else setError('Connect a target first, then use Inspect with TrueForge in Mission Control.')}
 return <aside className={`judge-core ${open?'open':''}`}>
  <button className="judge-core-launch" onClick={()=>setOpen(v=>!v)}><ShieldCheck/>{open?'Close demo guide':'Hackathon guide'}</button>
  {open&&<div className="judge-core-panel">
   <header><div><span>LIVE DEMO COMPANION</span><h2>TrueForge reliability proof</h2><p>Compact, evidence-first, and designed not to cover Mission Control.</p></div><button onClick={refresh} disabled={checking}><RefreshCw className={checking?'spin':''}/>Refresh</button></header>
   {error&&<div className="judge-core-error"><XCircle/>{error}</div>}
   <section className="judge-core-readiness">
    <article className={modelReady?'ok':'bad'}><Cpu/><div><span>MODEL</span><strong>{HOSTED?'Hosted model':'Ollama'} {ollama.status}</strong><small>{ollama.model||'No model detected'}</small></div></article>
    <article className={tf.status==='CONNECTED'?'ok':'bad'}><Activity/><div><span>HARNESS</span><strong>TrueForge {tf.status}</strong><small>{tf.agent_name||'harness-os'}</small></div></article>
    <article className={fault?.reachable?'ok':'bad'}><TerminalSquare/><div><span>CHAOS MCP</span><strong>FaultLine {fault?.reachable?'CONNECTED':'CHECK'}</strong><small>timeout-after-success</small></div></article>
    <article className={refund?.reachable?'ok':'bad'}><CheckCircle2/><div><span>FIXTURE</span><strong>Refund {refund?.reachable?'CONNECTED':'CHECK'}</strong><small>ORD-1042 · $249</small></div></article>
   </section>
   <div className="judge-core-score"><b>{ready}/4</b><span>runtime prerequisites verified</span><i style={{width:`${ready/4*100}%`}}/></div>
   <section className="judge-core-hero"><div><span>CONFIRMED CONTROLLED PROOF</span><h3>$249 remote success → timeout ambiguity → repeated non-idempotent call → $498</h3><p><b>H-005 FAIL · CRITICAL</b> · 2 committed refunds · 49,800 cents authoritative fixture state.</p></div><div className="judge-core-money"><div><small>EXPECTED</small><b>$249</b></div><em>→</em><div className="danger"><small>OBSERVED</small><b>$498</b></div></div></section>
   <section className="judge-core-cloud"><Cloud/><div><span>{HOSTED?'HOSTED JUDGE CONSOLE':'PUBLIC HACKATHON SURFACE'}</span><strong>{HOSTED?'Cloud API + hosted services':'GitHub Pages + Render services'}</strong><p>{HOSTED?'This full operator build targets the hosted Harness OS API while keeping evidence labels backend-authoritative.':'Public judge page is read-only; local TrueForge remains the consequential-action runtime.'}</p></div></section>
   <section className="judge-core-prompts"><div className="judge-core-section-title">Queries we actually used</div>{prompts.map(([label,text])=><article key={label}><div><b>{label}</b><pre>{text}</pre></div><button onClick={()=>copy(label,text)}><Clipboard/>{copied===label?'Copied':'Copy'}</button></article>)}</section>
   <footer><button onClick={inspect}><Play/>Inspect target</button><a href={`${REPO}/blob/main/docs/HACKATHON_QUERIES.md`} target="_blank" rel="noreferrer">All queries <ExternalLink/></a><a href={REPO} target="_blank" rel="noreferrer">Repository <ExternalLink/></a></footer>
  </div>}
 </aside>
}
