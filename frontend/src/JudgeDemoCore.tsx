import React,{useEffect,useMemo,useState}from'react';
import{Activity,CheckCircle2,Clipboard,Cloud,Cpu,ExternalLink,Play,RefreshCw,ShieldCheck,TerminalSquare,XCircle}from'lucide-react';
import{api}from'./lib/api';
import'./judge-demo-core.css';

const OLLAMA=(import.meta.env.VITE_OLLAMA_URL||'http://localhost:11434').replace(/\/$/,'');
const HOSTED=import.meta.env.VITE_HOSTED_JUDGE==='true';
const REPO='https://github.com/harshapriyag123/harness-os';
type AsyncResult<T>={ok:true;v:T}|{ok:false;e:any};
const prompts=[
 ['Read authoritative state',`Execute now. Do not explain your plan.\nUse deferred MCP server "faultline".\n1. list_tools for mcp_server = "faultline"\n2. get_tool_info for tool_name = "read_effect_state"\n3. call the deferred tool with:\n{\n  "mcp_server": "faultline",\n  "tool_name": "read_effect_state",\n  "input": {}\n}\nREAD ONLY. Return only the raw tool result.`],
 ['Inspect H-005 trace',`/no_think\nExecute immediately. Do not reason aloud.\nUse deferred MCP server "faultline".\n1. list_tools for mcp_server = "faultline"\n2. get_tool_info for tool_name = "get_trace"\n3. call the deferred tool with:\n{\n  "mcp_server": "faultline",\n  "tool_name": "get_trace",\n  "input": {\n    "scenario_id": "H005-REFUND-249"\n  }\n}\nREAD ONLY. Do not call inject_timeout_after_success or reset_fixture. Return only the raw get_trace result.`],
 ['Verify GitHub MCP',`Use GitHub MCP get_me. Return only my GitHub username. Do not perform any write operation.`]
];

