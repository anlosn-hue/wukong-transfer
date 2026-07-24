# BOOTSTRAP — 悟空复建指南

> 本文件面向**接管本仓的 AI 助手**书写：指令式、逐步执行、每步带验证。人类用户只需在关键节点（取离线包、填 .env、扫码登录）介入。
> 全部完成的标志 = 第 8 节验收清单逐项打钩。

---

## 1. 这是什么

你将复建的是「悟空」——商业银行数字运营部门的声誉风险管理 AI 工作台：声誉风险评估、活动评审、舆情监测、投诉分析、聊天质检等能力，以 12 个技能 + 知识库 + SOP 的形式交付。

**12 技能一览：**

| # | 技能 | 中文名 | 职责 | 触发词 |
|---|------|--------|------|--------|
| 1 | `anzhi-huoyanjinjing` | 火眼金睛 | 声誉风险评估（六维评估法） | 火眼金睛、声誉风险评估、开始评估 |
| 2 | `anzhi-huodongpingshen` | 照妖镜 | 活动前置评审（七阶段协议） | 照妖镜、活动评审 |
| 3 | `anzhi-qishierbian` | 七十二变 | 活动方案共创+配套备料 | 七十二变、做方案、备料 |
| 4 | `anzhi-issue-shunfenger` | 顺风耳 | 舆情热点搜索 | 顺风耳、舆情热点 |
| 5 | `anzhi-honghaier` | 红孩儿 | 小红书舆情查询 | 红孩儿、查小红书 XX |
| 6 | `anzhi-qianliyan` | 千里眼 | 周度舆情监测报告 | 千里眼、周度舆情监测 |
| 7 | `anzhi-diting` | 谛听 | 评估校正 + 事后采集闭环 | 评估校正、事后采集 |
| 8 | `anzhi-tousufenxi-jingubang` | 金箍棒 | 客户投诉分析（月度） | 投诉分析、金箍棒、深挖 XX |
| 9 | `anzhi-jinguzhou` | 紧箍咒 | 企微聊天质检 + 复核回填 | 聊天质检、质检复核 |
| 10 | `anzhi-file-go-home` | 筋斗云 | `_raw/` 新材料归位入库 | 筋斗云、归位 |
| 11 | `anzhi-send-email` | 发邮件 | 邮件/附件发送 | 发邮件、把文件发给… |
| 12 | `anzhi-word-format` | Word 排版 | Markdown → 规范 docx | 格式化文档、Word 排版 |

**不随交说明**：原体系中的 `anzhi-xiyou`（内部交接包同步）与 `anzhi-qingyun`（服务器活动库同步）因生态/服务器耦合不随交。业务流程已相应调整（如「盯盘完成」不再有同步尾步），你无需寻找或补建这两个技能。

---

## 2. 环境前置

逐项安装并执行验证命令，全部通过再进入第 3 节。

| 前置项 | 说明 | 验证命令 | 预期 |
|--------|------|---------|------|
| Agent 平台 | Claude Code（推荐）或兼容 agent（Codex / Kimi Code 等，先读 `AGENTS.md`） | 启动 agent，确认能读取仓内文件 | 能读到 `soul.md` |
| Python 3.11+ | 金箍棒/紧箍咒/谛听脚本、Word 排版依赖 | `py -3.11 --version` | `Python 3.11.x` 或更高 |
| Python 依赖 | Word 排版与数据脚本所需 | `py -3.11 -m pip install python-docx pyyaml jieba` 后 `py -3.11 -c "import docx, yaml, jieba; print('ok')"` | 输出 `ok` |
| officecli | Office 文档读写 CLI（anzhi-word-format 依赖，评估/质检读 docx/xlsx 也用它） | `officecli --version` | 输出版本号 |
| pandoc（可选） | 部分文档转换路径的后备 | `pandoc --version` | 输出版本号；缺失不阻塞复建 |
| playwright + chromium（仅红孩儿需要） | 小红书查询走浏览器 | `py -3.11 -m pip install playwright` 后 `py -3.11 -m playwright install chromium`，验证 `py -3.11 -m playwright --version` | 输出版本号；不用红孩儿可跳过 |
| PowerShell | `scripts/skills_lint.ps1` 校验用（Windows 自带） | `powershell -Command "$PSVersionTable.PSVersion"` | 输出版本号 |

