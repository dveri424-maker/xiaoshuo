当前小说正文创作已完成，项目进入去小说 AI 味阶段。

工作流由 Codex 作为项目经理，Claude 作为实际修改执行者。

## 创作环境启动

首先以全权限启动 codex cli:

```bash
codex --sandbox danger-full-access
```

### codex 给 claude 下达任务

在 Codex CLI 中，可以使用如下提示词分派并行任务给 claude：

```text
$codex-pm-claude 继续派发4个任务，分别启动4个 claude: "使用 novel-de-ai skill，并行修改 151-155 章, 156-160 章，161-165 章，166-170 章，要求上下文连贯，不要影响剧情，禁止任何比喻句与作者式总结。"修改完成后，由 codex 检查上下文连贯性并兜底修正，再中文提交本地仓库。
```

```text
以之前的工作形式，20章节分成4个任务，依次完成后续的300个章节的修改，每20章节的修改要求如下：$codex-pm-claude 继续派发4个任务，分别启动4个 claude: "使用 novel-de-ai skill，并行修改 151-155 章, 156-160 章，161-165 章，166-170章，要求上下文连贯，不要影响剧情，禁止任何比喻句与作者式总结。"修改完成后，由 codex 检查上下文连贯性并兜底修正，再中文提交本地仓库。
```

### 新版正文创作任务示例：
```text
$codex-pm-claude 派发4个任务，分别启动4个 Claude：“使用 活人感创作 skill 与 老嗷文风 skill，依据 新版设定/ 下的新版设定、卷纲、章节细纲和既有 新版正文/ 内容，分别创作或修改 新版正文 第001-005章、第006-010章、第011-015章、第016-020章。要求符合新版设定，上下文连贯，主角中心明确，案件/权力/物件收益落地；写作腔调必须贴主角意识流动，读感贴近老嗷文风；禁止比喻句、作者式总结、AI腔和剧情跳变。各 Claude 只处理自己负责的章节范围，不改其他章节。”完成后由 Codex 统一检查章节交界、设定一致性、禁用表达和 git diff，必要时兜底修正，再用中文提交本地仓库。

补充强制要求：
写作腔调强制要求：用贴合主角意识流动的第三人称写，旁白贴韦德本人，不贴作者；信息从感官、动作、误判、记忆触发和当场利害中自然进入；句式长短随主角心理变化，禁止使用冷硬短句堆酷感。

所有 Claude 写作前必须额外读取并执行 `新版设定/新版正文轻松爽感与老嗷读感校准.md`。该文档是本轮正文创作的读感校准必读项，不能只按 `老嗷文风` skill 的通用规则写。

写作时重点落实：读者先获得主角、工资箱案主脊梁、发现型强、动作化穿越、银星异常早露晚解且不直接替主角给答案、物件四连问、硬场面里的坏笑。不得把这些规则写成正文打卡表，必须落实到动作、对白、站位、物件归属、旁人行为变化和章末可见后果。

每个 Claude 在正式写正文前，先用 5 条说明本章节范围将如何落实：1. 如何让读者先获得韦德；2. 哪个硬物件过四连问；3. 哪个场面体现发现型强；4. 银星异常如何保留怪味但不替主角破案；5. 哪个场面提供硬场面里的坏笑。写完后按同一口径自检。

Codex 统一检查时，必须对照 `新版设定/新版正文轻松爽感与老嗷读感校准.md` 检查是否仍有冷硬装感、酷哥摆拍、连续证据解释、工资箱案被挤成背景、银星眼替代刑警经验、物件只服务功能、缺少坏笑/狼狈/街面反馈等问题；必要时兜底修正。
```

### 新版正文腔调与句式修改任务示例：
```text
让 Codex 并行派发 4 个 worker 子任务，分别处理新版正文的 4 个连续章节段。所有 worker 必须先读取：

  - 新版正文/第001章-银矿街上的工资箱.md
  - .claude/skills/老嗷文风/SKILL.md
  - .claude/skills/活人感创作/SKILL.md
  - 新版设定/README.md 指定的设定文档
  - 自己负责章节的前后一章用于衔接

  任务目标：只改正文腔调与句式，让负责章节尽量贴近第一章的阅读口感。重点不是新增情节，而是统一成第一章那种贴主角意识流动的第三人称：旁白贴韦德本人，不贴作者；句子长短随他的疼痛、困惑、误判、刑警经验、临场判断和当场利害自然变化。

  强制要求：
  - 保留现有剧情、线索、物件、人物、章末钩子和章节收益，不擅自新增支线。
  - 信息从感官、动作、证物、记忆触发、误判和旁人反应进入。
  - 对话要有活人开口的停顿、试探、顶嘴、改口、怂意和现场反应。
  - 禁止出戏比喻、作者式总结、AI腔、剧情跳变、冷硬短句堆酷感。
  - 禁止高频短句短词，尤其避免“名词。名词。判断。”式装感。
  - 银星异常只能早露晚解、催促韦德看证据，不能替主角给答案；禁止写成“银星告诉他/没有告诉他”这种规则说明。
  - 每个 worker 只改自己负责章节，不改其他文件。

  完成后每个 worker 列出改动文件和自检结果。

  最后由 Codex 主进程统一检查：
  - 是否真贴近第一章腔调与句式；
  - 是否仍有出戏比喻、作者总结、AI腔、冷硬短句；
  - 是否有“银星告诉他/没有告诉他”式说明腔；
  - 章节交界是否顺；
  - 设定、人物、物件、案件收益是否被改乱；
  - git diff 和空白检查是否通过。

  必要时由 Codex 主进程兜底修正，再用中文提交本地仓库。

```