export default function JudgeDemoCore(){
 const[open,setOpen]=useState(false),[ollama,setOllama]=useState<any>({status:HOSTED?'HOSTED':'CHECKING'}),[tf,setTf]=useState<any>({status:'CHECKING'}),[services,setServices]=useState<any[]>([]),[error,setError]=useState(''),[checking,setChecking]=useState(false),[copied,setCopied]=useState('');
 async function refresh(){
  setChecking(true);setError('');setTf({status:'CHECKING'});setServices([]);if(!HOSTED)setOllama({status:'CHECKING'});
  const failures:string[]=[];
  const tfResult:AsyncResult<any>=await api.trueforgeStatus().then((v:any)=>({ok:true as const,v})).catch((e:any)=>({ok:false as const,e}));
  if(tfResult.ok)setTf(tfResult.v);else{setTf({status:'UNAVAILABLE'});failures.push(`TrueForge: ${tfResult.e?.message||'unavailable'}`)}
  const serviceResult:AsyncResult<any>=await api.publicServices(true).then((v:any)=>({ok:true as const,v})).catch((e:any)=>({ok:false as const,e}));
  if(serviceResult.ok)setServices(serviceResult.v.services||[]);else{setServices([]);failures.push(`Services: ${serviceResult.e?.message||'unavailable'}`)}
  if(HOSTED){const modelName=tfResult.ok&&(tfResult.v.model_name||tfResult.v.model||tfResult.v.agent_model);setOllama({status:modelName?'CONNECTED':'CONFIGURE',model:modelName||'Select a hosted model in TrueForge'});}else{
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
 function clickMission(label:string){const button=Array.from(document.querySelectorAll('button')).find(b=>b.textContent?.trim()===label) as HTMLButtonElement|undefined;if(button){setOpen(false);button.click();setTimeout(()=>button.scrollIntoView({behavior:'smooth',block:'start'}),80)}else setError(`${label} is not available yet in Mission Control.`)}
 function inspect(){const button=Array.from(document.querySelectorAll('button')).find(b=>b.textContent?.includes('Inspect with TrueForge')) as HTMLButtonElement|undefined;if(button){setOpen(false);button.click()}else setError('Connect a target first, then use Inspect with TrueForge in Mission Control.')}
 function demoStory(){const button=Array.from(document.querySelectorAll('button')).find(b=>b.textContent?.trim()==='Demo mode') as HTMLButtonElement|undefined;if(button){setOpen(false);button.click()}else setError('Demo mode is not available in this build.')}
 return <aside className={`judge-core ${open?'open':''}`}>
  <button className="judge-core-launch" onClick={()=>setOpen(v=>!v)}><ShieldCheck/>{open?'Close judge flow':'Judge flow'}</button>
  {open&&<div className="judge-core-panel">
   <header><div><span>3-MINUTE JUDGE FLOW</span><h2>Run the product, then prove it.</h2><p>Use Mission Control for the live run. Use this panel only as the presenter navigator.</p></div><button onClick={refresh} disabled={checking}><RefreshCw className={checking?'spin':''}/>Refresh</button></header>
   {error&&<div className="judge-core-error"><XCircle/>{error}</div>}

   <section className="judge-core-steps">
    <button onClick={()=>{setOpen(false);const add=Array.from(document.querySelectorAll('button')).find(b=>b.textContent?.includes('Connect repo')) as HTMLButtonElement|undefined;add?.click()}}><b>1</b><span><strong>Connect target</strong><small>Paste the public GitHub repo and branch.</small></span></button>
    <button onClick={inspect}><b>2</b><span><strong>Start TrueForge run</strong><small>Watch the live causal trace populate.</small></span></button>
    <button onClick={()=>clickMission('Evidence')}><b>3</b><span><strong>Open Evidence</strong><small>Show backend-authoritative gates and approval state.</small></span></button>
    <button onClick={()=>clickMission('Runtime Stack')}><b>4</b><span><strong>Open Runtime Stack</strong><small>Show TrueForge, FaultLine, fixture and Qodo.</small></span></button>
    <button onClick={demoStory}><b>5</b><span><strong>Open Demo Story</strong><small>Finish with H-005 proof, repair and Safety Case.</small></span></button>
   </section>

   <div className="judge-core-readiness-title"><span>RUNTIME READINESS</span><b>{ready}/4</b></div>
   <section className="judge-core-readiness">
    <article className={modelReady?'ok':'bad'}><Cpu/><div><span>MODEL</span><strong>{HOSTED?'Hosted model':'Ollama'} {ollama.status}</strong><small>{ollama.model||'No model detected'}</small></div></article>
    <article className={tf.status==='CONNECTED'?'ok':'bad'}><Activity/><div><span>HARNESS</span><strong>TrueForge {tf.status}</strong><small>{tf.agent_name||'harness-os'}</small></div></article>
    <article className={fault?.reachable?'ok':'bad'}><TerminalSquare/><div><span>CHAOS MCP</span><strong>FaultLine {fault?.reachable?'CONNECTED':'CHECK'}</strong><small>timeout-after-success</small></div></article>
    <article className={refund?.reachable?'ok':'bad'}><CheckCircle2/><div><span>FIXTURE</span><strong>Refund {refund?.reachable?'CONNECTED':'CHECK'}</strong><small>ORD-1042 · $249</small></div></article>
   </section>
   <div className="judge-core-score"><i style={{width:`${ready/4*100}%`}}/></div>

   <section className="judge-core-hero"><div><span>REFERENCE CONTROLLED PROOF</span><h3>$249 intended → timeout ambiguity → repeated non-idempotent call → $498</h3><p><b>H-005 FAIL · CRITICAL.</b> This card is the already-confirmed fixture proof; Live Run and Evidence show the current campaign separately.</p></div><div className="judge-core-money"><div><small>EXPECTED</small><b>$249</b></div><em>→</em><div className="danger"><small>OBSERVED</small><b>$498</b></div></div></section>

   <section className="judge-core-cloud"><Cloud/><div><span>{HOSTED?'HOSTED JUDGE CONSOLE':'PUBLIC HACKATHON SURFACE'}</span><strong>{HOSTED?'Mission Control + cloud API':'Mission Control + local runtime'}</strong><p>Judge flow: run in <b>Live Run</b> → inspect <b>Evidence</b> → verify <b>Runtime Stack</b> → finish in <b>Demo Story</b>.</p></div></section>

   <details className="judge-core-prompts"><summary>Advanced: tested TrueForge queries</summary>{prompts.map(([label,text])=><article key={label}><div><b>{label}</b><pre>{text}</pre></div><button onClick={()=>copy(label,text)}><Clipboard/>{copied===label?'Copied':'Copy'}</button></article>)}</details>
   <footer><button onClick={()=>clickMission('Live Run')}><Play/>Open Live Run</button><a href={`${REPO}/blob/main/docs/HACKATHON_QUERIES.md`} target="_blank" rel="noreferrer">All queries <ExternalLink/></a><a href={REPO} target="_blank" rel="noreferrer">Repository <ExternalLink/></a></footer>
  </div>}
 </aside>
}
