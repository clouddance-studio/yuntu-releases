# MCP 校验、预览渲染与标准导出增量验证

本轮按用户要求补齐 MCP 能力，改动保留在 `release/1.0.0-beta`，不合并、不推送、不发布。应用目标仍为 `1.0.0-beta / beta / 1.0.0.0`；MCP 组件独立升级为 **0.2.0**。

## 实现

- `editor_read` 新增 `document.validate`、`preview.snapshot`、`project.export.read`。
- 新增 `editor_output`，仅允许 `preview.render`、`job.cancel`、`project.export.settings`、`project.export.capture`、`project.export.configure`、`project.export.write`。必须提供观察到的 `expectedSessionId`、方法及原生参数。
- 作者修改仍只经原 `editor_execute` → `ai.execute`，不存在失败后降级直写。输出任务显式走编辑器已有公共输出 API，继续经过原生会话、revision、GUI／草稿、项目及配置 CAS、路径和原子发布门禁；不执行生成程序，也不伪造 AI 作者变化记录。
- 不开放无 jobId 作用域的 `project.export.cancel`，避免取消别的界面正在执行的任务。预览取消使用明确的 jobId。
- 读取 preview 的 `job.status` 与 export 的 `project.export.read` 分开处理。受理不等于完成；导出从 `job` 或 `recentJobs` 按 jobId 及 projectKey 匹配回执。
- Skill、四工具连接说明、英文完整工作流和最终交接说明已同步。

本轮没有修改或构建编辑器 Rust 业务代码。只在已有共享预算文件登记 `yuntu-releases/.local` 原生测试目录，沿用工作区 100 GB 总额；该源仓库配置改动留在本地，不夹带提交到发布仓库。

## 来源与版本

`source-provenance.json` 保留上游提交与 `baseFiles` 的真实身份，并单列本地增量及当前 `files` 摘要。桥接和协议测试不再声称与旧源提交逐字节一致；`editor-api.py` 仍是原始快照。准备检查同时核对当前文件长度、摘要和 MCP 组件声明版本。

**发现了实际构建不一致：** 已安装程序及现有开发可执行文件的 `--release-info` 返回 `1.0.1-beta / beta / 1.0.1.0`，不能替代本次固定目标。本轮原生验证只使用其中的已安装程序新建独立进程，记录真实身份为 `1.0.1-beta`；安装目录名称不能证明版本。该结果属于 API 集成证据，不是 `1.0.0-beta` 发行验收，也不验证真实外部客户端或模型。

因此最终发布检查新增必填 `--build-identity`，读取实际 release-profile 程序 `--release-info` 的 JSON，连同源码 `--editor-identity` 分别核对。现有 `1.0.1-beta` 身份即使搭配正确的源码配置仍会被拒绝。该记录不替代最终源提交、打包、签名或 Store 验收。

## 自动测试

- MCP 协议回归 **51 项通过**：保留原作者通道行为，新增只读调用、六个有限输出方法、源／项目／配置参数原样传递、旧 session 拒绝、能力缺失不降级、原生错误及超时不重试、未知方法／额外字段拒绝。
- 准备及交付检查 **17 项通过**：包含四工具 stdio 子进程握手、明确路由隔离、版本锁定、文件／事实边界，以及组件版本不能仅在清单重贴标签。
- Skill 官方 `quick_validate.py` 通过；仍使用临时校验环境，没有修改全局客户端配置。
- 普通准备及源码配置核对通过；提供真实 `1.0.1-beta` 构建身份时普通检查返回 1，严格检查返回 2。十一项发行门禁继续 pending，没有自动清关。

## 真实原生链路

使用全新 LOCALAPPDATA／APPDATA 和显式私有 discovery，在空隔离工作区通过实际 MCP stdio 进程新建测试项目，正常保存后完成 **11 项检查**：

1. 文档校验及同源 layout 预览快照成功。
2. 错误 revision 返回 `E_STALE_REVISION`。
3. 真实输出 480 × 200 PNG，并核对图像 SHA-256、尺寸与源身份。
4. `../outside.png` 返回 `E_OUTPUT_PATH`。
5. 同名 PNG 覆盖被 `E_OUTPUT_PATH` 拒绝，原文件保留。
6. 旧 session 在输出前被 `E_SESSION` 拒绝。
7. 明确 preview jobId 的取消通过新输出工具调用；本轮已越过发布边界，真实终态为 succeeded，按回执保留结果，没有谎称取消成功。
8. 错误项目清单摘要返回 `E_EXPORT_SOURCE_CHANGED`。
9. 设置读取、配置 CAS、capture、标准包 write 和同内容重复 write 全部走真实任务。每个包文件的长度／SHA-256 与清单一致，重复导出 `unchanged=true`，已保存作者字节不变。
10. 错误配置摘要使匹配 write 任务 failed，保留原配置和有效包。
11. 导出目录 `../escape` 的匹配任务 failed，无越界目录，包清单及作者保持原字节；输出结束后作者仍 clean。

测试报告将部分检查归为同一条目，详细原始回执保留在忽略目录 `.local/mcp-native/a8a8d47be1/case-1/verification.json`。原生 PNG 已用图像查看器实际检查：完整画板显示蓝色 “MCP native verification”，不是模拟绘图或 GUI 裁切。

- PNG SHA-256：`f4be732189611318a793965b6a39e5296122a10475ad780a61200f4f21068483`。
- 标准包 manifest SHA-256：`dd54e0d3a1b30c4b3eaba6bf64ca5bcbe82edb444c89fcb19db74038c162bfe3`。

原生验证脚本在一次重新打开页面时遇到只读 session 切换保护；已补齐有界只读重新读取，不重试写操作，随后在又一个空隔离实例完整复验通过。测试实例通过正常退出请求关闭，没有强杀或操作用户的验收实例。所有 discovery、profile、图片和生成测试包均忽略 Git，不作为最终发行归档。

## 未宣称完成

目标 `1.0.0-beta` 的实际安装包与外部客户端／模型完整联调、提前取消成功路径、真实用户 GUI 草稿阻断的物理输入验证、MSIX 安装及升级、域名和用户整体审阅仍需后续验收。原生现有门禁本轮未修改，不能用接口透传／模拟错误回归替代这些独立验收。
