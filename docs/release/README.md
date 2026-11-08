# Yuntu Editor release preparation

The [1.0.0-beta GitHub prerelease](1.0.0-beta/README.md) is published, with its exact [manifest](1.0.0-beta/release-manifest.json) and [checksums](1.0.0-beta/SHA256SUMS.txt). The owner confirmed installation acceptance and approved integration into `main`; the reviewed release materials and download homepage are now on `main`. Website and Store readiness remain separate pending work.

## Release identity and future changes

The published release is fixed at **1.0.0-beta**, channel **beta**, Windows file version **1.0.0.0**. Its release branch is `release/1.0.0-beta`, and its tag is `v1.0.0-beta`. The original installer and matching build identity have been verified and archived. Keep published artifact bytes and their recorded identities intact. Future pushes, releases, attachment changes, and Store submissions require the corresponding explicit user authorization; the completed publication does not authorize later work automatically.

Start with these materials:

1. [Release usage](../guides/installing-a-release.md): how users identify, install, verify, update, and remove a release.
2. [First project](../guides/getting-started.md) and [FAQ](../guides/faq.md).
3. [Skill and MCP setup](../guides/ai-mcp.md): the user-facing skill, local bridge, connection configuration, and checks.
4. [English Store copy](store-listing.en.json) and [capture plan](screenshots.md).
5. [Launch handoff](launch-handoff.md): final acceptance inputs, MSIX packaging, legal and support facts, artifact storage, and publication order.
6. [Repository boundaries](repository-boundaries.md): why no additional Git repository is required now.
7. [Readiness data](readiness.json): pending gates remain explicit; documentation checks do not clear them.
8. [Local preparation verification](preparation-verification.md): completed checks and their limits.
9. [Full branch review](review-2026-11-08.md): corrected Skill/MCP scope, restart instructions, version locking, and file checks.
10. [MCP validation, preview, and export](../guides/mcp-validation-preview-export.md): bridge 0.2.0 output jobs and completion evidence.
11. [Native MCP output verification](mcp-output-verification-2026-11-08.md): actual PNG/export results, refusals, version mismatch, and remaining release gates.

## Local checks

From the repository root, with Python 3.11+ available for the preparation checker:

```powershell
python -B scripts/check_preparation.py
python -B -m unittest discover -s scripts -p 'test_*.py'
python -B integrations/mcp/test-editor-mcp.py
```

The first command checks the preparation files, local links, English copy, and bundled bridge identities. It reports pending release gates while allowing valid preparation work to pass. To require a complete release record:

```powershell
python -B scripts/check_preparation.py --require-ready --editor-identity '..\rust-ui-editor\packaging\release.json' --build-identity '.local\accepted-build-identity.json'
```

This must fail while any release gate remains pending. None of these commands builds the editor, modifies a running editor, copies a final package, changes client configuration, or publishes anything.

`--build-identity` must contain the actual release executable's `--release-info` JSON, not a copy of `packaging/release.json`. It must identify a release-profile Yuntu Editor at `1.0.0-beta / beta / 1.0.0.0`. Use a deliberate, verified executable path and save its output as UTF-8 without BOM. The historical integration-test program reports `1.0.1-beta` and is rejected as the target. The newly archived, hash-matched build reports the correct `1.0.0-beta`; its captured identity is under the local archive as `build-identity.json`. This guard does not certify the installer or turn a metadata file into package acceptance.

The optional `scripts/verify_mcp_native.py --info <explicit-private-file> --workspace <new-.local-test-directory>` creates a tiny project in a separately launched, isolated editor. It rejects nonempty editor workspaces and existing case projects. It validates, snapshots, renders, configures/captures/writes/reuses standard JSON, checks every package hash, tests conflicts and path refusals, and preserves the saved author. It is not run by ordinary unit-test discovery. Read its captured actual editor identity before using its results; native API integration is not final release or external-model acceptance.

The script tests include a real stdio subprocess connected only to a synthetic loopback API server. They do not connect to a native editor or prove final installed-client compatibility. Artifact fixtures contain synthetic bytes in temporary test directories; a checksum or file extension is not Store package certification. Required Store facts cannot be dropped from the record, and final assets must remain inside the exact `1.0.0-beta/windows-x64` archive with matching hashes and an MSIX submission package for the selected route.

## Artifact handoff

After final acceptance and an actual packaging task, archive the exact approved files under `releases/1.0.0-beta/windows-x64/` in this repository. This directory is ignored by Git. Do not create empty release directories or substitute a development executable for a verified installer.

Keep the installer or Store submission package, checksums, English notes, third-party notices, and a release record identifying the editor source commit, build identity, package identity, validation evidence, and every distributed file. GitHub's automatically generated source archive is the documentation repository, not an editor installer.
