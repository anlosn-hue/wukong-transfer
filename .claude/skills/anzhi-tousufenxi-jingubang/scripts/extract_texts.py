# -*- coding: utf-8 -*-
"""按问题点抽取 G/H 文本并切批。用法：
python extract_texts.py <底库dir> <月份> <问题点> <输出dir> [--batch-chars N] [--all-months] [--sample-n N]"""
import argparse, json, random
from pathlib import Path
import pandas as pd

def run(lib_dir, month, problem, out_dir, batch_chars=15000, all_months=False, sample_n=None):
    problem = problem.strip()
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("batch_*.txt"):  # 清残留：同目录重跑不留上次多出来的批次文件
        stale.unlink()
    pieces = []
    for kind, label in (("duban", "督办"), ("tousu", "投诉")):
        for f in sorted(Path(lib_dir, kind).glob("*.csv")):
            if not all_months and f.stem != month:
                continue
            df = pd.read_csv(f, encoding="utf-8-sig")
            for _, r in df[df["问题点"] == problem].iterrows():
                date_col = "受理时间" if kind == "duban" else "受理日期"
                反馈 = r["客户反馈内容"] if pd.notna(r["客户反馈内容"]) else "（空）"
                处理 = r["处理结果"] if pd.notna(r["处理结果"]) else "（空）"
                pieces.append(f"[{label} {f.stem} {r[date_col]}]\n【反馈】{反馈}\n【处理】{处理}\n")
    总条数 = len(pieces)
    抽样说明 = None
    if sample_n and 总条数 > sample_n:
        random.seed(42)  # 固定种子保证同一批次可复现
        pieces = random.sample(pieces, sample_n)
        抽样说明 = f"随机抽样{sample_n}/{总条数}条（seed=42），非全量"
    batches, buf, size = [], [], 0
    for p in pieces:
        buf.append(p); size += len(p)
        if size >= batch_chars:
            batches.append(buf); buf, size = [], 0
    if buf:
        batches.append(buf)
    result = {"问题点": problem, "总条数": 总条数, "抽样条数": len(pieces) if 抽样说明 else None,
              "抽样说明": 抽样说明, "总字数": sum(len(p) for p in pieces), "批次": []}
    for i, b in enumerate(batches, 1):
        name = f"batch_{i:02d}.txt"
        (out_dir / name).write_text("\n".join(b), encoding="utf-8")
        result["批次"].append({"文件": name, "条数": len(b), "字数": sum(len(x) for x in b)})
    return result

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("lib"); ap.add_argument("month"); ap.add_argument("problem"); ap.add_argument("out")
    ap.add_argument("--batch-chars", type=int, default=15000)
    ap.add_argument("--all-months", action="store_true")
    ap.add_argument("--sample-n", type=int, default=None)
    a = ap.parse_args()
    print(json.dumps(run(a.lib, a.month, a.problem, a.out, a.batch_chars, a.all_months, a.sample_n),
                     ensure_ascii=False, indent=1))
