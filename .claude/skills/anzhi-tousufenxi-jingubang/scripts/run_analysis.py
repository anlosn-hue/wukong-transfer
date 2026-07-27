# -*- coding: utf-8 -*-
"""模型管线：读底库→按注册表跑启用模型→汇总预警→写指标.json
用法：python run_analysis.py <底库dir> <月份YYYY-MM> <config.yaml> <输出dir>"""
import importlib, json, sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import yaml
import normalize
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

def _meta(lib_dir):
    p = Path(lib_dir) / "_meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def data_scope(ctx, dept_map=None):
    """本期数据范围：两张表各自的条数与实际出现的部门清单，供报告首章「报告说明」渲染。

    两侧都过一遍部门映射（督办侧「部门」列已在 normalize 阶段映射过，此处幂等；
    投诉侧「责任机构」是原始写法，含行名与合并称谓）。报告正文一律写「总行XX部」，
    不写行名、不列本期口径外的部门——规范 A2，2026-06 报告即因投诉侧原样保留
    「兴业银行零售金融部/消费者权益保护办公室/养老金融部」被处室修订（knowledge/tools/报告体例规范.md）。
    映射表里没有的原样保留，不静默丢弃——留着被人看见才会去补映射。"""
    dept_map = dept_map or {}
    out = {}
    for kind, label, col in (("duban", "督办", "部门"), ("tousu", "投诉", "责任机构")):
        df = ctx[kind].get(ctx["month"])
        if df is None or not len(df) or col not in df.columns:
            out[label] = {"条数": 0, "机构": []}
            continue
        vals = sorted({dept_map.get(s, s) for s in
                       (str(v).strip() for v in df[col].dropna()) if s})
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
              "数据范围": data_scope(ctx, normalize.load_dept_map(Path(lib_dir) / "部门映射.yaml")),
              "菜单归一": _meta(lib_dir).get("菜单归一", []),
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