---

## 3. 落位

### 3.1 clone 本仓

```
git clone <移交人提供的仓库地址> wukong-transfer
cd wukong-transfer
```

验证：`git log --oneline --reverse | Select-Object -First 1`（PowerShell）输出的最早一条提交应为占位初始提交（全新历史）。

### 3.2 取得离线数据包

向移交人索取 `wukong-data-YYYYMMDD.zip`（U盘或网盘），并**核对批次**：zip 文件名中的日期应能在 `data-manifest.md` 批次表中找到对应行，且该行标注的仓 commit 与当前 `git log` 首条一致或更早（错位风险见 data-manifest.md）。

### 3.3 按 data-manifest.md 解压落位

落位对照表、解压步骤与核对命令以 `data-manifest.md` 为准。落位后五个数据目录应有内容：

```
powershell -Command "'work','internal-comms','knowledge-raw','templates/originals','knowledge/tools/assessment-manual/private' | ForEach-Object { '{0}: {1} 个文件' -f $_, (Get-ChildItem $_ -Recurse -File | Measure-Object).Count }"
```

预期：五行输出，每行文件数 > 0。

### 3.4 建立 `_raw/` 空目录

`_raw/` 是筋斗云技能的新材料收纳桶，不在仓与离线包中，需自建：

```
powershell -Command "New-Item -ItemType Directory -Force _raw | Out-Null; Test-Path _raw"
```

预期：输出 `True`。

### 3.5 目录树核对清单

逐项确认存在：

- [ ] `CLAUDE.md`、`soul.md`、`WORKSPACE.md`、`AGENTS.md`、`README.md`、`BOOTSTRAP.md`、`data-manifest.md`、`声誉风险管理员初始提示词.md`
- [ ] `.claude/skills/` 下恰好 12 个技能目录（与第 1 节表格一致），校验：`powershell -File scripts\skills_lint.ps1` 通过
- [ ] `knowledge/INDEX.md`、`knowledge/log.md`、`knowledge/daily/`、`knowledge/cases/`、`knowledge/活动方案库/INDEX.md`
- [ ] `knowledge/tools/` 下六个子目录：六维规则库、声誉风险事件库、投诉预警点、risk-checklist、管理机制、assessment-manual
- [ ] `workflows/reputation-assessment/声誉风险评估-SOP.md`、`workflows/activity-review/活动评审-SOP.md`
- [ ] `templates/活动卡片模板.md`、`templates/originals/`（有内容）
- [ ] `scripts/skills_lint.ps1`、`scripts/diting_excel.py`、`scripts/test_diting_excel.py`
- [ ] `memory/海马体.md`（空白模板）
- [ ] `work/`、`internal-comms/`、`knowledge-raw/`、`knowledge/tools/assessment-manual/private/`（离线包已落位）
- [ ] `_raw/`（3.4 已建）

---

## 4. 配置

### 4.1 发邮件 `.env`

1. 复制 `.claude/skills/anzhi-send-email/.env.example` 为同目录 `.env`
2. 请**用户本人**填入自己的邮箱账号、授权码、SMTP/IMAP 服务器（字段名见 .env.example 注释）——AI 不代填、不回显真值
3. 验证：按该技能 SKILL.md 的 dry-run 方式执行一次（见第 5 节冒烟表），确认配置读取成功且**不实际发送**

### 4.2 处室清单核对

确认 `knowledge/tools/assessment-manual/private/处室清单.md` 存在且可读（评估/评审流程要用）：

```
powershell -Command "Test-Path 'knowledge/tools/assessment-manual/private/处室清单.md'"
```

