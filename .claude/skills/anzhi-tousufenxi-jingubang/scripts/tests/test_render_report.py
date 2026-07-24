# -*- coding: utf-8 -*-
import json
import render_report

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
