import React,{useEffect,useState}from'react';
import{Boxes,ExternalLink,GitBranch,Globe2,Play,Plus,RefreshCw,ShieldCheck}from'lucide-react';
import{api}from'./lib/api';

function deriveName(url:string){try{const parts=new URL(url).pathname.split('/').filter(Boolean);return parts.at(-1)||''}catch{return''}}

export default function TargetManager(){
 const[agents,setAgents]=useState<any[]>([]),[services,setServices]=useState<any[]>([]),[repo,setRepo]=useState(''),[branch,setBranch]=useState('main'),[name,setName]=useState(''),[nameTouched,setNameTouched]=useState(false),[busy,setBusy]=useState(''),[error,setError]=useState('');
 const active=agents[0];
 async function load(){try{const[a,s]=await Promise.all([api.agents(),api.publicServices()]);setAgents(a);setServices(s.services||[])}catch(e:any){setError(e.message)}}
 useEffect(()=>{load()},[]);
 async function connect(e:React.FormEvent){e.preventDefault();setBusy('connect');setError('');try{const derived=deriveName(repo.trim());if(!derived)throw new Error('Enter a valid GitHub repository URL.');const body={repository_url:repo.trim(),branch:branch.trim()||'main',name:(name.trim()||derived),harness_type:'TrueForge',config_path:null};await api.connectTarget(body);window.location.reload()}catch(e:any){setError(e.message)}finally{setBusy('')}}
 async function inspect(){if(!active)return;setBusy('inspect');setError('');try{await api.inspectTarget(active.id);window.location.reload()}catch(e:any){setError(e.message)}finally{setBusy('')}}
 const hostedReady=services.filter(x=>x.reachable).length;
 return <section className="target-manager" aria-label="Repository target manager">
  <div className="target-manager-head"><div><span className="target-kicker"><Boxes/>TARGET WORKSPACE</span><h2>Connect any GitHub repository to Harness OS</h2><p>Repository identity, TrueForge inspection, hosted FaultLine services and approval-gated remediation all meet in one local operator surface.</p></div><div className="hosted-score"><Globe2/><strong>{hostedReady}/{services.length||2}</strong><span>public services online</span></div></div>
  <div className="target-grid">
   <div className="target-current"><span>ACTIVE TARGET</span>{active?<><h3>{active.name}</h3>{active.repository_url.startsWith('http')?<a href={active.repository_url} target="_blank" rel="noreferrer">{active.repository_url}<ExternalLink/></a>:<p>{active.repository_url}</p>}<div className="target-meta"><b>{active.status}</b><span><GitBranch/>{active.branch}</span><span>Risk {active.risk||'UNKNOWN'}</span></div><button className="target-primary" type="button" onClick={inspect} disabled={busy==='inspect'}><Play/>{busy==='inspect'?'Starting TrueForge…':'Inspect with TrueForge'}</button></>:<p>No repository connected yet.</p>}</div>
   <form className="target-connect" onSubmit={connect}><div className="target-form-title"><Plus/><div><strong>Add another repository</strong><small>Public GitHub URL; credentials stay server-side.</small></div></div><label>Repository URL<input required placeholder="https://github.com/owner/repository" value={repo} onChange={e=>{const value=e.target.value;setRepo(value);if(!nameTouched)setName(deriveName(value))}}/></label><div className="target-form-row"><label>Branch<input required value={branch} onChange={e=>setBranch(e.target.value)}/></label><label>Display name<input value={name} onChange={e=>{setNameTouched(true);setName(e.target.value)}} placeholder="Auto from repository"/></label></div><button className="target-secondary" disabled={busy==='connect'}><ShieldCheck/>{busy==='connect'?'Connecting…':'Connect repository'}</button></form>
  </div>
  <div className="hosted-strip"><div className="hosted-title"><Globe2/><strong>PUBLIC RUNTIME BRIDGE</strong><button type="button" onClick={load}><RefreshCw/>Refresh</button></div>{services.map((s:any)=><a key={s.name} className={`hosted-service ${s.reachable?'online':'offline'}`} href={s.url} target="_blank" rel="noreferrer"><i/><div><strong>{s.name}</strong><span>{s.reachable?`ONLINE · ${s.latency_ms} ms`:`OFFLINE${s.http_status?` · HTTP ${s.http_status}`:''}`}</span></div><ExternalLink/></a>)}</div>
  {error&&<div className="target-error">{error}</div>}
 </section>
}
