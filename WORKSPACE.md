# wukong-transfer 工作台规范

所有在此工作台协作的 agent（Claude Code / Codex / Kimi Code / 其他）共同遵守本文件。
人格定义见 `soul.md`（悟空），不因平台而变。

> **多平台原则：** 业务流程对所有 agent 同等生效，平台差异只写在各自入口文件（CLAUDE.md / AGENTS.md），不在此处区分。硬约束与高频规则集中在 CLAUDE.md，本文件负责协作约定与技能发现。

---

## 一、文件分工

| 文件 | 谁读 | 内容 |
|------|------|------|
| `CLAUDE.md` | Claude Code（自动加载） | 会话启动清单 + 业务规范**共享权威**（目录结构 / 工作流 / 记忆规则 / 约定与启动检查点） |
| `AGENTS.md` | Codex、Kimi Code 等（各自自动加载） | 启动读取清单 + 平台差异与替代做法 |
| `WORKSPACE.md` | 所有 agent | 多 agent 协作约定 + 技能发现协议（本文件） |
| `soul.md` | 所有 agent | 人格与工作原则 |
| `memory/海马体.md`、`knowledge/*` | 所有 agent | 纯 Markdown 状态文件与知识库，任何 agent 均可读写 |
| `workflows/*/‥-SOP.md` | 所有 agent | 评估/评审 SOP，本身就是平台中立的文字流程 |
| `BOOTSTRAP.md`、`data-manifest.md` | 复建阶段的 AI | 复建指南与离线包落位说明，日常使用无需重读 |

> 业务规范主体在 `CLAUDE.md`，全文对所有 agent 同等生效：
> - 文中出现的「XX 技能」，非 Claude agent 按本文件第二、三节协议换算执行
> - `CLAUDE.md`「约定」节的**启动检查点**（活动盯盘窗口扫描、谛听事后采集预筛、知识库月度健检提醒、_raw/ 筋斗云提示）对所有 agent 同等生效，非 Claude agent 也必须在会话开始时执行

---

## 二、技能发现协议 ★

**技能库物理位置**（目录名虽带 "claude"，实际作为本工作台的**通用技能库**，所有 agent 从这里读取）：

- `.claude/skills/<技能名>/SKILL.md`（仓内相对路径，本仓只有这一处技能库）

**各平台的发现方式：**

- **Claude Code**：自动发现，用 Skill 工具调用，无需读本节。
- **其他 agent（Codex / Kimi Code / 任何无技能机制的 agent）**：
  1. 会话开始不必预读技能，只需知道本协议；
  2. 用户消息命中下方「技能清单」某行的触发词 → **读该技能的 `SKILL.md` 全文** → 把它当作 SOP 按步骤内联执行；
  3. `SKILL.md` 内引用的 `references/` `scripts/` `templates/` 等相对路径，一律基于该技能目录解析；
  4. 技能文本中调用其他技能（Skill 工具）的步骤 → 改为直接读那个技能的 `SKILL.md` 内联执行（例：火眼金睛/照妖镜调用顺风耳）；
  5. 技能文本中的 Claude 专用工具名按第三节映射表换算。

**登记义务（发现契约）**：新增、改名、删除技能时，**必须同步更新下方技能清单**。未登记的技能对非 Claude agent 等于不存在。
机械校验：`powershell -File scripts\skills_lint.ps1`（清单与 `.claude/skills/` 目录漂移即报红；技能增删改后立即跑，月度健检时顺带跑）。

### 技能清单（项目级，`.claude/skills/`，共 12 个）

