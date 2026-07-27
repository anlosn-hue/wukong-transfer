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
                         # 口径＝两张表的重合部分，不是时间上的流向（2026-07-25 用户定）；
                         # 也不是"客户转向监管渠道"（2026-07-21）
                         "依据": f"投诉侧多发（近{len(months)}月{int(counts[p])}笔），当月督办侧同一诉点"
                                 f"又有{hits}笔（≥{hit_thr}），两表重合，属潜在投诉风险点"})
    # 疑似跨表命名错配兜底探测（2026-07-25 新增）：本模型按「二级菜单-三级菜单」拼接串
    # 精确匹配两张表。两表对同一业务概念的二级菜单命名不同时，匹配恒为 0，红警静默漏报——
    # 不报错、不告警，只是少一条红警。2026-06 即因此漏掉「借记卡增值权益服务问题-积点权益
    # 供应商服务问题」。已知不一致由 normalize 的菜单映射修掉；此处兜底发现映射表尚未收录的。
    # 「督办零命中」是比「疑似错配」更宽的兜底：错配探测只认「三级菜单相同、二级菜单不同」，
    # 若三级菜单名也漂移就探不到。多发诉点在督办侧一笔都没有本身就值得看一眼——
    # 要么确实没有同类督办，要么命名对不上，人工扫一遍即可分辨。
    零命中 = [p for p in sorted(prolific, key=lambda x: (-counts[x], x))
              if int(dcounts.get(p, 0)) == 0]
    疑似错配 = []
    if duban is not None and "三级菜单" in duban.columns:
        tousu_all = concat
        for p in sorted(prolific, key=lambda x: (-counts[x], x)):
            if int(dcounts.get(p, 0)) > 0:
                continue  # 已匹配上，不是错配
            lv3 = set(tousu_all.loc[tousu_all["问题点"] == p, "三级菜单"].dropna().astype(str)) - {""}
            if not lv3:
                continue
            同三级 = duban[duban["三级菜单"].astype(str).isin(lv3)]
            候选 = sorted(set(同三级["问题点"].astype(str)) - {p})
            if 候选:
                疑似错配.append({"投诉侧问题点": p, "督办侧疑似对应": 候选,
                                 "督办侧笔数": int(len(同三级))})
    md = (f"### 督办×投诉比照（红色预警来源）\n\n投诉多发类型 {len(prolific)} 个（近{len(months)}月"
          f"Top{topn} ∪ 月均≥{avg_thr}笔）：\n\n| 诉点 | 近{len(months)}月投诉 | 当月督办 | 命中 |\n"
          f"|---|---|---|---|\n" + "\n".join(rows))
    if 疑似错配:
        md += ("\n\n> ⚠️ 疑似跨表命名错配（督办侧命中为 0，但存在同三级菜单、异二级菜单的督办记录），"
               "须人工确认后补入 `底库/菜单映射.yaml`：\n\n"
               + "\n".join(f"> - 投诉侧「{m['投诉侧问题点']}」 ⇄ 督办侧 {'、'.join(m['督办侧疑似对应'])}"
                           f"（{m['督办侧笔数']} 笔）" for m in 疑似错配))
    return {"指标": {"多发类型": sorted(prolific), "走势": 走势, "疑似命名错配": 疑似错配,
                     "督办零命中": 零命中},
            "预警": 预警, "md": md}
