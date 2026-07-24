# -*- coding: utf-8 -*-
"""m01 排名：三时间窗 TopN + 意见来源分布 + 日趋势 + 本月vs年度变动标记 + 首进榜黄警"""
import pandas as pd
from month_utils import month_shift

TABLES = {"duban": "督办", "tousu": "投诉"}
DATE_COL = {"duban": "受理时间", "tousu": "受理日期"}

def _window_df(dfs, month, window):
    if window == "本月":
        return dfs.get(month, pd.DataFrame(columns=["问题点"]))
    keys = [k for k in dfs if k.startswith(month[:4])] if window == "今年" else list(dfs)
    return pd.concat([dfs[k] for k in sorted(keys)]) if keys else pd.DataFrame(columns=["问题点"])

def _top(df, n):
    total = len(df)
    vc = df["问题点"].value_counts().head(n)
    return [{"问题点": k, "笔数": int(v), "占比": f"{v/total*100:.1f}%" if total else "-"}
            for k, v in vc.items()]

def _detail(df, points, date_col):
    out = {}
    for p in points:
        sub = df[df["问题点"] == p]
        src = sub["意见来源"].value_counts().head(3)
        days = pd.to_datetime(sub[date_col], errors="coerce").dt.strftime("%d").value_counts().sort_index()
        out[p] = {"意见来源": {k: int(v) for k, v in src.items()},
                  "日趋势": {k: int(v) for k, v in days.items()}}
    return out

def run(ctx, params):
    n, windows = params.get("TopN", 10), params.get("时间窗", ["本月", "今年", "全量"])
    指标, 预警, md = {}, [], []
    for kind, label in TABLES.items():
        dfs = ctx[kind]
        指标[label] = {w: _top(_window_df(dfs, ctx["month"], w), n) for w in windows}
        cur_top = [x["问题点"] for x in 指标[label].get("本月", [])]
        指标[label]["本月明细"] = _detail(_window_df(dfs, ctx["month"], "本月"), cur_top[:5],
                                          DATE_COL[kind])
        # 变动标记：本月 vs 今年榜
        year_rank = {x["问题点"]: i for i, x in enumerate(指标[label].get("今年", []))}
        for i, x in enumerate(指标[label].get("本月", [])):
            p = x["问题点"]
            x["变动"] = "新进榜" if p not in year_rank else ("↑" if year_rank[p] - i >= 3 else "")
        # 首进榜黄警：上月（日历精确）榜里没有的本月上榜点；缺月不猜测，直接跳过（2026-07-07修复：
        # 此前用"排序后取相邻可用月"，缺月时会把更早的月份误当成"上月"）
        prev = month_shift(ctx["month"], -1)
        if prev in dfs:
            prev_top = {x["问题点"] for x in _top(dfs[prev], n)}
            for x in 指标[label].get("本月", []):
                if x["问题点"] not in prev_top:
                    预警.append({"级别": "黄", "表": label, "问题点": x["问题点"],
                                 "依据": f"首次进入{label}本月Top{n}（{x['笔数']}笔）"})
        rows = "\n".join(f"| {i+1} | {x['问题点']} | {x['笔数']} | {x['占比']} | {x.get('变动','')} |"
                         for i, x in enumerate(指标[label].get("本月", [])))
        md.append(f"### {label}·问题点排名（本月）\n\n| # | 问题点 | 笔数 | 占比 | 变动 |\n|---|---|---|---|---|\n{rows}")
    return {"指标": 指标, "预警": 预警, "md": "\n\n".join(md)}
