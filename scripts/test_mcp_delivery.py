"""Launch the actual stdio bridge against a loopback stub, never a native editor."""
import importlib.util
import json
import socketserver
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "integrations/mcp/editor-mcp.py"
READ_METHODS = {"document.validate", "preview.snapshot", "project.export.read"}
OUTPUT_METHODS = {"preview.render", "job.cancel", "project.export.settings", "project.export.capture", "project.export.configure", "project.export.write"}


class DeliveryTests(unittest.TestCase):
    def test_new_operations_have_separate_read_and_output_routes(self):
        spec = importlib.util.spec_from_file_location("delivery_bridge", BRIDGE)
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        tools = bridge.tools()
        self.assertTrue(READ_METHODS <= set(tools[0]["inputSchema"]["properties"]["method"]["enum"]))
        self.assertEqual(OUTPUT_METHODS, set(tools[3]["inputSchema"]["properties"]["method"]["enum"]))
        self.assertTrue(OUTPUT_METHODS.isdisjoint(tools[1]["inputSchema"]["properties"]["method"]["enum"]))

    def test_stdio_lifecycle_and_capability_read_in_a_standalone_process(self):
        received = []
        fake_token = "d" * 64
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                envelope = json.loads(self.rfile.readline(1024 * 1024))
                request = envelope["request"]
                received.append((request["method"], envelope["token"] == fake_token))
                response = {"apiVersion": "editor-api/0.1", "id": request["id"], "result": {"sessionId": "delivery-test-session", "methods": ["editor.capabilities"], "release": {"version": "1.0.0-beta"}}}
                self.wfile.write(json.dumps(response).encode() + b"\n")
        base = Path(tempfile.gettempdir()).resolve()
        with tempfile.TemporaryDirectory(prefix="yuntu-mcp-delivery-", dir=base) as temporary:
            directory = Path(temporary).resolve()
            self.assertEqual(directory.parent, base)
            with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    info = directory / "synthetic-info.json"
                    info.write_text(json.dumps({"apiVersion": "editor-api/0.1", "address": "127.0.0.1:" + str(server.server_address[1]), "token": fake_token, "instanceId": "delivery-test-instance", "exportRoot": str(directory)}), encoding="utf8")
                    requests = [
                        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "delivery-test", "version": "1"}}},
                        {"jsonrpc": "2.0", "method": "notifications/initialized"},
                        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "editor_read", "arguments": {"method": "editor.capabilities"}}},
                    ]
                    run = subprocess.run([sys.executable, "-B", str(BRIDGE), "--info", str(info)], input="".join(json.dumps(item) + "\n" for item in requests), encoding="utf8", capture_output=True, timeout=10)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stderr, "")
                    responses = [json.loads(line) for line in run.stdout.splitlines()]
                    self.assertEqual([item["id"] for item in responses], [1, 2, 3])
                    self.assertEqual([tool["name"] for tool in responses[1]["result"]["tools"]], ["editor_read", "editor_execute", "editor_prompts", "editor_output"])
                    self.assertFalse(responses[2]["result"]["isError"])
                    self.assertEqual(received, [("editor.capabilities", True), ("editor.capabilities", True)])
                    self.assertNotIn(fake_token, run.stdout)
                finally:
                    server.shutdown()
                    thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
