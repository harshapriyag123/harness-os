import json
import unittest
from unittest.mock import patch

from app.integrations import qodo

class FakeResponse:
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,exc_type,exc,tb):return False
    def read(self):return json.dumps(self.payload).encode('utf-8')

class QodoIntegrationTest(unittest.TestCase):
    @patch('app.integrations.qodo.urlopen')
    def test_snapshot_reports_real_qodo_evidence(self,mocked_urlopen):
        mocked_urlopen.side_effect=[FakeResponse([{'user':{'login':'qodo-code-review[bot]'},'created_at':'2026-08-31T18:00:00Z','html_url':'https://github.com/example/repo/pull/7#issuecomment-1','body':'Code Review by Qodo: 3 bugs found.'}]),FakeResponse([])]
        result=qodo.snapshot('example/repo',7)
        self.assertEqual('Qodo Review',result['name'])
        self.assertEqual('EVIDENCE_FOUND',result['status'])
        self.assertEqual(1,result['proof']['qodo_events'])
        self.assertEqual(7,result['proof']['pr_number'])
        self.assertEqual('example/repo',result['proof']['repository'])
        self.assertIn('3 bugs found',result['detail'])

    @patch('app.integrations.qodo.urlopen')
    def test_snapshot_does_not_fake_missing_review(self,mocked_urlopen):
        mocked_urlopen.side_effect=[FakeResponse([]),FakeResponse([])]
        result=qodo.snapshot('example/repo',8)
        self.assertEqual('WAITING_FOR_REVIEW',result['status'])
        self.assertEqual(0,result['proof']['qodo_events'])
        self.assertIn('Replay remains locked',result['detail'])

    @patch('app.integrations.qodo.urlopen')
    def test_is_reviewed_is_bound_to_requested_pr(self,mocked_urlopen):
        mocked_urlopen.side_effect=[FakeResponse([]),FakeResponse([{'user':{'login':'qodo-code-review[bot]'},'submitted_at':'2026-08-31T18:10:00Z','html_url':'https://github.com/example/repo/pull/42#pullrequestreview-1','body':'Reviewed exact remediation PR.','state':'COMMENTED'}])]
        reviewed,evidence=qodo.is_reviewed('example/repo',42)
        self.assertTrue(reviewed)
        self.assertEqual(42,evidence['proof']['pr_number'])
        self.assertEqual('example/repo',evidence['proof']['repository'])

if __name__=='__main__':unittest.main()
