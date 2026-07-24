# -*- coding: utf-8 -*-
import report_outline

METRICS = {
    "模型": {
        "排名分析": {
            "指标": {
                "投诉": {"本月": [{"问题点": "借记卡限额", "笔数": 96, "占比": "39.0%", "变动": ""},
                                  {"问题点": "征信异议", "笔数": 12, "占比": "4.9%", "变动": ""}]},
                "督办": {"本月": [{"问题点": "钱大掌柜", "笔数": 7, "占比": "13.2%", "变动": ""}]},
            },
            "md": "占位（不使用，改由report_outline自建分表）",
        },
        "环比同比": {
            "指标": {"投诉": {"环比": "无上月数据", "同比": "无去年同月数据", "骤降提示": []},
                    "督办": {"环比超标上升": [{"问题点": "A/B", "变幅": "+50.0%", "上月": 4, "本月": 6}],
                             "骤降提示": [], "同比": "无去年同月数据"}},
            "md": "占位",
        },
        "新面孔": {"指标": {"投诉": "无上月数据，跳过",
                          "督办": [{"问题点": "新问题/新故障", "笔数": 3}]}, "md": "占位"},
        "集中度": {"指标": {"Top5占比": "58.5%"}, "md": "### 投诉·集中度\n\nTop5占比58.5%"},
        "超时分析": {"指标": {"部门": {"总行数字运营部": {"超时办结率": "0.0%"},
                                    "总行财富管理部": {"超时办结率": "30.8%"}}},
                   "md": "### 督办·超时办结\n\n表格内容"},
        "督办投诉比照": {"指标": {}, "md": "### 督办×投诉比照\n\n表格内容"},
        "活动关联": {"指标": {}, "md": "### 在途活动/系统变更关联投诉\n\n表格内容"},
        "惯犯": {"指标": {}, "md": "### 惯犯清单\n\n暂无"},
    }
}
SUMMARIES = {}
NARRATIVE = {
    "章节": {
        "投诉情况": {"叙述": "投诉呈点状集中。", "洞察": None, "风险提示": None},
        "督办情况": {"叙述": "督办分布分散。", "洞察": "建议专项督办。", "风险提示": None},
        "督办转投诉预警": {"叙述": "本月无红警。", "洞察": None, "风险提示": None},
        "在途活动关联": {"叙述": "本月无在途活动。", "洞察": None, "风险提示": None},
        "重复发现问题清单": {"叙述": "数据积累中。", "洞察": None, "风险提示": None},
    }
}

def test_outline_has_five_sections_in_order():
    outline = report_outline.build_outline(METRICS, SUMMARIES, NARRATIVE)
    assert [s["title"] for s in outline] == [
        "投诉情况", "督办情况", "督办转投诉预警", "在途活动关联", "重复发现问题清单"]

def test_tousu_section_table_and_chart_from_raw_metrics():
    outline = report_outline.build_outline(METRICS, SUMMARIES, NARRATIVE)
    tousu = outline[0]
    assert "借记卡限额" in tousu["table_md"] and "96" in tousu["table_md"]
    assert "Top5占比58.5%" in tousu["table_md"]  # 集中度md直接拼入
    assert tousu["narrative"] == "投诉呈点状集中。"
    assert tousu["chart"]["labels"] == ["借记卡限额", "征信异议"]
    assert tousu["chart"]["series"]["笔数"] == [96, 12]

def test_duban_section_includes_overtime_and_dept_chart():
    outline = report_outline.build_outline(METRICS, SUMMARIES, NARRATIVE)
    duban = outline[1]
    assert "钱大掌柜" in duban["table_md"]
    assert "表格内容" in duban["table_md"]  # 超时分析md拼入
    assert duban["insight"] == "建议专项督办。"
    assert duban["chart"]["labels"] == ["总行数字运营部", "总行财富管理部"]
    assert duban["chart"]["series"]["超时办结率(%)"] == [0.0, 30.8]

def test_mom_yoy_and_newcomers_text_included_in_both_sections():
    outline = report_outline.build_outline(METRICS, SUMMARIES, NARRATIVE)
    tousu, duban = outline[0], outline[1]
    assert "无上月数据" in tousu["table_md"]  # 投诉侧环比+新面孔跳过文案
    assert "环比明细" in duban["table_md"] and "A/B" in duban["table_md"]  # 环比已改表格展示
    assert "新问题/新故障" in duban["table_md"]

def test_m04_and_m07_trend_charts_restored():
    metrics = {"模型": dict(METRICS["模型"])}
    metrics["模型"]["督办投诉比照"] = {
        "指标": {"走势": {"A/B": {"2026-05": 3, "2026-06": 8}, "C/D": {"2026-05": 1, "2026-06": 1}}},
        "md": "占位"}
    metrics["模型"]["惯犯"] = {
        "指标": {"惯犯": [{"问题点": "E/F", "各月笔数": {"2026-04": 3, "2026-05": 5, "2026-06": 8}}]},
        "md": "占位"}
    outline = report_outline.build_outline(metrics, SUMMARIES, NARRATIVE)
    红警章节 = outline[2]  # 督办转投诉预警
    assert 红警章节["chart"]["type"] == "line"
    assert 红警章节["chart"]["series"] == {"2026-05": 3, "2026-06": 8}  # 取合计笔数更高的A/B，不是C/D
    重复章节 = outline[4]  # 重复发现问题清单
    assert 重复章节["chart"]["type"] == "line"
    assert 重复章节["chart"]["series"] == {"2026-04": 3, "2026-05": 5, "2026-06": 8}

def test_mom_yoy_and_newcomers_zero_result_branches():
    metrics = {"模型": dict(METRICS["模型"])}
    metrics["模型"]["环比同比"] = {
        "指标": {"投诉": {"环比超标上升": [], "骤降提示": [], "同比": "无去年同月数据"},
                "督办": {"环比超标上升": [], "骤降提示": [], "同比": "无去年同月数据"}},
        "md": "占位"}
    metrics["模型"]["新面孔"] = {"指标": {"投诉": [], "督办": []}, "md": "占位"}
    outline = report_outline.build_outline(metrics, SUMMARIES, NARRATIVE)
    tousu, duban = outline[0], outline[1]
    assert "投诉侧本月无环比超标上升或骤降项" in tousu["table_md"]
    assert "投诉侧本月无新面孔问题点" in tousu["table_md"]
    assert "督办侧本月无环比超标上升或骤降项" in duban["table_md"]
    assert "督办侧本月无新面孔问题点" in duban["table_md"]

def test_duban_chart_handles_dash_overtime_rate():
    metrics = {"模型": dict(METRICS["模型"])}
    metrics["模型"]["超时分析"] = {
        "指标": {"部门": {"总行数字运营部": {"超时办结率": "-"},
                        "总行财富管理部": {"超时办结率": "12.5%"}}},
        "md": "占位"}
    outline = report_outline.build_outline(metrics, SUMMARIES, NARRATIVE)
    duban = outline[1]
    assert duban["chart"]["series"]["超时办结率(%)"] == [0.0, 12.5]
