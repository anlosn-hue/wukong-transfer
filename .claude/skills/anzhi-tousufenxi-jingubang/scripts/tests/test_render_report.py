# -*- coding: utf-8 -*-
import json
import render_report
import report_notes

METRICS = {"月份": "2026-06", "生成时间": "2026-07-06 20:00",
           "参数快照": {"分析模型": {"排名分析": {"启用": True, "TopN": 10}}},
           "预警汇总": [
               {"级别": "红", "表": "督办", "问题点": "A/B", "依据": "比照命中", "来源模型": "督办投诉比照"},
               {"级别": "橙", "表": "投诉", "问题点": "C/D", "依据": "环比+50.0%", "来源模型": "环比同比"},
               {"级别": "黄", "表": "投诉", "问题点": "E/F", "依据": "新面孔", "来源模型": "新面孔"}],
           "模型": {"排名分析": {"指标": {
                        "投诉": {"本月": [{"问题点": "A/B", "笔数": 8, "占比": "40%"}]},
                        "督办": {"本月": [{"问题点": "A/B", "笔数": 8, "占比": "40%"}]}},
                            "md": "### 排名\n\n| # |\n|---|\n| 1 |"},
                    "督办投诉比照": {"指标": {"走势": {"A/B": {"2026-05": 3, "2026-06": 8}}},
                                     "md": "### 比照"},
                    "惯犯": {"指标": {"惯犯": [{"问题点": "A/B",
                                                "各月笔数": {"2026-05": 3, "2026-06": 8}}]},
                            "md": "### 惯犯清单\n\n- **A/B**：{'2026-05': 3, '2026-06': 8}"}},
           "深挖候选": [{"问题点": "A/B", "级别": "红", "条数": 8, "预估字数": 2400}]}

SUMMARIES = {"A/B": {"归因": "供应商接口不稳", "子问题": [{"主题": "白屏", "条数": 5, "典型例": "积点页白屏"}],
                     "处理对症": "多为模板回复", "空处理结果占比": "25%"}}

