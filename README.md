# 《未知进化》创作工作区

末日生态进化科幻网文。主线从南京仙林校园灾变开始，经千里返乡、绵德防线、成都控制区与盆地退潮，最终抵达柴达木低能耗生物库。

迁跃体加速真实生物试错，不是系统、灵异或无限流。所有强化受能量、结构和生态位约束。

## 规则怎么用

一次只打开对应入口。写时不加载文风 skill。

| 要做什么 | 打开 |
|---|---|
| 总规则、写时六条 | `CLAUDE.md` |
| 文件索引 | `未知进化_简介与大纲.md` |
| 做或重做细纲 | `商业化章节细纲设计任务.md` |
| 写正文 | `串行正文创作任务.md`，写时只盯 `CLAUDE.md` 第七节 |
| 审查改稿 | `正文复核任务.md` |

优先级：用户本次要求 > `CLAUDE.md` > 总纲 / 世界 / 路线 / 图鉴 > 当前细纲与相邻正文。`未知进化_拆分前完整归档.md` 只读。

## 工作文件

| 文件 | 用途 |
|---|---|
| `CLAUDE.md` | 项目总规则。写单章只盯第七节六条 |
| `未知进化_故事总纲.md` | 人物、七卷、成长、爽点、结局 |
| `未知进化_第一卷章节细纲.md` | 第1—36章 |
| `未知进化_第二卷章节细纲.md` | 第37—136章 |
| `未知进化_世界设定.md` | 灾变、迁跃、表型、庇护城 |
| `未知进化_物种图鉴.md` | 生态链、俗名、弱点、资源 |
| `未知进化_地理路线.md` | 返乡、成都、高原路线 |
| `正文/` | 已完成章节 |
| `参考小说/《全球进化》（精校版全本）作者：咬狗.txt` | 只参考类型方法 |

不要每次把全部文档喂给 AI。写单章只读对应卷、当前地点/物种、本章细纲和前一章正文。

## 任务提示

### 写正文

```text
请打开并执行 串行正文创作任务.md，串行创作【第X章】至【第Y章】。
写时只盯 CLAUDE.md 第七节。不要打开复核清单当提纲。
```

### 审查改稿

```text
请按 正文复核任务.md 审查【目标章节】。先审后改。
口感以 CLAUDE.md 第七节为准。已经能看懂的动作不要再补成工序表。
```

### 做细纲

```text
请按 商业化章节细纲设计任务.md，为第【起始章】-第【结束章】设计或重做细纲。
```

### 设定一致性

```text
请先读 CLAUDE.md 和未知进化_故事总纲.md，再按问题读取世界设定、地理路线或物种图鉴。审查【目标】与当前设定是否一致。先列带位置的问题，再给最小修订。不改拆分前完整归档。
```

## 番茄草稿箱上传工具

本项目提供一个浏览器自动化工具，用于把根目录 `正文/` 下的正文章节保存到番茄小说作者后台草稿箱。

> 注意：`fanqie_draft_upload/fanqie_publish.yaml` 当前仍保留上一作品的 `book_name` 和后台地址。在取得《未知进化》的作品 ID 并人工更新配置前，不要执行远端保存命令。

功能边界：

- 只保存草稿，不发布、不定时发布、不提交审核。
- 不在项目中保存账号、密码、cookie 或 token。
- 浏览器登录状态保存在仓库外，具体路径以 `fanqie_publish.yaml` 为准。
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
