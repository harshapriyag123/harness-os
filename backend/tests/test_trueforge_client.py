import json,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from app.integrations.trueforge import TrueForgeClient

class Handler(BaseHTTPRequestHandler):
 requests=[]
 def log_message(self,*args):pass
 def _send(self,data,status=200):raw=json.dumps({'data':data}).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  Handler.requests.append(('GET',self.path,None));self._send({'id':'sess_real'} if self.path.endswith('/sessions/sess_real') else {'streaming':True})
 def do_POST(self):
  length=int(self.headers.get('Content-Length','0'));body=json.loads(self.rfile.read(length) or b'{}');Handler.requests.append(('POST',self.path,body));self._send({'id':'turn_real','state':{'status':'running'}} if self.path.endswith('/turns') else {'id':'sess_real'},201)

class TrueForgeClientTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.client=TrueForgeClient(f'http://127.0.0.1:{cls.server.server_port}')
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
 def setUp(self):Handler.requests.clear()
 def test_official_session_and_turn_shapes(self):
  session=self.client.create_session('harness-os');turn=self.client.submit_task(session['id'],'verify H-005',False)
  self.assertEqual('turn_real',turn['id']);self.assertEqual(('POST','/api/v1/sessions',{'agent':{'name':'harness-os'}}),Handler.requests[0]);self.assertEqual('/api/v1/sessions/sess_real/turns',Handler.requests[1][1]);self.assertEqual([{'content':'verify H-005','type':'user.message'}],Handler.requests[1][2]['input']);self.assertEqual('auto',Handler.requests[1][2]['previous_turn_id']);self.assertFalse(Handler.requests[1][2]['stream'])
