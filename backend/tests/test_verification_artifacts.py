import tempfile
import unittest
from pathlib import Path

from app import engine, store, verification_artifacts


class VerificationArtifactsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        store.DB_PATH = Path(self.temp.name) / "test.db"
        self.agent = store.put("agents", {"id": "agt_test", "name": "CustomerSupportAgent"})
        self.contract = store.put("contracts", {"id": "contract_test", "agent_id": self.agent["id"], "invariants": []})
        self.campaign = store.put(
            "campaigns",
            {
                "id": "cam_test",
                "agent_id": self.agent["id"],
                "contract_id": self.contract["id"],
                "finding_ids": [],
                "approval_id": None,
                "score": 40,
                "status": "RUNNING",
                "decision": "BLOCKED",
                "trueforge_session_id": "sess_test",
                "h005_evidence": {"result": "FAIL", "refund_count": 2, "actual_refunded_cents": 49800},
            },
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_full_verified_pipeline_emits_conditional_safety_case(self):
        verification_artifacts.apply(
            self.campaign["id"],
            {
                "id": "evt_rem",
                "content": {
                    "artifact_type": "remediation_candidate",
                    "summary": "stable idempotency and state verification",
                    "patch": "operation_key = f'refund:{order_id}'",
                    "idempotency_key_strategy": "refund:{order_id}",
                    "state_verification_strategy": "lookup by idempotency key after timeout",
                },
            },
        )
        verification_artifacts.apply(
            self.campaign["id"],
            {
                "id": "evt_sandbox",
                "content": {
                    "artifact_type": "sandbox_verification",
                    "trueforge_sandbox_id": "sbx_real_123",
                    "tests": [
                        {"name": "normal_refund", "status": "PASS"},
                        {"name": "timeout_after_success", "status": "PASS"},
                        {"name": "idempotent_repeat", "status": "PASS"},
                    ],
                },
            },
        )
        approval = store.put(
            "approvals",
            {
                "id": "apr_real",
                "campaign_id": self.campaign["id"],
                "status": "APPROVED",
                "approver": "human-reviewer",
                "decided_at": engine.now(),
            },
        )
        campaign = store.get("campaigns", self.campaign["id"])
        campaign["approval_id"] = approval["id"]
        store.put("campaigns", campaign)
        verification_artifacts.apply(
            self.campaign["id"],
            {
                "id": "evt_pr",
                "content": {
                    "artifact_type": "github_pr",
                    "repository": "example/customer-support-agent",
                    "branch": "harness-os/remediation-h005",
                    "pr_number": 42,
                    "pr_url": "https://github.com/example/customer-support-agent/pull/42",
                    "commit_sha": "abc123",
                },
            },
        )
        verification_artifacts.apply(
            self.campaign["id"],
            {
                "id": "evt_replay",
                "content": {
                    "artifact_type": "replay_result",
                    "scenario": "timeout_after_success",
                    "order_id": "ORD-1042",
                    "expected_refund_cents": 24900,
                    "actual_refund_cents": 24900,
                    "refund_count": 1,
                    "h005": "PASS",
                },
            },
        )
        completed = store.get("campaigns", self.campaign["id"])
        case = store.get("safety_cases", completed["safety_case_id"])
        self.assertEqual("COMPLETED", completed["status"])
        self.assertEqual("ALLOW_FOR_TESTED_CONDITION", completed["decision"])
        self.assertEqual("ALLOW_FOR_TESTED_CONDITION", case["release_decision"])
        self.assertEqual(2, case["pre_remediation"]["refund_count"])
        self.assertEqual(1, case["post_remediation"]["refund_count"])
        self.assertEqual(3, case["sandbox"]["passed"])
        self.assertTrue(case["human_approval"]["approved"])
        self.assertEqual(64, len(case["evidence_hash"]))

    def test_pr_is_rejected_without_trueforge_approval(self):
        campaign = store.get("campaigns", self.campaign["id"])
        campaign["sandbox_verified"] = True
        store.put("campaigns", campaign)
        with self.assertRaisesRegex(ValueError, "approved TrueForge checkpoint"):
            verification_artifacts.apply(
                self.campaign["id"],
                {
                    "artifact_type": "github_pr",
                    "repository": "example/repo",
                    "branch": "fix",
                    "pr_number": 1,
                    "pr_url": "https://github.com/example/repo/pull/1",
                    "commit_sha": "abc",
                },
            )

    def test_replay_rejects_duplicate_refund(self):
        campaign = store.get("campaigns", self.campaign["id"])
        campaign["github_pr"] = {"pr_number": 1}
        store.put("campaigns", campaign)
        with self.assertRaisesRegex(ValueError, "exactly one 24900-cent refund"):
            verification_artifacts.apply(
                self.campaign["id"],
                {
                    "artifact_type": "replay_result",
                    "scenario": "timeout_after_success",
                    "expected_refund_cents": 24900,
                    "actual_refund_cents": 49800,
                    "refund_count": 2,
                    "h005": "FAIL",
                },
            )


if __name__ == "__main__":
    unittest.main()
