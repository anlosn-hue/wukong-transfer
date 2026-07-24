# -*- coding: utf-8 -*-
"""C 层入口：读研判.json 里高风险笔记的 top-N，抓评论写入 评论/<id>.txt。
人工确认闸门 / --auto-deep 由 SKILL.md 控制；本脚本只负责抓取执行。
用法：python run_fetch_comments.py --outdir <目录>"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config
from contract import notes_from_json
from ledger import record_query, 会话抓取数
from channels import get_channel
from channels.playwright_channel import BlockedError

def 执行(*, 输出目录, 台账路径, channel, 下钻上限, 通道名, 会话上限=None, 关键词=""):
    d = Path(输出目录)
    清单 = json.loads((d / "清单.json").read_text(encoding="utf-8"))
    关键词 = 关键词 or 清单.get("查询", {}).get("关键词", "")
    notes = {n.id: n for n in notes_from_json(清单)}
    研判 = json.loads((d / "研判.json").read_text(encoding="utf-8")).get("研判", [])
    高风险ids = [r["id"] for r in 研判 if r.get("高风险")][:下钻上限]
    评论目录 = d / "评论"
    评论目录.mkdir(parents=True, exist_ok=True)
    下钻数, 中断 = 0, None
    for nid in 高风险ids:
        n = notes.get(nid)
        if not n:
            continue
        if 会话上限 is not None and 会话抓取数(输出目录) >= 会话上限:
            中断 = f"会话抓取上限 {会话上限} 已达，停止本次深挖"
            break
        try:
            cs = channel.fetch_comments(n)
        except BlockedError as e:
            中断 = f"{nid}: {e}"
            break
        (评论目录 / f"{nid}.txt").write_text("\n".join(cs), encoding="utf-8")
        下钻数 += 1
    record_query(台账路径, 关键词=关键词, 通道=通道名, 层级="C", 抓取量=下钻数)
    return {"下钻数": 下钻数, "中断": 中断}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    cfg = load_config()
    通道名 = cfg["通道"]["默认"]
    ch = get_channel(通道名)
    if 通道名 == "playwright":
        ch.登录态目录 = cfg["路径"]["登录态目录_绝对"]
        ch.间隔秒 = tuple(cfg["合规"]["请求间隔秒"])
    out = 执行(输出目录=args.outdir, 台账路径=cfg["路径"]["台账文件_绝对"],
              channel=ch, 下钻上限=cfg["漏斗"]["C层下钻上限"], 通道名=通道名,
              会话上限=cfg["合规"]["会话内抓取上限"])
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()
