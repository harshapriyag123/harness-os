from __future__ import annotations
import importlib.util,json,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from app import fixture_service
from app.h005 import evaluate
agent_path=ROOT/'fixtures'/'customer-support-agent'/'agent.py';spec=importlib.util.spec_from_file_location('customer_support_agent',agent_path);agent=importlib.util.module_from_spec(spec);spec.loader.exec_module(agent)
with tempfile.TemporaryDirectory() as directory:
 fixture_service.DB_PATH=Path(directory)/'fixture.db';fixture_service.reset();calls=0;events=[]
 def injected(**kwargs):
  global calls
  calls+=1
  if calls==1:
   try:fixture_service.timeout_after_success(**kwargs)
   except TimeoutError:
    events.extend([{'event':'refund.created','remote_effect_success':True},{'event':'response.timeout','response_to_agent':'timeout'}]);raise
  result=fixture_service.create_refund(**kwargs);events.append({'event':'refund.created','same_operation':True,'state_verified':False});return result
 agent.refund_duplicate_charge(injected);refunds=fixture_service.list_refunds();proof={'refund_attempts':calls,'refund_count':len(refunds),'amounts_cents':[r['amount_cents'] for r in refunds],'h005':evaluate(events),'trace':fixture_service.traces()};print(json.dumps(proof,indent=2));raise SystemExit(0 if len(refunds)==2 and proof['h005']['violation'] else 1)
