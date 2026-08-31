const DEFAULT_API=(import.meta.env.VITE_API_URL||'http://localhost:8080').replace(/\/$/,'');
const API_STORAGE_KEY='harness-os-api-base';

export function getApiBase(){
  try{return (localStorage.getItem(API_STORAGE_KEY)||DEFAULT_API).replace(/\/$/,'')}catch{return DEFAULT_API}
}
export function setApiBase(value:string){
  const normalized=(value||'').trim().replace(/\/$/,'');
  if(!/^https?:\/\//i.test(normalized))throw new Error('Control-plane URL must start with http:// or https://');
  localStorage.setItem(API_STORAGE_KEY,normalized);
  return normalized;
}
export function resetApiBase(){localStorage.removeItem(API_STORAGE_KEY);return DEFAULT_API}
export function isPublicApi(){try{const host=new URL(getApiBase()).hostname;return host!=='localhost'&&host!=='127.0.0.1'}catch{return false}}

export class ApiError extends Error{constructor(message:string,public status:number){super(message)}}
async function request<T>(path:string,init?:RequestInit):Promise<T>{
  const response=await fetch(`${getApiBase()}${path}`,{...init,headers:{'Content-Type':'application/json',...(init?.headers||{})}});
  if(!response.ok){let message=`Request failed (${response.status})`;try{const body=await response.json();message=body.detail?.message||body.detail||message}catch{}throw new ApiError(message,response.status)}
  return response.status===204?undefined as T:response.json();
}
async function operatorSnapshot(campaign_id?:string,refresh_qodo=false,agent_id?:string){
  if(refresh_qodo&&campaign_id){try{await request<any>(`/api/v1/campaigns/${campaign_id}/qodo-refresh`,{method:'POST'})}catch(e){if(!(e instanceof ApiError&&e.status===409))throw e}}
  const query=new URLSearchParams();if(campaign_id)query.set('campaign_id',campaign_id);if(agent_id)query.set('agent_id',agent_id);
  return request<any>(`/api/v1/operator-snapshot${query.toString()?`?${query}`:''}`)
}
export const api={
 health:()=>request<any>('/health'),dashboard:()=>request<any>('/api/v1/dashboard'),agents:()=>request<any[]>('/api/v1/agents'),createAgent:(body:any)=>request<any>('/api/v1/agents',{method:'POST',body:JSON.stringify(body)}),connectTarget:(body:any)=>request<any>('/api/v1/targets/connect',{method:'POST',body:JSON.stringify(body)}),inspectTarget:(id:string)=>request<any>(`/api/v1/targets/${id}/inspect`,{method:'POST'}),publicServices:(force=false)=>request<any>(`/api/v1/public-services?force=${force}`),operatorSnapshot,refreshQodo:(id:string)=>request<any>(`/api/v1/campaigns/${id}/qodo-refresh`,{method:'POST'}),trueforgeStatus:()=>request<any>('/api/v1/trueforge/status'),discover:(id:string)=>request<any>(`/api/v1/agents/${id}/discover`,{method:'POST'}),graph:(id:string)=>request<any>(`/api/v1/agents/${id}/graph`),contracts:(id:string)=>request<any[]>(`/api/v1/agents/${id}/contracts`),generateContract:(id:string)=>request<any>(`/api/v1/agents/${id}/contracts/generate`,{method:'POST'}),campaigns:()=>request<any[]>('/api/v1/campaigns'),createCampaign:(agent_id:string)=>request<any>('/api/v1/campaigns',{method:'POST',body:JSON.stringify({agent_id})}),campaign:(id:string)=>request<any>(`/api/v1/campaigns/${id}`),control:(id:string,action:string)=>request<any>(`/api/v1/campaigns/${id}/${action}`,{method:'POST'}),traces:(id:string)=>request<any[]>(`/api/v1/campaigns/${id}/traces`),certification:(id:string)=>request<any>(`/api/v1/campaigns/${id}/certification-status`),findings:()=>request<any[]>('/api/v1/findings'),approvals:()=>request<any[]>('/api/v1/approvals'),decide:(id:string,action:'approve'|'reject',reason:string)=>request<any>(`/api/v1/approvals/${id}/${action}`,{method:'POST',body:JSON.stringify({approver:'local-user',reason})}),cases:()=>request<any[]>('/api/v1/safety-cases'),integrations:()=>request<any>('/api/v1/integrations')};
export function subscribe(id:string,onEvent:(e:any)=>void,onError:(e:Event)=>void){const es=new EventSource(`${getApiBase()}/api/v1/campaigns/${id}/events`);es.onmessage=e=>onEvent(JSON.parse(e.data));['campaign.started','subagent.started','scenario.started','sandbox.started','tool.called','fault.injected','contract.failed','contract.passed','finding.created','remediation.generated','approval.requested','approval.approved','approval.rejected','campaign.completed','campaign.paused','campaign.resumed','campaign.cancelled'].forEach(type=>es.addEventListener(type,(e:any)=>onEvent(JSON.parse(e.data))));es.onerror=onError;return()=>es.close()}
