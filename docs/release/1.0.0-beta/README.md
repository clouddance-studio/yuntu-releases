# Yuntu Editor 1.0.0-beta

Windows x64 beta · Application version **1.0.0-beta** · Windows file version **1.0.0.0**

This is a GitHub prerelease for evaluation. Installation acceptance was confirmed by the release owner on November 8, 2026. Microsoft Store submission and the company website remain separate work; this release does not require the planned website domain.

## Downloads

Download assets from [this release](https://github.com/clouddance-studio/yuntu-releases/releases/tag/v1.0.0-beta):

- **Yuntu-Editor-1.0.0-beta-windows-x64-setup.exe** — Windows x64 installer, 115,935,744 bytes.
- **Yuntu-MCP-0.2.0.zip** — the separate four-tool stdio bridge, helper, provenance record, and protocol tests. Python is required separately; verification used Python 3.12.14.
- **Yuntu-Skill-1.0.0-beta.zip** — the complete `yuntu-editor` user Skill folder. Extract it before using your client's skill installation mechanism.
- **SHA256SUMS.txt** — SHA-256 values for all three downloads.
- **release-manifest.json** — application/build identities, original package hashes, integration component identities, and verification boundaries.

GitHub's automatic source archives contain this documentation and integration repository, not the editor application. This prerelease does not provide a Microsoft Store MSIX package or promise Store-managed updates.

## Install and check

1. Back up existing projects and close the editor before installing the beta.
2. Download the installer and `SHA256SUMS.txt` from the release above. Run `Get-FileHash -LiteralPath '.\Yuntu-Editor-1.0.0-beta-windows-x64-setup.exe' -Algorithm SHA256` and compare the complete value.
3. The exact installer SHA-256 is `0066cdea9412ea01197fc311273ec9620324da704dae7522cb0a1e406509c850`.
4. This installer is **not Authenticode signed**. Its PE metadata identifies Yuntu Editor at `1.0.0-beta / 1.0.0.0`; a matching checksum verifies file bytes, not publisher identity. Evaluate it under your normal Windows security policy.
5. Use the installer's English interface and selected installation directory. On first launch, confirm the application version and try a separate test project before opening important work.

The package declares Windows 10 as its minimum and contains a .NET Framework 4.x WPF installer. Broad Windows build, hardware, clean-upgrade, and downgrade coverage has not been certified by this repository. See the [installation guide](../../guides/installing-a-release.md), [first project](../../guides/getting-started.md), and [support guidance](../../guides/support.md).

## Product and integration scope

Yuntu provides local visual UI editing, AI-client integration, object-specific review, supported previews and animation workflows, and versioned JSON handoff. The package includes official Web, WeChat Mini Program, Android, and iOS exporter packages; their inclusion does not establish runtime or visual parity across all targets. Export format and generator versions are independent of the application version.

The installer contains its own bridge snapshot identifying as **0.1.0**. The separately downloadable MCP **0.2.0** is a different, hash-pinned component: it exposes `editor_read`, `editor_execute`, `editor_prompts`, and `editor_output`, including validation, PNG rendering, and standard JSON output jobs. To follow this repository's four-tool instructions, configure the client to run the extracted **0.2.0** script and its matching sibling helper; do not mix files from the two bridge snapshots or assume the installer installs the separate bundle.

Read [Skill/MCP setup](../../guides/ai-mcp.md) and the [validation/render/export workflow](../../guides/mcp-validation-preview-export.md). The bridge and Skill do not install an AI client or provide model access. They do not modify client configuration automatically.

## Verification and limits

- The original installer, its checksum sidecar, package report, and payload manifest were archived unchanged. All 1,060 staged payload files (404,753,888 bytes) were independently checked against the package report.
- The matching release executable's SHA-256 and actual `--release-info` agree with the fixed application identity. The installer PE metadata agrees as well.
- Installation acceptance was supplied by the release owner. Device details and individual installation test cases were not supplied; this repository does not claim a repeated automated installation or upgrade matrix.
- MCP 0.2.0 has 51 passing protocol regressions and the repository has 17 passing preparation/delivery tests. The previous 11-check native render/export run used an accurately recorded `1.0.1-beta` program; that historical evidence is not relabeled as validation of this installer. External client/model pairing with this final package remains unverified here.
- This packaging run did not repeat the full editor test suite or four-target generate/build/runtime acceptance. Earlier results retain their original candidate identities.
- The source handoff retains a known DX12 native JavaScript preview shutdown case: the child/public preview closed, but the main program exceeded a 45-second quit window before exiting later, without an exit-zero receipt. Packaging does not claim to fix it.

Keep `.yt` documents, `.thme` themes, manifests, and assets together. Back up before beta upgrades; an older editor may not read files saved by a newer one. The website, production account services, support inbox, and Store listing are not announced as available endpoints by this release.

## Provenance and notices

Editor source commit: `6f24c642e08ac6fb8feb7b7679d204a0c75d5880`. Build profile: `release`; target: `x86_64-pc-windows-gnullvm`. Build identity SHA-256: `4d95546b6a9cf2c6b951e00d5ed96db65534fdb43d89ba26f8ed611824065a0a`.

The installer contains third-party notices under `resources/licenses/`, font licenses under `resources/font-packs/common-ui/licenses/`, and FFmpeg license/source information under `resources/tools/ffmpeg/`. Those materials retain their respective terms. This documentation does not grant a new blanket license to the editor or integration files. Store legal/support requirements remain separate release gates.
