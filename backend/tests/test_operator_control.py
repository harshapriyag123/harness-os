import unittest
from unittest.mock import patch

from app import operator_control
from app.integrations.trueforge import TrueForgeError


class FakeClient:
    def __init__(self, base_url='https://trueforge.example', token='secret', timeout=60):
        self.base_url = base_url
        self.token = token
        self.timeout = timeout

    @classmethod
    def from_env(cls):
        return cls()

    def capabilities(self):
        raise TrueForgeError('Invalid/timeout response from TrueForge: timed out')


class OperatorControlTest(unittest.TestCase):
    @patch('app.operator_control.store.events', return_value=[])
    @patch('app.operator_control.store.get')
    @patch('app.operator_control.store.list_records')
    def test_snapshot_prioritizes_waiting_approval(self, list_records, get_record, _events):
        waiting = {'id': 'c-wait', 'agent_id': 'a1', 'status': 'WAITING_APPROVAL', 'current_stage': 'HUMAN_CHECKPOINT', 'campaign_kind': 'GENERIC_REPOSITORY_INSPECTION'}
        completed = {'id': 'c-done', 'agent_id': 'a1', 'status': 'COMPLETED', 'current_stage': 'DONE', 'campaign_kind': 'GENERIC_REPOSITORY_INSPECTION'}
        approval = {'id': 'apr1', 'campaign_id': 'c-wait', 'status': 'PENDING'}

        def records(kind):
            if kind == 'campaigns':
                return [completed, waiting]
            if kind == 'approvals':
                return [approval]
            return []

        list_records.side_effect = records
        get_record.return_value = {'id': 'a1', 'name': 'repo'}
        result = operator_control.snapshot()
        self.assertEqual('c-wait', result['campaign']['id'])
        self.assertEqual('apr1', result['approval']['id'])
        self.assertEqual('WAITING_APPROVAL_PRIORITY', result['selection_reason'])

    @patch('app.operator_control.store.get')
    @patch('app.operator_control.store.list_records')
    def test_explicit_target_does_not_fall_back_to_other_campaign(self, list_records, get_record):
        list_records.side_effect = lambda kind: [{'id': 'other-campaign', 'agent_id': 'a2', 'status': 'WAITING_APPROVAL'}] if kind == 'campaigns' else []
        get_record.return_value = {'id': 'a1', 'name': 'selected'}
        result = operator_control.snapshot(agent_id='a1')
        self.assertIsNone(result['campaign'])
        self.assertEqual('a1', result['target']['id'])
        self.assertEqual('NO_CAMPAIGN_FOR_TARGET', result['selection_reason'])

    @patch('app.operator_control.TrueForgeClient', FakeClient)
    def test_trueforge_timeout_is_actionable(self):
        result = operator_control.trueforge_status()
        self.assertEqual('TIMEOUT', result['status'])
        self.assertTrue(result['retryable'])
        self.assertIn('TRUEFORGE_API_BASE_URL', result['diagnosis'])
        self.assertNotIn('secret', str(result))

    @patch.dict('os.environ', {'TRUEFORGE_PROBE_TIMEOUT_SECONDS': 'not-a-number'})
    @patch('app.operator_control.TrueForgeClient', FakeClient)
    def test_invalid_probe_timeout_falls_back_instead_of_crashing(self):
        result = operator_control.trueforge_status()
        self.assertEqual(4.0, result['probe_timeout_seconds'])
        self.assertIn('Invalid TRUEFORGE_PROBE_TIMEOUT_SECONDS', result['configuration_warning'])

    @patch.dict('os.environ', {'HARNESS_OS_MODE': 'live', 'TRUEFORGE_BASE_URL': '', 'TRUEFORGE_API_BASE_URL': ''}, clear=False)
    def test_live_mode_without_hosted_api_is_not_configured(self):
        result = operator_control.trueforge_status()
        self.assertEqual('NOT_CONFIGURED', result['status'])
        self.assertTrue(result['configuration_required'])
        self.assertIn('public TrueForge API', result['diagnosis'])

    @patch.dict('os.environ', {'HARNESS_OS_MODE': 'live', 'TRUEFORGE_BASE_URL': 'http://127.0.0.1:8791', 'TRUEFORGE_API_BASE_URL': ''}, clear=False)
    def test_live_mode_rejects_localhost_trueforge(self):
        result = operator_control.trueforge_status()
        self.assertEqual('NOT_CONFIGURED', result['status'])
        self.assertIn('localhost', result['detail'].lower())
        self.assertNotIn('WinError', result['detail'])


if __name__ == '__main__':
    unittest.main()
