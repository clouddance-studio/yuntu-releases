# Yuntu Editor 1.0.0-beta Windows x64 ZIP

[**Download the Windows x64 ZIP**](https://github.com/clouddance-studio/yuntu-releases/releases/download/v1.0.0-beta/Yuntu-Editor-1.0.0-beta-windows-x64.zip) · [SHA-256](https://github.com/clouddance-studio/yuntu-releases/releases/download/v1.0.0-beta/Yuntu-Editor-1.0.0-beta-windows-x64.zip.sha256) · [ZIP manifest](https://github.com/clouddance-studio/yuntu-releases/releases/download/v1.0.0-beta/zip-package-manifest.json)

This ZIP is an additional asset for the [1.0.0-beta GitHub prerelease](https://github.com/clouddance-studio/yuntu-releases/releases/tag/v1.0.0-beta). The original EXE installer remains unchanged.

## Package identity

- Filename: `Yuntu-Editor-1.0.0-beta-windows-x64.zip`.
- Application: **1.0.0-beta**, channel **beta**, Windows file version **1.0.0.0**.
- Archive size: **161,788,355 bytes** (about 154 MiB).
- SHA-256: `f2e8bb73863c87c832e3674c89313f11c6aa7105f95eebe7aeedd6458461986d`.
- Application executable SHA-256: `fec08db6eaaf9745c7f08f48f90af2c7e4afc4b7ea81324f7babead9e835d28c`.
- Signature: **NotSigned**; no trusted Authenticode code-signing certificate is currently available for this beta.

The ZIP contains the original 1,060 staged payload files from the accepted installer, plus an English `README.txt`. It preserves the sibling DLL, runtime marker, fonts, official exporter packages, bundled MCP snapshot, third-party notices, and other runtime resources. The packaged application version and component versions are unchanged.

## Extract and run

1. Compare the complete ZIP SHA-256 with the checksum supplied alongside that exact attachment.
2. Extract the entire archive to a writable folder. Do not run the editor directly inside the compressed folder.
3. Keep `yuntu-editor.exe`, the sibling DLL, `payload-manifest.json`, and `resources/` together.
4. Run `yuntu-editor.exe`. If SmartScreen appears and you trust the official release, choose **More info**, then **Run anyway**. See the [unsigned beta instructions](../../guides/installing-a-release.md#windows-smartscreen).
5. Confirm **1.0.0-beta** in About and use a separate test project before opening important work.

The ZIP avoids running the installer; it does not provide installer-created shortcuts, file associations, or an uninstaller. Settings, recovery data, and runtime files may still be stored in the Windows user profile. This is not a self-contained portable profile. Back up projects separately before changing versions or deleting the extracted application folder.

Compressing the application does not add a digital signature or prevent warnings for the extracted EXE. Keep Windows protection enabled. A matching checksum confirms file bytes, not publisher identity or software safety.

## Verification scope

All 1,060 payload files were checked against the original package report before archiving and again after ZIP decompression. ZIP CRC checks passed. Running the extracted executable with `--release-info` from outside its application folder returned the fixed release identity. The extracted application is unsigned.

GUI workflows, a clean-machine compatibility matrix, and external AI client/model pairing have not been revalidated for this ZIP. Installation acceptance for the EXE is not represented as ZIP functional acceptance. Existing [release notes](README.md), requirements, licensing, and integration limits continue to apply.