| 技能 | 中文名 | 一句话职责 | 触发词 | 备注 |
|------|--------|-----------|--------|------|
| `anzhi-huoyanjinjing` | 火眼金睛 | 声誉风险评估（六维评估法），输出评审结论并建活动卡 | 火眼金睛、声誉风险评估、开始评估 | 活动卡建卡唯一入口（活动台账轨） |
| `anzhi-huodongpingshen` | 照妖镜 | 活动前置评审（七阶段协议，正式发起申请前） | 照妖镜、活动评审 | 不建活动卡；新隐患知识轨当场沉淀 |
| `anzhi-qishierbian` | 七十二变 | 活动方案共创 + 配套备料（评估表 xlsx / 应急预案 docx） | 七十二变、做方案、备料 | 不出正式风险定级 |
| `anzhi-issue-shunfenger` | 顺风耳 | 舆情热点搜索（快扫/深查，被火眼金睛/照妖镜复用） | 顺风耳、舆情热点 | **降级**：原热榜聚合网站不随交，仅联网搜索通道可用 |
| `anzhi-honghaier` | 红孩儿 | 小红书舆情风险查询（三层漏斗风险快照） | 红孩儿、查小红书 XX | **降级**：需自备监测小号扫码登录 |
| `anzhi-qianliyan` | 千里眼 | 周度舆情监测报告（同业九家 + 本行 + 监管动态） | 千里眼、周度舆情监测 | 强依赖联网搜索能力 |
| `anzhi-diting` | 谛听 | 事后反馈采集闭环：评估校正（月度批量）+ 事后采集（活动结束后） | 评估校正、事后采集 | 会话启动有自动预筛提醒 |
| `anzhi-tousufenxi-jingubang` | 金箍棒 | 客户投诉分析：督办/投诉归一化入库 + 八模型定量 + 预警 + 深挖 + 月度报告 | 投诉分析、金箍棒、深挖 XX | 数据放 `work/客户投诉分析/原始/` 后触发 |
| `anzhi-jinguzhou` | 紧箍咒 | 企微聊天记录质检 + 人工复核回填 | 聊天质检、质检复核 | xlsx 放 `work/事后质检/原始/` 后触发 |
| `anzhi-file-go-home` | 筋斗云 | `_raw/` 新材料归位：知识类入知识库、活动材料入活动方案库 | 筋斗云、归位 | `_raw/` 为用户自建普通目录（见 BOOTSTRAP 落位步骤） |
| `anzhi-send-email` | 发邮件 | 通过用户自己的邮箱账号发送邮件/附件 | 发邮件、把文件发给… | 需先按 BOOTSTRAP 完成 `.env` 配置 |
| `anzhi-word-format` | Word 排版 | Markdown/文本内容排版为规范 docx | 格式化文档、Word 排版 | 依赖 officecli，Python 依赖见技能内 requirements.txt |

### 常用全局技能

无——本移交仓不附带全局技能层，全部 12 个技能都在上方项目级清单内（`scripts\skills_lint.ps1` 校验的也是项目级清单与目录的一致性）。

**不随交的两个技能**：原体系中的 `anzhi-xiyou`（内部交接包同步）与 `anzhi-qingyun`（服务器活动库同步）因生态/服务器耦合不随交——前者服务于源仓的旧移交通道，后者的同步对端（源侧网站服务器）不在移交范围内。CLAUDE.md 的「盯盘完成」流程已相应去掉同步尾步：更新卡片与 INDEX 即为完成。

---

## 三、平台工具映射（非 Claude agent 用）

| Claude 工具 / 机制 | 等价做法 |
|--------------------|---------|
| Read / Write / Edit / Glob / Grep | 各平台自己的文件读写与搜索 |
| Bash / PowerShell | shell 执行 |
| WebSearch / WebFetch | 各平台联网搜索能力；无联网能力时明确告知用户该步骤无法执行（顺风耳/千里眼强依赖联网），不要凭记忆编造舆情 |
| Skill 工具 | 读对应技能 `SKILL.md` 内联执行（第二节） |
| AskUserQuestion | 直接向用户提问 |
| Task / 子代理 | 自行顺序执行各子任务 |
| 完成前核查类技能 | 宣称完成前，逐项对照原始需求确认已做/未做/不适用 |

---

## 四、记忆、状态与并发

- `memory/海马体.md`、`knowledge/log.md` 等为共享状态文件，所有 agent 按 `CLAUDE.md` 的规则读写（对 knowledge/ 的实质操作必须在 `knowledge/log.md` 记一条，**新条目插在文件顶部**、按日期降序，勿追加到文件末尾）。
- 平台自带持久记忆可自行使用，但**业务记忆以 `memory/海马体.md` 为准**，平台私有记忆不得替代它。
- **并发约定**：允许多个 agent 同时打开本工作台，但同一时间只允许一个 agent 编辑同一个状态文件；多 agent 同开时先向用户声明分工；发现他人未收尾的半成品编辑（冲突标记、残缺表格）先停手报告用户，不覆盖。

---

## 五、本仓库特有注意事项（全 agent）

- **数据落位目录**：`work/`、`internal-comms/`、`knowledge-raw/`、`templates/originals/`、`knowledge/tools/assessment-manual/private/` 内容来自离线数据包（见 `data-manifest.md`），已被 `.gitignore` 排除——它们是普通实目录，正常读写即可，但**不会随 git 同步**，注意自行备份。
- **本仓由源仓导出脚本单向同步**：勿在本仓直接修改由源仓生成的业务内容（技能文件、CLAUDE.md、知识库工具轨等）——下次同步会整体覆盖。本地积累（memory/、work/、活动方案库新卡、log.md 新条目等运行时数据）不受影响。修改建议反馈移交人。
- **风险等级口径**：一级（极高）/ 二级（高）/ 三级（中）/ 四级（低），一级最高，任何 agent 输出结论时不得自创口径。

---

## 六、多 Agent 扩展说明

新增 agent 平台时：

1. 若它自动读取 `AGENTS.md`（Codex / Kimi Code / OpenCode 等通行约定）→ 零成本接入，无需改任何文件；
2. 若它用别的入口文件（如 GEMINI.md）→ 新建该文件，内容 = 引用 `AGENTS.md`（或复述其启动清单），指向本文件；
3. 无需修改 `WORKSPACE.md` 与业务规范本身。
