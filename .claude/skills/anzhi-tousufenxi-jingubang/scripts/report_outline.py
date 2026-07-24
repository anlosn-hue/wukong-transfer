# -*- coding: utf-8 -*-
"""构建正式报告的结构化章节大纲：合并 指标.json（8模型定量）+ 摘要.json（L2归因）
+ 叙述.json（LLM撰写的书面分析）→ 章节列表，docx/html渲染器共同消费，避免逻辑重复。
每个章节: {"title", "narrative", "insight"(可None), "risk"(可None), "table_md", "chart"(可None)}
chart 结构: {"type": "bar"|"line", "labels": [...]（bar专用）,
             "series": {"系列名": [...]}（bar多系列/line单系列同key）, "title": str}"""


def _top_table_md(rows, cols=("问题点", "笔数", "占比")):
    if not rows:
        return "（本月无数据）"
    head = "| # | " + " | ".join(cols) + " |"
    sep = "|---|" + "---|" * len(cols)
    body = "\n".join(f"| {i+1} | " + " | ".join(str(r.get(c, "-")) for c in cols) + " |"
                     for i, r in enumerate(rows))
    return "\n".join([head, sep, body])


def _mom_yoy_table(kind_metrics, label):
    """环比变动明细做成表格（原先是大段文字堆砌，不直观）；超标上升与骤降各成一段表。"""
    if "环比" in kind_metrics:  # 无上月数据分支（首月运行）
        return f"{label}侧{kind_metrics['环比']}，{kind_metrics['同比']}。"
    rises = kind_metrics.get("环比超标上升", [])
    drops = kind_metrics.get("骤降提示", [])
    if not rises and not drops:
        return f"{label}侧本月无环比超标上升或骤降项。"
    rows = [(x["问题点"], x["上月"], x["本月"], x["变幅"], "上升") for x in rises] + \
           [(x["问题点"], x["上月"], x["本月"], x["变幅"], "骤降") for x in drops]
    head = "| 问题点 | 上月 | 本月 | 变幅 | 类型 |\n|---|---|---|---|---|"
    body = "\n".join(f"| {p} | {pv} | {c} | {pct} | {t} |" for p, pv, c, pct, t in rows)
    return f"{label}侧环比明细：\n\n{head}\n{body}"


def _newcomers_text(kind_metrics, label):
    if isinstance(kind_metrics, str):
        return f"{label}侧{kind_metrics}。"
    if not kind_metrics:
        return f"{label}侧本月无新面孔问题点。"
    return f"{label}侧新面孔 {len(kind_metrics)} 个：" + "；".join(
        f"{x['问题点']}（{x['笔数']}笔）" for x in kind_metrics)


def _sec(narrative, title, table_md, chart, note=None):
    c = narrative.get("章节", {}).get(title, {})
    # 叙述.json 里的自定义章节可自带「表格」（markdown），优先于模型产出的默认表格
    return {"title": title, "narrative": c.get("叙述", ""), "insight": c.get("洞察"),
            "risk": c.get("风险提示"), "table_md": c.get("表格") or table_md,
            "chart": chart, "note": note}


def _warned_by(metrics, model_name):
    return [w for w in metrics.get("预警汇总", []) if w.get("来源模型") == model_name]


def _huanbi_note(metrics):
    """环比预警判定标准（仅当本节确有环比预警时才附注，标准来自config，非编造）"""
    if not _warned_by(metrics, "环比同比"):
        return None
    p = metrics.get("参数快照", {}).get("分析模型", {}).get("环比同比", {})
    thr, abs_thr = p.get("阈值", 0.2), p.get("绝对增量门槛", 5)
    return f"注：环比预警判定标准为变幅≥{thr*100:.0f}%且增量≥{abs_thr}笔（与上月同问题点笔数对比，两者同时满足才计入橙色预警）。"


def _overtime_note(metrics):
    if not _warned_by(metrics, "超时分析"):
        return None
    p = metrics.get("参数快照", {}).get("分析模型", {}).get("超时分析", {})
    thr = p.get("超时率阈值", 0.10)
    return f"注：部门超时预警判定标准为该部门督办超时办结率≥{thr*100:.0f}%。"


