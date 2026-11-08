# Set up the Yuntu Editor Skill and MCP connection

These files are prepared locally for review. They have not been published as an editor release, a package-manager package, or a plugin-store listing. Final compatibility with the accepted installed editor remains a release gate. The website domain is still under review; setup does not depend on it.

## What each component does

| Component | Purpose |
| --- | --- |
| Yuntu Editor | Runs locally and owns the editable project. Install it separately. |
| `integrations/mcp/editor-mcp.py` | Starts a stdio MCP bridge for a local AI client. |
| `integrations/mcp/editor-api.py` | The bridge's required sibling helper for the authenticated local editor API. |
| `integrations/skills/yuntu-editor/` | Instructions that help an AI client inspect, edit, verify, and export a user project. |
| External AI client | Runs the bridge, provides the conversation and model access, and enforces its own tool permissions. |

The two bridge files use Python's standard library. The current preparation checks use Python 3.12.14; a minimum supported Python version has not been certified. There is no requirement to obtain the private editor source or build Rust. Keep both scripts in the same directory. `source-provenance.json` records their exact source snapshot and checksums; its observed editor version is not a compatibility guarantee.

The bridge is local stdio MCP, not a hosted HTTP service. Its editor-side connection uses the private discovery file created by a specific editor process. A cloud-only client that cannot run on your Windows computer cannot use it merely by entering a localhost URL.

## Start the intended editor instance

For an installed executable supporting `--api-info`, replace the executable path below with the one from your verified distribution. Do not copy a developer-machine path or assume this is already the final Store MSIX launch command.

```powershell
$editorExe = 'C:\Path\To\yuntu-editor.exe'
$connectionDirectory = Join-Path $env:LOCALAPPDATA 'Yuntu\connections'
New-Item -ItemType Directory -Path $connectionDirectory -Force | Out-Null
$connectionInfo = Join-Path $connectionDirectory ('editor-' + [guid]::NewGuid().ToString('N') + '.json')
& $editorExe --api-info $connectionInfo
```

Open the intended project in that editor. Keep the discovery file outside shared projects and source control. Use its **path**, not its contents, in the client configuration. It contains a credential authorizing access to that local process; do not paste the token into a configuration example or screenshot.

The final installed MSIX must have its actual launch, discovery-file location, permissions, and restart behavior verified before its setup instructions are approved. This executable example does not establish MSIX compatibility.

## Configure a local Codex client

Codex supports stdio servers in a `[mcp_servers.<name>]` table. Edit the appropriate configuration deliberately, preserving other entries. Do not replace the entire configuration file. This example contains paths you must replace:

```toml
[mcp_servers.yuntu]
command = 'C:\Path\To\python.exe'
args = ['-B', 'C:\Path\To\yuntu-releases\integrations\mcp\editor-mcp.py', '--info', 'C:\Path\To\private\editor-info.json']
```

Use your actual Python executable, the complete bridge location, and the discovery file created above. Restart or reload the MCP connection using the client's supported workflow. Configuration and transport details are documented in [the official MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

In Codex, the user configuration is normally `~/.codex/config.toml`; a trusted project can use `.codex/config.toml`. Use the scope appropriate to your setup, preserve other entries, and replace every example path before enabling the server. The bridge reads its discovery credential at startup, so changing the editor process requires restarting the bridge, not just repeating a tool call.

For a different client, use its own stdio MCP configuration format. A JSON `mcpServers` example is not interchangeable with Codex TOML. Do not turn off the client's tool permissions to make the connection work.

## Install the user Skill

Install the complete `integrations/skills/yuntu-editor` folder using your client's supported skill mechanism. For a Codex repository-scoped installation, place it at `.agents/skills/yuntu-editor/` in the project where you work. Preserve any existing same-named skill rather than overwriting it silently. Current discovery locations are documented in [the official Skill guide](https://learn.chatgpt.com/docs/build-skills).

This does not change your client configuration automatically, connect the editor, or install a model. The user-facing skill is named `yuntu-editor`; `rust-ui-editor-dev` is an internal source-development skill and is not needed by users.

## Check the connection before editing

1. Confirm that the client lists `editor_read`, `editor_execute`, and `editor_prompts` from the intended server. A client may prefix their names.
2. Ask it to call `editor_read` with `method: editor.capabilities` and an empty parameter object.
3. Inspect the returned product identity, session, available methods, and active author. Ask it to read the current document using the actual parameters reported by that build.
4. Confirm the correct project and page, then request one small reversible edit.
5. Check the editor result, save status, and supported undo before continuing with a larger task.

Example request: "Use the Yuntu Editor skill. Inspect the active project first. On my settings page, align the Theme label with its field while keeping the current text. Re-read the result and tell me which checks you performed and which need the editor GUI."

Every write requires the current `expectedSessionId`, a unique external `requestId`, and the underlying operation's real revision, plan, owner, hash, or idempotency parameters. The client must not invent IDs or automatically retry an ambiguous write. Accepted background work must reach a matching successful terminal result before it is reported as complete.

## Current bridge coverage

The editor's native API and the MCP bridge have separate allowlists. A method must be in both the editor's capabilities and the MCP tool schema before the client can call it.

| Workflow | This bundled bridge |
| --- | --- |
| Inspect project, document, capabilities, and supported canvas state | Available through the corresponding `editor_read` methods when the installed editor supports them. |
| Plan/apply a page edit, inspect saved operation receipts, use supported history and review | Available through the allowlisted methods with their actual session and author guards. |
| Native `document.validate` | Not exposed by this bundle; do not invent a call or claim the native validation ran. |
| Pure artwork `preview.snapshot` / `preview.render` | Not exposed by this bundle. Canvas state/snapshots are a different surface. Use the editor's available GUI preview for visual inspection. |
| Standard JSON `project.export.*` | Not exposed by this bundle. Use the intended project's Export GUI. `codegen.export` is not a replacement for standard JSON export. |

The current integration is usable for its stated subset; complete MCP-driven validate/render/standard-export automation is not delivered here. Record this limit during final acceptance rather than bypassing the bridge. The bridge's own `serverInfo.version` is a component identifier, not the Yuntu Editor product version. This release's accepted application must identify as `1.0.0-beta`; an old installed beta cannot be relabeled as the accepted release.

## Restart and connection failures

If you only switch documents within the same editor process, re-read capabilities and the target author before writing. If the editor process restarts, use this full reconnection sequence:

1. Finish or preserve current work and close the intended editor normally. Stop the corresponding MCP connection in the client; do not terminate an unrelated editor process.
2. Start the editor with a new discovery filename using the launch example above, then open the intended project.
3. Update only the `--info` argument in that server's client configuration to the newly created discovery path. The UUID-based launch example produces a different path each time.
4. Restart the client-side MCP server so it loads the new process's credential. A tool retry alone keeps the old bridge credential and cannot reconnect it.
5. Read capabilities, verify the release identity and current project/document/session, and reassess the pending task before any new write.

Do not point the client at an arbitrary discovery file found by name, automatically replay a write that timed out, or copy the credential into configuration. A transport error after restart differs from a document-session change within a running process.

- A missing sibling helper means the bridge folder was copied incompletely.
- A missing discovery file means the editor has not created that selected connection file, or the client has the wrong path.
- `E_SESSION` means the observed target session changed; re-read and reassess rather than replaying the write.
- A method not reported by capabilities is not available in that build even if an older example mentions it.

For reports, record versions and sanitized error text using [Support](support.md). Do not include discovery JSON, tokens, or your full client configuration. These setup examples have not modified your client or contacted an external model.
