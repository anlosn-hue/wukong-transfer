# -*- coding: utf-8 -*-
"""m08 活动关联：解析活动方案库INDEX表格，在途活动/系统变更的risk_keywords在当月两表反馈文本中检索"""
import re
from pathlib import Path

COLS = ["活动ID", "活动名", "来源", "类型", "客群", "时间窗", "渠道", "状态",
        "风险等级", "舆情关键词", "下次盯盘节点", "评估校正"]

def parse_index(path):
    if not path:  # ctx里键缺失/None/空串——避免 Path("") 解析成当前目录导致 read_text() 崩溃
        return []
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|") or set(line.replace("|", "").strip()) <= {"-", " "}:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < len(COLS) or cells[0] == COLS[0]:
            continue
        rows.append(dict(zip(COLS, cells)))
    return rows

def _covers_month(window, month, status):
    m = re.findall(r"(\d{4}-\d{2})-\d{2}", window)
    if len(m) >= 2:
        return m[0] <= month <= m[1]
    if len(m) == 1:  # "2026-07-03~长期" 或单端待填（起始/结束二者之一已知）
        start_in = window.strip().startswith(m[0][:7]) or window.split("~")[0].strip().startswith(m[0])
        if "长期" in window and start_in:
            return m[0] <= month
        if not start_in:  # 已知结束日期、起始待填（"待填~YYYY-MM-DD"）：不能因为忘改状态就无限期在途
            return status == "进行中" and month <= m[0]
        return status == "进行中"
    return status == "进行中"  # 双端待填：只看状态

def run(ctx, params):
    acts = [a for a in parse_index(ctx.get("activity_index") or "")
            if _covers_month(a["时间窗"], ctx["month"], a["状态"])]
    if not acts:
        return {"指标": {"活动": []}, "预警": [],
                "md": "### 在途活动/系统变更关联投诉\n\n本月无在途活动/变更（或活动方案库不可用）"}
    结果 = []
    for a in acts:
        kws = [k.strip() for k in re.split(r"[,，]", a["舆情关键词"]) if k.strip()]
        item = {"活动名": a["活动名"], "类型": a["类型"], "时间窗": a["时间窗"],
                "督办命中": 0, "投诉命中": 0, "命中关键词": {}}
        for kind, field in (("duban", "督办命中"), ("tousu", "投诉命中")):
            df = ctx[kind].get(ctx["month"])
            if df is None:
                continue
            text = df["客户反馈内容"].fillna("")
            hit_mask = None
            for kw in kws:
                m = text.str.contains(re.escape(kw), na=False)
                if m.any():
                    item["命中关键词"][kw] = item["命中关键词"].get(kw, 0) + int(m.sum())
                hit_mask = m if hit_mask is None else (hit_mask | m)
            item[field] = int(hit_mask.sum()) if hit_mask is not None else 0
        结果.append(item)
    rows = "\n".join(f"| {x['活动名']} | {x['类型']} | {x['督办命中']} | {x['投诉命中']} | "
                     f"{'、'.join(f'{k}×{v}' for k, v in sorted(x['命中关键词'].items(), key=lambda y: (-y[1], y[0]))[:3]) or '-'} |"
                     for x in 结果)
    md = ("### 在途活动/系统变更关联投诉\n\n"
          "⚠️ 关键词命中为初筛，同词不同事的误命中由 L2 深挖确认后在归因摘要中说明。\n\n"
          f"| 活动/变更 | 类型 | 督办命中 | 投诉命中 | 主要命中词 |\n|---|---|---|---|---|\n{rows}")
    return {"指标": {"活动": 结果}, "预警": [], "md": md}
