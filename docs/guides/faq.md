# Yuntu Editor FAQ

## Is this already a public release?

Yes. [Yuntu Editor 1.0.0-beta is available on GitHub](https://github.com/clouddance-studio/yuntu-releases/releases/tag/v1.0.0-beta) as a Windows x64 prerelease. Installation acceptance was confirmed by the release owner. Microsoft Store is not yet available, and the company website domain is still under review. See the [release notes](../release/1.0.0-beta/README.md) for checksums, the unsigned installer, known issues, and verification limits.

## Which platform is supported?

Windows x64 is the current validation target. Exact supported Windows builds, hardware, graphics requirements, and runtime dependencies must come from the accepted package's test results. macOS and browser-based editor releases are not announced here.

## Do I need AI access to edit a page?

Local visual editing does not require an AI connection. AI assistance uses a compatible external client and model access that you configure separately. Any provider charges are separate from the editor.

## What is the difference between the Skill and MCP?

The user Skill teaches an AI client how to work with a Yuntu project. MCP supplies the actual tools that read and edit a running local editor. Installing the Skill alone does not install or connect the editor. Installing the bridge alone does not provide a model or grant new permissions to your AI client.

The `rust-ui-editor-dev` skill is for maintaining the application source. The distributable `yuntu-editor` skill is for using the application; it does not instruct users to build Rust or obtain the private source repository.

## Are accounts, subscriptions, or cloud storage available?

Production account services, subscriptions, cloud project storage, and hosted team collaboration are not presented as available beta features. Planned regional quotas and Pro prices are not release entitlements. Actual account and offline behavior must be confirmed for the release you install.

## Does JSON export generate my whole application?

Standard JSON is a versioned UI handoff. The installer includes official Web, WeChat Mini Program, Android, and iOS exporter packages; support varies by format, content, and target. Package inclusion does not establish end-to-end validation of generated output on Android, iOS, or other target platforms. The optional Web exporter produces React / TypeScript for a supported subset. Application data, services, business logic, deployment, and target-specific validation still belong in your development workflow.

## Are history and recovery a backup?

They help with supported workflows but have limits and do not replace backups. Finish edits, wait for saving, and keep the complete project and resources together. Do not delete profile or recovery files to resolve a save error.

## Will this repository update my editor automatically?

No. A future Store MSIX release and a separately downloaded EXE have different update paths. Follow [the release usage guide](installing-a-release.md) and the specific release notes.

## Where do I report a problem?

Use [Support](support.md) to prepare a minimal, sanitized report. A verified direct support endpoint has not yet been announced; the published beta does not establish a working support inbox or website service.
