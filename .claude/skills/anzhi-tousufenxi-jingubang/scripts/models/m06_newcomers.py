# -*- coding: utf-8 -*-
"""m06 新面孔：上月为零、本月冒出≥门槛的诉点（督办+投诉都查）→ 黄警"""
from month_utils import month_shift

TABLES = {"duban": "督办", "tousu": "投诉"}

def run(ctx, params):
    thr = params.get("门槛", 3)
    指标, 预警 = {}, []
    for kind, label in TABLES.items():
        cur = ctx[kind].get(ctx["month"])
        # 日历精确取上月（2026-07-07修复：此前用"排序后取相邻可用月"，缺月时会误把更早月份当上月）
        prev_df = ctx[kind].get(month_shift(ctx["month"], -1))
        if cur is None or prev_df is None:
            指标[label] = "无上月数据，跳过"
            continue
        prev_set = set(prev_df["问题点"])
        news = []
        for p, c in cur["问题点"].value_counts().items():
            if p not in prev_set and c >= thr:
                news.append({"问题点": p, "笔数": int(c)})
                预警.append({"级别": "黄", "表": label, "问题点": p,
                             "依据": f"新面孔：上月0笔→本月{c}笔（≥{thr}），或为新业务/新故障早期信号"})
        指标[label] = news
    total = sum(len(v) for v in 指标.values() if isinstance(v, list))
    return {"指标": 指标, "预警": 预警,
            "md": f"### 新面孔诉点\n\n本月新冒出 {total} 个（详见预警总览黄色预警条目）"}
