# Yuntu Editor

**Build with AI. Review precisely. Generate your way.**

Yuntu Editor is a visual UI workspace for Windows that connects product ideas, design, AI-assisted editing, review, and code generation around the same local project. It is built for independent developers and small teams who want to refine an interface visually and bring the result into their own development workflow.

Connect an external AI client, see changes in the editor, attach review comments to specific elements, and use structured JSON with a generator that fits your project.

> **Release preparation:** Final acceptance and release-channel checks are in progress. This repository does not yet provide an editor installer or a Microsoft Store download link. The company website domain is still under review. The capabilities below describe the current development beta, not a published release.

## From an idea to an implementation

1. **Design the interface.** Build pages, arrange elements, add local assets, and create prototypes for supported interactions.
2. **Work with AI.** Use a connected external AI client to inspect and edit the project while viewing the results in Yuntu.
3. **Review specific elements.** Keep feedback attached to its target, guide the next revision, and compare the changes.
4. **Show the process.** Preview supported interactions, create animations, and export supported animation or recording workflows to video.
5. **Generate for your project.** Export versioned JSON and mappings, then use an optional official Web exporter or your own generation program.

## What the current beta supports

| Area | Current capabilities |
| --- | --- |
| Visual editing | Pages with text, buttons, images, and containers; layout and geometry controls; layers, selection, rulers, and guides. |
| Local projects | Project navigation, page thumbnails, local assets organized into directories, asset specifications, and automatic saving with recovery support. |
| Prototypes and preview | Prototype components and navigation, screenshot overlays, and previews of supported page interactions. Preview behavior depends on the controls and actions configured. |
| AI-assisted editing | External MCP connections, visual before-and-after comparisons, command details, and selective undo for supported changes. A separate observation window can show the work while you use your AI client. |
| Precise review | Comments associated with specific objects, review rounds, object navigation, and read-only review history. |
| Appearance | Fonts, styles, project theme settings, and supported visual effects, including shadows, glows, and layer blur. Support varies by document type and export target. |
| Animation and video | Keyframe animation for position and opacity, animation preview, and MP4 export for supported saved animations and editor recordings. |
| Developer handoff | Versioned JSON export packages, source mappings, project-level and global generator registration, and an optional React / TypeScript Web exporter. |

The editor includes an English interface and light and dark themes.

## AI stays connected to the real project

AI conversations take place in your connected external client. Yuntu provides MCP access to supported editor operations and shows their effects on the project. You can inspect command changes, compare earlier and later states, and selectively undo supported edits.

A compatible external client, connection setup, and access to an AI model are required for AI-assisted workflows. Model access and any provider charges are handled separately from the editor.

Review comments provide specific context for the next revision. Object navigation and review history help you check whether a change addresses the feedback.

## Use your own generation workflow

Yuntu separates editable project documents from the JSON packages used for developer handoff:

- **Editable documents:** `.yt` files hold authoring content; standalone themes use `.thme` files.
- **Export packages:** Versioned JSON describes supported UI content, source mappings, and required assets for downstream tools.
- **Generation programs:** Register a generator for one project or for reuse across projects, configure it, and explicitly run it against the exported input.

The JSON format is Yuntu's own versioned exchange format. The current implementation supports multiple format versions, and the selected version determines which content can be exported. The JSON export works independently of the optional official Web exporter.

The official Web exporter produces React / TypeScript output for a supported subset of UI content. Your own generator can target another framework or component system, subject to the information available in the export format. Generated output still needs integration with your application's business logic and validation in its target environment.

## Current scope and limitations

- **Windows x64 is the current validation target.** macOS and browser-based editor support remain future work.
- **Preview and export coverage varies.** Some controls, effects, media features, and document combinations are not supported by every preview or generator. Unsupported project content is reported during export; complete visual or behavioral parity across targets is not guaranteed.
- **Export coverage is still expanding.** Current JSON export includes supported pages, local static component projects, and a limited page-plus-animation workflow. It does not yet cover every project document type. Complete official Android and iOS generators are outside the current first-release scope.
- **Media preview has limits.** Some supported video previews are silent, and exported captions may not appear in the editor's playback view.
- **Online services are still in preparation.** Production account services, subscriptions, online feedback submission, and trusted update delivery are not presented here as available features. The current workflow centers on local projects; hosted team collaboration and cloud project storage are outside this beta's scope.

This is a development beta. Wider device testing, external AI workflow testing, and release validation are ongoing.

## Downloads and documentation

Microsoft Store is the planned primary channel for Windows installation and updates. A verified Store link, system requirements, and installation instructions will be added when a public release is ready.

English is the primary language for this repository and its release materials. Read the [installation and Release usage guide](docs/guides/installing-a-release.md), [first-project walkthrough](docs/guides/getting-started.md), [Skill and MCP setup](docs/guides/ai-mcp.md), and [FAQ](docs/guides/faq.md). These are preparation materials awaiting final package verification. Real release screenshots, editable examples, public JSON specifications, and generator tutorials remain follow-up work. See the [documentation index](docs/README.md) and [release preparation entry](docs/release/README.md).

## About this repository and licensing

This repository is intended for Yuntu Editor release information, documentation, and distributable examples. The editor's application source code is maintained separately.

Editor usage terms and reuse permissions for examples and generators will be provided with their respective releases. Third-party components retain their own licenses.
