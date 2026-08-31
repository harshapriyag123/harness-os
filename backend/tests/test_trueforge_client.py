import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.integrations.trueforge import TrueForgeClient


class Handler(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, *args):
        pass

    def _send(self, data, status=200):
        raw = json.dumps({"data": data}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        Handler.requests.append(("GET", self.path, None))
        self._send({"id": "sess_real"} if self.path.endswith("/sessions/sess_real") else {"streaming": True})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        Handler.requests.append(("POST", self.path, body))
        self._send(
            {"id": "turn_real", "state": {"status": "running"}}
            if self.path.endswith("/turns")
            else {"id": "sess_real"},
            201,
        )


class TrueForgeClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.client = TrueForgeClient(f"http://127.0.0.1:{cls.server.server_port}")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Handler.requests.clear()

    def test_official_session_and_turn_shapes(self):
        session = self.client.create_session("harness-os")
        turn = self.client.submit_task(session["id"], "verify H-005", stream=False)
        self.assertEqual("turn_real", turn["id"])
        self.assertEqual(
            ("POST", "/api/v1/sessions", {"agent": {"name": "harness-os"}}),
            Handler.requests[0],
        )
        self.assertEqual("/api/v1/sessions/sess_real/turns", Handler.requests[1][1])
        self.assertEqual(
            [{"content": "verify H-005", "type": "user.message"}],
            Handler.requests[1][2]["input"],
        )
        self.assertEqual("auto", Handler.requests[1][2]["previous_turn_id"])
        self.assertFalse(Handler.requests[1][2]["stream"])

    def test_native_tool_approval_allow_shape(self):
        self.client.resume_with_approval(
            "sess_real",
            approved=True,
            thread_id="main",
            tool_call_ids=["call_1", "call_2"],
            reason="sandbox evidence reviewed",
        )
        payload = Handler.requests[-1][2]
        self.assertEqual(
            [
                {
                    "type": "user.tool_approval",
                    "thread_id": "main",
                    "tool_call_id": "call_1",
                    "approval": {"status": "allow"},
                },
                {
                    "type": "user.tool_approval",
                    "thread_id": "main",
                    "tool_call_id": "call_2",
                    "approval": {"status": "allow"},
                },
            ],
            payload["input"],
        )

    def test_native_tool_approval_deny_shape(self):
        self.client.resume_with_approval(
            "sess_real",
            approved=False,
            thread_id="main",
            tool_call_ids=["call_1"],
            reason="do not write repository",
        )
        self.assertEqual(
            {
                "type": "user.tool_approval",
                "thread_id": "main",
                "tool_call_id": "call_1",
                "approval": {"status": "deny", "reason": "do not write repository"},
            },
            Handler.requests[-1][2]["input"][0],
        )
