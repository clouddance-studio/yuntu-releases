# Yuntu Editor FAQ

## Is this already a public release?

No public installer or Store listing is announced by these preparation materials. Final editor acceptance and channel preparation are separate tasks. The company website domain is still under review.

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

Standard JSON is a versioned UI handoff. The optional official Web exporter supports a subset of content; another generator can target a different development workflow. Application data, services, business logic, and deployment still need integration and testing. Complete official Android and iOS generators are outside the current first-release scope.

## Are history and recovery a backup?

They help with supported workflows but have limits and do not replace backups. Finish edits, wait for saving, and keep the complete project and resources together. Do not delete profile or recovery files to resolve a save error.

## Will this repository update my editor automatically?

No. A future Store MSIX release and a separately downloaded EXE have different update paths. Follow [the release usage guide](installing-a-release.md) and the specific release notes.

## Where do I report a problem?

Use [Support](support.md) to prepare a minimal, sanitized report. A verified direct support endpoint will be supplied with the actual release; none is invented from the company domain.
