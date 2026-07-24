---
name: anzhi-word-format
description: 独立 Word 文档公文格式整理工具，套用页面设置（纸张/页边距/文档网格/页码）与正文格式（标题/正文字体字号、落款日期、目录），并做文本校对（引号方向、日期补零、行首符号等）。触发词：格式化文档、Word 排版。用户给出 .docx 文件且要求"格式化/排版/套公文格式"时使用。不用于生成全新文档内容，只做既有文档的格式整理。
---

# anzhi-word-format — Word 公文格式整理工具

**声明：** 我正在使用 anzhi-word-format 技能，对 Word 文档套用公文格式模板。

**职责边界：** 只做"格式整理"这一件事——页面设置、正文字体字号、标题识别、文本校对、可选目录。不做内容撰写、不做审校（错别字/语法），不做排版之外的文档生成。

---

## 依赖

- **Python 3.11+**
- `pip install -r requirements.txt`（python-docx、pyyaml、jieba——jieba 用于主标题智能折行，默认开启，可用 `--no-title-wrap` 关闭以跳过该依赖路径）
- **officecli**（可选外部 CLI）：仅 `--toc`（自动目录）功能需要，用于插入/刷新 TOC 域。未安装时 `--toc` 会降级为「打好大纲级别但目录域未生成」并在报告中给出警告，不中断整体格式化流程；页码固化还需 Windows + 已装 Word。
- **pandoc**：本工具**不直接调用** pandoc。`pandoc_cleanup.py` 只是清理"文档若曾经过 pandoc 转换"遗留的样式污染（标题主题蓝、引号方向），对普通 docx 是安全无操作，不需要本机装 pandoc。

---

## 用法

所有命令从 `scripts/` 目录下以模块方式运行：

```bash
cd scripts
py -3.11 -m word_format.word_format_tool --input 文件.docx --template 公文_本单位 --page-number
```

### 常用组合

```bash
# 仅页面设置
py -3.11 -m word_format.word_format_tool --input 文件.docx --page-only

# 仅正文格式（含文本校对）
py -3.11 -m word_format.word_format_tool --input 文件.docx --style-only

# 页面 + 正文 + 日常页码
py -3.11 -m word_format.word_format_tool --input 文件.docx --template 公文_本单位 --page-number

# 页面 + 正文 + 公文页码（— n —）
py -3.11 -m word_format.word_format_tool --input 文件.docx --template 公文_本单位 --page-number --page-style 公文

# 国标模板
py -3.11 -m word_format.word_format_tool --input 文件.docx --template 公文_国标 --page-number

# 表格格式一并整理
py -3.11 -m word_format.word_format_tool --input 文件.docx --format-table

# 自动编号转纯文本
py -3.11 -m word_format.word_format_tool --input 文件.docx --fix-list

# 只检查不改写，输出检查报告
py -3.11 -m word_format.word_format_tool --input 文件.docx --check-only

# 生成目录（需要 officecli）
py -3.11 -m word_format.word_format_tool --input 文件.docx --toc

# 列出可用模板 / 设默认模板
py -3.11 -m word_format.word_format_tool --list-templates
py -3.11 -m word_format.word_format_tool --set-default 公文_国标
```

**输入解析**：`--input` 未指定时自动取 `scripts/word_format/input/` 下最新的 .docx；产出写入 `scripts/word_format/output/`（`<原文件名>_formatted.docx` + `<原文件名>_report.md`），原始文件归档到 `scripts/word_format/history/`。这三个目录会自动创建，不随本包提交（见 `.gitignore`）。

**全部参数**：`--input` `--template` `--set-default` `--list-templates` `--interactive/-i` `--verbose` `--page-only` `--style-only` `--page-number` `--page-style {日常,公文}` `--format-table` `--fix-list` `--check-only` `--no-title-wrap` `--toc`。`--interactive` 需额外装 `rich`+`questionary`（未装时自动降级为直接用默认模板）。

---

## config.yaml（顶层配置）

`scripts/word_format/config.yaml`：

