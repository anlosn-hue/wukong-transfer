# -*- coding: utf-8 -*-
"""A 层入口：搜索 → 确定性筛选 → 清单.json + 台账。
用法：python run_search.py <关键词> [--days N] [--channel playwright]"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config
from contract import notes_to_json
from funnel import 筛选A层
from ledger import cap_ok, record_query
from channels import get_channel

def 执行(*, 关键词, 时间窗天数, 输出目录, 台账路径, channel,
        风险语气词, 互动阈值, 单日上限, 通道名="playwright"):
    if not cap_ok(台账路径, 单日上限=单日上限, 层级="A"):
        return {"拒绝": True, "原因": f"已达单日上限（A层查询）{单日上限} 次，明日再试或调 config"}
    notes = channel.search_notes(关键词, 时间窗天数=时间窗天数)
    notes = 筛选A层(notes, 风险语气词=风险语气词, 互动阈值=互动阈值, 时间窗天数=时间窗天数)
    Path(输出目录).mkdir(parents=True, exist_ok=True)
    payload = {"查询": {"关键词": 关键词, "时间窗天数": 时间窗天数, "通道": 通道名},
               **notes_to_json(notes)}
    (Path(输出目录) / "清单.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    record_query(台账路径, 关键词=关键词, 通道=通道名, 层级="A", 抓取量=len(notes))
    命中 = sum(1 for n in notes if n.命中筛选)
    return {"拒绝": False, "总数": len(notes), "命中数": 命中}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("关键词")
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--channel", default=None)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    cfg = load_config()
    通道名 = args.channel or cfg["通道"]["默认"]
    ch = get_channel(通道名)
    if 通道名 == "playwright":
        ch.登录态目录 = cfg["路径"]["登录态目录_绝对"]
        ch.间隔秒 = tuple(cfg["合规"]["请求间隔秒"])
    out = 执行(关键词=args.关键词,
              时间窗天数=args.days or cfg["漏斗"]["A层时间窗天数"],
              输出目录=args.outdir, 台账路径=cfg["路径"]["台账文件_绝对"],
              channel=ch, 风险语气词=cfg["漏斗"]["风险语气词"],
              互动阈值=cfg["漏斗"]["A层互动阈值"], 单日上限=cfg["合规"]["单日查询上限"],
              通道名=通道名)
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()
