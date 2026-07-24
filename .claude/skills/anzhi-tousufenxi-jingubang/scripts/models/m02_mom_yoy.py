# -*- coding: utf-8 -*-
"""m02 环比同比：双向±阈值；正向且满足绝对增量→橙警；负向仅提示；同比缺数据则标注"""
from month_utils import month_shift

TABLES = {"duban": "督办", "tousu": "投诉"}

def _counts(dfs, month):
    df = dfs.get(month)
    return df["问题点"].value_counts().to_dict() if df is not None else None

def run(ctx, params):
    thr, abs_thr = params.get("阈值", 0.20), params.get("绝对增量门槛", 5)
    指标, 预警, md = {}, [], []
    for kind, label in TABLES.items():
        cur = _counts(ctx[kind], ctx["month"]) or {}
        prev = _counts(ctx[kind], month_shift(ctx["month"], -1))
        yoy = _counts(ctx[kind], month_shift(ctx["month"], -12))
        同比 = "无去年同月数据" if yoy is None else "已启用"  # 与"环比"是否可算独立，缺项各自标注不互相覆盖
        rises, drops = [], []
        if prev is None:
            指标[label] = {"环比": "无上月数据", "同比": 同比, "骤降提示": []}
        else:
            for p in sorted(set(cur) | set(prev)):
                c, pv = cur.get(p, 0), prev.get(p, 0)
                if pv == 0:
                    continue  # 新面孔归 m06
                pct = (c - pv) / pv
                item = {"问题点": p, "上月": pv, "本月": c, "变幅": f"{pct*100:+.1f}%"}
                if pct >= thr and c - pv >= abs_thr:
                    rises.append(item)
                    预警.append({"级别": "橙", "表": label, "问题点": p,
                                 "依据": f"环比{item['变幅']}（{pv}→{c}笔，增量≥{abs_thr}）"})
                elif pct <= -thr:
                    drops.append(item)
            指标[label] = {"环比超标上升": rises, "骤降提示": drops, "同比": 同比}
        md.append(f"### {label}·环比变动\n\n" + (
            "无上月数据（首月运行）" if prev is None else
            f"超标上升 {len(rises)} 项（详见预警），骤降 {len(drops)} 项（或为问题解决/口径变化）"))
    return {"指标": 指标, "预警": 预警, "md": "\n\n".join(md)}
