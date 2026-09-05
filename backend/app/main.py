import asyncio,json,os
from fastapi import FastAPI,HTTPException,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from . import engine,store,trueforge_runtime,verification_artifacts,repository_targets,public_services,operator_control
from .integrations import qodo
from .integrations.trueforge import TrueForgeClient
from .models import AgentCreate,CampaignCreate,Decision,InvariantUpdate

def _cors_origins():
 configured=[x.strip().rstrip('/') for x in os.getenv('HARNESS_OS_CORS_ORIGINS','').split(',') if x.strip()]
 return list(dict.fromkeys(['http://localhost:5173',*configured]))

app=FastAPI(title='Harness OS API',version='1.8.1')
app.add_middleware(CORSMiddleware,allow_origins=_cors_origins(),allow_methods=['*'],allow_headers=['*'])

def required(kind,item_id):
 item=store.get(kind,item_id)
 if not item:raise HTTPException(404,detail={'code':'NOT_FOUND','message':f'{kind[:-1]} not found'})
 return item

def fail(exc):
 raise HTTPException(404 if isinstance(exc,KeyError) else 409 if isinstance(exc,ValueError) else 503,detail={'code':exc.__class__.__name__.upper(),'message':str(exc).strip("'")})

@app.get('/')
def root():return {'service':'Harness OS API','status':'ok','mode':engine.MODE,'health':'/health','dashboard':'/api/v1/dashboard','operator_snapshot':'/api/v1/operator-snapshot','trueforge_status':'/api/v1/trueforge/status','public_services':'/api/v1/public-services','docs':'/docs'}
@app.get('/health')
def health():return {'status':'ok','mode':engine.MODE}
@app.get('/api/v1/dashboard')
def dashboard():return engine.dashboard()
@app.get('/api/v1/operator-snapshot')
def operator_snapshot(campaign_id:str|None=None,agent_id:str|None=None):return operator_control.snapshot(campaign_id,refresh_qodo=False,agent_id=agent_id)
@app.get('/api/v1/trueforge/status')
def trueforge_status(force:bool=False):return operator_control.trueforge_status(force=force)
@app.post('/api/v1/agents',status_code=201)
def create_agent(body:AgentCreate):
 try:return engine.create_agent(body.model_dump())
 except Exception as exc:fail(exc)
@app.post('/api/v1/targets/connect',status_code=201)
def connect_target(body:AgentCreate):
 try:return repository_targets.connect_target(body.model_dump())
 except Exception as exc:fail(exc)
@app.post('/api/v1/targets/{agent_id}/inspect',status_code=201)
def inspect_target(agent_id:str):
 try:return repository_targets.start_inspection(agent_id)
 except Exception as exc:fail(exc)
@app.get('/api/v1/public-services')
def hosted_services(force:bool=False):return public_services.snapshot(force=force)
@app.get('/api/v1/agents')
def agents():return store.list_records('agents')
@app.get('/api/v1/agents/{agent_id}')
def agent(agent_id:str):return required('agents',agent_id)
@app.delete('/api/v1/agents/{agent_id}',status_code=204)
def delete_agent(agent_id:str):
 if not store.delete('agents',agent_id):required('agents',agent_id)
@app.post('/api/v1/agents/{agent_id}/discover')
def discover(agent_id:str):
 try:return engine.discover(agent_id)
 except Exception as exc:fail(exc)
@app.get('/api/v1/agents/{agent_id}/graph')
def graph(agent_id:str):
 found=next((x for x in store.list_records('graphs') if x['agent_id']==agent_id),None)
 if not found:raise HTTPException(404,detail={'code':'NOT_DISCOVERED','message':'agent has not been discovered'})
 return found
@app.post('/api/v1/agents/{agent_id}/contracts/generate')
def generate_contract(agent_id:str):
 try:return engine.generate_contract(agent_id)
 except Exception as exc:fail(exc)
@app.get('/api/v1/agents/{agent_id}/contracts')
def contracts(agent_id:str):return [x for x in store.list_records('contracts') if x['agent_id']==agent_id]
@app.patch('/api/v1/contracts/{contract_id}/invariants/{invariant_id}')
def update_invariant(contract_id:str,invariant_id:str,body:InvariantUpdate):
 contract=required('contracts',contract_id);item=next((x for x in contract['invariants'] if x['id']==invariant_id),None)
 if not item:raise HTTPException(404,detail={'code':'NOT_FOUND','message':'invariant not found'})
 item.update(body.model_dump(exclude_none=True));return store.put('contracts',contract)
@app.post('/api/v1/campaigns',status_code=201)
async def create_campaign(body:CampaignCreate):
 try:
  target=required('agents',body.agent_id)
  return repository_targets.start_inspection(body.agent_id,body.model_dump(exclude={'agent_id'})) if not target.get('repository_url','').startswith('fixture://') else trueforge_runtime.start_campaign(body.model_dump())
 except Exception as exc:fail(exc)
@app.get('/api/v1/campaigns')
def campaigns():return store.list_records('campaigns')
@app.get('/api/v1/campaigns/{cid}')
def campaign(cid:str):return required('campaigns',cid)
@app.post('/api/v1/campaigns/{cid}/{action}')
def campaign_control(cid:str,action:str):
 if action not in {'pause','resume','cancel'}:raise HTTPException(404)
 current=required('campaigns',cid)
 if current.get('runtime')=='TRUEFORGE':
  if action!='cancel':raise HTTPException(409,detail={'code':'UNSUPPORTED_TRUEFORGE_ACTION','message':f'TrueForge does not expose a generic {action} session operation.'})
  try:
   result=TrueForgeClient.from_env().cancel_session(current['trueforge_session_id']);current['status']='CANCELLED';store.put('campaigns',current);return {'campaign':current,'trueforge':result}
  except Exception as exc:fail(exc)
 try:return engine.control_campaign(cid,action)
 except Exception as exc:fail(exc)
