# Installing and using a Yuntu Editor release

**GitHub beta:** the [1.0.0-beta release](https://github.com/clouddance-studio/yuntu-releases/releases/tag/v1.0.0-beta) provides the Windows x64 EXE installer. See its [release notes](../release/1.0.0-beta/README.md) for exact checksums, unsigned status, and owner-confirmed installation acceptance. Microsoft Store/MSIX and detailed requirements/upgrade coverage remain separate work. The website is not yet available as a public installation or support endpoint.

This release is fixed at **1.0.0-beta**, channel **beta**, Windows file version **1.0.0.0**. An installer filename, an older internal beta, or the MCP bridge's component version is not a substitute for that accepted application identity.

## Choose the correct download

For 1.0.0-beta, download the Windows x64 EXE from the [GitHub release](https://github.com/clouddance-studio/yuntu-releases/releases/tag/v1.0.0-beta). Check the exact filename and SHA-256 against its release record.

Microsoft Store/MSIX remains a planned channel. When a verified listing becomes available, check its publisher, architecture, supported Windows version, and release channel. The current GitHub beta is a prerelease, and its EXE does not provide Store-managed updates.

A GitHub Release's automatically generated **Source code** ZIP or tarball contains this documentation repository. It is not an editor installer. Skill and MCP files also do not contain the editor application or provide model access.

## Check a separately downloaded installer

Use the checksum published for that exact file. For example, after replacing the filename with your download:

```powershell
Get-FileHash -LiteralPath '.\Yuntu-Editor-1.0.0-beta-windows-x64-setup.exe' -Algorithm SHA256
```

Compare the entire result with the release's SHA-256 record. A mismatch means the file is not the one described by that record. A matching checksum checks bytes; it does not by itself authenticate a publisher.

For a separately distributed EXE, you can inspect its signature:

```powershell
Get-AuthenticodeSignature -LiteralPath '.\Yuntu-Editor-1.0.0-beta-windows-x64-setup.exe'
```

The 1.0.0-beta EXE is not Authenticode signed and has no Authenticode-verified publisher identity. The signature check should report `NotSigned`. A matching SHA-256 checksum verifies the file bytes, not the publisher. Follow your normal Windows security policy. A future Store MSIX release will use the Store's package validation workflow.

## First launch

Open Yuntu Editor and check the version in About against the release notes. Choose English if needed. Use a separate test project to check that the program can create a page, save it, reopen it, preview supported content, and export standard JSON.

Keep your project directory somewhere you control. Editable documents normally use `.yt`; standalone themes use `.thme`. Preserve the project manifest, related documents, and assets together. See [the first-project walkthrough](getting-started.md).

## Update safely

Back up your saved projects before a beta update. Read the new release's compatibility and known-issue sections before opening important work.

The planned Store MSIX channel uses Store-managed updates once the real package and channel have been validated. Do not assume that an EXE obtained through a Store listing or GitHub has the same update mechanism. Separate installer updates require their own verified instructions. No automatic-update feed is published by this repository.

Keep the user Skill and MCP bundle paired with a tested editor version. Restart the editor connection and re-read its capabilities after an update. Do not keep using an old discovery credential or document session.

## Uninstall or return to an earlier version

Use the uninstall action provided by Windows or the actual installer. Save and close work first, and keep an independent backup of your projects. Do not manually delete profile or recovery folders to remove the application.

An older editor may not understand files saved by a newer build. A retained older installer is not a guarantee of downgrade compatibility; use a backup made before the update and consult that release's instructions.
