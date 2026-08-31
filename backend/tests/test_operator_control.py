import unittest
from unittest.mock import patch

from app import operator_control
from app.integrations.trueforge import TrueForgeError


class FakeClient:
    def __init__(self,base_url='https://trueforge.example',token='secret',timeout=60):
        self.base_url=base_url;self.token=token;self.timeout=timeout

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
        waiting={'id':'c-wait','agent_id':'a1','status':'WAITING_APPROVAL','current_stage':'HUMAN_CHECKPOINT','campaign_kind':'GENERIC_REPOSITORY_INSPECTION'}
        completed={'id':'c-done','agent_id':'a1','status':'COMPLETED','current_stage':'DONE','campaign_kind':'GENERIC_REPOSITORY_INSPECTION'}
        approval={'id':'apr1','campaign_id':'c-wait','status':'PENDING'}
        def records(kind):
            if kind=='campaigns':return [completed,waiting]
            if kind=='approvals':return [approval]
            return []
        list_records.side_effect=records
        get_record.return_value={'id':'a1','name':'repo'}
        result=operator_control.snapshot()
        self.assertEqual('c-wait',result['campaign']['id'])
        self.assertEqual('apr1',result['approval']['id'])
        self.assertEqual('WAITING_APPROVAL_PRIORITY',result['selection_reason'])

    @patch('app.operator_control.TrueForgeClient', FakeClient)
    def test_trueforge_timeout_is_actionable(self):
        result=operator_control.trueforge_status()
        self.assertEqual('TIMEOUT',result['status'])
        self.assertTrue(result['retryable'])
        self.assertIn('TRUEFORGE_BASE_URL',result['diagnosis'])
        self.assertNotIn('secret',str(result))


if __name__=='__main__':
    unittest.main()
