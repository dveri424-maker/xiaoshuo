当前小说正文创作已完成，项目进入去小说 AI 味阶段。

工作流由 Codex 作为项目经理，Claude 作为实际修改执行者。

首先以全权限启动 codex cli:

codex --sandbox danger-full-access
codex 全功能权限启动

在 Codex CLI 中，可以使用如下提示词分派并行任务：

```text
$codex-pm-claude 继续派发4个任务，分别启动4个 claude: "使用 novel-de-ai skill，并行修改 91-95 章, 96-100 章，101-105 章，106-110 章，要求上下文连贯，不要影响剧情，禁止任何比喻句与作者式总结。"修改完成后，由 codex 检查上下文连贯性并兜底修正，再提交本地仓库。
```

通过上述流程，可以让 Claude 先完成分段审查与修改，再由 Codex 统一检查工具残留、禁用表达、章节交界和剧情连贯性，最后提交本地仓库。
