import React,{useEffect,useMemo,useRef,useState}from'react';
import{Activity,AlertTriangle,CheckCircle2,ChevronRight,Clock3,ExternalLink,GitBranch,GitPullRequest,Globe2,LockKeyhole,Play,Plus,RefreshCw,Server,Settings2,ShieldCheck,TerminalSquare,Wifi,WifiOff,XCircle}from'lucide-react';
import{api,getApiBase,isPublicApi,setApiBase,subscribe}from'./lib/api';
import'./mission-control.css';

type Tab='run'|'evidence'|'integrations'|'targets';
const ACTIVE=['WAITING_APPROVAL','RUNNING','PLANNING','PAUSED'];
const DEFAULT_REPO='https://github.com/harshapriyag123/harness-os';
const gateLabels:any={sandbox:'Sandbox',human_approval:'Human approval',github_pr:'GitHub PR',qodo_review:'Qodo review',exact_replay:'Exact replay',safety_case:'Safety Case',repository_inspection:'Repository inspection',runtime_evidence:'Runtime evidence'};
const deriveName=(url:string)=>{try{const parts=new URL(url).pathname.split('/').filter(Boolean);return parts.length?parts[parts.length-1]:''}catch{return''}};
const cls=(s:string)=>String(s||'unknown').toLowerCase().replace(/_/g,'-').replace(/ /g,'-');