@app.get('/api/v1/campaigns/{cid}/events')
async def campaign_events(cid:str,request:Request,after:int=0):
 required('campaigns',cid)
 async def stream():
  cursor=after
  while not await request.is_disconnected():
   batch=store.events(cid,cursor)
   for event in batch:
    cursor=event['sequence'];yield f"id: {cursor}\nevent: {event['event_type']}\ndata: {json.dumps(event)}\n\n"
   current=store.get('campaigns',cid)
   if current and current['status'] in {'COMPLETED','CANCELLED','ERROR'} and not batch:break
   if not batch:yield ': heartbeat\n\n'
   await asyncio.sleep(.4)
 return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
@app.get('/api/v1/campaigns/{cid}/traces')
def campaign_traces(cid:str):required('campaigns',cid);return store.events(cid)
@app.get('/api/v1/campaigns/{cid}/h005-evidence')
def campaign_h005_evidence(cid:str):
 required('campaigns',cid)
 try:return trueforge_runtime.evaluate_h005(cid)
 except Exception as exc:fail(exc)
@app.get('/api/v1/campaigns/{cid}/verification-artifacts')
def campaign_verification_artifacts(cid:str):
 required('campaigns',cid);return [x for x in store.list_records('verification_artifacts') if x.get('campaign_id')==cid]
@app.post('/api/v1/campaigns/{cid}/verification-artifacts/sync')
def sync_verification_artifacts(cid:str):
 required('campaigns',cid)
 try:return {'artifacts':verification_artifacts.sync_from_persisted_events(cid),'campaign':required('campaigns',cid)}
 except Exception as exc:fail(exc)
@app.get('/api/v1/campaigns/{cid}/certification-status')
def certification_status(cid:str):
 c=required('campaigns',cid)
 if c.get('campaign_kind')=='GENERIC_REPOSITORY_INSPECTION':
  return {'campaign_id':cid,'stage':c.get('current_stage'),'next_gate':'repository_inspection' if c.get('status') not in {'COMPLETED','ERROR','CANCELLED'} else 'complete','generic':True,'gates':{},'qodo_blocks_replay':False}
 try:return verification_artifacts.certification_status(cid,refresh_qodo=False)
 except Exception as exc:fail(exc)
@app.post('/api/v1/campaigns/{cid}/qodo-refresh')
def refresh_qodo(cid:str):
 c=required('campaigns',cid)
 if c.get('campaign_kind')=='GENERIC_REPOSITORY_INSPECTION':raise HTTPException(409,detail={'code':'NOT_APPLICABLE','message':'Qodo certification gate is not part of a generic repository inspection.'})
 try:return verification_artifacts._qodo_gate(c,refresh=True)
 except Exception as exc:fail(exc)
@app.get('/api/v1/traces')
def traces(campaign_id:str|None=None):return store.events(campaign_id) if campaign_id else [e for c in store.list_records('campaigns') for e in store.events(c['id'])]
@app.get('/api/v1/findings')
def findings():return store.list_records('findings')
@app.get('/api/v1/approvals')
def approvals():return store.list_records('approvals')
@app.post('/api/v1/approvals/{approval_id}/{action}')
def approval_decision(approval_id:str,action:str,body:Decision):
 if action not in {'approve','reject'}:raise HTTPException(404)
 try:return trueforge_runtime.decide_approval(approval_id,action=='approve',body.approver,body.reason)
 except Exception as exc:fail(exc)
@app.get('/api/v1/safety-cases')
def safety_cases():return store.list_records('safety_cases')
@app.get('/api/v1/safety-cases/{case_id}')
def safety_case(case_id:str):return required('safety_cases',case_id)
@app.post('/api/v1/campaigns/{cid}/safety-case')
def create_safety_case(cid:str):
 try:return engine.create_safety_case(cid)
 except Exception as exc:fail(exc)
@app.get('/api/v1/integrations')
def integrations():
 tf=operator_control.trueforge_status();tf_status='CONNECTED' if tf.get('status')=='CONNECTED' else tf.get('status','ERROR');tf_detail=tf.get('detail','TrueForge status unavailable.')
 qodo_status=qodo.snapshot();hosted=public_services.snapshot()['services'];hosted_by_name={x['name']:x for x in hosted}
 return {'mode':engine.MODE,'pipeline':'TrueForge -> FaultLine MCP -> GitHub MCP -> Qodo Review -> Safety Case','integrations':[
   {'name':'TrueForge','status':tf_status,'detail':tf_detail,'proof':tf,'href':None},
   {'name':'Chaos MCP','status':'CONNECTED' if hosted_by_name.get('FaultLine MCP',{}).get('reachable') else 'UNAVAILABLE','detail':'Public FaultLine H-005 service is probed by the local control plane.','proof':hosted_by_name.get('FaultLine MCP',{}),'href':hosted_by_name.get('FaultLine MCP',{}).get('url')},
   {'name':'GitHub MCP','status':'MANAGED_NOT_PROBED','detail':'GitHub MCP is configured inside TrueForge. Harness OS treats this as configuration, not a live-health assertion; actual reads/writes must appear as TrueForge tool evidence.','proof':{'repository':'selected per target'},'href':'https://github.com/harshapriyag123/harness-os'},
   qodo_status,
   {'name':'Safety Case','status':'HARNESS OS','detail':'Normalized runtime evidence, approvals, Qodo review evidence, replay evidence and release verdicts are persisted by Harness OS.','proof':{'cases':len(store.list_records('safety_cases'))},'href':None},
  ],'public_services':hosted}
