import './judge-integrations.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8080';

type Integration = {name:string;status:string;detail:string;href?:string|null;proof?:Record<string,unknown>};
type IntegrationPayload = {mode:string;pipeline?:string;integrations:Integration[]};
const root=document.getElementById('judge-live-integrations');

function normalized(status:string){return status.toLowerCase().replaceAll('_',' ')}
function statusClass(status:string){const value=normalized(status);if(value.includes('connected')||value.includes('evidence found')||value.includes('configured'))return'ok';if(value.includes('error')||value.includes('unavailable'))return'bad';return'warn'}
function proofText(item:Integration){
 if(item.name==='Qodo Review'&&item.proof){const count=Number(item.proof.qodo_events||0);const pr=item.proof.pr_number?`PR #${item.proof.pr_number}`:'review evidence';return`${count} Qodo event${count===1?'':'s'} · ${pr}`}
 if(item.name==='TrueForge'&&item.status==='CONNECTED')return'Live runtime capability check';
 if(item.name==='Safety Case'&&item.proof)return`${Number(item.proof.cases||0)} persisted case${Number(item.proof.cases||0)===1?'':'s'}`;
 return normalized(item.status).toUpperCase();
}
function card(item:Integration,index:number,total:number){return `
 <article class="judge-integration-card ${statusClass(item.status)}"><div class="judge-integration-head"><span class="judge-step">${String(index+1).padStart(2,'0')}</span><span class="judge-dot" aria-hidden="true"></span><strong>${item.name}</strong></div><div class="judge-integration-status">${normalized(item.status).toUpperCase()}</div><p>${item.detail}</p><small>${proofText(item)}</small>${item.href?`<a href="${item.href}" target="_blank" rel="noreferrer">Open evidence ↗</a>`:''}</article>${index<total-1?'<div class="judge-pipeline-arrow" aria-hidden="true">→</div>':''}`}
async function load(){
 if(!root)return;root.innerHTML='<div class="judge-live-loading">Checking TrueForge + Qodo evidence…</div>';
 try{const response=await fetch(`${API}/api/v1/integrations`,{headers:{Accept:'application/json'}});if(!response.ok)throw new Error(`API ${response.status}`);const payload=(await response.json())as IntegrationPayload;const wanted=['TrueForge','Chaos MCP','GitHub MCP','Qodo Review','Safety Case'];const integrations=wanted.map(name=>payload.integrations.find(item=>item.name===name)).filter(Boolean)as Integration[];const healthy=integrations.filter(item=>statusClass(item.status)==='ok').length;
 root.innerHTML=`<section class="judge-live-panel" aria-label="Live agent safety evidence pipeline"><div class="judge-live-title"><div><span class="judge-kicker">LIVE JUDGE MODE</span><h2>Execution → Evidence → Review → Release</h2><p>${payload.pipeline||'TrueForge → FaultLine MCP → GitHub MCP → Qodo Review → Safety Case'}</p></div><div class="judge-live-score"><strong>${healthy}/${integrations.length}</strong><span>signals ready</span></div></div><div class="judge-pipeline">${integrations.map((item,i)=>card(item,i,integrations.length)).join('')}</div><div class="judge-live-foot"><span><b>Mode:</b> ${String(payload.mode||'unknown').toUpperCase()}</span><span>No mocked Qodo status: review evidence is read from GitHub.</span><button id="judge-refresh-integrations" type="button">Refresh evidence</button></div></section>`;document.getElementById('judge-refresh-integrations')?.addEventListener('click',load)
 }catch(error){root.innerHTML=`<section class="judge-live-panel judge-live-error"><div><span class="judge-kicker">JUDGE MODE</span><h2>Integration evidence unavailable</h2></div><p>The React UI is running, but it cannot currently reach the Harness OS control-plane API at <code>${API}</code>. Start the API or set <code>VITE_API_URL</code>, then refresh.</p><button id="judge-refresh-integrations" type="button">Retry connection</button></section>`;document.getElementById('judge-refresh-integrations')?.addEventListener('click',load)}
}
load();
