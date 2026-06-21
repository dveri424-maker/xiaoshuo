当前小说正文创作已完成，项目进入去小说 AI 味阶段。

工作流由 Codex 作为项目经理，Claude 作为实际修改执行者。

首先以全权限启动 codex cli:

```bash
codex --sandbox danger-full-access
```

在 Codex CLI 中，可以使用如下提示词分派并行任务：

```text
$codex-pm-claude 继续派发4个任务，分别启动4个 claude: "使用 novel-de-ai skill，并行修改 151-155 章, 156-160 章，161-165 章，166-170 章，要求上下文连贯，不要影响剧情，禁止任何比喻句与作者式总结。"修改完成后，由 codex 检查上下文连贯性并兜底修正，再提交本地仓库。
```

```text
以之前的工作形式，20章节分成4个任务，依次完成后续的300个章节的修改，每20章节的修改要求如下：$codex-pm-claude 继续派发4个任务，分别启动4个 claude: "使用 novel-de-ai skill，并行修改 151-155 章, 156-160 章，161-165 章，166-170章，要求上下文连贯，不要影响剧情，禁止任何比喻句与作者式总结。"修改完成后，由 codex 检查上下文连贯性并兜底修正，再提交本地仓库。
```

通过上述流程，可以让 Claude 先完成分段审查与修改，再由 Codex 统一检查工具残留、禁用表达、章节交界和剧情连贯性，最后提交本地仓库。

## 番茄草稿箱上传工具

本项目提供一个浏览器自动化工具，用于把根目录 `正文/` 下的正文章节保存到番茄小说作者后台草稿箱。

功能边界：

- 只保存草稿，不发布、不定时发布、不提交审核。
- 不在项目中保存账号、密码、cookie 或 token。
- 浏览器登录状态保存在仓库外：`/home/weishida/.local/share/xiaoshuo/fanqie-browser-profile`。
- 工具只读取 `正文/` 并写入本地状态台账，不移动、不改写小说创作文件。

相关文件集中在：

```text
fanqie_draft_upload/
├── fanqie_prepare_manifest.py      # 生成/刷新章节状态台账
├── fanqie_publish_browser.py       # 打开番茄后台并保存草稿
├── fanqie_publish.yaml             # 番茄后台地址、选择器、路径与安全配置
├── requirements.txt                # Playwright/PyYAML 依赖
└── data/fanqie_publish_state.json  # 本地章节状态台账，不提交
```

### 安装依赖

```bash
pip install -r fanqie_draft_upload/requirements.txt
python -m playwright install chromium
```

### 首次登录番茄后台

```bash
python fanqie_draft_upload/fanqie_publish_browser.py login
```

脚本会打开浏览器。请手动完成番茄作者后台登录、验证码、短信或滑块验证。

### 生成或刷新章节台账

```bash
python fanqie_draft_upload/fanqie_prepare_manifest.py
```

默认读取根目录 `正文/`，生成：

```text
fanqie_draft_upload/data/fanqie_publish_state.json
```

如果某章已标记为 `draft_saved`，但本地正文 hash 已变化，脚本会停止并要求先人工确认远端草稿，避免覆盖不明状态。

### 检查后台页面

```bash
python fanqie_draft_upload/fanqie_publish_browser.py check
```

用于确认脚本能进入对应作品的章节管理/草稿箱页面。

### 审核待上传章节

```bash
python fanqie_draft_upload/fanqie_publish_browser.py audit
```

该命令只读取本地状态台账，输出各状态章节数量和章节范围，不会打开远端保存草稿。

### 保存章节到番茄草稿箱

```bash
python fanqie_draft_upload/fanqie_publish_browser.py save-drafts --confirm-save-drafts
```

常用范围参数：

```bash
python fanqie_draft_upload/fanqie_publish_browser.py save-drafts --start 1 --end 10 --confirm-save-drafts
python fanqie_draft_upload/fanqie_publish_browser.py save-drafts --only-chapter 12 --confirm-save-drafts
python fanqie_draft_upload/fanqie_publish_browser.py save-drafts --limit 3 --confirm-save-drafts
```

真正写入远端草稿箱前，脚本还会要求输入确认语，例如：

```text
SAVE FANQIE DRAFTS 1-10
```

确认语不匹配会取消操作。

### 中断后继续

```bash
python fanqie_draft_upload/fanqie_publish_browser.py resume --confirm-save-drafts
```

如果出现 `draft_saving` 遗留状态，应先人工确认番茄后台草稿是否已保存，再手动把对应章节状态改回 `pending` 或标记为 `draft_saved`。

### 日志、截图与本地状态

运行截图和错误截图默认保存在：

```text
fanqie_draft_upload/logs/
```

这些运行产物和本地状态台账已在 `.gitignore` 中忽略，不应提交到仓库。
