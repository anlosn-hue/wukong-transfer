# -*- coding: utf-8 -*-
"""m04 督办×投诉比照：投诉多发类型（近N月TopN ∪ 月均≥阈值）出现在当月督办≥命中门槛 → 红警"""
import pandas as pd

def run(ctx, params):
    look, avg_thr, hit_thr = params.get("回看月数", 3), params.get("月均笔数", 5), params.get("命中门槛", 3)
    topn = ctx["config"].get("分析模型", {}).get("排名分析", {}).get("TopN", 10)
    months = sorted(m for m in ctx["tousu"] if m <= ctx["month"])[-look:]
    if not months:
        return {"指标": {"多发类型": [], "走势": {}}, "预警": [], "md": "### 督办×投诉比照\n\n无投诉数据"}
    concat = pd.concat([ctx["tousu"][m] for m in months])
    counts = concat["问题点"].value_counts()
    prolific = set(counts.head(topn).index) | set(counts[counts / len(months) >= avg_thr].index)
    # sorted(prolific)：prolific 是 set，直接迭代时键序随进程哈希种子变化，
    # 同一份数据每次跑出来的走势 JSON 键序都不同（2026-07-21 实证：5 次 5 种顺序）
    走势 = {p: {m: int((ctx["tousu"][m]["问题点"] == p).sum()) for m in months}
            for p in sorted(prolific)}
    duban = ctx["duban"].get(ctx["month"])
    dcounts = duban["问题点"].value_counts() if duban is not None else pd.Series(dtype=int)
    预警, rows = [], []
    # 同分项按问题点名兜底排序：只按 -counts 排时，笔数相同的几项谁在前取决于
    # prolific（set）的迭代顺序。这不只是表格好不好看的问题——红警顺序会传到
    # 深挖候选排序，深挖有总预算字数上限，截断处有并列时每次跑深挖的对象都不一样
    for p in sorted(prolific, key=lambda x: (-counts[x], x)):
        hits = int(dcounts.get(p, 0))
        rows.append(f"| {p} | {int(counts[p])} | {hits} | {'🔴' if hits >= hit_thr else ''} |")
        if hits >= hit_thr:
            预警.append({"级别": "红", "表": "督办", "问题点": p,
                         # 文案要写清演化方向：督办（未形成投诉）→ 投诉（已形成）。
                         # 旧文案"督办正向投诉演化"被误读成"客户转向监管渠道"（2026-07-21 用户指出）
                         "依据": f"投诉侧多发（近{len(months)}月{int(counts[p])}笔），当月另有{hits}笔"
                                 f"（≥{hit_thr}）同类诉求停留在督办环节，有转为正式投诉的压力"})
    md = (f"### 督办×投诉比照（红警来源）\n\n投诉多发类型 {len(prolific)} 个（近{len(months)}月"
          f"Top{topn} ∪ 月均≥{avg_thr}笔）：\n\n| 问题点 | 近{len(months)}月投诉 | 当月督办 | 命中 |\n"
          f"|---|---|---|---|\n" + "\n".join(rows))
    return {"指标": {"多发类型": sorted(prolific), "走势": 走势}, "预警": 预警, "md": md}
