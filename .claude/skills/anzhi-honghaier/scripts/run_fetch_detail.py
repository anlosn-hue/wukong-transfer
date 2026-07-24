# -*- coding: utf-8 -*-
"""B 层入口：读清单.json 里命中笔记的 top-N，抓正文写入 正文/<id>.txt。
用法：python run_fetch_detail.py --outdir <目录>"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config
from contract import notes_from_json
from ledger import record_query, 会话抓取数
from channels import get_channel
from channels.playwright_channel import BlockedError

def 执行(*, 输出目录, 台账路径, channel, 抓取上限, 通道名, 会话上限=None, 关键词=""):
    data = json.loads((Path(输出目录) / "清单.json").read_text(encoding="utf-8"))
    关键词 = 关键词 or data.get("查询", {}).get("关键词", "")
    命中 = [n for n in notes_from_json(data) if n.命中筛选][:抓取上限]
    正文目录 = Path(输出目录) / "正文"
    正文目录.mkdir(parents=True, exist_ok=True)
    抓取数, 中断 = 0, None
    for n in 命中:
        if 会话上限 is not None and 会话抓取数(输出目录) >= 会话上限:
            中断 = f"会话抓取上限 {会话上限} 已达，停止本次深挖"
            break
        try:
            text = channel.fetch_detail(n)
        except BlockedError as e:
            中断 = f"{n.id}: {e}"
            break
        (正文目录 / f"{n.id}.txt").write_text(
            f"标题: {n.标题}\n链接: {n.链接}\n\n{text}", encoding="utf-8")
        抓取数 += 1
    record_query(台账路径, 关键词=关键词, 通道=通道名, 层级="B", 抓取量=抓取数)
    return {"抓取数": 抓取数, "中断": 中断}

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
              channel=ch, 抓取上限=cfg["漏斗"]["B层抓取上限"], 通道名=通道名,
              会话上限=cfg["合规"]["会话内抓取上限"])
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()
