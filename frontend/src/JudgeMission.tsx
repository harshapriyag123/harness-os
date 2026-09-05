import React,{useEffect,useMemo,useState}from'react';
import{Activity,ArrowRight,CheckCircle2,CircleDollarSign,ExternalLink,GitBranch,Play,RefreshCw,Server,ShieldAlert,ShieldCheck,Sparkles,TerminalSquare}from'lucide-react';
import{api}from'./lib/api';
import'./judge-mission.css';

const REPO='https://github.com/harshapriyag123/harness-os';
const TARGET='CustomerSupportAgent';
const SCENARIO='H005-REFUND-249';
const ACTIVE=['WAITING_APPROVAL','RUNNING','PLANNING','PAUSED'];

type Health={tf?:any;services:any[]};

function clickText(selector:string,text:string){
 const node=Array.from(document.querySelectorAll(selector)).find(el=>el.textContent?.trim().toLowerCase().includes(text.toLowerCase())) as HTMLElement|undefined;
 node?.click();
 if(node)node.scrollIntoView({behavior:'smooth',block:'start'});
 return !!node;
}

export default function JudgeMission(){
 const[health,setHealth]=useState<Health>({services:[]});
 const[agents,setAgents]=useState<any[]>([]);
 const[campaigns,setCampaigns]=useState<any[]>([]);
 const[busy,setBusy]=useState(false);
 const[error,setError]=useState('');
 const[lastAction,setLastAction]=useState('Ready for the judge');

 async function refresh(force=false){
  setError('');
  try{
   const[tf,svc,a,c]=await Promise.all([api.trueforgeStatus(force),api.publicServices(force),api.agents(),api.campaigns()]);
   setHealth({tf,services:svc.services||[]});setAgents(a||[]);setCampaigns(c||[]);
  }catch(e:any){setError(e.message||String(e))}
 }
 useEffect(()=>{refresh(false)},[]);

 const target=useMemo(()=>agents.find(a=>String(a.name).toLowerCase()===TARGET.toLowerCase())||agents.find(a=>String(a.repository_url||'').includes('harshapriyag123/harness-os')),[agents]);
 const campaign=useMemo(()=>campaigns.find(c=>c.agent_id===target?.id&&ACTIVE.includes(c.status))||campaigns.find(c=>c.agent_id===target?.id),[campaigns,target?.id]);
 const fault=health.services.find(s=>String(s.name).toLowerCase().includes('faultline'));
 const fixture=health.services.find(s=>String(s.name).toLowerCase().includes('refund'));
 const tfOk=health.tf?.status==='CONNECTED';
 const readiness=[tfOk,!!fault?.reachable,!!fixture?.reachable,!!target].filter(Boolean).length;

 function openTab(label:string){if(!clickText('.mc-tabs button',label))setError(`Could not open ${label}. Refresh the page and try again.`)}
 function openDemo(){if(!clickText('button','Demo mode'))setError('Demo Mode is not available in this build.')}

 async function launch(){
  if(busy)return;setBusy(true);setError('');setLastAction('Preparing controlled H-005 mission…');
  try{
   let activeTarget=target;
   if(!activeTarget){
    setLastAction('Connecting prepared CustomerSupportAgent target…');
    activeTarget=await api.connectTarget({repository_url:REPO,branch:'main',name:TARGET,harness_type:'TrueForge',config_path:null});
    setAgents(v=>[activeTarget,...v.filter(x=>x.id!==activeTarget.id)]);
   }
   setLastAction('Starting TrueForge reliability inspection…');
   const started=await api.inspectTarget(activeTarget.id);
   setCampaigns(v=>[started,...v.filter(x=>x.id!==started.id)]);
   setLastAction(`Live campaign ${started.id||SCENARIO} started`);
   setTimeout(()=>openTab('Live Run'),250);
   setTimeout(()=>refresh(false),1200);
  }catch(e:any){setError(e.message||String(e));setLastAction('Mission launch needs attention')}
  finally{setBusy(false)}
 }

 return <section className="jm-shell" aria-label="Harness OS judge mission">
  <div className="jm-aurora"/>
  <header className="jm-top"><div className="jm-badge"><Sparkles/>JUDGE MISSION · H-005</div><div className="jm-live"><i className={campaign&&ACTIVE.includes(campaign.status)?'on':''}/>{campaign?.status||'READY'}</div></header>
  <div className="jm-grid">
   <div className="jm-main">
    <span className="jm-eyebrow">AUTONOMOUS AGENT RELIABILITY CRASH TEST</span>
    <h1>Can one <em>$249</em> refund become <strong>$498</strong>?</h1>
    <p>Harness OS uses <b>TrueForge</b> to inspect the agent, drive a deterministic timeout-after-success fault through FaultLine, preserve causal evidence, and stop before consequential repository writes.</p>
    <div className="jm-meta"><span><ShieldCheck/>{TARGET}</span><span><GitBranch/>main</span><span><TerminalSquare/>{SCENARIO}</span></div>
    <div className="jm-actions"><button className="jm-launch" onClick={launch} disabled={busy}><Play/>{busy?'Launching controlled test…':campaign&&ACTIVE.includes(campaign.status)?'Resume live mission':'Run H-005 reliability test'}<ArrowRight/></button><button className="jm-secondary" onClick={()=>openTab('Evidence')}>Open evidence</button><button className="jm-secondary" onClick={openDemo}>3-minute story</button></div>
    <div className="jm-action-status"><Activity/><span>{lastAction}</span>{error&&<strong>{error}</strong>}</div>
   </div>
   <aside className="jm-proof">
    <div className="jm-proof-title"><ShieldAlert/><div><span>CONFIRMED CONTROLLED REFERENCE</span><b>Failure signature</b></div></div>
    <div className="jm-money"><article><small>EXPECTED</small><strong>$249</strong><span>1 effect</span></article><ArrowRight/><article className="bad"><small>OBSERVED</small><strong>$498</strong><span>2 effects</span></article></div>
    <p>Remote effect committed → success response lost → ambiguous timeout → repeated non-idempotent execution.</p>
   </aside>
  </div>
  <div className="jm-runtime">
   <button className={tfOk?'ok':'warn'} onClick={()=>refresh(true)}><Server/><span>TRUEFORGE</span><b>{tfOk?'CONNECTED':health.tf?.status==='RATE_LIMITED'?'RATE LIMITED':'CHECK'}</b></button>
   <button className={fault?.reachable?'ok':'warn'} onClick={()=>refresh(true)}><TerminalSquare/><span>FAULTLINE MCP</span><b>{fault?.reachable?'CONNECTED':'CHECK'}</b></button>
   <button className={fixture?.reachable?'ok':'warn'} onClick={()=>refresh(true)}><CircleDollarSign/><span>REFUND FIXTURE</span><b>{fixture?.reachable?'CONNECTED':'CHECK'}</b></button>
   <button className={target?'ok':'warn'} onClick={launch}><ShieldCheck/><span>DEMO TARGET</span><b>{target?'READY':'PREPARE'}</b></button>
   <div className="jm-score"><strong>{readiness}/4</strong><span>mission prerequisites</span><i><u style={{width:`${readiness/4*100}%`}}/></i></div>
  </div>
  <nav className="jm-nav" aria-label="Judge demo shortcuts">
   <button onClick={()=>openTab('Live Run')}><Activity/>Live Run</button>
   <button onClick={()=>openTab('Evidence')}><CheckCircle2/>Evidence</button>
   <button onClick={()=>openTab('Runtime Stack')}><Server/>Runtime Stack</button>
   <button onClick={openDemo}><Sparkles/>Flight Recorder · Repair · Safety Case</button>
   <a href={REPO} target="_blank" rel="noreferrer">Source / Qodo<ExternalLink/></a>
  </nav>
 </section>
}