预期：`True`。若为 `False`，回查 3.3 的 `private/` 落位。

### 4.3 外部能力不随交声明（务必知悉，避免排障走弯路）

- 原体系配套的**网站/服务器能力不随交**（源侧自建的舆情热榜聚合站、活动库同步对端等）。
- **顺风耳降级口径**：SKILL 中的热榜聚合网站取数通道在本环境不可用，属预期行为；仅联网搜索（WebSearch 类能力）通道有效。技能内已附降级说明。
- **红孩儿**：需用户自备小红书**监测小号**扫码登录后方可查询；未配置时技能应报告缺配置，而不是报错崩溃。纯观察者只读，绝不发布/点赞/评论/互动。

---

## 5. 逐技能冒烟

原则：评估/评审类用 `work/` 内**真实历史材料**作输入重跑一单，与存档结论对读——方向一致即通过（措辞差异正常，等级/要点大幅偏离则排查规则库加载）。逐行执行，结果记入第 8 节验收清单。

| # | 技能 | 最小验证动作 | 预期 |
|---|------|-------------|------|
| 1 | 火眼金睛 | 从 `work/声誉风险评估/` 挑一单历史评估的申请材料，触发「声誉风险评估」重跑 | 输出六维评估结论；风险等级与存档定稿一致或偏差可解释 |
| 2 | 照妖镜 | 从 `work/活动评审/` 挑一单历史评审的活动方案，触发「活动评审」重跑 | 输出评审意见+风险等级；与存档结论对读方向一致 |
| 3 | 七十二变 | 触发「做方案」，给一个简单活动主题（如"支付满减") | 检索活动方案库同类历史活动并生成方案初稿 |
| 4 | 顺风耳 | 触发「顺风耳」快扫任一关键词 | 热榜通道报降级说明；联网搜索通道返回结果 |
| 5 | 红孩儿 | 未配置小号时触发「红孩儿」 | 明确报告缺监测小号配置并给出配置指引（不崩溃）；已配置则返回风险快照 |
| 6 | 千里眼 | 触发「周度舆情监测」生成一期周报底稿 | 产出 .md 底稿，含同业与监管动态栏目 |
| 7 | 谛听 | 触发「事后采集」（Step 1 列表模式），指向 `work/` 内历史采集批次目录 | 列出待采集活动/历史批次，可复算不报错 |
| 8 | 金箍棒 | 指向 `work/客户投诉分析/` 任一历史月份，复算定量分析 | 八模型数值与存档报告一致（钩稽：总计=分项之和） |
| 9 | 紧箍咒 | 指向 `work/事后质检/` 任一历史批次，复算解析+扫描 | 命中统计与存档报告一致 |
| 10 | 筋斗云 | 放一个测试 md 文件进 `_raw/`，触发「筋斗云」 | 识别文件类型并给出归位建议/执行归位；`_raw/` 清空 |
| 11 | 发邮件 | 按 SKILL.md 的 **dry-run** 模式发一封测试邮件给用户自己 | 打印将发送的内容与收件人，**不实际发送**；.env 读取成功 |
| 12 | Word 排版 | 触发「格式化文档」，把仓内任一 .md 转 docx | 生成排版后的 .docx，officecli 链路无报错 |

---

## 6. 日常使用入口

### 会话启动检查项（每次会话开始，`CLAUDE.md` 为准绳）

1. 读 `soul.md` → `memory/海马体.md` → `CLAUDE.md` 约定节
2. 活动盯盘窗口扫描（📡 提醒：活动类五节点 / 系统维护类两节点，准入规则与畸形行报告见 CLAUDE.md）
3. 谛听事后采集预筛（👂 提醒：已结束活动待采集）
4. 知识库健检提醒（当月 25 日及以后且本月未健检）
5. `_raw/` 有新文件 → 提示筋斗云

### 触发词速查表

