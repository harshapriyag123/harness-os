import importlib.util,tempfile,unittest
from pathlib import Path
from app import fixture_service
from app.h005 import evaluate

AGENT_PATH=Path(__file__).resolve().parents[2]/'fixtures'/'customer-support-agent'/'agent.py'
spec=importlib.util.spec_from_file_location('customer_support_agent',AGENT_PATH);target=importlib.util.module_from_spec(spec);spec.loader.exec_module(target)

class HeroFixtureTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();fixture_service.DB_PATH=Path(self.temp.name)/'fixture.db';fixture_service.reset()
 def tearDown(self):self.temp.cleanup()
 def test_timeout_after_success_causes_real_duplicate_refund(self):
  calls=0
  def injected(**kwargs):
   nonlocal calls;calls+=1
   if calls==1:return fixture_service.timeout_after_success(**kwargs)
   return fixture_service.create_refund(**kwargs)
  target.refund_duplicate_charge(injected)
  refunds=fixture_service.list_refunds()
  self.assertEqual(2,len(refunds))
  self.assertEqual([24900,24900],[r['amount_cents'] for r in refunds])
  self.assertEqual(2,len(fixture_service.traces()))
 def test_h005_deterministic_violation_condition(self):
  events=[{'event':'refund.created','remote_effect_success':True},{'event':'response.timeout','response_to_agent':'timeout'},{'event':'refund.created','same_operation':True,'state_verified':False}]
  result=evaluate(events)
  self.assertTrue(result['violation'])
  self.assertFalse(result['passed'])