| 字段 | 说明 |
|------|------|
| `default_template` | 未传 `--template` 时使用的默认模板名，对应 `templates/<名称>.yaml` |
| `schema_version` | 配置文件版本号，固定为 1 |

## text_check_config.yaml（文本校对开关）

`scripts/word_format/text_check_config.yaml`：

| 字段 | 说明 |
|------|------|
| `built_in.fix_date_padding` | `2024年03月05日`→`2024年3月5日`（去补零） |
| `built_in.fix_bullet_chars` | 删除行首手打项目符号 `·`/`-`（表格单元格不处理，避免误删负数/层级前缀） |
| `built_in.fix_zhizhi` | `截止`（非"截止到"）→`截至` |
| `built_in.fix_quotes` | 英文直双引号 `"…"` → 中文弯引号 `“…”` |
| `built_in.fix_quote_direction` | 中文弯引号方向重排（修复 pandoc smart quotes 误判） |
| `built_in.fix_list` | 自动编号转纯文本，可用命令行 `--fix-list` 临时覆盖开启 |
| `custom_fixes` | 自定义查找替换列表，每项 `{from: "原文", to: "替换文"}` |
| `leader_check.enabled` / `leaders` | 领导人姓名出场顺序核查（按 `rank` 数值应升序出现），`leaders` 每项 `{name, title, rank}` |
| `org_check.enabled` / `orgs` | 机构简称须先出现全称核查，`orgs` 每项 `{full, abbr}` |

## templates/*.yaml（页面 + 正文格式模板）

内置两个模板：`公文_本单位.yaml`（日常页码模式）、`公文_国标.yaml`（GB/T 9704-2012，公文页码模式）。字段：

| 字段 | 说明 |
|------|------|
| `name` / `description` | 模板名称与说明 |
| `page.page_width_cm` / `page_height_cm` | 纸张尺寸（默认 A4：21×29.7） |
| `page.margin_top/bottom/left/right_cm` | 页边距 |
| `page.header_dist_cm` / `footer_dist_cm` | 页眉/页脚距边距 |
| `page.grid_font` / `grid_font_pt` | 文档网格基准字体与字号 |
| `page.chars_per_line` | 每行字数 |
| `page.line_pitch_pt` | 行距（磅，固定值） |
| `page.page_number.mode` | `daily`（第n页 共m页）或 `official`（— n —，奇偶页独立页脚，字体字号写死宋体四号，不受模板配置） |
| `page.page_number.font/size_pt/align` | 仅 `daily` 模式生效 |
| `body.main_title.font/size_pt` | 主标题（第一段） |
| `body.sub_title.font/size_pt` | 副标题/称呼语/落款/日期所在段（标题块内非首段） |
| `body.headings[]` | 各级标题：`level`（1-4）、`pattern`（识别正则）、`font`、`size_pt`、`bold` |
| `body.body.font/size_pt` | 正文字体字号 |
| `body.table.font/size_pt/line_spacing_pt` | 表格字体字号与行距，`--format-table` 时生效 |

用 `--set-default <名称>` 或 `--interactive` 保存修改后的参数为新模板（写入 `templates/<新名称>.yaml`）。

---

## 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| `--toc` 后目录为空/未生成 | 未装 officecli，或文档标题不符合模板 `headings[].pattern` 正则 | 装 officecli 后重试；或检查标题编号格式是否匹配（如 `一、`、`（一）`） |
| 报错"未找到输入文件" | 未传 `--input` 且 `scripts/word_format/input/` 下无 .docx | 传 `--input <路径>` 或把文件放入该目录 |
| 报错"配置文件格式错误" | `templates/*.yaml` 或 `config.yaml` 缺字段/YAML 语法错误（常见：中文全角冒号 `：`代替 `:`） | 按报错提示的行号核对 YAML 语法 |
| `--page-only` 与 `--toc` 同时报错 | 目录需要正文格式处理（do_style 分支），二者互斥 | 去掉 `--page-only` |
| 主标题折行报 `ModuleNotFoundError: jieba` | 未安装 jieba | `pip install jieba`，或加 `--no-title-wrap` 跳过折行 |