| 说什么 | 干什么 |
|--------|--------|
| 火眼金睛 / 声誉风险评估 / 开始评估 | 声誉风险评估（建活动卡入口） |
| 照妖镜 / 活动评审 | 活动前置评审（不建卡） |
| 七十二变 / 做方案 / 备料 | 方案共创+评估表/预案备料 |
| 顺风耳 / 舆情热点 | 舆情热点搜索 |
| 红孩儿 / 查小红书 XX | 小红书舆情查询 |
| 千里眼 / 周度舆情监测 | 周度舆情监测报告 |
| 活动盯盘 | 列全部进行中活动+舆情关键词 |
| 盯盘完成 | 回填 sfe_checked_dates + INDEX 下次盯盘节点 |
| 事后采集 / 评估校正 | 谛听两条流程 |
| 投诉分析 / 金箍棒 / 深挖 XX | 客户投诉分析 |
| 聊天质检 / 质检复核 | 企微聊天质检 / 复核回填 |
| 筋斗云 / 归位 | `_raw/` 材料归位 |
| 发邮件 / 把文件发给… | 邮件发送 |
| 格式化文档 / Word 排版 | md → docx |

---

## 7. 记忆机制初始化

- `memory/海马体.md` 已随仓提供**空白模板**（仅表头结构），无需新建；首次会话直接按模板内「触发清单」积累。
- 五条写入触发（详见 `CLAUDE.md` 记忆写入规则）：任务跨会话 / 非显而易见的风险判断 / 新排查要点 / 监管新动向 / 用户纠正业务判断。**每次会话结束前过一遍五条。**
- 条目积累超过 5 条 → 主动提议用户整理（升格独立主题文件或删除）。
- 平台自带持久记忆可用，但业务记忆以海马体为唯一共享事实源。

---

## 8. 验收清单

全部打钩 = 复建完成。任一项不过：停下报告用户，不要带病宣称完成。

**环境（4 项）**
- [ ] Python 3.11+ 验证通过（`py -3.11 --version`）
- [ ] Python 依赖导入 ok（python-docx / pyyaml / jieba）
- [ ] officecli 可用（`officecli --version`）
- [ ] PowerShell 可用、`scripts\skills_lint.ps1` 跑通（pandoc / playwright 为可选项，未装需在报告中注明）

**落位（5 项）**
- [ ] 仓已 clone，第 3.5 节目录树核对清单逐项存在
- [ ] 离线包批次与 `data-manifest.md` 批次表对上号
- [ ] 五个数据目录均有内容（3.3 核对命令通过）
- [ ] `_raw/` 空目录已建立
- [ ] `memory/海马体.md` 空白模板就位

**配置（2 项）**
- [ ] `anzhi-send-email/.env` 已由用户填写，dry-run 读取成功
- [ ] `knowledge/tools/assessment-manual/private/处室清单.md` 可读

**逐技能冒烟（12 项，对应第 5 节表格逐行）**
- [ ] 1 火眼金睛　- [ ] 2 照妖镜　- [ ] 3 七十二变　- [ ] 4 顺风耳
- [ ] 5 红孩儿　- [ ] 6 千里眼　- [ ] 7 谛听　- [ ] 8 金箍棒
- [ ] 9 紧箍咒　- [ ] 10 筋斗云　- [ ] 11 发邮件（dry-run）　- [ ] 12 Word 排版

**红线自查（2 项）**
- [ ] `git log --oneline --reverse | Select-Object -First 1` 最早一条提交为占位初始提交（orphan 全新历史，与任何其他仓无共同祖先）
- [ ] 全仓搜索盘符前缀路径 0 命中：`powershell -Command "(Get-ChildItem -Recurse -File -Include *.md,*.py,*.ps1,*.txt,*.yaml,*.json | Select-String -Pattern 'D:\\' -SimpleMatch).Count"` 输出 `0`（技能与规范文件应全部使用仓内相对路径；命中即说明存在源侧绝对路径残留，报告移交人）
