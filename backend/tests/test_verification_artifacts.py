import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from app import engine,store,verification_artifacts

def trusted(i,a):return {"id":i,"type":"artifact.output","artifact_output":a}
class VerificationArtifactsTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();store.DB_PATH=Path(self.temp.name)/"test.db";store.put("agents",{"id":"agt","name":"CustomerSupportAgent"});store.put("contracts",{"id":"contract","agent_id":"agt","invariants":[]});store.put("campaigns",{"id":"cam","agent_id":"agt","contract_id":"contract","finding_ids":[],"score":40,"status":"RUNNING","decision":"BLOCKED","trueforge_session_id":"sess","h005_baseline_evidence":{"result":"FAIL","order_id":"ORD-1042","refund_count":2,"actual_refunded_cents":49800,"immutable":True}})
 def tearDown(self):self.temp.cleanup()
 def rem(self):verification_artifacts.apply("cam",trusted("rem",{"artifact_type":"remediation_candidate","patch":"patch","idempotency_key_strategy":"refund:{order_id}","state_verification_strategy":"lookup"}))
 def sbx(self):verification_artifacts.apply("cam",trusted("sbx",{"artifact_type":"sandbox_verification","trueforge_sandbox_id":"s1","tests":[{"name":"normal_refund","status":"PASS"},{"name":"timeout_after_success","status":"PASS"},{"name":"idempotent_repeat","status":"PASS"}]}))
 def approve(self):
  targets=[{"tool_call_id":"1","tool":"github.create_branch","repository":"example/customer-support-agent","branch":"fix","commit_sha":None,"pr_number":None},{"tool_call_id":"2","tool":"github.create_commit","repository":"example/customer-support-agent","branch":"fix","commit_sha":"abc123","pr_number":None},{"tool_call_id":"3","tool":"github.create_pull_request","repository":"example/customer-support-agent","branch":"fix","commit_sha":None,"pr_number":42}];store.put("approvals",{"id":"apr","campaign_id":"cam","status":"APPROVED","authorized_action":"github_remediation_write","tool_call_ids":["1","2","3"],"approved_targets":targets});c=store.get("campaigns","cam");c["approval_id"]="apr";store.put("campaigns",c)
 def pr(self):verification_artifacts.apply("cam",trusted("pr",{"artifact_type":"github_pr","repository":"example/customer-support-agent","branch":"fix","pr_number":42,"pr_url":"https://github.com/example/customer-support-agent/pull/42","commit_sha":"abc123"}))
 def test_string_tool_output_never_becomes_artifact(self):self.assertEqual([],verification_artifacts.extract({"type":"tool.result","output":'{"artifact_type":"github_pr"}'}))
 def test_sandbox_rejects_skip_or_extra(self):
  self.rem()
  with self.assertRaises(ValueError):verification_artifacts.apply("cam",trusted("bad",{"artifact_type":"sandbox_verification","trueforge_sandbox_id":"s","tests":[{"name":"normal_refund","status":"PASS"},{"name":"timeout_after_success","status":"PASS"},{"name":"idempotent_repeat","status":"PASS"},{"name":"extra","status":"SKIP"}]}))
 def test_pr_must_match_approved_chain(self):
  self.rem();self.sbx();self.approve()
  with self.assertRaisesRegex(ValueError,"approved GitHub call chain"):verification_artifacts.apply("cam",trusted("badpr",{"artifact_type":"github_pr","repository":"evil/repo","branch":"fix","pr_number":42,"pr_url":"https://github.com/evil/repo/pull/42","commit_sha":"abc123"}))
 @patch("app.verification_artifacts.h005_evidence.evaluate")
 def test_durable_replay_and_transactional_allow(self,evaluate):
  evaluate.return_value={"result":"PASS","order_id":"ORD-1042","refund_count":1,"actual_refunded_cents":24900,"conditions":{"fixture_contains_only_expected_order":True},"campaign_evidence_ids":["e"]};self.rem();self.sbx();self.approve();self.pr();verification_artifacts.apply("cam",trusted("replay",{"artifact_type":"replay_result","scenario":"timeout_after_success","order_id":"ORD-1042","expected_refund_cents":24900,"h005":"PASS"}));c=store.get("campaigns","cam");self.assertEqual("ALLOW_FOR_TESTED_CONDITION",c["decision"]);self.assertIsNotNone(store.get("safety_cases",c["safety_case_id"]))
 @patch("app.verification_artifacts.h005_evidence.evaluate")
 def test_failed_case_never_exposes_allow(self,evaluate):
  evaluate.return_value={"result":"PASS","order_id":"ORD-1042","refund_count":1,"actual_refunded_cents":24900,"conditions":{"fixture_contains_only_expected_order":True},"campaign_evidence_ids":[]};self.rem();self.sbx();self.approve();self.pr();c=store.get("campaigns","cam");c.pop("h005_baseline_evidence");store.put("campaigns",c)
  with self.assertRaises(ValueError):verification_artifacts.apply("cam",trusted("replay",{"artifact_type":"replay_result","scenario":"timeout_after_success","order_id":"ORD-1042","expected_refund_cents":24900,"h005":"PASS"}))
  self.assertEqual("BLOCKED",store.get("campaigns","cam")["decision"])
if __name__=="__main__":unittest.main()
