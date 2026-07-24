# -*- coding: utf-8 -*-
"""m07 惯犯：投诉连续≥N月（日历精确，不含缺口）上榜TopN（与m01 TopN联动）→ 升格进事件库候选池（不出预警条目）"""
from month_utils import month_shift

def run(ctx, params):
    streak_n = params.get("连续月数", 3)
    topn = ctx["config"].get("分析模型", {}).get("排名分析", {}).get("TopN", 10)
    数据月数 = sum(1 for m in ctx["tousu"] if m <= ctx["month"])
    # 日历精确取最近streak_n个连续月份（早→晚）；只要有一个月缺数据就不算"连续"
    # 2026-07-07修复：此前用"排序后取最后N个可用月"，中间缺月会被静默跳过当成连续
    window = [month_shift(ctx["month"], -i) for i in range(streak_n - 1, -1, -1)]
    连续无缺 = all(m in ctx["tousu"] for m in window)
    惯犯 = []
    if 连续无缺:
        tops = [set(ctx["tousu"][m]["问题点"].value_counts().head(topn).index) for m in window]
        # sorted：tops[-1] 是 set，直接迭代会让惯犯表行序随进程变化
        for p in sorted(tops[-1]):
            if all(p in t for t in tops):
                惯犯.append({"问题点": p,
                             "各月笔数": {m: int((ctx["tousu"][m]["问题点"] == p).sum()) for m in window}})
    if 惯犯:
        # 做成表格而非"- 名称：{python dict}"——原写法把字典 repr 直接印进正式报告，
        # 读者看到的是 {'2026-04': 216, ...} 这种带引号大括号的东西（2026-07-21 officecli 体检发现）
        head = ("| 问题点 | " + " | ".join(window) + " | 趋势 |\n"
                "|---|" + "---|" * (len(window) + 1))
        rows = []
        for x in 惯犯:
            v = [x["各月笔数"][m] for m in window]
            trend = "上升" if v[-1] > v[0] else ("下降" if v[-1] < v[0] else "持平")
            rows.append(f"| {x['问题点']} | " + " | ".join(str(n) for n in v) + f" | {trend} |")
        body = head + "\n" + "\n".join(rows)
    else:
        note = f"（近{streak_n}个月数据不连续或不足）" if not 连续无缺 else ""
        body = f"暂无连续{streak_n}个月上榜Top{topn}的问题点{note}"
    md = "### 重复问题清单（升格进事件库候选）\n\n" + body
    return {"指标": {"惯犯": 惯犯, "数据月数": 数据月数}, "预警": [], "md": md}
