# -*- coding: utf-8 -*-
"""m05 集中度：投诉本月 Top5 诉点占总量比重（点状 vs 面上）"""

def run(ctx, params):
    df = ctx["tousu"].get(ctx["month"])
    if df is None or not len(df):
        return {"指标": {"Top5占比": "-"}, "预警": [], "md": "### 投诉·集中度\n\n本月无投诉数据"}
    top5 = df["问题点"].value_counts().head(5)
    share = top5.sum() / len(df)
    指标 = {"Top5占比": f"{share*100:.1f}%",
            "Top5明细": {k: int(v) for k, v in top5.items()}, "总笔数": len(df)}
    md = (f"### 投诉·集中度\n\nTop5 诉点合计 {int(top5.sum())} 笔，占当月投诉总量 "
          f"{指标['Top5占比']}——{'点状集中，优先攻坚头部问题' if share >= 0.5 else '分布较散，属面上波动'}")
    return {"指标": 指标, "预警": [], "md": md}
