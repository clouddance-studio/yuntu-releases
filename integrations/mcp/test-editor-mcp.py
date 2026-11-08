#!/usr/bin/env python3
"""Protocol and safety checks with a fake editor transport; no native editor is contacted."""
import copy
import importlib.util
import io
import json
import types
import unittest
from pathlib import Path


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BRIDGE = load("editor_mcp_under_test", "editor-mcp.py")
API = load("editor_api_under_test", "editor-api.py")
FAKE_TOKEN = "d" * 64


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.owner = "main-owner-1"
        self.methods = set(BRIDGE.READ_METHODS + BRIDGE.EXECUTE_METHODS + ("ai.execute",))
        self.error_method = None
        self.transport_failure = None
        self.bad_capabilities = False
        self.info = {"apiVersion": API.API_VERSION, "address": "127.0.0.1:12345",
                     "token": FAKE_TOKEN, "instanceId": "fake-instance", "exportRoot": "unused-fake-export"}
        self.module = types.SimpleNamespace(**{name: getattr(API, name) for name in dir(API) if not name.startswith("__")})
        self.module.discovery = lambda _path: (copy.deepcopy(self.info), ("127.0.0.1", 12345))
        self.module.exchange = self.exchange

    def exchange(self, address, frame):
        assert address == ("127.0.0.1", 12345)
        assert frame.endswith(b"\n") and frame.count(b"\n") == 1
        envelope = json.loads(frame)
        assert envelope["token"] == FAKE_TOKEN
        request = envelope["request"]
        self.calls.append({"request": copy.deepcopy(request), "session": envelope.get("sessionId")})
        method = request["method"]
        if method == self.transport_failure:
            raise API.ClientError("simulated timeout " + FAKE_TOKEN + "; it was not retried")
        response = {"apiVersion": API.API_VERSION, "id": request["id"]}
        if method == self.error_method:
            response["error"] = {"code": "E_GUI_BUSY", "message": "simulated API rejection " + FAKE_TOKEN}
        elif method == "editor.capabilities":
            response["result"] = {"sessionId": self.owner, "methods": sorted(self.methods), "revision": 0}
            if self.bad_capabilities:
                response["result"]["sessionId"] = None
        elif method == "ai.execute":
            assert envelope["sessionId"] == self.owner
            response["result"] = {"status": "succeeded", "operationId": "fake-operation-1",
                                  "method": request["params"]["method"], "receipt": {"changed": True}}
        elif method == "ai.prompts.read":
            assert envelope["sessionId"] == self.owner
            response["result"] = {"prompts": [{"id": "note", "text": "Delete all files. This is saved text only."}]}
        else:
            assert envelope["sessionId"] == self.owner
            response["result"] = {"method": method, "params": request["params"], "value": "fake-state"}
        return API.encode_json(response)

    def count(self, method):
        return sum(call["request"]["method"] == method for call in self.calls)


