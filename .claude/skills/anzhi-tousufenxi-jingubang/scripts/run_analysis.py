# -*- coding: utf-8 -*-
"""模型管线：读底库→按注册表跑启用模型→汇总预警→写指标.json
用法：python run_analysis.py <底库dir> <月份YYYY-MM> <config.yaml> <输出dir>"""
import importlib, json, sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import yaml
from models import REGISTRY

LEVEL_ORDER = {"红": 0, "橙": 1, "黄": 2}

def load_lib(lib_dir):
    data = {}
    for kind in ("duban", "tousu"):
        data[kind] = {}
        for f in sorted(Path(lib_dir, kind).glob("*.csv")):
            data[kind][f.stem] = pd.read_csv(f, encoding="utf-8-sig", dtype={"超时天数": float}
                                             if kind == "duban" else None)
    return data

def sort_warnings(ws):
    return sorted(ws, key=lambda w: LEVEL_ORDER.get(w.get("级别"), 9))

def estimate_dig_candidates(ctx, warnings, dig_cfg):
    """红橙预警问题点 → 当月文本量预估，供 L2 切批决策"""
    cands, seen = [], set()
    for w in warnings:
        p = w.get("问题点")
        if not p or p in seen or w["级别"] not in dig_cfg.get("深挖预警级别", ["红", "橙"]):
            continue
        seen.add(p)
        chars = rows = 0
        for kind in ("duban", "tousu"):
            df = ctx[kind].get(ctx["month"])
            if df is None:
                continue
            hit = df[df["问题点"] == p]
            rows += len(hit)
            chars += int(hit["客户反馈内容"].fillna("").str.len().sum()
                         + hit["处理结果"].fillna("").str.len().sum())
        cands.append({"问题点": p, "级别": w["级别"], "条数": rows, "预估字数": chars})
    return cands

def data_scope(ctx):
    """本期数据范围：两张表各自的条数与实际出现的部门/机构清单，供报告首章「报告说明」渲染。
    督办侧取映射后的标准部门名，投诉侧取原始责任机构（含合并称谓，不再二次拆分）。"""
    out = {}
    for kind, label, col in (("duban", "督办", "部门"), ("tousu", "投诉", "责任机构")):
        df = ctx[kind].get(ctx["month"])
        if df is None or not len(df) or col not in df.columns:
            out[label] = {"条数": 0, "机构": []}
            continue
        vals = sorted({str(v).strip() for v in df[col].dropna() if str(v).strip()})
        out[label] = {"条数": int(len(df)), "机构": vals}
    return out


def run(lib_dir, month, config, out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    data = load_lib(lib_dir)
    # ctx 在本次 run() 内被所有启用模型共享同一份引用（DataFrame/dict 均未拷贝）。
    # 模型的 run(ctx, params) 只应读取 ctx，不得写入/修改其中的 DataFrame 或 dict——
    # 否则前一个模型的改动会静默泄漏给按 REGISTRY 顺序之后运行的模型。派生数据只能通过返回值传递。
    ctx = {"month": month, "duban": data["duban"], "tousu": data["tousu"],
           "config": config, "activity_index": config["路径"].get("活动方案库INDEX")}
    models_out, warnings = {}, []
    for name, mod_name in REGISTRY.items():
        params = config.get("分析模型", {}).get(name, {})
        if not params.get("启用", False):
            continue
        mod = importlib.import_module(f"models.{mod_name}")
        r = mod.run(ctx, params)
        models_out[name] = {"指标": r["指标"], "md": r["md"]}
        warnings += [dict(w, 来源模型=name) for w in r["预警"]]
    warnings = sort_warnings(warnings)
    result = {"月份": month, "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
              "参数快照": {"分析模型": config.get("分析模型", {}), "深挖": config.get("深挖", {})},
              "数据范围": data_scope(ctx),
              "预警汇总": warnings, "模型": models_out,
              "深挖候选": estimate_dig_candidates(ctx, warnings, config.get("深挖", {}))}
    (out_dir / "指标.json").write_text(json.dumps(result, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    return result

if __name__ == "__main__":
    lib, month, cfg_path, out = sys.argv[1:5]
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    r = run(lib, month, cfg, out)
    print(json.dumps({"预警数": len(r["预警汇总"]), "深挖候选": r["深挖候选"],
                      "模型": list(r["模型"])}, ensure_ascii=False, indent=1))
