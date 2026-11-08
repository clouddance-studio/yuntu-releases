# Yuntu Editor release preparation

This is a local preparation branch, not a published release. The website domain has not completed review, final editor acceptance is still in progress, and no public download or Store URL is available here.

## Review this branch

The branch is `release/1.0.0-beta.3`, based on the currently observed product identity. The user confirmed that the main branch remains `main`; do not merge into it, push this branch, publish a GitHub Release, upload assets, or submit to Microsoft Store until the user has reviewed the complete result and explicitly authorized the relevant action. The branch name does not freeze the final application version.

Start with these materials:

1. [Release usage](../guides/installing-a-release.md): how users identify, install, verify, update, and remove a release.
2. [First project](../guides/getting-started.md) and [FAQ](../guides/faq.md).
3. [Skill and MCP setup](../guides/ai-mcp.md): the user-facing skill, local bridge, connection configuration, and checks.
4. [English Store copy](store-listing.en.json) and [capture plan](screenshots.md).
5. [Launch handoff](launch-handoff.md): final acceptance inputs, MSIX packaging, legal and support facts, artifact storage, and publication order.
6. [Repository boundaries](repository-boundaries.md): why no additional Git repository is required now.
7. [Readiness data](readiness.json): pending gates remain explicit; documentation checks do not clear them.
8. [Local preparation verification](preparation-verification.md): completed checks and their limits.

## Local checks

From the repository root, with Python 3.11+ available for the preparation checker:

```powershell
python -B scripts/check_preparation.py
python -B -m unittest discover -s scripts -p 'test_preparation.py'
python -B integrations/mcp/test-editor-mcp.py
```

The first command checks the preparation files, local links, English copy, and bundled bridge identities. It reports pending release gates while allowing valid preparation work to pass. To require a complete release record:

```powershell
python -B scripts/check_preparation.py --require-ready
```

This must fail while any release gate remains pending. None of these commands builds the editor, modifies a running editor, copies a final package, changes client configuration, or publishes anything.

## Artifact handoff

After final acceptance and an actual packaging task, archive the exact approved files under `releases/<product-version>/windows-x64/` in this repository. This directory is ignored by Git. Do not create empty release directories or substitute a development executable for a verified installer.

Keep the installer or Store submission package, checksums, English notes, third-party notices, and a release record identifying the editor source commit, build identity, package identity, validation evidence, and every distributed file. GitHub's automatically generated source archive is the documentation repository, not an editor installer.
