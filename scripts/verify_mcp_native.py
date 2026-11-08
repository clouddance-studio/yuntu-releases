"""Opt-in MCP integration test in an explicitly selected isolated editor instance.

Creates only a new test project under this repository's ignored .local directory.
Never selects a discovery file automatically or claims release acceptance.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NativeError(RuntimeError):
    def __init__(self, tool, value):
        super().__init__(tool + ": " + json.dumps(value))
        self.code = value.get("error", {}).get("code")


class Client:
    def __init__(self, info):
        self.serial = 0
        self.proc = subprocess.Popen([sys.executable, "-B", str(ROOT / "integrations/mcp/editor-mcp.py"), "--info", str(info)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf8")
        result = self.request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "yuntu-native-verification", "version": "1"}})
        self.component = result["serverInfo"]
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params):
        self.serial += 1
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.serial, "method": method, "params": params}) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP process closed before its response")
        response = json.loads(line)
        if response.get("id") != self.serial or "error" in response:
            raise RuntimeError("MCP request rejected: " + json.dumps(response.get("error")))
        return response["result"]

    def tool(self, name, args, allow_error=False):
        result = self.request("tools/call", {"name": name, "arguments": args})
        value = result.get("structuredContent")
        if value is None:
            value = json.loads(result["content"][0]["text"])
        if result.get("isError") and not allow_error:
            raise NativeError(name, value)
        return value

    def read(self, method, params=None):
        return self.tool("editor_read", {"method": method, "params": params or {}})

    def output(self, method, params, allow_error=False, session=None):
        caps = self.read("editor.capabilities")
        return self.tool("editor_output", {"method": method, "params": params, "expectedSessionId": session or caps["sessionId"]}, allow_error)

    def edit(self, method, params):
        caps = self.read("editor.capabilities")
        return self.tool("editor_execute", {"method": method, "params": params, "expectedSessionId": caps["sessionId"], "requestId": uuid.uuid4().hex})

    def wait(self, method, predicate, params=None):
        end = time.monotonic() + 45
        while True:
            try:
                value = self.read(method, params)
            except NativeError as error:
                if error.code not in ("E_SESSION", "E_FILE_BUSY"):
                    raise
                if time.monotonic() > end:
                    raise TimeoutError("Readonly poll did not acquire its expected source") from error
                time.sleep(.15)
                continue
            if predicate(value):
                return value
            if time.monotonic() > end:
                raise TimeoutError(method + " did not reach the expected state")
            time.sleep(.15)

    def export_job(self, accepted, success=True):
        def locate(state):
            for job in [state.get("job"), *state.get("recentJobs", [])]:
                if job and job.get("jobId") == accepted["jobId"] and (not accepted.get("projectKey") or job.get("projectKey") == accepted["projectKey"]):
                    return job
            return None
        state = self.wait("project.export.read", lambda s: bool(locate(s)) and locate(s)["status"] in ("completed", "failed", "cancelled"))
        job = locate(state)
        if success and job["status"] != "completed":
            raise RuntimeError("Export failed: " + json.dumps(job))
        if not success and job["status"] == "completed":
            raise RuntimeError("An invalid export unexpectedly completed")
        return job

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)
        error = self.proc.stderr.read()
        if self.proc.returncode or error:
            raise RuntimeError("MCP did not exit cleanly")


def portable_path(value):
    prefix = chr(92) * 2 + "?" + chr(92)
    return Path(value[len(prefix):] if value.startswith(prefix) else value).resolve()


def verify(info, directory):
    local = (ROOT / ".local").resolve()
    directory = directory.resolve()
    if not directory.is_relative_to(local) or not info.resolve().is_relative_to(local):
        raise ValueError("Native verification requires explicitly selected private paths inside .local")
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "mcp-native-case").exists():
        raise ValueError("Use a new verification directory; existing projects are never overwritten")
    e = Client(info)
    report = {"kind": "native-integration-only-not-release-acceptance", "component": e.component, "checks": {}}
    try:
        caps = e.read("editor.capabilities")
        report["actualEditorRelease"] = caps.get("release")
        projects = e.read("project.read")
        if projects["projects"]:
            raise ValueError("Selected editor must have an empty isolated workspace")
        names = [tool["name"] for tool in e.request("tools/list", {})["tools"]]
        assert names == ["editor_read", "editor_execute", "editor_prompts", "editor_output"]
        accepted = e.edit("project.create", {"name": "mcp-native-case", "directory": str(directory), "targets": ["web"]})
        state = e.wait("project.read", lambda s: not s["busy"] and (s.get("lastJob") or {}).get("jobId") == accepted["jobId"])
        assert state["lastJob"]["status"] == "succeeded"
        project = next(p for p in state["projects"] if portable_path(p["manifestPath"]) == (directory / "mcp-native-case/project.yt").resolve())
        accepted = e.edit("project.document.open", {"projectKey": project["key"], "documentId": project["entryDocumentId"]})
        e.wait("project.read", lambda s: not s["busy"] and (s.get("lastJob") or {}).get("jobId") == accepted["jobId"])
        stable = 0
        last = None
        for _ in range(100):
            caps = e.read("editor.capabilities")
            try:
                doc = e.read("document.read", {"expectedRevision": caps["revision"]})["document"]
            except NativeError as error:
                if error.code not in ("E_SESSION", "E_FILE_BUSY"):
                    raise
                stable = 0
                time.sleep(.15)
                continue
            if doc["id"] == project["entryDocumentId"] and not caps["gui"]["fileBusy"]:
                stable = stable + 1 if last == caps["sessionId"] else 1
                last = caps["sessionId"]
                if stable >= 3:
                    break
            time.sleep(.15)
        else:
            raise TimeoutError("Test project author did not become stable")
        ops = [
            {"type": "setViewport", "viewport": {"width": 480, "height": 200, "background": "#FCFCFE"}},
            {"type": "createText", "parentId": "page", "nodeId": "proof", "name": "Proof", "text": "MCP native verification", "width": 430, "height": 70},
            {"type": "moveNode", "nodeId": "proof", "x": 24, "y": 60},
            {"type": "setTextStyle", "nodeId": "proof", "fontSize": 30, "fontWeight": 600, "lineHeight": 1.3, "fontFamily": "system-ui"},
            {"type": "setNodeAppearance", "nodeId": "proof", "patch": {"color": "#0052FF"}},
        ]
        revision = caps["revision"]
        plan = e.edit("document.plan", {"expectedRevision": revision, "operations": ops})
        e.edit("document.apply", {"expectedRevision": revision, "planId": plan["planId"], "idempotencyKey": uuid.uuid4().hex})
        history = e.read("history.read")
        e.edit("history.save", {"expectedRevision": history["revision"], "expectedTimelineRevision": history["timelineRevision"], "idempotencyKey": uuid.uuid4().hex})
        e.wait("history.read", lambda s: not s["fileBusy"])
        caps = e.read("editor.capabilities")
        revision = caps["revision"]
        source = {"kind": "committed", "expectedRevision": revision}
        validation = e.read("document.validate", {"expectedRevision": revision})
        assert validation.get("diagnostics") == []
        report["validation"] = validation
        snapshot = e.read("preview.snapshot", {"source": source})
        report["snapshotSource"] = snapshot["source"]
        report["checks"]["validation-and-preview-snapshot"] = True
        rejected = e.tool("editor_read", {"method": "document.validate", "params": {"expectedRevision": revision + 999}}, True)
        assert "REVISION" in rejected["error"]["code"]
        report["checks"]["stale-revision-refused"] = rejected["error"]["code"]
        params = {"source": source, "format": "png", "outputPath": "mcp-proof.png"}
        accepted = e.output("preview.render", params)
        rendered = e.wait("job.status", lambda s: s["status"] != "pending", {"jobId": accepted["jobId"]})
        assert rendered["status"] == "succeeded", rendered
        image = portable_path(rendered["result"]["outputPath"])
        assert hashlib.sha256(image.read_bytes()).hexdigest() == rendered["result"]["sha256"]
        report["render"] = rendered
        for output in ["../outside.png", "mcp-proof.png"]:
            rejected = e.output("preview.render", dict(params, outputPath=output), True)
            assert "error" in rejected, rejected
            report["checks"]["render-refused-" + output] = rejected["error"]["code"]
        rejected = e.output("preview.render", params, True, session="a-stale-session")
        assert rejected["error"]["code"] == "E_SESSION"
        report["checks"]["stale-session-refused"] = True
        pending = e.output("preview.render", dict(params, outputPath="cancel-check.png"))
        cancellation = e.output("job.cancel", {"jobId": pending["jobId"]})
        terminal = e.wait("job.status", lambda s: s["status"] != "pending", {"jobId": pending["jobId"]})
        assert terminal["status"] in ("cancelled", "succeeded"), terminal
        if terminal["status"] == "succeeded":
            assert hashlib.sha256(portable_path(terminal["result"]["outputPath"]).read_bytes()).hexdigest() == terminal["result"]["sha256"]
        report["checks"]["render-cancellation-boundary"] = {"cancelReceipt": cancellation, "terminalStatus": terminal["status"]}
        base = {"projectKey": project["key"], "expectedManifestHash": project["manifestHash"]}
        rejected = e.output("project.export.settings", dict(base, expectedManifestHash="0" * 64), True)
        assert rejected["error"]["code"] == "E_EXPORT_SOURCE_CHANGED"
        report["checks"]["project-manifest-conflict-refused"] = rejected["error"]["code"]
        config = e.export_job(e.output("project.export.settings", base))["result"]
        versions = dict(base, expectedConfigurationSha256=config.get("sha256"), uiVersion="1.0.0-draft.1", mappingsVersion="1.0.0-draft.1")
        e.export_job(e.output("project.export.configure", versions))
        config = e.export_job(e.output("project.export.settings", base))["result"]
        versions["expectedConfigurationSha256"] = config["sha256"]
        report["capture"] = e.export_job(e.output("project.export.capture", base))
        source_file = directory / "mcp-native-case/home.yt"
        original_author = source_file.read_bytes()
        exported = e.export_job(e.output("project.export.write", dict(versions, outputDirectory="exports/ui")))
        output = exported["result"]["output"]
        package = portable_path(output["directory"])
        manifest_bytes = (package / "manifest.json").read_bytes()
        assert hashlib.sha256(manifest_bytes).hexdigest() == output["manifestSha256"]
        manifest = json.loads(manifest_bytes)
        for name, identity in manifest["files"].items():
            file = (package / name).resolve()
            assert file.is_relative_to(package)
            data = file.read_bytes()
            assert len(data) == identity["bytes"] and hashlib.sha256(data).hexdigest() == identity["sha256"]
        repeated = e.export_job(e.output("project.export.write", dict(versions, outputDirectory="exports/ui")))
        assert repeated["result"]["output"]["unchanged"] is True
        assert repeated["result"]["output"]["manifestSha256"] == output["manifestSha256"]
        assert source_file.read_bytes() == original_author
        report["checks"]["author-clean-after-output"] = not e.read("editor.capabilities")["gui"]["authorDirty"]
        assert report["checks"]["author-clean-after-output"]
        report["export"] = exported
        report["checks"]["export-files-hashes-repeat-and-author-preservation"] = True
        bad = e.output("project.export.write", dict(versions, expectedConfigurationSha256="0" * 64, outputDirectory="exports/ui"), True)
        report["checks"]["configuration-conflict-refused"] = bad if "error" in bad else e.export_job(bad, False)
        bad = e.output("project.export.write", dict(versions, outputDirectory="../escape"), True)
        report["checks"]["export-path-escape-refused"] = bad if "error" in bad else e.export_job(bad, False)
        assert not (directory / "escape").exists()
        assert (package / "manifest.json").read_bytes() == manifest_bytes
        assert source_file.read_bytes() == original_author
        report["passed"] = True
        return report
    finally:
        e.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--info", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.info, args.workspace)
    destination = args.workspace / "verification.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"passed": result["passed"], "checks": len(result["checks"]), "report": str(destination)}))
