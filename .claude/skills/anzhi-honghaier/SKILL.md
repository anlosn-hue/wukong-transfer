---
name: anzhi-honghaier
description: 小红书舆情风险查询（红孩儿）。使用时机：需要查某关键词/活动在小红书上的负面、投诉、维权舆情时——顺风耳热榜通道搜不到小红书（无公开 API+登录墙），红孩儿用自有监测小号登录后查询。触发短语：红孩儿、小红书盯盘、查小红书 XX、红孩儿配置。产物：小红书风险快照报告（Markdown，含 A 层命中笔记清单+B 层正文研判+C 层评论发酵度，落数据区目录）。负向边界：仅限小红书——微博/抖音等其他平台、常规热榜或同业周度舆情请用顺风耳/千里眼，不要触发红孩儿；纯观察者只读，绝不发布/点赞/评论/互动。
---

> **复建环境说明**：本技能依赖自备的小红书监测账号（扫码登录、纯观察者只读）。复建方需自行准备监测账号并完成 `playwright install chromium` 后首次扫码。

# 红孩儿 — 小红书查询引擎

首次使用/换机器：`pip install -r requirements.txt && python -m playwright install chromium`（依赖 playwright+beautifulsoup4+pyyaml+chromium）。
配置：`config.yaml`（本目录）。阈值/开关/风险词全在里面，代码零硬编码。
数据区：config `路径.数据区`（建议配置为仓内 work/ 下对应目录，不进 git）。
设计文档：`docs/superpowers/specs/2026-07-11-红孩儿小红书查询引擎-design.md`。

**平台侧硬约束（spec §4.2，不可违反）：**
- 登录只用**专用监测小号**，绝不用用户个人主账号；
- **纯观察者**：只读公开内容，绝不发布/点赞/收藏/评论/关注/私信——脚本层面无写接口，你也绝不手动做任何写操作；
- 低频只读：单日查询上限、请求间隔已写死在 config，不绕过。

**脱敏铁律**：写进报告的摘录一律去除可识别信息（作者真名之外的手机号/卡号/单号等），只留业务事实。

## 主流程（触发词：红孩儿 / 小红书盯盘 / 查小红书 XX）

### Step 0 前置检查
1. 读 `config.yaml`，记住数据区路径、B/C 层上限、单日上限。
2. 确认登录态存在：查 `.state/state.json`（技能根目录，与 `scripts/` 平级——与 `台账文件` 同规范，见 config.yaml 注释「相对技能目录」+ `config.py` 的 `SKILL_DIR` 解析）。不存在 → 提示用户先扫码：
   `python -c "import sys;sys.path.insert(0,'.claude/skills/anzhi-honghaier/scripts');from channels.playwright_channel import ensure_login;ensure_login('.claude/skills/anzhi-honghaier/.state')"`
   （用户用**专用监测小号**扫码；检测到登录后自动保存登录态，**无需按回车**。因 `!`/终端执行无交互 stdin，故用轮询 web_session cookie 判定登录，不用 input。）

### Step 1 A 层搜索
1. 确定输出目录：`<数据区>/<今日YYYYMMDD>-<关键词>/`（关键词可取活动卡 risk_keywords）。
2. 运行：`python .claude/skills/anzhi-honghaier/scripts/run_search.py "<关键词>" --outdir "<输出目录>"`
   （需指定时间窗加 `--days N`；换通道加 `--channel thirdparty`，未接入会明确报错）
3. 若返回 `拒绝=true`（已达单日上限）→ 如实告知用户，停止。
4. 复述：抓取总数、A 层命中数。命中 0 → 直接跳 Step 4 出「无命中」报告。

### Step 2 B 层抓正文 + 研判
1. 运行：`python .claude/skills/anzhi-honghaier/scripts/run_fetch_detail.py --outdir "<输出目录>"`
   （只抓 A 层命中的 top-N，N=config B层抓取上限；风控中断会返回 `中断`，如实报告）
2. 逐篇读 `<输出目录>/正文/<id>.txt`，对每篇产出研判，写入 `<输出目录>/研判.json`：
   `{"研判":[{"id","情绪":"负面/中性/正面","涉我行":true/false,"风险性质":"疑似真实投诉/营销吐槽/无关/...","高风险":true/false,"摘录":"脱敏后关键句","研判说明":"一句话依据"}]}`
   - **涉我行**：正文是否确指本行（兴业/兴业银行/具体活动名）而非泛泛谈行业。
   - **高风险**：情绪负面 且 涉我行 且 风险性质为疑似真实投诉/负面发酵 → true。这是 C 层下钻的依据。
3. 复述：各篇研判结论，标出高风险几篇。

### Step 3 C 层下钻评论（默认人工确认）
1. **默认**：向用户报「B 层有 N 篇高风险，是否下钻评论看群体发酵？」，等用户点头。
   **例外**：触发词带 `--auto-deep` → 跳过询问直接下钻。
2. 下钻执行：`python .claude/skills/anzhi-honghaier/scripts/run_fetch_comments.py --outdir "<输出目录>"`
   （只抓研判.json 里高风险的 top-N，N=config C层下钻上限）
3. 逐篇读 `<输出目录>/评论/<id>.txt`，判断群体发酵度，写入 `<输出目录>/发酵.json`：
   `{"发酵":[{"id","群体信号":true/false,"复现表述":["我也没到账","+1"],"发酵度":"高/中/低","说明":"一句话"}]}`
   - **群体信号**：多条评论复现同一诉求（"我也""+1""还没到账"）→ true，发酵度高。

### Step 4 出报告
1. 运行：`python .claude/skills/anzhi-honghaier/scripts/render_report.py --outdir "<输出目录>"`
2. 读 `<输出目录>/报告.md` 复述关键结论给用户（命中数、高风险篇、发酵度）。
3. **用后即焚**（config `产出物开关.保留原始抓取=false` 时）：删除 `<输出目录>/正文/` 与 `<输出目录>/评论/` 目录（数据最小化，spec §4.1）；保留 清单/研判/发酵/报告 四个 JSON+md。
4. 提醒用户：如需存档进活动卡或转下游，人工决定（v1 不自动回填）。

## 配置（触发词：红孩儿配置）
交互式修改 `config.yaml`：阈值/风险词/上限/间隔。改完复述改了哪几项。

## 风控/异常处理
- 任一层返回 `中断`（BlockedError）→ 视为**预期内**（监测号可能被风控），如实报告"监测号可能已被限，需换号或稍后再试"，已抓取的上层结果与报告仍出。
- `中断` 含"会话抓取上限" → 本次命中笔记太多、跨层累计触顶（防失控 backstop），如实告知"本次抓取量已达会话上限、只深挖了前 N 篇"，其余可另起一次查询或调 config。
- 登录态失效 → 提示重新扫码，不自动重试。
- 搜索无结果 → 出「无命中」报告，不算失败。
- 时间窗为降级兜底：抓不到发布时间的笔记不会被误杀（保留），故清单里可能混入个别老帖，研判时留意即可。
