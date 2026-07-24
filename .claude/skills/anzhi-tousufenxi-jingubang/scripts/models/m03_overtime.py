# -*- coding: utf-8 -*-
"""m03 超时（仅督办）：先全行整体，再按部门（B列映射）分列；部门超时率≥阈值→橙警

口径（2026-07-21 用户定，与原始数据「说明」sheet 的处室口径一致）：
    超时办结率 = 超时笔数 / 当月总督办单量
    超时笔数   = 「超时天数」字段为 1 天及以上的笔数
不再采信「是否超时办结」标志位：真实数据里该字段 2026 年 5-6 月共 3034 行仅 2 行填「是」，
而带超时天数的有 380 行，标志位与天数严重不一致，天数是唯一可靠信号（旧口径下 6 月
全行超时率算出 2.8%，实为 11.6%，低估四倍）。
"""
import pandas as pd

分档 = [("1-3天", 1, 3), ("4-7天", 4, 7), ("8天及以上", 8, None)]


def _days(df):
    return pd.to_numeric(df["超时天数"], errors="coerce")


def _stats(df):
    total = len(df)
    ot = _days(df)
    ot = ot[ot >= 1]
    s = {"总笔数": total, "超时笔数": int(len(ot)),
         "超时办结率": f"{len(ot)/total*100:.1f}%" if total else "-",
         "超时天数均值": round(float(ot.mean()), 1) if len(ot) else 0,
         "超时天数最大": int(ot.max()) if len(ot) else 0}
    for name, lo, hi in 分档:
        s[name] = int(((ot >= lo) & (ot <= hi)).sum()) if hi else int((ot >= lo).sum())
    return s


def run(ctx, params):
    thr = params.get("超时率阈值", 0.10)
    df = ctx["duban"].get(ctx["month"])
    if df is None or not len(df):
        return {"指标": {"全行": {}, "部门": {}}, "预警": [], "md": "### 督办·超时\n\n本月无督办数据"}
    全行 = _stats(df)
    部门, 预警 = {}, []
    for dept, sub in df.groupby("部门"):
        s = _stats(sub)
        部门[dept] = s
        rate = s["超时笔数"] / s["总笔数"] if s["总笔数"] else 0
        if rate >= thr:
            预警.append({"级别": "橙", "表": "督办", "问题点": "",
                         "依据": f"{dept}超时办结率{s['超时办结率']}（≥{thr*100:.0f}%，"
                                 f"超时{s['超时笔数']}/{s['总笔数']}笔，最长{s['超时天数最大']}天）"})
    d = _days(df)
    top = df.assign(_d=d)[d >= 1].nlargest(5, "_d")
    top5 = [{"问题点": r["问题点"], "部门": r["部门"], "超时天数": int(r["_d"])}
            for _, r in top.iterrows()]
    rows = "\n".join(f"| {name} | {s['总笔数']} | {s['超时笔数']} | {s['超时办结率']} | "
                     f"{s['1-3天']}/{s['4-7天']}/{s['8天及以上']} | {s['超时天数均值']} | {s['超时天数最大']} |"
                     for name, s in ([("全行合计", 全行)] +
                                     sorted(部门.items(),
                                            key=lambda x: (-x[1]["超时笔数"], x[0]))))
    md = (f"### 督办·超时办结（全行→部门）\n\n"
          f"**全行**：总{全行['总笔数']}笔，超时{全行['超时笔数']}笔，超时办结率{全行['超时办结率']}；"
          f"超时天数均值{全行['超时天数均值']}天，最长{全行['超时天数最大']}天\n\n"
          f"| 部门 | 总笔数 | 超时笔数 | 超时办结率 | 超时天数分档(1-3/4-7/8+) | 均值天数 | 最长天数 |\n"
          f"|---|---|---|---|---|---|---|\n{rows}")
    return {"指标": {"全行": 全行, "部门": 部门, "超时Top5": top5}, "预警": 预警, "md": md}
