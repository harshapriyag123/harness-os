import unittest
from unittest.mock import patch
from app import repository_targets,store

class RepositoryTargetsTest(unittest.TestCase):
    def test_normalize_github_url(self):
        url,owner,repo=repository_targets.normalize_github_url('https://github.com/example/agent-repo/')
        self.assertEqual('https://github.com/example/agent-repo',url)
        self.assertEqual('example',owner)
        self.assertEqual('agent-repo',repo)

    def test_rejects_non_github_url(self):
        with self.assertRaises(ValueError):repository_targets.normalize_github_url('https://example.com/not-github')

    @patch('app.repository_targets.engine.generate_contract')
    @patch('app.repository_targets.store.put')
    @patch('app.repository_targets.engine.create_agent')
    def test_generic_target_becomes_ready_without_fake_repo_scan(self,create_agent,put,generate_contract):
        create_agent.return_value={'id':'agt_1','repository_url':'https://github.com/example/agent-repo','branch':'main','name':'agent-repo','status':'CONNECTED','risk':'UNKNOWN'}
        put.side_effect=lambda kind,record:record
        result=repository_targets.connect_target({'repository_url':'https://github.com/example/agent-repo','branch':'main','name':'agent-repo','harness_type':'TrueForge'})
        self.assertEqual('READY',result['status'])
        self.assertEqual('UNKNOWN',result['risk'])
        graph=[call.args[1] for call in put.call_args_list if call.args[0]=='graphs'][0]
        self.assertEqual('Repository Target',graph['nodes'][0]['type'])
        self.assertEqual('UNKNOWN',graph['nodes'][0]['risk'])
        generate_contract.assert_called_once_with('agt_1')

if __name__=='__main__':unittest.main()