export default function MissionControl(){
 const[tab,setTab]=useState<Tab>('run');
 const[agents,setAgents]=useState<any[]>([]),[campaigns,setCampaigns]=useState<any[]>([]),[selectedId,setSelectedId]=useState(''),[snapshot,setSnapshot]=useState<any>();
 const[services,setServices]=useState<any[]>([]),[tf,setTf]=useState<any>(),[integrations,setIntegrations]=useState<any>();
 const[apiHealth,setApiHealth]=useState<'checking'|'online'|'offline'>('checking'),[apiBase,setApiBaseState]=useState(getApiBase()),[runtimeOpen,setRuntimeOpen]=useState(false),[runtimeDraft,setRuntimeDraft]=useState(getApiBase());
 const[busy,setBusy]=useState(''),[error,setError]=useState(''),[connectOpen,setConnectOpen]=useState(false),[confirming,setConfirming]=useState(false);
 const[repo,setRepo]=useState(DEFAULT_REPO),[branch,setBranch]=useState('main'),[displayName,setDisplayName]=useState('Harness OS'),[nameTouched,setNameTouched]=useState(false);
 const requestToken=useRef(0),selectedRef=useRef('');
 const selected=agents.find(a=>a.id===selectedId)||(!selectedId?agents[0]:undefined);
 const selectedCampaign=useMemo(()=>campaigns.find(c=>c.agent_id===selected?.id&&ACTIVE.includes(c.status))||campaigns.find(c=>c.agent_id===selected?.id),[campaigns,selected?.id]);
 const campaign=snapshot?.campaign,cert=snapshot?.certification,approval=snapshot?.approval,events=snapshot?.events||[];
 useEffect(()=>{selectedRef.current=selectedId},[selectedId]);

 async function probeApi(){setApiHealth('checking');try{await api.health();setApiHealth('online')}catch{setApiHealth('offline')}}
 async function loadRuntime(force=false){
  const results=await Promise.allSettled([api.publicServices(force),api.trueforgeStatus()]);
  if(results[0].status==='fulfilled')setServices(results[0].value.services||[]);else setServices([]);
  if(results[1].status==='fulfilled')setTf(results[1].value);else setTf({status:'UNAVAILABLE',retryable:true,detail:'TrueForge status could not be loaded from the selected control plane.'});
 }
 async function loadCore(targetOverride?:string){
  const token=++requestToken.current,targetId=targetOverride!==undefined?targetOverride:selectedRef.current;
  try{
   const[a,c]=await Promise.all([api.agents(),api.campaigns()]);if(token!==requestToken.current)return;
   setAgents(a||[]);setCampaigns(c||[]);
   const effectiveTarget=targetId||((a||[])[0]?.id||'');
   if(!selectedRef.current&&effectiveTarget){selectedRef.current=effectiveTarget;setSelectedId(effectiveTarget)}
   const chosen=effectiveTarget?(c||[]).find((x:any)=>x.agent_id===effectiveTarget&&ACTIVE.includes(x.status))||(c||[]).find((x:any)=>x.agent_id===effectiveTarget):undefined;
   const snap=await api.operatorSnapshot(chosen?.id,false,effectiveTarget||undefined);
   if(token===requestToken.current)setSnapshot(snap);
  }catch(e:any){if(token===requestToken.current){setError(e.message);setApiHealth('offline')}}
 }
 async function boot(targetOverride?:string){await probeApi();loadCore(targetOverride);loadRuntime(false)}
 useEffect(()=>{boot(selectedId);const core=setInterval(()=>loadCore(selectedRef.current),5000),runtime=setInterval(()=>loadRuntime(false),20000);return()=>{clearInterval(core);clearInterval(runtime);requestToken.current++}},[]);
 useEffect(()=>{
  if(!selectedCampaign?.id||selectedCampaign.agent_id!==selected?.id)return;
  let alive=true;const campaignId=selectedCampaign.id,targetId=selected.id;
  api.operatorSnapshot(campaignId,false,targetId).then(x=>{if(alive&&selectedRef.current===targetId){setSnapshot(x);setConfirming(false)}}).catch(()=>{});
  const stop=subscribe(campaignId,()=>api.operatorSnapshot(campaignId,false,targetId).then(x=>{if(alive&&selectedRef.current===targetId)setSnapshot(x)}).catch(()=>{}),()=>{});
  return()=>{alive=false;stop()}
 },[selectedCampaign?.id,selected?.id]);

 async function applyRuntime(e:React.FormEvent){e.preventDefault();try{const next=setApiBase(runtimeDraft);setApiBaseState(next);setRuntimeOpen(false);requestToken.current++;setAgents([]);setCampaigns([]);setSelectedId('');selectedRef.current='';setSnapshot(undefined);setTf(undefined);setServices([]);setError('');await boot('')}catch(e:any){setError(e.message)}}
 async function connect(e:React.FormEvent){e.preventDefault();setBusy('connect');setError('');try{const name=displayName.trim()||deriveName(repo.trim());if(!name)throw new Error('Enter a valid public GitHub repository URL.');const a=await api.connectTarget({repository_url:repo.trim(),branch:branch.trim()||'main',name,harness_type:'TrueForge',config_path:null});requestToken.current++;selectedRef.current=a.id;setSelectedId(a.id);setSnapshot(undefined);setConnectOpen(false);await loadCore(a.id)}catch(e:any){setError(e.message)}finally{setBusy('')}}
 async function inspect(){if(!selected)return;const targetId=selected.id,token=++requestToken.current;setBusy('inspect');setError('');setSnapshot(undefined);setConfirming(false);try{const c=await api.inspectTarget(targetId);if(token!==requestToken.current||selectedRef.current!==targetId)return;setCampaigns(v=>[c,...v.filter(x=>x.id!==c.id)]);setSnapshot(await api.operatorSnapshot(c.id,false,targetId));setTab('run')}catch(e:any){if(token===requestToken.current)setError(e.message)}finally{if(token===requestToken.current)setBusy('')}}
 async function retryTrueForge(){setBusy('trueforge');setError('');try{setTf(await api.trueforgeStatus())}catch(e:any){setTf({status:'UNAVAILABLE',detail:e.message});setError(e.message)}finally{setBusy('')}}
 async function loadIntegrations(){setBusy('integrations');try{setIntegrations(await api.integrations());await loadRuntime(true)}catch(e:any){setError(e.message)}finally{setBusy('')}}
 async function syncEvidence(){if(!selected)return;setBusy('sync');try{if(campaign?.id)setSnapshot(await api.operatorSnapshot(campaign.id,true,selected.id));await loadRuntime(true)}catch(e:any){setError(e.message)}finally{setBusy('')}}
 async function decide(action:'approve'|'reject'){
  if(!selected?.id||!campaign?.id||campaign.agent_id!==selected.id||!approval?.id||approval.campaign_id!==campaign.id){setConfirming(false);setError('Approval context changed or belongs to another target. Refresh before deciding.');return}
  const targetId=selected.id,campaignId=campaign.id;setBusy(action);setError('');
  try{await api.decide(approval.id,action,action==='approve'?'Operator reviewed the exact bound GitHub MCP calls in Mission Control and confirmed approval before execution.':'Operator rejected the proposed irreversible GitHub MCP calls.');if(selectedRef.current!==targetId)return;setConfirming(false);setSnapshot(await api.operatorSnapshot(campaignId,true,targetId))}catch(e:any){setError(e.message)}finally{setBusy('')}
 }
 function pickTarget(id:string){requestToken.current++;selectedRef.current=id;setSelectedId(id);setSnapshot(undefined);setConfirming(false);setError('');loadCore(id)}
 function useDemoRepo(){setRepo(DEFAULT_REPO);setBranch('main');setDisplayName('Harness OS');setNameTouched(true);setConnectOpen(true)}

 const next=cert?.next_gate||((campaign?.status==='ERROR')?'runtime_evidence':'repository_inspection');
 const waiting=approval?.status==='PENDING'?'YOUR APPROVAL':campaign?.status==='ERROR'?'RUNTIME RECOVERY':gateLabels[next]||'NEXT EVIDENCE';
 const lastEvent=events.length?events[events.length-1]:undefined,online=services.filter((s:any)=>s.reachable).length,tfStatus=tf?.status||'CHECKING';
 const publicControl=isPublicApi();
 return <main className="mc-shell">
  <header className="mc-header">
   <div className="mc-brand"><div className="mc-logo"><ShieldCheck/></div><div><strong>Harness OS</strong><span>Agent Safety Mission Control</span></div></div>
   <div className="mc-header-right">
    <button className={`mc-health ${apiHealth}`} onClick={()=>setRuntimeOpen(v=>!v)}><Server/><span><b>{publicControl?'PUBLIC':'LOCAL'} CONTROL PLANE</b><small>{apiHealth.toUpperCase()}</small></span></button>
    <span className={`mc-runtime ${tfStatus==='CONNECTED'?'ok':tfStatus==='CHECKING'?'pending':'bad'}`}><i/>{tfStatus} TrueForge</span>
    <span className={`mc-runtime ${online===services.length&&services.length?'ok':'pending'}`}><Globe2/>{online}/{services.length||2} public</span>
   </div>
  </header>

  {runtimeOpen&&<form className="mc-runtime-config" onSubmit={applyRuntime}><div><Settings2/><div><strong>Control-plane endpoint</strong><p>Point this browser UI at your public Harness OS API for the demo. Do not use the refund fixture URL here.</p></div></div><input value={runtimeDraft} onChange={e=>setRuntimeDraft(e.target.value)} placeholder="https://your-harness-os-api.onrender.com"/><button className="mc-primary">Connect endpoint</button></form>}

  <section className="mc-targetbar">
   <div className="mc-target-selector"><span>ACTIVE TARGET</span><select value={selected?.id||''} onChange={e=>pickTarget(e.target.value)} disabled={!agents.length}><option value="">{agents.length?'Choose repository':'No repository connected'}</option>{agents.map(a=><option key={a.id} value={a.id}>{a.name} · {a.branch}</option>)}</select></div>
   <div className="mc-target-url">{selected?.repository_url?.startsWith('http')?<a href={selected.repository_url} target="_blank" rel="noreferrer">{selected.repository_url}<ExternalLink/></a>:<span>Connect a GitHub repository to start a real inspection.</span>}</div>
   <button type="button" className="mc-secondary" onClick={()=>setConnectOpen(v=>!v)}><Plus/>{connectOpen?'Close':'Connect repo'}</button>
   <button type="button" className="mc-primary" onClick={inspect} disabled={!selected||busy==='inspect'||apiHealth!=='online'}><Play/>{busy==='inspect'?'Starting…':'Inspect with TrueForge'}</button>
  </section>

  {connectOpen&&<form className="mc-connect" onSubmit={connect}><div className="mc-connect-head"><GitBranch/><div><strong>Connect a repository</strong><p>Harness OS verifies the public repo + branch before it becomes a target.</p></div></div><label>Repository URL<input required value={repo} placeholder={DEFAULT_REPO} onChange={e=>{const v=e.target.value;setRepo(v);if(!nameTouched)setDisplayName(deriveName(v))}}/></label><label>Branch<input required value={branch} onChange={e=>setBranch(e.target.value)}/></label><label>Display name<input value={displayName} placeholder="Auto from repository" onChange={e=>{setNameTouched(true);setDisplayName(e.target.value)}}/></label><button className="mc-primary" disabled={busy==='connect'}>{busy==='connect'?'Verifying…':'Verify & connect'}</button></form>}

  {error&&<div className="mc-error"><XCircle/>{error}<button onClick={()=>setError('')}>Dismiss</button></div>}

  {!selected&&<section className="mc-onboarding">
   <div className="mc-onboarding-copy"><div className="mc-kicker"><span>TRUEFORGE</span><span>GITHUB MCP</span><span>QODO</span></div><h1>See what your agent will do<br/><em>before it does it.</em></h1><p>Connect a repository. Harness OS sends it through TrueForge, watches every tool call, stops irreversible actions for approval, and turns runtime evidence into a Safety Case.</p><div className="mc-onboarding-actions"><button className="mc-primary mc-large" onClick={useDemoRepo}><GitBranch/>Connect Harness OS repo</button><button className="mc-secondary mc-large" onClick={()=>setRuntimeOpen(true)}><Globe2/>Set public demo API</button></div><div className="mc-demo-repo"><span>DEMO REPOSITORY</span><code>{DEFAULT_REPO}</code></div></div>
   <div className="mc-flow-card"><div className="mc-flow-head"><Activity/><span>LIVE ASSURANCE FLOW</span></div>{['Repository inspection','TrueForge sandbox','Human approval','GitHub MCP PR','Qodo review','Safety Case'].map((label,i)=><div className="mc-flow-step" key={label}><span>{String(i+1).padStart(2,'0')}</span><strong>{label}</strong>{i===0?<b>START HERE</b>:<ChevronRight/>}</div>)}<div className="mc-flow-footer"><LockKeyhole/><span>Irreversible writes pause before execution.</span></div></div>
  </section>}

  {selected&&<>
   {tf&&tf.status!=='CONNECTED'&&<section className="mc-recovery"><div><AlertTriangle/><div><strong>TrueForge needs attention</strong><p>{tf.detail||'The runtime did not answer the control plane.'}</p><small>{tf.diagnosis||'Verify the public API can reach your TrueForge server.'}</small></div></div><button className="mc-secondary" onClick={retryTrueForge} disabled={busy==='trueforge'}><RefreshCw className={busy==='trueforge'?'spin':''}/>{busy==='trueforge'?'Retrying…':'Retry TrueForge'}</button></section>}
   <nav className="mc-tabs">{(['run','evidence','integrations','targets'] as Tab[]).map(t=><button key={t} className={tab===t?'active':''} onClick={()=>{setTab(t);if(t==='integrations'&&!integrations)loadIntegrations()}}>{t==='run'?'Live Run':t==='evidence'?'Evidence':t==='integrations'?'Runtime Stack':'Targets'}</button>)}</nav>

   {tab==='run'&&<section className="mc-run">
    <div className="mc-run-hero"><div><span className="mc-eyebrow">ACTIVE SAFETY RUN</span><h2>{selected.name}</h2><a href={selected.repository_url} target="_blank" rel="noreferrer">{selected.repository_url}<ExternalLink/></a></div><div className="mc-run-meta"><span className={`mc-status ${cls(campaign?.status||'ready')}`}>{campaign?.status||'READY'}</span><span>Branch <b>{selected.branch}</b></span><span>Risk <b>{selected.risk||'UNKNOWN'}</b></span></div></div>
    <div className="mc-state-grid"><article><span><Activity/>WHAT IT'S DOING</span><strong>{campaign?.status==='ERROR'?'Recovering runtime':gateLabels[next]||'Ready to inspect'}</strong><p>{campaign?.current_stage||'Ready to start a TrueForge repository inspection.'}</p></article><article className={approval?.status==='PENDING'?'attention':''}><span><Clock3/>WHAT IT'S WAITING ON</span><strong>{waiting}</strong><p>{approval?.status==='PENDING'?'TrueForge is paused before the irreversible GitHub write.':campaign?.status==='ERROR'?'Runtime recovery is required before continuing.':'The next evidence gate controls progress.'}</p></article><article><span><CheckCircle2/>WHAT IT DID</span><strong>{lastEvent?.title||'No evidence yet'}</strong><p>{lastEvent?.detail||'Runtime history will appear here as TrueForge acts.'}</p></article></div>
    <div className="mc-runbar"><span>Session <code>{campaign?.trueforge_session_id||'not started'}</code></span><span>Stage <code>{cert?.stage||campaign?.current_stage||'idle'}</code></span><button className="mc-icon-btn" onClick={syncEvidence} disabled={busy==='sync'}><RefreshCw className={busy==='sync'?'spin':''}/>Sync evidence</button></div>
    <div className="mc-gates">{cert?.generic?<><div className={`mc-gate ${campaign?.status==='COMPLETED'?'done':campaign?.status==='ERROR'?'locked':'current'}`}><TerminalSquare/><span>Repository inspection</span><b>{campaign?.status==='COMPLETED'?'DONE':campaign?.status==='ERROR'?'FAILED':'CURRENT'}</b></div><ChevronRight/><div className="mc-gate locked"><ShieldCheck/><span>Safety findings</span><b>EVIDENCE-DRIVEN</b></div></>:['sandbox','human_approval','github_pr','qodo_review','exact_replay','safety_case'].map((g,i)=>{const passed=!!cert?.gates?.[g]?.passed,current=cert?.next_gate===g;return <React.Fragment key={g}><div className={`mc-gate ${passed?'done':current?'current':'locked'}`}>{passed?<CheckCircle2/>:current?<Clock3/>:<LockKeyhole/>}<span>{gateLabels[g]}</span><b>{passed?'VERIFIED':current?'CURRENT':'LOCKED'}</b></div>{i<5&&<ChevronRight/>}</React.Fragment>})}</div>
    {approval?.status==='PENDING'&&approval.campaign_id===campaign?.id&&campaign?.agent_id===selected?.id&&<section className="mc-approval"><div className="mc-approval-title"><LockKeyhole/><div><span>IRREVERSIBLE STEP — PAUSED BEFORE EXECUTION</span><h2>Review the exact GitHub MCP scope</h2><p>Nothing executes until you confirm.</p></div></div><div className="mc-scope">{(approval.approved_targets||[]).map((t:any)=><article key={t.tool_call_id}><GitPullRequest/><div><strong>{t.tool}</strong><span>{t.repository} · {t.branch||'tool-selected branch'}</span></div><code>{t.tool_call_id}</code></article>)}</div>{!confirming?<div className="mc-actions"><button className="mc-danger" onClick={()=>decide('reject')} disabled={!!busy}><XCircle/>Reject</button><button className="mc-primary" onClick={()=>setConfirming(true)}><ShieldCheck/>Review & approve</button></div>:<div className="mc-confirm"><div><strong>Confirm approval</strong><p>Only the bound calls shown above will resume.</p></div><button className="mc-secondary" onClick={()=>setConfirming(false)}>Back</button><button className="mc-primary" onClick={()=>decide('approve')} disabled={busy==='approve'}>{busy==='approve'?'Approving…':'Confirm & resume TrueForge'}</button></div>}</section>}
    <div className="mc-feed"><div className="mc-section-title"><Activity/><strong>Live causal trace</strong><span>{events.length} persisted events</span></div>{events.length?events.slice(-8).reverse().map((e:any)=><article key={e.id||e.sequence}><i/><div><strong>{e.title||e.event_type}</strong><p>{e.detail}</p><small>{e.source||'HARNESS OS'} · {e.timestamp?new Date(e.timestamp).toLocaleTimeString():`#${e.sequence}`}</small></div></article>):<div className="mc-empty"><Activity/><strong>Waiting for runtime evidence</strong><span>Click “Inspect with TrueForge” to start.</span></div>}</div>
   </section>}

   {tab==='evidence'&&<section className="mc-panel"><div className="mc-section-title"><ShieldCheck/><strong>Evidence inspector</strong><span>backend-authoritative</span></div><div className="mc-evidence-grid"><article><span>Campaign</span><strong>{campaign?.id||'No campaign'}</strong><pre>{JSON.stringify({target:selected.name,status:campaign?.status,stage:campaign?.current_stage,kind:campaign?.campaign_kind},null,2)}</pre></article><article><span>Certification</span><strong>{cert?.next_gate||'Not started'}</strong><pre>{JSON.stringify(cert?.gates||{},null,2)}</pre></article><article><span>Approval</span><strong>{approval?.status||'NONE'}</strong><pre>{JSON.stringify(approval?{id:approval.id,campaign_id:approval.campaign_id,status:approval.status,targets:approval.approved_targets}:null,null,2)}</pre></article></div></section>}

   {tab==='integrations'&&<section className="mc-panel"><div className="mc-section-title"><Server/><strong>Runtime stack</strong><button className="mc-icon-btn" onClick={loadIntegrations}><RefreshCw/>Refresh</button></div><div className="mc-stack-summary"><article><span>CONTROL PLANE</span><strong>{publicControl?'PUBLIC':'LOCAL'}</strong><code>{apiBase}</code></article><article><span>TRUEFORGE</span><strong>{tfStatus}</strong><small>{tf?.detail||'Status pending'}</small></article><article><span>PUBLIC SERVICES</span><strong>{online}/{services.length||2} ONLINE</strong><small>FaultLine + fixture health</small></article></div><div className="mc-integration-grid">{(integrations?.integrations||[]).map((i:any)=><article key={i.name} className={cls(i.status)}><div><i/><strong>{i.name}</strong><span>{i.status}</span></div><p>{i.detail}</p>{i.href&&<a href={i.href} target="_blank" rel="noreferrer">Inspect evidence <ExternalLink/></a>}</article>)}</div><div className="mc-service-row">{services.map(s=><a key={s.name} href={s.url} target="_blank" rel="noreferrer" className={s.reachable?'online':'offline'}>{s.reachable?<Wifi/>:<WifiOff/>}<div><strong>{s.name}</strong><span>{s.reachable?`ONLINE · ${s.latency_ms} ms`:`OFFLINE${s.http_status?` · HTTP ${s.http_status}`:''}`}</span></div><ExternalLink/></a>)}</div></section>}

   {tab==='targets'&&<section className="mc-panel"><div className="mc-section-title"><GitBranch/><strong>Connected repositories</strong><button className="mc-primary compact" onClick={()=>setConnectOpen(true)}><Plus/>Add repository</button></div><div className="mc-target-list">{agents.map(a=><button key={a.id} className={selected?.id===a.id?'selected':''} onClick={()=>{pickTarget(a.id);setTab('run')}}><div><strong>{a.name}</strong><span>{a.repository_url}</span></div><div><b>{a.status}</b><span>{a.branch}</span><span>Risk {a.risk||'UNKNOWN'}</span></div><ChevronRight/></button>)}</div></section>}
  </>}
 </main>
}