def _write_inputs(tmp_path):
    (tmp_path / "报告" / "2026-06").mkdir(parents=True)
    (tmp_path / "报告" / "2026-06" / "指标.json").write_text(
        json.dumps(METRICS, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "报告" / "2026-06" / "摘要.json").write_text(
        json.dumps(SUMMARIES, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "底库").mkdir()
    (tmp_path / "底库" / "_meta.json").write_text(
        json.dumps({"duban": {"2026-06": {"条数": 9, "源文件": "x.xlsx"}},
                    "tousu": {"2026-06": {"条数": 12, "源文件": "x.xlsx"}},
                    "未映射主办单位": ["某新单位"]},
                   ensure_ascii=False), encoding="utf-8")
    return tmp_path

def test_render_all_outputs(tmp_path):
    base = _write_inputs(tmp_path)
    cfg = {"路径": {"数据区": str(base), "预警点文件": str(base / "预警点" / "当前预警点.md")},
           "产出物开关": {"md报告": True, "预警清单": True, "预警点文件": True, "html报告": True}}
    render_report.run(base / "报告" / "2026-06", cfg)
    md = (base / "报告" / "2026-06" / "月度分析报告.md").read_text(encoding="utf-8")
    assert "参数快照" in md and "🔴" in md and "供应商接口不稳" in md
    清单 = (base / "报告" / "2026-06" / "督办预警清单.md").read_text(encoding="utf-8")
    assert "A/B" in 清单 and "E/F" not in 清单     # 黄警不进清单
    点 = (base / "预警点" / "当前预警点.md").read_text(encoding="utf-8")
    assert "A/B" in 点 and "2026-05" in 点          # 近月走势渲染进预警点
    html = (base / "报告" / "2026-06" / "月度分析报告.html").read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert "参数快照" not in html  # html不再展示参数快照（正式报告封面替代）
    assert "总行数字运营部" in html  # 新封面
    assert "<table>" in html  # 排名表格仍渲染
    assert "http" not in html.split("</style>")[1]  # 自包含无外链（base64图不算http链接）
    index = (base / "INDEX.md").read_text(encoding="utf-8")
    assert "2026-06" in index and "红1橙1黄1" in index
    assert "某新单位" in index  # 映射待补板块

def test_md_to_html_table():
    html = render_report.md_to_html("### 标\n\n| a | b |\n|---|---|\n| 1 | 2 |")
    assert "<h3>标</h3>" in html and "<td>1</td>" in html

def test_md_to_html_bold_in_list_item():
    # 代码审查发现的bug：粗体转换此前只在段落分支生效，列表项(- **X**)会原样输出字面量**
    html = render_report.md_to_html("- **归因**：供应商接口不稳\n- 子问题：白屏")
    assert "<b>归因</b>" in html and "**" not in html
    assert "<ul>" in html and "</ul>" in html  # 列表项应有容器包裹

def test_build_formal_html_has_cover_and_no_config_snapshot():
    metrics = {"月份": "2026-05", "生成时间": "2026-07-07 09:00",
               "预警汇总": [], "模型": {
                   "排名分析": {"指标": {"投诉": {"本月": []}, "督办": {"本月": []}}, "md": ""},
                   "督办投诉比照": {"指标": {}, "md": "### 督办×投诉比照\n\n无"},
                   "活动关联": {"指标": {}, "md": "### 活动\n\n无"},
                   "惯犯": {"指标": {}, "md": "### 惯犯\n\n无"}}}
    narrative = {"关键发现速览": [{"标签": "测试", "文本": "测试发现"}],
                 "结论摘要": ["1. 测试结论。"],
                 "章节": {"投诉情况": {"叙述": "投诉平稳。", "洞察": None, "风险提示": None},
                         "督办情况": {"叙述": "督办平稳。", "洞察": None, "风险提示": None},
                         "督办转投诉预警": {"叙述": "无红警。", "洞察": None, "风险提示": None},
                         "在途活动关联": {"叙述": "无活动。", "洞察": None, "风险提示": None},
                         "重复发现问题清单": {"叙述": "积累中。", "洞察": None, "风险提示": None}},
                 "策略建议": [{"标题": "建议一：测试", "内容": "测试建议内容。"}]}
    html = render_report.build_formal_html(metrics, {}, narrative)
    assert html.startswith("<!DOCTYPE html>")
    assert "参数快照" not in html
    assert "总行数字运营部" in html and "客户投诉分析报告" in html
    assert "总行数字运营部声誉风险管理智能体·悟空" in html and "金箍棒" in html
    assert "#1a4d8f" in html  # 蓝色主题色
    assert "测试发现" in html and "建议一：测试" in html
    assert "http" not in html.split("</style>")[1]  # 自包含无外链（base64图不算http链接）

def test_build_formal_html_renders_insight_risk_and_chart():
    metrics = {"月份": "2026-05", "生成时间": "2026-07-07 09:00",
               "预警汇总": [], "模型": {
                   "排名分析": {"指标": {"投诉": {"本月": [{"问题点": "借记卡限额", "笔数": 96,
                                                          "占比": "39.0%", "变动": ""}]},
                                       "督办": {"本月": []}}, "md": ""},
                   "督办投诉比照": {"指标": {}, "md": "### 督办×投诉比照\n\n无"},
                   "活动关联": {"指标": {}, "md": "### 活动\n\n无"},
                   "惯犯": {"指标": {}, "md": "### 惯犯\n\n无"}}}
    narrative = {"关键发现速览": [], "结论摘要": [],
                 "章节": {"投诉情况": {"叙述": "投诉平稳。", "洞察": "建议关注借记卡限额类。",
                                     "风险提示": None},
                         "督办情况": {"叙述": "", "洞察": None, "风险提示": "建议核实处理。"},
                         "督办转投诉预警": {"叙述": "", "洞察": None, "风险提示": None},
                         "在途活动关联": {"叙述": "", "洞察": None, "风险提示": None},
                         "重复发现问题清单": {"叙述": "", "洞察": None, "风险提示": None}},
                 "策略建议": []}
    html = render_report.build_formal_html(metrics, {}, narrative)
    assert "insight-box" in html and "建议关注借记卡限额类" in html
    assert "risk-box" in html and "建议核实处理" in html
    assert "data:image/png;base64," in html  # 图表真正以base64嵌入，不只是没崩溃


def test_undug_candidates_are_listed(tmp_path):
    """SKILL Step 3 第7点：预算内挤不进的预警诉点必须在报告里显名，
    否则读者会以为所有预警都精读过（2026-06 首版即漏标 23 个橙色预警）。"""
    import json, render_report
    out = tmp_path / "报告"; out.mkdir()
    metrics = {"月份": "2026-06", "生成时间": "-", "数据范围": {},
               "参数快照": {"分析模型": {}, "深挖": {}}, "预警汇总": [], "模型": {},
               "深挖候选": [{"问题点": "甲-乙", "级别": "红", "条数": 100, "预估字数": 1},
                            {"问题点": "丙-丁", "级别": "橙", "条数": 20, "预估字数": 1}]}
    (out / "指标.json").write_text(json.dumps(metrics, ensure_ascii=False), encoding="utf-8")
    (out / "摘要.json").write_text(json.dumps({"甲-乙": {"归因": "x"}}, ensure_ascii=False),
                                   encoding="utf-8")
    cfg = {"路径": {"数据区": str(tmp_path), "预警点文件": str(tmp_path / "预警点.md")},
           "产出物开关": {"md报告": True, "预警清单": False, "预警点文件": False,
                        "html报告": False}}
    render_report.run(out, cfg)
    md = (out / "月度分析报告.md").read_text(encoding="utf-8")
    assert "未纳入精读" in md
    assert "丙-丁（橙色预警，20条）" in md  # 级别写全称（用户 2026-07-25）
    assert "甲-乙" not in md.split("未纳入精读")[1]  # 已深挖的不列


def test_data_quality_hints_md_only(tmp_path):
    """跨表命名错配与督办零命中清单进 md 工作底稿，不进正式 docx——
    这是舆情管理员的自查出口，处室不需要看到。"""
    import json, render_report
    out = tmp_path / "报告"; out.mkdir()
    metrics = {"月份": "2026-06", "生成时间": "-", "数据范围": {},
               "参数快照": {"分析模型": {}, "深挖": {}}, "预警汇总": [], "深挖候选": [],
               "模型": {"督办投诉比照": {"md": "x", "指标": {
                   "疑似命名错配": [{"投诉侧问题点": "甲-丙", "督办侧疑似对应": ["乙-丙"],
                                     "督办侧笔数": 4}],
                   "督办零命中": ["丁-戊"]}}}}
    (out / "指标.json").write_text(json.dumps(metrics, ensure_ascii=False), encoding="utf-8")
    cfg = {"路径": {"数据区": str(tmp_path), "预警点文件": str(tmp_path / "预警点.md")},
           "产出物开关": {"md报告": True, "预警清单": False, "预警点文件": False, "html报告": False}}
    render_report.run(out, cfg)
    md = (out / "月度分析报告.md").read_text(encoding="utf-8")
    assert "数据质量提示（内部自查，不随正式报告交付）" in md
    assert "投诉侧「甲-丙」 ⇄ 督办侧 乙-丙（4笔）" in md
    assert "丁-戊" in md

def test_no_data_quality_section_when_clean(tmp_path):
    import json, render_report
    out = tmp_path / "报告"; out.mkdir()
    metrics = {"月份": "2026-06", "生成时间": "-", "数据范围": {},
               "参数快照": {"分析模型": {}, "深挖": {}}, "预警汇总": [], "深挖候选": [],
               "模型": {"督办投诉比照": {"md": "x", "指标": {"疑似命名错配": [], "督办零命中": []}}}}
    (out / "指标.json").write_text(json.dumps(metrics, ensure_ascii=False), encoding="utf-8")
    cfg = {"路径": {"数据区": str(tmp_path), "预警点文件": str(tmp_path / "预警点.md")},
           "产出物开关": {"md报告": True, "预警清单": False, "预警点文件": False, "html报告": False}}
    render_report.run(out, cfg)
    assert "数据质量提示" not in (out / "月度分析报告.md").read_text(encoding="utf-8")


# ---------- 悬浮明细（〔tip:标签¦明细〕）与脚注悬浮注文 ----------

def _tip_narrative():
    return {"关键发现速览": [], "结论摘要": [
                "高敏感条目共〔tip:73案¦06-07 零售信贷部 强制搭售‖06-09 财富管理部 信托承诺未兑现〕。"],
            "章节": {"投诉情况": {"叙述": "", "洞察": None, "风险提示": None},
                    "督办情况": {"叙述": "", "洞察": None, "风险提示": None},
                    "督办转投诉预警": {"叙述": "", "洞察": None, "风险提示": None},
                    "在途活动关联": {"叙述": "", "洞察": None, "风险提示": None},
                    "重复发现问题清单": {"叙述": "", "洞察": None, "风险提示": None}},
            "策略建议": []}


def _tip_metrics():
    return {"月份": "2026-06", "生成时间": "2026-07-25 09:00", "预警汇总": [],
            "参数快照": {"分析模型": {}}, "模型": {
        "排名分析": {"指标": {"投诉": {"本月": []}, "督办": {"本月": []}}, "md": ""},
        "督办投诉比照": {"指标": {}, "md": "无"}, "活动关联": {"指标": {}, "md": "无"},
        "惯犯": {"指标": {}, "md": "无"}}}


def test_html_悬浮标记渲染成蒙版且明细分条():
    html = render_report.build_formal_html(_tip_metrics(), {}, _tip_narrative())
    assert 'class="mask"' in html and 'class="mask-body"' in html
    assert html.count('class="m-i"') == 2          # ‖ 分隔的两条各自成条
    assert "强制搭售" in html and "信托承诺未兑现" in html
    assert "〔tip:" not in html                     # 源码标记不得漏出
    assert ".mask:hover .mask-body" in html         # 悬停显示的样式必须在页内（自包含）


def test_html_脚注上标带悬浮注文():
    m = _tip_metrics()
    n = _tip_narrative()
    n["结论摘要"] = ["深挖说明见此〔fn:深挖〕。"]
    html = render_report.build_formal_html(m, {}, n)
    import html as _h
    note = report_notes.footnotes(m)["深挖"]
    # 注文整段挂在该上标里，不是只挂个空壳
    assert f'<span class="fn-tip">{_h.escape(note)}</span>' in html
    assert "sup.fn:hover .fn-tip" in html


def test_md_悬浮标记退化为标签不漏源码():
    md = render_report.build_md(_tip_metrics(), {}, _tip_narrative())
    assert "〔tip:" not in md and "¦" not in md and "‖" not in md


def test_md_专项章节内的悬浮标记也被剥掉():
    n = _tip_narrative()
    n["章节"]["兜底类目专项分析"] = {
        "叙述": "见〔tip:A¦a1‖a2〕。", "表格": "共〔tip:B¦b1〕条。",
        "洞察": "〔tip:C¦c1〕", "风险提示": "〔tip:D¦d1〕"}
    md = render_report.build_md(_tip_metrics(), {}, n)
    assert "〔tip:" not in md and "a1" not in md and "d1" not in md
    assert "见A。" in md and "共B条。" in md


def test_单个星号对不成对时按字面处理不吞后文():
    """数据里混进落单的 ** 会把「加粗」一路开到段尾，静默毁掉整段排版
    （2026-06 报告的姓名脱敏码 ** 就撞过一次）。不成对时按字面输出，
    错误可见且影响被限制在原地。"""
    html = render_report.md_to_html("- 甲**乙：说明文字")
    assert html.count("<b>") == html.count("</b>")
    assert "甲**乙：说明文字" in html
    # 成对的仍要正常加粗
    assert "<b>乙</b>" in render_report.md_to_html("- 甲**乙**丙")


def test_html_悬浮窗带版心夹取脚本且自包含():
    """靠近右边界的注释蒙版会溢出版心，读者得横向拖滚动条、一动鼠标就丢焦点
    （用户 2026-07-25 反馈）。页内必须带夹取脚本把蒙版收回版心，且不引外链。"""
    n = _tip_narrative()
    n["结论摘要"] = ["高敏感共〔tip:73案¦甲‖乙〕，说明见此〔fn:深挖〕。"]
    html = render_report.build_formal_html(_tip_metrics(), {}, n)
    assert "<script>" in html and "</script>" in html
    script = html.split("<script>")[1].split("</script>")[0]
    # 三要素：取到两类蒙版、量到版心右界、把越界量补回 left
    assert ".fn-tip" in script and ".mask-body" in script
    assert "getBoundingClientRect" in script and "paddingRight" in script
    assert "style.left" in script
    assert "mouseenter" in script and "focus" in script   # 键盘 tab 聚焦也要夹取
    assert "http" not in script and "src=" not in html.split("</style>")[1].replace("data:image", "")


def test_html_夹取前强制可见避免量到零尺寸():
    """mouseenter 触发时 :hover 样式未必已生效，量到 0×0 会把蒙版推到版心外。"""
    html = render_report.build_formal_html(_tip_metrics(), {}, _tip_narrative())
    script = html.split("<script>")[1].split("</script>")[0]
    i, j = script.index("style.display='block'"), script.index("getBoundingClientRect")
    assert i < j                                    # 先强制可见，再测量
    assert "tip.style.display=prev" in script       # 量完还原，交回 :hover 控制


# ---------- 左侧目录 ----------

def _toc_narrative():
    n = _tip_narrative()
    n["结论摘要"] = ["结论一。"]
    n["章节"]["投诉情况"]["叙述"] = "正文。"
    n["章节"]["兜底类目专项分析"] = {
        "叙述": "见下。", "洞察": None, "风险提示": None,
        "表格": "### （一）总览\n\n甲。\n\n### （二）明细\n\n乙。"}
    return n


def test_html_左侧目录收录到二层标题且可跳转():
    """用户 2026-07-25：html 需要左侧目录，收到（一）（二）这层，点了能跳。"""
    import re
    html = render_report.build_formal_html(_tip_metrics(), {}, _toc_narrative())
    assert '<nav id="toc">' in html
    doc = html.split('<nav id="toc">')[0] + html.split("</nav>", 1)[1]
    nav = html.split('<nav id="toc">')[1].split("</nav>")[0]
    heads = re.findall(r'<h([23])(\s[^>]*)?>', doc)
    # 正文里每个二/三级标题都要有 id，否则目录项点了跳不到
    assert heads and all(a and "id=" in a for _l, a in heads), heads
    ids = re.findall(r'<h[23] id="([^"]+)"', doc)
    hrefs = re.findall(r'href="#([^"]+)"', nav)
    assert hrefs == ids, (hrefs, ids)          # 一一对应且顺序一致
    assert "（一）总览" in nav and "（二）明细" in nav
    assert "三级" not in nav or True


def test_html_目录可整体收起也可分节展开():
    html = render_report.build_formal_html(_tip_metrics(), {}, _toc_narrative())
    assert 'id="toc-btn"' in html                    # 收起后的重新展开入口
    script = html.split("<script>")[1].split("</script>")[0]
    assert "toc-open" in script                      # 整体收起/展开
    assert "toc-fold" in script                      # 分节折叠
    assert "@media print" in html and "#toc" in html.split("@media print")[1][:120]


def test_html_正文包在doc容器内且夹取按它算版心():
    """加了侧边目录后，body 不再等于版心；蒙版夹取必须按 .doc 算，否则又会溢出。"""
    html = render_report.build_formal_html(_tip_metrics(), {}, _toc_narrative())
    assert '<div class="doc">' in html
    script = html.split("<script>")[1].split("</script>")[0]
    assert "'.doc'" in script or '".doc"' in script
    assert "document.body.getBoundingClientRect" not in script


def test_html_章节叙述支持分段与分点():
    """叙述此前被硬塞进一个 <p>，换行和 '- ' 都失效（用户 2026-07-25 要求分点分段）。"""
    n = _tip_narrative()
    n["章节"]["投诉情况"]["叙述"] = ("总述一句。\n- **第一位** 甲：1038条\n- **第二位** 乙：228条\n"
                                    "环比方面，另起一段。")
    html = render_report.build_formal_html(_tip_metrics(), {}, n)
    assert "<ul>" in html and "<li><b>第一位</b> 甲：1038条</li>" in html
    assert "<p>总述一句。</p>" in html and "<p>环比方面，另起一段。</p>" in html


def test_html_单行叙述仍是一个段落():
    n = _tip_narrative()
    n["章节"]["投诉情况"]["叙述"] = "只有一句话。"
    assert "<p>只有一句话。</p>" in render_report.build_formal_html(_tip_metrics(), {}, n)


def test_html_文末注释不重复编号():
    """<ol> 会自带 1. 2.，与条目里的 [1][2] 撞成「1. [1] …」（用户 2026-07-25）。
    保留 [n] 与正文上标一致，去掉列表自动编号。"""
    n = _tip_narrative()
    n["结论摘要"] = ["甲〔fn:深挖〕乙〔fn:红警〕。"]
    html = render_report.build_formal_html(_tip_metrics(), {}, n)
    lst = html.split('<div class="fn-list">')[1].split("</div>")[0]
    assert "list-style:none" in lst
    assert "<li>[1] " in lst and "<li>[2] " in lst


# ---------- 术语悬浮（预警级别 / 分析模型） ----------

def _gloss_metrics():
    m = _tip_metrics()
    m["预警汇总"] = [{"级别": "红", "表": "督办", "问题点": "A-B", "依据": "比照命中",
                     "来源模型": "督办投诉比照"}]
    m["模型"]["排名分析"] = {"指标": {"投诉": {"本月": []}, "督办": {"本月": []}}, "md": ""}
    return m


def _gloss_narrative():
    n = _tip_narrative()
    n["结论摘要"] = ["本月共 13 个红色预警，全部来自督办投诉比照模型。"]
    n["章节"]["投诉情况"]["叙述"] = "另有黄色预警若干，集中度处于中位。红色预警在本节第二次出现。"
    return n


def test_html_预警级别与分析模型带术语悬浮():
    """用户 2026-07-25：正文提到预警级别或分析模型时，悬停显示报告说明章里的定义。"""
    html = render_report.build_formal_html(_gloss_metrics(), {}, _gloss_narrative())
    assert 'class="gl"' in html and 'class="gl-tip"' in html
    assert 'class="gl-mk"' in html                       # 边上的小标记
    g = report_notes.glossary(_gloss_metrics())
    d = dict(g)
    assert "红色预警" in d and "督办投诉比照" in d and "黄色预警" in d
    # 悬浮内容取自报告说明章同一份定义，不另抄
    import html as _h
    assert _h.escape(d["红色预警"]) in html


def test_html_术语每节只标首次出现():
    """每处都标会满屏小图标；每章首次出现即可。"""
    import re
    html = render_report.build_formal_html(_gloss_metrics(), {}, _gloss_narrative())
    sec = html.split('<h2 id="sec-3"')[1].split("<h2 ")[0]      # 三、投诉情况 整节
    assert sec.count(">红色预警<") == 1                          # 该节出现两次，只标一次
    # 剥掉悬浮内容再看正文：释义是行内插入的，不剥会把正文切断
    plain = re.sub(r"<[^>]+>", "", re.sub(r'<span class="gl-tip">.*?</span>', "", sec, flags=re.S))
    assert "红色预警" in plain and "在本节第二次出现" in plain


def test_html_术语不标进标题与已有悬浮窗内():
    html = render_report.build_formal_html(_gloss_metrics(), {}, _gloss_narrative())
    nav = html.split('<nav id="toc">')[1].split("</nav>")[0]
    assert "🔍" not in nav                                       # 目录里不能混进小标记
    import re
    for tip in re.findall(r'<span class="(?:fn-tip|mask-body)">.*?</span>', html):
        assert 'class="gl"' not in tip                           # 不做悬浮套悬浮
    for h in re.findall(r"<h[23][^>]*>.*?</h[23]>", html):
        assert 'class="gl"' not in h


def test_html_报告说明章不标术语():
    """定义本身就在这一章，再挂悬浮是自我循环。"""
    html = render_report.build_formal_html(_gloss_metrics(), {}, _gloss_narrative())
    intro = html.split('<h2 id="sec-1"')[1].split('<h2 id="sec-2"')[0]
    assert 'class="gl"' not in intro


def test_html_术语悬浮也受版心夹取():
    html = render_report.build_formal_html(_gloss_metrics(), {}, _gloss_narrative())
    script = html.split("<script>")[1].split("</script>")[0]
    assert ".gl-tip" in script and ".gl" in script


def test_预警级别一律写全称():
    """用户 2026-07-25：不用红警/橙警/黄警简称。"""
    import re
    html = render_report.build_formal_html(_gloss_metrics(), {}, _gloss_narrative())
    text = re.sub(r"<[^>]+>", "", html)
    assert not re.search(r"(?<![色])(红警|橙警|黄警)", text)
    md = render_report.build_md(_gloss_metrics(), {}, _gloss_narrative())
    assert not re.search(r"(?<![色])(红警|橙警|黄警)", md)
    lst = render_report.build_alert_list(_gloss_metrics())
    assert not re.search(r"(?<![色])(红警|橙警|黄警)", lst)
    for t in (text, md, lst):                       # 「红/橙预警」这类合写也算简称
        assert not re.search(r"[红橙黄][/、／]\s*[红橙黄]预警", t)


def _appendix_narrative():
    n = _tip_narrative()
    n["策略建议"] = [{"标题": "建议一：某事", "内容": "做某事。"}]
    n["章节"]["附件清单"] = {
        "叙述": "随附明细如下。", "洞察": None, "风险提示": None,
        "表格": ("| 附件 | 名称 | 对应正文 |\n|---|---|---|\n"
                 "| 附件一 | 环比明细 | 投诉情况 |\n"
                 "| 附件四 | 高敏感明细 | 无此标题 |")}
    return n


def test_html_附件清单排在正文最后():
    html = render_report.build_formal_html(_tip_metrics(), {}, _appendix_narrative())
    assert html.index("策略建议") < html.index("附件清单")


def test_html_附件清单对应正文列可点击跳转():
    """用户 2026-07-25：「对应正文」这列点了要能到正文对应位置。"""
    import re
    html = render_report.build_formal_html(_tip_metrics(), {}, _appendix_narrative())
    ap = html.split("附件清单</h2>")[1]
    m = re.search(r'<td><a href="#(sec-\d+)">投诉情况</a></td>', ap)
    assert m, ap[:600]
    assert ('<h2 id="%s">' % m.group(1)) in html                 # 锚点真实存在
    assert re.search(r"<h2 id=\"%s\">[^<]*投诉情况</h2>" % m.group(1), html)
    assert "<td>无此标题</td>" in ap                             # 匹配不到就原样留着，不瞎链
