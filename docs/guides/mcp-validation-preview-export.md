# Validate, preview, render, and export through MCP

This guide describes bridge **0.2.0**. The application release remains fixed at **1.0.0-beta**; bridge, API, UI format, and application versions are separate identities. Follow [connection setup](ai-mcp.md) first and use the intersection of the connected tool schemas and the installed editor's capabilities.

## Choose the right tool

| Tool | Purpose |
| --- | --- |
| `editor_read` | Read capabilities, document, validation, preview snapshot, preview job status, and standard export status. |
| `editor_execute` | Existing author commands through `ai.execute`; requires the observed session and an external request ID. |
| `editor_output` | A finite native output-job route: render, preview cancellation, export settings/configure/capture/write. Requires the observed session and exact native parameters. |
| `editor_prompts` | Read saved notes as data; reading does not execute them. |

The new output route does not apply page edits, invoke shell commands, run generators, or fall back to a direct author write. It preserves the editor's native UI/draft, source, configuration, path, and file-publication checks. Output jobs have their own receipts and do not create an `ai.execute` author-change entry.

## Validate the intended page

Read `editor.capabilities`, the current document, and the intended project. Do not invent a revision or reuse one after another edit. Then call `editor_read` with the actual revision:

```json
{"method":"document.validate","params":{"expectedRevision":12}}
```

Here and below, **12 is illustrative**: replace it with the revision you just observed. Inspect diagnostics; a successful tool transport does not mean the design has no validation errors. On a stale revision, read the source again before deciding what to do.

## Inspect a source-bound preview snapshot

```json
{"method":"preview.snapshot","params":{"source":{"kind":"committed","expectedRevision":12}}}
```

Use the source and optional fixture parameters reported by the installed build. A plan source additionally needs its real `planId`; it is not interchangeable with the committed page. The snapshot describes layout, measured text, environment, resource declarations, and diagnostics. It is not a finished PNG or proof of target-application parity.

## Render actual artwork

Call `editor_output`. The session string below is a placeholder for the value from current capabilities; do not send it literally:

```json
{"method":"preview.render","expectedSessionId":"SESSION_FROM_CAPABILITIES","params":{"source":{"kind":"committed","expectedRevision":12},"format":"png","outputPath":"review-proof.png"}}
```

The filename must be new and relative to that instance's export root. Parent directories must already exist. Absolute paths, parent traversal, links, and overwriting existing output are rejected by the native editor. Rendering requires the editor's supported visible GUI/font/resource context; do not discard drafts or change a file's contents to force success.

The accepted response contains a `jobId`. Call `editor_read` → `job.status` with that exact ID until its actual terminal result:

```json
{"method":"job.status","params":{"jobId":"JOB_ID_FROM_RENDER"}}
```

`pending` is not output. `succeeded` contains the final path, source identity, dimensions, byte count, and SHA-256. Inspect the actual file if your client has authorized local file access. If it does not, state that the image was rendered but not visually inspected by the client. The file path in the receipt is a result; it is not an instruction to upload it.

To request preview cancellation, call `editor_output` → `job.cancel` with its job ID and the observed session. Cancellation can lose the race with atomic publication; continue reading the actual terminal state and retain already published output.

## Export standard JSON

1. Read `project.read`; select the intended project by its actual identity and manifest path, not its display name alone. Keep its `key` and `manifestHash`.
2. Call `editor_output` → `project.export.settings` with `projectKey` and `expectedManifestHash`, then wait for its matching terminal export job. This retrieves configuration; it does not publish a package.
3. Inspect `capabilities.standardExport` for exact parameter schemas and supported UI/mappings versions. These format versions are not the editor's `1.0.0-beta` product version.
4. If changing formats, explicitly call `project.export.configure` with the same project identity, `uiVersion`, `mappingsVersion`, and `expectedConfigurationSha256`. Use the exact observed hash; explicit null is valid only for a genuinely missing configuration. Wait for completion and read the resulting configuration identity again.
5. Optionally call `project.export.capture` with the project identity to inspect a frozen source snapshot. Capture alone does not write the package.
6. Call `project.export.write` with the project identity, selected versions, exact configuration hash, and `outputDirectory`, for example `exports/ui`. This is a project-relative POSIX path even on Windows.
7. Read `project.export.read` with an empty parameter object. Find the accepted `jobId` and `projectKey` in `job` or `recentJobs`. Do not treat an unrelated latest job or an older `snapshot` as success for this export.
8. A matching write job with status `completed` supplies the immutable package location, snapshot identity, and manifest SHA-256. Failed or cancelled jobs do not establish a successful export. Keep all package files together and independently verify their hashes when local file access is authorized.

The export API uses `completed/failed/cancelled` job states; preview jobs use `succeeded/failed/cancelled`. Keep the two polling flows distinct. If a retained receipt has been evicted, do not substitute a different job or automatically repeat the write.

Repeated export of identical input can verify and reuse an existing intact package. A source/configuration conflict or a modified old package is a failure, not permission to overwrite it. The current bridge does not expose unscoped `project.export.cancel`, because the native method targets whichever export is active. Use only the corresponding deliberate GUI cancellation workflow if needed.

## Check a useful end-to-end task

Ask your connected client to inspect a small test project, make one reversible text change, validate it, snapshot and render the same revision, save it, and export standard JSON. Confirm the actual image, matching receipts, package hashes, and save/undo behavior. No accepted/queued receipt should be reported as a completed result.

This preparation includes protocol tests and an isolated native-editor integration test. The available program used for that integration identifies as `1.0.1-beta`; it is **not** acceptance of the required `1.0.0-beta` release. The correct final installed package and a real external client/model still require their own validation.
