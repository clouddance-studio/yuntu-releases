# Your first Yuntu Editor project

Start with the [1.0.0-beta Windows x64 release](../release/1.0.0-beta/README.md). This beta walkthrough covers a small local editing workflow; it does not establish compatibility on every Windows device. Check the release notes for package requirements, known issues, and verification limits.

1. Install the beta release using [its installation instructions](installing-a-release.md), then check its version in About.
2. Create a local project in a directory you control. Use its add-page action if it does not already have an initial page.
3. Add a container, a heading, a short description, and a button. Name the important elements so that you can identify them in review and AI instructions.
4. Adjust layout and text properties. Finish pending field input or Apply actions and wait for saving to complete.
5. Reopen the saved page and check the content. A recovery draft or an exported copy is not proof that the source project was saved.
6. Preview the page. Check text, images, clipping, and the supported actions you configured; a visual button alone does not implement application behavior.
7. Add a review comment to a specific element. Check that the comment belongs to the intended review round. Saving feedback does not automatically change the design.
8. Export standard JSON from the intended project's export action. Wait for a completed result and keep the package together. Generated code requires a separately enabled, compatible generator.

The expected result is a saved, reopenable local project and a completed JSON handoff. Building or deploying an application is a separate development step.

AI assistance is optional. To connect a compatible external client, follow [Skill and MCP setup](ai-mcp.md). For limitations and failure reporting, see [FAQ](faq.md) and [Support](support.md).
