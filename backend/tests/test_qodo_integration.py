import json
import unittest
from unittest.mock import patch

from app.integrations import qodo


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode('utf-8')


class QodoIntegrationTest(unittest.TestCase):
    @patch('app.integrations.qodo.urlopen')
    def test_snapshot_reports_real_qodo_evidence(self, mocked_urlopen):
        mocked_urlopen.side_effect = [
            FakeResponse([
                {
                    'user': {'login': 'qodo-code-review[bot]'},
                    'created_at': '2026-08-31T18:00:00Z',
                    'html_url': 'https://github.com/example/repo/pull/7#issuecomment-1',
                    'body': 'Code Review by Qodo: 3 bugs found.',
                }
            ]),
            FakeResponse([]),
        ]

        with patch.dict('os.environ', {'QODO_REPOSITORY': 'example/repo', 'QODO_PR_NUMBER': '7'}, clear=False):
            result = qodo.snapshot()

        self.assertEqual('Qodo Review', result['name'])
        self.assertEqual('EVIDENCE FOUND', result['status'])
        self.assertEqual(1, result['proof']['qodo_events'])
        self.assertEqual(7, result['proof']['pr_number'])
        self.assertIn('3 bugs found', result['detail'])

    @patch('app.integrations.qodo.urlopen')
    def test_snapshot_does_not_fake_missing_review(self, mocked_urlopen):
        mocked_urlopen.side_effect = [FakeResponse([]), FakeResponse([])]

        with patch.dict('os.environ', {'QODO_REPOSITORY': 'example/repo', 'QODO_PR_NUMBER': '8'}, clear=False):
            result = qodo.snapshot()

        self.assertEqual('NO REVIEW FOUND', result['status'])
        self.assertEqual(0, result['proof']['qodo_events'])


if __name__ == '__main__':
    unittest.main()
