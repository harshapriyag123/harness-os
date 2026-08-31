import asyncio,json,os
from fastapi import FastAPI,HTTPException,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from . import engine,store,trueforge_runtime,verification_artifacts
from .integrations.trueforge import TrueForgeClient,TrueForgeError
from .models import AgentCreate,CampaignCreate,Decision,InvariantUpdate


def _cors_origins():
 configured=[x.strip().rstrip('/') for x in os.getenv('HARNESS_OS_CORS_ORIGINS','').split(',') if x.strip()]
 return list(dict.fromkeys(['http://localhost:5173',*configured]))


app=FastAPI(title='Harness OS API',version='1.2.0')
app.add_middleware(CORSMiddleware,allow_origins=_cors_origins(),allow_methods=['*'],allow_headers=['*'])

def required(kind,item_id):
 item=store.get(kind,item_id)
 if not item:raise HTTPException(404,detail={'code':'NOT_FOUND','message':f'{kind[:-1]} not found'})
 return item

def fail(exc):
 raise HTTPException(404 if isinstance(exc,KeyError) else 409 if isinstance(exc,ValueError) else 503,detail={'code':exc.__class__.__name__.upper(),'message':str(exc).strip("'")})

@app.get('/health')
def health():return {'status':'ok','mode':engine.MODE}

@app.get('/api/v1/dashboard')
def dashboard():return engine.dashboard()

@app.post('/api/v1/agents',status_code=201)
def create_agent(body:AgentCreate):
 try:return engine.create_agent(body.model_dump())
 except Exception as exc:fail(exc)

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
 try:return trueforge_runtime.start_campaign(body.model_dump())
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
 required('campaigns',cid)
 return [x for x in store.list_records('verification_artifacts') if x.get('campaign_id')==cid]

@app.post('/api/v1/campaigns/{cid}/verification-artifacts/sync')
def sync_verification_artifacts(cid:str):
 required('campaigns',cid)
 try:return {'artifacts':verification_artifacts.sync_from_persisted_events(cid),'campaign':required('campaigns',cid)}
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
 try:
  TrueForgeClient.from_env().capabilities();tf_status='CONNECTED';tf_detail='TrueForge HTTP API reachable; native sessions/events/approvals enabled'
 except TrueForgeError as exc:
  tf_status='ERROR';tf_detail=str(exc)
 return {'mode':engine.MODE,'integrations':[{'name':'TrueForge','status':tf_status,'detail':tf_detail},{'name':'GitHub MCP','status':'TRUEFORGE MANAGED','detail':'Configure GitHub MCP in the Harness OS TrueForge agent; repository writes must be approval-gated'},{'name':'Chaos MCP','status':'CONFIGURED','detail':'Fixture-only FaultLine endpoint from HARNESS_CHAOS_MCP_URL'},{'name':'Model Provider','status':'TRUEFORGE MANAGED','detail':'Configure OpenAI/model provider inside TrueForge'}]}
