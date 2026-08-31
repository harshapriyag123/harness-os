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
    def test_snapshot_reports_official_qodo_evidence(self,mocked_urlopen):
        mocked_urlopen.side_effect=[FakeResponse([{'user':{'login':'qodo-code-review[bot]'},'created_at':'2026-08-31T18:00:00Z','html_url':'https://github.com/example/repo/pull/7#issuecomment-1','body':'Code Review by Qodo: 3 bugs found.'}]),FakeResponse([])]
        result=qodo.snapshot('example/repo',7)
        self.assertEqual('EVIDENCE_FOUND',result['status'])
        self.assertEqual(1,result['proof']['qodo_events'])
        self.assertEqual('qodo-code-review[bot]',result['proof']['latest_author'])

    @patch('app.integrations.qodo.urlopen')
    def test_impostor_login_does_not_unlock_qodo(self,mocked_urlopen):
        mocked_urlopen.side_effect=[FakeResponse([{'user':{'login':'qodo-security-fan'},'created_at':'2026-08-31T18:00:00Z','body':'looks good'}]),FakeResponse([])]
        result=qodo.snapshot('example/repo',7)
        self.assertEqual('WAITING_FOR_REVIEW',result['status'])
        self.assertEqual(0,result['proof']['qodo_events'])

    @patch('app.integrations.qodo.urlopen')
    def test_commit_bound_review_must_match_exact_sha(self,mocked_urlopen):
        review={'user':{'login':'qodo-code-review[bot]'},'submitted_at':'2026-08-31T18:10:00Z','html_url':'https://github.com/example/repo/pull/42#pullrequestreview-1','body':'Reviewed remediation.','state':'COMMENTED','commit_id':'abc123'}
        mocked_urlopen.side_effect=[FakeResponse([]),FakeResponse([review])]
        reviewed,evidence=qodo.is_reviewed('example/repo',42,'abc123')
        self.assertTrue(reviewed)
        self.assertEqual('abc123',evidence['proof']['reviewed_commit_sha'])

    @patch('app.integrations.qodo.urlopen')
    def test_stale_commit_review_does_not_unlock_replay(self,mocked_urlopen):
        review={'user':{'login':'qodo-code-review[bot]'},'submitted_at':'2026-08-31T18:10:00Z','state':'COMMENTED','commit_id':'oldsha'}
        mocked_urlopen.side_effect=[FakeResponse([]),FakeResponse([review])]
        reviewed,evidence=qodo.is_reviewed('example/repo',42,'newsha')
        self.assertFalse(reviewed)
        self.assertEqual('WAITING_FOR_REVIEW',evidence['status'])
        self.assertEqual('newsha',evidence['proof']['expected_commit_sha'])

    @patch('app.integrations.qodo.urlopen')
    def test_blank_explicit_repository_fails_closed(self,mocked_urlopen):
        result=qodo.snapshot('',42,'abc',require_commit=True)
        self.assertEqual('UNAVAILABLE',result['status'])
        mocked_urlopen.assert_not_called()

    @patch('app.integrations.qodo.urlopen')
    def test_snapshot_does_not_fake_missing_review(self,mocked_urlopen):
        mocked_urlopen.side_effect=[FakeResponse([]),FakeResponse([])]
        result=qodo.snapshot('example/repo',8)
        self.assertEqual('WAITING_FOR_REVIEW',result['status'])
        self.assertEqual(0,result['proof']['qodo_events'])

if __name__=='__main__':unittest.main()
