import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from app import store,verification_artifacts

def trusted(i,a):return {"id":i,"type":"artifact.output","artifact_output":a}
class VerificationArtifactsTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();store.DB_PATH=Path(self.temp.name)/"test.db";store.put("agents",{"id":"agt","name":"CustomerSupportAgent"});store.put("contracts",{"id":"contract","agent_id":"agt","invariants":[]});store.put("campaigns",{"id":"cam","agent_id":"agt","contract_id":"contract","finding_ids":[],"score":40,"status":"RUNNING","decision":"BLOCKED","trueforge_session_id":"sess","h005_baseline_evidence":{"result":"FAIL","order_id":"ORD-1042","refund_count":2,"actual_refunded_cents":49800,"immutable":True}})
 def tearDown(self):self.temp.cleanup()
 def rem(self):verification_artifacts.apply("cam",trusted("rem",{"artifact_type":"remediation_candidate","patch":"patch","idempotency_key_strategy":"refund:{order_id}","state_verification_strategy":"lookup"}))
 def sbx(self):verification_artifacts.apply("cam",trusted("sbx",{"artifact_type":"sandbox_verification","trueforge_sandbox_id":"s1","tests":[{"name":"normal_refund","status":"PASS"},{"name":"timeout_after_success","status":"PASS"},{"name":"idempotent_repeat","status":"PASS"}]}))
 def approve(self):
  targets=[{"tool_call_id":"1","tool":"github.create_branch","repository":"example/customer-support-agent","branch":"fix"},{"tool_call_id":"2","tool":"github.create_commit","repository":"example/customer-support-agent","branch":"fix"},{"tool_call_id":"3","tool":"github.create_pull_request","repository":"example/customer-support-agent","branch":"fix"}];store.put("approvals",{"id":"apr","campaign_id":"cam","status":"APPROVED","authorized_action":"github_remediation_write","tool_call_ids":["1","2","3"],"approved_targets":targets});
  for r in [{"id":"r1","approval_id":"apr","campaign_id":"cam","tool_call_id":"1","tool":"github.create_branch","repository":"example/customer-support-agent","branch":"fix"},{"id":"r2","approval_id":"apr","campaign_id":"cam","tool_call_id":"2","tool":"github.create_commit","repository":"example/customer-support-agent","branch":"fix","commit_sha":"abc123"},{"id":"r3","approval_id":"apr","campaign_id":"cam","tool_call_id":"3","tool":"github.create_pull_request","repository":"example/customer-support-agent","branch":"fix","pr_number":42,"pr_url":"https://github.com/example/customer-support-agent/pull/42"}]:store.put("github_tool_results",r)
  c=store.get("campaigns","cam");c["approval_id"]="apr";store.put("campaigns",c)
 def pr(self):verification_artifacts.apply("cam",trusted("pr",{"artifact_type":"github_pr","repository":"example/customer-support-agent","branch":"fix","pr_number":42,"pr_url":"https://github.com/example/customer-support-agent/pull/42","commit_sha":"abc123"}))
 def durable(self):return {"result":"PASS","order_id":"ORD-1042","refund_count":1,"actual_refunded_cents":24900,"conditions":{"fixture_contains_only_expected_order":True,"state_verification_between_attempts":True,"state_verification_key":"refund:ORD-1042"},"campaign_evidence_ids":["e"]}
 def test_string_tool_output_never_becomes_artifact(self):self.assertEqual([],verification_artifacts.extract({"type":"tool.result","output":'{"artifact_type":"github_pr"}'}))
 def test_pr_must_match_actual_results(self):
  self.rem();self.sbx();self.approve()
  with self.assertRaisesRegex(ValueError,"structured outputs"):verification_artifacts.apply("cam",trusted("bad",{"artifact_type":"github_pr","repository":"example/customer-support-agent","branch":"fix","pr_number":99,"pr_url":"https://github.com/example/customer-support-agent/pull/99","commit_sha":"abc123"}))
 @patch("app.verification_artifacts.h005_evidence.evaluate")
 def test_replay_is_in_case_hash_and_idempotent(self,evaluate):
  evaluate.return_value=self.durable();self.rem();self.sbx();self.approve();self.pr();evt=trusted("replay",{"artifact_type":"replay_result","scenario":"timeout_after_success","order_id":"ORD-1042","expected_refund_cents":24900,"h005":"PASS"});verification_artifacts.apply("cam",evt);c1=store.get("campaigns","cam");case1=store.get("safety_cases",c1["safety_case_id"]);self.assertEqual("ALLOW_FOR_TESTED_CONDITION",c1["decision"]);self.assertEqual(case1["replay_artifact_id"],case1["evidence_bundle"]["replay_artifact"]["id"]);self.assertIn("refund:ORD-1042",case1["post_remediation"]["state_verification_key"]);verification_artifacts.apply("cam",evt);c2=store.get("campaigns","cam");self.assertEqual(c1["safety_case_id"],c2["safety_case_id"]);self.assertEqual(1,len([x for x in store.list_records("safety_cases") if x.get("campaign_id")=="cam"]))
 @patch("app.verification_artifacts.h005_evidence.evaluate")
 def test_missing_baseline_never_allows(self,evaluate):
  evaluate.return_value=self.durable();self.rem();self.sbx();self.approve();self.pr();c=store.get("campaigns","cam");c.pop("h005_baseline_evidence");store.put("campaigns",c)
  with self.assertRaises(ValueError):verification_artifacts.apply("cam",trusted("replay",{"artifact_type":"replay_result","scenario":"timeout_after_success","order_id":"ORD-1042","expected_refund_cents":24900,"h005":"PASS"}))
  self.assertEqual("BLOCKED",store.get("campaigns","cam")["decision"])
if __name__=="__main__":unittest.main()
