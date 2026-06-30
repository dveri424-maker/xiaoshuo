# 《美恐最严厉的父亲》工作区

当前分支是中文美恐无限流幻想小说《美恐最严厉的父亲》。

项目核心：林扬进入不同欧美恐怖类型副本，入场时不知道具体原型，只能通过现场线索、试错代价和怪物行为逐步识别规则；恐怖压迫成立后，再用荒诞理性和父亲式秩序感反向整改恐怖规则。

## 必读文档

涉及新书设计、卷纲、章节细纲、正文写作、改稿、审稿和文档同步时，先读：

- `CLAUDE.md`
- `《美恐最严厉的父亲》设定文档.md`
- `《美恐最严厉的父亲》剧情大纲与写法定稿.md`
- `.claude/skills/meikong-horror-workflow/SKILL.md`

## 推荐 Skill 组合

- 新书、总纲、卷纲、章节细纲：`webnovel-workflow` + `meikong-horror-workflow`
- 正文写作、正文续写：`webnovel-workflow` + `meikong-horror-workflow`
- 正文去 AI 味、恐怖现场感改稿：`novel-de-ai` + `meikong-horror-workflow`
- Codex 与 Claude 协作讨论或分工：`codex-pm-claude`

当前项目规则以 `CLAUDE.md` 和两份正式设定文档为准。旧分支任务示例不作为当前项目参考。

## 常用任务模板

### 单章正文

```text
使用 webnovel-workflow 与 meikong-horror-workflow，依据 CLAUDE.md、《美恐最严厉的父亲》设定文档.md、《美恐最严厉的父亲》剧情大纲与写法定稿.md，设计并写作第XXX章。

要求：
- 林扬入场或推进时不能全知，必须通过现场物件、人物反应、异常变化和试错代价缩小规则范围。
- 本章先成立恐怖压迫，再让林扬冷静拆解或反制。
- 至少出现一个可见物件、一个规则线索或代价、一个章末钩子。
- 林扬可以嘴欠，但必须服务观察、推理、压场或反制。
- 禁止死亡现场玩梗、规则说明书腔、任务面板替代现场探索。
```

### 3-5 章连续改稿

```text
使用 novel-de-ai 与 meikong-horror-workflow，连续审查并修改第XXX-XXX章。

目标：
- 保留剧情、人物关系、规则线索、死亡/污染代价、章末钩子。
- 降低 AI 腔、作者解释腔、规则说明书腔、同步反应和短句装感。
- 强化恐怖现场感、物件触发感、配角真实恐惧和林扬的冷静反制。
- 检查章节交界是否顺，前章钩子是否接住下一章开场。

完成后列出：
- 修改文件
- 修掉的主要问题
- 仍需人工确认的问题
- git diff 检查结果
```

### 只读审查

```text
使用 meikong-horror-workflow 只读审查以下大纲/章节，不修改文件。

重点检查：
- 是否有强识别物和欧美恐怖类型外壳。
- 是否有原创隐藏规则和原作/类型误导。
- 是否有死亡、不可逆污染、身份替换、记忆缺口或救人付债等代价。
- 林扬是否误判、付债或救不全。
- 恐怖是否先成立，黑色幽默是否没有冲淡死亡重量。
- 系统是否没有用万能黑箱替代现场探索。
```

### 三轮 Claude 讨论

```text
$codex-pm-claude 使用“多次 Claude 进程 + 同一个临时讨论文件”的方式，与 Claude 做三轮讨论。任务结束后删除临时讨论文件。

讨论主题：
【这里写主题】

流程要求：
1. Codex 先在临时文件中写入任务背景、Codex 初始观点和需要 Claude 反驳的问题。
2. 第一轮 Claude 读取临时文件，重点反驳 Codex 方案，指出不爽、不稳、不合理、读者可能不买账的地方。
3. Codex 读取 Claude 反馈后，把接受点、拒绝点、修订方案追加到同一个临时文件。
4. 第二轮 Claude 读取临时文件，对 Codex 修订方案做二审，继续挑问题并给替代建议。
5. Codex 再次追加最终判断：哪些采纳、哪些不采纳、最终方案是什么。
6. 如有必要，第三轮 Claude 只检查最终方案是否还有明显漏洞。
7. Codex 最后输出：讨论摘要、分歧点、采纳点、最终定稿，并删除临时讨论文件。

限制：
- 临时讨论文件只用于协作讨论，任务完成后删除。
- 最终由 Codex 负责判断和落地。
```

## 提交前检查

常用检查：

```bash
git status --short
git diff --check
```

旧分支残留词检查应使用临时 pattern 文件或临时命令完成，检查文件不要提交。高危旧分支残留只允许出现在 `CLAUDE.md` 的警示句中。临时讨论文件应在任务结束前删除。

## 发布/上传工具

本项目保留番茄草稿箱上传工具，但只在用户明确要求上传或检查上传状态时使用。不要在普通写作、审稿、改稿任务中自动执行上传命令。

功能边界：

- 只保存草稿，不发布、不定时发布、不提交审核。
- 不在项目中保存账号、密码、cookie 或 token。
- 浏览器登录状态保存在仓库外：`/home/weishida/.local/share/xiaoshuo/fanqie-browser-profile`。
- 工具只读取 `正文/` 并写入本地状态台账，不移动、不改写小说创作文件。

相关文件：

```text
fanqie_draft_upload/
├── fanqie_prepare_manifest.py
├── fanqie_publish_browser.py
├── fanqie_publish.yaml
├── requirements.txt
└── data/fanqie_publish_state.json
```

常用命令：

```bash
python3 fanqie_draft_upload/fanqie_prepare_manifest.py
python3 fanqie_draft_upload/fanqie_publish_browser.py audit
python3 fanqie_draft_upload/fanqie_publish_browser.py check
python3 fanqie_draft_upload/fanqie_publish_browser.py save-drafts --confirm-save-drafts
```

真正写入远端草稿箱前，脚本会要求输入确认语；确认语不匹配会取消操作。