def _escalation_note(metrics):
    if not _warned_by(metrics, "督办投诉比照"):
        return None
    p = metrics.get("参数快照", {}).get("分析模型", {}).get("督办投诉比照", {})
    look, avg, hit = p.get("回看月数", 3), p.get("月均笔数", 20), p.get("命中门槛", 10)
    # 方向必须写清：督办（未形成投诉）→ 投诉（已形成），不是"投诉向督办演化"，
    # 更不是"客户转向监管渠道"（2026-07-21 用户指出原文案误导）
    return (f"注：红色预警判定标准为投诉侧近{look}个月月均≥{avg}笔的多发问题点，"
            f"且当月督办命中≥{hit}笔，视为仍有同类诉求停留在督办环节、有转为正式投诉的压力。")


def _combine_notes(*notes):
    parts = [n for n in notes if n]
    return "\n".join(parts) if parts else None


def _tousu_section(m, narrative, metrics):
    rank = m.get("排名分析", {}).get("指标", {}).get("投诉", {}).get("本月", [])
    parts = [_top_table_md(rank)]
    if "环比同比" in m:
        parts.append(_mom_yoy_table(m["环比同比"]["指标"].get("投诉", {}), "投诉"))
    if "新面孔" in m:
        parts.append(_newcomers_text(m["新面孔"]["指标"].get("投诉", "无上月数据，跳过"), "投诉"))
    if "集中度" in m:
        parts.append(m["集中度"]["md"])
    chart = {"type": "bar", "labels": [x["问题点"] for x in rank[:10]],
             "series": {"笔数": [x["笔数"] for x in rank[:10]]},
             "title": "投诉问题点排名（本月）", "xlabel": "笔数"} if rank else None
    return _sec(narrative, "投诉情况", "\n\n".join(parts), chart, _huanbi_note(metrics))


def _duban_section(m, narrative, metrics):
    rank = m.get("排名分析", {}).get("指标", {}).get("督办", {}).get("本月", [])
    parts = [_top_table_md(rank)]
    if "环比同比" in m:
        parts.append(_mom_yoy_table(m["环比同比"]["指标"].get("督办", {}), "督办"))
    if "新面孔" in m:
        parts.append(_newcomers_text(m["新面孔"]["指标"].get("督办", "无上月数据，跳过"), "督办"))
    if "超时分析" in m:
        parts.append(m["超时分析"]["md"])
    dept = m.get("超时分析", {}).get("指标", {}).get("部门", {})
    chart = {"type": "bar", "labels": list(dept.keys()),
             "series": {"超时办结率(%)": [float(v["超时办结率"].rstrip("%"))
                                        if v.get("超时办结率", "-") != "-" else 0.0
                                        for v in dept.values()]},
             "title": "各部门超时办结率", "xlabel": "超时办结率（%）"} if dept else None
    return _sec(narrative, "督办情况", "\n\n".join(parts), chart,
                _combine_notes(_huanbi_note(metrics), _overtime_note(metrics)))


def build_outline(metrics, summaries, narrative):
    m = metrics["模型"]
    结果 = [_tousu_section(m, narrative, metrics), _duban_section(m, narrative, metrics)]

    m04 = m.get("督办投诉比照", {})
    trend = m04.get("指标", {}).get("走势", {})
    m04_chart = None
    if trend:
        # 走势可能有多个问题点，取笔数合计最高的一个展示，避免章节里堆太多图表
        top_p = max(trend, key=lambda p: sum(trend[p].values()))
        m04_chart = {"type": "line", "series": trend[top_p], "title": f"{top_p}·督办走势"}
    结果.append(_sec(narrative, "督办转投诉预警", m04.get("md", "（本月无数据）"), m04_chart,
                    _escalation_note(metrics)))

    m08 = m.get("活动关联", {})
    结果.append(_sec(narrative, "在途活动关联", m08.get("md", "（本月无数据）"), None))

    m07 = m.get("惯犯", {})
    repeaters = m07.get("指标", {}).get("惯犯", [])
    m07_chart = ({"type": "line", "series": repeaters[0]["各月笔数"],
                  "title": f"{repeaters[0]['问题点']}·重复发现走势"}
                 if repeaters else None)
    结果.append(_sec(narrative, "重复发现问题清单", m07.get("md", "（本月无数据）"), m07_chart))

    # 叙述.json 中自定义的额外章节（如专项说明）追加到末尾
    for title in extra_titles(narrative):
        结果.append(_sec(narrative, title, "（本节为专项说明，无固定表格）", None))

    return 结果


FIXED_TITLES = {"投诉情况", "督办情况", "督办转投诉预警", "在途活动关联", "重复发现问题清单"}


def extra_titles(narrative):
    return [t for t in narrative.get("章节", {}) if t not in FIXED_TITLES]
