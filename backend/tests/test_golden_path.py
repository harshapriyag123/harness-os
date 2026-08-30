import tempfile
import unittest
from pathlib import Path

from app import engine, store

class GoldenPathTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        store.DB_PATH = Path(self.temp.name) / "test.db"
        engine.CONTROLS.clear(); engine.TASKS.clear()

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def test_discover_attack_prove_fix_approve_certify(self):
        agent = engine.create_agent({"repository_url":"fixture://customer-support-agent","branch":"main","name":"CustomerSupportAgent","harness_type":"TrueForge","config_path":None,"instruction_path":None,"mcp_config_path":None,"policy_path":None})
        graph = engine.discover(agent["id"])
        self.assertIn("refund.create", [node["id"] for node in graph["nodes"]])
        contract = engine.generate_contract(agent["id"])
        self.assertIn("H-005", [item["id"] for item in contract["invariants"]])
        campaign = engine.create_campaign({"agent_id":agent["id"],"maximum_scenarios":1,"maximum_runtime":300,"parallelism":1,"fault_injection":True,"stop_on_critical":True,"categories":["RELIABILITY"]})
        await engine.run_campaign(campaign["id"])
        failed = store.get("campaigns", campaign["id"])
        self.assertEqual("WAITING_APPROVAL", failed["status"])
        finding = store.get("findings", failed["finding_ids"][0])
        self.assertEqual((3,3), (finding["reproduction_count"], finding["successful_reproductions"]))
        engine.decide(failed["approval_id"], True, "test-operator", "evidence reviewed")
        await engine.TASKS[campaign["id"]]
        completed = store.get("campaigns", campaign["id"])
        case = store.get("safety_cases", completed["safety_case_id"])
        self.assertEqual("CERTIFIED", completed["decision"])
        self.assertEqual("CERTIFIED", case["release_decision"])
        self.assertEqual(64, len(case["evidence_hash"]))
        self.assertTrue(any(event["event_type"] == "fault.injected" for event in store.events(campaign["id"])))

if __name__ == "__main__": unittest.main()