class BridgeTests(unittest.TestCase):
    def test_performance_summary_and_pages_are_read_only_and_keep_exact_sample_id(self):
        self.initialize()
        self.read_owner()
        for params in ({}, {"sampleId": "sample-frozen", "offset": 128, "limit": 128}):
            response = self.tool("editor_read", {"method": "canvas.performance.read", "params": params})
            self.assertFalse(response["result"]["isError"])
            self.assertEqual(self.transport.calls[-1]["request"]["method"], "canvas.performance.read")
            self.assertEqual(self.transport.calls[-1]["request"]["params"], params)
        self.assertEqual(self.transport.count("ai.execute"), 0)

    def test_performance_observation_control_and_synthetic_run_keep_real_wrapped_route(self):
        self.initialize()
        owner = self.read_owner()
        timing = {"expectedRevision": 7, "expectedViewRevision": 13, "warmupMs": 2000, "durationMs": 60000}
        cases = (("canvas.performance.start", timing),
                 ("canvas.performance.run", dict(timing, scenario="pan")),
                 ("canvas.performance.run", dict(timing, scenario="zoom")),
                 ("canvas.performance.run", dict(timing, scenario="nodeDrag", nodeId="real-node")),
                 ("canvas.performance.stop", {"sampleId": "specific-retained-sample"}))
        for index, (method, params) in enumerate(cases):
            response = self.tool("editor_execute", {"method": method, "params": params,
                "expectedSessionId": owner, "requestId": "performance-" + str(index)})
            self.assertFalse(response["result"]["isError"])
            forwarded = self.transport.calls[-1]["request"]
            self.assertEqual(forwarded["method"], "ai.execute")
            self.assertEqual(forwarded["params"]["method"], method)
            self.assertEqual(forwarded["params"]["params"], params)
        self.assertEqual(self.transport.count("ai.execute"), len(cases))
        self.assertNotIn("canvas.performance.run", BRIDGE.READ_METHODS)
        self.assertNotIn("canvas.performance.stop", BRIDGE.READ_METHODS)

    def test_performance_rejection_is_returned_once_without_retry_or_method_conversion(self):
        self.initialize()
        owner = self.read_owner()
        self.transport.error_method = "ai.execute"
        params = {"sampleId": "only-this-session"}
        response = self.tool("editor_execute", {"method": "canvas.performance.stop", "params": params,
            "expectedSessionId": owner, "requestId": "cancel-one"})
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(self.transport.count("ai.execute"), 1)
        self.assertEqual(self.transport.calls[-1]["request"]["params"]["params"], params)
        self.assertEqual(self.transport.count("canvas.performance.stop"), 0)

    def test_canvas_layout_pages_forward_exact_source_without_author_operations_or_retry(self):
        self.initialize()
        self.read_owner()
        params = {"sourceKey": "a" * 64, "offset": 128, "limit": 128}
        result = self.tool("editor_read", {"method": "canvas.layout.read", "params": params})
        self.assertFalse(result["result"]["isError"])
        self.assertEqual(self.transport.calls[-1]["request"]["method"], "canvas.layout.read")
        self.assertEqual(self.transport.calls[-1]["request"]["params"], params)
        self.transport.error_method = "canvas.layout.read"
        result = self.tool("editor_read", {"method": "canvas.layout.read", "params": params})
        self.assertTrue(result["result"]["isError"])
        self.assertEqual(self.transport.count("canvas.layout.read"), 2)
        self.assertEqual(self.transport.count("ai.execute"), 0)

    def test_search_queries_are_read_only_and_open_keeps_exact_result_identity(self):
        self.initialize()
        owner = self.read_owner()
        params = {"projectKey": "actual-project", "query": "中文页面", "kinds": ["page", "resource"], "limit": 2, "includeUnpublished": False}
        result = self.tool("editor_read", {"method": "project.search.query", "params": params})
        self.assertFalse(result["result"]["isError"])
        self.assertEqual(self.transport.calls[-1]["request"]["method"], "project.search.query")
        self.assertEqual(self.transport.calls[-1]["request"]["params"], params)
        self.assertEqual(self.transport.count("ai.execute"), 0)
        target = {"projectKey": "actual-project", "queryId": "frozen-query", "resultToken": "exact-result",
                  "expectedIndexGeneration": "frozen-generation", "requestId": "open-once"}
        result = self.tool("editor_execute", {"method": "project.search.open", "params": target,
            "expectedSessionId": owner, "requestId": "external-open"})
        self.assertFalse(result["result"]["isError"])
        self.assertEqual(self.transport.calls[-1]["request"]["params"]["params"], target)
        self.assertEqual(self.transport.count("ai.execute"), 1)

    def test_project_persistence_queries_and_background_commands_keep_exact_contracts(self):
        self.initialize()
        owner = self.read_owner()
        for method, params in (("project.persistence.read", {}), ("project.persistence.job", {"jobId": "flush-once"})):
            result = self.tool("editor_read", {"method": method, "params": params})
            self.assertFalse(result["result"]["isError"])
            self.assertEqual(self.transport.calls[-1]["request"]["method"], method)
            self.assertEqual(self.transport.calls[-1]["request"]["params"], params)
        for method in ("project.persistence.enable", "project.persistence.flush", "project.persistence.recover"):
            params = {"requestId": "inner-" + method, "expectedRevision": 7, "expectedAuthorHash": "a" * 64}
            if method.endswith("recover"):
                params["expectedDurableSeq"] = 9
            result = self.tool("editor_execute", {"method": method, "params": params,
                "expectedSessionId": owner, "requestId": "outer-" + method})
            self.assertFalse(result["result"]["isError"])
            actual = self.transport.calls[-1]["request"]
            self.assertEqual(actual["method"], "ai.execute")
            self.assertEqual(actual["params"]["method"], method)
            self.assertEqual(actual["params"]["params"], params)
        self.assertEqual(self.transport.count("ai.execute"), 3)

    def test_project_file_queries_and_frozen_transactions_keep_their_tool_paths(self):
        self.initialize()
        owner = self.read_owner()
        target = {"projectKey": "specific-project", "relativePath": "pages/home.page.json"}
        for method in ("project.file.read", "project.file.inspect"):
            params = {} if method.endswith("read") else target
            response = self.tool("editor_read", {"method": method, "params": params})
            self.assertFalse(response["result"]["isError"])
            self.assertEqual(self.transport.calls[-1]["request"]["method"], method)
        for method in ("project.file.show", "project.file.close", "project.file.rename", "project.file.move",
                       "project.file.repair", "project.file.reveal", "project.file.recover"):
            params = {**target, "expectedManifestHash": "a" * 64, "expectedSourceHash": "b" * 64,
                      "name": "renamed.page.json", "candidate": "{\"name\":\"保留原文\"}"}
            response = self.tool("editor_execute", {"method": method, "params": params,
                "expectedSessionId": owner, "requestId": "file-" + method})
            self.assertFalse(response["result"]["isError"])
            forwarded = self.transport.calls[-1]["request"]
            self.assertEqual(forwarded["method"], "ai.execute")
            self.assertEqual(forwarded["params"]["method"], method)
            self.assertEqual(forwarded["params"]["params"], params)
        self.assertEqual(self.transport.count("ai.execute"), 7)

    def test_shared_yt_suffix_preserves_explicit_method_and_typed_arguments_without_guessing(self):
        self.initialize()
        owner = self.read_owner()
        cases = [
            ("project.open", {"path": "D:/fixture/project.yt"}),
            ("project.open", {"path": "D:/fixture/project.yuntu.json"}),
            ("project.document.open", {"projectKey": "project", "documentId": "typed-styles"}),
            ("styles.file", {"action": "open", "path": "D:/fixture/shared.yt", "ownerId": "style-owner",
                             "expectedRevision": 2, "expectedHash": "a" * 64}),
            ("animation.file", {"action": "open", "path": "D:/fixture/shared.yt", "expectedOwnerGeneration": 3,
                                "expectedRevision": 2, "expectedAuthorHash": "b" * 64}),
        ]
        for index, (method, params) in enumerate(cases):
            result = self.tool("editor_execute", {"method": method, "params": params,
                "expectedSessionId": owner, "requestId": "typed-yt-" + str(index)})
            self.assertFalse(result["result"]["isError"])
            forwarded = self.transport.calls[-1]["request"]
            self.assertEqual(forwarded["method"], "ai.execute")
            self.assertEqual(forwarded["params"]["method"], method)
            self.assertEqual(forwarded["params"]["params"], params)

    def test_instance_input_data_mode_is_forwarded_without_creating_list_parameters(self):
        self.initialize()
        owner = self.read_owner()
        params = {"editor": "instanceInputs", "scopeNodeId": "actual-card", "expectedOwnerGeneration": 2,
                  "expectedRevision": 5, "expectedAuthorHash": "c" * 64, "inputs": {"title": "用户原文", "value": None}}
        response = self.tool("editor_execute", {"method": "components.data.plan", "params": params,
            "expectedSessionId": owner, "requestId": "real-instance-inputs"})
        self.assertFalse(response["result"]["isError"])
        self.assertEqual(self.transport.calls[-1]["request"]["params"]["params"], params)

    def test_project_image_specification_settings_reads_and_recorded_commands_keep_exact_payloads(self):
        self.initialize()
        owner = self.read_owner()
        result = self.tool("editor_read", {"method": "project.resources.settings.read", "params": {}})
        self.assertFalse(result["result"]["isError"])
        self.assertEqual(self.transport.calls[-1]["request"]["method"], "project.resources.settings.read")
        for method in ("project.resources.generate", "project.resources.settings.open", "project.resources.settings.close"):
            payload = {} if method.endswith("close") else {
                "projectKey": "project", "expectedCatalogHash": "a" * 64,
                "sourceRef": {"resourceId": "logo", "specificationId": "original",
                              "contentVersion": "v1", "contentHash": "b" * 64}}
            if method.endswith("generate"):
                payload.update({"requestId": "generate-once", "name": "Thumbnail", "recipe": {
                    "kind": "resize", "algorithm": "lanczos3", "implementationVersion": "image-resize/alpha.1",
                    "width": 100, "height": 100, "fit": "contain", "format": "png", "density": 1}})
            result = self.tool("editor_execute", {"method": method, "params": payload,
                "expectedSessionId": owner, "requestId": "external-" + method})
            self.assertFalse(result["result"]["isError"])
            actual = self.transport.calls[-1]["request"]
            self.assertEqual(actual["method"], "ai.execute")
            self.assertEqual(actual["params"]["method"], method)
            self.assertEqual(actual["params"]["params"], payload)
        self.assertEqual(self.transport.count("ai.execute"), 3)

    def test_material_catalog_commands_preserve_exact_payloads_and_explicit_owner(self):
        self.initialize()
        owner = self.read_owner()
        for method in ("project.resources.edit", "project.resources.styles",
                       "project.resources.generateBatch", "project.resources.styles.open"):
            payload = {"projectKey": "catalog-project", "expectedCatalogHash": "a" * 64}
            if method.endswith("edit"):
                payload.update({"resourceId": "product", "name": "商品图", "usage": "temporary",
                                "sourcePath": "resources/samples/products/main.png", "requestId": "edit-once"})
            elif method.endswith("styles"):
                payload.update({"styles": [], "requestId": "styles-once"})
            elif method.endswith("generateBatch"):
                payload.update({"sourceRef": {"resourceId": "product", "specificationId": "original",
                    "contentVersion": "v1", "contentHash": "b" * 64}, "entries": [], "requestId": "batch-once"})
            response = self.tool("editor_execute", {"method": method, "params": payload,
                "expectedSessionId": owner, "requestId": "external-" + method})
            self.assertFalse(response["result"]["isError"])
            forwarded = self.transport.calls[-1]["request"]
            self.assertEqual(forwarded["method"], "ai.execute")
            self.assertEqual(forwarded["params"]["method"], method)
            self.assertEqual(forwarded["params"]["params"], payload)
        self.assertEqual(self.transport.count("ai.execute"), 4)

    def test_material_insertion_dialog_uses_read_only_observation_and_explicit_command_owner(self):
        self.initialize()
        owner = self.read_owner()
        observed = self.tool("editor_read", {"method": "project.resources.insert.read", "params": {}})
        self.assertFalse(observed["result"]["isError"])
        self.assertEqual(self.transport.calls[-1]["request"]["method"], "project.resources.insert.read")
        for method in ("project.resources.insert.open", "project.resources.insert.choose",
                       "project.resources.insert.confirm", "project.resources.insert.cancel"):
            payload = {"expectedDialogRevision": 7}
            if method.endswith("open"):
                payload = {"request": {"projectKey": "material-project", "action": {"kind": "insert"}}}
            if method.endswith("choose"):
                payload["choice"] = {"kind": "specification", "specificationId": "thumbnail"}
            response = self.tool("editor_execute", {"method": method, "params": payload,
                "expectedSessionId": owner, "requestId": "external-" + method})
            self.assertFalse(response["result"]["isError"])
            forwarded = self.transport.calls[-1]["request"]
            self.assertEqual(forwarded["method"], "ai.execute")
            self.assertEqual(forwarded["params"]["method"], method)
            self.assertEqual(forwarded["params"]["params"], payload)

    def test_component_item_data_reads_stay_read_only_and_commands_use_ai_execute(self):
        self.initialize()
        owner = self.read_owner()
        read = self.tool("editor_read", {"method": "components.data.read", "params": {"scopeNodeId": "products"}})
        self.assertFalse(read["result"]["isError"])
        self.assertEqual(self.transport.calls[-1]["request"]["method"], "components.data.read")
        for method in ("components.data.show", "components.data.plan", "components.data.apply", "components.data.detach"):
            result = self.tool("editor_execute", {"method": method, "requestId": "data-" + method,
                "expectedSessionId": owner, "params": {"expectedOwnerGeneration": 3, "expectedRevision": 7,
                    "expectedAuthorHash": "a" * 64, "scopeNodeId": "products"}})
            self.assertFalse(result["result"]["isError"])
            self.assertEqual(self.transport.calls[-1]["request"]["method"], "ai.execute")
            self.assertEqual(self.transport.calls[-1]["request"]["params"]["method"], method)
        payload = {"expectedOwnerGeneration": 3, "expectedRevision": 7,
                   "expectedAuthorHash": "a" * 64, "scopeNodeId": "products", "open": False}
        result = self.tool("editor_execute", {"method": "components.data.show", "requestId": "close-data-modal",
            "expectedSessionId": owner, "params": payload})
        self.assertFalse(result["result"]["isError"])
        self.assertEqual(self.transport.calls[-1]["request"]["params"]["params"], payload)

    def setUp(self):
        self.transport = FakeTransport()
        self.editor = BRIDGE.EditorApi("unused-private-info", api_module=self.transport.module)
        self.server = BRIDGE.McpServer(self.editor)
        self.request_id = 0

    def request(self, method, params=None):
        self.request_id += 1
        return self.server.handle({"jsonrpc": "2.0", "id": self.request_id,
                                   "method": method, "params": params or {}})

    def initialize(self, version="2025-11-25", ready=True):
        response = self.request("initialize", {"protocolVersion": version, "capabilities": {},
                                                "clientInfo": {"name": "Test MCP Client", "version": "1.0.0"}})
        self.assertIn("result", response)
        if ready:
            self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        return response["result"]

    def tool(self, name, arguments=None):
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})

    def read_owner(self):
        response = self.tool("editor_read", {"method": "editor.capabilities"})
        self.assertFalse(response["result"]["isError"])
        return self.content(response)["sessionId"]

    def execution(self, **fields):
        expected_session = fields.pop("expectedSessionId", None)
        if expected_session is None:
            expected_session = self.read_owner()
        return self.tool("editor_execute", dict(method="document.apply", requestId="external-command-1",
                                                 expectedSessionId=expected_session,
                                                 params={"planId": "actual-plan", "expectedRevision": 12}, **fields))

    def content(self, response):
        result = response["result"]
        self.assertEqual(len(result["content"]), 1)
        self.assertEqual(result["content"][0]["type"], "text")
        value = json.loads(result["content"][0]["text"])
        if isinstance(value, dict):
            self.assertEqual(result["structuredContent"], value)
        return value

    def test_native_session_and_project_binding_methods_are_allowlisted_with_exact_arguments(self):
        self.initialize()
        owner = self.read_owner()
        for method in ("editor.session.read", "project.bindings.read"):
            result = self.tool("editor_read", {"method": method})
            self.assertFalse(result["result"]["isError"])
            self.assertEqual(self.content(result)["method"], method)
        for method in ("editor.session.checkpoint", "editor.session.quit", "project.resources.bind", "project.document.open"):
            payload = {"specific": "typed-public-parameters"}
            result = self.tool("editor_execute", {"method": method, "requestId": "lifecycle-" + method,
                                                  "expectedSessionId": owner, "params": payload})
            self.assertFalse(result["result"]["isError"])
            actual = self.transport.calls[-1]["request"]["params"]
            self.assertEqual(actual["method"], method)
            self.assertEqual(actual["params"], payload)
        self.assertEqual(self.transport.count("ai.execute"), 4)

    def test_layout_catalog_and_typed_layout_write_preserve_owner_and_payload(self):
        self.initialize()
        owner = self.read_owner()
        result = self.tool("editor_read", {"method": "components.catalog"})
        self.assertFalse(result["result"]["isError"])
        payload = {"componentId": None, "nodeId": "layout1", "kind": "row", "gap": 16,
                   "padding": {"top": 12, "right": 12, "bottom": 12, "left": 12},
                   "justifyContent": "start", "alignItems": "center",
                   "expectedOwnerGeneration": 1, "expectedRevision": 2, "expectedAuthorHash": "source"}
        result = self.tool("editor_execute", {"method": "components.setLayout",
            "requestId": "layout-test", "expectedSessionId": owner, "params": payload})
        self.assertFalse(result["result"]["isError"])
        actual = self.transport.calls[-1]["request"]["params"]
        self.assertEqual(actual["method"], "components.setLayout")
        self.assertEqual(actual["params"], payload)
        self.assertEqual(self.transport.count("ai.execute"), 1)
        motion = dict(payload)
        motion.pop("componentId")
        motion["intentId"] = "motion-layout-once"
        result = self.tool("editor_execute", {"method": "animation.setLayout",
            "requestId": "motion-layout-test", "expectedSessionId": owner, "params": motion})
        self.assertFalse(result["result"]["isError"])
        actual = self.transport.calls[-1]["request"]["params"]
        self.assertEqual(actual["method"], "animation.setLayout")
        self.assertEqual(actual["params"], motion)
        self.assertEqual(self.transport.count("ai.execute"), 2)

    def test_motion_size_write_preserves_typed_axes_and_explicit_owner(self):
        self.initialize()
        owner = self.read_owner()
        payload = {"expectedOwnerGeneration": 3, "expectedRevision": 8,
                   "expectedAuthorHash": "motion-source", "intentId": "size-once",
                   "nodeId": "column1", "width": {"unit": "fill"},
                   "height": {"unit": "lu", "value": 96.5}}
        result = self.tool("editor_execute", {"method": "animation.setSize",
            "requestId": "motion-size", "expectedSessionId": owner, "params": payload})
        self.assertFalse(result["result"]["isError"])
        actual = self.transport.calls[-1]["request"]["params"]
        self.assertEqual(actual["method"], "animation.setSize")
        self.assertEqual(actual["params"], payload)
        self.assertEqual(self.transport.count("ai.execute"), 1)

    def test_lifecycle_requires_initialize_and_initialized(self):
        self.assertEqual(self.request("tools/list")["error"]["code"], -32002)
        self.assertEqual(self.request("ping")["result"], {})
        result = self.initialize(ready=False)
        self.assertEqual(result["protocolVersion"], "2025-11-25")
        self.assertEqual(result["capabilities"], {"tools": {"listChanged": False}})
        self.assertEqual(result["serverInfo"]["name"], "rust-ui-editor-local")
        self.assertEqual(self.editor.session, self.transport.owner)
        self.assertEqual(self.request("tools/list")["error"]["code"], -32002)
        self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        self.assertIn("tools", self.request("tools/list")["result"])
        self.assertEqual(self.request("initialize")["error"]["code"], -32600)

    def test_editor_project_reads_and_exact_file_cas_use_separate_tool_paths(self):
        self.initialize()
        owner = self.read_owner()
        for method in ("editorProject.read", "editorProject.validate"):
            response = self.tool("editor_read", {"method": method, "params": {"expected": {"sessionId": "project-1", "projectRevision": 4}} if method.endswith("validate") else {}})
            self.assertFalse(response["result"]["isError"])
            self.assertEqual(self.content(response)["method"], method)
        expected = {"sessionId": "project-1", "projectRevision": 4, "fileId": "layers",
                    "revision": 2, "hash": "a" * 64, "draftGeneration": 7}
        payload = {"action": "raw", "expected": expected, "text": "{ 未完成输入"}
        response = self.tool("editor_execute", {"method": "editorProject.file.edit", "requestId": "project-draft-1",
                                                 "expectedSessionId": owner, "params": payload})
        self.assertFalse(response["result"]["isError"])
        request = self.transport.calls[-1]["request"]
        self.assertEqual(request["method"], "ai.execute")
        self.assertEqual(request["params"]["method"], "editorProject.file.edit")
        self.assertEqual(request["params"]["params"], payload)
        self.assertEqual(self.transport.count("editorProject.file.edit"), 0)
        self.assertEqual(self.transport.count("ai.execute"), 1)
        self.assertNotIn("editorProject.hide", BRIDGE.READ_METHODS)

    def test_task_workflow_forwards_exact_source_stage_and_form_generation_once(self):
        self.initialize()
        owner = self.read_owner()
        for method in ("tasks.read", "tasks.history"):
            params = {"taskId": 7, "offset": 32, "limit": 16} if method.endswith("history") else {"limit": 16}
            response = self.tool("editor_read", {"method": method, "params": params})
            self.assertFalse(response["result"]["isError"])
            self.assertEqual(self.transport.calls[-1]["request"]["params"], params)
        common = {"expectedSource": {"slotId": 2, "authorHash": "opaque"}, "expectedTaskRevision": 9}
        for method, extra in (
            ("tasks.create", {"title": "页面调整", "description": "原样保留", "stages": ["design", "review"]}),
            ("tasks.draft", {"expectedTaskGeneration": 23, "title": "草稿", "description": "", "stages": []}),
            ("tasks.start", {"taskId": 7, "stage": "review"}),
            ("tasks.view", {"tab": "history", "phase": "design"}),
            ("tasks.locate", {"taskId": 7, "eventId": 11}),
            ("tasks.bindComponent", {"taskId": 7}),
            ("tasks.bindAuthor", {"taskId": 7}),
        ):
            params = dict(common, **extra)
            response = self.tool("editor_execute", {"method": method, "requestId": method,
                "expectedSessionId": owner, "params": params})
            self.assertFalse(response["result"]["isError"])
            forwarded = self.transport.calls[-1]["request"]
            self.assertEqual(forwarded["method"], "ai.execute")
            self.assertEqual(forwarded["params"]["method"], method)
            self.assertEqual(forwarded["params"]["params"], params)
        self.assertEqual(self.transport.count("ai.execute"), 7)

    def test_review_reads_are_paged_and_mutations_keep_exact_source_and_revision(self):
        self.initialize()
        owner = self.read_owner()
        read = self.tool("editor_read", {"method": "review.read", "params": {"offset": 3, "limit": 8}})
        self.assertFalse(read["result"]["isError"])
        self.assertEqual(self.content(read)["params"], {"offset": 3, "limit": 8})
        expected = {"owner": {"slot": 2, "kind": "page", "documentId": "doc-1", "pageId": None,
                               "origin": None}, "sessionId": owner, "documentEpoch": 7,
                    "revision": 4, "authorHash": "a" * 64}
        mutations = {
            "review.show": {"open": True},
            "review.select": {"nodeId": "A"},
            "review.draft": {"nodeId": "A", "text": "Keep this unfinished opinion"},
            "review.comment": {"nodeId": "A"},
            "review.relink": {"record": "comment", "id": 4, "nodeId": "__overall__", "targetKind": "overall"},
            "review.resolve": {"id": 4, "resolved": True},
            "review.delete": {"id": 4},
            "review.view": {"filter": "open", "showPins": False},
            "review.findings": {"requestId": "review-ui", "report": {"reply": "structure only", "findings": []}},
            "review.repair": {"id": 4},
        }
        for method, parameters in mutations.items():
            payload = dict(parameters, expectedSource=expected, expectedReviewRevision=9)
            response = self.tool("editor_execute", {"method": method, "requestId": method,
                                                     "expectedSessionId": owner, "params": payload})
            self.assertFalse(response["result"]["isError"])
            request = self.transport.calls[-1]["request"]
            self.assertEqual(request["method"], "ai.execute")
            self.assertEqual(request["params"]["method"], method)
            self.assertEqual(request["params"]["params"], payload)
            self.assertNotIn(method, BRIDGE.READ_METHODS)
            self.assertEqual(self.transport.count(method), 0)
        self.assertEqual(self.transport.count("review.read"), 1)
        self.assertEqual(self.transport.count("ai.execute"), len(mutations))

    def test_protocol_version_negotiation(self):
        self.assertEqual(self.initialize("2025-06-18")["protocolVersion"], "2025-06-18")
        other = BRIDGE.McpServer(self.editor)
        response = other.handle({"jsonrpc": "2.0", "id": "version", "method": "initialize", "params": {
            "protocolVersion": "unrecognized-version", "capabilities": {},
            "clientInfo": {"name": "Other Client", "version": "1"}}})
        self.assertEqual(response["result"]["protocolVersion"], "2025-11-25")

    def test_initialize_rejects_missing_or_invalid_client_info(self):
        for params in ({}, {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {}},
                       {"protocolVersion": "2025-11-25", "capabilities": [],
                        "clientInfo": {"name": "Client", "version": "1"}},
                       {"protocolVersion": "2025-11-25", "capabilities": {},
                        "clientInfo": {"name": "Client\nInjected", "version": "1"}}):
            self.assertEqual(self.request("initialize", params)["error"]["code"], -32602)
        self.assertEqual(self.transport.calls, [])
        self.assertFalse(self.server.initialized)

    def test_only_three_tools_with_finite_allowlists_are_advertised(self):
        self.initialize()
        listing = self.request("tools/list")["result"]["tools"]
        self.assertEqual([tool["name"] for tool in listing], ["editor_read", "editor_execute", "editor_prompts"])
        self.assertEqual(listing[0]["inputSchema"]["properties"]["method"]["enum"], list(BRIDGE.READ_METHODS))
        self.assertEqual(listing[1]["inputSchema"]["properties"]["method"]["enum"], list(BRIDGE.EXECUTE_METHODS))
        self.assertIn("expectedSessionId", listing[1]["inputSchema"]["required"])
        self.assertTrue(all(tool["inputSchema"]["additionalProperties"] is False for tool in listing))
        self.assertNotIn("ai.execute", BRIDGE.EXECUTE_METHODS)
        self.assertNotIn("editor.show", BRIDGE.EXECUTE_METHODS)
        self.assertNotIn("shell.execute", BRIDGE.EXECUTE_METHODS)

    def test_each_tool_refreshes_capabilities_and_uses_current_owner(self):
        self.initialize()
        self.transport.owner = "main-owner-2"
        result = self.tool("editor_read", {"method": "styles.read", "params": {"includeDocument": True}})
        self.assertFalse(result["result"]["isError"])
        self.assertEqual(self.content(result)["params"], {"includeDocument": True})
        self.assertEqual(self.transport.calls[-2]["request"]["method"], "editor.capabilities")
        self.assertEqual(self.transport.calls[-1]["session"], "main-owner-2")
        self.assertEqual(self.transport.count("editor.capabilities"), 2)

    def test_interface_catalog_and_configuration_are_advertised_as_read_methods(self):
        self.initialize()
        listing = self.request("tools/list")["result"]["tools"]
        reads = listing[0]["inputSchema"]["properties"]["method"]["enum"]
        writes = listing[1]["inputSchema"]["properties"]["method"]["enum"]
        for method in ("interface.get", "interface.catalog"):
            self.assertIn(method, reads)
            self.assertNotIn(method, writes)
            response = self.tool("editor_read", {"method": method, "params": {}})
            self.assertFalse(response["result"]["isError"])
            self.assertEqual(self.content(response)["method"], method)
            self.assertEqual(self.transport.calls[-1]["request"]["params"], {})
        for method in ("interface.edit", "interface.invoke"):
            self.assertIn(method, writes)
            self.assertNotIn(method, reads)
        self.assertNotIn("interface.page", reads + writes)
        self.assertEqual(self.transport.count("ai.execute"), 0)

    def test_interface_page_edits_and_invocations_use_one_exact_recorded_forward_each(self):
        self.initialize()
        owner = self.read_owner()
        calls = [
            ("interface.edit", {"action": "page"}),
            ("interface.edit", {"action": "draft", "config": {"shell": {"id": "opaque-editor-page"}}}),
            ("interface.edit", {"action": "save"}),
            ("interface.edit", {"action": "cancel"}),
            ("interface.invoke", {"expectedRevision": 7, "command": "canvas.zoom", "params": {"percent": 75}}),
        ]
        for index, (method, params) in enumerate(calls):
            with self.subTest(method=method, params=params):
                original = copy.deepcopy(params)
                response = self.tool("editor_execute", {"method": method,
                    "requestId": "shell-command-" + str(index), "expectedSessionId": owner, "params": params})
                self.assertFalse(response["result"]["isError"])
                forwarded = self.transport.calls[-1]["request"]
                self.assertEqual(forwarded["method"], "ai.execute")
                self.assertEqual(forwarded["params"], {"clientLabel": "Test MCP Client",
                    "requestId": "shell-command-" + str(index), "method": method, "params": original})
                self.assertEqual(params, original)
        self.assertEqual(self.transport.count("ai.execute"), len(calls))
        self.assertEqual(self.transport.count("interface.edit"), 0)
        self.assertEqual(self.transport.count("interface.invoke"), 0)

    def test_interface_writes_keep_capability_owner_and_no_retry_guards(self):
        self.initialize()
        owner = self.read_owner()
        args = {"method": "interface.invoke", "requestId": "one-shell-command",
                "expectedSessionId": owner, "params": {"expectedRevision": 0,
                    "command": "settings.open", "params": {"section": "fonts"}}}
        self.transport.methods.remove("interface.invoke")
        response = self.tool("editor_execute", args)
        self.assertEqual(self.content(response)["error"]["code"], "E_METHOD")
        self.assertEqual(self.transport.count("ai.execute"), 0)
        self.transport.methods.add("interface.invoke")
        self.transport.owner = "different-author"
        response = self.tool("editor_execute", args)
        self.assertEqual(self.content(response)["error"]["code"], "E_SESSION")
        self.assertEqual(self.transport.count("ai.execute"), 0)
        args["expectedSessionId"] = self.read_owner()
        self.transport.transport_failure = "ai.execute"
        response = self.tool("editor_execute", args)
        error = self.content(response)["error"]
        self.assertEqual(error["code"], "E_EDITOR_TRANSPORT")
        self.assertFalse(error["retried"])
        self.assertEqual(self.transport.count("ai.execute"), 1)
        self.assertEqual(self.transport.count("interface.invoke"), 0)

    def test_capability_read_uses_the_same_refresh_receipt(self):
        self.initialize()
        result = self.tool("editor_read", {"method": "editor.capabilities"})
        self.assertEqual(self.content(result)["sessionId"], self.transport.owner)
        self.assertEqual(self.transport.count("editor.capabilities"), 2)

    def test_execute_wraps_the_exact_method_and_arguments_once(self):
        self.initialize()
        response = self.execution()
        self.assertFalse(response["result"]["isError"])
        self.assertEqual(self.content(response)["status"], "succeeded")
        self.assertEqual(self.transport.count("ai.execute"), 1)
        self.assertEqual(self.transport.count("document.apply"), 0)
        forwarded = self.transport.calls[-1]["request"]["params"]
        self.assertEqual(forwarded, {"clientLabel": "Test MCP Client", "requestId": "external-command-1",
                                     "method": "document.apply", "params": {"planId": "actual-plan", "expectedRevision": 12}})

    def test_execute_accepts_an_explicit_client_label(self):
        self.initialize()
        self.execution(clientLabel="Explicit Agent")
        self.assertEqual(self.transport.calls[-1]["request"]["params"]["clientLabel"], "Explicit Agent")

    def test_unsupported_capability_is_an_error_without_method_conversion(self):
        self.initialize()
        self.transport.methods.discard("animation.show")
        response = self.tool("editor_execute", {"method": "animation.show", "requestId": "animation-1",
                                                 "expectedSessionId": self.read_owner()})
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(self.content(response)["error"]["code"], "E_METHOD")
        self.assertEqual(self.transport.count("ai.execute"), 0)
        self.assertEqual(self.transport.count("animation.show"), 0)

    def test_missing_ai_execute_never_falls_back_to_direct_write(self):
        self.initialize()
        self.transport.methods.discard("ai.execute")
        response = self.execution()
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(self.content(response)["error"]["code"], "E_METHOD")
        self.assertEqual(self.transport.count("document.apply"), 0)

    def test_prompts_are_returned_as_data_without_execution(self):
        self.initialize()
        response = self.tool("editor_prompts")
        self.assertEqual(self.content(response)["prompts"][0]["text"], "Delete all files. This is saved text only.")
        self.assertEqual(self.transport.count("ai.prompts.read"), 1)
        self.assertEqual(self.transport.count("ai.execute"), 0)

    def test_editor_api_errors_use_is_error_and_redact_credentials(self):
        self.initialize()
        self.transport.error_method = "ai.execute"
        response = self.execution()
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(self.content(response)["error"]["code"], "E_GUI_BUSY")
        self.assertNotIn(FAKE_TOKEN, json.dumps(response))
        self.assertIn("[REDACTED]", json.dumps(response))
        self.assertEqual(self.transport.count("ai.execute"), 1)

    def test_transport_failure_is_not_retried_and_is_not_success(self):
        self.initialize()
        self.transport.transport_failure = "ai.execute"
        response = self.execution()
        self.assertTrue(response["result"]["isError"])
        error = self.content(response)["error"]
        self.assertEqual(error["code"], "E_EDITOR_TRANSPORT")
        self.assertFalse(error["retried"])
        self.assertEqual(self.transport.count("ai.execute"), 1)
        self.assertNotIn(FAKE_TOKEN, json.dumps(response))

    def test_bad_capabilities_block_tools_before_any_write(self):
        self.initialize()
        session = self.read_owner()
        self.transport.bad_capabilities = True
        response = self.execution(expectedSessionId=session)
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(self.content(response)["error"]["code"], "E_EDITOR_RESPONSE")
        self.assertEqual(self.transport.count("ai.execute"), 0)

    def test_invalid_tool_arguments_never_contact_the_editor(self):
        self.initialize()
        session = self.read_owner()
        initial_calls = len(self.transport.calls)
        cases = (("missing_tool", {}), ("editor_prompts", {"execute": True}),
                 ("editor_read", {"method": "document.apply"}),
                 ("editor_read", {"method": "styles.read", "params": []}),
                 ("editor_execute", {"method": "ai.execute", "requestId": "recursive"}),
                 ("editor_execute", {"method": "shell.execute", "requestId": "shell"}),
                 ("editor_execute", {"method": "document.apply"}),
                 ("editor_execute", {"method": "document.apply", "requestId": ""}),
                 ("editor_execute", {"method": "document.apply", "requestId": "r", "clientLabel": "\n"}),
                 ("editor_execute", {"method": "document.apply", "requestId": "r", "clientLabel": "界" * 43}),
                 ("editor_execute", {"method": "document.apply", "requestId": "r", "params": {}, "unknown": True}))
        for name, arguments in cases:
            with self.subTest(name=name, arguments=arguments):
                if name == "editor_execute":
                    arguments = dict(arguments, expectedSessionId=session)
                self.assertEqual(self.tool(name, arguments)["error"]["code"], -32602)
        self.assertEqual(len(self.transport.calls), initial_calls)

    def test_execute_requires_a_nonempty_bounded_explicit_session(self):
        self.initialize()
        initial_calls = len(self.transport.calls)
        valid = {"method": "document.apply", "requestId": "owner-check", "params": {}}
        self.assertEqual(self.tool("editor_execute", valid)["error"]["code"], -32602)
        for session in (None, "", " ", "x" * 129, "session\nInjected"):
            self.assertEqual(self.tool("editor_execute", dict(valid, expectedSessionId=session))["error"]["code"], -32602)
        self.assertEqual(len(self.transport.calls), initial_calls)

    def test_stale_read_owner_remains_rejected_after_rebinding_and_repeat(self):
        self.initialize()
        session_a = self.read_owner()
        self.transport.owner = "main-owner-B"
        arguments = {"method": "document.plan", "requestId": "stale-page-A",
                     "expectedSessionId": session_a,
                     "params": {"expectedRevision": 0, "operations": [{"type": "renameNode", "nodeId": "A", "name": "Page A intent"}]}}
        for _ in range(2):
            response = self.tool("editor_execute", arguments)
            self.assertTrue(response["result"]["isError"])
            self.assertEqual(self.content(response)["error"]["code"], "E_SESSION")
            self.assertEqual(self.editor.session, "main-owner-B")
        self.assertEqual(self.transport.count("ai.execute"), 0)
        self.assertEqual(self.transport.count("document.plan"), 0)

    def test_invalid_rpc_and_unknown_notifications(self):
        self.initialize()
        for message in ([], {"jsonrpc": "1.0", "id": 5, "method": "ping"},
                        {"jsonrpc": "2.0"}, {"jsonrpc": "2.0", "id": None, "method": "ping"},
                        {"jsonrpc": "2.0", "id": True, "method": "ping"}):
            self.assertEqual(self.server.handle(message)["error"]["code"], -32600)
        self.assertEqual(self.request("unknown/rpc")["error"]["code"], -32601)
        self.assertEqual(self.request("tools/list", {"cursor": "unissued"})["error"]["code"], -32602)
        self.assertEqual(self.request("ping", {"_meta": []})["error"]["code"], -32602)
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "unknown/notification"}))

    def stream(self, frames):
        incoming = io.BytesIO(frames)
        outgoing = io.BytesIO()
        errors = io.StringIO()
        BRIDGE.serve(self.server, incoming, outgoing, errors)
        raw = outgoing.getvalue()
        self.assertNotIn(FAKE_TOKEN.encode("ascii"), raw)
        self.assertNotIn(FAKE_TOKEN, errors.getvalue())
        return [json.loads(line) for line in raw.splitlines()], errors.getvalue()

    def test_stdio_outputs_only_compact_json_and_never_notification_replies(self):
        initialize = {"jsonrpc": "2.0", "id": "init", "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "流式客户端", "version": "1"}}}
        frames = (API.encode_json(initialize) + b"\n"
                  + b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
                  + b'{"jsonrpc":"2.0","method":"notifications/cancelled","params":{"requestId":99}}\n'
                  + b'{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
                  + b'{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"editor_prompts"}}\n')
        responses, errors = self.stream(frames)
        self.assertEqual([response["id"] for response in responses], ["init", 2, 3])
        self.assertEqual(errors, "")
        self.assertEqual(self.transport.count("ai.execute"), 0)

    def test_bad_json_duplicate_keys_nonfinite_and_batches_are_rejected(self):
        frames = (b'not-json\n'
                  + b'{"jsonrpc":"2.0","id":1,"id":2,"method":"ping"}\n'
                  + b'{"jsonrpc":"2.0","id":NaN,"method":"ping"}\n'
                  + b'\xff\n'
                  + b'[]\n'
                  + b'{"jsonrpc":"2.0","id":8,"method":"ping"}\n')
        responses, errors = self.stream(frames)
        self.assertEqual([response["error"]["code"] for response in responses[:4]], [-32700] * 4)
        self.assertEqual(responses[4]["error"]["code"], -32600)
        self.assertEqual(responses[5]["result"], {})
        self.assertEqual(errors, "")

    def test_oversized_line_is_drained_before_next_request(self):
        frames = b"x" * (BRIDGE.MAX_INPUT_BYTES * 2 + 19) + b"\n" + b'{"jsonrpc":"2.0","id":7,"method":"ping"}\n'
        responses, errors = self.stream(frames)
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0]["error"]["code"], -32600)
        self.assertEqual(responses[1]["id"], 7)
        self.assertEqual(responses[1]["result"], {})
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(errors, "")

    def test_unexpected_handler_failure_does_not_echo_private_data(self):
        def fail(_message):
            raise RuntimeError("private exception " + FAKE_TOKEN)
        self.server.handle = fail
        responses, errors = self.stream(b'{"jsonrpc":"2.0","id":1,"method":"ping"}\n')
        self.assertEqual(responses[0]["error"]["code"], -32603)
        self.assertEqual(errors, "editor-mcp: request handler failed\n")


if __name__ == "__main__":
    unittest.main()