### codex 与 claude 讨论任务
在 Codex CLI 中，可以使用以下方式让 codex 与 claude 实现讨论：

```text
  $codex-pm-claude 使用“多次 Claude 进程 + 同一个临时讨论文件”的方式，与 Claude 做三轮讨论。任务结束后删除临时讨论文件。

  讨论主题：
  【这里写你的主题】

  流程要求：
  1. Codex 先在临时文件中写入任务背景、Codex 初始观点和需要 Claude 反驳的问题。
  2. 第一轮 Claude 读取临时文件，重点反驳 Codex 方案，指出不爽、不稳、不合理、读者可能不买账的地方。
  3. Codex 读取 Claude 反馈后，把接受点、拒绝点、修订方案追加到同一个临时文件。
  4. 第二轮 Claude 读取临时文件，对 Codex 修订方案做二审，继续挑问题并给替代建议。
  5. Codex 再次追加最终判断：哪些采纳、哪些不采纳、最终方案是什么。
  6. 如有必要，第三轮 Claude 只检查最终方案是否还有明显漏洞。
  7. Codex 最后输出：讨论摘要、分歧点、采纳点、最终定稿，并删除临时讨论文件。

  限制：
  - 临时讨论文件只用于协作讨论,任务完成后删除
  - 最终由 Codex 负责判断和落地。

  讨论完成后，由 Codex 根据最终定稿修改/新建正式设定文档，并检查 git diff, 再用中文提交本地仓库。
```

或者简化版本讨论提示词：
```text
$codex-pm-claude 使用“多次 Claude 进程 + 同一个临时讨论文件”的方式，与 Claude 做三轮讨论。任务结束后删除临时讨论文件。讨论主题：【这里写你的主题】，第一轮 claude 反驳 codex 初稿，第二轮 claude 二审 codex 修订，第三轮 claude 查漏。最后 codex 输出分歧、采纳点和最终定稿。检查 git diff, 再中文提交本地仓库。
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
python3 -m playwright install chromium
```

### 首次登录番茄后台

```bash
python3 fanqie_draft_upload/fanqie_publish_browser.py login
```

脚本会打开浏览器。请手动完成番茄作者后台登录、验证码、短信或滑块验证。

### 生成或刷新章节台账

```bash
python3 fanqie_draft_upload/fanqie_prepare_manifest.py
```

默认读取根目录 `正文/`，生成：

```text
fanqie_draft_upload/data/fanqie_publish_state.json
```

如果某章已标记为 `draft_saved`，但本地正文 hash 已变化，脚本会停止并要求先人工确认远端草稿，避免覆盖不明状态。

### 检查后台页面

```bash
python3 fanqie_draft_upload/fanqie_publish_browser.py check
```

用于确认脚本能进入对应作品的章节管理/草稿箱页面。

### 审核待上传章节

```bash
python3 fanqie_draft_upload/fanqie_publish_browser.py audit
```

该命令只读取本地状态台账，输出各状态章节数量和章节范围，不会打开远端保存草稿。

### 保存章节到番茄草稿箱

```bash
python3 fanqie_draft_upload/fanqie_publish_browser.py save-drafts --confirm-save-drafts
```

常用范围参数：

```bash
python3 fanqie_draft_upload/fanqie_publish_browser.py save-drafts --start 1 --end 10 --confirm-save-drafts
python3 fanqie_draft_upload/fanqie_publish_browser.py save-drafts --only-chapter 12 --confirm-save-drafts
python3 fanqie_draft_upload/fanqie_publish_browser.py save-drafts --limit 3 --confirm-save-drafts
```

真正写入远端草稿箱前，脚本还会要求输入确认语，例如：

```text
SAVE FANQIE DRAFTS 1-10
```

确认语不匹配会取消操作。

### 中断后继续

```bash
python3 fanqie_draft_upload/fanqie_publish_browser.py resume --confirm-save-drafts
```

如果出现 `draft_saving` 遗留状态，应先人工确认番茄后台草稿是否已保存，再手动把对应章节状态改回 `pending` 或标记为 `draft_saved`。

### 日志、截图与本地状态

运行截图和错误截图默认保存在：

```text
fanqie_draft_upload/logs/
```

这些运行产物和本地状态台账已在 `.gitignore` 中忽略，不应提交到仓库。
